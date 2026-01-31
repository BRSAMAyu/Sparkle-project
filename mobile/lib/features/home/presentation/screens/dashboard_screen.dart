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
    // OmniBar: ~52px, MultiAgentBar: ~44px, IntentPredictionBar: ~36px
    final omniBarHeight = 52.0;
    final multiAgentBarHeight = 44.0;
    final intentBarHeight = 36.0;
    final spacing = 8.0;

    // Calculate cumulative bottom positions
    final omniBarBottom = spacing; // 16
    final multiAgentBarBottom = omniBarBottom + omniBarHeight + spacing; // ~76
    final intentBarBottom = multiAgentBarBottom + multiAgentBarHeight + spacing; // ~128
    final totalBottomHeight = intentBarBottom + intentBarHeight + spacing; // ~172

    // Max width for floating components on larger screens
    final floatingMaxWidth = switch (category) {
      DeviceCategory.tablet => DS.contentMaxWidthTablet,
      DeviceCategory.desktop => DS.contentMaxWidthDesktop,
      DeviceCategory.tv => DS.contentMaxWidthDesktop,
      DeviceCategory.watch => double.infinity,
      DeviceCategory.phone => double.infinity,
      DeviceCategory.phablet => double.infinity,
    };

    return Scaffold(
      extendBody: true,
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
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
                  // Top Overlay
                  SliverToBoxAdapter(
                      child: _buildTopOverlay(context, user, l10n),),

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
                      height: totalBottomHeight + (hasPredictions ? 40 : 0),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Layer 3: Intent Prediction Bar (only show when has predictions)
          if (hasPredictions)
            Positioned(
              left: 0,
              right: 0,
              bottom: intentBarBottom,
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                    child: const IntentPredictionBar(),
                  ),
                ),
              ),
            ),

          // Layer 4: MultiAgent Bar (always show above OmniBar)
          Positioned(
            left: 0,
            right: 0,
            bottom: multiAgentBarBottom,
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

          // Layer 6: Theme Toggle Button - responsive positioning
          _buildThemeToggleButton(context, ref, isSmallScreen, multiAgentBarBottom),
        ],
      ),
    );
  }

  /// Build theme toggle button with responsive positioning
  /// On small screens: top-right corner
  /// On larger screens: right side floating above MultiAgentBar
  Widget _buildThemeToggleButton(
    BuildContext context,
    WidgetRef ref,
    bool isSmallScreen,
    double multiAgentBarBottom,
  ) {
    if (isSmallScreen) {
      // Small screen: position at top-right
      return Positioned(
        top: 8,
        right: 8,
        child: _ThemeToggleButton(onTap: () {
          ref.read(themeManagerProvider).toggleDarkMode();
        }),
      );
    }

    // Larger screen: position to the right of MultiAgentBar
    return Positioned(
      right: 8,
      bottom: multiAgentBarBottom + 8, // Slightly above MultiAgentBar
      child: _ThemeToggleButton(onTap: () {
        ref.read(themeManagerProvider).toggleDarkMode();
      }),
    );
  }

  Widget _buildTopOverlay(
          BuildContext context, UserModel? user, AppLocalizations l10n,) =>
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundImage:
                  user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
              backgroundColor: DS.primaryBase,
              child: user?.avatarUrl == null
                  ? Text((user?.nickname ?? 'U')[0].toUpperCase())
                  : null,
            ),
            const SizedBox(width: 10),
            Column(
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
                  user?.nickname ?? (user?.username ?? l10n.exploreGalaxy),
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightBold,
                    color: DS.brandPrimaryConst,
                  ),
                ),
              ],
            ),
          ],
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
          // Card A: Focus Core (2x1.5)
          StaggeredGridTile.count(
            crossAxisCellCount: 2,
            mainAxisCellCount: 1.5,
            child: FocusCard(onTap: () => context.push('/focus')),
          ),
          // Card E: Calendar Heatmap (1x1)
          const StaggeredGridTile.count(
            crossAxisCellCount: 1,
            mainAxisCellCount: 1,
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
