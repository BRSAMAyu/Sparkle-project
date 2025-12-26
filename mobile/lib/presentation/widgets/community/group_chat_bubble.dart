import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

class GroupChatBubble extends ConsumerStatefulWidget {
  final MessageInfo message;

  const GroupChatBubble({required this.message, super.key});

  @override
  ConsumerState<GroupChatBubble> createState() => _GroupChatBubbleState();
}

class _GroupChatBubbleState extends ConsumerState<GroupChatBubble> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);
    final isMe = widget.message.sender?.id == currentUser?.id;
    final isSystem = widget.message.isSystemMessage;

    if (isSystem) {
      return FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: AppDesignTokens.neutral100,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppDesignTokens.neutral200),
            ),
            child: Text(
              widget.message.content ?? '',
              style: const TextStyle(fontSize: 12, color: AppDesignTokens.neutral600),
            ),
          ),
        ),
      );
    }

    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
          child: Row(
            mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isMe) ...[
                _buildAvatar(widget.message.sender),
                const SizedBox(width: 8),
              ],
              Flexible(
                child: Column(
                  crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    if (!isMe && widget.message.sender != null)
                      Padding(
                        padding: const EdgeInsets.only(left: 4, bottom: 4),
                        child: Text(
                          widget.message.sender!.displayName,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppDesignTokens.neutral500,
                          ),
                        ),
                      ),
                    _buildContent(context, isMe),
                    // Timestamp (optional, could be added)
                  ],
                ),
              ),
              if (isMe) ...[
                const SizedBox(width: 8),
                _buildAvatar(widget.message.sender),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    switch (widget.message.messageType) {
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
        boxShadow: isMe 
            ? [BoxShadow(color: AppDesignTokens.primaryBase.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 4))] 
            : AppDesignTokens.shadowSm,
        border: isMe ? null : Border.all(color: AppDesignTokens.neutral100),
      ),
      child: Text(
        widget.message.content ?? '',
        style: TextStyle(
          color: isMe ? Colors.white : AppDesignTokens.neutral900,
          fontSize: 16,
          height: 1.4,
        ),
      ),
    );
  }

  Widget _buildCheckinBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final flame = data['flame_power'] ?? 0;
    final duration = data['today_duration'] ?? 0;
    final streak = data['streak'] ?? 0;

    return Container(
      width: 240,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isMe 
              ? [Colors.orange.shade600, Colors.deepOrange.shade600]
              : [Colors.orange.shade50, Colors.orange.shade100],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.orange.withValues(alpha: 0.3),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
        border: isMe ? null : Border.all(color: Colors.orange.shade200),
      ),
      child: Stack(
        children: [
          // Background decoration
          Positioned(
            right: -10,
            bottom: -10,
            child: Icon(
              Icons.local_fire_department,
              size: 80,
              color: isMe ? Colors.white.withValues(alpha: 0.1) : Colors.orange.withValues(alpha: 0.1),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: isMe ? Colors.white.withValues(alpha: 0.2) : Colors.white,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.bolt, color: Colors.yellow, size: 18),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Daily Check-in',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: isMe ? Colors.white : Colors.deepOrange.shade800,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildCheckinStat('Duration', '${duration}m', isMe),
                    _buildCheckinStat('Flame', '+$flame', isMe),
                    if (streak > 0) _buildCheckinStat('Streak', '$streak 🔥', isMe),
                  ],
                ),
                if (widget.message.content != null && widget.message.content!.isNotEmpty) ...[
                   const SizedBox(height: 12),
                   Container(
                     padding: const EdgeInsets.all(8),
                     decoration: BoxDecoration(
                       color: isMe ? Colors.black.withValues(alpha: 0.1) : Colors.white.withValues(alpha: 0.6),
                       borderRadius: BorderRadius.circular(8),
                     ),
                     child: Text(
                       widget.message.content!,
                       style: TextStyle(
                         color: isMe ? Colors.white.withValues(alpha: 0.9) : Colors.brown.shade800,
                         fontStyle: FontStyle.italic,
                         fontSize: 13,
                       ),
                     ),
                   ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCheckinStat(String label, String value, bool isMe) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
            color: isMe ? Colors.white : Colors.deepOrange.shade900,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: isMe ? Colors.white70 : Colors.deepOrange.shade700,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskShareBubble(BuildContext context, bool isMe) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isMe ? Colors.blue.shade600 : Colors.blue.shade50,
        borderRadius: BorderRadius.circular(16),
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.task_alt, color: isMe ? Colors.white : Colors.blue),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              widget.message.content ?? 'Shared a task',
              style: TextStyle(color: isMe ? Colors.white : Colors.blue.shade900),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAvatar(UserBrief? user) {
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 2),
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: SparkleAvatar(
        radius: 16,
        url: user?.avatarUrl,
        fallbackText: user?.displayName,
      ),
    );
  }
}
