import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/data/repositories/prediction_repository.dart';
import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';
import 'package:sparkle/features/home/domain/services/intent_classifier.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Predicted action for intent prediction bar
class PredictedAction {
  PredictedAction({
    required this.label,
    required this.icon,
    required this.action,
    this.confidence = 0.0,
    this.color,
    this.candidateId,
    this.actionType,
    this.reason,
  });

  final String label;
  final IconData icon;
  final VoidCallback action;
  final double confidence;
  final Color? color;
  final String? candidateId;
  final String? actionType;
  final String? reason;
}

/// Intent prediction state
class IntentPredictionState {
  IntentPredictionState({
    this.idlePredictions = const [],
    this.typingPredictions = const [],
    this.typingInsight,
    this.isTyping = false,
    this.currentInput = '',
  });

  final List<PredictedAction> idlePredictions;
  final List<PredictedAction> typingPredictions;
  final PredictionInsightData? typingInsight;
  final bool isTyping;
  final String currentInput;

  IntentPredictionState copyWith({
    List<PredictedAction>? idlePredictions,
    List<PredictedAction>? typingPredictions,
    PredictionInsightData? typingInsight,
    bool? isTyping,
    String? currentInput,
  }) =>
      IntentPredictionState(
        idlePredictions: idlePredictions ?? this.idlePredictions,
        typingPredictions: typingPredictions ?? this.typingPredictions,
        typingInsight: typingInsight ?? this.typingInsight,
        isTyping: isTyping ?? this.isTyping,
        currentInput: currentInput ?? this.currentInput,
      );
}

/// Intent prediction notifier
class IntentPredictionNotifier extends StateNotifier<IntentPredictionState> {
  IntentPredictionNotifier(this._ref) : super(IntentPredictionState()) {
    _feedbackService = CandidateFeedbackService(
      _ref.read(dioProvider),
      accessTokenGetter: _ref.read(authRepositoryProvider).getAccessToken,
    );
    _eventStream = _ref.read(appEventStreamServiceProvider);
    _predictionAttribution = _ref.read(predictionAttributionServiceProvider);
    _generateIdlePredictions();
  }

  final Ref _ref;
  late final CandidateFeedbackService _feedbackService;
  late final AppEventStreamService _eventStream;
  late final PredictionAttributionService _predictionAttribution;
  Timer? _backendDebounce;
  int _backendRequestId = 0;
  String _lastBackendText = '';

