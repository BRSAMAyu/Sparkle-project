import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';
import 'package:sparkle/features/home/domain/services/intent_classifier.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/intent/data/repositories/intent_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';

/// Predicted action for intent prediction bar
class PredictedAction {
  PredictedAction({
    required this.label,
    required this.icon,
    required this.action,
    this.confidence = 0.0,
    this.color,
  });

  final String label;
  final IconData icon;
  final VoidCallback action;
  final double confidence;
  final Color? color;
}

/// Intent prediction state
class IntentPredictionState {
  IntentPredictionState({
    this.idlePredictions = const [],
    this.typingPredictions = const [],
    this.isTyping = false,
    this.currentInput = '',
  });

  final List<PredictedAction> idlePredictions;
  final List<PredictedAction> typingPredictions;
  final bool isTyping;
  final String currentInput;

  IntentPredictionState copyWith({
    List<PredictedAction>? idlePredictions,
    List<PredictedAction>? typingPredictions,
    bool? isTyping,
    String? currentInput,
  }) =>
      IntentPredictionState(
        idlePredictions: idlePredictions ?? this.idlePredictions,
        typingPredictions: typingPredictions ?? this.typingPredictions,
        isTyping: isTyping ?? this.isTyping,
        currentInput: currentInput ?? this.currentInput,
      );
}

/// Intent prediction notifier
class IntentPredictionNotifier extends StateNotifier<IntentPredictionState> {
  IntentPredictionNotifier(this._ref)
      : super(IntentPredictionState()) {
    _generateIdlePredictions();
  }

  final Ref _ref;
  Timer? _backendDebounce;
  int _backendRequestId = 0;
  String _lastBackendText = '';

  void _generateIdlePredictions() {
    final dashboardState = _ref.read(dashboardProvider);
    final sprint = dashboardState.sprint;
    final nextActions = dashboardState.nextActions;

    final predictions = <PredictedAction>[
      // Sprint-based prediction
      if (sprint != null && sprint.daysLeft <= 3)
        PredictedAction(
          label: '冲刺冲刺',
          icon: Icons.flash_on_rounded,
          confidence: 0.9,
          color: const Color(0xFFFFA726),
          action: _navigateToFocus,
        ),
      // Next task prediction
      if (nextActions.isNotEmpty)
        PredictedAction(
          label: '继续"${nextActions.first.title}"',
          icon: Icons.play_arrow_rounded,
          confidence: 0.8,
          action: () => _navigateToTaskExecution(nextActions.first.id),
        ),
      // General predictions
      PredictedAction(
        label: '创建任务',
        icon: Icons.add_task_rounded,
        confidence: 0.6,
        action: _navigateToTaskCreate,
      ),
      PredictedAction(
        label: '开始专注',
        icon: Icons.center_focus_strong_rounded,
        confidence: 0.5,
        action: _navigateToFocus,
      ),
      PredictedAction(
        label: '查看日历',
        icon: Icons.calendar_today_rounded,
        confidence: 0.4,
        action: _navigateToCalendar,
      ),
      PredictedAction(
        label: '好奇心胶囊',
        icon: Icons.lightbulb_rounded,
        confidence: 0.3,
        action: _navigateToCapsule,
      ),
    ];

    state = state.copyWith(idlePredictions: predictions);
  }

  void onInputChanged(String text) {
    final isTyping = text.isNotEmpty;
    final result = IntentClassifier.classify(text);

    final typingPredictions = <PredictedAction>[];
    var localTopConfidence = 0.0;

    if (result != null) {
      final intent = result.type;
      final confidence = result.confidence;
      localTopConfidence = confidence;

      typingPredictions.addAll(_predictionsForIntent(intent, confidence, text));
    } else if (text.length > 3) {
      // Generic predictions for longer input without clear intent
      typingPredictions.addAll([
        PredictedAction(
          label: '发送给AI',
          icon: Icons.auto_awesome_rounded,
          confidence: 0.7,
          action: () => _sendChatMessage(text),
        ),
        PredictedAction(
          label: '创建任务',
          icon: Icons.add_task_rounded,
          confidence: 0.5,
          action: () => _navigateToTaskCreate(text),
        ),
        PredictedAction(
          label: '记录想法',
          icon: Icons.lightbulb_rounded,
          confidence: 0.4,
          action: () => _createCognitiveFragment(text),
        ),
      ]);
    }

    // Sort predictions by confidence (highest first)
    typingPredictions.sort((a, b) => b.confidence.compareTo(a.confidence));

    state = state.copyWith(
      isTyping: isTyping,
      currentInput: text,
      typingPredictions: typingPredictions,
    );

    _scheduleBackendPrediction(text, localTopConfidence);
  }

