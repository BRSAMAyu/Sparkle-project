import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/achievement/presentation/providers/home_close_to_unlock_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// Home screen card showing up to 3 closest-to-unlock achievements.
/// Fetches data on first build; respects a 5-minute cache.
class AchievementProgressCard extends ConsumerStatefulWidget {
  const AchievementProgressCard({super.key});

  @override
  ConsumerState<AchievementProgressCard> createState() =>
      _AchievementProgressCardState();
}

class _AchievementProgressCardState
    extends ConsumerState<AchievementProgressCard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(homeCloseToUnlockProvider.notifier).fetch();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(homeCloseToUnlockProvider);
    final l10n = AppLocalizations.of(context)!;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Hide when loading with no previous data, or when list is empty
    if (state.items.isEmpty && !state.isLoading) return const SizedBox.shrink();

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                Color.lerp(
                  DS.surfaceSecondary,
                  DS.warning,
                  isDark ? 0.12 : 0.06,
                )!,
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.warning.withValues(alpha: isDark ? 0.22 : 0.14),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Header(l10n: l10n),
              const SizedBox(height: DS.spacing10),
              if (state.isLoading && state.items.isEmpty)
                _LoadingRows()
              else
                ...state.items.map(
                  (item) => _AchievementRow(item: item, l10n: l10n),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Header row
// ---------------------------------------------------------------------------

class _Header extends StatelessWidget {
  const _Header({required this.l10n});

  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(
            Icons.emoji_events_outlined,
            color: DS.warning,
            size: 16,
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            l10n.achievementAlmostThere,
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: () => context.push(AchievementRoutes.basePath),
            child: Row(
              children: [
                Text(
                  l10n.achievementViewAll,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(width: 2),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.textSecondary,
                  size: 14,
                ),
              ],
            ),
          ),
        ],
      );
}

// ---------------------------------------------------------------------------
// Single achievement row
// ---------------------------------------------------------------------------

class _AchievementRow extends StatelessWidget {
  const _AchievementRow({required this.item, required this.l10n});

  final AchievementWithProgress item;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final achievement = item.achievement;
    final rarity = achievement.rarity;
    final progress = (item.progressPercentage / 100.0).clamp(0.0, 1.0);
    final current = item.userProgress?.progressValue ?? 0;
    final target = item.userProgress?.progressTarget ?? 1;
    final visualRewards = _extractVisualElementRewards(achievement);

    return GestureDetector(
      onTap: () => context.push('/achievements/${achievement.id}'),
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Container(
          padding: const EdgeInsets.all(DS.spacing10),
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.82),
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: _rarityColor(rarity).withValues(alpha: 0.14),
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: _rarityColor(rarity).withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.workspace_premium_rounded,
                  size: 16,
                  color: _rarityColor(rarity),
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            achievement.name,
                            style: context.sparkleTypography.labelSmall.copyWith(
                              color: DS.textPrimary,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: DS.spacing4),
                        Text(
                          '$current/$target',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textTertiary,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(999),
                            child: LinearProgressIndicator(
                              value: progress,
                              minHeight: 4,
                              backgroundColor: DS.neutral200,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(_rarityColor(rarity)),
                            ),
                          ),
                        ),
                        if (visualRewards.isNotEmpty) ...[
                          const SizedBox(width: DS.spacing8),
                          _VisualRewardBadge(
                            rewards: visualRewards,
                            l10n: l10n,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 从成就奖励配置中提取视觉元素奖励
  List<Map<String, dynamic>> _extractVisualElementRewards(
    AchievementModel achievement,
  ) {
    final rewardConfig = achievement.rewardConfig;
    if (rewardConfig == null || rewardConfig.isEmpty) return [];

    return rewardConfig
        .where((r) =>
            r['type'] == 'visual_element' ||
            r['type'] == 'background' ||
            r['type'] == 'particle' ||
            r['type'] == 'effect',)
        .toList();
  }

  Color _rarityColor(AchievementRarity? rarity) {
    final rarityName = switch (rarity) {
      AchievementRarity.legendary => 'legendary',
      AchievementRarity.epic => 'epic',
      AchievementRarity.rare => 'rare',
      AchievementRarity.common || null => 'common',
    };
    return getAchievementColor(rarityName);
  }
}

/// 视觉元素奖励徽章
class _VisualRewardBadge extends StatefulWidget {
  const _VisualRewardBadge({
    required this.rewards,
    required this.l10n,
  });

  final List<Map<String, dynamic>> rewards;
  final AppLocalizations l10n;

  @override
  State<_VisualRewardBadge> createState() => _VisualRewardBadgeState();
}

class _VisualRewardBadgeState extends State<_VisualRewardBadge>
    with SingleTickerProviderStateMixin {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final firstReward = widget.rewards.first;
    final rarityStr = firstReward['rarity'] as String? ?? 'common';
    final rarity = _parseRarity(rarityStr);
    final colors = _getRarityColors(rarity);

    return GestureDetector(
      onTapDown: (_) {
        setState(() => _isPressed = true);
        unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
      },
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        curve: Curves.easeOut,
        transform: Matrix4.diagonal3Values(
          _isPressed ? 0.96 : 1.0,
          _isPressed ? 0.96 : 1.0,
          1,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: DS.spacing2,
        ),
        decoration: BoxDecoration(
          color: colors.background.withValues(alpha: 0.92),
          borderRadius: DS.borderRadius6,
          border: Border.all(color: colors.border, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.auto_awesome,
              size: 12,
              color: colors.text,
            ),
            const SizedBox(width: DS.spacing2),
            Text(
              _getRarityName(rarity),
              style: TextStyle(
                fontSize: 10,
                fontWeight: DS.fontWeightMedium,
                color: colors.text,
              ),
            ),
          ],
        ),
      ),
    );
  }

  VisualElementRarity _parseRarity(String rarity) {
    return switch (rarity) {
      'legendary' => VisualElementRarity.legendary,
      'epic' => VisualElementRarity.epic,
      'rare' => VisualElementRarity.rare,
      _ => VisualElementRarity.common,
    };
  }

  String _getRarityName(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.legendary:
        return widget.l10n.achievementRarityLegendary;
      case VisualElementRarity.epic:
        return widget.l10n.achievementRarityEpic;
      case VisualElementRarity.rare:
        return widget.l10n.achievementRarityRare;
      case VisualElementRarity.common:
        return widget.l10n.achievementRarityCommon;
    }
  }

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
        );
    }
  }
}

class _RarityColors {
  _RarityColors({
    required this.background,
    required this.border,
    required this.text,
  });

  final Color background;
  final Color border;
  final Color text;
}

// ---------------------------------------------------------------------------
// Loading placeholder
// ---------------------------------------------------------------------------

class _LoadingRows extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Column(
        children: List.generate(
          2,
          (_) => Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: DS.neutral200,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        height: 12,
                        width: 120,
                        decoration: BoxDecoration(
                          color: DS.neutral200,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(2),
                        child: LinearProgressIndicator(
                          value: null,
                          minHeight: 3,
                          backgroundColor: DS.neutral200,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(DS.neutral300),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
