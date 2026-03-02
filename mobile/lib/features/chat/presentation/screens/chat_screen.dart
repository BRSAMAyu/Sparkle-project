import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
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
import 'package:sparkle/features/plan/presentation/screens/execution_copilot_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final ScrollController _scrollController = ScrollController();

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
          if (message != null && mounted) {
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

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        flexibleSpace: ClipRect(
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    (isDark ? DS.surfaceAmbient : DS.surfacePrimary)
                        .withValues(alpha: 0.9),
                    (isDark ? DS.surfacePrimary : DS.neutral50)
                        .withValues(alpha: 0.9),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: Border(
                  bottom: BorderSide(
                    color: isDark
                        ? DS.brandPrimary.withValues(alpha: 0.1)
                        : DS.brandPrimary.withValues(alpha: 0.05),
                    width: 0.5,
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
                gradient: DS.secondaryGradient,
                shape: BoxShape.circle,
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
      body: DecoratedBox(
        decoration: BoxDecoration(
          // Use three-layer gradient matching Dashboard WeatherHeader style
          gradient: isDark
              ? LinearGradient(
                  colors: [
                    DS.surfaceAmbient,
                    DS.surfacePrimary,
                    DS.surfaceSecondary
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                )
              : LinearGradient(
                  colors: [DS.neutral50, DS.neutral100, DS.neutral200],
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
                                  onQuickAdjust: (instruction) {
                                    ref
                                        .read(chatProvider.notifier)
                                        .sendMessage(instruction);
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

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
            builder: (context, scrollController) => DecoratedBox(
              decoration: BoxDecoration(
                // Use surfaceSecondary to match Dashboard ceramic cards
                color: isDark ? DS.surfaceSecondary : DS.surfacePrimaryElevated,
                borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(DS.spacing24)),
              ),
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
                      padding: const EdgeInsets.all(DS.lg),
                      child: Row(
                        children: [
                          Icon(Icons.history_rounded, color: DS.primaryBase),
                          const SizedBox(width: DS.md),
                          Text(
                            '历史对话',
                            style: TextStyle(
                              fontSize: DS.fontSizeLg,
                              fontWeight: FontWeight.bold,
                              color: DS.textPrimary,
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

                              return ListTile(
                                leading: Container(
                                  padding: const EdgeInsets.all(DS.sm),
                                  decoration: BoxDecoration(
                                    color: isCurrent
                                        ? DS.primaryBase.withValues(alpha: 0.1)
                                        : DS.surfaceTertiary,
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
                                  style: TextStyle(
                                    color: DS.textPrimary,
                                    fontWeight: isCurrent
                                        ? FontWeight.bold
                                        : FontWeight.normal,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                subtitle: Text(
                                  (session['updated_at'] as String?)
                                          ?.split('T')[0] ??
                                      '',
                                  style: TextStyle(
                                    fontSize: DS.fontSizeXs,
                                    color: DS.neutral500,
                                  ),
                                ),
                                trailing: isCurrent
                                    ? Icon(
                                        Icons.check_circle,
                                        color: DS.primaryBase,
                                        size: DS.iconSizeXs,
                                      )
                                    : null,
                                onTap: () {
                                  Navigator.pop(context);
                                  unawaited(
                                    ref
                                        .read(chatProvider.notifier)
                                        .loadConversationHistory(
                                          session['id'] as String,
                                        ),
                                  );
                                },
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

  void _openExecutionCopilot({
    required BuildContext context,
    required String planId,
  }) {
    unawaited(
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => ExecutionCopilotScreen(planId: planId),
        ),
      ),
    );
  }

  /// Calculate bottom padding for ListView to prevent messages being hidden
  /// behind fixed components at the bottom.
  double _calculateBottomPadding(BuildContext context, ChatState chatState) {
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
    final transparentMode = ref.watch(transparentModeProvider);
    final selectedPlanId = ref.watch(activePlanProvider);

    return SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (transparentMode)
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
          const PlanSelectorPill(),
          const ChatModeSelectorPill(),
          const IntentPredictionBar(showIdle: false),
          if (selectedPlanId != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                DS.spacing8,
                DS.spacing16,
                DS.spacing4,
              ),
              child: Align(
                alignment: Alignment.centerLeft,
                child: ActionChip(
                  avatar: const Icon(Icons.checklist_rounded, size: 18),
                  label: const Text('今日执行驾驶舱'),
                  onPressed: chatState.isSending
                      ? null
                      : () {
                          _openExecutionCopilot(
                            context: context,
                            planId: selectedPlanId,
                          );
                        },
                ),
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