  void onInputCleared() {
    state = state.copyWith(
      isTyping: false,
      currentInput: '',
      typingPredictions: [],
    );
    _backendDebounce?.cancel();
    _lastBackendText = '';
  }

  void refreshIdlePredictions() {
    _generateIdlePredictions();
  }

  @override
  void dispose() {
    _backendDebounce?.cancel();
    super.dispose();
  }

  void _scheduleBackendPrediction(String text, double localConfidence) {
    final normalized = text.trim();
    if (normalized.length < 2) return;
    if (normalized == _lastBackendText) return;

    _backendDebounce?.cancel();
    final requestId = ++_backendRequestId;

    _backendDebounce = Timer(const Duration(milliseconds: 250), () async {
      try {
        final activePlanId = _ref.read(activePlanProvider);
        final response =
            await _ref.read(intentRepositoryProvider).predictIntent(
                  partialText: normalized,
                  activePlanId: activePlanId,
                );

        if (requestId != _backendRequestId) return;
        if (normalized != state.currentInput.trim()) return;

        final backendIntent = _mapBackendIntent(response.intentType);
        if (backendIntent == null) return;
        if (response.confidence < 0.5) return;
        if (response.confidence + 0.05 < localConfidence) return;

        final backendPredictions =
            _predictionsForIntent(backendIntent, response.confidence, normalized)
              ..sort((a, b) => b.confidence.compareTo(a.confidence));
        if (backendPredictions.isEmpty) return;

        state = state.copyWith(
          isTyping: true,
          currentInput: normalized,
          typingPredictions: backendPredictions,
        );
        _lastBackendText = normalized;
      } catch (e) {
        debugPrint('Intent prediction API failed, using local classifier: $e');
      }
    });
  }

  EnhancedIntentType? _mapBackendIntent(String intentType) {
    switch (intentType) {
      case 'task_management':
      case 'time_planning':
        return EnhancedIntentType.task;
      case 'knowledge_query':
      case 'learning':
        return EnhancedIntentType.learn;
      case 'reflection':
        return EnhancedIntentType.review;
      case 'social':
        return EnhancedIntentType.chat;
      case 'tool_call':
        return EnhancedIntentType.task;
      default:
        return null;
    }
  }

  List<PredictedAction> _predictionsForIntent(
    EnhancedIntentType intent,
    double confidence,
    String text,
  ) {
    switch (intent) {
      case EnhancedIntentType.task:
        return [
          PredictedAction(
            label: '创建任务',
            icon: Icons.add_task_rounded,
            confidence: confidence,
            color: const Color(0xFF66BB6A),
            action: () => _navigateToTaskCreate(text),
          ),
          PredictedAction(
            label: '设置提醒',
            icon: Icons.notification_add_rounded,
            confidence: confidence * 0.85,
            action: () => _navigateToTaskCreate(text),
          ),
        ];
      case EnhancedIntentType.capsule:
        return [
          PredictedAction(
            label: '记录想法',
            icon: Icons.lightbulb_rounded,
            confidence: confidence,
            color: const Color(0xFFAB47BC),
            action: () => _createCognitiveFragment(text),
          ),
          PredictedAction(
            label: '认知棱镜',
            icon: Icons.psychology_rounded,
            confidence: confidence * 0.7,
            action: _navigateToPatterns,
          ),
        ];
      case EnhancedIntentType.translation:
        return [
          PredictedAction(
            label: '翻译文本',
            icon: Icons.translate_rounded,
            confidence: confidence,
            color: const Color(0xFF26C6DA),
            action: () => _sendChatMessage(text),
          ),
          PredictedAction(
            label: '学习语言',
            icon: Icons.language_rounded,
            confidence: confidence * 0.75,
            action: () => _sendChatMessage('请帮我学习$text'),
          ),
        ];
      case EnhancedIntentType.prism:
        return [
          PredictedAction(
            label: '查看认知棱镜',
            icon: Icons.psychology_rounded,
            confidence: confidence,
            color: const Color(0xFF7E57C2),
            action: _navigateToPatterns,
          ),
          PredictedAction(
            label: '行为分析',
            icon: Icons.analytics_rounded,
            confidence: confidence * 0.8,
            action: _navigateToPatterns,
          ),
        ];
      case EnhancedIntentType.sprint:
        return [
          PredictedAction(
            label: '开始冲刺',
            icon: Icons.flash_on_rounded,
            confidence: confidence,
            color: const Color(0xFFFFA726),
            action: _navigateToFocus,
          ),
          PredictedAction(
            label: '专注模式',
            icon: Icons.center_focus_strong_rounded,
            confidence: confidence * 0.85,
            action: _navigateToFocus,
          ),
        ];
      case EnhancedIntentType.learn:
        return [
          PredictedAction(
            label: '开始学习',
            icon: Icons.school_rounded,
            confidence: confidence,
            color: const Color(0xFFEC407A),
            action: () => _sendChatMessage(text),
          ),
          PredictedAction(
            label: '创建学习计划',
            icon: Icons.edit_calendar_rounded,
            confidence: confidence * 0.7,
            action: () => _navigateToTaskCreate(text),
          ),
        ];
      case EnhancedIntentType.review:
        return [
          PredictedAction(
            label: '开始复习',
            icon: Icons.replay_rounded,
            confidence: confidence,
            color: const Color(0xFF5C6BC0),
            action: () => _sendChatMessage('请帮我复习：$text'),
          ),
          PredictedAction(
            label: '查看错题本',
            icon: Icons.menu_book_rounded,
            confidence: confidence * 0.75,
            action: _navigateToErrorBook,
          ),
        ];
      case EnhancedIntentType.chat:
        return [
          PredictedAction(
            label: '发送给AI',
            icon: Icons.auto_awesome_rounded,
            confidence: confidence,
            color: const Color(0xFF42A5F5),
            action: () => _sendChatMessage(text),
          ),
        ];
    }
  }

