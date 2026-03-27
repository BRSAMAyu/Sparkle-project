import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar_heatmap_card.dart';
import 'package:sparkle/features/home/presentation/widgets/cognitive_tool_hub_card.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_carousel.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_grid.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_curiosity_card.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_edit_sheet.dart';
import 'package:sparkle/features/home/presentation/widgets/focus_card.dart';
import 'package:sparkle/features/home/presentation/widgets/insight_hub_card.dart';
import 'package:sparkle/features/home/presentation/widgets/long_term_plan_card.dart';
import 'package:sparkle/features/home/presentation/widgets/next_actions_card.dart';
import 'package:sparkle/features/home/presentation/widgets/seed_library_dashboard_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class DashboardCardSection extends ConsumerWidget {
  const DashboardCardSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardCardConfigProvider);
    final isGridMode = config.layoutMode == DashboardCardLayoutMode.grid;
    final visibleCardIds = config.visibleOrderedCards;
    final cards = visibleCardIds
        .map((cardId) => _buildCard(context, cardId, isGridMode: isGridMode))
        .toList(growable: false);

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compactHeader = constraints.maxWidth < 430;

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (compactHeader)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '驾驶舱组件',
                        style: context.sparkleTypography.labelLarge.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '把常用入口和摘要信息固定在这里。',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: () => _openEditSheet(context),
                          style: TextButton.styleFrom(
                            visualDensity: VisualDensity.compact,
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing10,
                              vertical: DS.spacing8,
                            ),
                          ),
                          icon: const Icon(Icons.tune_rounded, size: 18),
                          label: Text(
                            AppLocalizations.of(context)!
                                .dashboardCustomizeCards,
                          ),
                        ),
                      ),
                    ],
                  )
                else
                  Row(
                    children: [
                      Text(
                        '驾驶舱组件',
                        style: context.sparkleTypography.labelLarge.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          '把常用入口和摘要信息固定在这里。',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                      TextButton.icon(
                        onPressed: () => _openEditSheet(context),
                        style: TextButton.styleFrom(
                          visualDensity: VisualDensity.compact,
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing10,
                            vertical: DS.spacing8,
                          ),
                        ),
                        icon: const Icon(Icons.tune_rounded, size: 18),
                        label: Text(
                          AppLocalizations.of(context)!.dashboardCustomizeCards,
                        ),
                      ),
                    ],
                  ),
                const SizedBox(height: DS.spacing10),
                if (cards.isEmpty)
                  const _EmptyDashboardCardSection()
                else if (config.layoutMode == DashboardCardLayoutMode.swipe)
                  DashboardCardCarousel(
                    cards: cards,
                    cardIds: visibleCardIds,
                    preferredInitialCardId: DashboardCardIds.calendar,
                  )
                else
                  DashboardCardGrid(cards: cards),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildCard(
    BuildContext context,
    String cardId, {
    required bool isGridMode,
  }) {
    switch (cardId) {
      case DashboardCardIds.insights:
        return InsightHubCard(compact: true, dense: isGridMode);
      case DashboardCardIds.focus:
        return FocusCard(onTap: () => context.push('/focus'));
      case DashboardCardIds.calendar:
        return CalendarHeatmapCard(compact: true, dense: isGridMode);
      case DashboardCardIds.tools:
        return CognitiveToolHubCard(compact: true, dense: isGridMode);
      case DashboardCardIds.streak:
        return const _DashboardStreakCard();
      case DashboardCardIds.nextActions:
        return NextActionsCard(
          compact: true,
          dense: isGridMode,
          embedded: true,
          onViewAll: () => context.push('/tasks'),
        );
      case DashboardCardIds.curiosity:
        return DashboardCuriosityCard(compact: true, dense: isGridMode);
      case DashboardCardIds.seedLibrary:
        return SeedLibraryDashboardCard(compact: true, dense: isGridMode);
      case DashboardCardIds.longTermPlan:
        return LongTermPlanCard(compact: true, dense: isGridMode);
      default:
        return const _EmptyDashboardCardSection();
    }
  }

  Future<void> _openEditSheet(BuildContext context) =>
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => const DashboardEditSheet(),
      );
}

class _DashboardStreakCard extends StatelessWidget {
  const _DashboardStreakCard();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SparklePressable(
      onTap: () => context.push('/achievements'),
      padding: EdgeInsets.zero,
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic.copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              Color.lerp(DS.surfaceSecondary, DS.warning, 0.08)!,
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.warning.withValues(alpha: 0.18),
          borderWidth: 1,
        ),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.local_fire_department_rounded,
                  color: DS.warning,
                  size: 18,
                ),
                const SizedBox(width: DS.spacing8),
                Text(
                  l10n.winStreak,
                  style: context.sparkleTypography.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const Spacer(),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.textTertiary,
                  size: 18,
                ),
              ],
            ),
            const Spacer(),
            const Center(child: DashboardStreakIndicator()),
            const Spacer(),
            Text(
              l10n.achievementViewStreakStatus,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyDashboardCardSection extends StatelessWidget {
  const _EmptyDashboardCardSection();

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Text(
          AppLocalizations.of(context)!.dashboardEmptyHint,
          style: context.sparkleTypography.bodyMedium.copyWith(
            color: DS.textSecondary,
          ),
        ),
      );
}
