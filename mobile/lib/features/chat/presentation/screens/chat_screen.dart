import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/chat/presentation/widgets/causal_timeline_panel.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/repositories/aurora_daily_startup_repository.dart';
import 'package:sparkle/features/chat/chat_routes.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_calibration_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_workflow_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_reasoning_mode_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_design_language_widgets.dart';
import 'package:sparkle/features/chat/presentation/widgets/comeback_banner.dart';
import 'package:sparkle/features/chat/presentation/widgets/contextual_correction_bar.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_transition_banner.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_prediction_dock.dart';
import 'package:sparkle/features/chat/presentation/widgets/expert_roundtable_widget.dart';
import 'package:sparkle/features/chat/presentation/widgets/guidance_mode_toggle.dart';
import 'package:sparkle/features/chat/presentation/widgets/offline_queue_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/community_insight_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/goal_arbitration_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/divine_moment_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/experience_envelope_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/growth_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/spine_receipt_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/stale_recovery_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/strategy_intervention_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_selector_pill.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/status_awareness_bar.dart';
import 'package:sparkle/features/chat/presentation/widgets/study_materials_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/transparency_floating_capsule.dart';
import 'package:sparkle/features/chat/presentation/widgets/understanding_drawer.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_drawer.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/presentation/providers/document_library_provider.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/settings/presentation/screens/transparency_settings_screen.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

const _defaultAiSystemPreferences = TransparencyPreferences(
  enabled: true,
  showTokenUsage: true,
  showAgentSwitching: true,
  showReasoningSteps: true,
  displayMode: TransparencyDisplayMode.collapsedFloating,
  autoCollapseOnComplete: true,
  allowPerTurnDismiss: true,
);

IconData _chatFailureIcon(String? code) {
  switch (FailureKindCode.fromCode(code)) {
    case FailureKind.offline:
    case FailureKind.network:
      return Icons.wifi_off_rounded;
    case FailureKind.auth:
      return Icons.lock_outline_rounded;
    case FailureKind.server:
      return Icons.cloud_sync_outlined;
    case FailureKind.validation:
      return Icons.edit_note_rounded;
    case FailureKind.unknown:
      return Icons.error_outline_rounded;
  }
}

String _chatFailureTitle(BuildContext context, String? code) {
  final l10n = AppLocalizations.of(context)!;
  return switch (FailureKindCode.fromCode(code)) {
    FailureKind.offline => l10n.chatFailureOffline,
    FailureKind.auth => l10n.chatFailureAuth,
    FailureKind.server => l10n.chatFailureServer,
    FailureKind.validation => l10n.chatFailureValidation,
    FailureKind.network => l10n.chatFailureNetwork,
    FailureKind.unknown => l10n.chatFailureUnknown,
  };
}

String _chatFailureActionLabel(BuildContext context, String? code) {
  final l10n = AppLocalizations.of(context)!;
  return switch (FailureKindCode.fromCode(code)) {
    FailureKind.auth => l10n.chatFailureActionSignIn,
    FailureKind.validation => l10n.chatFailureActionEdit,
    FailureKind.offline => l10n.chatFailureActionRetryOnline,
    _ => l10n.retry,
  };
}

