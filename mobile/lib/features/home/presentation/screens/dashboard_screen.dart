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
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
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
  static const double _bottomOverlayReserveHeight = 148;

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

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final l10n = AppLocalizations.of(context)!;
    final showFirstGoalEmptyState =
        _shouldShowFirstGoalEmptyState(dashboardState);
    final textScale = MediaQuery.textScalerOf(context).scale(1);

    final category = ResponsiveSystem.getCategory(context);
    final fallbackBottomHeight = 52.0 +
        (predictions.isNotEmpty ? (textScale >= 1.2 ? 48.0 : 36.0) : 0.0);
    final overlayReserveHeight =
        _bottomOverlayReserveHeight + ((textScale - 1).clamp(0.0, 0.5) * 56);
    final totalBottomHeight = (overlayReserveHeight > fallbackBottomHeight
            ? overlayReserveHeight
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
                      ..._buildDashboardSkeletonSections().asMap().entries.map(
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
                        child:
                            _GrowthStatusCard(dashboardState: dashboardState),
                      ),
                      _staggeredSection(
                        index: 2,
                        child: MetricsRow(dashboardState: dashboardState),
                      ),
                      if (showFirstGoalEmptyState)
                        _staggeredSection(
                          index: 3,
                          child: _buildFirstGoalEmptyState(),
                        )
                      else ...[
                        _staggeredSection(
                          index: 3,
                          child: _MostImportantThingCard(
                            task: dashboardState.mostImportantTask,
                            nextMoveCard: dashboardState.nextMoveCard,
                          ),
                        ),
                        _staggeredSection(
                          index: 4,
                          child: _GrowthSignalCard(
                            signal: dashboardState.growthSignal,
                          ),
                        ),
                        _staggeredSection(
                          index: 5,
                          child: _ActivePlanProgressCard(
                            plan: dashboardState.activePlanProgress,
                          ),
                        ),
                        _staggeredSection(
                          index: 6,
                          child: const _DashboardQuickActionsRow(),
                        ),
                        _staggeredSection(
                          index: 7,
                          child: NextActionsCard(
                            compact: true,
                            onViewAll: () => context.push('/tasks'),
                          ),
                        ),
                        _staggeredSection(
                          index: 8,
                          child: const PredictedIntentCard(),
                        ),
                        _staggeredSection(
                          index: 9,
                          child: const HomeNotificationCard(),
                        ),
                        _staggeredSection(
                          index: 10,
                          child: const RecentInsightsCard(),
                        ),
                        _staggeredSection(
                          index: 11,
                          child: const NightlyReviewPanel(),
                        ),
                        _staggeredSection(
                          index: 12,
                          child: const DashboardCardSection(),
                        ),
                        _staggeredSection(
                          index: 13,
                          child: const AchievementProgressCard(),
                        ),
                        _staggeredSection(
                          index: 14,
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

class _GrowthStatusCard extends StatelessWidget {
  const _GrowthStatusCard({required this.dashboardState});

  final DashboardState dashboardState;

  @override
  Widget build(BuildContext context) {
    final growthStatus = dashboardState.growthStatus;
    final whatChangedCard = dashboardState.whatChangedCard;
    if (growthStatus == null && whatChangedCard == null) {
      return const SizedBox.shrink();
    }
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context).copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.brandPrimary.withValues(alpha: 0.18),
                DS.info.withValues(alpha: 0.12),
                DS.surfacePrimaryElevated,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.brandPrimary.withValues(alpha: 0.18),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isChinese ? 'Sparkle 的观察' : 'What Sparkle Noticed',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textSecondary,
                  letterSpacing: 0.2,
                ),
              ),
              if (whatChangedCard != null) ...[
                const SizedBox(height: DS.spacing6),
                Text(
                  whatChangedCard.timeframeLabel,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing8),
              Text(
                whatChangedCard?.headline ?? growthStatus!.headline,
                style: context.sparkleTypography.headingMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                whatChangedCard?.summary ?? growthStatus!.subtitle,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
              if (whatChangedCard != null &&
                  whatChangedCard.highlights.length > 1) ...[
                const SizedBox(height: DS.spacing12),
                ...whatChangedCard.highlights.skip(1).take(2).map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(
                                top: 7,
                                right: DS.spacing8,
                              ),
                              child: Container(
                                width: 5,
                                height: 5,
                                decoration: BoxDecoration(
                                  color: DS.brandPrimary,
                                  borderRadius: DS.borderRadiusFull,
                                ),
                              ),
                            ),
                            Expanded(
                              child: Text(
                                item,
                                style: context.sparkleTypography.bodySmall
                                    .copyWith(
                                  color: DS.textSecondary,
                                  height: 1.35,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _MostImportantThingCard extends StatelessWidget {
  const _MostImportantThingCard({
    required this.task,
    required this.nextMoveCard,
  });

  final PriorityTaskData? task;
  final NextMoveCardData? nextMoveCard;

  @override
  Widget build(BuildContext context) {
    if (task == null && nextMoveCard == null) {
      return const SizedBox.shrink();
    }
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isChinese ? '今天最值得先做的一步' : 'Best Next Step',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                nextMoveCard?.headline ?? task!.title,
                style: context.sparkleTypography.titleLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                nextMoveCard?.summary ?? task!.reason,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
              if (nextMoveCard != null && nextMoveCard!.whyNow.isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  nextMoveCard!.whyNow,
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _DashboardChip(
                    icon: Icons.schedule_rounded,
                    label:
                        '${nextMoveCard?.estimatedMinutes ?? task!.estimatedMinutes} min',
                  ),
                  if ((nextMoveCard?.planName ?? task?.planName) != null &&
                      (nextMoveCard?.planName ?? task?.planName)?.isNotEmpty ==
                          true)
                    _DashboardChip(
                      icon: Icons.flag_rounded,
                      label: nextMoveCard?.planName ?? task!.planName!,
                    ),
                  if ((nextMoveCard?.daysToDeadline ?? task?.daysToDeadline) !=
                      null)
                    _DashboardChip(
                      icon: Icons.timelapse_rounded,
                      label: isChinese
                          ? '还有 ${nextMoveCard?.daysToDeadline ?? task!.daysToDeadline} 天'
                          : '${nextMoveCard?.daysToDeadline ?? task!.daysToDeadline} days left',
                    ),
                ],
              ),
              if (nextMoveCard != null &&
                  nextMoveCard!.reassurance.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                Text(
                  nextMoveCard!.reassurance,
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.primary(
                      label: isChinese ? '先做这个' : 'Start Here',
                      onPressed: () => context.push(
                        '/tasks/${nextMoveCard?.taskId ?? task!.id}',
                      ),
                    ),
                  ),
                  const SizedBox(width: DS.spacing10),
                  Expanded(
                    child: SparkleButton.ghost(
                      label: isChinese ? '查看全部任务' : 'View Tasks',
                      onPressed: () => context.push('/tasks'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GrowthSignalCard extends StatelessWidget {
  const _GrowthSignalCard({required this.signal});

  final GrowthSignalData? signal;

  @override
  Widget build(BuildContext context) {
    if (signal == null) {
      return const SizedBox.shrink();
    }
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing10,
          DS.spacing16,
          DS.spacing10,
        ),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context).copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.success.withValues(alpha: 0.12),
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.success.withValues(alpha: 0.16),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isChinese ? '这段时间最明显的变化' : 'Growth Signal',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                signal!.headline,
                style: context.sparkleTypography.titleLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                signal!.summary,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: DS.spacing10),
              Text(
                isChinese
                    ? '依据：${signal!.source}'
                    : 'Source: ${signal!.source}',
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActivePlanProgressCard extends StatelessWidget {
  const _ActivePlanProgressCard({required this.plan});

  final ActivePlanProgressData? plan;

  @override
  Widget build(BuildContext context) {
    if (plan == null) {
      return const SizedBox.shrink();
    }
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic(context),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isChinese ? '当前主计划进度' : 'Active Plan Progress',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                plan!.name,
                style: context.sparkleTypography.titleLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                isChinese
                    ? '阶段：${plan!.phase.isEmpty ? '进行中' : plan!.phase}'
                    : 'Phase: ${plan!.phase.isEmpty ? 'in progress' : plan!.phase}',
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              ClipRRect(
                borderRadius: DS.borderRadiusFull,
                child: LinearProgressIndicator(
                  minHeight: 10,
                  value: plan!.progress.clamp(0, 1),
                  backgroundColor: DS.surfaceOverlay,
                  valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                ),
              ),
              const SizedBox(height: DS.spacing10),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      isChinese
                          ? '进度 ${(plan!.progress * 100).round()}%'
                          : 'Progress ${(plan!.progress * 100).round()}%',
                      style: context.sparkleTypography.labelLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                  if (plan!.daysToDeadline != null)
                    Text(
                      isChinese
                          ? '距离截止还有 ${plan!.daysToDeadline} 天'
                          : '${plan!.daysToDeadline} days to deadline',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardQuickActionsRow extends StatelessWidget {
  const _DashboardQuickActionsRow();

  @override
  Widget build(BuildContext context) => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing10,
            DS.spacing16,
            DS.spacing8,
          ),
          child: Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: 'Start Focus',
                  onPressed: () => context.push('/focus'),
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: SparkleButton.ghost(
                  label: "Today's Tasks",
                  onPressed: () => context.push('/tasks'),
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: SparkleButton.ghost(
                  label: 'Chat',
                  onPressed: () => context.go('/chat'),
                ),
              ),
            ],
          ),
        ),
      );
}

class _DashboardChip extends StatelessWidget {
  const _DashboardChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}
