import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
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

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final activePlanId = ref.read(activePlanProvider);
      unawaited(
          ref.read(chatProvider.notifier).switchPlanSession(activePlanId));
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final messages = chatState.messages;
    final isDark = Theme.of(context).brightness == Brightness.dark;

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
                  'AI学习助手',
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    fontSize: DS.fontSizeBase,
                  ),
                ),
                Text(
                  '随时为你解答',
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
            semanticLabel: '历史对话',
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
          ),
          SparkleIconButton(
            icon: Icon(Icons.add_comment_outlined, color: DS.textSecondary),
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
            semanticLabel: '新建对话',
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
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
                                        bottom: DS.spacing12),
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
                                        bottom: DS.spacing12),
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
                                          bottom: DS.spacing12),
                                      child: _StreamingBubble(
                                        content: chatState.streamingContent,
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
                                  padding: EdgeInsets.all(DS.spacing4),
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
                          context, chatState, constraints),
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
      showModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (context) {
          final mediaQuery = MediaQuery.of(context);
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
                            '历史对话',
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
                                    child: Text('加载失败: ${snapshot.error}'),
                                  ),
                                ),
                              ],
                            );
                          }

                          final sessions = snapshot.data ?? [];
                          if (sessions.isEmpty) {
                            return ListView(
                              controller: scrollController,
                              children: const [
                                SizedBox(
                                  height: 200,
                                  child: Center(child: Text('暂无历史记录')),
                                ),
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
                                      (session['title'] as String?) ?? '未命名会话',
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
                                          context, session),
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
      AppFeedback.error(context, '无法识别跳转地址');
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
        AppFeedback.error(context, '页面跳转失败，请重试');
      }
    }
  }

  Future<void> _handleHistorySessionTap(
    BuildContext sheetContext,
    Map<String, dynamic> session,
  ) async {
    Navigator.of(sheetContext).pop();

    final sessionId = session['id']?.toString() ?? '';
    if (sessionId.isEmpty) {
      AppFeedback.error(context, '会话数据异常，请重试');
      return;
    }

    final currentSessionId = ref.read(chatProvider).conversationId;
    if (currentSessionId == sessionId) {
      return;
    }

    await ref.read(chatProvider.notifier).loadConversationHistory(sessionId);
    if (!mounted) {
      return;
    }

    final loadError = ref.read(chatProvider).error;
    if (loadError != null && loadError.isNotEmpty) {
      AppFeedback.error(context, loadError);
    }
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
                  '你好，我是你的 AI 导师',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: DS.textPrimary,
                      ),
                ),
                const SizedBox(height: DS.sm),
                Text(
                  '今天想做点什么？',
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
                          label: '新建微任务',
                          color: DS.brandPrimaryConst,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage('帮我创建一个新的微任务'),
                          ),
                        ),
                        _QuickActionChip(
                          icon: Icons.calendar_month_rounded,
                          label: '生成长期计划',
                          color: DS.capsuleAccent,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage('帮我生成一个长期学习计划'),
                          ),
                        ),
                        _QuickActionChip(
                          icon: Icons.bug_report_rounded,
                          label: '错误归因',
                          color: DS.brandPrimaryConst,
                          isNarrow: isNarrow,
                          onTap: () => unawaited(
                            ref
                                .read(chatProvider.notifier)
                                .sendMessage('我想分析一下最近的错误原因'),
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
    ChatMessageModel? latestAssistant;
    for (final message in chatState.messages.reversed) {
      if (message.role == MessageRole.assistant) {
        latestAssistant = message;
        break;
      }
    }
    final latestEnvelope =
        latestAssistant?.uxEnvelope ?? const <String, dynamic>{};
    final continuityBanner =
        latestEnvelope['continuity_banner'] as Map<String, dynamic>?;
    final modeExplanation =
        latestEnvelope['mode_explanation'] as Map<String, dynamic>?;
    final currentMode = ref.watch(chatModeProvider);
    final dynamicPrompts = _buildPromptStarters(currentMode.apiValue);
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
                    ? '标准对话'
                    : currentMode.label,
                planLabel: activePlan?.name ?? '未绑定计划',
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
            const ChatModeSelectorPill(),
          ],
          if (showExpandedContext &&
              (modeExplanation != null || currentMode.apiValue != 'standard'))
            Padding(
              padding: const EdgeInsets.only(
                left: DS.spacing16,
                right: DS.spacing16,
                top: DS.spacing8,
              ),
              child: _ContextStrip(
                icon: Icons.auto_awesome,
                title:
                    modeExplanation?['label']?.toString() ?? currentMode.label,
                description: modeExplanation?['description']?.toString() ??
                    currentMode.description,
              ),
            ),
          if (showExpandedContext && continuityBanner != null)
            Padding(
              padding: const EdgeInsets.only(
                left: DS.spacing16,
                right: DS.spacing16,
                top: DS.spacing8,
              ),
              child: _ContextStrip(
                icon: Icons.link_rounded,
                title: continuityBanner['title']?.toString() ?? '继续当前上下文',
                description: continuityBanner['message']?.toString() ?? '',
              ),
            ),
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
                AppFeedback.info(context, '文件处理中，完成后可用于对话');
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

  List<String> _buildPromptStarters(String mode) {
    switch (mode) {
      case 'deep_analysis':
        return const ['先给综合判断，再展开依据', '只看关键结论和风险', '补一个反方观点帮我校准'];
      case 'study_plan':
        return const ['先按今天能开始的节奏排', '拆成今天/本周两个层级', '按我现在水平再降一点难度'];
      case 'error_diagnosis':
        return const ['先定位错因和证据', '给我一条针对性修复练习', '告诉我下次怎么避免再错'];
      case 'expert_auto':
        return const ['自动选专家给我综合结论', '先告诉我这轮请了谁', '把专家结果压成执行清单'];
      default:
        return const ['直接回答我的当前问题', '先给我 3 步执行清单', '结合我当前计划继续推进'];
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

class _ContextStrip extends StatelessWidget {
  const _ContextStrip({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    if (title.trim().isEmpty && description.trim().isEmpty) {
      return const SizedBox.shrink();
    }
    return DecoratedBox(
      decoration: BoxDecoration(
        color: DS.surfaceTertiary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.neutral200),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: DS.iconSizeSm, color: DS.primaryBase),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (title.trim().isNotEmpty)
                    Text(
                      title,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.textPrimary,
                          ),
                    ),
                  if (description.trim().isNotEmpty) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      description,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
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
                    '$modeLabel · ${planLabel.isEmpty ? '未绑定计划' : planLabel}',
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
