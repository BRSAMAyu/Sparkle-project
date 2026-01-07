import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/presentation/widgets/group_chat_bubble.dart';

class ThreadSheet extends ConsumerStatefulWidget {
  const ThreadSheet(
      {required this.groupId, required this.rootMessage, super.key,});

  final String groupId;
  final MessageInfo rootMessage;

  @override
  ConsumerState<ThreadSheet> createState() => _ThreadSheetState();
}

class _ThreadSheetState extends ConsumerState<ThreadSheet> {
  List<MessageInfo> _messages = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadThread();
  }

  Future<void> _loadThread() async {
    setState(() => _loading = true);
    final messages = await ref
        .read(groupChatProvider(widget.groupId).notifier)
        .getThreadMessages(
          widget.rootMessage.id,
        );
    if (!mounted) return;
    setState(() {
      _messages = messages;
      _loading = false;
    });
  }

  Future<void> _sendReply(String content) async {
    await ref.read(groupChatProvider(widget.groupId).notifier).sendMessage(
          content: content,
          threadRootId: widget.rootMessage.id,
        );
    await _loadThread();
  }

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.only(top: DS.lg),
          child: Column(
            children: [
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.neutral300,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: DS.sm),
              Text('线程讨论', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: DS.md),
              Expanded(
                child: _loading
                    ? const Center(child: LoadingIndicator())
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: DS.lg),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          final message = _messages[index];
                          return GroupChatBubble(
                            message: message,
                            groupId: widget.groupId,
                            onRevoke: (msg) => ref
                                .read(
                                    groupChatProvider(widget.groupId).notifier,)
                                .revokeMessage(msg.id),
                            onEdit: (msg, content) => ref
                                .read(
                                    groupChatProvider(widget.groupId).notifier,)
                                .editMessage(msg.id, content),
                            onReaction: (msg, emoji) => ref
                                .read(
                                    groupChatProvider(widget.groupId).notifier,)
                                .toggleReaction(msg.id, emoji),
                          );
                        },
                      ),
              ),
              ChatInput(
                hintText: '回复线程...',
                onSend: (text, {replyToId}) => _sendReply(text),
              ),
            ],
          ),
        ),
      );
}
