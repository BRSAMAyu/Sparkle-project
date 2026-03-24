import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_card.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/compact_status_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_section.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/metrics_row.dart';
import 'package:sparkle/features/home/presentation/widgets/next_actions_card.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';
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

  SliverToBoxAdapter _staggeredSection({
    required int index,
    required Widget child,
  }) =>
      SliverToBoxAdapter(
        child: SparkleStaggerItem(
          index: index,
          child: child,
        ),
      );

  bool _shouldShowFirstGoalEmptyState(DashboardState state) {
    if (state.isLoading || state.error != null) {
      return false;
    }
    return state.nextActions.isEmpty &&
        state.sprint == null &&
        state.growth == null;
  }

  bool get _isChinese => Localizations.localeOf(context)
      .languageCode
      .toLowerCase()
      .startsWith('zh');

  Widget _buildFirstGoalEmptyState() => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing6,
          DS.spacing16,
          DS.spacing10,
        ),
        child: Container(
          padding: const EdgeInsets.all(DS.spacing20),
          decoration: BoxDecoration(
            color: DS.surfacePanel.withValues(alpha: 0.78),
            borderRadius: BorderRadius.circular(DS.radius20),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.12),
            ),
            boxShadow: [
              BoxShadow(
                color: DS.brandPrimary.withValues(alpha: 0.08),
                blurRadius: 30,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      DS.brandPrimary.withValues(alpha: 0.92),
                      DS.info.withValues(alpha: 0.88),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: const Icon(
                  Icons.auto_awesome_rounded,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                _isChinese ? '先定下你的第一个目标' : 'Set your first goal',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                _isChinese
                    ? '告诉我你最近最想推进的一件事，我会立刻帮你拆成可执行的计划。'
                    : 'Tell me the one thing you want to move forward, and I will turn it into an actionable plan.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              Wrap(
                spacing: DS.spacing12,
                runSpacing: DS.spacing10,
                children: [
                  SparkleButton.primary(
                    label: _isChinese ? '和 AI 定目标' : 'Start with AI',
                    onPressed: () => context.go('/chat'),
                  ),
                  SparkleButton.ghost(
                    label: _isChinese ? '查看任务列表' : 'Open tasks',
                    onPressed: () => context.push('/tasks'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  List<Widget> _buildDashboardSkeletonSections() => const [
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: SparkleChatBubbleSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
      ];

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
    final showFirstGoalEmptyState =
        _shouldShowFirstGoalEmptyState(dashboardState);

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
          Positioned.fill(
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: const Alignment(0.82, -0.28),
                    radius: 1.0,
                    colors: [
                      DS.info.withValues(alpha: 0.1),
                      DS.brandPrimary.withValues(alpha: 0.04),
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.42, 1.0],
                  ),
                ),
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
              child: ScrollEdgeHaptics(
                child: CustomScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  slivers: [
                  if (dashboardState.isLoading) ...[
                    _staggeredSection(
                      index: 0,
                      child: CompactStatusBar(
                        user: user,
                        dashboardState: dashboardState,
                      ),
                    ),
                    ..._buildDashboardSkeletonSections()
                        .asMap()
                        .entries
                        .map(
                          (entry) => _staggeredSection(
                            index: entry.key + 1,
                            child: entry.value,
                          ),
                        ),
                  ] else ...[
                    _staggeredSection(
                      index: 0,
                      child: CompactStatusBar(
                        user: user,
                        dashboardState: dashboardState,
                      ),
                    ),
                    _staggeredSection(
                      index: 1,
                      child: MetricsRow(dashboardState: dashboardState),
                    ),
                    if (showFirstGoalEmptyState)
                      _staggeredSection(
                        index: 2,
                        child: _buildFirstGoalEmptyState(),
                      )
                    else ...[
                      _staggeredSection(
                        index: 2,
                        child: NextActionsCard(
                          compact: true,
                          onViewAll: () => context.push('/tasks'),
                        ),
                      ),
                      _staggeredSection(
                        index: 3,
                        child: const PredictedIntentCard(),
                      ),
                      _staggeredSection(
                        index: 4,
                        child: const HomeNotificationCard(),
                      ),
                      _staggeredSection(
                        index: 5,
                        child: const NightlyReviewPanel(),
                      ),
                      _staggeredSection(
                        index: 6,
                        child: const DashboardCardSection(),
                      ),
                      _staggeredSection(
                        index: 7,
                        child: const AchievementProgressCard(),
                      ),
                      _staggeredSection(
                        index: 8,
                        child: const TaskBoardCard(),
                      ),
                    ],
                  ],

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
}