enum _ChatShortcutAction {
  newSession,
}

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({
    super.key,
    this.initialPrompt,
    this.initialChatMode,
    this.initialConversationId,
    this.initialAiMessage,
    this.initialUserMessage,
    this.fromModelingComplete = false,
    this.modelingOutput,
    this.initialExtraContext,
  });

  final String? initialPrompt;
  final String? initialChatMode;
  final String? initialConversationId;

  /// Pre-generated AI opening message shown immediately on first open (no backend call).
  /// Used after onboarding to make the AI feel present from the very first moment.
  final String? initialAiMessage;

  /// User message to dispatch automatically after route hydration.
  /// Used by onboarding/modeling completion and by contextual Aurora correction
  /// entries that need to carry structured context into the next chat turn.
  final String? initialUserMessage;
  final bool fromModelingComplete;
  final Map<String, dynamic>? modelingOutput;
  final Map<String, dynamic>? initialExtraContext;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  static const Set<String> _shellRootPaths = {
    '/home',
    '/galaxy',
    '/chat',
    '/community',
    '/profile',
  };
  static const double _chatBottomSurfaceHorizontalInset = DS.spacing16;

  final ScrollController _scrollController = ScrollController();
  bool _showContextControls = false;
  String? _dispatchedInitialPrompt;
  String? _dispatchedInitialUserMessage;
  String? _hydratedConversationId;
  String? _hydratedChatOpeningConversationId;
  String? _hydratedComebackSignature;
  String? _hydratedDailyStartupKey;
  AuroraComebackContext? _comebackContext;
  bool _showComebackBanner = false;
  String? _newMessageDividerBeforeId;
  String? _latestReadConversationId;
  String? _latestReadMessageId;
  final Map<String, GlobalKey> _messageKeys = <String, GlobalKey>{};
  bool _dailyStartupRetryBannerVisible = false;
  bool _dailyStartupRetryInFlight = false;
  String? _reviewNodeLabel;
  double? _reviewNodeMastery;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_handleScroll);
    _extractReviewNodeContext();
    ref
      ..listenManual(
        chatProvider.select((state) => state.messages),
        (previous, next) {
          if (next.length > (previous?.length ?? 0)) {
            _scrollToBottom();
          }
        },
      )
      ..listenManual(activePlanProvider, (previous, next) {
        if (previous != next) {
          unawaited(ref.read(chatProvider.notifier).switchPlanSession(next));
        }
      })
      ..listenManual(chatProvider.select((state) => state.aiStatus),
          (previous, next) {
        final hadStatus = previous != null && previous.trim().isNotEmpty;
        final hasStatus = next != null && next.trim().isNotEmpty;
        if (!hadStatus && hasStatus) {
          unawaited(
            SensoryFeedbackService.emit(
              SensoryFeedbackEvent.aiResponseStart,
            ),
          );
        }
      })
      ..listenManual(
        chatProvider.select(_shouldDuckForReasoning),
        (previous, next) {
          unawaited(
            BgmService.setReadingActivity(next),
          );
        },
      )
      // F-08: 监听错误状态，10秒后自动清除并提示用户
      ..listenManual(chatProvider.select((state) => state.error),
          (previous, next) {
        if (next != null && next != previous) {
          AppFeedback.error(context, next);
          Future.delayed(const Duration(seconds: 10), () {
            if (mounted) {
              final currentError = ref.read(chatProvider).error;
              if (currentError == next) {
                final notifier = ref.read(chatProvider.notifier);
                notifier.state = notifier.state.copyWith(clearError: true);
              }
            }
          });
        }
      })
      // 🔧 修复：将ref.listen移到initState，避免在build中监听
      ..listenManual(
        chatProvider.select((state) => state.lastActionStatus),
        (previous, next) {
          if (next != null && next != previous) {
            final message = ref.read(chatProvider).lastActionMessage;
            if (!mounted) {
              return;
            }
            if (next == 'navigation_ready' &&
                message != null &&
                message.isNotEmpty) {
              final notifier = ref.read(chatProvider.notifier);
              notifier.state =
                  notifier.state.copyWith(clearActionFeedback: true);
              unawaited(_navigateFromAction(message));
              return;
            }
            if (message != null) {
              if (next == 'failed' || next == 'error') {
                AppFeedback.error(context, message);
              } else {
                AppFeedback.success(context, message);
              }
            }
          }
        },
      )
      // 🔧 Phase 2.3: 监听 WebSocket 连接状态变化并显示反馈
      ..listenManual(
        chatProvider.select((state) => state.wsConnectionState),
        (previous, next) {
          if (!mounted) return;

          final l10n = I18nService.instance.l10n;

          if (next == WsConnectionState.reconnecting &&
              previous != WsConnectionState.reconnecting) {
            // 进入重连状态
            AppFeedback.loading(context, l10n.chatReconnecting);
          } else if (next == WsConnectionState.connected &&
              previous == WsConnectionState.reconnecting) {
            // 重连成功
            AppFeedback.success(context, l10n.chatReconnected);

            // 🔧 修复：重连后重新加载历史消息
            final conversationId = ref.read(chatProvider).conversationId;
            if (conversationId != null && conversationId.isNotEmpty) {
              unawaited(
                ref
                    .read(chatProvider.notifier)
                    .loadConversationHistory(conversationId),
              );
            }
          } else if (next == WsConnectionState.failed &&
              previous != WsConnectionState.failed) {
            // 连接失败
            AppFeedback.error(context, l10n.chatConnectionFailed);
          }
        },
      );

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      unawaited(ref.read(chatProvider.notifier).warmUpConnection());
      unawaited(
        ref.read(auroraCoreSessionStateProvider.notifier).refreshFromBackend(),
      );
      final activePlanId = ref.read(activePlanProvider);
      await ref.read(chatProvider.notifier).switchPlanSession(activePlanId);
      if (ref.read(dashboardProvider).nextIntentForecast == null) {
        unawaited(ref.read(dashboardProvider.notifier).refresh());
      }
      await _hydrateInitialConversationAndPrompt();
    });
  }

  void _extractReviewNodeContext() {
    final ctx = widget.initialExtraContext;
    _reviewNodeLabel = null;
    _reviewNodeMastery = null;
    if (ctx == null) return;
    final nodeLabel = ctx['node_label'] as String?;
    if (nodeLabel == null || nodeLabel.isEmpty) return;
    _reviewNodeLabel = nodeLabel;
    final mastery = ctx['mastery'];
    if (mastery is num) {
      _reviewNodeMastery = _normalizeReviewNodeMastery(mastery);
    }
  }

  Map<String, dynamic>? _normalizeInitialExtraContext(
    Map<String, dynamic>? context,
  ) {
    if (context == null || context.isEmpty) {
      return context;
    }
    final normalized = Map<String, dynamic>.from(context);
    final rawCorrection = normalized['aurora_correction'];
    if (rawCorrection is Map) {
      final chatState = ref.read(chatProvider);
      final payload = AuroraCorrectionPayload.fromJson(
        Map<String, dynamic>.from(rawCorrection),
      );
      final conversationId = payload.conversationId.trim().isNotEmpty
          ? payload.conversationId
          : chatState.conversationId ?? '';
      normalized['aurora_correction'] = payload
          .copyWith(
            conversationId: conversationId,
            messageId: payload.messageId.trim().isNotEmpty
                ? payload.messageId
                : _latestAssistantMessageId(),
          )
          .toJson();
    }
    return normalized;
  }

  String _latestAssistantMessageId() {
    for (final message in ref.read(chatProvider).messages.reversed) {
      if (message.role == MessageRole.assistant && message.id.isNotEmpty) {
        return message.id;
      }
    }
    return '';
  }

  double _normalizeReviewNodeMastery(num mastery) {
    final value = mastery.toDouble();
    final normalized = value > 1 ? value / 100 : value;
    return normalized.clamp(0.0, 1.0);
  }

  @override
  void didUpdateWidget(covariant ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialPrompt != widget.initialPrompt ||
        oldWidget.initialChatMode != widget.initialChatMode ||
        oldWidget.initialConversationId != widget.initialConversationId ||
        oldWidget.initialExtraContext != widget.initialExtraContext) {
      _extractReviewNodeContext();
      unawaited(_hydrateInitialConversationAndPrompt());
    }
  }

  Future<void> _hydrateInitialConversationAndPrompt() async {
    if (!mounted) {
      return;
    }
    final sessionId = widget.initialConversationId?.trim();
    if (sessionId != null &&
        sessionId.isNotEmpty &&
        sessionId != _hydratedConversationId &&
        ref.read(chatProvider).conversationId != sessionId) {
      _hydratedConversationId = sessionId;
      await ref.read(chatProvider.notifier).loadConversationHistory(sessionId);
    }
    _queueInitialPromptDispatch();
    _queueInitialUserMessageDispatch();
    _injectWelcomeMessageIfNeeded();
    final hydratedComeback = await _hydrateComebackContextIfNeeded();
    if (hydratedComeback) {
      return;
    }
    final hydratedDailyStartup = await _hydrateDailyStartupIfNeeded(
      showFailure: true,
    );
    if (!hydratedDailyStartup) {
      await _hydrateChatOpeningIfNeeded();
    }
  }

  void _queueInitialUserMessageDispatch() {
    final msg = widget.initialUserMessage?.trim();
    if (msg == null || msg.isEmpty || msg == _dispatchedInitialUserMessage) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final nextMsg = widget.initialUserMessage?.trim();
      if (nextMsg == null ||
          nextMsg.isEmpty ||
          nextMsg == _dispatchedInitialUserMessage) {
        return;
      }
      _dispatchedInitialUserMessage = nextMsg;
      final overrides = <String, dynamic>{
        ...?_normalizeInitialExtraContext(widget.initialExtraContext),
      };
      if (widget.fromModelingComplete) {
        overrides['from_modeling_complete'] = true;
      }
      if (widget.modelingOutput != null) {
        overrides['modeling_output'] = widget.modelingOutput;
      }
      await ref.read(chatProvider.notifier).sendMessage(
            nextMsg,
            extraContextOverrides: overrides.isEmpty ? null : overrides,
          );
    });
  }

  void _injectWelcomeMessageIfNeeded() {
    final msg = widget.initialAiMessage?.trim();
    if (msg == null || msg.isEmpty) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(chatProvider.notifier).prependWelcomeMessage(msg);
    });
  }

  Future<void> _hydrateChatOpeningIfNeeded() async {
    if (!mounted) {
      return;
    }
    if (widget.initialAiMessage?.trim().isNotEmpty ?? false) {
      return;
    }

    final conversationId = ref.read(chatProvider).conversationId?.trim();
    if (conversationId == null ||
        conversationId.isEmpty ||
        conversationId == _hydratedChatOpeningConversationId) {
      return;
    }

    _hydratedChatOpeningConversationId = conversationId;
    try {
      final created = await ref
          .read(userRepositoryProvider)
          .hydrateChatOpening(conversationId);
      if (!mounted || !created) {
        return;
      }
      await ref.read(chatProvider.notifier).loadConversationHistory(
            conversationId,
          );
    } catch (_) {
      _hydratedChatOpeningConversationId = null;
    }
  }

  Future<bool> _hydrateDailyStartupIfNeeded({bool showFailure = false}) async {
    if (!mounted) {
      return false;
    }
    if (widget.initialAiMessage?.trim().isNotEmpty ?? false) {
      return false;
    }
    if (widget.initialPrompt?.trim().isNotEmpty ?? false) {
      return false;
    }
    if (widget.initialUserMessage?.trim().isNotEmpty ?? false) {
      return false;
    }
    if (widget.initialConversationId?.trim().isNotEmpty ?? false) {
      final conversationId = widget.initialConversationId!.trim();
      await _restoreReadPositionForConversation(conversationId);
      return false;
    }
    if (!_canShowAuroraOpenerOver(ref.read(chatProvider).messages)) {
      return false;
    }

    final startupRepository = ref.read(auroraDailyStartupRepositoryProvider);
    final resolution = await _resolveDailyStartupPlan(
      startupRepository: startupRepository,
      showFailure: showFailure,
    );
    if (!mounted || resolution == null || resolution.planId.trim().isEmpty) {
      return false;
    }

    final sprintPlanId = resolution.planId.trim();
    if (resolution.shouldSelectPlan) {
      await ref.read(chatProvider.notifier).switchPlanSession(sprintPlanId);
      if (!mounted ||
          !_canShowAuroraOpenerOver(ref.read(chatProvider).messages)) {
        return false;
      }
      ref.read(activePlanProvider.notifier).selectPlan(sprintPlanId);
    }

    final todayKey = _dateKey(DateTime.now());
    final storageKey = 'aurora_daily_startup:$sprintPlanId:$todayKey';
    if (_hydratedDailyStartupKey == storageKey) {
      return true;
    }

    final prefs = await SharedPreferences.getInstance();
    if (prefs.getBool(storageKey) ?? false) {
      return false;
    }

    final cachedStartup = resolution.cachedStartup;
    if (cachedStartup != null) {
      ref.read(chatProvider.notifier).showDailyStartupMessage(
            cachedStartup,
            planId: sprintPlanId,
            dateKey: todayKey,
          );
      _hydratedDailyStartupKey = storageKey;
      return true;
    }

    try {
      final startup =
          await startupRepository.getDailyStartup(planId: sprintPlanId);
      if (!mounted ||
          startup.message.trim().isEmpty ||
          !_canShowAuroraOpenerOver(ref.read(chatProvider).messages)) {
        return false;
      }
      ref.read(chatProvider.notifier).showDailyStartupMessage(
            startup.message,
            planId: sprintPlanId,
            dateKey: todayKey,
          );
      await prefs.setBool(storageKey, true);
      _hydratedDailyStartupKey = storageKey;
      _hideDailyStartupRetryBanner();
      return true;
    } catch (_) {
      if (showFailure) {
        _showDailyStartupRetryBanner();
      }
      return false;
    }
  }

  Future<_DailyStartupPlanResolution?> _resolveDailyStartupPlan({
    required AuroraDailyStartupRepository startupRepository,
    required bool showFailure,
  }) async {
    final selectedPlanId = ref.read(activePlanProvider)?.trim();
    final dashboard = ref.read(examSprintDashboardProvider).valueOrNull;
    final dashboardPlanId = dashboard?.planId.trim();
    if (dashboardPlanId != null && dashboardPlanId.isNotEmpty) {
      if (selectedPlanId != null &&
          selectedPlanId.isNotEmpty &&
          selectedPlanId != dashboardPlanId) {
        return null;
      }
      return _DailyStartupPlanResolution(
        planId: dashboardPlanId,
        shouldSelectPlan: selectedPlanId == null || selectedPlanId.isEmpty,
      );
    }

    if (selectedPlanId != null && selectedPlanId.isNotEmpty) {
      return _DailyStartupPlanResolution(planId: selectedPlanId);
    }

    final cachedStartup = await startupRepository.getCachedDailyStartup();
    if (cachedStartup != null) {
      return _DailyStartupPlanResolution(
        planId: cachedStartup.planId,
        cachedStartup: cachedStartup.message.message,
        shouldSelectPlan: true,
      );
    }

    try {
      final loadedDashboard =
          await ref.read(examSprintDashboardProvider.future);
      if (!mounted ||
          loadedDashboard == null ||
          loadedDashboard.planId.trim().isEmpty) {
        return null;
      }
      return _DailyStartupPlanResolution(
        planId: loadedDashboard.planId.trim(),
        shouldSelectPlan: true,
      );
    } catch (_) {
      if (showFailure) {
        _showDailyStartupRetryBanner();
      }
      final fallbackStartup = await startupRepository.getCachedDailyStartup();
      if (fallbackStartup == null) {
        return null;
      }
      return _DailyStartupPlanResolution(
        planId: fallbackStartup.planId,
        cachedStartup: fallbackStartup.message.message,
        shouldSelectPlan: true,
      );
    }
  }

  void _showDailyStartupRetryBanner() {
    if (!mounted || _dailyStartupRetryBannerVisible) {
      return;
    }
    setState(() {
      _dailyStartupRetryBannerVisible = true;
    });
  }

  void _hideDailyStartupRetryBanner() {
    if (!mounted ||
        (!_dailyStartupRetryBannerVisible && !_dailyStartupRetryInFlight)) {
      return;
    }
    setState(() {
      _dailyStartupRetryBannerVisible = false;
      _dailyStartupRetryInFlight = false;
    });
  }

  Future<void> _retryDailyStartupHydration() async {
    if (_dailyStartupRetryInFlight) {
      return;
    }
    setState(() {
      _dailyStartupRetryInFlight = true;
    });
    final hydrated = await _hydrateDailyStartupIfNeeded(showFailure: true);
    if (mounted && !hydrated) {
      setState(() {
        _dailyStartupRetryInFlight = false;
        _dailyStartupRetryBannerVisible = true;
      });
    }
    if (!hydrated && mounted) {
      await _hydrateChatOpeningIfNeeded();
    }
  }

  Future<bool> _hydrateComebackContextIfNeeded() async {
    if (!mounted) {
      return false;
    }
    if (widget.initialAiMessage?.trim().isNotEmpty ?? false) {
      return false;
    }
    if (widget.initialPrompt?.trim().isNotEmpty ?? false) {
      return false;
    }
    if (widget.initialUserMessage?.trim().isNotEmpty ?? false) {
      return false;
    }

    AuroraComebackContext comeback;
    try {
      comeback = await ref
          .read(auroraDailyStartupRepositoryProvider)
          .getComebackContext()
          .timeout(const Duration(seconds: 5));
    } catch (_) {
      return false;
    }
    if (!mounted || !comeback.hasContent) {
      return false;
    }

    final signature = '${comeback.comebackKind}:${comeback.conversationId}:'
        '${comeback.lastActiveAt}:${comeback.planId}:${comeback.resumeToken}';
    if (_hydratedComebackSignature == signature) {
      return true;
    }

    final selectedPlanId = ref.read(activePlanProvider)?.trim();
    final comebackPlanId = comeback.planId.trim();
    final comebackConversationId = comeback.conversationId.trim();

    if (comebackConversationId.isNotEmpty &&
        comebackConversationId !=
            (ref.read(chatProvider).conversationId ?? '').trim()) {
      await ref
          .read(chatProvider.notifier)
          .loadConversationHistory(comebackConversationId);
      if (!mounted) {
        return false;
      }
      await _restoreReadPositionForConversation(comebackConversationId);
    } else if (comebackConversationId.isNotEmpty) {
      await _restoreReadPositionForConversation(comebackConversationId);
    } else if ((selectedPlanId == null || selectedPlanId.isEmpty) &&
        comebackPlanId.isNotEmpty) {
      await ref.read(chatProvider.notifier).switchPlanSession(comebackPlanId);
      if (!mounted) {
        return false;
      }
      final conversationId = ref.read(chatProvider).conversationId;
      if (conversationId != null && conversationId.isNotEmpty) {
        await _restoreReadPositionForConversation(conversationId);
      }
    }

    if ((selectedPlanId == null || selectedPlanId.isEmpty) &&
        comebackPlanId.isNotEmpty) {
      ref.read(activePlanProvider.notifier).selectPlan(comebackPlanId);
    }

    if (comeback.shouldShowBanner) {
      setState(() {
        _comebackContext = comeback;
        _showComebackBanner = true;
      });
    } else if (_showComebackBanner) {
      setState(() {
        _showComebackBanner = false;
      });
    }

    _hydratedComebackSignature = signature;
    return true;
  }

  Future<void> _restoreReadPositionForConversation(
      String conversationId) async {
    final normalizedConversationId = conversationId.trim();
    if (normalizedConversationId.isEmpty) {
      return;
    }
    final messages = ref.read(chatProvider).messages;
    _pruneMessageKeys(messages);
    final prefs = await SharedPreferences.getInstance();
    final storedLastReadId =
        prefs.getString(_lastReadMessagePrefsKey(normalizedConversationId));
    String? firstUnreadId;
    if (storedLastReadId != null &&
        storedLastReadId.isNotEmpty &&
        messages.isNotEmpty) {
      final storedIndex =
          messages.indexWhere((message) => message.id == storedLastReadId);
      if (storedIndex >= 0 && storedIndex < messages.length - 1) {
        firstUnreadId = messages[storedIndex + 1].id;
      } else if (storedIndex < 0) {
        firstUnreadId = messages.first.id;
      }
    }
    if (mounted) {
      setState(() {
        _newMessageDividerBeforeId = firstUnreadId;
      });
    }
    final targetId =
        firstUnreadId ?? (messages.isNotEmpty ? messages.last.id : null);
    if (targetId == null) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final targetContext = _messageKeys[targetId]?.currentContext;
      if (targetContext == null) {
        _scrollToBottom();
        return;
      }
      Scrollable.ensureVisible(
        targetContext,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
        alignment: 0.22,
      );
    });
  }

  void _pruneMessageKeys(List<ChatMessageModel> messages) {
    final ids = messages.map((message) => message.id).toSet();
    _messageKeys.removeWhere((id, _) => !ids.contains(id));
  }

  GlobalKey _messageKeyFor(String id) =>
      _messageKeys.putIfAbsent(id, () => GlobalKey());

  String _lastReadMessagePrefsKey(String conversationId) =>
      'chat:last_read_message_id:$conversationId';

  Future<void> _writeLatestReadPosition(
    String conversationId,
    String latestId,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastReadMessagePrefsKey(conversationId), latestId);
  }

  void _rememberLatestReadPosition(ChatState chatState) {
    final conversationId = chatState.conversationId?.trim();
    final latestId =
        chatState.messages.isNotEmpty ? chatState.messages.last.id.trim() : '';
    if (conversationId == null || conversationId.isEmpty || latestId.isEmpty) {
      return;
    }
    _latestReadConversationId = conversationId;
    _latestReadMessageId = latestId;
  }

  void _dismissComebackBanner() {
    if (!_showComebackBanner) {
      return;
    }
    setState(() {
      _showComebackBanner = false;
    });
  }

  void _continueFromComebackBanner() {
    _dismissComebackBanner();
    _scrollToBottom();
  }

  Future<void> _resumeComebackCoreSession() async {
    final comeback = _comebackContext;
    final resumeToken = comeback?.resumeToken.trim() ?? '';
    if (resumeToken.isEmpty || !mounted) {
      return;
    }
    _dismissComebackBanner();
    await showAuroraCoreSession(
      context: context,
      bandStatus: 'calibration_available',
      wakeReasons: const ['cross_session_resume'],
      conversationId: ref.read(chatProvider).conversationId,
      resumeToken: resumeToken,
      sessionType: 'resume',
      initialSize: AuroraCoreSessionSheetSize.expanded,
    );
  }

  void _handleComebackItemSelected(AuroraComebackItem item) {
    if (item.type == 'core_session' || item.resumeToken.isNotEmpty) {
      unawaited(_resumeComebackCoreSession());
      return;
    }
    if (item.route.isNotEmpty) {
      _dismissComebackBanner();
      unawaited(_navigateFromAction(item.route));
      return;
    }
    _continueFromComebackBanner();
  }

  Future<void> _submitFreeformAuroraCorrection(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      return;
    }
    final snapshot = ref.read(auroraStatusProvider);
    final chatState = ref.read(chatProvider);
    final telemetry = AuroraTelemetryService(ref.read(apiClientProvider));
    unawaited(
      telemetry.recordStatusBandCorrection(
        label: trimmed,
        semanticValue: 'freeform_correction',
        isDisconfirming: true,
        bandStatus: snapshot?.overallStatus ?? 'needs_confirm',
        isFreeform: true,
        freeformText: trimmed,
        conversationId: chatState.conversationId,
      ),
    );
    ref.read(auroraStatusProvider.notifier).markCorrectionEffective(
          semanticValue: 'freeform_correction',
          action: 'freeform_correction',
        );
    final payload = AuroraCorrectionPayload.freeform(
      surface: AuroraCorrectionSurface.chat,
      semanticValue: 'freeform_correction',
      label: trimmed,
      freeformText: trimmed,
      isDisconfirming: true,
      bandStatus: snapshot?.overallStatus ?? 'needs_confirm',
      conversationId: chatState.conversationId ?? '',
      messageId: _latestAssistantMessageId(),
    );
    unawaited(
      ref.read(chatProvider.notifier).sendMessage(
        trimmed,
        extraContextOverrides: {
          'aurora_correction': payload.toJson(),
        },
      ),
    );
    unawaited(
      ref.read(auroraStatusProvider.notifier).refresh(
            conversationId: chatState.conversationId,
          ),
    );
  }

  Future<String?> _promptForAuroraCorrection(BuildContext context) {
    final controller = TextEditingController();
    final focusNode = FocusNode();
    return showDialog<String?>(
      context: context,
      builder: (dialogContext) {
        String? submittedText() {
          final text = controller.text.trim();
          return text.isEmpty ? null : text;
        }

        return AlertDialog(
          title: Text(context.l10n.auroraCorrectionInputTitle),
          content: TextField(
            controller: controller,
            focusNode: focusNode,
            autofocus: true,
            maxLines: 3,
            minLines: 2,
            decoration: InputDecoration(
              hintText: context.l10n.auroraCorrectionInputHint,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.radius12),
              ),
              contentPadding: const EdgeInsets.all(DS.spacing12),
            ),
            textInputAction: TextInputAction.send,
            onSubmitted: (_) {
              final text = submittedText();
              if (text != null) {
                Navigator.of(dialogContext).pop(text);
              }
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(null),
              child: Text(context.l10n.auroraCorrectionInputCancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(submittedText()),
              child: Text(context.l10n.auroraCorrectionInputSend),
            ),
          ],
        );
      },
    ).whenComplete(() {
      focusNode.dispose();
      controller.dispose();
    });
  }

  bool _canShowAuroraOpenerOver(List<ChatMessageModel> messages) {
    if (messages.any((message) => message.role == MessageRole.user)) {
      return false;
    }
    return messages.every(
      (message) =>
          message.id.startsWith('comeback_') ||
          message.id.startsWith('daily_startup_') ||
          message.id.startsWith('welcome_'),
    );
  }

  String _dateKey(DateTime date) => '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  void _queueInitialPromptDispatch() {
    final prompt = widget.initialPrompt?.trim();
    if (prompt == null ||
        prompt.isEmpty ||
        prompt == _dispatchedInitialPrompt) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final nextPrompt = widget.initialPrompt?.trim();
      if (nextPrompt == null ||
          nextPrompt.isEmpty ||
          nextPrompt == _dispatchedInitialPrompt) {
        return;
      }
      _dispatchedInitialPrompt = nextPrompt;
      final initialMode = widget.initialChatMode?.trim();
      if (initialMode != null && initialMode.isNotEmpty) {
        ref.read(chatModeProvider.notifier).setFromApiValue(initialMode);
      }
      await ref.read(chatProvider.notifier).sendMessage(
            nextPrompt,
            extraContextOverrides:
                _normalizeInitialExtraContext(widget.initialExtraContext),
          );
    });
  }

  @override
  void dispose() {
    final conversationId = _latestReadConversationId;
    final latestId = _latestReadMessageId;
    if (conversationId != null && latestId != null) {
      unawaited(_writeLatestReadPosition(conversationId, latestId));
    }
    _scrollController
      ..removeListener(_handleScroll)
      ..dispose();
    unawaited(BgmService.setReadingActivity(false));
    unawaited(BgmService.setThinkingActivity(false));
    super.dispose();
  }

  void _handleScroll() {
    if (!_scrollController.hasClients) {
      return;
    }
    final position = _scrollController.position;
    if (position.maxScrollExtent <= 0) {
      return;
    }
    if (position.userScrollDirection == ScrollDirection.idle) {
      return;
    }
    if (position.pixels >= position.maxScrollExtent - 240) {
      unawaited(ref.read(chatProvider.notifier).loadMoreHistory());
    }
  }

  Map<String, ChatBubbleDeliveryStatus> _offlineDeliveryStatusesByMessageId(
    List<ChatMessageModel> messages,
    List<OfflineQueueEntry> queueEntries,
  ) {
    if (queueEntries.isEmpty) {
      return const <String, ChatBubbleDeliveryStatus>{};
    }

    final statuses = <String, ChatBubbleDeliveryStatus>{};
    final unmatchedEntries = List<OfflineQueueEntry>.from(queueEntries);
    for (final message in messages) {
      if (message.role != MessageRole.user) {
        continue;
      }
      final requestId =
          message.rawMetadata?['offline_request_id']?.toString() ?? message.id;
      final exactIndex = unmatchedEntries.indexWhere(
        (entry) => entry.requestId == requestId,
      );
      var matchIndex = exactIndex;
      if (matchIndex < 0) {
        matchIndex = unmatchedEntries.indexWhere(
          (entry) =>
              entry.message == message.content &&
              (entry.sessionId == message.conversationId ||
                  entry.sessionId.isEmpty ||
                  message.conversationId == 'temp_conversation') &&
              entry.createdAt
                      .difference(message.createdAt)
                      .inMilliseconds
                      .abs() <
                  const Duration(minutes: 10).inMilliseconds,
        );
      }
      if (matchIndex < 0) {
        continue;
      }
      final entry = unmatchedEntries.removeAt(matchIndex);
      statuses[message.id] = _chatDeliveryStatusFor(entry.status);
    }
    return statuses;
  }

  ChatBubbleDeliveryStatus _chatDeliveryStatusFor(
    OfflineMessageStatus status,
  ) {
    switch (status) {
      case OfflineMessageStatus.pending:
        return ChatBubbleDeliveryStatus.queued;
      case OfflineMessageStatus.sent:
        return ChatBubbleDeliveryStatus.sending;
      case OfflineMessageStatus.failed:
        return ChatBubbleDeliveryStatus.failed;
      case OfflineMessageStatus.acked:
        return ChatBubbleDeliveryStatus.normal;
    }
  }

  @override
  Widget build(BuildContext context) {
    const experience = ExperienceProfiles.assistantFlow;
    final chatState = ref.watch(chatProvider);
    _rememberLatestReadPosition(chatState);
    final aiSystemPreferences =
        ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
            _defaultAiSystemPreferences;
    final messages = chatState.messages;
    final chatPureMode = ref.watch(chatPureModeProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider) && !chatPureMode;
    final showStatusIndicator =
        chatState.shouldShowStatusIndicator && !chatPureMode;
    final showReasoningIndicator =
        chatState.shouldShowReasoningIndicator && !chatPureMode;
    final openClawConnection = ref.watch(openClawConnectionProvider);
    final showOpenClawAttention = openClawConnection.queuedRequestCount > 0 ||
        (openClawConnection.config.isConfigured &&
            !openClawConnection.isConnected);
    final showStreamingBubble = chatState.shouldShowStreamingBubble;
    final offlineUserId =
        ref.watch(offlineQueueCurrentUserIdProvider).valueOrNull;
    final offlineSnapshot = offlineUserId == null
        ? OfflineQueueSnapshot.empty
        : ref.watch(offlineQueueSnapshotProvider(offlineUserId)).valueOrNull ??
            OfflineQueueSnapshot.empty;
    final offlineStatuses = _offlineDeliveryStatusesByMessageId(
      messages,
      offlineSnapshot.entries,
    );
    final listItemCount = messages.length +
        (showStreamingBubble ? 1 : 0) +
        (showStatusIndicator ? 1 : 0) +
        (showReasoningIndicator ? 1 : 0);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final l10n = context.l10n;
    String? latestAssistantMessageId;
    for (final message in messages.reversed) {
      if (message.role == MessageRole.assistant) {
        latestAssistantMessageId = message.id;
        break;
      }
    }

    return GraphiteScaffold(
      role: experience.pageRole,
      motionToken: experience.motionToken,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        flexibleSpace: ClipRect(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
            child: Container(
              decoration: BoxDecoration(
                color: DS.surfaceOverlay.withValues(alpha: isDark ? 0.9 : 0.96),
                border: Border(
                  bottom: BorderSide(
                    color: DS.borderSubtle,
                    width: 0.6,
                  ),
                ),
              ),
            ),
          ),
        ),
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        elevation: 0,
        leading: SparkleIconButton(
          icon: Icon(Icons.arrow_back_rounded, color: DS.textSecondary),
          onPressed: () => _handleExitChat(context),
          semanticLabel: l10n.back,
          variant: ButtonVariant.ghost,
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.surfacePanel,
                shape: BoxShape.circle,
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Icon(
                Icons.auto_awesome,
                color: DS.brandPrimaryConst,
                size: 20,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    l10n.chatTitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                      fontSize: DS.fontSizeBase,
                    ),
                  ),
                  Text(
                    l10n.chatSubtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          SparkleIconButton(
            icon: _OpenClawAppBarIcon(
              highlighted: showOpenClawAttention,
              queueCount: openClawConnection.queuedRequestCount,
            ),
            onPressed: () =>
                context.push('${HomeRoutes.openClawHub}?section=delegate'),
            semanticLabel: showOpenClawAttention
                ? context.l10n.chatOpenclawHubQueued(
                    openClawConnection.queuedRequestCount)
                : 'OpenClaw Hub',
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Icon(Icons.tune_rounded, color: DS.textSecondary),
            onPressed: () => _openChatSettings(context),
            semanticLabel: l10n.settings,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Icon(Icons.history, color: DS.textSecondary),
            onPressed: () => _showHistoryBottomSheet(context),
            semanticLabel: l10n.chatHistoryTitle,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Badge(
              isLabelVisible: chatState.causalTraceCount > 0,
              label: Text('${chatState.causalTraceCount}'),
              child: Icon(Icons.timeline, color: DS.textSecondary),
            ),
            onPressed: () => _showCausalTimelineSheet(context),
            semanticLabel: context.l10n.chatDecisionTimeline,
            variant: ButtonVariant.ghost,
          ),
          PopupMenuButton<_ChatShortcutAction>(
            tooltip: context.l10n.chatMoreActions,
            color: DS.surfacePrimary,
            surfaceTintColor: DS.surfacePrimary,
            icon: Icon(Icons.more_horiz_rounded, color: DS.textSecondary),
            onSelected: (value) {
              if (value == _ChatShortcutAction.newSession) {
                ref.read(chatProvider.notifier).startNewSession();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem<_ChatShortcutAction>(
                value: _ChatShortcutAction.newSession,
                child: Row(
                  children: [
                    Icon(Icons.add_comment_outlined, size: 18),
                    SizedBox(width: DS.spacing12),
                    Text(context.l10n.chatNewConversation),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.surfacePrimary,
              Color.lerp(DS.surfacePrimary, DS.surfaceCanvas, 0.5)!,
              DS.surfaceCanvas,
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Stack(
          children: [
            if (!chatPureMode && _shouldShowReasoningAtmosphere(chatState))
              const Positioned.fill(
                child: IgnorePointer(
                  child: _ReasoningBreathOverlay(),
                ),
              ),
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0.8, -0.55),
                      radius: 1.08,
                      colors: [
                        DS.info.withValues(alpha: 0.08),
                        DS.brandPrimary.withValues(alpha: 0.035),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.4, 1.0],
                    ),
                  ),
                ),
              ),
            ),
            SafeArea(
              bottom: false, // Handle bottom padding manually to avoid double padding with ChatInput
              child: ContentConstraint(
                child: Column(
                  children: [
                    if (chatState.isLoading)
                      LinearProgressIndicator(
                        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
                        valueColor:
                            AlwaysStoppedAnimation<Color>(DS.primaryBase),
                        minHeight: 2,
                      ),
                    ChatWorkingMemoryPanel(
                      sessionId: chatState.conversationId,
                      onViewSource: _showWorkingMemorySource,
                    ),
                    StatusAwarenessBar(
                      conversationId: chatState.conversationId,
                      hasActiveRun: chatState.hasActiveRun,
                    ),
                    if (!chatPureMode) const ChatUnderstandingDrawerButton(),
                    AuroraCoreSessionResumeBanner(
                      conversationId: chatState.conversationId,
                    ),
                    if (chatState.dualCoreMode != null)
                      _DualCoreModeChip(mode: chatState.dualCoreMode!),
                    if (_reviewNodeLabel != null)
                      _ReviewNodeBanner(
                        nodeLabel: _reviewNodeLabel!,
                        mastery: _reviewNodeMastery,
                      ),
                    if (_dailyStartupRetryBannerVisible)
                      DailyStartupRetryBanner(
                        isRetrying: _dailyStartupRetryInFlight,
                        onRetry: _retryDailyStartupHydration,
                      ),
                    if (_showComebackBanner && _comebackContext != null)
                      ComebackBanner(
                        contextData: _comebackContext!,
                        onDismiss: _dismissComebackBanner,
                        onContinue: _continueFromComebackBanner,
                        onResumeCoreSession:
                            _comebackContext!.hasActiveCoreSession
                                ? () => unawaited(_resumeComebackCoreSession())
                                : null,
                        onItemSelected: _handleComebackItemSelected,
                      ),
                    Expanded(
                      child: messages.isEmpty &&
                              chatState.streamingContent.isEmpty &&
                              !showStatusIndicator &&
                              !showReasoningIndicator
                          ? _buildQuickActions(context)
                          : ListView.builder(
                              controller: _scrollController,
                              reverse: true,
                              padding: EdgeInsets.only(
                                left: DS.spacing16,
                                right: DS.spacing16,
                                top: DS.spacing16,
                                bottom: _calculateBottomPadding(
                                  context,
                                  chatState,
                                  aiSystemPreferences,
                                  showChatTransparencyCapsule,
                                  showStatusIndicator,
                                ),
                              ),
                              cacheExtent: 600,
                              itemCount: listItemCount,
                              itemBuilder: (context, index) {
                                final isStatusShowing = showStatusIndicator;
                                final isReasoningShowing =
                                    showReasoningIndicator;
                                final isSendingShowing = showStreamingBubble;

                                if (isStatusShowing && index == 0) {
                                  return Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: DS.spacing12,
                                    ),
                                    child: AiStatusIndicator(
                                      status: chatState.aiStatus,
                                      details: chatState.aiStatusDetails,
                                      startedAtEpochMs: chatState
                                          .activeRunSummary?.startedAtEpochMs,
                                      enableStatusTrack: false,
                                    ),
                                  );
                                }

                                final reasoningIndex = isStatusShowing ? 1 : 0;
                                if (isReasoningShowing &&
                                    index == reasoningIndex) {
                                  final durationMs =
                                      chatState.reasoningStartTime != null
                                          ? DateTime.now()
                                                  .millisecondsSinceEpoch -
                                              chatState.reasoningStartTime!
                                          : null;

                                  return Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: DS.spacing12,
                                    ),
                                    child: AgentReasoningBubble(
                                      steps: chatState.reasoningSteps,
                                      isThinking: true,
                                      totalDurationMs: durationMs,
                                    ),
                                  );
                                }

                                var streamIndex = 0;
                                if (isStatusShowing) streamIndex++;
                                if (isReasoningShowing) streamIndex++;

                                if (isSendingShowing && index == streamIndex) {
                                  if (chatState.streamingContent.isNotEmpty) {
                                    return Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: DS.spacing12,
                                      ),
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          if (chatState.routingPreview !=
                                                  null ||
                                              chatState
                                                  .roundtableTurns.isNotEmpty)
                                            Padding(
                                              padding: const EdgeInsets.only(
                                                bottom: DS.spacing12,
                                              ),
                                              child: chatPureMode
                                                  ? const SizedBox.shrink()
                                                  : ExpertRoundtableWidget(
                                                      routingPreview: chatState
                                                          .routingPreview,
                                                      turns: chatState
                                                          .roundtableTurns,
                                                      collapseId:
                                                          'stream:${chatState.activeRunId ?? chatState.reasoningStartTime ?? 'preview'}',
                                                    ),
                                            ),
                                          _StreamingBubble(
                                            content: chatState.streamingContent,
                                          ),
                                          if (!chatPureMode)
                                            AgentWorkflowPanel(
                                              liveActivities:
                                                  chatState.agentActivities,
                                            ),
                                        ],
                                      ),
                                    );
                                  }

                                  if (!isStatusShowing && !isReasoningShowing) {
                                    return const Padding(
                                      padding:
                                          EdgeInsets.only(bottom: DS.spacing12),
                                      child: _TypingIndicator(),
                                    );
                                  }

                                  return const SizedBox.shrink();
                                }

                                var msgIndex = index;
                                if (isStatusShowing) msgIndex--;
                                if (isReasoningShowing) msgIndex--;
                                if (isSendingShowing) msgIndex--;

                                if (msgIndex < 0) {
                                  return const SizedBox.shrink();
                                }

                                final messageCount = messages.length;
                                final adjustedIndex =
                                    messageCount - 1 - msgIndex;

                                if (adjustedIndex < 0 ||
                                    adjustedIndex >= messageCount) {
                                  return const SizedBox.shrink();
                                }

                                final message = messages[adjustedIndex];
                                final isLatestAssistant =
                                    message.id == latestAssistantMessageId;
                                final showCorrectionBar = isLatestAssistant &&
                                    message.role == MessageRole.assistant &&
                                    !chatState.hasActiveRun;
                                final showEnvelopeIndicator =
                                    isLatestAssistant &&
                                        message.role == MessageRole.assistant;
                                final showNewMessagesDivider =
                                    message.id == _newMessageDividerBeforeId;
                                return Column(
                                  key: _messageKeyFor(message.id),
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    if (showNewMessagesDivider)
                                      const ChatNewMessagesDivider(),
                                    ChatBubble(
                                      message: message,
                                      isLatestAssistantMessage:
                                          isLatestAssistant,
                                      deliveryStatus:
                                          offlineStatuses[message.id] ??
                                              ChatBubbleDeliveryStatus.normal,
                                      onRetryDelivery:
                                          message.role == MessageRole.user
                                              ? () => ref
                                                  .read(chatProvider.notifier)
                                                  .sendMessage(message.content)
                                              : null,
                                      onActionConfirm: (action) {
                                        ref
                                            .read(chatProvider.notifier)
                                            .confirmAction(action);
                                      },
                                      onActionDismiss: (action) {
                                        ref
                                            .read(chatProvider.notifier)
                                            .dismissAction(action);
                                      },
                                      onResponseFeedback: (msg, feedbackType) {
                                        ref
                                            .read(chatProvider.notifier)
                                            .sendResponseFeedback(
                                              msg,
                                              feedbackType,
                                            );
                                      },
                                      onCitationFeedback:
                                          (msg, citation, helpful) async {
                                        ref
                                            .read(chatProvider.notifier)
                                            .sendCitationFeedback(
                                              message: msg,
                                              citation: citation,
                                              helpful: helpful,
                                            );
                                      },
                                      onWidgetAction: (
                                        actionType,
                                        payload,
                                      ) async {
                                        await ref
                                            .read(chatProvider.notifier)
                                            .handleWidgetAction(
                                              actionType,
                                              payload,
                                            );
                                      },
                                    ),
                                    if (showCorrectionBar)
                                      Builder(
                                        builder: (ctx) {
                                          final auroraStatus = ref.watch(
                                            auroraStatusProvider,
                                          );
                                          final l10n = ctx.l10n;
                                          return ContextualCorrectionBar(
                                            predictedReplyGroups: auroraStatus
                                                ?.predictedReplyOptions,
                                            bandStatus:
                                                auroraStatus?.overallStatus ??
                                                    '',
                                            conversationId:
                                                chatState.conversationId,
                                            messageId: message.id,
                                            onSendCorrection:
                                                (option, groupId) {
                                              final presentation =
                                                  auroraCorrectionPresentationFor(
                                                ctx,
                                                option,
                                              );
                                              final telemetry =
                                                  AuroraTelemetryService(
                                                ref.read(apiClientProvider),
                                              );
                                              unawaited(
                                                telemetry.recordChipSelected(
                                                  option: option,
                                                  groupId: groupId,
                                                  bandStatus: auroraStatus
                                                          ?.overallStatus ??
                                                      '',
                                                  conversationId: ref
                                                      .read(chatProvider)
                                                      .conversationId,
                                                ),
                                              );
                                              ref
                                                  .read(auroraStatusProvider
                                                      .notifier)
                                                  .markCorrectionEffective(
                                                    semanticValue:
                                                        option.semanticValue,
                                                  );
                                              final text = presentation.label;
                                              final chatState =
                                                  ref.read(chatProvider);
                                              final payload =
                                                  AuroraCorrectionPayload.chip(
                                                surface: AuroraCorrectionSurface
                                                    .chat,
                                                semanticValue:
                                                    option.semanticValue,
                                                label: text,
                                                isDisconfirming:
                                                    option.isDisconfirming,
                                                bandStatus: auroraStatus
                                                        ?.overallStatus ??
                                                    '',
                                                telemetryId: option.telemetryId,
                                                groupId: groupId,
                                                conversationId:
                                                    chatState.conversationId ??
                                                        '',
                                                messageId:
                                                    _latestAssistantMessageId(),
                                              );
                                              unawaited(
                                                ref
                                                    .read(chatProvider.notifier)
                                                    .sendMessage(
                                                  text,
                                                  extraContextOverrides: {
                                                    'aurora_correction':
                                                        payload.toJson(),
                                                  },
                                                ),
                                              );
                                            },
                                            onFreeformCorrectionRequested: () {
                                              unawaited(
                                                _promptForAuroraCorrection(ctx)
                                                    .then((value) {
                                                  final text =
                                                      value?.trim() ?? '';
                                                  if (text.isNotEmpty) {
                                                    unawaited(
                                                      _submitFreeformAuroraCorrection(
                                                        text,
                                                      ),
                                                    );
                                                  }
                                                }),
                                              );
                                            },
                                            onNotRightDirection: () {
                                              final telemetry =
                                                  AuroraTelemetryService(
                                                ref.read(apiClientProvider),
                                              );
                                              unawaited(
                                                telemetry
                                                    .recordStatusBandCorrection(
                                                  label: l10n
                                                      .auroraCorrectNotRight,
                                                  semanticValue:
                                                      'not_right_direction',
                                                  isDisconfirming: true,
                                                  bandStatus: auroraStatus
                                                          ?.overallStatus ??
                                                      '',
                                                  conversationId: ref
                                                      .read(chatProvider)
                                                      .conversationId,
                                                ),
                                              );
                                              unawaited(
                                                ref
                                                    .read(chatProvider.notifier)
                                                    .sendMessage(
                                                  l10n.auroraCorrectNotRight,
                                                  extraContextOverrides: {
                                                    'aurora_correction':
                                                        AuroraCorrectionPayload
                                                            .chip(
                                                      surface:
                                                          AuroraCorrectionSurface
                                                              .chat,
                                                      semanticValue:
                                                          'not_right_direction',
                                                      label: l10n
                                                          .auroraCorrectNotRight,
                                                      isDisconfirming: true,
                                                      bandStatus: auroraStatus
                                                              ?.overallStatus ??
                                                          '',
                                                      conversationId: ref
                                                              .read(
                                                                  chatProvider)
                                                              .conversationId ??
                                                          '',
                                                      messageId:
                                                          _latestAssistantMessageId(),
                                                    ).toJson(),
                                                  },
                                                ),
                                              );
                                              ref
                                                  .read(auroraStatusProvider
                                                      .notifier)
                                                  .markCorrectionEffective(
                                                    semanticValue:
                                                        'not_right_direction',
                                                  );
                                            },
                                            onMakeShorter: () {
                                              final telemetry =
                                                  AuroraTelemetryService(
                                                ref.read(apiClientProvider),
                                              );
                                              unawaited(
                                                telemetry
                                                    .recordStatusBandCorrection(
                                                  label:
                                                      l10n.auroraCorrectShorter,
                                                  semanticValue: 'make_shorter',
                                                  isDisconfirming: false,
                                                  bandStatus: auroraStatus
                                                          ?.overallStatus ??
                                                      '',
                                                  conversationId: ref
                                                      .read(chatProvider)
                                                      .conversationId,
                                                ),
                                              );
                                              unawaited(
                                                ref
                                                    .read(chatProvider.notifier)
                                                    .sendMessage(
                                                  l10n.auroraCorrectShorter,
                                                  extraContextOverrides: {
                                                    'aurora_correction':
                                                        AuroraCorrectionPayload
                                                            .chip(
                                                      surface:
                                                          AuroraCorrectionSurface
                                                              .chat,
                                                      semanticValue:
                                                          'make_shorter',
                                                      label: l10n
                                                          .auroraCorrectShorter,
                                                      isDisconfirming: false,
                                                      bandStatus: auroraStatus
                                                              ?.overallStatus ??
                                                          '',
                                                      conversationId: ref
                                                              .read(
                                                                  chatProvider)
                                                              .conversationId ??
                                                          '',
                                                      messageId:
                                                          _latestAssistantMessageId(),
                                                    ).toJson(),
                                                  },
                                                ),
                                              );
                                            },
                                            onGivePractice: () {
                                              final telemetry =
                                                  AuroraTelemetryService(
                                                ref.read(apiClientProvider),
                                              );
                                              unawaited(
                                                telemetry
                                                    .recordStatusBandCorrection(
                                                  label:
                                                      l10n.auroraCorrectDirect,
                                                  semanticValue:
                                                      'give_practice',
                                                  isDisconfirming: false,
                                                  bandStatus: auroraStatus
                                                          ?.overallStatus ??
                                                      '',
                                                  conversationId: ref
                                                      .read(chatProvider)
                                                      .conversationId,
                                                ),
                                              );
                                              unawaited(
                                                ref
                                                    .read(chatProvider.notifier)
                                                    .sendMessage(
                                                  l10n.auroraCorrectDirect,
                                                  extraContextOverrides: {
                                                    'aurora_correction':
                                                        AuroraCorrectionPayload
                                                            .chip(
                                                      surface:
                                                          AuroraCorrectionSurface
                                                              .chat,
                                                      semanticValue:
                                                          'give_practice',
                                                      label: l10n
                                                          .auroraCorrectDirect,
                                                      isDisconfirming: false,
                                                      bandStatus: auroraStatus
                                                              ?.overallStatus ??
                                                          '',
                                                      conversationId: ref
                                                              .read(
                                                                  chatProvider)
                                                              .conversationId ??
                                                          '',
                                                      messageId:
                                                          _latestAssistantMessageId(),
                                                    ).toJson(),
                                                  },
                                                ),
                                              );
                                            },
                                            onRecalibrate: () {
                                              final snapshot = ref.read(
                                                auroraStatusProvider,
                                              );
                                              unawaited(
                                                showAuroraCoreSession(
                                                  context: context,
                                                  bandStatus:
                                                      snapshot?.overallStatus ??
                                                          'needs_confirm',
                                                  wakeReasons: snapshot
                                                          ?.wakeEligibility
                                                          .wakeReasons ??
                                                      const [
                                                        'standard_layer_uncertainty'
                                                      ],
                                                  entryReason: snapshot == null
                                                      ? AuroraCoreSessionEntryReason(
                                                          triggerSource:
                                                              'chat_correction_chip',
                                                          observedSignals: [
                                                            context.l10n
                                                                .auroraCalibrationObserved,
                                                          ],
                                                          suggestedAgendaPreview: [
                                                            context.l10n
                                                                .chatAgendaConfirmCorrectionFeedback,
                                                            context.l10n
                                                                .chatAgendaAdjustReplyStrategy,
                                                          ],
                                                          whyNow: context.l10n
                                                              .auroraCalibrationJudgment,
                                                          estimatedMinutes: 4,
                                                        )
                                                      : AuroraCoreSessionEntryReason
                                                          .fromSnapshot(
                                                          snapshot: snapshot,
                                                          triggerSource:
                                                              'chat_correction_chip',
                                                          agendaPreview: [
                                                            context.l10n
                                                                .chatAgendaConfirmCorrectionFeedback,
                                                            context.l10n
                                                                .chatAgendaAdjustReplyStrategy,
                                                          ],
                                                        ),
                                                  conversationId: ref
                                                      .read(chatProvider)
                                                      .conversationId,
                                                  scope: snapshot
                                                              ?.wakeEligibility
                                                              .suggestedScope
                                                              .isNotEmpty ??
                                                          false
                                                      ? snapshot!
                                                          .wakeEligibility
                                                          .suggestedScope
                                                      : null,
                                                  sessionType:
                                                      'belief_revision',
                                                ),
                                              );
                                            },
                                          );
                                        },
                                      ),
                                    if (showEnvelopeIndicator)
                                      const ExperienceEnvelopeIndicator(),
                                  ],
                                );
                              },
                            ),
                    ),
                    SparkleExitTransition(
                      visible: chatState.error != null,
                      maintainSize: false,
                      child: Container(
                        width: double.infinity,
                        margin: const EdgeInsets.fromLTRB(
                          DS.spacing16,
                          0,
                          DS.spacing16,
                          DS.spacing8,
                        ),
                        padding: const EdgeInsets.all(DS.sm),
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              DS.error.withValues(alpha: 0.1),
                              DS.surfacePrimary,
                            ],
                          ),
                          borderRadius: DS.borderRadius16,
                          border: Border.all(
                            color: DS.error.withValues(alpha: 0.18),
                          ),
                        ),
                        child: chatState.error == null
                            ? const SizedBox.shrink()
                            : Builder(
                                builder: (context) {
                                  final failureKind = FailureKindCode.fromCode(
                                    chatState.errorCode,
                                  );
                                  return Row(
                                    children: [
                                      Icon(
                                        _chatFailureIcon(chatState.errorCode),
                                        size: 20,
                                        color: DS.error,
                                      ),
                                      const SizedBox(width: DS.spacing8),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Text(
                                              _chatFailureTitle(
                                                context,
                                                chatState.errorCode,
                                              ),
                                              style: TextStyle(
                                                color: DS.error,
                                                fontSize: DS.fontSizeSm,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              chatState.error!,
                                              style: TextStyle(
                                                color: DS.error,
                                                fontSize: DS.fontSizeSm,
                                              ),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ],
                                        ),
                                      ),
                                      if (chatState.isErrorRetryable ||
                                          failureKind == FailureKind.auth)
                                        Padding(
                                          padding: const EdgeInsets.only(
                                            left: DS.spacing8,
                                          ),
                                          child: SparkleButton(
                                            label: _chatFailureActionLabel(
                                              context,
                                              chatState.errorCode,
                                            ),
                                            icon: Icon(
                                              failureKind == FailureKind.auth
                                                  ? Icons.login_rounded
                                                  : Icons.refresh_rounded,
                                            ),
                                            onPressed: () {
                                              if (failureKind ==
                                                  FailureKind.auth) {
                                                context.go('/login');
                                                return;
                                              }
                                              unawaited(
                                                ref
                                                    .read(
                                                      chatProvider.notifier,
                                                    )
                                                    .retryLastMessage(),
                                              );
                                            },
                                            variant: ButtonVariant.secondary,
                                          ),
                                        ),
                                      Material(
                                        color: DS.surfacePrimary
                                            .withValues(alpha: 0),
                                        borderRadius: DS.borderRadiusFull,
                                        child: InkWell(
                                          borderRadius: DS.borderRadiusFull,
                                          onTap: () {
                                            final notifier =
                                                ref.read(chatProvider.notifier);
                                            notifier.state = notifier.state
                                                .copyWith(clearError: true);
                                          },
                                          child: Padding(
                                            padding: const EdgeInsets.all(
                                                DS.spacing4),
                                            child: Icon(
                                              Icons.close,
                                              size: DS.iconSizeXs,
                                              color: DS.error,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  );
                                },
                              ),
                      ),
                    ),
                    // Spine: Time-Aware Recovery Card (divine moment #4 记得时间)
                    if (chatState.pendingStaleCard != null)
                      StaleRecoveryCard(
                        elapsedMinutes:
                            chatState.pendingStaleCard!.elapsedMinutes,
                        pendingTaskStatus:
                            chatState.pendingStaleCard!.pendingTaskStatus,
                        resumeOptions:
                            chatState.pendingStaleCard!.resumeOptions,
                        onOptionSelected: (option) {
                          ref.read(chatProvider.notifier).dismissStaleCard();
                          ref.read(chatProvider.notifier).sendMessage(option);
                        },
                        onDismiss: () =>
                            ref.read(chatProvider.notifier).dismissStaleCard(),
                      ),
                    // Spine: Aurora Judgment-Correction Card (divine moment #2 承认误判)
                    if (chatState.pendingSpineReceipt != null)
                      SpineReceiptCard(
                        trigger: chatState.pendingSpineReceipt!.trigger,
                        summary: chatState.pendingSpineReceipt!.summary,
                        correctable: chatState.pendingSpineReceipt!.correctable,
                        correctionOptions:
                            chatState.pendingSpineReceipt!.correctionOptions,
                        onCorrect: (correction) {
                          ref.read(chatProvider.notifier).dismissSpineReceipt();
                          ref
                              .read(chatProvider.notifier)
                              .sendMessage(correction);
                        },
                        onDismiss: () => ref
                            .read(chatProvider.notifier)
                            .dismissSpineReceipt(),
                      ),
                    // Spine: Community Insight Card (divine moment #6 社群经验转策略)
                    if (chatState.pendingCommunityHint != null)
                      CommunityInsightCard(
                        hintType: chatState.pendingCommunityHint!.hintType,
                        title: chatState.pendingCommunityHint!.title,
                        anonymousSummary:
                            chatState.pendingCommunityHint!.anonymousSummary,
                        tip: chatState.pendingCommunityHint!.tip,
                        onApply: () {
                          final hint = chatState.pendingCommunityHint!;
                          ref
                              .read(chatProvider.notifier)
                              .dismissCommunityHint();
                          ref.read(chatProvider.notifier).sendMessage(
                                context.l10n.chatCommunitySuggestion(
                                    hint.anonymousSummary, hint.tip),
                              );
                        },
                        onDismiss: () => ref
                            .read(chatProvider.notifier)
                            .dismissCommunityHint(),
                      ),
                    // Spine: Strategy Intervention Card (divine moment #5 阻止低收益)
                    if (chatState.pendingUXWarning != null)
                      StrategyInterventionCard(
                        label: chatState.pendingUXWarning!.label,
                        reason: chatState.pendingUXWarning!.reason,
                        suggestedAction:
                            chatState.pendingUXWarning!.suggestedAction,
                        onAdjust: () {
                          final warning = chatState.pendingUXWarning!;
                          ref.read(chatProvider.notifier).dismissUXWarning();
                          ref.read(chatProvider.notifier).sendMessage(
                                context.l10n.chatWarningAction(
                                    warning.suggestedAction, warning.reason),
                              );
                        },
                        onDismiss: () =>
                            ref.read(chatProvider.notifier).dismissUXWarning(),
                      ),
                    // STAB-012: Spine degraded indicator
                    if (chatState.spineDegraded)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        child: Chip(
                          avatar: Icon(
                            Icons.info_outline,
                            size: 14,
                            color: DS.textTertiary,
                          ),
                          label: Text(
                            context.l10n.chatSmartAdjustUnavailable,
                            style: DS.labelSmall.copyWith(
                              color: DS.textTertiary,
                            ),
                          ),
                          backgroundColor: DS.surfacePanel,
                          side: BorderSide.none,
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                    // Spine: Growth Card — divine moment #1 看见坚持
                    if (chatState.pendingGrowthCard != null)
                      GrowthCard(
                        title: chatState.pendingGrowthCard!.title,
                        narrative: chatState.pendingGrowthCard!.narrative,
                        streakDays: chatState.pendingGrowthCard!.streakDays,
                        strategyEffect:
                            chatState.pendingGrowthCard!.strategyEffect,
                        isMilestone: chatState.pendingGrowthCard!.isMilestone,
                        actions: chatState.pendingGrowthCard!.actions,
                        onAction: (action) {
                          ref.read(chatProvider.notifier).dismissGrowthCard();
                          if (action.contains('累') ||
                              action.contains(context.l10n.chatNotNeeded)) {
                            ref.read(chatProvider.notifier).sendMessage(action);
                          }
                        },
                      ),
                    // Spine: Goal Arbitration Card — multi-goal conflict surface
                    if (chatState.pendingGoalArbitration != null)
                      GoalArbitrationCard(
                        primaryGoalTitle:
                            chatState.pendingGoalArbitration!.primaryGoalTitle,
                        reason: chatState.pendingGoalArbitration!.reason,
                        goals: chatState.pendingGoalArbitration!.goals,
                        conflicts: chatState.pendingGoalArbitration!.conflicts,
                        onFocusPrimary: () {
                          final arb = chatState.pendingGoalArbitration!;
                          ref
                              .read(chatProvider.notifier)
                              .dismissGoalArbitration();
                          ref.read(chatProvider.notifier).sendMessage(
                                context.l10n
                                    .chatFocusOnGoal(arb.primaryGoalTitle),
                              );
                        },
                        onContinueMulti: () => ref
                            .read(chatProvider.notifier)
                            .dismissGoalArbitration(),
                        onDismiss: () => ref
                            .read(chatProvider.notifier)
                            .dismissGoalArbitration(),
                      ),
                    // Spine: Divine Moment Card — MAGIC-002 through MAGIC-006
                    if (chatState.pendingDivineMoment != null)
                      DivineMomentCard(
                        data: DivineMomentData.fromJson(
                          chatState.pendingDivineMoment!.cardData,
                        ),
                        onAction: (action) {
                          ref.read(chatProvider.notifier).dismissDivineMoment();
                          if (action.isNotEmpty) {
                            ref.read(chatProvider.notifier).sendMessage(action);
                          }
                        },
                      ),
                    SparkleExitTransition(
                      visible: chatState.pendingPlanReview != null,
                      maintainSize: false,
                      child: chatState.pendingPlanReview == null
                          ? const SizedBox.shrink()
                          : Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.lg,
                                vertical: DS.sm,
                              ),
                              child: PlanReviewCard(
                                review: chatState.pendingPlanReview!,
                                onDecision: (decision, {userComment, meta}) =>
                                    ref
                                        .read(chatProvider.notifier)
                                        .submitPlanReview(
                                          decision: decision,
                                          userComment: userComment,
                                          meta: meta,
                                        ),
                              ),
                            ),
                    ),
                    SparkleExitTransition(
                      visible: chatState.attachedFiles.isNotEmpty,
                      maintainSize: false,
                      child: chatState.attachedFiles.isEmpty
                          ? const SizedBox.shrink()
                          : Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.lg,
                                vertical: DS.sm,
                              ),
                              child: ConstrainedBox(
                                constraints:
                                    const BoxConstraints(maxHeight: 80),
                                child: SingleChildScrollView(
                                  child: Wrap(
                                    spacing: DS.spacing8,
                                    runSpacing: DS.spacing8,
                                    children: chatState.attachedFiles
                                        .map(
                                          (file) => InputChip(
                                            avatar: Icon(
                                              _attachmentStatusIcon(
                                                file.status,
                                              ),
                                              size: 16,
                                              color: _attachmentStatusColor(
                                                file.status,
                                              ),
                                            ),
                                            label: Text(
                                              _attachmentChipLabel(file),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            backgroundColor: Color.alphaBlend(
                                              DS.info.withValues(alpha: 0.04),
                                              DS.surfacePrimary,
                                            ),
                                            side: BorderSide(
                                              color: DS.border
                                                  .withValues(alpha: 0.4),
                                            ),
                                            onDeleted: () => ref
                                                .read(chatProvider.notifier)
                                                .removeAttachment(file.id),
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ),
                              ),
                            ),
                    ),
                    // Bottom input area - wrapped to prevent overflow
                    LayoutBuilder(
                      builder: (context, constraints) => _buildBottomInputArea(
                        context,
                        chatState,
                        constraints,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showHistoryBottomSheet(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (sheetContext) => FractionallySizedBox(
          heightFactor: 0.78,
          child: _ChatHistorySheet(
            currentConversationId: ref.read(chatProvider).conversationId,
            onSelectSession: _loadHistorySessionFromSheet,
          ),
        ),
      ),
    );
  }

  void _showCausalTimelineSheet(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (_) => FractionallySizedBox(
          heightFactor: 0.70,
          child: const CausalTimelinePanel(),
        ),
      ),
    );
  }

  void _openChatSettings(BuildContext context) {
    unawaited(context.push(ChatRoutes.chatSettings));
  }

  Future<void> _navigateFromAction(String route) async {
    if (!mounted || route.isEmpty || !route.startsWith('/')) {
      return;
    }

    final router = GoRouter.of(context);
    final targetUri = Uri.tryParse(route);
    if (targetUri == null) {
      AppFeedback.error(context, context.l10n.chatInvalidNavigationTarget);
      return;
    }

    final currentUri = router.routerDelegate.currentConfiguration.uri;
    if (currentUri.toString() == targetUri.toString()) {
      return;
    }

    try {
      if (_shellRootPaths.contains(targetUri.path)) {
        router.go(route);
        return;
      }
      await router.push(route);
    } catch (_) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.chatNavigationFailed);
      }
    }
  }

  Future<String?> _loadHistorySessionFromSheet(String sessionId) async {
    final l10n = context.l10n;
    if (sessionId.isEmpty) {
      return l10n.chatSessionDataError;
    }

    final currentSessionId = ref.read(chatProvider).conversationId;
    if (currentSessionId == sessionId) {
      return null;
    }

    ref.read(chatProvider.notifier).cancelActiveRun(reason: 'history_switch');
    try {
      await ref
          .read(chatProvider.notifier)
          .loadConversationHistory(sessionId)
          .timeout(const Duration(seconds: 12));
    } on TimeoutException {
      return l10n.chatHistoryLoadFailed(context.l10n.chatHistoryOpenTimeout);
    }
    if (mounted && _scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }
    if (!mounted) {
      return null;
    }

    if (ref.read(chatProvider).conversationId != sessionId) {
      return l10n.chatHistoryLoadFailed(context.l10n.chatHistorySwitchFailed);
    }

    final loadError = ref.read(chatProvider).error;
    return (loadError != null && loadError.isNotEmpty) ? loadError : null;
  }

  void _handleExitChat(BuildContext context) {
    final router = GoRouter.of(context);
    if (router.canPop()) {
      router.pop();
      return;
    }
    router.go('/home');
  }

  void _showWorkingMemorySource(String evidenceToken) {
    final messages = ref.read(chatProvider).messages;
    final matched =
        messages.where((message) => message.id == evidenceToken).toList();
    if (matched.isEmpty) {
      AppFeedback.info(context, context.l10n.chatOriginalTurnUnavailable);
      return;
    }
    final message = matched.first;
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        useRootNavigator: true,
        builder: (sheetContext) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.chatOriginalTurn,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    fontSize: DS.fontSizeLg,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  message.content,
                  style: TextStyle(color: DS.textPrimary),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) => Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(DS.xxl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        DS.primaryBase.withValues(alpha: 0.12),
                        DS.info.withValues(alpha: 0.08),
                      ],
                    ),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: DS.primaryBase.withValues(alpha: 0.18),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: DS.primaryBase.withValues(alpha: 0.08),
                        blurRadius: 18,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Icon(
                    Icons.auto_awesome,
                    size: DS.iconSize3xl,
                    color: DS.primaryBase,
                  ),
                ),
                const SizedBox(height: DS.xl),
                Text(
                  context.l10n.chatWelcomeTitle,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                      ),
                ),
                const SizedBox(height: DS.sm),
                Text(
                  context.l10n.chatWelcomeSubtitle,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: DS.textSecondary,
                        height: 1.5,
                      ),
                ),
                const SizedBox(height: DS.spacing40),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final isNarrow = constraints.maxWidth < DS.breakpointNarrow;
                    return Wrap(
                      spacing: DS.spacing12,
                      runSpacing: DS.spacing12,
                      alignment: WrapAlignment.center,
                      children: [
                        ChatQuickActionChip(
                          icon: Icons.add_task_rounded,
                          label: context.l10n.chatQuickActionNewTask,
                          color: DS.brandPrimaryConst,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref.read(chatProvider.notifier).sendMessage(
                                  context.l10n.chatQuickActionNewTaskPrompt,
                                ),
                          ),
                        ),
                        ChatQuickActionChip(
                          icon: Icons.calendar_month_rounded,
                          label: context.l10n.chatQuickActionLongPlan,
                          color: DS.capsuleAccent,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref.read(chatProvider.notifier).sendMessage(
                                  context.l10n.chatQuickActionLongPlanPrompt,
                                ),
                          ),
                        ),
                        ChatQuickActionChip(
                          icon: Icons.cloud_sync_rounded,
                          label: context.l10n.chatDelegateToOpenclaw,
                          subtitle: context.l10n.chatOpenclawSuitable,
                          color: DS.info,
                          isNarrow: isNarrow,
                          onTap: () => context.push(
                            '${HomeRoutes.openClawHub}?section=delegate',
                          ),
                        ),
                        ChatQuickActionChip(
                          icon: Icons.bug_report_rounded,
                          label: context.l10n.chatQuickActionErrorAttribution,
                          color: DS.brandPrimaryConst,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref.read(chatProvider.notifier).sendMessage(
                                  context.l10n
                                      .chatQuickActionErrorAttributionPrompt,
                                ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      );

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    unawaited(
      _scrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      ),
    );
  }

  /// Calculate bottom padding for ListView to prevent messages being hidden
  /// behind fixed components at the bottom.
  double _calculateBottomPadding(
    BuildContext context,
    ChatState chatState,
    TransparencyPreferences aiSystemPreferences,
    bool showChatTransparencyCapsule,
    bool showStatusIndicator,
  ) {
    final isCompactMobile = _isCompactMobileContext(context);

    if (isCompactMobile && !_showContextControls) {
      return 132 + MediaQuery.of(context).padding.bottom;
    }

    // Use a more generous calculation based on actual screen height
    final screenHeight = MediaQuery.of(context).size.height;
    final isSmallScreen = screenHeight < 700;

    // Base padding
    var padding = isSmallScreen ? DS.spacing40 : DS.spacing64 - DS.spacing4;

    // PlanSelectorPill height (can vary with content)
    padding += isSmallScreen
        ? DS.touchTargetMinSize - DS.spacing4
        : DS.touchTargetMinSize + DS.spacing4;

    // ChatModeSelectorPill height
    padding += isSmallScreen
        ? DS.spacing32 + DS.spacing4
        : DS.touchTargetMinSize - DS.spacing4;

    // AiReasoningModePill height
    padding += isSmallScreen
        ? DS.spacing32 + DS.spacing4
        : DS.touchTargetMinSize - DS.spacing4;

    // IntentPredictionBar height (when visible)
    if (showStatusIndicator) {
      padding += isSmallScreen
          ? DS.touchTargetMinSize
          : DS.touchTargetMinSize + DS.spacing8;
    }

    // ChatInput base height + expansion buffer
    padding += isSmallScreen ? 80.0 : 100.0;

    if (!chatState.hasActiveRun) {
      padding += isSmallScreen ? 108.0 : 124.0;
    }

    if (showChatTransparencyCapsule &&
        aiSystemPreferences.enabled &&
        aiSystemPreferences.displayMode != TransparencyDisplayMode.detailOnly &&
        !chatState.transparencyPresentationState.isDismissed) {
      padding += isSmallScreen ? 56.0 : DS.spacing64;
    }

    // GraphRAG visualizer
    if (chatState.graphragTrace != null) {
      padding += DS.spacing64 + DS.spacing16;
    }

    // SafeArea bottom padding - use actual value with more buffer
    final bottomPadding = MediaQuery.of(context).padding.bottom;
    padding += bottomPadding.clamp(0.0, 50.0);

    // Add extra buffer for safety
    padding += isSmallScreen ? DS.spacing40 : DS.spacing20;

    return padding;
  }

  /// Build the bottom input area with proper overflow handling.
  /// Uses SingleChildScrollView to prevent overflow when components expand.
  Widget _buildBottomInputArea(
    BuildContext context,
    ChatState chatState,
    BoxConstraints constraints,
  ) {
    final aiSystemPreferences =
        ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
            _defaultAiSystemPreferences;
    final isCompactMobile = _isCompactMobileContext(context);
    final showExpandedContext = !isCompactMobile || _showContextControls;
    final showAiSystemPanel = aiSystemPreferences.enabled;
    final currentMode = ref.watch(chatModeProvider);
    final reasoningMode = ref.watch(aiReasoningModeProvider);
    final showChatContextToggle = ref.watch(showChatContextToggleProvider);
    final showChatPredictionDock = ref.watch(showChatPredictionDockProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider);
    final chatPureMode = ref.watch(chatPureModeProvider);
    final documentLibraryState = ref.watch(documentLibraryProvider);
    final readyStudyMaterialsCount =
        (documentLibraryState.documents.valueOrNull ??
                const <DocumentLibraryItem>[])
            .where((doc) => doc.effectiveStatus == DocumentStatus.ready)
            .length;
    final promptStarters = _buildPromptStarters(context, currentMode.apiValue);
    final activePlanId = ref.watch(activePlanProvider);
    final activePlans =
        ref.watch(planListProvider.select((s) => s.activePlans));
    final activePlan =
        activePlans.where((plan) => plan.id == activePlanId).firstOrNull;
    final offlineUserId =
        ref.watch(offlineQueueCurrentUserIdProvider).valueOrNull;
    final offlineSnapshot = offlineUserId == null
        ? OfflineQueueSnapshot.empty
        : ref.watch(offlineQueueSnapshotProvider(offlineUserId)).valueOrNull ??
            OfflineQueueSnapshot.empty;

    return SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isCompactMobile && showChatContextToggle)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                _chatBottomSurfaceHorizontalInset,
                0,
                _chatBottomSurfaceHorizontalInset,
                0,
              ),
              child: ChatContextToggle(
                isExpanded: _showContextControls,
                reasoningLabel: _reasoningModeLabel(reasoningMode),
                modeLabel: currentMode.apiValue == 'standard'
                    ? context.l10n.chatModeStandard
                    : currentMode.label,
                planLabel: activePlan?.name ?? context.l10n.chatPlanUnbound,
                onTap: () {
                  setState(() {
                    _showContextControls = !_showContextControls;
                  });
                },
              ),
            ),
          if (showAiSystemPanel &&
              showChatTransparencyCapsule &&
              !chatPureMode &&
              aiSystemPreferences.displayMode !=
                  TransparencyDisplayMode.detailOnly)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                _chatBottomSurfaceHorizontalInset,
                0,
                _chatBottomSurfaceHorizontalInset,
                DS.spacing4,
              ),
              child: TransparencyFloatingCapsule(
                preferences: aiSystemPreferences,
                runPhase: chatState.runPhase,
                presentationState: chatState.transparencyPresentationState,
                status: chatState.aiStatus,
                details: chatState.aiStatusDetails,
                promptTokens: chatState.lastPromptTokens,
                completionTokens: chatState.lastCompletionTokens,
                totalTokens: chatState.lastTotalTokens,
                currentAgentName: chatState.currentAgentName,
                activeAgentType: chatState.activeAgentType,
                activeTools: chatState.activeTools,
                dailyTokens: chatState.dailyTokens,
                dailyTokenLimit: chatState.dailyTokenLimit,
                dailyCostMicroUsd: chatState.dailyCostMicroUsd,
                transparencyData: chatState.transparencyData,
                runLedgerSummary: chatState.runLedgerSummary,
                currentStepIndex: chatState.currentStepIndex,
                onDismiss: aiSystemPreferences.allowPerTurnDismiss
                    ? () => ref
                        .read(chatProvider.notifier)
                        .dismissTransparencyForCurrentRun()
                    : null,
                onExpandedChanged: (expanded) => ref
                    .read(chatProvider.notifier)
                    .setTransparencyExpanded(expanded),
              ),
            ),
          if (showExpandedContext) ...[
            const SparkleStaggerItem(
              index: 0,
              child: PlanSelectorPill(),
            ),
            const SizedBox(height: DS.spacing8),
            const SparkleStaggerItem(
              index: 1,
              child: AiReasoningModePill(),
            ),
            const SizedBox(height: DS.spacing8),
            const SparkleStaggerItem(
              index: 2,
              child: ChatModeSelectorPill(),
            ),
            const SizedBox(height: DS.spacing8),
            const SparkleStaggerItem(
              index: 3,
              child: GuidanceModeToggle(),
            ),
            Builder(
              builder: (context) {
                final transitions = ref.watch(modeTransitionHistoryProvider);
                if (transitions.isNotEmpty) {
                  return Padding(
                    padding: const EdgeInsets.only(top: DS.spacing4),
                    child: ChatModeTransitionBanner(
                      transition: transitions.last,
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
            const SizedBox(height: DS.spacing2),
          ],
          SparkleExitTransition(
            visible: !chatState.hasActiveRun && showChatPredictionDock,
            maintainSize: false,
            child: !chatState.hasActiveRun && showChatPredictionDock
                ? Padding(
                    padding: const EdgeInsets.only(
                      left: _chatBottomSurfaceHorizontalInset,
                      right: _chatBottomSurfaceHorizontalInset,
                      bottom: DS.spacing6,
                    ),
                    child: SparkleStaggerItem(
                      index: 3,
                      child: ChatPredictionDock(
                        compact: isCompactMobile,
                        promptStarters: promptStarters,
                        onPromptSelected: (prompt) => unawaited(
                          ref.read(chatProvider.notifier).sendMessage(prompt),
                        ),
                      ),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
          Consumer(builder: (context, ref, _) {
            final aurora = ref.watch(auroraStatusProvider);
            if (aurora == null || !aurora.auroraActive)
              return const SizedBox.shrink();
            return _AuroraQuickTrigger(
              snapshot: aurora,
              onTap: () {
                final wake = aurora.wakeEligibility;
                if (wake.canUserWake &&
                    (aurora.overallStatus == 'risk_found' ||
                        aurora.overallStatus == 'calibration_available' ||
                        aurora.overallStatus == 'needs_confirm')) {
                  unawaited(showAuroraCoreSession(
                    context: context,
                    bandStatus: aurora.overallStatus,
                    wakeReasons: wake.wakeReasons,
                    entryReason: AuroraCoreSessionEntryReason.fromSnapshot(
                      snapshot: aurora,
                      triggerSource: 'status_bar',
                      agendaPreview: [
                        context.l10n.chatAgendaConfirmStatusBarJudgment,
                        context.l10n.chatAgendaDecideAdjustNextSteps,
                      ],
                    ),
                    conversationId: chatState.conversationId,
                  ));
                } else {
                  showAuroraCalibration(
                    context: context,
                    observation: aurora.summary,
                    judgment: aurora.summary,
                    confirmQuestion: context.l10n.auroraCalibrationConfirm,
                    confirmOptions: [
                      context.l10n.chatMinutes30,
                      context.l10n.chatMinutes45,
                      context.l10n.chatMinutes60
                    ],
                    onConfirm: (option) {
                      ref.read(chatProvider.notifier).sendMessage(
                            '${context.l10n.auroraCorrectRecalibrate}: $option',
                          );
                    },
                  );
                }
              },
            );
          }),
          _OfflineQueueIndicatorHost(
            snapshot: offlineSnapshot,
            connectionState: chatState.wsConnectionState,
          ),
          ChatInput(
            enabled: !chatState.hasActiveRun,
            studyMaterialsEnabled: chatState.documentRetrievalEnabled,
            documentContextMode: chatState.documentContextMode,
            availableStudyMaterialsCount: readyStudyMaterialsCount,
            onToggleStudyMaterials: () {
              ref.read(chatProvider.notifier).setDocumentRetrievalEnabled(
                    !chatState.documentRetrievalEnabled,
                  );
            },
            onSetDocumentContextMode: (mode) {
              ref.read(chatProvider.notifier).setDocumentContextMode(mode);
            },
            onOpenStudyMaterials: () => _showStudyMaterialsSheet(
              chatState.documentRetrievalEnabled,
            ),
            onTextChanged: (text) {
              if (mounted) {
                ref
                    .read(intentPredictionProvider.notifier)
                    .onInputChanged(text);
              }
            },
            onFileUploaded: (StoredFile file) {
              ref.read(chatProvider.notifier).addAttachment(file);
              final status = file.status.trim().toLowerCase();
              if (status.isNotEmpty && status != 'processed') {
                AppFeedback.info(
                  context,
                  context.l10n.chatFileAdded(
                      file.fileName, _attachmentStatusText(file.status)),
                );
              }
            },
            onSend: (text, {replyToId}) => unawaited(
              ref.read(chatProvider.notifier).sendMessage(text),
            ),
            onFreeformCorrection: (text) =>
                _submitFreeformAuroraCorrection(text),
          ),
          if (chatState.graphragTrace != null)
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing8),
              child: GraphRAGVisualizer(
                trace: chatState.graphragTrace,
              ),
            ),
          // Bottom safe area padding — only shown when keyboard is closed
          if (MediaQuery.of(context).viewInsets.bottom == 0)
            SizedBox(
              height: max(
                DS.spacing8,
                MediaQuery.of(context).padding.bottom,
              ),
            ),
        ],
      ),
    );
  }

  String _reasoningModeLabel(String mode) {
    switch (mode) {
      case 'fast':
        return context.l10n.chatReasoningFast;
      case 'deep':
        return context.l10n.chatReasoningDeep;
      case 'balanced':
      default:
        return context.l10n.chatReasoningBalanced;
    }
  }

  static bool _shouldDuckForReasoning(ChatState state) {
    if (state.isReasoningActive) {
      return true;
    }
    final status = state.aiStatus;
    return status == 'THINKING' ||
        status == 'ANALYZING' ||
        status == 'PLANNING' ||
        status == 'REVIEWING' ||
        status == 'SEARCHING';
  }

  bool _shouldShowReasoningAtmosphere(ChatState state) =>
      _shouldDuckForReasoning(state) &&
      state.runPhase.isActive &&
      state.streamingContent.isEmpty;

  void _showStudyMaterialsSheet(bool retrievalEnabled) {
    final chatState = ref.read(chatProvider);
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => StudyMaterialsSheet(
          retrievalEnabled: retrievalEnabled,
          documentContextMode: chatState.documentContextMode,
          onModeChanged: (mode) {
            ref.read(chatProvider.notifier).setDocumentContextMode(mode);
          },
        ),
      ),
    );
  }

  String _attachmentChipLabel(StoredFile file) {
    final statusText = _attachmentStatusText(file.status);
    if (statusText.isEmpty) {
      return file.fileName;
    }
    return '${file.fileName} · $statusText';
  }

  String _attachmentStatusText(String status) {
    switch (status.trim().toLowerCase()) {
      case 'processed':
        return context.l10n.chatReady;
      case 'uploaded':
      case 'processing':
        return context.l10n.chatProcessing;
      case 'failed':
        return context.l10n.chatAttachmentFailed;
      default:
        return status.trim();
    }
  }

  IconData _attachmentStatusIcon(String status) {
    switch (status.trim().toLowerCase()) {
      case 'processed':
        return Icons.check_circle_rounded;
      case 'uploaded':
      case 'processing':
        return Icons.hourglass_top_rounded;
      case 'failed':
        return Icons.error_rounded;
      default:
        return Icons.insert_drive_file_rounded;
    }
  }

  Color _attachmentStatusColor(String status) {
    switch (status.trim().toLowerCase()) {
      case 'processed':
        return DS.semanticSuccess;
      case 'uploaded':
      case 'processing':
        return DS.warning;
      case 'failed':
        return DS.semanticError;
      default:
        return DS.textSecondary;
    }
  }

  bool _isCompactMobileContext(BuildContext context) {
    final media = MediaQuery.of(context);
    return media.orientation == Orientation.portrait && media.size.width < 430;
  }

  List<String> _buildPromptStarters(BuildContext context, String mode) {
    switch (mode) {
      case 'deep_analysis':
        return [
          context.l10n.chatPromptDeepAnalysis1,
          context.l10n.chatPromptDeepAnalysis2,
          context.l10n.chatPromptDeepAnalysis3,
        ];
      case 'study_plan':
        return [
          context.l10n.chatPromptStudyPlan1,
          context.l10n.chatPromptStudyPlan2,
          context.l10n.chatPromptStudyPlan3,
        ];
      case 'error_diagnosis':
        return [
          context.l10n.chatPromptErrorDiagnosis1,
          context.l10n.chatPromptErrorDiagnosis2,
          context.l10n.chatPromptErrorDiagnosis3,
        ];
      case 'expert_auto':
        return [
          context.l10n.chatPromptExpertAuto1,
          context.l10n.chatPromptExpertAuto2,
          context.l10n.chatPromptExpertAuto3,
        ];
      default:
        return [
          context.l10n.chatPromptDefault1,
          context.l10n.chatPromptDefault2,
          context.l10n.chatPromptDefault3,
        ];
    }
  }
}

