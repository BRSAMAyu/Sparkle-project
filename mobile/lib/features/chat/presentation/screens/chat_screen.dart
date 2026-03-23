import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_workflow_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_reasoning_mode_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_prediction_dock.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/transparency_floating_capsule.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/settings/presentation/screens/transparency_settings_screen.dart';
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

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({
    super.key,
    this.initialPrompt,
    this.initialChatMode,
  });

  final String? initialPrompt;
  final String? initialChatMode;

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

  final ScrollController _scrollController = ScrollController();
  bool _showContextControls = false;
  String? _dispatchedInitialPrompt;

  @override
  void initState() {
    super.initState();
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
      // 🔧 错误修复：监听错误状态，10秒后自动清除（避免长时间阻塞UI）
      ..listenManual(chatProvider.select((state) => state.error),
          (previous, next) {
        if (next != null && next != previous) {
          Future.delayed(const Duration(seconds: 10), () {
            if (mounted) {
              final currentError = ref.read(chatProvider).error;
              if (currentError == next) {
                // 错误仍然相同，自动清除
                // 🔧 修复：正确使用StateNotifier更新状态
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

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final activePlanId = ref.read(activePlanProvider);
      unawaited(
        ref.read(chatProvider.notifier).switchPlanSession(activePlanId),
      );
      if (ref.read(dashboardProvider).nextIntentForecast == null) {
        unawaited(ref.read(dashboardProvider.notifier).refresh());
      }
      _queueInitialPromptDispatch();
    });
  }

  @override
  void didUpdateWidget(covariant ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialPrompt != widget.initialPrompt ||
        oldWidget.initialChatMode != widget.initialChatMode) {
      _queueInitialPromptDispatch();
    }
  }

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
      await ref.read(chatProvider.notifier).sendMessage(nextPrompt);
    });
  }

  @override
  Widget build(BuildContext context) {
    const experience = ExperienceProfiles.assistantFlow;
    final chatState = ref.watch(chatProvider);
    final aiSystemPreferences =
        ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
            _defaultAiSystemPreferences;
    final messages = chatState.messages;
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
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  l10n.chatTitle,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    fontSize: DS.fontSizeBase,
                  ),
                ),
                Text(
                  l10n.chatSubtitle,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: DS.fontSizeXs,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          SparkleIconButton(
            icon: Icon(Icons.tune_rounded, color: DS.textSecondary),
            onPressed: () => _showAiSystemSettings(context),
            semanticLabel: 'AI system settings',
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Icon(Icons.history, color: DS.textSecondary),
            onPressed: () => _showHistoryBottomSheet(context),
            semanticLabel: l10n.chatHistoryTitle,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Icon(Icons.add_comment_outlined, color: DS.textSecondary),
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
            semanticLabel: l10n.chatNewConversation,
            variant: ButtonVariant.ghost,
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
                    Expanded(
                      child: messages.isEmpty &&
                              chatState.streamingContent.isEmpty &&
                              !chatState.shouldShowStatusIndicator &&
                              !chatState.shouldShowReasoningIndicator
                          ? _buildQuickActions(context)
                          : ListView.builder(
                              controller: _scrollController,
                              reverse: true,
                              padding: EdgeInsets.only(
                                left: DS.spacing16,
                                right: DS.spacing16,
                                top: DS.spacing20,
                                bottom: _calculateBottomPadding(
                                  context,
                                  chatState,
                                  aiSystemPreferences,
                                ),
                              ),
                              cacheExtent: 600,
                              itemCount: chatState.listItemCount,
                              itemBuilder: (context, index) {
                                final isStatusShowing =
                                    chatState.shouldShowStatusIndicator;
                                final isReasoningShowing =
                                    chatState.shouldShowReasoningIndicator;
                                final isSendingShowing =
                                    chatState.shouldShowStreamingBubble;

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
                                          _StreamingBubble(
                                            content: chatState.streamingContent,
                                          ),
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
                                return ChatBubble(
                                  message: message,
                                  isLatestAssistantMessage:
                                      message.id == latestAssistantMessageId,
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
                            : Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      chatState.error!,
                                      style: TextStyle(
                                        color: DS.error,
                                        fontSize: DS.fontSizeSm,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  Material(
                                    color:
                                        DS.surfacePrimary.withValues(alpha: 0),
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
                                        padding:
                                            const EdgeInsets.all(DS.spacing4),
                                        child: Icon(
                                          Icons.close,
                                          size: DS.iconSizeXs,
                                          color: DS.error,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                      ),
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
                                              _attachmentStatusIcon(file.status),
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
    if (sessionId.isEmpty) {
      return context.l10n.chatSessionDataError;
    }

    final currentSessionId = ref.read(chatProvider).conversationId;
    if (currentSessionId == sessionId) {
      return null;
    }

    ref.read(chatProvider.notifier).cancelActiveRun(reason: 'history_switch');
    await ref.read(chatProvider.notifier).loadConversationHistory(sessionId);
    if (mounted) {
      _scrollController.jumpTo(0);
    }
    if (!mounted) {
      return null;
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
                        fontWeight: FontWeight.bold,
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
                        _QuickActionChip(
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
                        _QuickActionChip(
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
                        _QuickActionChip(
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
    if (chatState.shouldShowStatusIndicator) {
      padding += isSmallScreen
          ? DS.touchTargetMinSize
          : DS.touchTargetMinSize + DS.spacing8;
    }

    // ChatInput base height + expansion buffer
    padding += isSmallScreen ? 80.0 : 100.0;

    if (!chatState.hasActiveRun) {
      padding += isSmallScreen ? 108.0 : 124.0;
    }

    if (aiSystemPreferences.enabled &&
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
    final promptStarters = _buildPromptStarters(context, currentMode.apiValue);
    final activePlanId = ref.watch(activePlanProvider);
    final activePlans =
        ref.watch(planListProvider.select((s) => s.activePlans));
    final activePlan =
        activePlans.where((plan) => plan.id == activePlanId).firstOrNull;

    return SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isCompactMobile && showChatContextToggle)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing12,
                0,
                DS.spacing12,
                DS.spacing4,
              ),
              child: _ChatContextToggle(
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
              aiSystemPreferences.displayMode !=
                  TransparencyDisplayMode.detailOnly)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing12),
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
            const SizedBox(height: DS.spacing10),
            const SparkleStaggerItem(
              index: 1,
              child: AiReasoningModePill(),
            ),
            const SizedBox(height: DS.spacing10),
            const SparkleStaggerItem(
              index: 2,
              child: ChatModeSelectorPill(),
            ),
            const SizedBox(height: DS.spacing4),
          ],
          SparkleExitTransition(
            visible: !chatState.hasActiveRun && showChatPredictionDock,
            maintainSize: false,
            child: !chatState.hasActiveRun && showChatPredictionDock
                ? Padding(
                    padding: const EdgeInsets.only(
                      left: DS.spacing16,
                      right: DS.spacing16,
                      top: DS.spacing2,
                      bottom: DS.spacing8,
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
          ChatInput(
            enabled: !chatState.hasActiveRun,
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
                  '${file.fileName} 已添加，当前状态：${_attachmentStatusText(file.status)}',
                );
              }
            },
            onSend: (text, {replyToId}) => unawaited(
              ref.read(chatProvider.notifier).sendMessage(text),
            ),
          ),
          if (chatState.graphragTrace != null)
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing8),
              child: GraphRAGVisualizer(
                trace: chatState.graphragTrace,
              ),
            ),
          // Bottom safe area padding
          SizedBox(height: MediaQuery.of(context).padding.bottom),
        ],
      ),
    );
  }

  String _reasoningModeLabel(String mode) {
    switch (mode) {
      case 'fast':
        return '敏捷';
      case 'deep':
        return '深思';
      case 'balanced':
      default:
        return '均衡';
    }
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
        return '已就绪';
      case 'uploaded':
      case 'processing':
        return '处理中';
      case 'failed':
        return '失败';
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

  void _showAiSystemSettings(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (sheetContext) => Consumer(
          builder: (context, ref, _) {
            final preferences =
                ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
                    _defaultAiSystemPreferences;
            final notifier =
                ref.read(transparencyPreferencesNotifierProvider.notifier);

            return GraphiteModalSurface(
              padding: EdgeInsets.zero,
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing20,
                    DS.spacing12,
                    DS.spacing20,
                    DS.spacing20,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Center(
                        child: Container(
                          width: DS.spacing40,
                          height: DS.spacing4,
                          decoration: BoxDecoration(
                            color: DS.surfaceTertiary,
                            borderRadius:
                                BorderRadius.circular(DS.spacing4 / 2),
                          ),
                        ),
                      ),
                      const SizedBox(height: DS.spacing20),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(DS.spacing10),
                            decoration: BoxDecoration(
                              color: DS.surfaceOverlay,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: DS.borderSubtle),
                            ),
                            child: Icon(
                              Icons.auto_awesome_rounded,
                              color: DS.primaryBase,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Sparkle AI System',
                                  style: DS.titleLarge.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '在对话中展示多 Agent 协作、模型编排与质量依据。',
                                  style: DS.bodySmall.copyWith(
                                    color: DS.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing20),
                      _buildAiSettingTile(
                        title: '显示 AI 系统面板',
                        subtitle: '默认开启，在聊天页直接展示协作与推理能力。',
                        value: preferences.enabled,
                        onChanged: notifier.setEnabled,
                      ),
                      if (preferences.enabled) ...[
                        const SizedBox(height: DS.spacing12),
                        _buildAiSettingTile(
                          title: '显示 Token 与成本',
                          subtitle: '展示本轮用量、成本估算和系统资源消耗。',
                          value: preferences.showTokenUsage,
                          onChanged: notifier.setShowTokenUsage,
                        ),
                        const SizedBox(height: DS.spacing12),
                        _buildAiSettingTile(
                          title: '显示 Agent 协作',
                          subtitle: '展示参与的专家、职责分工和模型协同。',
                          value: preferences.showAgentSwitching,
                          onChanged: notifier.setShowAgentSwitching,
                        ),
                        const SizedBox(height: DS.spacing12),
                        _buildAiSettingTile(
                          title: '显示推理时间线',
                          subtitle: '展示关键步骤、审查与反思过程。',
                          value: preferences.showReasoningSteps,
                          onChanged: notifier.setShowReasoningSteps,
                        ),
                      ],
                      const SizedBox(height: DS.spacing20),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.of(sheetContext).pop();
                            unawaited(
                              Navigator.of(context, rootNavigator: true).push(
                                MaterialPageRoute<void>(
                                  builder: (_) =>
                                      const TransparencySettingsScreen(),
                                ),
                              ),
                            );
                          },
                          icon: const Icon(Icons.settings_outlined),
                          label: const Text('打开高级设置'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildAiSettingTile({
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        child: SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(
            title,
            style: DS.bodyLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          subtitle: Text(
            subtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          value: value,
          onChanged: onChanged,
        ),
      );

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
          onTimeout: () => throw Exception('加载对话历史超时，请稍后重试'),
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
    final error = await widget.onSelectSession(sessionId);
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
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                SparkleIconButton(
                  icon: Icon(Icons.refresh_rounded, color: DS.textSecondary),
                  onPressed: _openingSessionId == null ? _refresh : null,
                  semanticLabel: 'refresh history',
                  variant: ButtonVariant.ghost,
                ),
                SparkleIconButton(
                  icon: Icon(Icons.close_rounded, color: DS.textSecondary),
                  onPressed: () =>
                      Navigator.of(context, rootNavigator: true).maybePop(),
                  semanticLabel: 'close history',
                  variant: ButtonVariant.ghost,
                ),
              ],
            ),
            if (_inlineError != null) ...[
              const SizedBox(height: DS.md),
              _InlineChatHistoryError(
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
                    return const Center(child: CircularProgressIndicator());
                  }

                  if (snapshot.hasError) {
                    return _InlineChatHistoryError(
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
                                    ? FontWeight.w700
                                    : FontWeight.w500,
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

class _InlineChatHistoryError extends StatelessWidget {
  const _InlineChatHistoryError({
    required this.message,
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: GraphiteCardSurface(
          borderColor: DS.error.withValues(alpha: 0.14),
          surfaceRole: SparkleSurfaceRole.card,
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline_rounded, color: DS.error),
                const SizedBox(height: DS.sm),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                if (onRetry != null) ...[
                  const SizedBox(height: DS.md),
                  SparkleButton(
                    label: '重试',
                    icon: const Icon(Icons.refresh_rounded),
                    onPressed: onRetry,
                    variant: ButtonVariant.secondary,
                  ),
                ],
              ],
            ),
          ),
        ),
      );
}

class _QuickActionChip extends StatefulWidget {
  const _QuickActionChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.isNarrow,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final bool isNarrow;
  final VoidCallback onTap;

  @override
  State<_QuickActionChip> createState() => _QuickActionChipState();
}

class _ChatContextToggle extends StatelessWidget {
  const _ChatContextToggle({
    required this.isExpanded,
    required this.reasoningLabel,
    required this.modeLabel,
    required this.planLabel,
    required this.onTap,
  });

  final bool isExpanded;
  final String reasoningLabel;
  final String modeLabel;
  final String planLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final labelColor =
        isDark ? DS.textPrimary.withValues(alpha: 0.92) : DS.textSecondary;
    final iconColor =
        isDark ? DS.secondaryLight.withValues(alpha: 0.92) : DS.textSecondary;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: DS.borderRadius16,
        onTap: onTap,
        child: Ink(
          decoration: BoxDecoration(
            color: isDark
                ? DS.surfaceTertiary.withValues(alpha: 0.92)
                : DS.surfaceOverlay,
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: isDark
                  ? DS.borderStrong.withValues(alpha: 0.68)
                  : DS.borderSubtle,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            child: Row(
              children: [
                Icon(
                  Icons.tune_rounded,
                  size: DS.iconSizeSm,
                  color: iconColor,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    '$reasoningLabel · $modeLabel · ${planLabel.isEmpty ? context.l10n.chatPlanUnbound : planLabel}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: DS.bodySmall.copyWith(
                      color: labelColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Icon(
                  isExpanded
                      ? Icons.keyboard_arrow_down_rounded
                      : Icons.keyboard_arrow_up_rounded,
                  size: DS.iconSizeSm,
                  color: iconColor,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuickActionChipState extends State<_QuickActionChip> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    // Use surfaceTertiary background for consistent theming
    final backgroundColor = DS.surfaceTertiary;
    // Use textPrimary for proper contrast in both modes
    final labelColor = DS.textPrimary;
    final horizontalPadding = widget.isNarrow ? DS.spacing12 : DS.spacing16;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _isPressed ? 0.95 : 1.0,
        duration: DS.durationFast,
        curve: DS.curveEaseOut,
        child: Container(
          // Ensure minimum 48px touch target
          height: DS.touchTargetMinSize,
          padding: EdgeInsets.symmetric(
            horizontal: horizontalPadding,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: DS.borderRadius20,
            border: Border.all(
              color: widget.color.withValues(alpha: _isPressed ? 0.6 : 0.3),
              width: _isPressed ? 1.5 : 1.0,
            ),
            boxShadow: [
              BoxShadow(
                color: widget.color.withValues(alpha: _isPressed ? 0.2 : 0.1),
                blurRadius: _isPressed ? 4 : 8,
                offset: _isPressed ? const Offset(0, 2) : const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                widget.icon,
                size: DS.iconSizeSm,
                color: widget.color,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                widget.label,
                style: TextStyle(
                  color: labelColor,
                  fontWeight: DS.fontWeightMedium,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

/// 流式输出气泡 - 显示正在流式输出的 AI 响应
class _StreamingBubble extends StatelessWidget {
  const _StreamingBubble({required this.content});
  final String content;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bubbleColor = DS.chatBubbleOther;
    final textColor = DS.chatBubbleOtherText;

    return Align(
      alignment: Alignment.centerLeft,
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
          border: Border.all(color: isDark ? DS.neutral700 : DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Flexible(
              child: SparkleMarkdown(
                content: content,
                isStreaming: true,
                textColor: textColor,
                codeBackgroundColor: isDark
                    ? DS.neutral700
                    : DS.chatBubbleOtherText.withValues(alpha: 0.06),
                linkColor: DS.brandPrimary,
              ),
            ),
            const SizedBox(width: DS.xs),
            _BlinkingCursor(color: textColor),
          ],
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
  Widget build(BuildContext context) => FadeTransition(
        opacity: _animation,
        child: Container(
          width: DS.spacing4 / 2,
          height: DS.spacing16,
          color: widget.color,
        ),
      );
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
    return Container(
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
          (index) => AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final delay = index * 0.2;
              final progress =
                  ((_controller.value - delay) % 1.0).clamp(0.0, 1.0);
              final offset = sin(progress * pi) * 6;

              return Transform.translate(
                offset: Offset(0, -offset),
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
              );
            },
          ),
        ),
      ),
    );
  }
}
