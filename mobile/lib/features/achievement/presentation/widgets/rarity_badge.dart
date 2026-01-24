import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 稀有度徽章组件
///
/// 显示成就稀有度的小型标签
class RarityBadge extends StatelessWidget {
  const RarityBadge({
    required this.rarity,
    super.key,
    this.showLabel = true,
    this.isCompact = false,
  });

  final AchievementRarity rarity;
  final bool showLabel;
  final bool isCompact;

  @override
  Widget build(BuildContext context) {
    final colors = _getRarityColors();
    final name = _getRarityName();
    final icon = _getRarityIcon();

    if (isCompact) {
      return Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: colors.background,
          borderRadius: DS.borderRadius8,
          border: Border.all(
            color: colors.border,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: DS.iconSizeXs,
              color: colors.text,
            ),
            if (showLabel) ...[
              const SizedBox(width: DS.spacing4),
              Text(
                name,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightMedium,
                  color: colors.text,
                ),
              ),
            ],
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: colors.border,
          width: 1.5,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: DS.iconSizeSm,
            color: colors.text,
          ),
          if (showLabel) ...[
            const SizedBox(width: DS.spacing4),
            Text(
              name,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                fontWeight: DS.fontWeightSemibold,
                color: colors.text,
              ),
            ),
          ],
        ],
      ),
    );
  }

  _RarityColors _getRarityColors() {
    switch (rarity) {
      case AchievementRarity.common:
        return _RarityColors(
          background: DS.neutral200,
          border: DS.neutral400,
          text: DS.neutral700,
        );
      case AchievementRarity.rare:
        return _RarityColors(
          background: const Color(0xFFFFF8DC),
          border: const Color(0xFFFFD700),
          text: const Color(0xFFB8860B),
          gradient: const LinearGradient(
            colors: [Color(0xFFFFD700), Color(0xFFFFA500)],
          ),
        );
      case AchievementRarity.epic:
        return _RarityColors(
          background: const Color(0xFFF3E5F5),
          border: const Color(0xFF9B59B6),
          text: const Color(0xFF7B1FA2),
          gradient: const LinearGradient(
            colors: [Color(0xFF9B59B6), Color(0xFF8E44AD)],
          ),
        );
      case AchievementRarity.legendary:
        return _RarityColors(
          background: const Color(0xFFE8F5E3),
          border: const Color(0xFFFF6B6B),
          text: const Color(0xFFD32F2F),
          gradient: const LinearGradient(
            colors: [
              Color(0xFFFF6B6B),
              Color(0xFFFFD93D),
              Color(0xFF6BCB77),
              Color(0xFF4D96FF),
            ],
            stops: [0.0, 0.33, 0.66, 1.0],
          ),
        );
    }
  }

  String _getRarityName() {
    switch (rarity) {
      case AchievementRarity.common:
        return '普通';
      case AchievementRarity.rare:
        return '稀有';
      case AchievementRarity.epic:
        return '史诗';
      case AchievementRarity.legendary:
        return '传说';
    }
  }

  IconData _getRarityIcon() {
    switch (rarity) {
      case AchievementRarity.common:
        return Icons.circle_outlined;
      case AchievementRarity.rare:
        return Icons.star_border;
      case AchievementRarity.epic:
        return Icons.auto_awesome;
      case AchievementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }
}

class _RarityColors {
  _RarityColors({
    required this.background,
    required this.border,
    required this.text,
    this.gradient,
  });

  final Color background;
  final Color border;
  final Color text;
  final LinearGradient? gradient;
}

/// 稀有度颜色获取器
class RarityColorProvider {
  /// 获取稀有度对应的颜色
  static Color getColor(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.neutral400;
      case AchievementRarity.rare:
        return const Color(0xFFFFD700);
      case AchievementRarity.epic:
        return const Color(0xFF9B59B6);
      case AchievementRarity.legendary:
        return const Color(0xFFFF6B6B);
    }
  }

  /// 获取稀有度对应的渐变
  static LinearGradient? getGradient(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return null;
      case AchievementRarity.rare:
        return const LinearGradient(
          colors: [Color(0xFFFFD700), Color(0xFFFFA500)],
        );
      case AchievementRarity.epic:
        return const LinearGradient(
          colors: [Color(0xFF9B59B6), Color(0xFF8E44AD)],
        );
      case AchievementRarity.legendary:
        return const LinearGradient(
          colors: [
            Color(0xFFFF6B6B),
            Color(0xFFFFD93D),
            Color(0xFF6BCB77),
            Color(0xFF4D96FF),
          ],
          stops: [0.0, 0.33, 0.66, 1.0],
        );
    }
  }

  /// 获取稀有度对应的背景颜色（带透明度）
  static Color getBackgroundColor(AchievementRarity rarity) {
    final color = getColor(rarity);
    switch (rarity) {
      case AchievementRarity.common:
        return DS.neutral200;
      case AchievementRarity.rare:
        return color.withValues(alpha: 0.15);
      case AchievementRarity.epic:
        return color.withValues(alpha: 0.15);
      case AchievementRarity.legendary:
        return color.withValues(alpha: 0.1);
    }
  }
}