  void _generateIdlePredictions() {
    final dashboardState = _ref.read(dashboardProvider);
    final sprint = dashboardState.sprint;
    final nextActions = dashboardState.nextActions;

    final l10n = I18nService.instance.l10n;
    final isChinese = I18nService.instance.isChinese;
    final predictions = <PredictedAction>[
      // Sprint-based prediction
      if (sprint != null && sprint.daysLeft <= 3)
        PredictedAction(
          label: l10n.intentPredictionSprint,
          icon: Icons.flash_on_rounded,
          confidence: 0.9,
          color: DS.warning,
          action: _navigateToFocus,
        ),
      // Next task prediction
      if (nextActions.isNotEmpty)
        PredictedAction(
          label: l10n.intentPredictionContinueTask(nextActions.first.title),
          icon: Icons.play_arrow_rounded,
          confidence: 0.8,
          action: () => _navigateToTaskExecution(nextActions.first.id),
        ),
      // General predictions
      PredictedAction(
        label: l10n.intentPredictionCreateTask,
        icon: Icons.add_task_rounded,
        confidence: 0.6,
        action: _navigateToTaskCreate,
      ),
      PredictedAction(
        label: l10n.intentPredictionStartFocus,
        icon: Icons.center_focus_strong_rounded,
        confidence: 0.5,
        action: _navigateToFocus,
      ),
      PredictedAction(
        label: l10n.intentPredictionViewCalendar,
        icon: Icons.calendar_today_rounded,
        confidence: 0.4,
        action: _navigateToCalendar,
      ),
      PredictedAction(
        label: l10n.intentPredictionCuriosityCapsule,
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
          label: l10n.intentPredictionSendToAI,
          icon: Icons.auto_awesome_rounded,
          confidence: 0.7,
          action: () => _sendChatMessage(text),
        ),
        PredictedAction(
          label: l10n.intentPredictionCreateTask,
          icon: Icons.add_task_rounded,
          confidence: 0.5,
          action: () => _navigateToTaskCreate(text),
        ),
        PredictedAction(
          label: l10n.intentPredictionNoteIdea,
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
        final insight =
            await _ref.read(predictionRepositoryProvider).getRealtimeNextStep(
                  partialText: normalized,
                  activePlanId: activePlanId,
                );

        if (requestId != _backendRequestId) return;
        if (normalized != state.currentInput.trim()) return;

        if (insight == null) return;
        if (insight.confidence < 0.45) return;
        if (insight.confidence + 0.05 < localConfidence) return;

        final backendPredictions = _predictionsFromInsight(insight)
          ..sort((a, b) => b.confidence.compareTo(a.confidence));
        if (backendPredictions.isEmpty) return;

        state = state.copyWith(
          isTyping: true,
          currentInput: normalized,
          typingPredictions: backendPredictions,
          typingInsight: insight,
        );
        _lastBackendText = normalized;
      } catch (e) {
        debugPrint('Realtime next-step API failed, using local classifier: $e');
      }
    });
  }

  List<PredictedAction> _predictionsFromInsight(PredictionInsightData insight) {
    final actions = insight.recommendedActions.isNotEmpty
        ? insight.recommendedActions
        : [
            PredictionActionData(
              id: '${insight.predictionId}:chat',
              label: l10n.intentPredictionContinue,
              actionType: insight.predictedActionType,
              targetRoute: '/chat',
              suggestedPrompt: insight.suggestedPrompt,
            ),
          ];

    return actions.map((action) {
      final config = _visualConfigForAction(action.actionType);
      return PredictedAction(
        label: action.label,
        icon: config.$1,
        color: config.$2,
        confidence: insight.confidence,
        candidateId: insight.trackingCandidateId,
        actionType: action.actionType,
        reason: insight.summary,
        action: () => _handlePredictionAction(insight, action),
      );
    }).toList();
  }

  (IconData, Color?) _visualConfigForAction(String actionType) {
    switch (actionType) {
      case 'create_task':
        return (Icons.add_task_rounded, DS.success);
      case 'study_plan':
        return (Icons.edit_calendar_rounded, DS.brandPrimary);
      case 'error_diagnosis':
        return (Icons.healing_rounded, DS.warning);
      case 'resume_task':
      case 'resume_priority_task':
        return (Icons.play_arrow_rounded, DS.prismBlue);
      case 'start_focus':
        return (Icons.center_focus_strong_rounded, DS.warning);
      case 'translate':
        return (Icons.translate_rounded, DS.info);
      default:
        return (Icons.auto_awesome_rounded, DS.brandPrimary);
    }
  }

  Future<void> _handlePredictionAction(
    PredictionInsightData insight,
    PredictionActionData action,
  ) async {
    unawaited(_feedbackService.recordFeedback(
      candidateId: insight.trackingCandidateId,
      actionType: action.actionType.isNotEmpty
          ? action.actionType
          : insight.trackingActionType,
      feedbackType: 'accept',
      contextSnapshot: _feedbackContext(insight),
    ),);
    unawaited(_eventStream.recordPredictionFeedback(
      predictionId: insight.predictionId,
      feedbackType: 'accept',
      actionType: action.actionType.isNotEmpty
          ? action.actionType
          : insight.trackingActionType,
      surface: insight.surface ?? 'chat_input',
      suggestedPrompt: action.suggestedPrompt.isNotEmpty
          ? action.suggestedPrompt
          : insight.suggestedPrompt,
      entityType: insight.entityCard?.entityType,
      entityId: insight.entityCard?.entityId,
    ),);
    unawaited(
      _predictionAttribution.rememberAcceptedPrediction(
        predictionId: insight.predictionId,
        candidateId: insight.trackingCandidateId,
        actionType: action.actionType.isNotEmpty
            ? action.actionType
            : insight.trackingActionType,
        surface: insight.surface ?? 'chat_input',
        horizon: insight.horizon,
        source: insight.predictionSource,
        suggestedPrompt: action.suggestedPrompt.isNotEmpty
            ? action.suggestedPrompt
            : insight.suggestedPrompt,
        entityType: insight.entityCard?.entityType,
        entityId: insight.entityCard?.entityId,
      ),
    );

    if (action.targetRoute == '/chat') {
      await _sendChatMessage(
        action.suggestedPrompt.isNotEmpty
            ? action.suggestedPrompt
            : insight.suggestedPrompt,
      );
      return;
    }

    final context = navigatorKey.currentContext;
    if (context != null) {
      unawaited(GoRouter.of(context).push(action.targetRoute));
    }
    _ref.invalidate(dashboardProvider);
  }

  Map<String, dynamic> _feedbackContext(PredictionInsightData insight) => {
        'prediction': {
          'prediction_id': insight.predictionId,
          'horizon': insight.horizon,
          'surface': insight.surface ?? 'chat_input',
          'source': insight.predictionSource,
          'tier': insight.predictionTier,
          'action_type': insight.predictedActionType,
        },
      };

  List<PredictedAction> _predictionsForIntent(
    EnhancedIntentType intent,
    double confidence,
    String text,
  ) {
    final l10n = I18nService.instance.l10n;
    switch (intent) {
      case EnhancedIntentType.task:
        return [
          PredictedAction(
            label: l10n.intentTaskCreate,
            icon: Icons.add_task_rounded,
            confidence: confidence,
            color: DS.success,
            action: () => _navigateToTaskCreate(text),
          ),
          PredictedAction(
            label: l10n.intentTaskSetReminder,
            icon: Icons.notification_add_rounded,
            confidence: confidence * 0.85,
            action: () => _navigateToTaskCreate(text),
          ),
        ];
      case EnhancedIntentType.capsule:
        return [
          PredictedAction(
            label: l10n.intentCapsuleNoteIdea,
            icon: Icons.lightbulb_rounded,
            confidence: confidence,
            color: DS.prismPurple,
            action: () => _createCognitiveFragment(text),
          ),
          PredictedAction(
            label: l10n.intentCapsuleCognitivePrism,
            icon: Icons.psychology_rounded,
            confidence: confidence * 0.7,
            action: _navigateToPatterns,
          ),
        ];
      case EnhancedIntentType.translation:
        return [
          PredictedAction(
            label: l10n.intentTranslationTranslate,
            icon: Icons.translate_rounded,
            confidence: confidence,
            color: DS.info,
            action: () => _sendChatMessage(text),
          ),
          PredictedAction(
            label: l10n.intentTranslationLearnLang,
            icon: Icons.language_rounded,
            confidence: confidence * 0.75,
            action: () => _sendChatMessage(l10n.intentTranslationHelpLearn(text)),
          ),
        ];
      case EnhancedIntentType.prism:
        return [
          PredictedAction(
            label: l10n.intentPrismView,
            icon: Icons.psychology_rounded,
            confidence: confidence,
            color: DS.brandSecondary,
            action: _navigateToPatterns,
          ),
          PredictedAction(
            label: l10n.intentPrismBehaviorAnalysis,
            icon: Icons.analytics_rounded,
            confidence: confidence * 0.8,
            action: _navigateToPatterns,
          ),
        ];
      case EnhancedIntentType.sprint:
        return [
          PredictedAction(
            label: l10n.intentSprintStart,
            icon: Icons.flash_on_rounded,
            confidence: confidence,
            color: DS.warning,
            action: _navigateToFocus,
          ),
          PredictedAction(
            label: l10n.intentSprintFocusMode,
            icon: Icons.center_focus_strong_rounded,
            confidence: confidence * 0.85,
            action: _navigateToFocus,
          ),
        ];
      case EnhancedIntentType.learn:
        return [
          PredictedAction(
            label: l10n.intentLearnStart,
            icon: Icons.school_rounded,
            confidence: confidence,
            color: DS.brandPrimary,
            action: () => _sendChatMessage(text),
          ),
          PredictedAction(
            label: l10n.intentLearnCreatePlan,
            icon: Icons.edit_calendar_rounded,
            confidence: confidence * 0.7,
            action: () => _navigateToTaskCreate(text),
          ),
        ];
      case EnhancedIntentType.review:
        return [
          PredictedAction(
            label: l10n.intentReviewStart,
            icon: Icons.replay_rounded,
            confidence: confidence,
            color: DS.info.shade700,
            action: () => _sendChatMessage(l10n.intentReviewHelpReview(text)),
          ),
          PredictedAction(
            label: l10n.intentReviewErrorBook,
            icon: Icons.menu_book_rounded,
            confidence: confidence * 0.75,
            action: _navigateToErrorBook,
          ),
        ];
      case EnhancedIntentType.chat:
        return [
          PredictedAction(
            label: l10n.intentChatSendToAI,
            icon: Icons.auto_awesome_rounded,
            confidence: confidence,
            color: DS.prismBlue,
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
      // 🔧 修复：从taskListProvider获取完整任务并设置activeTaskProvider
      final taskState = _ref.read(taskListProvider);
      TaskModel? task;

      // 尝试从各个列表中查找任务
      try {
        task = taskState.tasks.firstWhere((t) => t.id == taskId);
      } catch (_) {
        try {
          task = taskState.todayTasks.firstWhere((t) => t.id == taskId);
        } catch (_) {
          try {
            task = taskState.recommendedTasks.firstWhere((t) => t.id == taskId);
          } catch (_) {
            // 任务不在任何列表中
          }
        }
      }

      if (task != null) {
        _ref.read(activeTaskProvider.notifier).state = task;
      }
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
      GoRouter.of(context).push('/errors');
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
    GoRouter.of(context).go('/chat');

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
      final location =
          GoRouter.of(context).routerDelegate.currentConfiguration.uri.path;
      return location == path || location.startsWith('$path/');
    } catch (e) {
      debugPrint('Error checking current route: $e');
      return false;
    }
  }

  Future<void> _createCognitiveFragment(String text) async {
    try {
      // Create the cognitive fragment
      final fragment =
          await _ref.read(cognitiveProvider.notifier).createFragment(
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
