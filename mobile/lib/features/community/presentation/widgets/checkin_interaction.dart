import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// 责任伙伴打卡互动组件
///
/// 显示打卡的点赞和鼓励消息，并提供互动功能
class CheckinInteraction extends StatelessWidget {
  const CheckinInteraction({
    super.key,
    required this.checkinId,
    required this.content,
    required this.authorName,
    required this.likes,
    required this.encouragements,
    required this.isMyCheckin,
    required this.isMyPartner,
    this.onLike,
    this.onEncourage,
  });

  final String checkinId;
  final String content;
  final String authorName;
  final int likes;
  final List<EncouragementMessage> encouragements;
  final bool isMyCheckin;
  final bool isMyPartner;
  final VoidCallback? onLike;
  final void Function(String message)? onEncourage;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context),
              const SizedBox(height: 8),
              _buildContent(context),
              const SizedBox(height: 12),
              _buildActions(context),
              if (encouragements.isNotEmpty) ...[
                const SizedBox(height: 12),
                _buildEncouragements(context),
              ],
            ],
          ),
        ),
      );

  Widget _buildHeader(BuildContext context) => Row(
        children: [
          CircleAvatar(
            radius: 16,
            child: Text(authorName[0].toUpperCase()),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  authorName,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                if (isMyCheckin)
                  Text(
                    context.l10n.communityMyCheckin,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                        ),
                  ),
              ],
            ),
          ),
        ],
      );

  Widget _buildContent(BuildContext context) => Text(
        content,
        style: Theme.of(context).textTheme.bodyMedium,
      );

  Widget _buildActions(BuildContext context) => Row(
        children: [
          if (!isMyCheckin && isMyPartner)
            _buildLikeButton(context)
          else
            _buildLikeCount(context),
          const SizedBox(width: 16),
          if (!isMyCheckin && isMyPartner)
            _buildEncourageButton(context)
          else
            _buildEncourageCount(context),
          const Spacer(),
        ],
      );

  Widget _buildLikeButton(BuildContext context) => InkWell(
        onTap: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
          onLike?.call();
        },
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.favorite_border, size: 16),
              const SizedBox(width: 4),
              Text(
                likes.toString(),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );

  Widget _buildLikeCount(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.favorite, size: 16, color: DS.error),
          const SizedBox(width: 4),
          Text(
            context.l10n.communityLikesCount(likes),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ],
      );

  Widget _buildEncourageButton(BuildContext context) => InkWell(
        onTap: () {
          unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
          _showEncourageDialog(context);
        },
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.chat_bubble_outline, size: 16),
              const SizedBox(width: 4),
              Text(
                context.l10n.communityEncourage,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );

  Widget _buildEncourageCount(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.chat_bubble_outline, size: 16),
          const SizedBox(width: 4),
          Text(
            context.l10n.communityEncouragementsCount(encouragements.length),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ],
      );

  Widget _buildEncouragements(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.communityEncouragementMessages,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
          const SizedBox(height: 8),
          ...encouragements.map((e) => _buildEncouragementItem(context, e)),
        ],
      );

  Widget _buildEncouragementItem(
    BuildContext context,
    EncouragementMessage encouragement,
  ) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 10,
                    child: Text(
                      _encouragementAuthor(context, encouragement)[0]
                          .toUpperCase(),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    _encouragementAuthor(context, encouragement),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const Spacer(),
                  Text(
                    _formatTime(context, encouragement.createdAt),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                encouragement.message,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      );

  String _encouragementAuthor(
      BuildContext context, EncouragementMessage encouragement) {
    if (encouragement.authorName.isNotEmpty) {
      return encouragement.authorName;
    }
    return context.l10n.communityPartnerFallback;
  }

  void _showEncourageDialog(BuildContext context) {
    final controller = TextEditingController();

    showSensoryDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.communitySendEncouragement),
        content: TextField(
          controller: controller,
          maxLines: 3,
          maxLength: 500,
          decoration: InputDecoration(
            hintText: context.l10n.communityWriteEncouragement,
            border: const OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(context.l10n.cancel),
          ),
          FilledButton(
            onPressed: () {
              final message = controller.text.trim();
              if (message.isNotEmpty && onEncourage != null) {
                onEncourage!(message);
                Navigator.of(context).pop();
              }
            },
            child: Text(context.l10n.communitySendEncouragement),
          ),
        ],
      ),
    );
  }

  String _formatTime(BuildContext context, DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);

    if (difference.inMinutes < 1) {
      return context.l10n.communityJustNow;
    } else if (difference.inMinutes < 60) {
      return context.l10n.communityMinutesAgo(difference.inMinutes);
    } else if (difference.inHours < 24) {
      return context.l10n.communityHoursAgo(difference.inHours);
    } else if (difference.inDays < 7) {
      return context.l10n.communityDaysAgo(difference.inDays);
    } else {
      return '${time.month}-${time.day}';
    }
  }
}