  // ========== Navigation Actions ==========

  void _navigateToFocus() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/focus');
    }
  }

  void _navigateToTaskExecution(String taskId) {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/tasks/$taskId/execute');
    }
  }

  void _navigateToTaskCreate([String? title]) {
    final context = navigatorKey.currentContext;
    if (context == null) return;

    if (title != null && title.isNotEmpty) {
      final encodedTitle = Uri.encodeComponent(title);
      GoRouter.of(context).push('/tasks/new?title=$encodedTitle');
    } else {
      GoRouter.of(context).push('/tasks/new');
    }
  }

  void _navigateToCalendar() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/calendar-stats');
    }
  }

  void _navigateToCapsule() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/curiosity-capsule');
    }
  }

  void _navigateToPatterns() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/cognitive/patterns');
    }
  }

  void _navigateToErrorBook() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/error-book');
    }
  }

  Future<void> _sendChatMessage(String text) async {
    final context = navigatorKey.currentContext;
    if (context == null) return;

    // If already on chat screen, send message directly without navigation
    if (_isCurrentRoute('/chat')) {
      try {
        await _ref.read(chatProvider.notifier).sendMessage(text);
      } catch (e) {
        debugPrint('Error sending chat message: $e');
      }
      return;
    }

    // Otherwise, navigate to chat screen first, then send message
    GoRouter.of(context).push('/chat');

    // Wait for navigation to complete, then send message
    await Future<void>.delayed(const Duration(milliseconds: 300));

    try {
      await _ref.read(chatProvider.notifier).sendMessage(text);
    } catch (e) {
      debugPrint('Error sending chat message: $e');
    }
  }

  /// Check if the current route matches the given path
  bool _isCurrentRoute(String path) {
    final context = navigatorKey.currentContext;
    if (context == null) return false;
    
    try {
      // Use routerDelegate.currentConfiguration to reliably get location from root context
      // GoRouterState.of(context) can fail if context is not below a GoRoute
      final location = GoRouter.of(context).routerDelegate.currentConfiguration.uri.path;
      return location == path || location.startsWith('$path/');
    } catch (e) {
      debugPrint('Error checking current route: $e');
      return false;
    }
  }

  Future<void> _createCognitiveFragment(String text) async {
    try {
      // Create the cognitive fragment
      final fragment = await _ref.read(cognitiveProvider.notifier).createFragment(
            content: text,
            sourceType: 'intent_prediction',
          );

      if (fragment != null) {
        // Navigate to capsule screen after successful creation
        final context = navigatorKey.currentContext;
        if (context != null) {
          GoRouter.of(context).push('/curiosity-capsule');
        }
      }
    } catch (e) {
      debugPrint('Error creating cognitive fragment: $e');
      // Still navigate to capsule screen even if creation fails
      final context = navigatorKey.currentContext;
      if (context != null) {
        GoRouter.of(context).push('/curiosity-capsule');
      }
    }
  }
}

/// Intent prediction provider
final intentPredictionProvider =
    StateNotifierProvider<IntentPredictionNotifier, IntentPredictionState>(
  IntentPredictionNotifier.new,
);

/// Current visible predictions provider (combines idle and typing)
final visiblePredictionsProvider = Provider<List<PredictedAction>>((ref) {
  final predictionState = ref.watch(intentPredictionProvider);
  if (predictionState.isTyping) {
    return predictionState.typingPredictions;
  }
  return predictionState.idlePredictions;
});