class _OpenClawAppBarIcon extends StatelessWidget {
  const _OpenClawAppBarIcon({
    required this.highlighted,
    required this.queueCount,
  });

  final bool highlighted;
  final int queueCount;

  @override
  Widget build(BuildContext context) => Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing4),
            decoration: BoxDecoration(
              color: highlighted
                  ? DS.info.withValues(alpha: 0.1)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.cloud_sync_outlined,
              color: highlighted ? DS.brandPrimaryConst : DS.textSecondary,
            ),
          ),
          if (highlighted)
            Positioned(
              right: -2,
              top: -2,
              child: Container(
                constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                padding: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  color: queueCount > 0 ? DS.warning : DS.semanticError,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Center(
                  child: Text(
                    queueCount > 0 ? '$queueCount' : '!',
                    style: DS.bodySmall.copyWith(
                      color: DS.onColor(
                        queueCount > 0 ? DS.warning : DS.semanticError,
                      ),
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
}

class _ChatHistorySheet extends ConsumerStatefulWidget {
  const _ChatHistorySheet({
    required this.onSelectSession,
    this.currentConversationId,
  });

  final String? currentConversationId;
  final Future<String?> Function(String sessionId) onSelectSession;

  @override
  ConsumerState<_ChatHistorySheet> createState() => _ChatHistorySheetState();
}

class _ChatHistorySheetState extends ConsumerState<_ChatHistorySheet> {
  late Future<List<Map<String, dynamic>>> _historyFuture;
  String? _openingSessionId;
  String? _inlineError;

  @override
  void initState() {
    super.initState();
    _historyFuture = _fetchHistory();
  }

  Future<List<Map<String, dynamic>>> _fetchHistory() async {
    final notifier = ref.read(chatProvider.notifier);
    return notifier.getRecentConversations().timeout(
          const Duration(seconds: 8),
          onTimeout: () => throw Exception(context.l10n.chatLoadHistoryTimeout),
        );
  }

  void _refresh() {
    setState(() {
      _inlineError = null;
      _historyFuture = _fetchHistory();
    });
  }

  Future<void> _openSession(String sessionId) async {
    if (_openingSessionId != null) {
      return;
    }
    if (sessionId == widget.currentConversationId) {
      if (mounted) {
        await Navigator.of(context, rootNavigator: true).maybePop();
      }
      return;
    }
    setState(() {
      _openingSessionId = sessionId;
      _inlineError = null;
    });
    final error = await widget.onSelectSession(sessionId).timeout(
          const Duration(seconds: 12),
          onTimeout: () => I18nService.instance.l10n.chatHistoryLoadFailed(
            context.l10n.chatHistoryOpenTimeout,
          ),
        );
    if (!mounted) {
      return;
    }
    if (error == null || error.isEmpty) {
      await Navigator.of(context, rootNavigator: true).maybePop();
      return;
    }
    setState(() {
      _openingSessionId = null;
      _inlineError = error;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = I18nService.instance.l10n;
    return GraphiteModalSurface(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
      expandChild: true,
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            Row(
              children: [
                DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        DS.surfaceOverlay,
                        Color.alphaBlend(
                          DS.info.withValues(alpha: 0.04),
                          DS.surfacePrimary,
                        ),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Icon(
                      Icons.history_rounded,
                      color: DS.primaryBase,
                    ),
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Text(
                    l10n.chatHistoryTitle,
                    style: DS.titleLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                SparkleIconButton(
                  icon: Icon(Icons.refresh_rounded, color: DS.textSecondary),
                  onPressed: _openingSessionId == null ? _refresh : null,
                  semanticLabel: l10n.refresh,
                  variant: ButtonVariant.ghost,
                ),
                SparkleIconButton(
                  icon: Icon(Icons.close_rounded, color: DS.textSecondary),
                  onPressed: () =>
                      Navigator.of(context, rootNavigator: true).maybePop(),
                  semanticLabel: l10n.close,
                  variant: ButtonVariant.ghost,
                ),
              ],
            ),
            if (_inlineError != null) ...[
              const SizedBox(height: DS.md),
              ChatHistoryInlineError(
                message: _inlineError!,
                onRetry: _openingSessionId == null ? _refresh : null,
              ),
            ],
            const SizedBox(height: DS.md),
            Expanded(
              child: FutureBuilder<List<Map<String, dynamic>>>(
                future: _historyFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const SparkleListSkeleton(count: 5);
                  }

                  if (snapshot.hasError) {
                    return ChatHistoryInlineError(
                      message: l10n.chatHistoryLoadFailed('${snapshot.error}'),
                      onRetry: _refresh,
                    );
                  }

                  final sessions = snapshot.data ?? [];
                  if (sessions.isEmpty) {
                    return Center(
                      child: Text(
                        l10n.chatHistoryEmpty,
                        style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                      ),
                    );
                  }

                  return ListView.builder(
                    itemCount: sessions.length,
                    itemBuilder: (context, index) {
                      final session = sessions[index];
                      final sessionId = session['id']?.toString() ?? '';
                      final isCurrent =
                          sessionId == widget.currentConversationId;
                      final isOpening = _openingSessionId == sessionId;

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: GraphiteCardSurface(
                          padding: EdgeInsets.zero,
                          borderColor: isCurrent
                              ? DS.primaryBase.withValues(alpha: 0.22)
                              : DS.borderSubtle,
                          surfaceRole: SparkleSurfaceRole.card,
                          child: ListTile(
                            enabled: !isOpening && _openingSessionId == null,
                            leading: Container(
                              padding: const EdgeInsets.all(DS.sm),
                              decoration: BoxDecoration(
                                color: isCurrent
                                    ? DS.primaryBase.withValues(alpha: 0.12)
                                    : DS.surfaceOverlay,
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.chat_bubble_outline_rounded,
                                size: DS.iconSizeXs,
                                color: isCurrent
                                    ? DS.primaryBase
                                    : DS.textSecondary,
                              ),
                            ),
                            title: Text(
                              (session['title'] as String?) ??
                                  l10n.chatSessionUntitled,
                              style: DS.bodyLarge.copyWith(
                                color: DS.textPrimary,
                                fontWeight: isCurrent
                                    ? DS.fontWeightBold
                                    : DS.fontWeightMedium,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: Text(
                              (session['updated_at'] as String?)
                                      ?.replaceFirst('T', ' ')
                                      .split('.')
                                      .first ??
                                  '',
                              style: DS.labelSmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                            trailing: isOpening
                                ? SizedBox(
                                    width: DS.iconSizeXs,
                                    height: DS.iconSizeXs,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                        DS.primaryBase,
                                      ),
                                    ),
                                  )
                                : isCurrent
                                    ? Icon(
                                        Icons.check_circle,
                                        color: DS.primaryBase,
                                        size: DS.iconSizeXs,
                                      )
                                    : null,
                            onTap: sessionId.isEmpty
                                ? null
                                : () => unawaited(_openSession(sessionId)),
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DailyStartupPlanResolution {
  const _DailyStartupPlanResolution({
    required this.planId,
    this.cachedStartup,
    this.shouldSelectPlan = false,
  });

  final String planId;
  final String? cachedStartup;
  final bool shouldSelectPlan;
}

class _OfflineQueueIndicatorHost extends StatefulWidget {
  const _OfflineQueueIndicatorHost({
    required this.snapshot,
    required this.connectionState,
  });

  final OfflineQueueSnapshot snapshot;
  final WsConnectionState connectionState;

  @override
  State<_OfflineQueueIndicatorHost> createState() =>
      _OfflineQueueIndicatorHostState();
}

class _OfflineQueueIndicatorHostState
    extends State<_OfflineQueueIndicatorHost> {
  Timer? _completeTimer;
  var _showComplete = false;
  var _hadActiveQueue = false;

  @override
  void didUpdateWidget(_OfflineQueueIndicatorHost oldWidget) {
    super.didUpdateWidget(oldWidget);
    final hasActiveQueue = widget.snapshot.hasActiveQueue;
    if (_hadActiveQueue && !hasActiveQueue) {
      _showComplete = true;
      _completeTimer?.cancel();
      _completeTimer = Timer(const Duration(seconds: 2), () {
        if (mounted) {
          setState(() => _showComplete = false);
        }
      });
    }
    _hadActiveQueue = hasActiveQueue;
  }

  @override
  void dispose() {
    _completeTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final snapshot = widget.snapshot;
    if (_showComplete && !snapshot.hasActiveQueue) {
      return const OfflineQueueIndicator(
        status: OfflineQueueIndicatorStatus.complete,
        pendingCount: 0,
      );
    }
    if (!snapshot.hasActiveQueue) {
      return const OfflineQueueIndicator(
        status: OfflineQueueIndicatorStatus.hidden,
        pendingCount: 0,
      );
    }

    final isSending = widget.connectionState == WsConnectionState.connected ||
        widget.connectionState == WsConnectionState.connecting ||
        widget.connectionState == WsConnectionState.reconnecting ||
        snapshot.sendingCount > 0;
    return OfflineQueueIndicator(
      status: isSending
          ? OfflineQueueIndicatorStatus.sending
          : OfflineQueueIndicatorStatus.queued,
      pendingCount: max(1, max(snapshot.pendingCount, snapshot.activeCount)),
    );
  }
}

class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _ReviewNodeBanner extends StatelessWidget {
  const _ReviewNodeBanner({
    required this.nodeLabel,
    this.mastery,
  });

  final String nodeLabel;
  final double? mastery;

  @override
  Widget build(BuildContext context) {
    final masteryText = mastery != null
        ? context.l10n.chatCurrentMastery(
            (mastery! * 100).round().clamp(0, 100).toString())
        : '';
    return Container(
      margin: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing4,
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: DS.info.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.info.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(Icons.auto_stories_rounded, size: DS.iconSizeSm, color: DS.info),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              context.l10n.chatReviewingNode(nodeLabel, masteryText),
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.info,
                fontWeight: DS.fontWeightMedium,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

/// 流式输出气泡 - 显示正在流式输出的 AI 响应
class _StreamingBubble extends StatefulWidget {
  const _StreamingBubble({required this.content});
  final String content;

  @override
  State<_StreamingBubble> createState() => _StreamingBubbleState();
}

class _StreamingBubbleState extends State<_StreamingBubble> {
  bool _entered = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        setState(() {
          _entered = true;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bubbleColor = DS.chatBubbleOther;
    final textColor = DS.chatBubbleOtherText;

    return TweenAnimationBuilder<Offset>(
      tween: Tween<Offset>(
        begin: const Offset(0, 0.08),
        end: _entered ? Offset.zero : const Offset(0, 0.08),
      ),
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      builder: (context, offset, child) => Transform.translate(
        offset: Offset(0, offset.dy * 32),
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          opacity: _entered ? 1 : 0,
          child: child,
        ),
      ),
      child: Align(
        alignment: Alignment.centerLeft,
        child: AnimatedSize(
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutQuint,
          alignment: Alignment.topLeft,
          child: Container(
            constraints: BoxConstraints(
              maxWidth: _bubbleMaxWidth(context),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(DS.spacing20),
                topRight: Radius.circular(DS.spacing20),
                bottomRight: Radius.circular(DS.spacing20),
                bottomLeft: Radius.circular(DS.spacing4),
              ),
              boxShadow: DS.shadowSm,
              border: Border.all(
                color: isDark ? DS.neutral700 : DS.borderSubtle,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Flexible(
                  child: SparkleMarkdown(
                    content: widget.content,
                    isStreaming: true,
                    textColor: textColor,
                    codeBackgroundColor: isDark
                        ? DS.neutral700
                        : DS.chatBubbleOtherText.withValues(alpha: 0.06),
                    linkColor: DS.brandPrimary,
                    contentRole: SparkleMarkdownRole.chatBubble,
                  ),
                ),
                const SizedBox(width: DS.xs),
                _BlinkingCursor(color: textColor),
              ],
            ),
          ),
        ),
      ),
    );
  }

  double _bubbleMaxWidth(BuildContext context) {
    final screenWidth = ResponsiveSystem.width(context);
    final contentMaxWidth = ContentConstraintSystem.maxWidth(context);
    final baseMax = contentMaxWidth.isFinite ? contentMaxWidth : screenWidth;
    return min(screenWidth * 0.8, baseMax * 0.9);
  }
}

/// 闪烁光标组件
class _BlinkingCursor extends StatefulWidget {
  const _BlinkingCursor({required this.color});

  final Color color;

  @override
  State<_BlinkingCursor> createState() => _BlinkingCursorState();
}

class _BlinkingCursorState extends State<_BlinkingCursor>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    unawaited(_controller.repeat(reverse: true));
    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) {
      return Container(
        width: DS.spacing4 / 2,
        height: DS.spacing16,
        color: widget.color,
      );
    }
    return RepaintBoundary(
      child: FadeTransition(
        opacity: _animation,
        child: Container(
          width: DS.spacing4 / 2,
          height: DS.spacing16,
          color: widget.color,
        ),
      ),
    );
  }
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bubbleColor = DS.chatBubbleOther;
    final dotColor = DS.chatBubbleOtherText.withValues(alpha: 0.7);
    final reduceMotion = context.reduceMotion;
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 8, end: 0),
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      builder: (context, translateY, child) => Transform.translate(
        offset: Offset(0, translateY),
        child: child,
      ),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: bubbleColor,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(DS.spacing20),
            topRight: Radius.circular(DS.spacing20),
            bottomRight: Radius.circular(DS.spacing20),
            bottomLeft: Radius.circular(DS.spacing4),
          ),
          boxShadow: DS.shadowSm,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(
            3,
            (index) {
              if (reduceMotion) {
                return Container(
                  margin: const EdgeInsets.symmetric(
                    horizontal: DS.spacing4 / 2,
                  ),
                  width: DS.spacing8,
                  height: DS.spacing8,
                  decoration: BoxDecoration(
                    color: dotColor,
                    shape: BoxShape.circle,
                  ),
                );
              }
              return AnimatedBuilder(
                animation: _controller,
                builder: (context, child) {
                  final delay = index * (1 / 3);
                  final progress =
                      ((_controller.value - delay + 1) % 1.0).clamp(0.0, 1.0);
                  final opacity = 0.25 + (sin(progress * pi) * 0.75);
                  final scale = 0.72 + (sin(progress * pi) * 0.28);

                  return Opacity(
                    opacity: opacity.clamp(0.2, 1.0),
                    child: Transform.scale(
                      scale: scale.clamp(0.72, 1.0),
                      child: Container(
                        margin: const EdgeInsets.symmetric(
                          horizontal: DS.spacing4 / 2,
                        ),
                        width: DS.spacing8,
                        height: DS.spacing8,
                        decoration: BoxDecoration(
                          color: dotColor,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ReasoningBreathOverlay extends StatefulWidget {
  const _ReasoningBreathOverlay();

  @override
  State<_ReasoningBreathOverlay> createState() =>
      _ReasoningBreathOverlayState();
}

class _ReasoningBreathOverlayState extends State<_ReasoningBreathOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );
    unawaited(_controller.repeat(reverse: true));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = context.reduceMotion;
    if (reduceMotion) {
      return const SizedBox.shrink();
    }
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final opacity = lerpDouble(0.03, 0.08, _controller.value) ?? 0.05;
        return DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0.1, -0.2),
              radius: 1.0,
              colors: [
                DS.info.withValues(alpha: opacity),
                DS.brandPrimary.withValues(alpha: opacity * 0.78),
                Colors.transparent,
              ],
              stops: const [0.0, 0.42, 1.0],
            ),
          ),
        );
      },
    );
  }
}

/// Lightweight chip that shows the current dual-core routing mode sent by
/// the backend in the `ux_turn.dual_core_mode` field of every agent_turn event.
///
/// Modes: "execution" → 执行模式 (amber), "cognitive" → 认知模式 (indigo),
///        "balanced" → 均衡模式 (teal / primary)
class _DualCoreModeChip extends StatelessWidget {
  const _DualCoreModeChip({required this.mode});

  final String mode;

  (String label, Color color, IconData icon) _resolve(BuildContext context) {
    return switch (mode) {
      'execution' => (
          context.l10n.chatExecutionMode,
          DS.warning,
          Icons.bolt_rounded
        ),
      'cognitive' => (
          context.l10n.chatCognitiveMode,
          DS.brandSecondary,
          Icons.psychology_rounded
        ),
      _ => (
          context.l10n.chatBalancedMode,
          DS.primaryBase,
          Icons.balance_rounded
        ),
    };
  }

  @override
  Widget build(BuildContext context) {
    final (label, color, icon) = _resolve(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border:
                  Border.all(color: color.withValues(alpha: 0.3), width: 0.8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 12, color: color),
                const SizedBox(width: 4),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: DS.fontWeightMedium,
                    color: color,
                    letterSpacing: 0.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AuroraQuickTrigger extends StatelessWidget {
  const _AuroraQuickTrigger({
    required this.snapshot,
    required this.onTap,
  });

  final AuroraControlSurfaceSnapshot snapshot;
  final VoidCallback onTap;

  Color _statusColor() {
    return switch (snapshot.overallStatus) {
      'calibrated' => DS.success,
      'risk_found' => DS.warning,
      'needs_confirm' => DS.info,
      'calibration_available' => DS.brandPrimary,
      'cooling_down' => DS.textSecondary,
      _ => DS.textSecondary,
    };
  }

  String _statusLabel(AppLocalizations l10n) {
    return switch (snapshot.overallStatus) {
      'calibrated' => l10n.auroraBandCalibrated,
      'risk_found' => l10n.auroraBandRiskFound,
      'needs_confirm' => l10n.auroraBandNeedsConfirm,
      'calibration_available' => l10n.auroraBandCalibrationAvailable,
      'cooling_down' => l10n.auroraBandCoolingDown,
      _ => l10n.auroraBandSensing,
    };
  }

  @override
  Widget build(BuildContext context) {
    final color = _statusColor();
    final l10n = context.l10n;
    final wake = snapshot.wakeEligibility;
    final canWake = wake.canUserWake &&
        (snapshot.overallStatus == 'risk_found' ||
            snapshot.overallStatus == 'calibration_available' ||
            snapshot.overallStatus == 'needs_confirm');
    final statusText = canWake
        ? '${_statusLabel(l10n)} · ${l10n.auroraWakeAvailable(wake.userQuotaRemaining)}'
        : _statusLabel(l10n);

    return Padding(
      padding:
          const EdgeInsets.fromLTRB(DS.spacing12, 0, DS.spacing12, DS.spacing4),
      child: Semantics(
        button: true,
        label: statusText,
        child: GestureDetector(
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 44),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: color.withValues(alpha: 0.2)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.auto_awesome_rounded, size: 14, color: color),
                  const SizedBox(width: DS.spacing6),
                  Text(
                    statusText,
                    style: TextStyle(
                      color: color,
                      fontSize: 11,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
