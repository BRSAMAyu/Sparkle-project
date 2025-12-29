import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';
import 'package:sparkle/presentation/widgets/chat/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/presentation/widgets/chat/ai_status_indicator.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/galaxy/graphrag_visualizer.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final ScrollController _scrollController = ScrollController();
  ProviderSubscription<List<ChatMessageModel>>? _messagesSubscription;

  @override
  void initState() {
    super.initState();
    _messagesSubscription = ref.listenManual(chatProvider.select((state) => state.messages), (previous, next) {
      if (next.length > (previous?.length ?? 0)) {
        _scrollToBottom();
      }
    });
  }

  @override
  void dispose() {
    _messagesSubscription?.close();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.minScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
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
                    (isDark ? DS.deepSpaceStart : DS.brandPrimary).withValues(alpha: 0.8),
                    (isDark ? DS.deepSpaceEnd : DS.brandPrimary).withValues(alpha: 0.9),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: Border(bottom: BorderSide(color: isDark ? DS.brandPrimary.withValues(alpha: 0.1) : DS.brandPrimary.withValues(alpha: 0.05), width: 0.5)),
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
              child: Icon(Icons.auto_awesome, color: DS.brandPrimaryConst, size: 20),
            ),
            const SizedBox(width: DS.md),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'AI学习助手',
                  style: TextStyle(
                    color: isDark ? DS.brandPrimary : DS.neutral900,
                    fontWeight: DS.fontWeightBold,
                    fontSize: DS.fontSizeBase,
                  ),
                ),
                Text(
                  '随时为你解答',
                  style: TextStyle(
                    color: isDark ? DS.neutral400 : DS.neutral600,
                    fontSize: DS.fontSizeXs,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.history, color: isDark ? DS.brandPrimary70 : DS.neutral700),
            onPressed: () => _showHistoryBottomSheet(context),
          ),
          IconButton(
            icon: Icon(Icons.add_comment_outlined, color: isDark ? DS.brandPrimary70 : DS.neutral700),
            tooltip: 'New Chat',
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
          ),
        ],
      ),
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: isDark
            ? DS.deepSpaceGradient
            : LinearGradient(
                colors: [DS.neutral50, DS.brandPrimary],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
        ),
        child: Stack(
          children: [
            SafeArea(
              child: Column(
                children: [
                  if (chatState.isLoading)
                    LinearProgressIndicator(
                      backgroundColor: Colors.transparent,
                      valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
                      minHeight: 2,
                    ),
                  Expanded(
                child: messages.isEmpty && chatState.streamingContent.isEmpty && chatState.aiStatus == null && !chatState.isReasoningActive
                    ? _buildQuickActions(context)
                    : ListView.builder(
                        controller: _scrollController,
                        reverse: true,
                        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 20.0),
                        // 🆕 显示状态指示器、推理气泡、流式内容或消息
                        itemCount: messages.length +
                            (chatState.isSending ? 1 : 0) +
                            (chatState.aiStatus != null ? 1 : 0) +
                            (chatState.isReasoningActive ? 1 : 0),
                        itemBuilder: (context, index) {
                          // 1. 如果有 AI 状态更新，在最底部显示（reversed 模式下 index 为 0）
                          if (chatState.aiStatus != null && index == 0) {
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12.0),
                              child: AiStatusIndicator(
                                status: chatState.aiStatus,
                                details: chatState.aiStatusDetails,
                              ),
                            );
                          }

                          // 2. 🆕 如果正在显示推理过程，显示 Chain of Thought Bubble
                          final isStatusShowing = chatState.aiStatus != null;
                          final reasoningIndex = isStatusShowing ? 1 : 0;

                          if (chatState.isReasoningActive && index == reasoningIndex) {
                            final durationMs = chatState.reasoningStartTime != null
                                ? DateTime.now().millisecondsSinceEpoch - chatState.reasoningStartTime!
                                : null;

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12.0),
                              child: AgentReasoningBubble(
                                steps: chatState.reasoningSteps,
                                isThinking: true,
                                totalDurationMs: durationMs,
                              ),
                            );
                          }

                          // 3. 如果正在发送/接收，显示流式内容或打字指示器
                          final streamIndex = isStatusShowing ? (chatState.isReasoningActive ? 2 : 1) : (chatState.isReasoningActive ? 1 : 0);

                          if (chatState.isSending && index == streamIndex) {
                            // 如果有流式内容，显示它
                            if (chatState.streamingContent.isNotEmpty) {
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 12.0),
                                child: _StreamingBubble(content: chatState.streamingContent),
                              );
                            }

                            // 如果没有流式内容且也没有显示状态指示器，则显示通用打字指示器
                            if (!isStatusShowing && !chatState.isReasoningActive) {
                              return const Padding(
                                padding: EdgeInsets.only(bottom: 12.0),
                                child: _TypingIndicator(),
                              );
                            }

                            return const SizedBox.shrink();
                          }

                          // 4. 计算正式消息的索引
                          var msgIndex = index;
                          if (isStatusShowing) msgIndex--;
                          if (chatState.isReasoningActive) msgIndex--;
                          if (chatState.isSending) msgIndex--;

                          if (msgIndex < 0) return const SizedBox.shrink();

                          final adjustedIndex = messages.length - 1 - msgIndex;
                          if (adjustedIndex < 0 || adjustedIndex >= messages.length) {
                            return const SizedBox.shrink();
                          }

                          final message = messages[adjustedIndex];
                          return ChatBubble(message: message);
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
                  ChatInput(
                    enabled: !chatState.isSending,
                    onSend: (text, {replyToId}) => ref.read(chatProvider.notifier).sendMessage(text),
                  ),
                ],
              ),
            ),
            // 🔥 必杀技 A: GraphRAG 实时可视化
            if (chatState.graphragTrace != null)
              GraphRAGVisualizer(
                trace: chatState.graphragTrace,
              ),
          ],
        ),
      ),
    );
  }

  void _showHistoryBottomSheet(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.7,
        decoration: BoxDecoration(
          color: isDark ? DS.neutral900 : DS.brandPrimary,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: isDark ? DS.neutral700 : DS.neutral300,
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
                      color: isDark ? DS.brandPrimary : DS.neutral900,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: FutureBuilder<List<Map<String, dynamic>>>(
                future: ref.read(chatProvider.notifier).getRecentConversations(),
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  
                  if (snapshot.hasError) {
                    return Center(child: Text('加载失败: ${snapshot.error}'));
                  }
                  
                  final sessions = snapshot.data ?? [];
                  if (sessions.isEmpty) {
                    return const Center(child: Text('暂无历史记录'));
                  }
                  
                  return ListView.builder(
                    itemCount: sessions.length,
                    itemBuilder: (context, index) {
                      final session = sessions[index];
                      final isCurrent = session['id'] == ref.read(chatProvider).conversationId;
                      
                      return ListTile(
                        leading: Container(
                          padding: const EdgeInsets.all(DS.sm),
                          decoration: BoxDecoration(
                            color: isCurrent ? DS.primaryBase.withValues(alpha: 0.1) : (isDark ? DS.neutral800 : DS.neutral100),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.chat_bubble_outline_rounded,
                            size: 18,
                            color: isCurrent ? DS.primaryBase : DS.neutral500,
                          ),
                        ),
                        title: Text(
                          session['title'] ?? '未命名会话',
                          style: TextStyle(
                            color: isDark ? DS.brandPrimary : DS.neutral900,
                            fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                          ),
                        ),
                        subtitle: Text(
                          session['updated_at']?.split('T')[0] ?? '',
                          style: TextStyle(fontSize: 12, color: DS.neutral500),
                        ),
                        trailing: isCurrent ? Icon(Icons.check_circle, color: DS.primaryBase, size: 18) : null,
                        onTap: () {
                          Navigator.pop(context);
                          ref.read(chatProvider.notifier).loadConversationHistory(session['id']);
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
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.xxl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
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
                color: isDark ? DS.brandPrimary : DS.neutral900,
              ),
            ),
            const SizedBox(height: DS.sm),
            Text(
              '今天想做点什么？',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: isDark ? DS.neutral400 : DS.neutral600,
              ),
            ),
            const SizedBox(height: 40),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                _QuickActionChip(
                  icon: Icons.add_task_rounded,
                  label: '新建微任务',
                  color: DS.brandPrimaryConst,
                  onTap: () => ref.read(chatProvider.notifier).sendMessage('帮我创建一个新的微任务'),
                ),
                _QuickActionChip(
                  icon: Icons.calendar_month_rounded,
                  label: '生成长期计划',
                  color: Colors.purple,
                  onTap: () => ref.read(chatProvider.notifier).sendMessage('帮我生成一个长期学习计划'),
                ),
                _QuickActionChip(
                  icon: Icons.bug_report_rounded,
                  label: '错误归因',
                  color: DS.brandPrimaryConst,
                  onTap: () => ref.read(chatProvider.notifier).sendMessage('我想分析一下最近的错误原因'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickActionChip extends StatefulWidget {

  const _QuickActionChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  State<_QuickActionChip> createState() => _QuickActionChipState();
}

class _QuickActionChipState extends State<_QuickActionChip> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

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
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: isDark ? DS.neutral800 : DS.brandPrimary,
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
                  color: isDark ? DS.brandPrimary : DS.neutral900,
                  fontWeight: DS.fontWeightMedium,
                ),
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
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? DS.neutral800 : DS.brandPrimary,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(4),
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
                  color: isDark ? DS.brandPrimary : DS.neutral900,
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
    )..repeat(reverse: true);
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

class _TypingIndicatorState extends State<_TypingIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? DS.neutral800 : DS.brandPrimary,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
          bottomLeft: Radius.circular(4),
        ),
        boxShadow: DS.shadowSm,
        border: Border.all(color: isDark ? DS.neutral700 : DS.neutral200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (index) => AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              final delay = index * 0.2;
              final progress = ((_controller.value - delay) % 1.0).clamp(0.0, 1.0);
              final offset = sin(progress * pi) * 6;

              return Transform.translate(
                offset: Offset(0, -offset),
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: isDark ? DS.neutral400 : DS.neutral300,
                    shape: BoxShape.circle,
                  ),
                ),
              );
            },
          ),),
      ),
    );
  }
}
