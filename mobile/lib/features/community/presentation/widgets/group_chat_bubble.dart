import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/presentation/widgets/file_message_bubble.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/widgets/share_cards/share_cards.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/features/file/file.dart';

class GroupChatBubble extends ConsumerStatefulWidget {
  const GroupChatBubble({
    required this.message,
    this.groupId,
    this.onRevoke,
    this.onQuote,
    this.onEdit,
    this.onReaction,
    this.onThread,
    this.onFavorite,
    this.onForward,
    this.onReport,
    super.key,
  });
  final MessageInfo message;
  final String? groupId;
  final void Function(MessageInfo message)? onRevoke;
  final void Function(MessageInfo message)? onQuote;
  final void Function(MessageInfo message, String content)? onEdit;
  final void Function(MessageInfo message, String emoji)? onReaction;
  final void Function(MessageInfo message)? onThread;
  final void Function(MessageInfo message)? onFavorite;
  final void Function(MessageInfo message)? onForward;
  final void Function(MessageInfo message)? onReport;

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

    unawaited(_controller.forward());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _showContextMenu(BuildContext context, bool isMe) {
    if (widget.message.isRevoked) return;
    final l10n = context.l10n;

    // Allow revocation within 24 hours for own messages
    final canRevoke = isMe &&
        DateTime.now().difference(widget.message.createdAt).inHours < 24;

    unawaited(
      showModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
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
                    title: Text(l10n.communityQuote),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onQuote!(widget.message);
                    },
                  ),
                ListTile(
                  leading: const Icon(Icons.copy_rounded),
                  title: Text(l10n.communityCopy),
                  onTap: () {
                    unawaited(
                      Clipboard.setData(
                        ClipboardData(text: widget.message.content ?? ''),
                      ),
                    );
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(l10n.communityCopiedToClipboard),
                        duration: const Duration(seconds: 1),
                      ),
                    );
                  },
                ),
                if (widget.onThread != null)
                  ListTile(
                    leading: const Icon(Icons.forum_outlined),
                    title: Text(l10n.communityThreadReply),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onThread!(widget.message);
                    },
                  ),
                if (widget.onFavorite != null)
                  ListTile(
                    leading: const Icon(Icons.bookmark_add_outlined),
                    title: const Text('收藏'),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onFavorite!(widget.message);
                    },
                  ),
                if (widget.onForward != null)
                  ListTile(
                    leading: const Icon(Icons.forward_rounded),
                    title: const Text('转发'),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onForward!(widget.message);
                    },
                  ),
                if (isMe &&
                    widget.onEdit != null &&
                    widget.message.messageType == MessageType.text)
                  ListTile(
                    leading: const Icon(Icons.edit_rounded),
                    title: Text(l10n.communityEdit),
                    onTap: () {
                      Navigator.pop(context);
                    },
                  ),
                if (canRevoke && widget.onRevoke != null)
                  ListTile(
                    leading: Icon(Icons.undo_rounded, color: DS.error),
                    title: Text(
                      l10n.communityRevoke,
                      style: TextStyle(color: DS.error),
                    ),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onRevoke!(widget.message);
                    },
                  ),
                if (!isMe && widget.onReport != null)
                  ListTile(
                    leading: Icon(Icons.flag_outlined, color: DS.error),
                    title: Text(
                      '举报',
                      style: TextStyle(color: DS.error),
                    ),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onReport!(widget.message);
                    },
                  ),
                const SizedBox(height: DS.sm),
              ],
            ),
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
                  ? context.l10n.communityRevokedOwnMessage
                  : context.l10n.communityRevokedUserMessage(
                      widget.message.sender?.displayName ??
                          context.l10n.communityMemberFallback,
                    ),
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
                      if (!isMe &&
                          (widget.message.sender != null ||
                              isCommunityAgentMessage(widget.message)))
                        Padding(
                          padding: const EdgeInsets.only(left: 4, bottom: 4),
                          child: Text(
                            widget.message.sender?.displayName ??
                                (isCommunityAgentMessage(widget.message)
                                    ? kCommunityAgentDisplayName
                                    : ''),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
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
    final readByUsers = widget.message.readByUsers ?? const <UserBrief>[];
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
                        _readAvatarUrl(
                          readerId: readBy[i],
                          readByUsers: readByUsers,
                        ),
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
            context.l10n.communityReadByCount(readBy.length),
            style: TextStyle(fontSize: 10, color: DS.info),
          ),
        ],
      ],
    );
  }

  String _readAvatarUrl({
    required String readerId,
    required List<UserBrief> readByUsers,
  }) {
    for (final user in readByUsers) {
      if (user.id == readerId && (user.avatarUrl?.trim().isNotEmpty ?? false)) {
        return user.avatarUrl!;
      }
    }
    return 'https://api.dicebear.com/9.x/avataaars/png?seed=$readerId';
  }

  Widget _buildContent(BuildContext context, bool isMe) {
    switch (widget.message.messageType) {
      case MessageType.checkin:
        return _buildCheckinBubble(context, isMe);
      case MessageType.taskShare:
        return _buildTaskShareBubble(context, isMe);
      case MessageType.planShare:
        return _buildPlanShareBubble(context, isMe);
      case MessageType.capsuleShare:
        return _buildCapsuleShareBubble(context, isMe);
      case MessageType.prismShare:
        return _buildPrismShareBubble(context, isMe);
      case MessageType.achievement:
        return _buildAchievementShareBubble(context, isMe);
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
          color: isMe ? DS.chatBubbleUser : DS.chatBubbleOther,
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
                    color: DS.chatBubbleUser.withValues(alpha: 0.24),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ]
              : DS.shadowSm,
          border: isMe ? null : Border.all(color: DS.borderSubtle),
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
                color: isMe ? DS.chatBubbleUserText : DS.chatBubbleOtherText,
                fontSize: 16,
                height: 1.4,
              ),
            ),
          ],
        ),
      );

  Widget _buildQuotePreview(BuildContext context, bool isMe) {
    final quoted = widget.message.quotedMessage;
    final quotedContent =
        quoted?.content ?? context.l10n.communityQuotedMessageFallback;
    final quotedSender =
        quoted?.sender?.displayName ?? context.l10n.communityMemberFallback;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: isMe
            ? Colors.white.withValues(alpha: 0.12)
            : DS.surfacePrimaryElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(
            color:
                isMe ? Colors.white.withValues(alpha: 0.52) : DS.brandSecondary,
            width: 3,
          ),
        ),
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
                    ? Colors.white.withValues(alpha: 0.9)
                    : DS.textSecondary,
              ),
            ),
          if (quoted != null) const SizedBox(height: 2),
          Text(
            quotedContent,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color: isMe
                  ? Colors.white.withValues(alpha: 0.84)
                  : DS.textSecondary,
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
              ? [
                  DS.chatBubbleUser,
                  Color.lerp(DS.chatBubbleUser, DS.brandSecondary, 0.32)!,
                ]
              : [
                  DS.surfacePrimaryElevated,
                  Color.lerp(DS.surfaceSecondary, DS.brandSecondary, 0.08)!,
                ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: (isMe ? DS.chatBubbleUser : DS.brandSecondary)
                .withValues(alpha: 0.18),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
        border: isMe ? null : Border.all(color: DS.borderSubtle),
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
                            ? Colors.white.withValues(alpha: 0.16)
                            : DS.brandSecondary.withValues(alpha: 0.14),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.bolt,
                        color: isMe ? Colors.white : DS.brandSecondary,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: DS.sm),
                    Text(
                      context.l10n.communityDailyCheckIn,
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: isMe ? Colors.white : DS.textPrimary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.md),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildCheckinStat(
                      context.l10n.communityDurationLabel,
                      '${duration}m',
                      isMe,
                    ),
                    _buildCheckinStat(
                      context.l10n.communityFlameLabel,
                      '+$flame',
                      isMe,
                    ),
                    if (streak > 0)
                      _buildCheckinStat(
                        context.l10n.communityStreakLabel,
                        '$streak 🔥',
                        isMe,
                      ),
                  ],
                ),
                if (widget.message.content != null &&
                    widget.message.content!.isNotEmpty) ...[
                  const SizedBox(height: DS.md),
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      color: isMe
                          ? Colors.white.withValues(alpha: 0.12)
                          : DS.surfaceOverlay,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      widget.message.content!,
                      style: TextStyle(
                        color: isMe
                            ? Colors.white.withValues(alpha: 0.9)
                            : DS.textSecondary,
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
              color: isMe ? Colors.white : DS.textPrimary,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: isMe
                  ? Colors.white.withValues(alpha: 0.72)
                  : DS.textSecondary,
            ),
          ),
        ],
      );

  Widget _buildTaskShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final payload = UniversalSharePayload(
      contentType: ShareableContentType.taskCompletion,
      resourceId: data['task_id'] as String? ?? '',
      title: data['title'] as String? ?? widget.message.content ?? '任务',
      subtitle: data['description'] as String?,
      metadata: {
        'duration': data['duration'],
        'points': data['points'],
        'streak': data['streak'],
        'completed_at': data['completed_at'],
      },
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      child: TaskShareCardFactory.fromPayload(
        payload,
        isCompact: false,
        onTap: () => _handleSharedResourceTap(payload),
      ),
    );
  }

  Widget _buildPlanShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final progress = data['progress'] as double?;
    final payload = UniversalSharePayload(
      contentType: ShareableContentType.planProgress,
      resourceId: data['plan_id'] as String? ?? '',
      title: data['title'] as String? ?? widget.message.content ?? '计划',
      subtitle: progress != null ? '进度: ${(progress * 100).toStringAsFixed(0)}%' : null,
      metadata: {
        'progress': progress,
        'completed_tasks': data['completed_tasks'],
        'total_tasks': data['total_tasks'],
        'milestones': data['milestones'],
        'deadline': data['deadline'],
      },
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      child: PlanShareCardFactory.fromPayload(
        payload,
        isCompact: false,
        onTap: () => _handleSharedResourceTap(payload),
      ),
    );
  }

  Widget _buildCapsuleShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final payload = UniversalSharePayload(
      contentType: ShareableContentType.capsule,
      resourceId: data['capsule_id'] as String? ?? '',
      title: data['title'] as String? ?? widget.message.content ?? '时光胶囊',
      subtitle: data['summary'] as String?,
      metadata: {
        'type': data['type'],
        'depth': data['depth'],
        'word_count': data['word_count'],
        'tags': data['tags'],
        'created_at': data['created_at'],
      },
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      child: CapsuleShareCardFactory.fromPayload(
        payload,
        isCompact: false,
        onTap: () => _handleSharedResourceTap(payload),
      ),
    );
  }

  Widget _buildPrismShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    return _buildRichCardWrapper(
      isMe: isMe,
      child: _buildPrismPreviewCard(context, isMe, data),
    );
  }

  Widget _buildAchievementShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    return _buildRichCardWrapper(
      isMe: isMe,
      child: _buildAchievementPreviewCard(context, isMe, data),
    );
  }

  Widget _buildRichCardWrapper({
    required bool isMe,
    required Widget child,
  }) =>
      Container(
        constraints: const BoxConstraints(maxWidth: 280),
        decoration: BoxDecoration(
          color: isMe ? DS.chatBubbleUser : DS.chatBubbleOther,
          borderRadius: BorderRadius.circular(16),
          boxShadow: isMe
              ? [
                  BoxShadow(
                    color: DS.chatBubbleUser.withValues(alpha: 0.24),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ]
              : DS.shadowSm,
          border: isMe ? null : Border.all(color: DS.borderSubtle),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: child,
        ),
      );

  Widget _buildPrismPreviewCard(
    BuildContext context,
    bool isMe,
    Map<String, dynamic> data,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.prismPurple.withValues(alpha: 0.15),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    Icons.psychology,
                    color: isMe ? Colors.white : DS.prismPurple,
                    size: 20,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '认知棱镜',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: isMe
                              ? Colors.white.withValues(alpha: 0.7)
                              : DS.textTertiary,
                        ),
                      ),
                      Text(
                        data['title'] as String? ?? '学习模式分析',
                        style: TextStyle(
                          fontWeight: DS.fontWeightBold,
                          color: isMe ? Colors.white : DS.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (data['patterns'] != null) ...[
              const SizedBox(height: DS.sm),
              Wrap(
                spacing: DS.xs,
                children: (data['patterns'] as List)
                    .take(3)
                    .map<Widget>((p) => Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.sm,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: isMe
                                ? Colors.white.withValues(alpha: 0.15)
                                : DS.prismPurple.withValues(alpha: 0.1),
                            borderRadius: DS.borderRadius4,
                          ),
                          child: Text(
                            p.toString(),
                            style: TextStyle(
                              fontSize: DS.fontSizeXs,
                              color: isMe ? Colors.white : DS.prismPurple,
                            ),
                          ),
                        ))
                    .toList(),
              ),
            ],
          ],
        ),
      );

  Widget _buildAchievementPreviewCard(
    BuildContext context,
    bool isMe,
    Map<String, dynamic> data,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.15),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    Icons.emoji_events,
                    color: isMe ? Colors.white : DS.warning,
                    size: 20,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '成就解锁',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: isMe
                              ? Colors.white.withValues(alpha: 0.7)
                              : DS.textTertiary,
                        ),
                      ),
                      Text(
                        data['name'] as String? ?? '新成就',
                        style: TextStyle(
                          fontWeight: DS.fontWeightBold,
                          color: isMe ? Colors.white : DS.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (data['rarity'] != null) ...[
              const SizedBox(height: DS.sm),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.sm,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: _getRarityColor(data['rarity'] as String)
                      .withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius4,
                ),
                child: Text(
                  data['rarity'] as String,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightBold,
                    color: _getRarityColor(data['rarity'] as String),
                  ),
                ),
              ),
            ],
          ],
        ),
      );

  Color _getRarityColor(String rarity) => switch (rarity.toLowerCase()) {
        'legendary' => DS.warning,
        'epic' => DS.prismPurple,
        'rare' => DS.info,
        _ => DS.neutral400,
      };

  void _handleSharedResourceTap(UniversalSharePayload payload) {
    final deepLink = payload.deepLink;
    if (deepLink.isNotEmpty) {
      // 使用深链接服务导航，而非复制链接
      if (!DeepLinkService.handleDeepLink(context, deepLink)) {
        // 导航失败时回退到复制链接
        UniversalShareService().copyDeepLink(deepLink);
        AppFeedback.info(context, '链接已复制');
      }
    }
  }

  Widget _buildAvatar(UserBrief? user) {
    final resolvedUser = user ??
        (isCommunityAgentMessage(widget.message) ? buildCommunityAgentUser() : null);
    return DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: DS.brandPrimaryConst, width: 2),
        boxShadow: DS.shadowSm,
      ),
      child: SparkleAvatar(
        radius: 16,
        url: resolvedUser?.avatarUrl,
        fallbackText: resolvedUser?.displayName,
      ),
    );
  }
}
