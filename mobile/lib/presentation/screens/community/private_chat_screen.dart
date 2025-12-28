import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

class PrivateChatScreen extends ConsumerStatefulWidget {

  const PrivateChatScreen({
    required this.friendId,
    this.friendName,
    super.key,
  });
  final String friendId;
  final String? friendName;

  @override
  ConsumerState<PrivateChatScreen> createState() => _PrivateChatScreenState();
}

class _PrivateChatScreenState extends ConsumerState<PrivateChatScreen> {
  String? _displayName;
  String? _avatarUrl;

  @override
  void initState() {
    super.initState();
    _displayName = widget.friendName;
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(privateChatProvider(widget.friendId));
    final notifier = ref.read(privateChatProvider(widget.friendId).notifier);
    final currentUser = ref.watch(currentUserProvider);

    // Try to get friend info from messages if name not provided
    chatState.whenData((messages) {
      if (_displayName == null && messages.isNotEmpty) {
        final friendMsg = messages.firstWhere(
          (m) => m.sender.id == widget.friendId,
          orElse: () => messages.first,
        );
        if (friendMsg.sender.id == widget.friendId) {
          _displayName = friendMsg.sender.displayName;
          _avatarUrl = friendMsg.sender.avatarUrl;
        } else if (friendMsg.receiver.id == widget.friendId) {
          _displayName = friendMsg.receiver.displayName;
          _avatarUrl = friendMsg.receiver.avatarUrl;
        }
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            if (_avatarUrl != null)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: SparkleAvatar(radius: 16, url: _avatarUrl, fallbackText: _displayName),
              ),
            Text(_displayName ?? '聊天'),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: chatState.when(
              data: (messages) {
                if (messages.isEmpty) {
                  return const Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.chat_bubble_outline, size: 48, color: AppDesignTokens.neutral300),
                        SizedBox(height: DS.lg),
                        Text('开始对话吧!', style: TextStyle(color: AppDesignTokens.neutral500)),
                      ],
                    ),
                  );
                }
                return ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 16),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final message = messages[index];
                    return ChatBubble(
                      message: message,
                      currentUserId: currentUser?.id,
                      onQuote: (msg) => setState(() => notifier.setQuote(msg)),
                      onRevoke: (msg) => notifier.revokeMessage(msg.id),
                    );
                  },
                );
              },
              loading: () => const Center(child: LoadingIndicator()),
              error: (e, s) => Center(
                child: CustomErrorWidget.page(
                  message: e.toString(),
                  onRetry: () => ref.read(privateChatProvider(widget.friendId).notifier).loadMessages(),
                ),
              ),
            ),
          ),
          ChatInput(
            quotedMessage: notifier.quotedMessage,
            onCancelQuote: () => setState(() => notifier.setQuote(null)),
            onSend: (text, {replyToId}) => notifier.sendMessage(content: text, replyToId: replyToId),
          ),
        ],
      ),
    );
  }
}
