import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
    final name = _getRarityName(context);
    final icon = _getRarityIcon();

    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.hasBoundedWidth
            ? constraints.maxWidth
            : double.infinity;
        final superCompact = width < 36;
        final compactLabel = width < 64;
        final adaptiveShowLabel = showLabel && !superCompact && !compactLabel;

        return Container(
          padding: EdgeInsets.symmetric(
            horizontal: isCompact
                ? (superCompact ? 2 : DS.spacing6)
                : (compactLabel ? DS.spacing6 : DS.spacing8),
            vertical: superCompact ? 2 : DS.spacing4,
          ),
          decoration: BoxDecoration(
            color: colors.background,
            borderRadius: isCompact ? DS.borderRadius8 : DS.borderRadius12,
            border: Border.all(
              color: colors.border,
              width: isCompact ? 1 : 1.5,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: superCompact
                    ? 11
                    : (isCompact ? DS.iconSizeXs : DS.iconSizeSm),
                color: colors.text,
              ),
              if (adaptiveShowLabel) ...[
                const SizedBox(width: DS.spacing4),
                Flexible(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: isCompact ? DS.fontSizeXs : DS.fontSizeSm,
                      fontWeight: isCompact
                          ? DS.fontWeightMedium
                          : DS.fontWeightSemibold,
                      color: colors.text,
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
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

  String _getRarityName(BuildContext context) {
    final l10n = context.l10n;
    switch (rarity) {
      case AchievementRarity.common:
        return l10n.achievementRarityCommon;
      case AchievementRarity.rare:
        return l10n.achievementRarityRare;
      case AchievementRarity.epic:
        return l10n.achievementRarityEpic;
      case AchievementRarity.legendary:
        return l10n.achievementRarityLegendary;
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
