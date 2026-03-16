import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/achievement/presentation/providers/home_close_to_unlock_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

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

    // Hide when loading with no previous data, or when list is empty
    if (state.items.isEmpty && !state.isLoading) return const SizedBox.shrink();

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.brandPrimary.withValues(alpha: 0.08),
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.brandPrimary.withValues(alpha: 0.18),
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
            color: DS.brandPrimary,
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
                    color: DS.brandPrimary,
                  ),
                ),
                const SizedBox(width: 2),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.brandPrimary,
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

    return GestureDetector(
      onTap: () => context.push('/achievements/${achievement.id}'),
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          children: [
            // Rarity colour dot
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: _rarityColor(rarity),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          achievement.name,
                          style: context.sparkleTypography.labelMedium.copyWith(
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
                  const SizedBox(height: 4),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 3,
                      backgroundColor: DS.neutral200,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(_rarityColor(rarity)),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _rarityColor(AchievementRarity? rarity) {
    switch (rarity) {
      case AchievementRarity.legendary:
        return const Color(0xFFFFB347);
      case AchievementRarity.epic:
        return const Color(0xFFB04AFF);
      case AchievementRarity.rare:
        return const Color(0xFF4A9EFF);
      case AchievementRarity.common:
      default:
        return const Color(0xFF78C778);
    }
  }
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
