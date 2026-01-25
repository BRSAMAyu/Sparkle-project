import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 成就卡片样式
enum AchievementCardStyle {
  /// 紧凑型 - 用于列表
  compact,
  /// 标准型 - 用于网格
  standard,
  /// 完整型 - 用于详情
  full,
}

/// 成就卡片组件
///
/// 显示成就图标、名称、进度，支持点击跳转
class AchievementCard extends StatelessWidget {
  const AchievementCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.style = AchievementCardStyle.standard,
    this.isPinned = false,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final AchievementCardStyle style;
  final bool isPinned;
  final bool showProgress;

  @override
  Widget build(BuildContext context) {
    switch (style) {
      case AchievementCardStyle.compact:
        return _buildCompact(context);
      case AchievementCardStyle.standard:
        return _buildStandard(context);
      case AchievementCardStyle.full:
        return _buildFull(context);
    }
  }

  Widget _buildCompact(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: isUnlocked ? rarityColor : DS.border,
            width: isUnlocked ? 1.5 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.15),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            _buildIcon(size: 40),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          achievement.achievement.name,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightSemibold,
                            color: isUnlocked ? DS.textPrimary : DS.textSecondary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (isPinned)
                        Padding(
                          padding: const EdgeInsets.only(left: DS.spacing8),
                          child: Icon(
                            Icons.push_pin,
                            size: DS.iconSizeXs,
                            color: DS.semanticWarning,
                          ),
                        ),
                    ],
                  ),
                  if (achievement.achievement.description != null) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      achievement.achievement.description!,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  if (showProgress && !isUnlocked) ...[
                    const SizedBox(height: DS.spacing6),
                    _buildCompactProgressBar(),
                  ],
                ],
              ),
            ),
            const SizedBox(width: DS.spacing8),
            _buildStatusIcon(),
          ],
        ),
      ),
    );
  }

  Widget _buildStandard(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);
    final rarityGradient = RarityColorProvider.getGradient(achievement.achievement.rarity);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          gradient: isUnlocked && rarityGradient != null
              ? LinearGradient(
                  colors: [
                    rarityGradient.colors.first.withValues(alpha: 0.1),
                    rarityGradient.colors.last.withValues(alpha: 0.05),
                  ],
                )
              : null,
          color: isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: isUnlocked ? rarityColor : DS.border,
            width: isUnlocked ? 2 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.2),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ]
              : DS.shadowSm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildIcon(),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              achievement.achievement.name,
                              style: TextStyle(
                                fontSize: DS.fontSizeBase,
                                fontWeight: DS.fontWeightBold,
                                color: isUnlocked ? DS.textPrimary : DS.textSecondary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isPinned) ...[
                            const SizedBox(width: DS.spacing6),
                            Icon(
                              Icons.push_pin,
                              size: DS.iconSizeXs,
                              color: DS.semanticWarning,
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: DS.spacing4),
                      RarityBadge(
                        rarity: achievement.achievement.rarity,
                        isCompact: true,
                      ),
                    ],
                  ),
                ),
                _buildStatusIcon(),
              ],
            ),
            if (achievement.achievement.description != null) ...[
              const SizedBox(height: DS.spacing12),
              Text(
                achievement.achievement.description!,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                  height: 1.4,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            if (showProgress) ...[
              const SizedBox(height: DS.spacing12),
              _buildProgressBar(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFull(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);
    final rarityGradient = RarityColorProvider.getGradient(achievement.achievement.rarity);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing20),
        decoration: BoxDecoration(
          gradient: isUnlocked && rarityGradient != null
              ? LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    rarityGradient.colors.first.withValues(alpha: 0.15),
                    rarityGradient.colors.last.withValues(alpha: 0.08),
                  ],
                )
              : null,
          color: isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadius20,
          border: Border.all(
            color: isUnlocked ? rarityColor : DS.border,
            width: isUnlocked ? 2 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.25),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ]
              : DS.shadowMd,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildIcon(size: 56),
                const SizedBox(width: DS.spacing16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        achievement.achievement.name,
                        style: TextStyle(
                          fontSize: DS.fontSizeLg,
                          fontWeight: DS.fontWeightBold,
                          color: isUnlocked ? DS.textPrimary : DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      RarityBadge(rarity: achievement.achievement.rarity),
                    ],
                  ),
                ),
                if (isPinned)
                  Icon(
                    Icons.push_pin,
                    size: DS.iconSizeSm,
                    color: DS.semanticWarning,
                  ),
                const SizedBox(width: DS.spacing8),
                _buildStatusIcon(size: 28),
              ],
            ),
            if (achievement.achievement.description != null) ...[
              const SizedBox(height: DS.spacing16),
              Text(
                achievement.achievement.description!,
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  color: DS.textSecondary,
                  height: 1.5,
                ),
              ),
            ],
            if (showProgress) ...[
              const SizedBox(height: DS.spacing16),
              _buildProgressBar(height: 8),
              const SizedBox(height: DS.spacing8),
              _buildProgressText(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildIcon({double size = 48}) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isUnlocked
              ? [
                  rarityColor.withValues(alpha: 0.9),
                  rarityColor.withValues(alpha: 0.6),
                ]
              : [
                  DS.neutral300,
                  DS.neutral400,
                ],
        ),
        boxShadow: isUnlocked
            ? [
                BoxShadow(
                  color: rarityColor.withValues(alpha: 0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Icon(
        _getIconForAchievement(),
        color: isUnlocked ? Colors.white : DS.neutral600,
        size: size * 0.5,
      ),
    );
  }

  Widget _buildStatusIcon({double size = 20}) {
    if (achievement.isUnlocked) {
      return Icon(
        Icons.check_circle,
        color: DS.semanticSuccess,
        size: size,
      );
    }
    return Icon(
      Icons.lock_outline,
      color: DS.textTertiary,
      size: size,
    );
  }

  Widget _buildProgressBar({double height = 6}) {
    final progress = achievement.progressPercentage / 100;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);

    return Container(
      height: height,
      decoration: BoxDecoration(
        color: DS.neutral200,
        borderRadius: DS.borderRadiusFull,
      ),
      child: FractionallySizedBox(
        alignment: Alignment.centerLeft,
        widthFactor: progress.clamp(0.0, 1.0),
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: achievement.isUnlocked
                  ? [DS.semanticSuccess, DS.semanticSuccess.withValues(alpha: 0.8)]
                  : [
                      rarityColor,
                      rarityColor.withValues(alpha: 0.7),
                    ],
            ),
            borderRadius: DS.borderRadiusFull,
          ),
        ),
      ),
    );
  }

  Widget _buildCompactProgressBar() {
    final progress = achievement.progressPercentage / 100;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Expanded(
          child: Container(
            height: 4,
            decoration: BoxDecoration(
              color: DS.neutral200,
              borderRadius: DS.borderRadiusFull,
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: progress.clamp(0.0, 1.0),
              child: Container(
                decoration: BoxDecoration(
                  color: rarityColor,
                  borderRadius: DS.borderRadiusFull,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: DS.spacing8),
        Text(
          '${achievement.progressPercentage}%',
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: DS.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildProgressText() {
    final userProgress = achievement.userProgress;

    if (userProgress == null) {
      return const SizedBox.shrink();
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          '进度',
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.textSecondary,
          ),
        ),
        Text(
          '${userProgress.progressValue} / ${userProgress.progressTarget}',
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: DS.textPrimary,
          ),
        ),
      ],
    );
  }

  IconData _getIconForAchievement() {
    // 根据成就类型返回对应图标
    switch (achievement.achievement.type) {
      case AchievementType.streak:
        return Icons.local_fire_department_rounded;
      case AchievementType.mastery:
        return Icons.military_tech;
      case AchievementType.taskComplete:
        return Icons.task_alt;
      case AchievementType.nodeExplore:
        return Icons.explore;
      case AchievementType.studyTime:
        return Icons.schedule;
      case AchievementType.hidden:
        return Icons.help_outline;
      case AchievementType.milestone:
        return Icons.flag;
      case AchievementType.social:
        return Icons.people;
      case AchievementType.contract:
        return Icons.description;
      case AchievementType.sprint:
        return Icons.directions_run;
    }
  }
}

/// 成就网格卡片（用于网格布局）
class AchievementGridCard extends StatelessWidget {
  const AchievementGridCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final bool showProgress;

  @override
  Widget build(BuildContext context) => AchievementCard(
      achievement: achievement,
      onTap: onTap,
      style: AchievementCardStyle.standard,
      showProgress: showProgress,
    );
}

/// 成就列表卡片（用于列表布局）
class AchievementListCard extends StatelessWidget {
  const AchievementListCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final bool showProgress;

  @override
  Widget build(BuildContext context) => AchievementCard(
      achievement: achievement,
      onTap: onTap,
      style: AchievementCardStyle.compact,
      showProgress: showProgress,
    );
}

/// 成就详情卡片（用于详情页）
class AchievementDetailCard extends StatelessWidget {
  const AchievementDetailCard({
    required this.achievement,
    super.key,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final bool showProgress;

  @override
  Widget build(BuildContext context) => AchievementCard(
      achievement: achievement,
      style: AchievementCardStyle.full,
      showProgress: showProgress,
    );
}
