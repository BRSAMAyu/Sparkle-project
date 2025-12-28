import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/community/community_widgets.dart';
import 'package:sparkle/core/design/sparkle_theme.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String id;
  final bool isGroup;

  const ChatScreen({required this.id, required this.isGroup, super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  Widget build(BuildContext context) {
    final messagesAsync = widget.isGroup 
        ? ref.watch(groupChatProvider(widget.id))
        : ref.watch(privateChatProvider(widget.id));
        
    final pendingNonces = widget.isGroup
        ? ref.watch(groupChatProvider(widget.id).notifier).pendingNonces
        : ref.watch(privateChatProvider(widget.id).notifier).pendingNonces;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.isGroup ? '学习小组' : '好友对话', style: const TextStyle(fontSize: 16)),
            const Row(
              children: [
                TypingIndicator(),
                SizedBox(width: DS.sm),
                Text('有人正在输入...', style: TextStyle(fontSize: 10, color: DS.brandPrimary)),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: messagesAsync.when(
              data: (messages) => ListView.builder(
                controller: _scrollController,
                reverse: true,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                itemCount: messages.length,
                itemBuilder: (context, index) {
                  final m = messages[index];
                  final bool isMe;
                  final String content;
                  final DateTime createdAt;
                  final String msgId;

                  if (m is MessageInfo) {
                    isMe = m.sender?.id != null; // Simplified logic for demo
                    content = m.content ?? '';
                    createdAt = m.createdAt;
                    msgId = m.id;
                  } else if (m is PrivateMessageInfo) {
                    isMe = m.sender.id != widget.id;
                    content = m.content ?? '';
                    createdAt = m.createdAt;
                    msgId = m.id;
                  } else {
                    return const SizedBox.shrink();
                  }
                  
                  return ChatBubble(
                    content: content,
                    isMe: isMe,
                    time: createdAt,
                    isSent: !pendingNonces.contains(msgId), 
                  );
                },
              ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('加载失败: $e')),
            ),
          ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: const BoxDecoration(
        color: DS.brandPrimary,
        boxShadow: [BoxShadow(color: DS.brandPrimary12, blurRadius: 4)],
      ),
      child: SafeArea(
        child: Row(
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: DS.brandPrimary[100],
                  borderRadius: BorderRadius.circular(24),
                ),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TextField(
                  controller: _controller,
                  decoration: const InputDecoration(
                    hintText: '发送消息...',
                    border: InputBorder.none,
                  ),
                ),
              ),
            ),
            const SizedBox(width: DS.sm),
            IconButton.filled(
              onPressed: _sendMessage,
              icon: const Icon(Icons.send),
              style: IconButton.styleFrom(backgroundColor: SparkleTheme.primary),
            ),
          ],
        ),
      ),
    );
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    
    if (widget.isGroup) {
      ref.read(groupChatProvider(widget.id).notifier).sendMessage(content: text);
    } else {
      ref.read(privateChatProvider(widget.id).notifier).sendMessage(content: text);
    }
    
    _controller.clear();
    _scrollController.animateTo(0, duration: SparkleTheme.fast, curve: SparkleTheme.curve);
  }
}
