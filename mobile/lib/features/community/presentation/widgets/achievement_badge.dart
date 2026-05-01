import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// 责任伙伴成就徽章组件
class AchievementBadge extends StatelessWidget {
  const AchievementBadge({
    super.key,
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.points,
    required this.isUnlocked,
    this.unlockedAt,
    this.size = AchievementBadgeSize.medium,
    this.onTap,
  });

  final String id;
  final String name;
  final String description;
  final String icon;
  final int points;
  final bool isUnlocked;
  final DateTime? unlockedAt;
  final AchievementBadgeSize size;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = _buildContent(context);

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: content,
      );
    }

    return content;
  }

  Widget _buildContent(BuildContext context) {
    final isSmall = size == AchievementBadgeSize.small;

    return Container(
      padding: EdgeInsets.all(isSmall ? 8 : 12),
      decoration: BoxDecoration(
        gradient: isUnlocked
            ? LinearGradient(
                colors: [
                  Theme.of(context).colorScheme.primaryContainer,
                  Theme.of(context).colorScheme.secondaryContainer,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        color: isUnlocked
            ? null
            : Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(isSmall ? 8 : 12),
        border: isUnlocked
            ? Border.all(
                color: Theme.of(
                  context,
                ).colorScheme.primary.withValues(alpha: 0.3),
              )
            : null,
      ),
      child:
          isSmall ? _buildSmallContent(context) : _buildMediumContent(context),
    );
  }

  Widget _buildSmallContent(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildIcon(context),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              icon,
              style: Theme.of(context).textTheme.bodyMedium,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      );

  Widget _buildMediumContent(BuildContext context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildIcon(context),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      name,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      description,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: isUnlocked
                                ? null
                                : Theme.of(context)
                                    .colorScheme
                                    .onSurfaceVariant,
                          ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              if (isUnlocked) _buildPointsBadge(context),
            ],
          ),
          if (unlockedAt != null && isUnlocked)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                I18nService.instance.isChinese
                    ? '在 ${_formatDate(unlockedAt!)} 解锁'
                    : 'Unlocked on ${_formatDate(unlockedAt!)}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
              ),
            ),
        ],
      );

  Widget _buildIcon(BuildContext context) => Container(
        width: size == AchievementBadgeSize.small ? 32 : 48,
        height: size == AchievementBadgeSize.small ? 32 : 48,
        decoration: BoxDecoration(
          color: isUnlocked
              ? Theme.of(context).colorScheme.primaryContainer
              : Theme.of(context).colorScheme.surfaceContainer,
          borderRadius:
              BorderRadius.circular(size == AchievementBadgeSize.small ? 6 : 8),
        ),
        child: Center(
          child: Text(
            icon,
            style: TextStyle(
              fontSize: size == AchievementBadgeSize.small ? 18 : 28,
            ),
          ),
        ),
      );

  Widget _buildPointsBadge(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.star,
              size: 12,
              color: DS.neutral0,
            ),
            const SizedBox(width: 4),
            Text(
              '+$points',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral0,
                    fontWeight: FontWeight.bold,
                  ),
            ),
          ],
        ),
      );

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays == 0) {
      return S.communityShareTodayDate;
    } else if (difference.inDays == 1) {
      return S.communityShareYesterday;
    } else if (difference.inDays < 7) {
      return S.communityDaysAgo(difference.inDays);
    } else if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return I18nService.instance.isChinese ? '$weeks 周前' : '$weeks weeks ago';
    } else if (difference.inDays < 365) {
      final months = (difference.inDays / 30).floor();
      return I18nService.instance.isChinese
          ? '$months 个月前'
          : '$months months ago';
    } else {
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    }
  }
}

enum AchievementBadgeSize {
  small,
  medium,
  large,
}

/// 成就网格列表
class AchievementGrid extends StatelessWidget {
  const AchievementGrid({
    super.key,
    required this.achievements,
    this.onAchievementTap,
    this.crossAxisCount = 2,
  });

  final List<AchievementInfo> achievements;
  final void Function(String achievementId)? onAchievementTap;
  final int crossAxisCount;

  @override
  Widget build(BuildContext context) {
    if (achievements.isEmpty) {
      return _buildEmptyState(context);
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: 1.5,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: achievements.length,
      itemBuilder: (context, index) {
        final achievement = achievements[index];
        return AchievementBadge(
          id: achievement.id,
          name: achievement.name,
          description: achievement.description,
          icon: achievement.icon,
          points: achievement.points,
          isUnlocked: achievement.isUnlocked,
          unlockedAt: achievement.unlockedAt,
          onTap: onAchievementTap != null
              ? () => onAchievementTap!(achievement.id)
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
                Icons.emoji_events_outlined,
                size: 64,
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              const SizedBox(height: 16),
              Text(
                context.l10n.communityShareNoAchievements,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                context.l10n.communityShareStartCheckin,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      );
}

/// 成就信息模型
class AchievementInfo {
  AchievementInfo({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.points,
    required this.isUnlocked,
    this.unlockedAt,
  });

  final String id;
  final String name;
  final String description;
  final String icon;
  final int points;
  final bool isUnlocked;
  final DateTime? unlockedAt;

  factory AchievementInfo.fromJson(Map<String, dynamic> json) =>
      AchievementInfo(
        id: json['id'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        icon: json['icon'] as String? ?? '🏆',
        points: json['points'] as int? ?? 0,
        isUnlocked: json['unlocked'] as bool? ?? false,
        unlockedAt: json['unlocked_at'] != null
            ? DateTime.parse(json['unlocked_at'] as String)
            : null,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'icon': icon,
        'points': points,
        'unlocked': isUnlocked,
        'unlocked_at': unlockedAt?.toIso8601String(),
      };
}

/// 成就进度展示组件
class AchievementProgressIndicator extends StatelessWidget {
  const AchievementProgressIndicator({
    super.key,
    required this.label,
    required this.current,
    required this.total,
    this.color,
  });

  final String label;
  final int current;
  final int total;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final progress = total > 0 ? current / total : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Text(
              '$current / $total',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor:
                Theme.of(context).colorScheme.surfaceContainerHighest,
            valueColor: AlwaysStoppedAnimation(
              color ?? Theme.of(context).colorScheme.primary,
            ),
            minHeight: 6,
          ),
        ),
      ],
    );
  }
}

/// 成就详情弹窗
class AchievementDetailDialog extends StatelessWidget {
  const AchievementDetailDialog({
    super.key,
    required this.achievement,
  });

  final AchievementInfo achievement;

  @override
  Widget build(BuildContext context) => AlertDialog(
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: achievement.isUnlocked
                    ? Theme.of(context).colorScheme.primaryContainer
                    : Theme.of(context).colorScheme.surfaceContainer,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Text(
                  achievement.icon,
                  style: const TextStyle(fontSize: 48),
                ),
              ),
            ),
            const SizedBox(height: 16),
            Text(
              achievement.name,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              achievement.description,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
              textAlign: TextAlign.center,
            ),
            if (achievement.isUnlocked) ...[
              const SizedBox(height: 16),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.star, size: 16),
                    const SizedBox(width: 8),
                    Text(
                      '+${achievement.points} 积分',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(context.l10n.communityShareClose),
          ),
        ],
      );

  static void show(BuildContext context, AchievementInfo achievement) {
    showSensoryDialog<void>(
      context: context,
      builder: (context) => AchievementDetailDialog(achievement: achievement),
    );
  }
}
