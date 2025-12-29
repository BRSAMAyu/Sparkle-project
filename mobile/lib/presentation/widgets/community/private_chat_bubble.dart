import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class PrivateChatBubble extends ConsumerStatefulWidget {

  const PrivateChatBubble({required this.message, super.key});
  final PrivateMessageInfo message;

  @override
  ConsumerState<PrivateChatBubble> createState() => _PrivateChatBubbleState();
}

class _PrivateChatBubbleState extends ConsumerState<PrivateChatBubble> with SingleTickerProviderStateMixin {
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
    final isMe = widget.message.sender.id == currentUser?.id;

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
                const SizedBox(width: DS.sm),
              ],
              Flexible(
                child: Column(
                  crossAxisAlignment: isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    _buildContent(context, isMe),
                    const SizedBox(height: 2),
                    if (isMe)
                      Text(
                        widget.message.isRead ? '已读' : '未读',
                        style: TextStyle(fontSize: 10, color: DS.brandPrimary70),
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
    );
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    if (widget.message.isRevoked) {
      return _buildRevokedBubble(isMe);
    }
    switch (widget.message.messageType) {
      case MessageType.taskShare:
      case MessageType.planShare:
      case MessageType.fragmentShare:
      case MessageType.capsuleShare:
      case MessageType.prismShare:
        return _buildShareBubble(context, isMe);
      case MessageType.text:
      default:
        return _buildTextBubble(context, isMe);
    }
  }

  Widget _buildRevokedBubble(bool isMe) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.neutral200),
      ),
      child: Text(
        isMe ? '你撤回了一条消息' : '对方撤回了一条消息',
        style: TextStyle(fontSize: 12, color: DS.neutral500),
      ),
    );

  Widget _buildTextBubble(BuildContext context, bool isMe) => Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: isMe ? DS.primaryBase : DS.brandPrimary,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(16),
          topRight: const Radius.circular(16),
          bottomLeft: isMe ? const Radius.circular(16) : const Radius.circular(4),
          bottomRight: isMe ? const Radius.circular(4) : const Radius.circular(16),
        ),
        boxShadow: isMe 
            ? [BoxShadow(color: DS.primaryBase.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 4))] 
            : DS.shadowSm,
        border: isMe ? null : Border.all(color: DS.neutral100),
      ),
      child: Text(
        widget.message.content ?? '',
        style: TextStyle(
          color: isMe ? DS.brandPrimary : DS.neutral900,
          fontSize: 16,
          height: 1.4,
        ),
      ),
    );

  Widget _buildShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final resourceType = (data['resource_type'] ?? _fallbackShareType()).toString();
    final title = (data['resource_title'] ?? widget.message.content ?? 'Shared item').toString();
    final summary = (data['resource_summary'] ?? '').toString();
    final comment = (data['comment'] ?? widget.message.content)?.toString();
    final meta = data['resource_meta'];

    final theme = _shareTheme(resourceType);
    final metaChips = _shareMetaChips(resourceType, meta);

    final card = Container(
      width: 240,
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            theme.color.withValues(alpha: isMe ? 0.22 : 0.16),
            theme.color.withValues(alpha: 0.06),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.message.replyToId != null) _buildQuotePreview(context, isMe),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: theme.color.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(theme.icon, size: 16, color: theme.color),
              ),
              const SizedBox(width: DS.sm),
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
          const SizedBox(height: DS.sm),
          Text(
            title,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 14,
              color: DS.textPrimary,
            ),
          ),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: DS.xs),
            Text(
              summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
          ],
          if (metaChips.isNotEmpty) ...[
            const SizedBox(height: DS.sm),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: metaChips
                  .map((label) => Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
            const SizedBox(height: DS.sm),
            Container(
              padding: const EdgeInsets.all(DS.sm),
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

  Widget _buildQuotePreview(BuildContext context, bool isMe) {
    final quoted = widget.message.quotedMessage;
    if (quoted == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: isMe ? DS.brandPrimary.withValues(alpha: 0.12) : DS.neutral100,
        borderRadius: BorderRadius.circular(8),
        border: Border(left: BorderSide(color: isMe ? DS.brandPrimary70 : DS.primaryBase, width: 3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            quoted.sender.displayName,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: isMe ? DS.brandPrimary.withValues(alpha: 0.9) : DS.neutral700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            quoted.content ?? '',
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

  Widget _buildAvatar(UserBrief user) => DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: DS.brandPrimary, width: 2),
        boxShadow: DS.shadowSm,
      ),
      child: CircleAvatar(
        radius: 16,
        backgroundImage: user.avatarUrl != null ? NetworkImage(user.avatarUrl!) : null,
        backgroundColor: DS.neutral200,
        child: user.avatarUrl == null
            ? Text(
                user.displayName.substring(0, 1).toUpperCase(),
                style: TextStyle(fontSize: 12, color: DS.neutral600),
              )
            : null,
      ),
    );
}

class _ShareTheme {
  _ShareTheme({required this.label, required this.icon, required this.color});

  final String label;
  final IconData icon;
  final Color color;
}