/// 鼓励消息模型
class EncouragementMessage {
  EncouragementMessage({
    required this.id,
    required this.authorId,
    required this.authorName,
    required this.message,
    required this.createdAt,
  });

  final String id;
  final String authorId;
  final String authorName;
  final String message;
  final DateTime createdAt;

  factory EncouragementMessage.fromJson(Map<String, dynamic> json) =>
      EncouragementMessage(
        id: json['id'] as String,
        authorId: json['user_id'] as String,
        authorName: json['author_name'] as String? ??
            context.l10n.communityPartnerFallback,
        message: json['message'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': authorId,
        'author_name': authorName,
        'message': message,
        'created_at': createdAt.toIso8601String(),
      };
}

/// 简化版打卡互动组件 - 仅显示互动信息
class CheckinInteractionCompact extends StatelessWidget {
  const CheckinInteractionCompact({
    super.key,
    required this.likes,
    required this.encouragementCount,
    this.showEncouragement = true,
    this.onTap,
  });

  final int likes;
  final int encouragementCount;
  final bool showEncouragement;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildInteractionItem(
                context,
                icon: Icons.favorite,
                count: likes,
                color: DS.error,
              ),
              if (showEncouragement) ...[
                const SizedBox(width: 12),
                _buildInteractionItem(
                  context,
                  icon: Icons.chat_bubble_outline,
                  count: encouragementCount,
                ),
              ],
            ],
          ),
        ),
      );

  Widget _buildInteractionItem(
    BuildContext context, {
    required IconData icon,
    required int count,
    Color? color,
  }) =>
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: color ?? Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 4),
          Text(
            count.toString(),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ],
      );
}

/// 打卡互动列表 - 用于时间线展示
class CheckinInteractionList extends StatelessWidget {
  const CheckinInteractionList({
    super.key,
    required this.checkins,
    required this.myUserId,
    this.onLike,
    this.onEncourage,
    this.onCheckinTap,
  });

  final List<CheckinWithInteraction> checkins;
  final String myUserId;
  final void Function(String checkinId)? onLike;
  final void Function(String checkinId, String message)? onEncourage;
  final void Function(String checkinId)? onCheckinTap;

  @override
  Widget build(BuildContext context) {
    if (checkins.isEmpty) {
      return _buildEmptyState(context);
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: checkins.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final checkin = checkins[index];
        final isMyCheckin = checkin.userId == myUserId;
        final isMyPartner = !isMyCheckin; // Simplified logic

        return CheckinInteraction(
          checkinId: checkin.id,
          content: checkin.content,
          authorName: checkin.authorName,
          likes: checkin.likes,
          encouragements: checkin.encouragements,
          isMyCheckin: isMyCheckin,
          isMyPartner: isMyPartner,
          onLike: onLike != null ? () => onLike!(checkin.id) : null,
          onEncourage: onEncourage != null
              ? (message) => onEncourage!(checkin.id, message)
              : null,
        );
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            children: [
              Icon(
                Icons.history,
                size: 48,
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              const SizedBox(height: 16),
              Text(
                context.l10n.communityNoCheckinYet,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      );
}

/// 带互动信息的打卡数据模型
class CheckinWithInteraction {
  CheckinWithInteraction({
    required this.id,
    required this.userId,
    required this.authorName,
    required this.content,
    required this.likes,
    required this.encouragements,
    required this.createdAt,
  });

  final String id;
  final String userId;
  final String authorName;
  final String content;
  final int likes;
  final List<EncouragementMessage> encouragements;
  final DateTime createdAt;

  factory CheckinWithInteraction.fromJson(Map<String, dynamic> json) =>
      CheckinWithInteraction(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        authorName: json['author_name'] as String? ?? 'User',
        content: json['content'] as String,
        likes: json['likes'] as int? ?? 0,
        encouragements: (json['encouragements'] as List? ?? [])
            .map(
                (e) => EncouragementMessage.fromJson(e as Map<String, dynamic>))
            .toList(),
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'author_name': authorName,
        'content': content,
        'likes': likes,
        'encouragements': encouragements.map((e) => e.toJson()).toList(),
        'created_at': createdAt.toIso8601String(),
      };
}
