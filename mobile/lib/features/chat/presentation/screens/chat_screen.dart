import 'dart:async';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_selector_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/transparency_panel.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/intent_prediction_bar.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
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
    ref.listenManual(
        chatProvider.select((state) => state.messages), (previous, next) {
      if (next.length > (previous?.length ?? 0)) {
        _scrollToBottom();
      }
    });

    ref.listenManual(activePlanProvider, (previous, next) {
      if (previous != next) {
        unawaited(ref.read(chatProvider.notifier).switchPlanSession(next));
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final activePlanId = ref.read(activePlanProvider);
      unawaited(ref.read(chatProvider.notifier).switchPlanSession(activePlanId));
    });
  }

  @override
  Widget build(BuildContext context) {
    // Listen for action status updates to show SnackBar
    ref.listen(chatProvider.select((state) => state.lastActionStatus),
        (previous, next) {
      if (next != null && next != previous) {
        final message = ref.read(chatProvider).lastActionMessage;
        if (message != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(message),
              behavior: SnackBarBehavior.floating,
              backgroundColor: next == 'failed' || next == 'error'
                  ? DS.error
                  : DS.primaryBase,
              duration: const Duration(seconds: 2),
            ),
          );
        }
      }
    });

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
                        width: 0.5,),),
              ),
            ),
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                gradient: DS.secondaryGradient,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.auto_awesome,
                  color: DS.brandPrimaryConst, size: 20,),
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
          IconButton(
            icon: Icon(Icons.history, color: DS.textSecondary),
            onPressed: () => _showHistoryBottomSheet(context),
          ),
          IconButton(
            icon: Icon(Icons.add_comment_outlined, color: DS.textSecondary),
            tooltip: 'New Chat',
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
          ),
        ],
      ),
      body: DecoratedBox(
        decoration: BoxDecoration(
          // Use three-layer gradient matching Dashboard WeatherHeader style
          gradient: isDark
              ? LinearGradient(
                  colors: [DS.surfaceAmbient, DS.surfacePrimary, DS.surfaceSecondary],
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
                        backgroundColor: Colors.transparent,
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
                                left: 16.0,
                                right: 16.0,
                                top: 20.0,
                                bottom: _calculateBottomPadding(context, chatState),
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
                                    padding:
                                        const EdgeInsets.only(bottom: 12.0),
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
                                    padding:
                                        const EdgeInsets.only(bottom: 12.0),
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
                                      padding:
                                          const EdgeInsets.only(bottom: 12.0),
                                      child: _StreamingBubble(
                                        content: chatState.streamingContent,
                                      ),
                                    );
                                  }

                                  if (!isStatusShowing &&
                                      !isReasoningShowing) {
                                    return const Padding(
                                      padding: EdgeInsets.only(bottom: 12.0),
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
                                );
                              },
                            ),
                    ),
                    if (chatState.error != null)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(DS.sm),
                        color: DS.error.withValues(alpha: 0.1),
                        child: Text(
                          'Error: ${chatState.error}',
                          style: TextStyle(color: DS.error),
                          textAlign: TextAlign.center,
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
                              spacing: 8,
                              runSpacing: 8,
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
                      builder: (context, constraints) => _buildBottomInputArea(context, chatState, constraints),
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
        backgroundColor: Colors.transparent,
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
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: SafeArea(
                top: false,
                child: Column(
                  children: [
                    Container(
                      width: 40,
                      height: 4,
                      margin: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: DS.surfaceTertiary,
                        borderRadius: BorderRadius.circular(2),
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
                              fontSize: 18,
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
                                    size: 18,
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
                                  style:
                                      TextStyle(fontSize: 12, color: DS.neutral500),
                                ),
                                trailing: isCurrent
                                    ? Icon(Icons.check_circle,
                                        color: DS.primaryBase, size: 18,)
                                    : null,
                                onTap: () {
                                  Navigator.pop(context);
                                  unawaited(
                                    ref
                                        .read(chatProvider.notifier)
                                        .loadConversationHistory(
                                            session['id'] as String,),
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
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.auto_awesome, size: 48, color: DS.primaryBase),
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
              const SizedBox(height: 40),
              LayoutBuilder(
                builder: (context, constraints) {
                  final isNarrow = constraints.maxWidth < DS.breakpointNarrow;
                  return Wrap(
                    spacing: 12,
                    runSpacing: 12,
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
    // Use a more generous calculation based on actual screen height
    final screenHeight = MediaQuery.of(context).size.height;
    final isSmallScreen = screenHeight < 700;

    // Base padding
    var padding = isSmallScreen ? 40.0 : 60.0;

    // PlanSelectorPill height (can vary with content)
    padding += isSmallScreen ? 44.0 : 52.0;

    // ChatModeSelectorPill height
    padding += isSmallScreen ? 36.0 : 44.0;

    // IntentPredictionBar height (when visible)
    if (chatState.aiStatus != null) {
      padding += isSmallScreen ? 48.0 : 56.0;
    }

    // ChatInput base height + expansion buffer
    padding += isSmallScreen ? 80.0 : 100.0;

    // TransparencyPanel (conditional)
    if (ref.watch(transparentModeProvider)) {
      padding += isSmallScreen ? 140.0 : 160.0;
    }

    // GraphRAG visualizer
    if (chatState.graphragTrace != null) {
      padding += 80.0;
    }

    // SafeArea bottom padding - use actual value with more buffer
    final bottomPadding = MediaQuery.of(context).padding.bottom;
    padding += bottomPadding.clamp(0.0, 50.0);

    // Add extra buffer for safety
    padding += isSmallScreen ? 40.0 : 20.0;

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
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('文件处理中，完成后可用于对话')),
                );
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
    final horizontalPadding = widget.isNarrow ? 12.0 : DS.spacing16;

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
    final bubbleColor = isDark ? const Color(0xFF2A2A2A) : DS.brandPrimary;
    final textColor = isDark ? DS.textPrimary : DS.onBrandPrimary;
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: _bubbleMaxWidth(context),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: bubbleColor,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(4),
          ),
          boxShadow: DS.shadowSm,
          border: Border.all(color: isDark ? const Color(0xFF3A3A3A) : DS.neutral200),
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
    final baseMax =
        contentMaxWidth.isFinite ? contentMaxWidth : screenWidth;
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
          width: 2,
          height: 16,
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
    final bubbleColor = isDark ? const Color(0xFF2A2A2A) : DS.brandPrimary;
    final dotColor = isDark
        ? DS.textPrimary.withValues(alpha: 0.7)
        : DS.onBrandPrimary.withValues(alpha: 0.7);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: bubbleColor,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
          bottomLeft: Radius.circular(4),
        ),
        boxShadow: DS.shadowSm,
        border: Border.all(color: isDark ? const Color(0xFF3A3A3A) : DS.neutral200),
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
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  width: 8,
                  height: 8,
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
