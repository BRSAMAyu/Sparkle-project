import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_workflow_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/transparency_panel.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/intent_prediction_bar.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

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

  @override
  void initState() {
    super.initState();
    ref.listenManual(chatProvider.select((state) => state.messages),
        (previous, next) {
      if (next.length > (previous?.length ?? 0)) {
        _scrollToBottom();
      }
    });

    ref.listenManual(activePlanProvider, (previous, next) {
      if (previous != next) {
        unawaited(ref.read(chatProvider.notifier).switchPlanSession(next));
      }
    });

    // 🔧 错误修复：监听错误状态，10秒后自动清除（避免长时间阻塞UI）
    ref.listenManual(chatProvider.select((state) => state.error),
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
    });

    // 🔧 修复：将ref.listen移到initState，避免在build中监听
    ref.listenManual(
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
            notifier.state = notifier.state.copyWith(clearActionFeedback: true);
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
    );

    // 🔧 Phase 2.3: 监听 WebSocket 连接状态变化并显示反馈
    ref.listenManual(
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
              ref.read(chatProvider.notifier).loadConversationHistory(conversationId),
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
          ref.read(chatProvider.notifier).switchPlanSession(activePlanId),);
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
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
      role: SparklePageRole.content,
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
                              chatState.aiStatus == null &&
                              !chatState.isReasoningActive
                          ? _buildQuickActions(context)
                          : ListView.builder(
                              controller: _scrollController,
                              reverse: true,
                              padding: EdgeInsets.only(
                                left: DS.spacing16,
                                right: DS.spacing16,
                                top: DS.spacing20,
                                bottom:
                                    _calculateBottomPadding(context, chatState),
                              ),
                              cacheExtent: 600,
                              itemCount: chatState.listItemCount,
                              itemBuilder: (context, index) {
                                final isStatusShowing =
                                    chatState.aiStatus != null;
                                final isReasoningShowing =
                                    chatState.isReasoningActive;
                                final isSendingShowing = chatState.isSending;

                                if (isStatusShowing && index == 0) {
                                  return Padding(
                                    padding: const EdgeInsets.only(
                                        bottom: DS.spacing12,),
                                    child: AiStatusIndicator(
                                      status: chatState.aiStatus,
                                      details: chatState.aiStatusDetails,
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
                                        bottom: DS.spacing12,),
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
                                          bottom: DS.spacing12,),
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
                    if (chatState.error != null)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(DS.sm),
                        color: DS.error.withValues(alpha: 0.1),
                        child: Row(
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
                              color: DS.surfacePrimary.withValues(alpha: 0),
                              borderRadius: DS.borderRadiusFull,
                              child: InkWell(
                                borderRadius: DS.borderRadiusFull,
                                onTap: () {
                                  // Clear error
                                  // 🔧 修复：正确使用StateNotifier更新状态
                                  final notifier =
                                      ref.read(chatProvider.notifier);
                                  notifier.state =
                                      notifier.state.copyWith(clearError: true);
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(DS.spacing4),
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
                    if (chatState.pendingPlanReview != null)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.lg,
                          vertical: DS.sm,
                        ),
                        child: PlanReviewCard(
                          review: chatState.pendingPlanReview!,
                          onDecision: (decision, {userComment, meta}) =>
                              ref.read(chatProvider.notifier).submitPlanReview(
                                    decision: decision,
                                    userComment: userComment,
                                    meta: meta,
                                  ),
                        ),
                      ),
                    if (chatState.attachedFiles.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.lg,
                          vertical: DS.sm,
                        ),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxHeight: 80),
                          child: SingleChildScrollView(
                            child: Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: chatState.attachedFiles
                                  .map(
                                    (file) => InputChip(
                                      label: Text(
                                        file.fileName,
                                        overflow: TextOverflow.ellipsis,
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
                    // Bottom input area - wrapped to prevent overflow
                    LayoutBuilder(
                      builder: (context, constraints) => _buildBottomInputArea(
                          context, chatState, constraints,),
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
    final l10n = I18nService.instance.l10n;
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        useRootNavigator: true,
        isScrollControlled: true,
        builder: (sheetContext) {
          final mediaQuery = MediaQuery.of(sheetContext);
          final maxHeight = mediaQuery.size.height -
              mediaQuery.viewPadding.top -
              kToolbarHeight;
          final maxChildSize =
              (maxHeight / mediaQuery.size.height).clamp(0.6, 0.95);
          final initialChildSize = min(0.7, maxChildSize);

          return DraggableScrollableSheet(
            expand: false,
            initialChildSize: initialChildSize,
            minChildSize: 0.4,
            maxChildSize: maxChildSize,
            builder: (context, scrollController) => GraphiteModalSurface(
              padding: EdgeInsets.zero,
              child: SafeArea(
                top: false,
                child: Column(
                  children: [
                    Container(
                      width: DS.spacing40,
                      height: DS.spacing4,
                      margin:
                          const EdgeInsets.symmetric(vertical: DS.spacing12),
                      decoration: BoxDecoration(
                        color: DS.surfaceTertiary,
                        borderRadius: BorderRadius.circular(DS.spacing4 / 2),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                      child: Row(
                        children: [
                          DecoratedBox(
                            decoration: BoxDecoration(
                              color: DS.surfaceOverlay,
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
                          Text(
                            l10n.chatHistoryTitle,
                            style: DS.titleLarge.copyWith(
                              color: DS.textPrimary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: FutureBuilder<List<Map<String, dynamic>>>(
                        future: ref
                            .read(chatProvider.notifier)
                            .getRecentConversations(),
                        builder: (context, snapshot) {
                          if (snapshot.connectionState ==
                              ConnectionState.waiting) {
                            return ListView(
                              controller: scrollController,
                              children: const [
                                SizedBox(
                                  height: 200,
                                  child: Center(
                                    child: CircularProgressIndicator(),
                                  ),
                                ),
                              ],
                            );
                          }

                          if (snapshot.hasError) {
                            return ListView(
                              controller: scrollController,
                              children: [
                                SizedBox(
                                  height: 200,
                                  child: Center(
                                    child: Text(
                                      l10n.chatHistoryLoadFailed(
                                        '${snapshot.error}',
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            );
                          }

                          final sessions = snapshot.data ?? [];
                          if (sessions.isEmpty) {
                            return ListView(
                              controller: scrollController,
                              children: [
                                const SizedBox(height: 200),
                                Center(child: Text(l10n.chatHistoryEmpty)),
                              ],
                            );
                          }

                          return ListView.builder(
                            controller: scrollController,
                            itemCount: sessions.length,
                            itemBuilder: (context, index) {
                              final session = sessions[index];
                              final isCurrent = session['id'] ==
                                  ref.read(chatProvider).conversationId;

                              return Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 6,
                                ),
                                child: GraphiteCardSurface(
                                  padding: EdgeInsets.zero,
                                  borderColor: isCurrent
                                      ? DS.primaryBase.withValues(alpha: 0.22)
                                      : DS.borderSubtle,
                                  child: ListTile(
                                    leading: Container(
                                      padding: const EdgeInsets.all(DS.sm),
                                      decoration: BoxDecoration(
                                        color: isCurrent
                                            ? DS.primaryBase
                                                .withValues(alpha: 0.12)
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
                                              ?.split('T')[0] ??
                                          '',
                                      style: DS.labelSmall.copyWith(
                                        color: DS.textSecondary,
                                      ),
                                    ),
                                    trailing: isCurrent
                                        ? Icon(
                                            Icons.check_circle,
                                            color: DS.primaryBase,
                                            size: DS.iconSizeXs,
                                          )
                                        : null,
                                    onTap: () => unawaited(
                                      _handleHistorySessionTap(
                                          sheetContext, session,),
                                    ),
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
            ),
          );
        },
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

  Future<void> _handleHistorySessionTap(
    BuildContext sheetContext,
    Map<String, dynamic> session,
  ) async {
    final navigator = Navigator.of(sheetContext, rootNavigator: true);
    if (navigator.canPop()) {
      navigator.pop();
    }

    final sessionId = session['id']?.toString() ?? '';
    if (sessionId.isEmpty) {
      AppFeedback.error(context, context.l10n.chatSessionDataError);
      return;
    }

    final currentSessionId = ref.read(chatProvider).conversationId;
    if (currentSessionId == sessionId) {
      return;
    }

    await ref.read(chatProvider.notifier).loadConversationHistory(sessionId);
    if (mounted) {
      _scrollController.jumpTo(0);
    }
    if (!mounted) {
      return;
    }

    final loadError = ref.read(chatProvider).error;
    if (loadError != null && loadError.isNotEmpty) {
      AppFeedback.error(context, loadError);
    }
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
                    color: DS.primaryBase.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
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
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: DS.textSecondary,
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
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage(
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
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage(
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
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage(
                                  context
                                      .l10n
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
  double _calculateBottomPadding(BuildContext context, ChatState chatState) {
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

    // IntentPredictionBar height (when visible)
    if (chatState.aiStatus != null) {
      padding += isSmallScreen
          ? DS.touchTargetMinSize
          : DS.touchTargetMinSize + DS.spacing8;
    }

    // ChatInput base height + expansion buffer
    padding += isSmallScreen ? 80.0 : 100.0;

    // TransparencyPanel (conditional)
    if (ref.watch(transparentModeProvider)) {
      padding += isSmallScreen
          ? DS.spacing64 + DS.spacing64 + DS.spacing12
          : DS.spacing64 + DS.spacing64 + DS.spacing32;
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
    final isCompactMobile = _isCompactMobileContext(context);
    final showExpandedContext = !isCompactMobile || _showContextControls;
    final transparentMode = ref.watch(transparentModeProvider);
    final currentMode = ref.watch(chatModeProvider);
    final dynamicPrompts =
        _buildPromptStarters(context, currentMode.apiValue);
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
          if (isCompactMobile)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing12,
                0,
                DS.spacing12,
                DS.spacing8,
              ),
              child: _ChatContextToggle(
                isExpanded: _showContextControls,
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
          if (showExpandedContext && transparentMode)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing12),
              child: TransparencyPanel(
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
                currentStepIndex: chatState.currentStepIndex,
              ),
            ),
          if (showExpandedContext) ...[
            const PlanSelectorPill(),
            const SizedBox(height: DS.spacing18),
            const ChatModeSelectorPill(),
          ],
          if (showExpandedContext) const IntentPredictionBar(showIdle: false),
          if (showExpandedContext &&
              !chatState.isSending &&
              dynamicPrompts.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(
                left: DS.spacing16,
                right: DS.spacing16,
                top: DS.spacing8,
              ),
              child: Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: dynamicPrompts
                    .map(
                      (prompt) => ActionChip(
                        label: Text(prompt),
                        onPressed: () => unawaited(
                          ref.read(chatProvider.notifier).sendMessage(prompt),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ChatInput(
            enabled: !chatState.isSending,
            onTextChanged: (text) {
              if (mounted) {
                ref
                    .read(intentPredictionProvider.notifier)
                    .onInputChanged(text);
              }
            },
            onFileUploaded: (StoredFile file) {
              if (file.status != 'processed') {
                AppFeedback.info(context, context.l10n.chatFileProcessing);
                return;
              }
              ref.read(chatProvider.notifier).addAttachment(file);
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
    required this.modeLabel,
    required this.planLabel,
    required this.onTap,
  });

  final bool isExpanded;
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
                    '$modeLabel · ${planLabel.isEmpty ? context.l10n.chatPlanUnbound : planLabel}',
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
    // Use a lighter color for better contrast in dark mode
    final bubbleColor = isDark ? DS.neutral800 : DS.brandPrimary;
    final textColor = isDark ? DS.textPrimary : DS.onBrandPrimary;
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
          border: Border.all(color: isDark ? DS.neutral700 : DS.neutral200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Flexible(
              child: Text(
                content,
                style: TextStyle(
                  color: textColor,
                  fontSize: DS.fontSizeBase,
                ),
              ),
            ),
            const SizedBox(width: DS.xs),
            // 闪烁的光标
            const _BlinkingCursor(),
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
  const _BlinkingCursor();

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
          color: DS.primaryBase,
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    // Use a lighter color for better contrast in dark mode
    final bubbleColor = isDark ? DS.neutral800 : DS.brandPrimary;
    final dotColor = isDark
        ? DS.textPrimary.withValues(alpha: 0.7)
        : DS.onBrandPrimary.withValues(alpha: 0.7);
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
        border: Border.all(color: isDark ? DS.neutral700 : DS.neutral200),
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
