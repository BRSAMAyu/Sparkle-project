import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/community/private_chat_bubble.dart';
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
                  padding: const EdgeInsets.all(16),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final message = messages[index];
                    return PrivateChatBubble(message: message);
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
            onSend: (text) {
              return ref.read(privateChatProvider(widget.friendId).notifier).sendMessage(content: text);
            },
          ),
        ],
      ),
    );
  }
}
