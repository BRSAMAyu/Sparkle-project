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

    if (text.isEmpty) {
      state = state.copyWith(
        isTyping: false,
        currentInput: '',
        typingPredictions: [],
      );
      return;
    }

    // Try backend API prediction first (for text longer than 2 characters)
    if (text.length > 2) {
      _fetchBackendPrediction(text);
      return;
    }

    // Fall back to local classifier for short text
    final result = IntentClassifier.classify(text);
    final typingPredictions = <PredictedAction>[];

    if (result != null) {
      final intent = result.type;
      final confidence = result.confidence;

      // Generate predictions based on intent type with confidence-aware sorting
      switch (intent) {
        case EnhancedIntentType.task:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.capsule:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.translation:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.prism:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.sprint:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.learn:
          typingPredictions.addAll([
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
          ]);
        case EnhancedIntentType.review:
          typingPredictions.addAll([
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
              action: () => _navigateToErrorBook(),
            ),
          ]);
        case EnhancedIntentType.chat:
          typingPredictions.addAll([
            PredictedAction(
              label: '发送给AI',
              icon: Icons.auto_awesome_rounded,
              confidence: confidence,
              color: const Color(0xFF42A5F5),
              action: () => _sendChatMessage(text),
            ),
          ]);
      }
    } else {
      // Generic predictions for input without clear intent
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
  }

  /// Fetch intent prediction from backend API
  Future<void> _fetchBackendPrediction(String text) async {
    try {
      final repository = _ref.read(intentRepositoryProvider);

      // Get active plan ID if available
      final activePlanId = _ref.read(activePlanProvider);

      final prediction = await repository.predictIntent(
        partialText: text,
        activePlanId: activePlanId,
      );

      // Convert backend prediction to PredictedAction list
      final typingPredictions = _convertPredictionToActions(prediction, text);

      // Sort predictions by confidence
      typingPredictions.sort((a, b) => b.confidence.compareTo(a.confidence));

      state = state.copyWith(
        isTyping: true,
        currentInput: text,
        typingPredictions: typingPredictions,
      );
    } catch (e) {
      // Fall back to local classifier on API error
      debugPrint('Backend prediction failed, using local classifier: $e');

      // Trigger local classification
      final result = IntentClassifier.classify(text);
      if (result != null) {
        onInputChanged(text);
      }
    }
  }

  /// Convert backend prediction response to PredictedAction list
  List<PredictedAction> _convertPredictionToActions(
    IntentPredictionResponse prediction,
    String originalText,
  ) {
    final actions = <PredictedAction>[];
    final intentType = prediction.intentType;
    final confidence = prediction.confidence;
    final suggestedActions = prediction.suggestedActions;

    // Map intent type to action configuration
    final actionConfig = _getActionConfigForIntentType(intentType);

    // Generate actions from backend suggestions
    for (final actionLabel in suggestedActions) {
      final config = actionConfig[actionLabel];
      if (config != null) {
        actions.add(PredictedAction(
          label: actionLabel,
          icon: config['icon'],
          confidence: confidence,
          color: config['color'],
          action: config['action'],
        ));
      }
    }

    // If no actions from suggestions, use defaults
    if (actions.isEmpty) {
      actions.addAll(_getDefaultActionsForIntentType(intentType, confidence, originalText));
    }

    return actions;
  }

  /// Get action configuration for intent type
  Map<String, Map<String, dynamic>> _getActionConfigForIntentType(String intentType) {
    switch (intentType) {
      case 'task_management':
        return {
          '创建任务': {
            'icon': Icons.add_task_rounded,
            'color': const Color(0xFF66BB6A),
            'action': () => _navigateToTaskCreate(),
          },
          '设置提醒': {
            'icon': Icons.notification_add_rounded,
            'color': const Color(0xFF66BB6A),
            'action': () => _navigateToTaskCreate(),
          },
        };
      case 'knowledge_query':
        return {
          '发送给AI': {
            'icon': Icons.auto_awesome_rounded,
            'color': const Color(0xFF42A5F5),
            'action': () => _sendChatMessage(''),
          },
          '查看星图': {
            'icon': Icons.public_rounded,
            'color': const Color(0xFF42A5F5),
            'action': () => _navigateToGalaxy(),
          },
        };
      case 'time_planning':
        return {
          '创建计划': {
            'icon': Icons.edit_calendar_rounded,
            'color': const Color(0xFFEC407A),
            'action': () => _navigateToTaskCreate(),
          },
          '日历视图': {
            'icon': Icons.calendar_today_rounded,
            'color': const Color(0xFFEC407A),
            'action': _navigateToCalendar,
          },
        };
      case 'learning':
        return {
          '开始学习': {
            'icon': Icons.school_rounded,
            'color': const Color(0xFFEC407A),
            'action': () => _sendChatMessage(),
          },
          '学习计划': {
            'icon': Icons.edit_calendar_rounded,
            'color': const Color(0xFFEC407A),
            'action': () => _navigateToTaskCreate(),
          },
        };
      case 'reflection':
        return {
          '开始复习': {
            'icon': Icons.replay_rounded,
            'color': const Color(0xFF5C6BC0),
            'action': () => _sendChatMessage(),
          },
          '错题本': {
            'icon': Icons.menu_book_rounded,
            'color': const Color(0xFF5C6BC0),
            'action': _navigateToErrorBook,
          },
        };
      default:
        return {
          '发送给AI': {
            'icon': Icons.auto_awesome_rounded,
            'color': const Color(0xFF42A5F5),
            'action': () => _sendChatMessage(),
          },
        };
    }
  }

  /// Get default actions for intent type when backend provides no suggestions
  List<PredictedAction> _getDefaultActionsForIntentType(
    String intentType,
    double confidence,
    String originalText,
  ) {
    switch (intentType) {
      case 'task_management':
        return [
          PredictedAction(
            label: '创建任务',
            icon: Icons.add_task_rounded,
            confidence: confidence,
            color: const Color(0xFF66BB6A),
            action: () => _navigateToTaskCreate(originalText),
          ),
        ];
      case 'knowledge_query':
        return [
          PredictedAction(
            label: '发送给AI',
            icon: Icons.auto_awesome_rounded,
            confidence: confidence,
            color: const Color(0xFF42A5F5),
            action: () => _sendChatMessage(originalText),
          ),
        ];
      case 'learning':
        return [
          PredictedAction(
            label: '开始学习',
            icon: Icons.school_rounded,
            confidence: confidence,
            color: const Color(0xFFEC407A),
            action: () => _sendChatMessage(originalText),
          ),
        ];
      default:
        return [
          PredictedAction(
            label: '发送给AI',
            icon: Icons.auto_awesome_rounded,
            confidence: confidence,
            action: () => _sendChatMessage(originalText),
          ),
        ];
    }
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

  void _navigateToErrorBook() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/error-book');
    }
  }

  void _navigateToGalaxy() {
    final context = navigatorKey.currentContext;
    if (context != null) {
      GoRouter.of(context).push('/galaxy');
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
