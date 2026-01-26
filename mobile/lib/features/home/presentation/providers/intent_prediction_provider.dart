import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/home/domain/services/intent_classifier.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

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
    final intent = IntentClassifier.classify(text);

    final typingPredictions = <PredictedAction>[];

    if (intent != null) {
      switch (intent) {
        case IntentType.task:
          typingPredictions.addAll([
            PredictedAction(
              label: '创建任务',
              icon: Icons.add_task_rounded,
              confidence: 0.95,
              color: const Color(0xFF66BB6A),
              action: () => _navigateToTaskCreate(text),
            ),
            PredictedAction(
              label: '设置提醒',
              icon: Icons.notification_add_rounded,
              confidence: 0.8,
              action: () => _navigateToTaskCreate(text),
            ),
          ]);
        case IntentType.capsule:
          typingPredictions.addAll([
            PredictedAction(
              label: '记录想法',
              icon: Icons.lightbulb_rounded,
              confidence: 0.95,
              color: const Color(0xFFAB47BC),
              action: () => _createCognitiveFragment(text),
            ),
            PredictedAction(
              label: '认知棱镜',
              icon: Icons.psychology_rounded,
              confidence: 0.7,
              action: _navigateToPatterns,
            ),
          ]);
        case IntentType.chat:
          typingPredictions.addAll([
            PredictedAction(
              label: '发送给AI',
              icon: Icons.auto_awesome_rounded,
              confidence: 0.95,
              color: const Color(0xFF42A5F5),
              action: () => _sendChatMessage(text),
            ),
          ]);
      }
    } else if (text.length > 3) {
      // Generic predictions for longer input
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
      ]);
    }

    state = state.copyWith(
      isTyping: isTyping,
      currentInput: text,
      typingPredictions: typingPredictions,
    );
  }

  void onInputCleared() {
    state = state.copyWith(
      isTyping: false,
      currentInput: '',
      typingPredictions: [],
    );
  }

  void refreshIdlePredictions() {
    _generateIdlePredictions();
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
