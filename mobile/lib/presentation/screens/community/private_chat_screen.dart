import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';

class PrivateChatScreen extends ConsumerStatefulWidget {
  final String friendId;
  final String friendName;

  const PrivateChatScreen({
    required this.friendId,
    required this.friendName,
    super.key,
  });

  @override
  ConsumerState<PrivateChatScreen> createState() => _PrivateChatScreenState();
}

class _PrivateChatScreenState extends ConsumerState<PrivateChatScreen> {
  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(privateChatProvider(widget.friendId));
    final notifier = ref.read(privateChatProvider(widget.friendId).notifier);
    final currentUser = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.friendName),
      ),
      body: Column(
        children: [
          Expanded(
            child: chatState.when(
              data: (messages) {
                if (messages.isEmpty) {
                  return const Center(child: Text('Start a conversation!'));
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
            onSend: (text, {replyToId}) {
              return notifier.sendMessage(content: text, replyToId: replyToId);
            },
          ),
        ],
      ),
    );
  }
}
