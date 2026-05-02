import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/presentation/widgets/file_message_bubble.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/share_cards/share_cards.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

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
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: DS.motionDuration(SparkleMotionToken.standard),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _scaleAnimation = Tween<double>(begin: 0.985, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
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
      showSensoryModalBottomSheet<void>(
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
                      SparkleSnackBar.info(
                        l10n.communityCopiedToClipboard,
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
                    title: Text(context.l10n.communityFavorite),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onFavorite!(widget.message);
                    },
                  ),
                if (widget.onForward != null)
                  ListTile(
                    leading: const Icon(Icons.forward_rounded),
                    title: Text(context.l10n.communityForward),
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
                      context.l10n
                          .communityReport, // TODO: i18n - this is inside a Text widget already using style
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
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: GestureDetector(
            onLongPress: () => _showContextMenu(context, isMe),
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(vertical: 8.0, horizontal: 8.0),
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
                        _buildReactions(context),
                        const SizedBox(height: DS.xs),
                        // Timestamp and read status
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                timeStr,
                                style: TextStyle(
                                    fontSize: 10, color: DS.neutral500),
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
      ),
    );
  }

  Widget _buildReactions(BuildContext context) {
    final reactions = widget.message.reactions;
    if (reactions == null || reactions.isEmpty) return const SizedBox.shrink();

    final entries = reactions.entries.where((e) {
      final v = e.value;
      if (v is int) return v > 0;
      if (v is List) return v.isNotEmpty;
      return false;
    }).toList();

    if (entries.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: DS.xs),
      child: Wrap(
        spacing: DS.xs,
        runSpacing: DS.xs,
        children: entries.map((e) {
          final count =
              e.value is int ? e.value as int : (e.value as List).length;
          return GestureDetector(
            onTap: widget.onReaction != null
                ? () => widget.onReaction!(widget.message, e.key)
                : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(e.key, style: const TextStyle(fontSize: 13)),
                  const SizedBox(width: 3),
                  Text(
                    '$count',
                    style: TextStyle(fontSize: 11, color: DS.textSecondary),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
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
                      child: SparkleNetworkImage(
                        imageUrl: _readAvatarUrl(
                          readerId: readBy[i],
                          readByUsers: readByUsers,
                        ),
                        fit: BoxFit.cover,
                        width: 18,
                        height: 18,
                        errorWidget: Center(
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
            _buildTextContent(context, isMe),
          ],
        ),
      );

  Widget _buildTextContent(BuildContext context, bool isMe) {
    final rawContent = isCommunityAgentMessage(widget.message)
        ? normalizeCommunityAgentOutput(widget.message.content ?? '')
        : widget.message.content ?? '';
    final textColor = isMe ? DS.chatBubbleUserText : DS.chatBubbleOtherText;
    return SparkleMarkdown(
      content: rawContent,
      textColor: textColor,
      codeBackgroundColor:
          isMe ? DS.neutral0.withValues(alpha: 0.12) : DS.surfaceTertiary,
      linkColor: isMe ? DS.neutral0 : DS.brandPrimary,
      contentRole: SparkleMarkdownRole.chatBubble,
    );
  }

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
            ? DS.neutral0.withValues(alpha: 0.12)
            : DS.surfacePrimaryElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(
            color:
                isMe ? DS.neutral0.withValues(alpha: 0.52) : DS.brandSecondary,
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
                fontWeight: DS.fontWeightBold,
                color: isMe
                    ? DS.neutral0.withValues(alpha: 0.9)
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
              color:
                  isMe ? DS.neutral0.withValues(alpha: 0.84) : DS.textSecondary,
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
                            ? DS.neutral0.withValues(alpha: 0.16)
                            : DS.brandSecondary.withValues(alpha: 0.14),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        Icons.bolt,
                        color: isMe ? DS.neutral0 : DS.brandSecondary,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: DS.sm),
                    Text(
                      context.l10n.communityDailyCheckIn,
                      style: TextStyle(
                        fontWeight: DS.fontWeightBold,
                        fontSize: 14,
                        color: isMe ? DS.neutral0 : DS.textPrimary,
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
                        '$streak 天',
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
                          ? DS.neutral0.withValues(alpha: 0.12)
                          : DS.surfaceOverlay,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      widget.message.content!,
                      style: TextStyle(
                        color: isMe
                            ? DS.neutral0.withValues(alpha: 0.9)
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
              fontWeight: DS.fontWeightBold,
              fontSize: 16,
              color: isMe ? DS.neutral0 : DS.textPrimary,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color:
                  isMe ? DS.neutral0.withValues(alpha: 0.72) : DS.textSecondary,
            ),
          ),
        ],
      );

  Widget _buildTaskShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final sharedResourceId = data['shared_resource_id']?.toString();
    final meta = (data['resource_meta'] as Map<String, dynamic>?) ?? {};
    final payload = UniversalSharePayload(
      contentType: ShareableContentType.taskCompletion,
      resourceId: data['resource_id'] as String? ?? '',
      title: data['resource_title'] as String? ??
          widget.message.content ??
          context.l10n.communityTaskFallback,
      subtitle: data['resource_summary'] as String?,
      metadata: {
        'duration': meta['estimated_minutes'],
        'completed_at': meta['completed_at'],
      },
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      onTap: () => _handleSharedResourceTap(payload),
      child: TaskShareCardFactory.fromPayload(
        payload,
        onTap: () => _handleSharedResourceTap(payload),
        sharedResourceId: sharedResourceId,
        onAdopt: sharedResourceId == null
            ? null
            : () => _handleAdopt(context, sharedResourceId, 'task'),
      ),
    );
  }

  Widget _buildPlanShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final sharedResourceId = data['shared_resource_id']?.toString();
    final meta = (data['resource_meta'] as Map<String, dynamic>?) ?? {};
    final progress = (meta['progress'] as num?)?.toDouble();
    final payload = UniversalSharePayload(
      contentType: ShareableContentType.planProgress,
      resourceId: data['resource_id'] as String? ?? '',
      title: data['resource_title'] as String? ??
          widget.message.content ??
          context.l10n.communityPlanFallback,
      subtitle: progress != null
          ? '进度: ${(progress * 100).toStringAsFixed(0)}%'
          : null,
      metadata: {
        'progress': progress,
        'deadline': meta['target_date'],
      },
    );

    return _buildRichCardWrapper(
      isMe: isMe,
      onTap: () => _handleSharedResourceTap(payload),
      child: PlanShareCardFactory.fromPayload(
        payload,
        onTap: () => _handleSharedResourceTap(payload),
        sharedResourceId: sharedResourceId,
        onAdopt: sharedResourceId == null
            ? null
            : () => _handleAdopt(context, sharedResourceId, 'plan'),
      ),
    );
  }

  Widget _buildCapsuleShareBubble(BuildContext context, bool isMe) {
    final data = widget.message.contentData ?? {};
    final sharedResourceType = data['resource_type'] as String?;
    if (sharedResourceType == 'knowledge_node') {
      final payload = UniversalSharePayload(
        contentType: ShareableContentType.knowledgeNode,
        resourceId: data['resource_id'] as String? ?? '',
        title: data['resource_title'] as String? ??
            data['title'] as String? ??
            widget.message.content ??
            (context.isChinese ? '知识节点' : 'Knowledge node'),
        subtitle:
            data['resource_summary'] as String? ?? data['summary'] as String?,
        metadata: {
          ...data,
          ...((data['resource_meta'] as Map<String, dynamic>?) ?? const {}),
        },
      );

      return _buildRichCardWrapper(
        isMe: isMe,
        onTap: () => _handleSharedResourceTap(payload),
        child: NodeShareCardFactory.fromPayload(
          payload,
          onTap: () => _handleSharedResourceTap(payload),
        ),
      );
    }
    if (sharedResourceType == 'seed_library' ||
        sharedResourceType == 'seed_item') {
      return _buildRichCardWrapper(
        isMe: isMe,
        child: _buildGenericSeedShareCard(isMe, data),
      );
    }

    final payload = UniversalSharePayload(
      contentType: ShareableContentType.capsule,
      resourceId:
          data['resource_id'] as String? ?? data['capsule_id'] as String? ?? '',
      title: data['resource_title'] as String? ??
          data['title'] as String? ??
          widget.message.content ??
          (context.isChinese ? '时光胶囊' : 'Time capsule'),
      subtitle:
          data['resource_summary'] as String? ?? data['summary'] as String?,
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
      onTap: () => _handleSharedResourceTap(payload),
      child: CapsuleShareCardFactory.fromPayload(
        payload,
        onTap: () => _handleSharedResourceTap(payload),
      ),
    );
  }

  Widget _buildGenericSeedShareCard(bool isMe, Map<String, dynamic> data) {
    final resourceType = data['resource_type'] as String? ?? 'seed_item';
    final title = data['resource_title'] as String? ??
        widget.message.content ??
        (resourceType == 'seed_library'
            ? context.l10n.communitySeedLibrary
            : context.l10n.communitySeedContent);
    final summary = data['resource_summary'] as String?;

    return Container(
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
                  color: DS.brandPrimary.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  resourceType == 'seed_library'
                      ? Icons.inventory_2
                      : Icons.auto_stories,
                  color: isMe ? DS.neutral0 : DS.brandPrimary,
                  size: 20,
                ),
              ),
              const SizedBox(width: DS.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontWeight: DS.fontWeightBold,
                        color: isMe ? DS.neutral0 : DS.textPrimary,
                      ),
                    ),
                    Text(
                      resourceType == 'seed_library'
                          ? context.l10n.communitySeedLibraryShare
                          : context.l10n.communitySeedContentShare,
                      style: TextStyle(
                        fontSize: 12,
                        color: isMe
                            ? DS.neutral0.withValues(alpha: 0.72)
                            : DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (summary != null && summary.isNotEmpty) ...[
            const SizedBox(height: DS.sm),
            Text(
              summary,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 13,
                color: isMe
                    ? DS.neutral0.withValues(alpha: 0.92)
                    : DS.textSecondary,
              ),
            ),
          ],
        ],
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

  Future<void> _handleAdopt(
    BuildContext context,
    String sharedResourceId,
    String fallbackResourceType,
  ) async {
    try {
      final result = await ref
          .read(communityShareRepositoryProvider)
          .adoptResource(sharedResourceId: sharedResourceId);
      if (!context.mounted) return;
      AppFeedback.success(context, context.l10n.communityAdoptedRedirecting);
      final resourceType =
          result['resource_type']?.toString() ?? fallbackResourceType;
      final entityCard = result['entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': result['entity_card'] as Map<String, dynamic>},
              fallbackType: resourceType,
            )
          : null;
      final newId = result['new_resource_id']?.toString();
      if (resourceType == 'plan') {
        unawaited(ref.read(planListProvider.notifier).refresh());
      } else if (resourceType == 'task') {
        unawaited(ref.read(taskListProvider.notifier).refreshTasks());
      }
      final route = entityCard?.detailRoute ??
          (newId == null
              ? null
              : resourceType == 'plan'
                  ? '/plans/$newId'
                  : resourceType == 'task'
                      ? '/tasks/$newId'
                      : null);
      if (route != null && route.isNotEmpty) {
        unawaited(context.push(route));
      }
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(
        context,
        context.isChinese ? '采纳失败: $e' : 'Adoption failed: $e',
      );
    }
  }

  Widget _buildRichCardWrapper({
    required bool isMe,
    required Widget child,
    VoidCallback? onTap,
  }) {
    final isLightMode = Theme.of(context).brightness == Brightness.light;
    final wrapperColor = isLightMode
        ? Colors.transparent
        : (isMe ? DS.chatBubbleUser : DS.chatBubbleOther);
    final wrapperShadow = isLightMode
        ? const <BoxShadow>[]
        : (isMe
            ? [
                BoxShadow(
                  color: DS.chatBubbleUser.withValues(alpha: 0.18),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ]
            : DS.shadowSm);

    return SparkleTappable(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 280),
        decoration: BoxDecoration(
          color: wrapperColor,
          borderRadius: BorderRadius.circular(16),
          boxShadow: wrapperShadow,
          border:
              isLightMode || isMe ? null : Border.all(color: DS.borderSubtle),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: child,
        ),
      ),
    );
  }

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
                    color: isMe ? DS.neutral0 : DS.prismPurple,
                    size: 20,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.communityCognitivePrism,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: isMe
                              ? DS.neutral0.withValues(alpha: 0.7)
                              : DS.textTertiary,
                        ),
                      ),
                      Text(
                        data['title'] as String? ??
                            context.l10n.communityLearningModeAnalysis,
                        style: TextStyle(
                          fontWeight: DS.fontWeightBold,
                          color: isMe ? DS.neutral0 : DS.textPrimary,
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
                    .map<Widget>(
                      (p) => Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.sm,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: isMe
                              ? DS.neutral0.withValues(alpha: 0.15)
                              : DS.prismPurple.withValues(alpha: 0.1),
                          borderRadius: DS.borderRadius4,
                        ),
                        child: Text(
                          p.toString(),
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: isMe ? DS.neutral0 : DS.prismPurple,
                          ),
                        ),
                      ),
                    )
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
                    color: isMe ? DS.neutral0 : DS.warning,
                    size: 20,
                  ),
                ),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.communityAchievementUnlocked,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: isMe
                              ? DS.neutral0.withValues(alpha: 0.7)
                              : DS.textTertiary,
                        ),
                      ),
                      Text(
                        data['name'] as String? ??
                            context.l10n.communityNewAchievement,
                        style: TextStyle(
                          fontWeight: DS.fontWeightBold,
                          color: isMe ? DS.neutral0 : DS.textPrimary,
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
        unawaited(UniversalShareService().copyDeepLink(deepLink));
        AppFeedback.info(context, context.l10n.communityLinkCopied);
      }
    }
  }

  Widget _buildAvatar(UserBrief? user) {
    final resolvedUser = user ??
        (isCommunityAgentMessage(widget.message)
            ? buildCommunityAgentUser()
            : null);
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
