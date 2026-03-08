import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar_heatmap_card.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_curiosity_card.dart';
import 'package:sparkle/features/home/presentation/widgets/expanded_toolbar_section.dart';
import 'package:sparkle/features/home/presentation/widgets/focus_card.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/intent_prediction_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/long_term_plan_card.dart';
import 'package:sparkle/features/home/presentation/widgets/multi_agent_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/next_actions_card.dart';
import 'package:sparkle/features/home/presentation/widgets/omnibar.dart';
import 'package:sparkle/features/home/presentation/widgets/prism_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// Dashboard screen - extracted from HomeScreen
/// Displays the main project cockpit with bento grid layout
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final l10n = AppLocalizations.of(context)!;

    // Dynamic bottom spacing based on visible predictions
    final hasPredictions = predictions.isNotEmpty;
    final category = ResponsiveSystem.getCategory(context);
    final isSmallScreen = category == DeviceCategory.phone ||
        category == DeviceCategory.phablet ||
        category == DeviceCategory.watch;

    // Calculate spacing for floating components
    const spacing = 8.0;

    // Calculate cumulative bottom positions
    final omniBarBottom = spacing; // 8

    // IntentPredictionBar position (above OmniBar)
    final intentBarBottom = omniBarBottom + 52.0 + spacing; // ~68

    // Base position for MultiAgentBar (when no IntentPredictionBar)
    final baseMultiAgentBarBottom = omniBarBottom + 52.0 + spacing; // ~68

    // Adjust MultiAgentBar position based on whether IntentPredictionBar is shown
    final showIntentBar = hasPredictions;
    final finalMultiAgentBarBottom = showIntentBar
        ? intentBarBottom +
            36.0 +
            spacing // ~108 (IntentPredictionBar is ~36px)
        : baseMultiAgentBarBottom;

    // IntentPredictionBar only shows when has predictions
    final finalIntentBarBottom = showIntentBar ? intentBarBottom : 0.0;

    // Total bottom spacing
    final totalBottomHeight = showIntentBar
        ? finalMultiAgentBarBottom + 44.0 + spacing // ~156
        : baseMultiAgentBarBottom + 44.0 + spacing; // ~120

    // Max width for floating components on larger screens
    final floatingMaxWidth = switch (category) {
      DeviceCategory.tablet => DS.contentMaxWidthTablet,
      DeviceCategory.desktop => DS.contentMaxWidthDesktop,
      DeviceCategory.tv => DS.contentMaxWidthDesktop,
      DeviceCategory.watch => double.infinity,
      DeviceCategory.phone => double.infinity,
      DeviceCategory.phablet => double.infinity,
    };

    return SparklePageScaffold(
      role: SparklePageRole.dashboard,
      safeArea: false,
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: DS.pageGradientForRole(SparklePageRole.dashboard),
              ),
            ),
          ),
          // Layer 1: Weather Background
          const Positioned.fill(child: WeatherHeader()),

          // Layer 2: Dashboard Content
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              onRefresh: () async {
                await ref.read(dashboardProvider.notifier).refresh();
                await ref.read(taskListProvider.notifier).refreshTasks();
              },
              child: CustomScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  // Top Overlay with theme toggle button
                  SliverToBoxAdapter(
                    child: _buildTopOverlay(context, ref, user, l10n),
                  ),

                  // Message Notification Widget
                  const SliverToBoxAdapter(child: HomeNotificationCard()),

                  const SliverToBoxAdapter(child: NightlyReviewPanel()),

                  const SliverToBoxAdapter(child: SizedBox(height: 10)),

                  // Bento Grid
                  const SliverToBoxAdapter(child: SizedBox(height: 10)),
                  SliverToBoxAdapter(
                    child: _buildBentoGrid(context, dashboardState),
                  ),

                  // Task Board Card (Full width below grid)
                  const SliverToBoxAdapter(
                    child: SizedBox(height: DS.spacing16),
                  ),
                  const SliverToBoxAdapter(child: TaskBoardCard()),

                  // Expanded Toolbar Section
                  const SliverToBoxAdapter(
                    child: SizedBox(height: DS.spacing16),
                  ),
                  const SliverToBoxAdapter(child: ExpandedToolbarSection()),

                  // Dynamic bottom spacing for floating components
                  SliverToBoxAdapter(
                    child: SizedBox(
                      height: totalBottomHeight,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Layer 3: Intent Prediction Bar (only show when has predictions)
          if (showIntentBar)
            Positioned(
              left: 0,
              right: 0,
              bottom: finalIntentBarBottom,
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
                    child: IntentPredictionBar(),
                  ),
                ),
              ),
            ),

          // Layer 4: MultiAgent Bar (above OmniBar)
          Positioned(
            left: 0,
            right: 0,
            bottom: finalMultiAgentBarBottom,
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                child: Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: isSmallScreen ? DS.spacing16 : DS.spacing16,
                    vertical: DS.spacing4,
                  ),
                  child: const MultiAgentBar(),
                ),
              ),
            ),
          ),

          // Layer 5: Omni-Bar (bottom)
          Positioned(
            left: 0,
            right: 0,
            bottom: omniBarBottom,
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  child: OmniBar(hintText: l10n.typeMessage),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTopOverlay(
    BuildContext context,
    WidgetRef ref,
    UserModel? user,
    AppLocalizations l10n,
  ) =>
      ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.glass,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing12,
            ),
            child: Row(
              children: [
                // Avatar and user info
                Expanded(
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 18,
                        backgroundImage: user?.avatarUrl != null
                            ? NetworkImage(user!.avatarUrl!)
                            : null,
                        backgroundColor: DS.avatarFallbackBackground,
                        child: user?.avatarUrl == null
                            ? Text(
                                (user?.nickname ?? 'U')[0].toUpperCase(),
                                style: TextStyle(
                                  color: DS.avatarFallbackForeground,
                                ),
                              )
                            : null,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Lv.${user?.flameLevel ?? 1}',
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                fontWeight: DS.fontWeightBold,
                                color: DS.warning,
                              ),
                            ),
                            Text(
                              user?.nickname ??
                                  (user?.username ?? l10n.exploreGalaxy),
                              style: TextStyle(
                                fontSize: DS.fontSizeSm,
                                fontWeight: DS.fontWeightBold,
                                color: DS.brandPrimaryConst,
                              ),
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                _ThemeToggleButton(
                  onTap: () {
                    ref.read(themeManagerProvider).toggleDarkMode();
                  },
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildBentoGrid(BuildContext context, DashboardState state) {
    // Wrap with ContentConstraint for responsive width on desktop
    final category = ResponsiveSystem.getCategory(context);
    final isLandscapeMobile = ResponsiveSystem.isLandscapeMobile(context);

    // Responsive column count based on screen size
    final crossAxisCount = switch (category) {
      DeviceCategory.desktop => 3,
      DeviceCategory.tv => 3,
      DeviceCategory.tablet => 2,
      // Use 2 columns for landscape mobile, 1 for portrait
      DeviceCategory.watch => isLandscapeMobile ? 2 : 1,
      DeviceCategory.phone => isLandscapeMobile ? 2 : 1,
      DeviceCategory.phablet => isLandscapeMobile ? 2 : 1,
    };

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: StaggeredGrid.count(
          crossAxisCount: crossAxisCount,
          mainAxisSpacing: DS.spacing12,
          crossAxisSpacing: DS.spacing12,
          children: [
            // Card A: Focus Core (2x1)
            StaggeredGridTile.count(
              crossAxisCellCount: 2,
              mainAxisCellCount: 1,
              child: FocusCard(onTap: () => context.push('/focus')),
            ),
            // Card E: Calendar Heatmap (fit height to avoid overlap when expanded)
            const StaggeredGridTile.fit(
              crossAxisCellCount: 1,
              child: CalendarHeatmapCard(),
            ),
            // Card B: Cognitive Prism (1x1)
            const StaggeredGridTile.count(
              crossAxisCellCount: 1,
              mainAxisCellCount: 1,
              child: PrismCard(),
            ),
            // Card H: Streak Indicator (1x1) - Achievement Integration
            StaggeredGridTile.count(
              crossAxisCellCount: 1,
              mainAxisCellCount: 1,
              child: _StreakCard(onTap: () => context.push('/achievements')),
            ),
            // Card C: Next Actions (1x1) - Resized
            StaggeredGridTile.count(
              crossAxisCellCount: 1,
              mainAxisCellCount: 1,
              child: NextActionsCard(onViewAll: () => context.push('/tasks')),
            ),
            // Card F: Curiosity Capsule (1x1)
            const StaggeredGridTile.count(
              crossAxisCellCount: 1,
              mainAxisCellCount: 1,
              child: DashboardCuriosityCard(),
            ),
            // Card G: Long Term Plan (1x1) - Bottom Right
            const StaggeredGridTile.count(
              crossAxisCellCount: 1,
              mainAxisCellCount: 1,
              child: LongTermPlanCard(),
            ),
          ],
        ),
      ),
    );
  }
}

/// 连胜指示器卡片 - 用于仪表盘
class _StreakCard extends StatelessWidget {
  const _StreakCard({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                DS.warning.withValues(alpha: 0.15),
                DS.warning.withValues(alpha: 0.05),
              ],
            ),
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: DS.warning.withValues(alpha: 0.3),
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.local_fire_department_rounded,
                    color: DS.warning,
                    size: DS.iconSizeSm,
                  ),
                  const SizedBox(width: DS.spacing6),
                  Text(
                    '连胜',
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textSecondary,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    Icons.chevron_right,
                    size: DS.iconSizeSm,
                    color: DS.textTertiary,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              const DashboardStreakIndicator(),
            ],
          ),
        ),
      );
}

/// Theme toggle button widget
class _ThemeToggleButton extends StatelessWidget {
  const _ThemeToggleButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          boxShadow: DS.shadowSm,
          color: DS.surfaceSecondary,
          border: Border.all(color: DS.brandPrimaryConst, width: 1.5),
        ),
        child: Icon(
          isDark ? Icons.wb_sunny : Icons.nightlight_round,
          size: 20,
          color: DS.brandPrimaryConst,
        ),
      ),
    );
  }
}
