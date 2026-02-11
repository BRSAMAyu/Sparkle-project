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
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case AchievementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
          gradient: LinearGradient(
            colors: [DS.rarityRare, DS.rarityRare.withValues(alpha: 0.7)],
          ),
        );
      case AchievementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
          gradient: LinearGradient(
            colors: [DS.rarityEpic, DS.rarityEpic.withValues(alpha: 0.7)],
          ),
        );
      case AchievementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
          gradient: LinearGradient(
            colors: [
              DS.error,
              DS.warning,
              DS.success,
              DS.info,
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
        return DS.rarityCommon;
      case AchievementRarity.rare:
        return DS.rarityRare;
      case AchievementRarity.epic:
        return DS.rarityEpic;
      case AchievementRarity.legendary:
        return DS.rarityLegendary;
    }
  }

  /// 获取稀有度对应的渐变
  static LinearGradient? getGradient(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return null;
      case AchievementRarity.rare:
        return LinearGradient(
          colors: [DS.rarityRare, DS.rarityRare.withValues(alpha: 0.7)],
        );
      case AchievementRarity.epic:
        return LinearGradient(
          colors: [DS.rarityEpic, DS.rarityEpic.withValues(alpha: 0.7)],
        );
      case AchievementRarity.legendary:
        return LinearGradient(
          colors: [
            DS.error,
            DS.warning,
            DS.success,
            DS.info,
          ],
          stops: [0.0, 0.33, 0.66, 1.0],
        );
    }
  }

  /// 获取稀有度对应的背景颜色
  static Color getBackgroundColor(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return DS.rarityCommonBg;
      case AchievementRarity.rare:
        return DS.rarityRareBg;
      case AchievementRarity.epic:
        return DS.rarityEpicBg;
      case AchievementRarity.legendary:
        return DS.rarityLegendaryBg;
    }
  }
}
