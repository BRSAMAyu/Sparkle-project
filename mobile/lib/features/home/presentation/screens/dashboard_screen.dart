import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_card.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_calibration_strip.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/active_bottleneck_alert.dart';
import 'package:sparkle/features/home/presentation/widgets/compact_status_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/daily_context_line.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_section.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/metrics_row.dart';
import 'package:sparkle/features/home/presentation/widgets/next_action_prompt.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/today_growth_status_card.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Dashboard screen - extracted from HomeScreen
/// Displays the main project cockpit with bento grid layout
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  static const double _minimumOmniBarViewportInset = 92;
  static const double _omniBarComfortSpacing = 28;
  static const double _bottomScrollTailHeight = 24;
  static const double _omniBarExpandedBuffer = 96;
  bool _isBriefingExpanded = false;
  double? _omniBarHeight;

  Widget _staggeredSection({
    required int index,
    required Widget child,
  }) =>
      SparkleStaggerItem(
        index: index,
        child: child,
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

  void _handleOmniBarHeightChanged(double height) {
    if (_omniBarHeight != null && (_omniBarHeight! - height).abs() < 0.5) {
      return;
    }
    setState(() {
      _omniBarHeight = height;
    });
  }

  Future<void> _refreshHomeGrowthState() async {
    ref
      ..invalidate(homeActivePlanStatusProvider)
      ..invalidate(homeTodayTasksSnapshotProvider)
      ..invalidate(homeStreakProvider)
      ..invalidate(homePlanBottlenecksProvider)
      ..invalidate(homeDailyContextLineProvider)
      ..invalidate(homeGrowthDashboardSnapshotProvider)
      ..invalidate(homeGrowthStateProvider);

    try {
      await Future.wait([
        ref.read(homeGrowthStateProvider.future),
        ref.read(homeDailyContextLineProvider.future),
      ]);
    } catch (_) {
      // The card falls back to an empty-plan state if growth data is unavailable.
    }
  }

  void _openBottleneckChat(HomeBottleneck bottleneck) {
    final prompt = '我想换个方式理解${bottleneck.topic}。请结合这个卡点，帮我调整接下来的学习路径。';
    context.go(
      Uri(
        path: '/chat',
        queryParameters: {
          'prompt': prompt,
          'chat_mode': 'growth',
        },
      ).toString(),
    );
  }

  void _startNextAction(HomeGrowthTask task) {
    if (task.id.isEmpty) {
      unawaited(context.push('/tasks'));
      return;
    }

    final taskModel = task.taskModel;
    if (taskModel == null) {
      unawaited(context.push('/tasks/${task.id}'));
      return;
    }

    ref.read(activeTaskProvider.notifier).state = taskModel;
    unawaited(
      context.push('/tasks/${task.id}/execute?origin=home_growth'),
    );
  }

  Widget _buildFirstGoalEmptyState() => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing6,
            DS.spacing16,
            DS.spacing10,
          ),
          child: DashboardSectionShell(
            tone: DashboardSurfaceTone.hero,
            padding: const EdgeInsets.all(DS.spacing20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DashboardSectionHeader(
                  icon: Icons.auto_awesome_rounded,
                  iconSize: 40,
                  accentColor: DS.brandPrimary,
                  title: _isChinese ? '先定下你的第一个目标' : 'Set your first goal',
                  summary: _isChinese
                      ? '告诉我你最近最想推进的一件事，我会立刻帮你拆成可执行的计划。'
                      : 'Tell me the one thing you want to move forward, and I will turn it into an actionable plan.',
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
    final growthAsync = ref.watch(homeGrowthStateProvider);
    final dailyContextAsync = ref.watch(homeDailyContextLineProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final l10n = AppLocalizations.of(context)!;
    final showFirstGoalEmptyState =
        _shouldShowFirstGoalEmptyState(dashboardState);
    final textScale = MediaQuery.textScalerOf(context).scale(1);
    final mediaPadding = MediaQuery.paddingOf(context);
    final bottomSafeInset = mediaPadding.bottom;

    final category = ResponsiveSystem.getCategory(context);
    final fallbackOmniBarHeight = 52.0 +
        (predictions.isNotEmpty ? (textScale >= 1.2 ? 48.0 : 36.0) : 0.0);
    final measuredOmniBarHeight =
        (_omniBarHeight ?? fallbackOmniBarHeight).clamp(
      _minimumOmniBarViewportInset,
      fallbackOmniBarHeight + _omniBarExpandedBuffer,
    );
    final viewportBottomInset =
        measuredOmniBarHeight + bottomSafeInset + _omniBarComfortSpacing;
    final totalBottomHeight = bottomSafeInset + _bottomScrollTailHeight;

    // Max width for floating components on larger screens
    final floatingMaxWidth = switch (category) {
      DeviceCategory.tablet => DS.contentMaxWidthTablet,
      DeviceCategory.desktop => DS.contentMaxWidthDesktop,
      DeviceCategory.tv => DS.contentMaxWidthDesktop,
      DeviceCategory.watch => double.infinity,
      DeviceCategory.phone => double.infinity,
      DeviceCategory.phablet => double.infinity,
    };

    final growthState = growthAsync.maybeWhen(
      data: (state) => state,
      error: (_, __) => const HomeGrowthState.empty(),
      orElse: () => null,
    );
    final dailyContextLine = dailyContextAsync.maybeWhen(
      data: (line) => line,
      error: (_, __) => HomeDailyContextLine.fallback(),
      orElse: () => null,
    );
    final activeBottleneck = growthState?.activeBottleneck;
    var growthSectionIndex = 0;
    final growthSections = <Widget>[
      _staggeredSection(
        index: growthSectionIndex++,
        child: DailyContextLine(
          text: dailyContextLine?.text,
          isLoading: dailyContextLine == null && dailyContextAsync.isLoading,
        ),
      ),
      _staggeredSection(
        index: growthSectionIndex++,
        child: TodayGrowthStatusCard(
          state: growthState,
          isLoading: growthState == null && growthAsync.isLoading,
          onCreatePlan: () {
            unawaited(context.push('/plans/new?type=growth'));
          },
        ),
      ),
      if (activeBottleneck != null)
        _staggeredSection(
          index: growthSectionIndex++,
          child: ActiveBottleneckAlert(
            bottleneck: activeBottleneck,
            onOpenChat: _openBottleneckChat,
          ),
        ),
      _staggeredSection(
        index: growthSectionIndex++,
        child: NextActionPrompt(
          task: growthState?.nextAction,
          isLoading: growthState == null && growthAsync.isLoading,
          onStart: _startNextAction,
          onOpenTasks: () {
            unawaited(context.push('/tasks'));
          },
        ),
      ),
    ];

    var sectionIndex = growthSections.length;
    final dashboardSections = <Widget>[];
    if (dashboardState.isLoading) {
      dashboardSections.add(
        _staggeredSection(
          index: sectionIndex++,
          child: CompactStatusBar(
            user: user,
            dashboardState: dashboardState,
          ),
        ),
      );
      for (final skeleton in _buildDashboardSkeletonSections()) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: skeleton,
          ),
        );
      }
    } else {
      dashboardSections.addAll([
        _staggeredSection(
          index: sectionIndex++,
          child: CompactStatusBar(
            user: user,
            dashboardState: dashboardState,
          ),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: _DailyBriefingCard(
            dashboardState: dashboardState,
            isExpanded: _isBriefingExpanded,
            onToggleExpanded: () {
              setState(() {
                _isBriefingExpanded = !_isBriefingExpanded;
              });
            },
          ),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: MetricsRow(dashboardState: dashboardState),
        ),
      ]);

      if (showFirstGoalEmptyState) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: _buildFirstGoalEmptyState(),
          ),
        );
      } else {
        dashboardSections.addAll([
          _staggeredSection(
            index: sectionIndex++,
            child: const _DashboardUpdatesSection(),
          ),
          _staggeredSection(
            index: sectionIndex++,
            child: const DashboardCardSection(),
          ),
          _staggeredSection(
            index: sectionIndex++,
            child: const AchievementProgressCard(),
          ),
          _staggeredSection(
            index: sectionIndex++,
            child: const TaskBoardCard(),
          ),
        ]);
      }
    }

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
                await _refreshHomeGrowthState();
              },
              child: Padding(
                padding: EdgeInsets.only(bottom: viewportBottomInset),
                child: ScrollEdgeHaptics(
                  child: CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverList(
                        delegate: SliverChildListDelegate(
                          [
                            ...growthSections,
                            ...dashboardSections,
                            const AuroraCalibrationStrip(),
                          ],
                        ),
                      ),
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
          ),

          // Layer 3: Unified Omni-Bar (bottom)
          Positioned(
            left: 0,
            right: 0,
            bottom: bottomSafeInset + DS.spacing8,
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  child: UnifiedOmniBar(
                    hintText: l10n.typeMessage,
                    onHeightChanged: _handleOmniBarHeightChanged,
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

String _formatDeadlineLabel({
  required bool isChinese,
  required int daysToDeadline,
}) {
  if (daysToDeadline == 0) {
    return isChinese ? '今天截止' : 'Due today';
  }

  final absoluteDays = daysToDeadline.abs();
  final englishDayUnit = absoluteDays == 1 ? 'day' : 'days';
  if (daysToDeadline < 0) {
    return isChinese
        ? '已逾期 $absoluteDays 天'
        : '$absoluteDays $englishDayUnit overdue';
  }

  return isChinese
      ? '还有 $daysToDeadline 天'
      : '$daysToDeadline $englishDayUnit left';
}

class _DailyBriefingCard extends StatelessWidget {
  const _DailyBriefingCard({
    required this.dashboardState,
    required this.isExpanded,
    required this.onToggleExpanded,
  });

  final DashboardState dashboardState;
  final bool isExpanded;
  final VoidCallback onToggleExpanded;

  @override
  Widget build(BuildContext context) {
    final observation = dashboardState.whatChangedCard;
    final growthStatus = dashboardState.growthStatus;
    final nextMove = dashboardState.nextMoveCard;
    final task = dashboardState.mostImportantTask;
    final growthSignal = dashboardState.growthSignal;
    final activePlan = dashboardState.activePlanProgress;
    final nextActionCount = dashboardState.nextActions.length;
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    final hasObservation = observation != null || growthStatus != null;
    final hasNextMove = nextMove != null || task != null;
    final hasDetailSection = growthSignal != null || activePlan != null;

    if (!hasObservation && !hasNextMove && !hasDetailSection) {
      return const SizedBox.shrink();
    }

    final observationTitle = observation?.headline ?? growthStatus?.headline;
    final observationSummary = observation?.summary ?? growthStatus?.subtitle;
    final nextTitle = nextMove?.headline ?? task?.title;
    final nextSummary = nextMove?.summary ?? task?.reason;
    final estimatedMinutes =
        nextMove?.estimatedMinutes ?? task?.estimatedMinutes;
    final planName = nextMove?.planName ?? task?.planName;
    final daysToDeadline = nextMove?.daysToDeadline ?? task?.daysToDeadline;
    final taskId = nextMove?.taskId ?? task?.id;

    final summaryBits = <String>[
      if (hasNextMove) isChinese ? '1 个重点动作' : '1 main move',
      if (nextActionCount > 1)
        isChinese
            ? '另有 ${nextActionCount - 1} 项待推进'
            : '${nextActionCount - 1} more queued',
      if (activePlan != null)
        isChinese
            ? '${(activePlan.progress * 100).round()}% 进度'
            : '${(activePlan.progress * 100).round()}% progress',
    ];

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('dashboard-briefing-section'),
          tone: DashboardSurfaceTone.hero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.auto_awesome_rounded,
                iconSize: 40,
                accentColor: DS.brandPrimary,
                title: isChinese ? '今日总览' : 'Today Briefing',
                summary: summaryBits.isEmpty
                    ? (isChinese
                        ? '把最重要的事情压缩成一张卡'
                        : 'One place for the important stuff')
                    : summaryBits.join(' • '),
                trailing: SparkleIconButton(
                  key: const ValueKey('dashboard-briefing-toggle'),
                  variant: ButtonVariant.ghost,
                  size: 34,
                  onPressed: onToggleExpanded,
                  icon: AnimatedRotation(
                    turns: isExpanded ? 0.5 : 0,
                    duration: DS.durationFast,
                    child: const Icon(
                      Icons.expand_more_rounded,
                      size: 18,
                    ),
                  ),
                ),
              ),
              if (hasObservation) ...[
                const SizedBox(height: DS.spacing12),
                _BriefingBlock(
                  eyebrow: isChinese ? 'Sparkle 的观察' : 'What Sparkle Noticed',
                  title: observationTitle ?? '',
                  summary: observationSummary ?? '',
                ),
              ],
              if (hasNextMove) ...[
                const SizedBox(height: DS.spacing12),
                _BriefingBlock(
                  eyebrow: isChinese ? '今天先做这一步' : 'Start With This',
                  title: nextTitle ?? '',
                  summary: nextSummary ?? '',
                  footer: Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      if (estimatedMinutes != null && estimatedMinutes > 0)
                        _DashboardChip(
                          icon: Icons.schedule_rounded,
                          label: '$estimatedMinutes min',
                        ),
                      if (planName != null && planName.isNotEmpty)
                        _DashboardChip(
                          icon: Icons.flag_rounded,
                          label: planName,
                        ),
                      if (daysToDeadline != null)
                        _DashboardChip(
                          icon: Icons.timelapse_rounded,
                          label: _formatDeadlineLabel(
                            isChinese: isChinese,
                            daysToDeadline: daysToDeadline,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              _BriefingActions(
                isChinese: isChinese,
                hasTaskAction: taskId != null && taskId.isNotEmpty,
                taskId: taskId,
              ),
              ClipRect(
                child: AnimatedSize(
                  duration: DS.quick,
                  curve: DS.motionCurve(SparkleMotionToken.standard),
                  alignment: Alignment.topCenter,
                  child: !isExpanded
                      ? const SizedBox.shrink()
                      : Padding(
                          padding: const EdgeInsets.only(top: DS.spacing12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (growthSignal != null)
                                _BriefingDetailTile(
                                  icon: Icons.trending_up_rounded,
                                  iconColor: DS.success,
                                  title:
                                      isChinese ? '最近最明显的变化' : 'Growth Signal',
                                  headline: growthSignal.headline,
                                  summary: growthSignal.summary,
                                  trailing: growthSignal.source,
                                ),
                              if (growthSignal != null && activePlan != null)
                                const SizedBox(height: DS.spacing10),
                              if (activePlan != null)
                                _PlanProgressTile(
                                  plan: activePlan,
                                  isChinese: isChinese,
                                ),
                              if (nextActionCount > 1) ...[
                                const SizedBox(height: DS.spacing12),
                                Text(
                                  isChinese
                                      ? '除了当前重点，还有 ${nextActionCount - 1} 项任务在队列中。'
                                      : '${nextActionCount - 1} more tasks are still queued after this one.',
                                  style: context.sparkleTypography.bodySmall
                                      .copyWith(
                                    color: DS.textSecondary,
                                    height: 1.35,
                                  ),
                                ),
                              ],
                              const SizedBox(height: DS.spacing12),
                              Wrap(
                                spacing: DS.spacing10,
                                runSpacing: DS.spacing10,
                                children: [
                                  SparkleButton.ghost(
                                    label: isChinese ? '开始专注' : 'Start Focus',
                                    onPressed: () => context.push('/focus'),
                                  ),
                                  SparkleButton.ghost(
                                    label: 'Chat',
                                    onPressed: () => context.go('/chat'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BriefingBlock extends StatelessWidget {
  const _BriefingBlock({
    required this.eyebrow,
    required this.title,
    required this.summary,
    this.footer,
  });

  final String eyebrow;
  final String title;
  final String summary;
  final Widget? footer;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.82),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              eyebrow,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              title,
              style: context.sparkleTypography.titleLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                summary,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
            ],
            if (footer != null) ...[
              const SizedBox(height: DS.spacing12),
              footer!,
            ],
          ],
        ),
      );
}

class _BriefingActions extends StatelessWidget {
  const _BriefingActions({
    required this.isChinese,
    required this.hasTaskAction,
    required this.taskId,
  });

  final bool isChinese;
  final bool hasTaskAction;
  final String? taskId;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final primaryButton = SparkleButton.primary(
            label: hasTaskAction
                ? (isChinese ? '先做这个' : 'Start Here')
                : (isChinese ? '查看任务' : 'Open Tasks'),
            onPressed: () => hasTaskAction
                ? context.push('/tasks/$taskId')
                : context.push('/tasks'),
          );
          final secondaryButton = SparkleButton.ghost(
            label: isChinese ? '任务列表' : 'View Tasks',
            onPressed: () => context.push('/tasks'),
          );

          if (constraints.maxWidth < 360) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                primaryButton,
                const SizedBox(height: DS.spacing10),
                secondaryButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: primaryButton),
              const SizedBox(width: DS.spacing10),
              Expanded(child: secondaryButton),
            ],
          );
        },
      );
}

class _BriefingDetailTile extends StatelessWidget {
  const _BriefingDetailTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.headline,
    required this.summary,
    this.trailing,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String headline;
  final String summary;
  final String? trailing;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 18, color: iconColor),
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    headline,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    summary,
                    style: context.sparkleTypography.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.35,
                    ),
                  ),
                ],
              ),
            ),
            if (trailing != null && trailing!.isNotEmpty) ...[
              const SizedBox(width: DS.spacing8),
              Flexible(
                child: Text(
                  trailing!,
                  textAlign: TextAlign.right,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      );
}

class _PlanProgressTile extends StatelessWidget {
  const _PlanProgressTile({
    required this.plan,
    required this.isChinese,
  });

  final ActivePlanProgressData plan;
  final bool isChinese;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    isChinese ? '当前主计划' : 'Active Plan',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                Text(
                  '${(plan.progress * 100).round()}%',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              plan.name,
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ClipRRect(
              borderRadius: DS.borderRadiusFull,
              child: LinearProgressIndicator(
                minHeight: 8,
                value: plan.progress.clamp(0, 1),
                backgroundColor: DS.surfaceOverlay,
                valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              isChinese
                  ? '阶段：${plan.phase.isEmpty ? '进行中' : plan.phase}'
                  : 'Phase: ${plan.phase.isEmpty ? 'in progress' : plan.phase}',
              style: context.sparkleTypography.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            if (plan.daysToDeadline != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                isChinese
                    ? '距离截止还有 ${plan.daysToDeadline} 天'
                    : '${plan.daysToDeadline} days to deadline',
                style: context.sparkleTypography.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ],
        ),
      );
}

class _DashboardUpdatesSection extends ConsumerStatefulWidget {
  const _DashboardUpdatesSection();

  @override
  ConsumerState<_DashboardUpdatesSection> createState() =>
      _DashboardUpdatesSectionState();
}

class _DashboardUpdatesSectionState
    extends ConsumerState<_DashboardUpdatesSection> {
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = ref.read(notificationCenterProvider);
      if (!state.isLoading && state.notifications.isEmpty) {
        unawaited(
          ref.read(notificationCenterProvider.notifier).loadNotifications(),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final unreadMessages = ref.watch(unreadMessageCountProvider);
    final unreadNotifications =
        ref.watch(unreadNotificationsProvider).maybeWhen(
              data: (notifications) => notifications.length,
              orElse: () => 0,
            );
    final notificationCenterState = ref.watch(notificationCenterProvider);
    final systemUpdates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );
    final reviewAsync = ref.watch(nightlyReviewProvider);
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');

    final insightCount = _recentInsightCount(
      notificationCenterState.notifications,
      systemUpdates,
    );
    final hasPendingReview = reviewAsync.maybeWhen(
      data: (review) =>
          review != null &&
          review.widgetPayload != null &&
          review.status != 'reviewed',
      orElse: () => false,
    );
    final hasPrediction = dashboardState.nextIntentForecast != null &&
        dashboardState.nextIntentForecast!.title.isNotEmpty &&
        dashboardState.nextIntentForecast!.summary.isNotEmpty;

    final summaryBits = <String>[
      if (hasPrediction) isChinese ? '预测建议' : 'prediction',
      if (unreadMessages > 0)
        isChinese ? '$unreadMessages 条消息' : '$unreadMessages messages',
      if (unreadNotifications > 0)
        isChinese ? '$unreadNotifications 条通知' : '$unreadNotifications alerts',
      if (insightCount > 0)
        isChinese ? '$insightCount 条洞察' : '$insightCount insights',
      if (hasPendingReview) isChinese ? '夜间复盘待处理' : 'review pending',
    ];

    if (summaryBits.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing4,
            ),
            child: DashboardSectionShell(
              key: const ValueKey('dashboard-updates-section'),
              tone: DashboardSurfaceTone.summary,
              padding: const EdgeInsets.all(14),
              child: InkWell(
                onTap: _toggleExpanded,
                borderRadius: DS.borderRadius16,
                child: DashboardSectionHeader(
                  icon: Icons.notifications_active_outlined,
                  accentColor: DS.info,
                  title: isChinese ? '更新与洞察' : 'Updates & Insights',
                  summary: summaryBits.take(3).join(' • '),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _SectionCountPill(count: summaryBits.length),
                      const SizedBox(width: DS.spacing8),
                      SparkleIconButton(
                        key: const ValueKey('dashboard-updates-toggle'),
                        variant: ButtonVariant.ghost,
                        size: 34,
                        onPressed: _toggleExpanded,
                        icon: AnimatedRotation(
                          turns: _isExpanded ? 0.5 : 0,
                          duration: DS.durationFast,
                          child: const Icon(
                            Icons.expand_more_rounded,
                            size: 18,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        ClipRect(
          child: AnimatedSize(
            duration: DS.quick,
            curve: DS.motionCurve(SparkleMotionToken.standard),
            alignment: Alignment.topCenter,
            child: !_isExpanded
                ? const SizedBox.shrink()
                : const Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      PredictedIntentCard(),
                      HomeNotificationCard(),
                      RecentInsightsCard(),
                      NightlyReviewPanel(compact: true),
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  int _recentInsightCount(
    List<UnifiedNotification> notifications,
    List<Map<String, dynamic>> systemUpdates,
  ) {
    final totalNotifications = notifications.where((item) {
      final type = item.type?.toString() ?? '';
      return type.startsWith('theater_') ||
          type == 'learning_report_ready' ||
          type == 'simulation_session_ready';
    }).length;

    final totalSystemUpdates = systemUpdates.where((item) {
      final type = item['type']?.toString() ?? '';
      return type.startsWith('theater_') ||
          type == 'learning_report_ready' ||
          type == 'simulation_session_ready';
    }).length;

    return totalNotifications + totalSystemUpdates;
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }
}

class _SectionCountPill extends StatelessWidget {
  const _SectionCountPill({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          '$count',
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightBold,
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
