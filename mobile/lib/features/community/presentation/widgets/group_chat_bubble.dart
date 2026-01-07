import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/chat/presentation/widgets/file_message_bubble.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';

class GroupChatBubble extends ConsumerStatefulWidget {
  const GroupChatBubble({
    required this.message,
    this.groupId,
    this.onRevoke,
    this.onQuote,
    this.onEdit,
    this.onReaction,
    this.onThread,
    super.key,
  });
  final MessageInfo message;
  final String? groupId;
  final Function(MessageInfo message)? onRevoke;
  final Function(MessageInfo message)? onQuote;
  final Function(MessageInfo message, String content)? onEdit;
  final Function(MessageInfo message, String emoji)? onReaction;
  final Function(MessageInfo message)? onThread;

  @override
  ConsumerState<GroupChatBubble> createState() => _GroupChatBubbleState();
}

class _GroupChatBubbleState extends ConsumerState<GroupChatBubble>
    with SingleTickerProviderStateMixin {
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

  void _showContextMenu(BuildContext context, bool isMe) {
    if (widget.message.isRevoked) return;

    // Allow revocation within 24 hours for own messages
    final canRevoke = isMe &&
        DateTime.now().difference(widget.message.createdAt).inHours < 24;

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (widget.onQuote != null)
                ListTile(
                  leading: const Icon(Icons.format_quote_rounded),
                  title: const Text('引用'),
                  onTap: () {
                    Navigator.pop(context);
                    widget.onQuote!(widget.message);
                  },
                ),
              ListTile(
                leading: const Icon(Icons.copy_rounded),
                title: const Text('复制'),
                onTap: () {
                  Clipboard.setData(
                      ClipboardData(text: widget.message.content ?? ''),);
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                        content: Text('已复制到剪贴板'),
                        duration: Duration(seconds: 1),),
                  );
                },
              ),
              if (widget.onThread != null)
                ListTile(
                  leading: const Icon(Icons.forum_outlined),
                  title: const Text('串联回复'),
                  onTap: () {
                    Navigator.pop(context);
                    widget.onThread!(widget.message);
                  },
                ),
              if (isMe &&
                  widget.onEdit != null &&
                  widget.message.messageType == MessageType.text)
                ListTile(
                  leading: const Icon(Icons.edit_rounded),
                  title: const Text('编辑'),
                  onTap: () {
                    Navigator.pop(context);
                    // Trigger edit flow (implementation dependent, but typically shows input)
                    // For now, we assume onEdit is called with new content from some dialog
                    // widget.onEdit!(widget.message, newContent);
                  },
                ),
              if (canRevoke && widget.onRevoke != null)
                ListTile(
                  leading: Icon(Icons.undo_rounded, color: DS.error),
                  title: Text('撤回', style: TextStyle(color: DS.error)),
                  onTap: () {
                    Navigator.pop(context);
                    widget.onRevoke!(widget.message);
                  },
                ),
              const SizedBox(height: DS.sm),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);
    final isMe = widget.message.sender?.id == currentUser?.id;
    final isSystem = widget.message.isSystemMessage;

    // Handle revoked messages
    if (widget.message.isRevoked) {
      return FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              isMe
                  ? '你撤回了一条消息'
                  : '${widget.message.sender?.displayName ?? "成员"}撤回了一条消息',
              style: TextStyle(fontSize: 12, color: DS.neutral400),
            ),
          ),
        ),
      );
    }

    if (isSystem) {
      return FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: DS.neutral200),
            ),
            child: Text(
              widget.message.content ?? '',
              style: TextStyle(fontSize: 12, color: DS.neutral600),
            ),
          ),
        ),
      );
    }

    final timeStr = DateFormat('HH:mm').format(widget.message.createdAt);

    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: GestureDetector(
          onLongPress: () => _showContextMenu(context, isMe),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
            child: Row(
              mainAxisAlignment:
                  isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (!isMe) ...[
                  _buildAvatar(widget.message.sender),
                  const SizedBox(width: DS.sm),
                ],
                Flexible(
                  child: Column(
                    crossAxisAlignment: isMe
                        ? CrossAxisAlignment.end
                        : CrossAxisAlignment.start,
                    children: [
                      if (!isMe && widget.message.sender != null)
                        Padding(
                          padding: const EdgeInsets.only(left: 4, bottom: 4),
                          child: Text(
                            widget.message.sender!.displayName,
                            style: TextStyle(
                              fontSize: 12,
                              color: DS.neutral500,
                            ),
                          ),
                        ),
                      _buildContent(context, isMe),
                      const SizedBox(height: DS.xs),
                      // Timestamp and read status
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              timeStr,
                              style:
                                  TextStyle(fontSize: 10, color: DS.neutral500),
                            ),
                            if (isMe && widget.message.readCount > 0) ...[
                              const SizedBox(width: DS.sm),
                              _buildReadByIndicator(),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                if (isMe) ...[
                  const SizedBox(width: DS.sm),
                  _buildAvatar(widget.message.sender),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildReadByIndicator() {
    final readBy = widget.message.readBy ?? [];
    if (readBy.isEmpty) return const SizedBox.shrink();

    final displayCount = readBy.length > 5 ? 5 : readBy.length;
    final remaining = readBy.length - 5;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Display first 5 avatars
        SizedBox(
          width: displayCount * 14.0 + 8,
          height: 20,
          child: Stack(
            children: [
              for (int i = 0; i < displayCount; i++)
                Positioned(
                  left: i * 12.0,
                  child: Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border:
                          Border.all(color: DS.brandPrimaryConst, width: 1.5),
                      color: DS.neutral200,
                    ),
                    child: ClipOval(
                      child: Image.network(
                        'https://api.dicebear.com/9.x/avataaars/png?seed=${readBy[i]}',
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Center(
                          child: Text(
                            '?',
                            style: TextStyle(fontSize: 8, color: DS.neutral500),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        // Show +N if more than 5
        if (remaining > 0) ...[
          Text(
            '+${readBy.length}',
            style: TextStyle(fontSize: 10, color: DS.info),
          ),
        ] else ...[
          Text(
            '${readBy.length}人已读',
            style: TextStyle(fontSize: 10, color: DS.info),
          ),
        ],
      ],
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    switch (widget.message.messageType) {
      case MessageType.checkin:
        return _buildCheckinBubble(context, isMe);
      case MessageType.taskShare:
        return _buildTaskShareBubble(context, isMe);
      case MessageType.fileShare:
        final data = FileMessageData.fromJson(widget.message.contentData ?? {});
        if (data.fileId.isEmpty) {
          return _buildTextBubble(context, isMe);
        }
        return FileMessageBubbleWithThumbnail(
          data: data,
          isMe: isMe,
          groupId: widget.groupId,
        );
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe);
    }
  }

  Widget _buildTextBubble(BuildContext context, bool isMe) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isMe ? DS.primaryBase : DS.brandPrimary,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft:
                isMe ? const Radius.circular(16) : const Radius.circular(4),
            bottomRight:
                isMe ? const Radius.circular(4) : const Radius.circular(16),
          ),
          boxShadow: isMe
              ? [
                  BoxShadow(
                      color: DS.primaryBase.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 4),),
                ]
              : DS.shadowSm,
          border: isMe ? null : Border.all(color: DS.neutral100),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.message.replyToId != null)
              _buildQuotePreview(context, isMe),
            Text(
              widget.message.content ?? '',
              style: TextStyle(
                color: isMe ? DS.brandPrimary : DS.neutral900,
                fontSize: 16,
                height: 1.4,
              ),
            ),
          ],
        ),
      );

  Widget _buildQuotePreview(BuildContext context, bool isMe) {
    final quoted = widget.message.quotedMessage;
    final quotedContent = quoted?.content ?? '引用的消息';
    final quotedSender = quoted?.sender?.displayName ?? '成员';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: isMe ? DS.brandPrimary.withValues(alpha: 0.15) : DS.neutral100,
        borderRadius: BorderRadius.circular(8),
        border: Border(
            left: BorderSide(
                color: isMe ? DS.brandPrimary70 : DS.primaryBase, width: 3,),),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (quoted != null)
            Text(
              quotedSender,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.bold,
                color: isMe
                    ? DS.brandPrimary.withValues(alpha: 0.9)
                    : DS.neutral700,
              ),
            ),
          if (quoted != null) const SizedBox(height: 2),
          Text(
            quotedContent,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color:
                  isMe ? DS.brandPrimary.withValues(alpha: 0.9) : DS.neutral600,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCheckinBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final flame = (data['flame_power'] as num?)?.toInt() ?? 0;
    final duration = (data['today_duration'] as num?)?.toInt() ?? 0;
    final streak = (data['streak'] as num?)?.toInt() ?? 0;

    return Container(
      width: 240,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: isMe
              ? [DS.brandPrimary.shade600, Colors.deepOrange.shade600]
              : [DS.brandPrimary.shade50, DS.brandPrimary.shade100],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: DS.brandPrimary.withValues(alpha: 0.3),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
        border: isMe ? null : Border.all(color: DS.brandPrimary.shade200),
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
              color: isMe
                  ? DS.brandPrimary.withValues(alpha: 0.1)
                  : DS.brandPrimary.withValues(alpha: 0.1),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: isMe
                            ? DS.brandPrimary.withValues(alpha: 0.2)
                            : DS.brandPrimary,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.bolt, color: DS.warning, size: 18),
                    ),
                    const SizedBox(width: DS.sm),
                    Text(
                      'Daily Check-in',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color:
                            isMe ? DS.brandPrimary : Colors.deepOrange.shade800,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.md),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildCheckinStat('Duration', '${duration}m', isMe),
                    _buildCheckinStat('Flame', '+$flame', isMe),
                    if (streak > 0)
                      _buildCheckinStat('Streak', '$streak 🔥', isMe),
                  ],
                ),
                if (widget.message.content != null &&
                    widget.message.content!.isNotEmpty) ...[
                  const SizedBox(height: DS.md),
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      color: isMe
                          ? DS.brandPrimary.withValues(alpha: 0.1)
                          : DS.brandPrimary.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      widget.message.content!,
                      style: TextStyle(
                        color: isMe
                            ? DS.brandPrimary.withValues(alpha: 0.9)
                            : Colors.brown.shade800,
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

  Widget _buildCheckinStat(String label, String value, bool isMe) => Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: isMe ? DS.brandPrimary : Colors.deepOrange.shade900,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: isMe ? DS.brandPrimary70 : Colors.deepOrange.shade700,
            ),
          ),
        ],
      );

  Widget _buildTaskShareBubble(BuildContext context, bool isMe) => Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isMe ? DS.brandPrimary.shade600 : DS.brandPrimary.shade50,
          borderRadius: BorderRadius.circular(16),
          boxShadow: DS.shadowSm,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.task_alt,
                color: isMe ? DS.brandPrimary : DS.brandPrimary,),
            const SizedBox(width: DS.sm),
            Flexible(
              child: Text(
                widget.message.content ?? 'Shared a task',
                style: TextStyle(
                    color: isMe ? DS.brandPrimary : DS.brandPrimary.shade900,),
              ),
            ),
          ],
        ),
      );

  Widget _buildAvatar(UserBrief? user) => DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: DS.brandPrimaryConst, width: 2),
          boxShadow: DS.shadowSm,
        ),
        child: SparkleAvatar(
          radius: 16,
          url: user?.avatarUrl,
          fallbackText: user?.displayName,
        ),
      );
}
