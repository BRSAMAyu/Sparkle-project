import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

class GroupChatBubble extends ConsumerStatefulWidget {

  const GroupChatBubble({
    required this.message,
    this.onRevoke,
    this.onQuote,
    this.onEdit,
    this.onReaction,
    this.onThread,
    super.key,
  });
  final MessageInfo message;
  final Function(MessageInfo message)? onRevoke;
  final Function(MessageInfo message)? onQuote;
  final void Function(MessageInfo message, String newContent)? onEdit;
  final void Function(MessageInfo message, String emoji)? onReaction;
  final void Function(MessageInfo message)? onThread;

  @override
  ConsumerState<GroupChatBubble> createState() => _GroupChatBubbleState();
}

class _GroupChatBubbleState extends ConsumerState<GroupChatBubble> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  static const List<String> _quickReactions = ['👍', '❤️', '😂', '😮', '🎯', '🔥'];

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

  void _showEditDialog(BuildContext context) {
    if (widget.onEdit == null || widget.message.isRevoked) return;
    final controller = TextEditingController(text: widget.message.content ?? '');
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('编辑消息'),
        content: TextField(
          controller: controller,
          maxLines: 5,
          decoration: const InputDecoration(hintText: '输入新的内容'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('取消')),
          TextButton(
            onPressed: () {
              final text = controller.text.trim();
              if (text.isNotEmpty) {
                widget.onEdit?.call(widget.message, text);
              }
              Navigator.pop(context);
            },
            child: const Text('保存'),
          ),
        ],
      ),
    );
  }

  void _showReactionPicker(BuildContext context) {
    if (widget.onReaction == null || widget.message.isRevoked) return;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.md, horizontal: DS.lg),
            child: Wrap(
              spacing: DS.md,
              children: _quickReactions.map((emoji) {
                return GestureDetector(
                  onTap: () {
                    Navigator.pop(context);
                    widget.onReaction?.call(widget.message, emoji);
                  },
                  child: Text(emoji, style: const TextStyle(fontSize: 26)),
                );
              }).toList(),
            ),
          ),
        ),
      ),
    );
  }

  void _showContextMenu(BuildContext context, bool isMe) {
    if (widget.message.isRevoked) return;

    // Allow revocation within 24 hours for own messages
    final canRevoke = isMe && DateTime.now().difference(widget.message.createdAt).inHours < 24;
    final canEdit = isMe && widget.message.messageType == MessageType.text;

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
              if (canEdit && widget.onEdit != null)
                ListTile(
                  leading: const Icon(Icons.edit_outlined),
                  title: const Text('编辑'),
                  onTap: () {
                    Navigator.pop(context);
                    _showEditDialog(context);
                  },
                ),
              ListTile(
                leading: const Icon(Icons.copy_rounded),
                title: const Text('复制'),
                onTap: () {
                  Clipboard.setData(ClipboardData(text: widget.message.content ?? ''));
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('已复制到剪贴板'), duration: Duration(seconds: 1)),
                  );
                },
              ),
              if (widget.onReaction != null)
                ListTile(
                  leading: const Icon(Icons.emoji_emotions_outlined),
                  title: const Text('表情'),
                  onTap: () {
                    Navigator.pop(context);
                    _showReactionPicker(context);
                  },
                ),
              if (widget.onThread != null)
                ListTile(
                  leading: const Icon(Icons.forum_outlined),
                  title: const Text('查看线程'),
                  onTap: () {
                    Navigator.pop(context);
                    widget.onThread!(widget.message);
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
              SizedBox(height: DS.sm),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);
    final currentUserId = currentUser?.id;
    final isAgent = isCommunityAgentMessage(widget.message);
    final isMe = widget.message.sender?.id == currentUserId && !isAgent;
    final isSystem = widget.message.isSystemMessage && !isAgent;
    final isMentioned = currentUserId != null && (widget.message.mentionUserIds?.contains(currentUserId) ?? false);

    // Handle revoked messages
    if (widget.message.isRevoked) {
      return FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 12),
            child: Text(
              isMe ? '你撤回了一条消息' : '${widget.message.sender?.displayName ?? "成员"}撤回了一条消息',
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
            margin: EdgeInsets.symmetric(vertical: 8),
            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 4),
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
            onDoubleTap: widget.onReaction == null
                ? null
                : () => widget.onReaction!(widget.message, '❤️'),
            onLongPress: () => _showContextMenu(context, isMe),
            child: Padding(
            padding: EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
            child: Row(
              mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (!isMe) ...[
                  _buildAvatar(isAgent ? buildCommunityAgentUser() : widget.message.sender),
                  SizedBox(width: DS.sm),
                ],
                Flexible(
                  child: Column(
                    crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                    children: [
                      if (!isMe && (widget.message.sender != null || isAgent))
                        Padding(
                          padding: EdgeInsets.only(left: 4, bottom: 4),
                          child: Text(
                            isAgent
                                ? kCommunityAgentDisplayName
                                : widget.message.sender!.displayName,
                            style: TextStyle(
                              fontSize: 12,
                              color: DS.neutral500,
                            ),
                          ),
                        ),
                      _buildContent(context, isMe, isAgent, isMentioned),
                      if (widget.message.reactions != null && widget.message.reactions!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: DS.xs),
                          child: _buildReactionRow(currentUserId),
                        ),
                      SizedBox(height: DS.xs),
                      // Timestamp and read status
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (widget.message.isEdited) ...[
                              Text('已编辑', style: TextStyle(fontSize: 10, color: DS.neutral400)),
                              const SizedBox(width: 6),
                            ],
                            Text(
                              timeStr,
                              style: TextStyle(fontSize: 10, color: DS.neutral500),
                            ),
                            if (isMe && widget.message.readCount > 0) ...[
                              SizedBox(width: DS.sm),
                              _buildReadByIndicator(),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                if (isMe) ...[
                  SizedBox(width: DS.sm),
                  _buildAvatar(isAgent ? buildCommunityAgentUser() : widget.message.sender),
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
                      border: Border.all(color: DS.brandPrimaryConst, width: 1.5),
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

  Widget _buildReactionRow(String? currentUserId) {
    final reactions = widget.message.reactions ?? {};
    if (reactions.isEmpty) return const SizedBox.shrink();
    return Wrap(
      spacing: 6,
      children: reactions.entries.map((entry) {
        final users = List<String>.from(entry.value as List? ?? <String>[]);
        final isMine = currentUserId != null && users.contains(currentUserId);
        return GestureDetector(
          onTap: widget.onReaction == null ? null : () => widget.onReaction!(widget.message, entry.key),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: isMine ? DS.brandPrimary.withValues(alpha: 0.15) : DS.neutral100,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: isMine ? DS.brandPrimary : DS.neutral200),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(entry.key, style: const TextStyle(fontSize: 12)),
                const SizedBox(width: 4),
                Text('${users.length}', style: TextStyle(fontSize: 11, color: DS.neutral600)),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildContent(BuildContext context, bool isMe, bool isAgent, bool isMentioned) {
    switch (widget.message.messageType) {
      case MessageType.checkin:
        return _buildCheckinBubble(context, isMe);
      case MessageType.taskShare:
      case MessageType.planShare:
      case MessageType.fragmentShare:
      case MessageType.capsuleShare:
      case MessageType.prismShare:
        return _buildShareBubble(context, isMe, isMentioned);
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe, isAgent, isMentioned);
    }
  }

  Widget _buildTextBubble(BuildContext context, bool isMe, bool isAgent, bool isMentioned) => Container(
      padding: EdgeInsets.all(DS.md),
      decoration: isAgent && !isMe
          ? BoxDecoration(
              gradient: DS.secondaryGradient,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomLeft: const Radius.circular(4),
                bottomRight: const Radius.circular(16),
              ),
              boxShadow: [
                BoxShadow(color: DS.brandSecondary.withValues(alpha: 0.3), blurRadius: 10, offset: Offset(0, 4)),
              ],
              border: isMentioned
                  ? Border.all(color: DS.brandPrimary, width: 1.5)
                  : Border.all(color: DS.brandSecondary.withValues(alpha: 0.2)),
            )
          : BoxDecoration(
              color: isMe ? DS.primaryBase : DS.brandPrimary,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomLeft: isMe ? Radius.circular(16) : const Radius.circular(4),
                bottomRight: isMe ? Radius.circular(4) : const Radius.circular(16),
              ),
              boxShadow: isMe
                  ? [BoxShadow(color: DS.primaryBase.withValues(alpha: 0.3), blurRadius: 8, offset: Offset(0, 4))]
                  : DS.shadowSm,
              border: isMentioned
                  ? Border.all(color: DS.brandPrimary, width: 1.5)
                  : (isMe ? null : Border.all(color: DS.neutral100)),
            ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isAgent)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.auto_awesome, size: 14, color: isMe ? DS.brandPrimary : DS.brandPrimaryConst),
                  const SizedBox(width: 6),
                  Text(
                    'AI助手',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isMe ? DS.brandPrimary : DS.brandPrimaryConst,
                    ),
                  ),
                ],
              ),
            ),
          if (widget.message.replyToId != null) _buildQuotePreview(context, isMe),
          Text(
            widget.message.content ?? '',
            style: TextStyle(
              color: isMe ? DS.brandPrimary : (isAgent ? DS.brandPrimaryConst : DS.neutral900),
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
      margin: EdgeInsets.only(bottom: 8),
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: isMe ? DS.brandPrimary.withValues(alpha: 0.15) : DS.neutral100,
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: isMe ? DS.brandPrimary70 : DS.primaryBase, width: 3)),
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
                color: isMe ? DS.brandPrimary.withValues(alpha: 0.9) : DS.neutral700,
              ),
            ),
          if (quoted != null) SizedBox(height: 2),
          Text(
            quotedContent,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color: isMe ? DS.brandPrimary.withValues(alpha: 0.9) : DS.neutral600,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
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
              ? [DS.brandPrimary.shade600, DS.warning.shade600]  // 使用设计系统警告色
              : [DS.brandPrimary.shade50, DS.brandPrimary.shade100],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: DS.brandPrimary.withValues(alpha: 0.3),
            blurRadius: 10,
            offset: Offset(0, 4),
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
              color: isMe ? DS.brandPrimary.withValues(alpha: 0.1) : DS.brandPrimary.withValues(alpha: 0.1),
            ),
          ),
          Padding(
            padding: EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: isMe ? DS.brandPrimary.withValues(alpha: 0.2) : DS.brandPrimary,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.bolt, color: DS.warning, size: 18),
                    ),
                    SizedBox(width: DS.sm),
                    Text(
                      'Daily Check-in',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: isMe ? DS.brandPrimary : DS.warning.shade800,  // 使用设计系统警告色
                      ),
                    ),
                  ],
                ),
                SizedBox(height: DS.md),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildCheckinStat('Duration', '${duration}m', isMe),
                    _buildCheckinStat('Flame', '+$flame', isMe),
                    if (streak > 0) _buildCheckinStat('Streak', '$streak 🔥', isMe),
                  ],
                ),
                if (widget.message.content != null && widget.message.content!.isNotEmpty) ...[
                   SizedBox(height: DS.md),
                   Container(
                     padding: EdgeInsets.all(DS.sm),
                     decoration: BoxDecoration(
                       color: isMe ? DS.brandPrimary.withValues(alpha: 0.1) : DS.brandPrimary.withValues(alpha: 0.6),
                       borderRadius: BorderRadius.circular(8),
                     ),
                     child: Text(
                       widget.message.content!,
                       style: TextStyle(
                         color: isMe ? DS.brandPrimary.withValues(alpha: 0.9) : DS.textPrimary,  // 使用设计系统主要文本色
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
            color: isMe ? DS.brandPrimary : DS.warning.shade900,  // 使用设计系统警告色
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: isMe ? DS.brandPrimary70 : DS.warning.shade700,  // 使用设计系统警告色
          ),
        ),
      ],
    );

  Widget _buildShareBubble(BuildContext context, bool isMe, bool isMentioned) {
    final data = widget.message.contentData ?? {};
    final resourceType = (data['resource_type'] ?? _fallbackShareType()).toString();
    final title = (data['resource_title'] ?? widget.message.content ?? 'Shared item').toString();
    final summary = (data['resource_summary'] ?? '').toString();
    final comment = (data['comment'] ?? widget.message.content)?.toString();
    final meta = data['resource_meta'];

    final theme = _shareTheme(resourceType);
    final metaChips = _shareMetaChips(resourceType, meta);

    final card = Container(
      width: 260,
      padding: EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.color.withValues(alpha: isMe ? 0.25 : 0.18),
            theme.color.withValues(alpha: 0.06),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isMentioned ? DS.brandPrimary : theme.color.withValues(alpha: 0.3),
          width: isMentioned ? 1.4 : 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: theme.color.withValues(alpha: 0.18),
            blurRadius: 10,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.message.replyToId != null) _buildQuotePreview(context, isMe),
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: theme.color.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(theme.icon, size: 16, color: theme.color),
              ),
              SizedBox(width: DS.sm),
              Text(
                theme.label,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                  color: theme.color,
                ),
              ),
            ],
          ),
          SizedBox(height: DS.sm),
          Text(
            title,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 15,
              color: DS.textPrimary,
            ),
          ),
          if (summary.isNotEmpty) ...[
            SizedBox(height: DS.xs),
            Text(
              summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
          ],
          if (metaChips.isNotEmpty) ...[
            SizedBox(height: DS.sm),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: metaChips
                  .map((label) => Container(
                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: theme.color.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          label,
                          style: TextStyle(fontSize: 10, color: theme.color),
                        ),
                      ))
                  .toList(),
            ),
          ],
          if (comment != null && comment.isNotEmpty && comment != title) ...[
            SizedBox(height: DS.sm),
            Container(
              padding: EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                comment,
                style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: DS.textPrimary,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: () => _openSharedResource(context, data),
      child: card,
    );
  }

  _ShareTheme _shareTheme(String resourceType) {
    switch (resourceType) {
      case 'plan':
        return _ShareTheme(
          label: '计划分享',
          icon: Icons.flag_outlined,
          color: DS.info,
        );
      case 'curiosity_capsule':
        return _ShareTheme(
          label: '好奇心胶囊',
          icon: Icons.lightbulb_outline,
          color: DS.prismGreen,
        );
      case 'cognitive_prism_pattern':
        return _ShareTheme(
          label: '认知棱镜',
          icon: Icons.diamond_outlined,
          color: DS.prismPurple,
        );
      case 'cognitive_fragment':
        return _ShareTheme(
          label: '认知碎片',
          icon: Icons.auto_awesome,
          color: DS.prismPurple,
        );
      case 'task':
      default:
        return _ShareTheme(
          label: '任务卡',
          icon: Icons.task_alt,
          color: DS.warning,
        );
    }
  }

  List<String> _shareMetaChips(String resourceType, dynamic meta) {
    if (meta is! Map) {
      return [];
    }
    final chips = <String>[];
    if (resourceType == 'plan') {
      final progress = meta['progress'];
      final targetDate = meta['target_date'];
      if (progress is num) {
        chips.add('${(progress * 100).round()}%');
      }
      if (targetDate is String && targetDate.isNotEmpty) {
        chips.add(targetDate.split('T').first);
      }
      if (meta['subject'] is String && (meta['subject'] as String).isNotEmpty) {
        chips.add(meta['subject']);
      }
    } else if (resourceType == 'curiosity_capsule') {
      final subject = meta['related_subject'];
      if (subject is String && subject.isNotEmpty) {
        chips.add(subject);
      }
      if (meta['related_task_id'] != null) {
        chips.add('linked task');
      }
    } else if (resourceType == 'cognitive_prism_pattern') {
      final patternType = meta['pattern_type'];
      if (patternType is String && patternType.isNotEmpty) {
        chips.add(patternType);
      }
      final frequency = meta['frequency'];
      if (frequency != null) {
        chips.add('x$frequency');
      }
    } else if (resourceType == 'cognitive_fragment') {
      final sourceType = meta['source_type'];
      if (sourceType is String && sourceType.isNotEmpty) {
        chips.add(sourceType);
      }
      final severity = meta['severity'];
      if (severity != null) {
        chips.add('S$severity');
      }
    } else {
      final minutes = meta['estimated_minutes'];
      if (minutes != null) {
        chips.add('${minutes}m');
      }
      final difficulty = meta['difficulty'];
      if (difficulty != null) {
        chips.add('L$difficulty');
      }
      final status = meta['status'];
      if (status is String && status.isNotEmpty) {
        chips.add(status);
      }
    }
    return chips;
  }

  String _fallbackShareType() {
    switch (widget.message.messageType) {
      case MessageType.planShare:
        return 'plan';
      case MessageType.fragmentShare:
        return 'cognitive_fragment';
      case MessageType.capsuleShare:
        return 'curiosity_capsule';
      case MessageType.prismShare:
        return 'cognitive_prism_pattern';
      case MessageType.taskShare:
      default:
        return 'task';
    }
  }

  void _openSharedResource(BuildContext context, Map<String, dynamic> data) {
    final resourceType = (data['resource_type'] ?? '').toString();
    final resourceId = (data['resource_id'] ?? '').toString();

    if (resourceId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('资源信息不完整')),
      );
      return;
    }

    switch (resourceType) {
      case 'task':
        context.push('/tasks/$resourceId');
        return;
      case 'plan':
        context.push('/plans/$resourceId');
        return;
      case 'curiosity_capsule':
        context.push('/curiosity-capsule?highlight=$resourceId');
        return;
      case 'cognitive_prism_pattern':
        context.push('/cognitive/patterns?highlight=$resourceId');
        return;
      default:
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('暂无可跳转的详情页')),
        );
    }
  }

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

class _ShareTheme {
  _ShareTheme({required this.label, required this.icon, required this.color});

  final String label;
  final IconData icon;
  final Color color;
}
