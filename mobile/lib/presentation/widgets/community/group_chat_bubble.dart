import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class GroupChatBubble extends ConsumerWidget {
  final MessageInfo message;

  const GroupChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final isMe = message.sender?.id == currentUser?.id;
    final isSystem = message.isSystemMessage;

    if (isSystem) {
      return Center(
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: Colors.grey.shade200,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            message.content ?? '',
            style: const TextStyle(fontSize: 12, color: Colors.grey),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
      child: Row(
        mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isMe) ...[
            _buildAvatar(message.sender),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                if (!isMe && message.sender != null)
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 4),
                    child: Text(
                      message.sender!.displayName,
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                  ),
                _buildContent(context, isMe),
              ],
            ),
          ),
          if (isMe) ...[
            const SizedBox(width: 8),
            _buildAvatar(message.sender),
          ],
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    switch (message.messageType) {
      case MessageType.checkin:
        return _buildCheckinBubble(context, isMe);
      case MessageType.taskShare:
        return _buildTaskShareBubble(context, isMe);
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe);
    }
  }

  Widget _buildTextBubble(BuildContext context, bool isMe) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isMe ? AppDesignTokens.primaryBase : Colors.white,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(16),
          topRight: const Radius.circular(16),
          bottomLeft: isMe ? const Radius.circular(16) : const Radius.circular(4),
          bottomRight: isMe ? const Radius.circular(4) : const Radius.circular(16),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Text(
        message.content ?? '',
        style: TextStyle(
          color: isMe ? Colors.white : Colors.black87,
          fontSize: 16,
        ),
      ),
    );
  }

  Widget _buildCheckinBubble(BuildContext context, bool isMe) {
    final data = message.contentData ?? {};
    final flame = data['flame_power'] ?? 0;
    final duration = data['today_duration'] ?? 0;
    final streak = data['streak'] ?? 0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isMe 
              ? [Colors.orange.shade400, Colors.deepOrange.shade400]
              : [Colors.orange.shade50, Colors.orange.shade100],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.local_fire_department, color: Colors.yellow, size: 20),
              const SizedBox(width: 4),
              Text(
                'Check-in!',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isMe ? Colors.white : Colors.deepOrange,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Studied $duration mins • +$flame Flame',
            style: TextStyle(
              fontSize: 12,
              color: isMe ? Colors.white70 : Colors.black87,
            ),
          ),
          if (streak > 0)
            Text(
              '$streak day streak! 🔥',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: isMe ? Colors.white : Colors.deepOrange,
              ),
            ),
          if (message.content != null && message.content!.isNotEmpty) ...[
             const SizedBox(height: 8),
             Text(
               message.content!,
               style: TextStyle(
                 color: isMe ? Colors.white : Colors.black87,
                 fontStyle: FontStyle.italic,
               ),
             ),
          ],
        ],
      ),
    );
  }

  Widget _buildTaskShareBubble(BuildContext context, bool isMe) {
    // Placeholder for task share
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isMe ? Colors.blue.shade100 : Colors.grey.shade100,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.task_alt),
          const SizedBox(width: 8),
          Text(message.content ?? 'Shared a task'),
        ],
      ),
    );
  }

  Widget _buildAvatar(UserBrief? user) {
    return CircleAvatar(
      radius: 16,
      backgroundImage: user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
      backgroundColor: Colors.grey.shade300,
      child: user?.avatarUrl == null
          ? Text(
              user?.displayName.substring(0, 1).toUpperCase() ?? '?',
              style: const TextStyle(fontSize: 12, color: Colors.black54),
            )
          : null,
    );
  }
}