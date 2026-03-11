import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

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

    return GraphiteScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
        ),
        title: Row(
          children: [
            if (_avatarUrl != null)
              Padding(
                padding: const EdgeInsets.only(right: DS.spacing8),
                child: SparkleAvatar(
                  url: _avatarUrl,
                  fallbackText: _displayName,
                ),
              ),
            Text(_displayName ?? context.l10n.privateChatDefaultTitle),
          ],
        ),
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            Expanded(
              child: chatState.when(
                data: (messages) {
                  if (messages.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.chat_bubble_outline,
                            size: DS.iconSize3xl,
                            color: DS.neutral300,
                          ),
                          const SizedBox(height: DS.spacing24),
                          Text(
                            context.l10n.privateChatEmptyPrompt,
                            style: TextStyle(
                              color: DS.neutral500,
                              fontSize: DS.fontSizeBase,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return ListView.builder(
                    reverse: true,
                    padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8, vertical: DS.spacing16),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final message = messages[index];
                      return ChatBubble(
                        message: message,
                        currentUserId: currentUser?.id,
                        onQuote: (msg) => setState(() =>
                            notifier.setQuote(msg as PrivateMessageInfo?)),
                        onRevoke: (msg) => notifier
                            .revokeMessage((msg as PrivateMessageInfo).id),
                      );
                    },
                  );
                },
                loading: () => const Center(child: LoadingIndicator()),
                error: (e, s) => Center(
                  child: CustomErrorWidget.page(
                    context: context,
                    message: e.toString(),
                    onRetry: () => ref
                        .read(privateChatProvider(widget.friendId).notifier)
                        .loadMessages(),
                  ),
                ),
              ),
            ),
            ChatInput(
              quotedMessage: notifier.quotedMessage,
              onCancelQuote: () => setState(() => notifier.setQuote(null)),
              onSend: (text, {replyToId}) =>
                  notifier.sendMessage(content: text, replyToId: replyToId),
            ),
          ],
        ),
      ),
    );
  }
}
