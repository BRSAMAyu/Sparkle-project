import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/leaderboard/data/models/self_anchor_model.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/self_anchor_provider.dart';
import 'package:sparkle/features/plan/plan_routes.dart';

/// D-COMM-1：自我 7 日锚视图（`GET /leaderboards/self-anchor`）。
///
/// D-COMM-1 裁决落地：全站综合榜保持 D17 隐藏，排行榜域唯一按裁决路由的
/// 产品面——本人近 7 日每日冲刺完成度/掌握度增量，只跟自己的历史比。
///
/// SPEC v1.0：必达项 2（① 窗口合计摘要 ② 每日完成柱状序列）；
/// 唯一交互 accent（brandPrimary），今日列以字重区分不作第二色；
/// `has_any_data:false` 为诚实空态——给引导，不画假零曲线。
class SelfAnchorScreen extends ConsumerWidget {
  const SelfAnchorScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final viewAsync = ref.watch(selfAnchorProvider);
    final colors = context.colors;
    final typo = context.typo;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.leaderboardSelfAnchorTitle),
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: () => ref.refresh(selfAnchorProvider.future),
          child: viewAsync.when(
            loading: () =>
                const _ScrollableStateFill(child: SparkleCardSkeleton()),
            error: (Object error, StackTrace stackTrace) =>
                _ScrollableStateFill(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: context.space.md),
                    child: CustomErrorWidget(
                      message:
                          context.l10n.leaderboardSelfAnchorLoadFailed(error),
                    ),
                  ),
                  SizedBox(height: context.space.md),
                  SparkleButton(
                    key: const ValueKey('self-anchor-retry-button'),
                    variant: ButtonVariant.outline,
                    label: context.l10n.leaderboardSelfAnchorRetry,
                    onPressed: () => ref.invalidate(selfAnchorProvider),
                  ),
                ],
              ),
            ),
            data: (SelfAnchorView view) {
              if (!view.hasAnyData) {
                return _ScrollableStateFill(
                  child: EmptyState(
                    key: const ValueKey('self-anchor-empty-state'),
                    icon: Icons.explore_off_outlined,
                    title: context.l10n.leaderboardSelfAnchorEmptyTitle,
                    description:
                        context.l10n.leaderboardSelfAnchorEmptyDescription,
                    actionText: context.l10n.leaderboardSelfAnchorEmptyAction,
                    onAction: () => unawaited(context.push(PlanRoutes.sprint)),
                  ),
                );
              }
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.all(context.space.md),
                children: [
                  _WindowSummaryCard(view: view),
                  SizedBox(height: context.space.md),
                  _DailySeriesCard(view: view),
                  SizedBox(height: context.space.md),
                  Text(
                    context.l10n.leaderboardSelfAnchorSubtitle,
                    style:
                        typo.labelSmall.copyWith(color: colors.textTertiary),
                    textAlign: TextAlign.center,
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

/// 必达项 ①：窗口合计摘要（完成 N 项冲刺任务 / 掌握度增量）。
class _WindowSummaryCard extends StatelessWidget {
  const _WindowSummaryCard({required this.view});

  final SelfAnchorView view;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;

    return GraphiteCardSurface(
      key: const ValueKey('self-anchor-summary-card'),
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.leaderboardSelfAnchorWindowTotal,
            style: typo.labelLarge.copyWith(color: colors.textSecondary),
          ),
          SizedBox(height: context.space.xs),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                '${view.totalTasksCompleted}',
                style: typo.displayLarge.copyWith(color: colors.textPrimary),
              ),
              SizedBox(width: context.space.sm),
              Text(
                context.l10n.leaderboardSelfAnchorTasksUnit,
                style: typo.bodyMedium.copyWith(color: colors.textSecondary),
              ),
            ],
          ),
          SizedBox(height: context.space.xs),
          Text(
            context.l10n.leaderboardSelfAnchorMasteryGained(
              view.totalMasteryDelta.toStringAsFixed(1),
            ),
            style: typo.bodyMedium.copyWith(color: colors.textSecondary),
          ),
        ],
      ),
    );
  }
}

/// 必达项 ②：每日完成柱状序列（7 列，旧→新；唯一 accent = brandPrimary）。
class _DailySeriesCard extends StatelessWidget {
  const _DailySeriesCard({required this.view});

  final SelfAnchorView view;

  static const double _chartHeight = 120;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final typo = context.typo;

    final maxTasks = view.series.fold<int>(
      1,
      (max, point) => point.tasksCompleted > max ? point.tasksCompleted : max,
    );
    final today = DateTime.now().toUtc();

    return GraphiteCardSurface(
      key: const ValueKey('self-anchor-series-card'),
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.leaderboardSelfAnchorSeriesTitle,
            style: typo.labelLarge.copyWith(color: colors.textSecondary),
          ),
          SizedBox(height: context.space.md),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              for (final point in view.series)
                Expanded(
                  child: _DayBar(point: point, maxTasks: maxTasks),
                ),
            ],
          ),
          SizedBox(height: context.space.sm),
          Row(
            children: [
              for (final point in view.series)
                Expanded(
                  child: Text(
                    _dayLabel(point.date),
                    style: typo.labelSmall.copyWith(
                      color: _isSameDay(point.date, today)
                          ? colors.textPrimary
                          : colors.textTertiary,
                      fontWeight: _isSameDay(point.date, today)
                          ? FontWeight.w700
                          : FontWeight.w400,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  static bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  static String _dayLabel(DateTime date) => '${date.month}/${date.day}';
}

/// 单日柱：accent 唯一走 brandPrimary；今日列以日期字重区分（不引入第二色）。
class _DayBar extends StatelessWidget {
  const _DayBar({required this.point, required this.maxTasks});

  final SelfAnchorDayPoint point;
  final int maxTasks;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final radius = context.radius;
    final fraction = point.tasksCompleted / maxTasks;
    final barHeight = (_DailySeriesCard._chartHeight * fraction)
        .clamp(2.0, _DailySeriesCard._chartHeight);

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: context.space.xs + 2),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          if (point.tasksCompleted > 0) ...[
            Text(
              '${point.tasksCompleted}',
              style:
                  context.typo.labelSmall.copyWith(color: colors.textSecondary),
            ),
            SizedBox(height: context.space.xs),
          ],
          Container(
            height: barHeight,
            decoration: BoxDecoration(
              color: colors.brandPrimary,
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(radius.sm),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ScrollableStateFill extends StatelessWidget {
  const _ScrollableStateFill({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            SizedBox(
              height: constraints.maxHeight,
              child: child,
            ),
          ],
        ),
      );
}
