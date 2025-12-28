import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/community/group_chat_bubble.dart';

class GroupChatScreen extends ConsumerStatefulWidget {

  const GroupChatScreen({required this.groupId, super.key});
  final String groupId;

  @override
  ConsumerState<GroupChatScreen> createState() => _GroupChatScreenState();
}

class _GroupChatScreenState extends ConsumerState<GroupChatScreen> {
  MessageInfo? _quotedMessage;

  void _showCheckinDialog() {
    final durationController = TextEditingController(text: '60');
    final messageController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Daily Check-in'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: durationController,
              decoration: InputDecoration(
                labelText: 'Duration (minutes)',
                suffixText: 'min',
              ),
              keyboardType: TextInputType.number,
            ),
            SizedBox(height: DS.lg),
            TextField(
              controller: messageController,
              decoration: const InputDecoration(
                labelText: 'Message (optional)',
                hintText: 'What did you learn today?',
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(label: 'Cancel', onPressed: () => Navigator.pop(context)),
          TextButton(
            onPressed: () async {
              final duration = int.tryParse(durationController.text) ?? 0;
              final message = messageController.text;
              Navigator.pop(context);

              try {
                await ref.read(groupDetailProvider(widget.groupId).notifier).checkin(duration, message);
                // Refresh chat to see the checkin message
                ref.invalidate(groupChatProvider(widget.groupId));
                
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Checked in successfully!')));
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
              }
            },
            child: const Text('Check-in'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(groupChatProvider(widget.groupId));
    final groupInfoState = ref.watch(groupDetailProvider(widget.groupId));

    return Scaffold(
      appBar: AppBar(
        title: groupInfoState.when(
          data: (group) => InkWell(
            onTap: () {
              // Go to details? No, we are linked from details.
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(group.name, style: TextStyle(fontSize: 16)),
                Text('${group.memberCount} members', style: TextStyle(fontSize: 12, color: DS.brandPrimary54)),
              ],
            ),
          ),
          loading: () => Text('Chat'),
          error: (_, __) => Text('Chat'),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.local_fire_department, color: DS.brandPrimary),
            onPressed: _showCheckinDialog,
            tooltip: 'Check-in',
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
               // Assuming we might be deep linked, ensuring we can go to details
               // Actually we came from details usually. 
               // But let's allow going to details if we are just in chat view
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: chatState.when(
              data: (messages) {
                if (messages.isEmpty) {
                  return Center(child: Text('No messages yet. Say hi!'));
                }
                return ListView.builder(
                  reverse: true,
                  padding: EdgeInsets.all(DS.lg),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final message = messages[index];
                    return GroupChatBubble(
                      message: message,
                      onQuote: (msg) => setState(() {
                        _quotedMessage = msg;
                        ref.read(groupChatProvider(widget.groupId).notifier).setQuote(msg);
                      }),
                      onRevoke: (msg) => ref.read(groupChatProvider(widget.groupId).notifier).revokeMessage(msg.id),
                    );
                  },
                );
              },
              loading: () => const Center(child: LoadingIndicator()),
              error: (e, s) => Center(
                child: CustomErrorWidget.page(
                  message: e.toString(),
                  onRetry: () => ref.read(groupChatProvider(widget.groupId).notifier).refresh(),
                ),
              ),
            ),
          ),
          ChatInput(
            quotedMessage: _quotedMessage != null
                ? PrivateMessageInfo(
                    id: _quotedMessage!.id,
                    sender: _quotedMessage!.sender ?? UserBrief(id: '', username: 'Unknown'),
                    receiver: UserBrief(id: '', username: ''),
                    messageType: _quotedMessage!.messageType,
                    content: _quotedMessage!.content,
                    createdAt: _quotedMessage!.createdAt,
                    updatedAt: _quotedMessage!.updatedAt,
                    isRevoked: _quotedMessage!.isRevoked,
                    isRead: false,
                  )
                : null,
            onCancelQuote: () => setState(() {
              _quotedMessage = null;
              ref.read(groupChatProvider(widget.groupId).notifier).setQuote(null);
            }),
            onSend: (text, {replyToId}) {
              final actualReplyId = _quotedMessage?.id ?? replyToId;
              setState(() => _quotedMessage = null);
              return ref.read(groupChatProvider(widget.groupId).notifier).sendMessage(
                content: text,
                replyToId: actualReplyId,
              );
            },
          ),
        ],
      ),
    );
  }
}
