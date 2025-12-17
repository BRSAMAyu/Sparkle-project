import 'dart:ui';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';

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
                    AppDesignTokens.primaryBase.withOpacity(0.05),
                    Colors.white.withOpacity(0.8),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: const Border(bottom: BorderSide(color: Colors.black12, width: 0.5)),
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
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'AI学习助手',
                  style: TextStyle(
                    color: AppDesignTokens.neutral900,
                    fontWeight: AppDesignTokens.fontWeightBold,
                    fontSize: AppDesignTokens.fontSizeBase,
                  ),
                ),
                Text(
                  '随时为你解答',
                  style: TextStyle(
                    color: AppDesignTokens.neutral600,
                    fontSize: AppDesignTokens.fontSizeXs,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.history, color: AppDesignTokens.neutral700),
            onPressed: () {
              // TODO: History
            },
          ),
          IconButton(
            icon: const Icon(Icons.add_comment_outlined, color: AppDesignTokens.neutral700),
            tooltip: 'New Chat',
            onPressed: () => ref.read(chatProvider.notifier).startNewSession(),
          ),
        ],
      ),
      body: Container(
        decoration: const BoxDecoration(
          color: AppDesignTokens.neutral50,
        ),
        child: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: messages.isEmpty && chatState.streamingContent.isEmpty
                    ? Center(
                        child: EmptyState.noChats(
                          onStartChat: () {
                            // Show quick starter prompts
                          },
                        ),
                      )
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
                   color: AppDesignTokens.error.withOpacity(0.1),
                   child: Text(
                     'Error: ${chatState.error}', 
                     style: const TextStyle(color: AppDesignTokens.error),
                     textAlign: TextAlign.center,
                   ),
                 ),
              ChatInput(
                enabled: !chatState.isSending,
                onSend: (text) => ref.read(chatProvider.notifier).sendMessage(text),
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
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.8,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(20),
            topRight: Radius.circular(20),
            bottomRight: Radius.circular(20),
            bottomLeft: Radius.circular(4),
          ),
          boxShadow: AppDesignTokens.shadowSm,
          border: Border.all(color: AppDesignTokens.neutral200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Flexible(
              child: Text(
                content,
                style: const TextStyle(
                  color: AppDesignTokens.neutral900,
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomRight: Radius.circular(20),
          bottomLeft: Radius.circular(4),
        ),
        boxShadow: AppDesignTokens.shadowSm,
        border: Border.all(color: AppDesignTokens.neutral200),
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
                  decoration: const BoxDecoration(
                    color: AppDesignTokens.neutral400,
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