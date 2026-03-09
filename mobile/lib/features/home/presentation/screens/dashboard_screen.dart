import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar_heatmap_card.dart';
import 'package:sparkle/features/home/presentation/widgets/cognitive_tool_hub_card.dart';
import 'package:sparkle/features/home/presentation/widgets/compact_status_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_curiosity_card.dart';
import 'package:sparkle/features/home/presentation/widgets/focus_card.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/long_term_plan_card.dart';
import 'package:sparkle/features/home/presentation/widgets/metrics_row.dart';
import 'package:sparkle/features/home/presentation/widgets/next_actions_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Dashboard screen - extracted from HomeScreen
/// Displays the main project cockpit with bento grid layout
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  double _bottomOverlayHeight = 52;

  void _handleUnifiedOmniBarHeightChanged(double height) {
    if ((height - _bottomOverlayHeight).abs() < 0.5) {
      return;
    }
    setState(() {
      _bottomOverlayHeight = height;
    });
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final l10n = AppLocalizations.of(context)!;

    final category = ResponsiveSystem.getCategory(context);
    final fallbackBottomHeight = 52.0 + (predictions.isNotEmpty ? 36.0 : 0.0);
    final totalBottomHeight = (_bottomOverlayHeight > 0
            ? _bottomOverlayHeight
            : fallbackBottomHeight) +
        DS.spacing16;

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
                  SliverToBoxAdapter(
                    child: CompactStatusBar(
                      user: user,
                      dashboardState: dashboardState,
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: MetricsRow(dashboardState: dashboardState),
                  ),
                  SliverToBoxAdapter(
                    child: NextActionsCard(
                      compact: true,
                      onViewAll: () => context.push('/tasks'),
                    ),
                  ),
                  const SliverToBoxAdapter(child: HomeNotificationCard()),
                  const SliverToBoxAdapter(child: NightlyReviewPanel()),
                  const SliverToBoxAdapter(
                    child: SizedBox(height: DS.spacing8),
                  ),
                  SliverToBoxAdapter(
                    child: _buildBentoGrid(context, dashboardState),
                  ),
                  const SliverToBoxAdapter(
                    child: SizedBox(height: DS.spacing16),
                  ),
                  const SliverToBoxAdapter(child: TaskBoardCard()),

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

          // Layer 3: Unified Omni-Bar (bottom)
          Positioned(
            left: 0,
            right: 0,
            bottom: DS.spacing8,
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  child: UnifiedOmniBar(
                    hintText: l10n.typeMessage,
                    onHeightChanged: _handleUnifiedOmniBarHeightChanged,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

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
            // Card B: Cognitive Tool Hub
            const StaggeredGridTile.fit(
              crossAxisCellCount: 1,
              child: CognitiveToolHubCard(),
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
