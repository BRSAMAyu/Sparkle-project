import 'dart:ui';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';

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
    ref.listenManual(chatProvider.select((state) => state.messages), (previous, next) {
      if (next.length > (previous?.length ?? 0)) {
        _scrollToBottom();
      }
    });
  }

  @override
  void dispose() {
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
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

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
                    (isDark ? AppDesignTokens.deepSpaceStart : Colors.white).withValues(alpha: 0.8),
                    (isDark ? AppDesignTokens.deepSpaceEnd : Colors.white).withValues(alpha: 0.9),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: Border(bottom: BorderSide(color: isDark ? Colors.white.withValues(alpha: 0.1) : Colors.black.withValues(alpha: 0.05), width: 0.5)),
              ),
            ),
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(
                gradient: AppDesignTokens.secondaryGradient,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'AI学习助手',
                  style: TextStyle(
                    color: isDark ? Colors.white : AppDesignTokens.neutral900,
                    fontWeight: AppDesignTokens.fontWeightBold,
                    fontSize: AppDesignTokens.fontSizeBase,
                  ),
                ),
                Text(
                  '随时为你解答',
                  style: TextStyle(
                    color: isDark ? AppDesignTokens.neutral400 : AppDesignTokens.neutral600,
                    fontSize: AppDesignTokens.fontSizeXs,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.history, color: isDark ? Colors.white70 : AppDesignTokens.neutral700),
            onPressed: () {
              // TODO: History
            },
          ),
          IconButton(
            icon: Icon(Icons.add_comment_outlined, color: isDark ? Colors.white70 : AppDesignTokens.neutral700),
            tooltip: 'New Chat',
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
          ),
        ],
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: isDark 
            ? AppDesignTokens.deepSpaceGradient 
            : const LinearGradient(
                colors: [AppDesignTokens.neutral50, Colors.white],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: messages.isEmpty && chatState.streamingContent.isEmpty
                    ? _buildQuickActions(context)
                    : ListView.builder(
                        controller: _scrollController,
                        reverse: true,
                        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 20.0),
                        // 🆕 显示流式内容或加载指示器
                        itemCount: messages.length + (chatState.isSending ? 1 : 0),
                        itemBuilder: (context, index) {
                          if (chatState.isSending && index == 0) {
                            // 如果有流式内容，显示它；否则显示加载指示器
                            if (chatState.streamingContent.isNotEmpty) {
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 12.0),
                                child: _StreamingBubble(content: chatState.streamingContent),
                              );
                            }
                            return const Padding(
                              padding: EdgeInsets.only(bottom: 12.0),
                              child: _TypingIndicator(),
                            );
                          }

                          // Adjust index if we have a loading indicator at 0
                          final msgIndex = chatState.isSending ? index - 1 : index;
                          final message = messages[messages.length - 1 - msgIndex];
                          return ChatBubble(message: message);
                        },
                      ),
              ),
              if (chatState.error != null)
                 Container(
                   width: double.infinity,
                   padding: const EdgeInsets.all(8.0),
                   color: AppDesignTokens.error.withValues(alpha: 0.1),
                   child: Text(
                     'Error: ${chatState.error}', 
                     style: const TextStyle(color: AppDesignTokens.error),
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
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppDesignTokens.primaryBase.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.auto_awesome, size: 48, color: AppDesignTokens.primaryBase),
            ),
            const SizedBox(height: 24),
            Text(
              '你好，我是你的 AI 导师',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : AppDesignTokens.neutral900,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '今天想做点什么？',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: isDark ? AppDesignTokens.neutral400 : AppDesignTokens.neutral600,
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
                  color: Colors.blue,
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
                  color: Colors.orange,
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
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickActionChip({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

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
        duration: const Duration(milliseconds: 100),
        curve: Curves.easeInOut,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: isDark ? AppDesignTokens.neutral800 : Colors.white,
            borderRadius: BorderRadius.circular(20),
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
              Icon(widget.icon, size: 18, color: widget.color),
              const SizedBox(width: 8),
              Text(
                widget.label,
                style: TextStyle(
                  color: isDark ? Colors.white : AppDesignTokens.neutral900,
                  fontWeight: FontWeight.w500,
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
  final String content;

  const _StreamingBubble({required this.content});

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isDark ? AppDesignTokens.neutral800 : Colors.white,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(4),
          ),
          boxShadow: AppDesignTokens.shadowSm,
          border: Border.all(color: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Flexible(
              child: Text(
                content,
                style: TextStyle(
                  color: isDark ? Colors.white : AppDesignTokens.neutral900,
                  fontSize: AppDesignTokens.fontSizeBase,
                ),
              ),
            ),
            const SizedBox(width: 4),
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
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _animation,
      child: Container(
        width: 2,
        height: 16,
        color: AppDesignTokens.primaryBase,
      ),
    );
  }
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
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? AppDesignTokens.neutral800 : Colors.white,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
          bottomLeft: Radius.circular(4),
        ),
        boxShadow: AppDesignTokens.shadowSm,
        border: Border.all(color: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral200),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (index) {
          return AnimatedBuilder(
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
                    color: isDark ? AppDesignTokens.neutral400 : AppDesignTokens.neutral300,
                    shape: BoxShape.circle,
                  ),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}