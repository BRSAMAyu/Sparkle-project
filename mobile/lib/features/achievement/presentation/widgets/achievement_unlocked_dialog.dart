import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

class SparkleAchievementUnlockedDialog extends StatelessWidget {
  const SparkleAchievementUnlockedDialog({
    required this.achievement,
    required this.onViewAchievements,
    super.key,
  });

  final AchievementModel achievement;
  final VoidCallback onViewAchievements;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    final rarityColor = RarityColorProvider.getColor(achievement.rarity);

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      title: Column(
        children: [
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.8, end: 1.0),
            duration: const Duration(milliseconds: 400),
            curve: Curves.elasticOut,
            builder: (context, value, child) => Transform.scale(
              scale: value,
              child: child,
            ),
            child: Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [rarityColor, rarityColor.withValues(alpha: 0.6)],
                ),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.3),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: Icon(
                _rarityIcon(achievement.rarity),
                color: Colors.white,
                size: 32,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            _t('成就解锁！', 'Achievement Unlocked!'),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
        ],
      ),
      content: SizedBox(
        width: double.maxFinite,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              achievement.name,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                    color: rarityColor,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            if (achievement.description != null &&
                achievement.description!.isNotEmpty)
              Text(
                achievement.description!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            const SizedBox(height: DS.spacing12),
            RarityBadge(rarity: achievement.rarity),
          ],
        ),
      ),
      actions: [
        FilledButton(
          onPressed: onViewAchievements,
          style: FilledButton.styleFrom(
            backgroundColor: rarityColor,
            shape: RoundedRectangleBorder(
              borderRadius: DS.borderRadius12,
            ),
          ),
          child: Text(_t('查看我的成就', 'View my achievements')),
        ),
      ],
      actionsAlignment: MainAxisAlignment.center,
    );
  }

  IconData _rarityIcon(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return Icons.emoji_events_outlined;
      case AchievementRarity.rare:
        return Icons.star_rounded;
      case AchievementRarity.epic:
        return Icons.auto_awesome;
      case AchievementRarity.legendary:
        return Icons.diamond;
    }
  }
}
