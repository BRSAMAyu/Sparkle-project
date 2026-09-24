import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/today_cockpit_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// J-03 Today Cockpit 主入口卡。
///
/// 产品契约（v3/03_modules/HOME.md）：
/// 1. 全页唯一 Primary Action（本卡的 [SparkleButton.primary]，其它卡片
///    均降级为折叠 slot / ghost 入口）；
/// 2. 携带 why（为什么是现在）+ goal context；
/// 3. 「我卡住了」作为统一的次级恢复入口（J-05 全旅程的 home 落点）；
/// 4. 当前 agent run 进行中时展示 current run 条（真实 WS 运行态）。
/// 四态（fresh / no-goal / active / stalled）由 [todayCockpitProvider]
/// 派生，本组件只做事实 → 文案渲染。
class TodayCockpitCard extends ConsumerWidget {
  const TodayCockpitCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final vm = ref.watch(todayCockpitProvider);

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing12,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('today-cockpit-card'),
          tone: DashboardSurfaceTone.hero,
          child: AnimatedSwitcher(
            duration: context.reduceMotion ? Duration.zero : DS.quick,
            child: vm.isLoading
                ? const _CockpitSkeleton()
                : _CockpitContent(vm: vm),
          ),
        ),
      ),
    );
  }
}

class _CockpitContent extends ConsumerWidget {
  const _CockpitContent({required this.vm});

  final TodayCockpitVm vm;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final accent = _accentColor();
    final headline = _headline(l10n);
    final why = _whyLine(l10n);

    return Column(
      key: const ValueKey('today-cockpit-content'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.12),
                borderRadius: DS.borderRadius16,
                border: Border.all(color: accent.withValues(alpha: 0.18)),
              ),
              child: Icon(
                vm.mode == TodayCockpitMode.stalled
                    ? Icons.priority_high_rounded
                    : vm.action == TodayCockpitAction.startTask
                        ? Icons.play_arrow_rounded
                        : Icons.auto_awesome_rounded,
                color: accent,
                size: 22,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _eyebrow(l10n),
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Semantics(
                    header: true,
                    child: Text(
                      headline,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.typo.titleLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                        height: 1.18,
                      ),
                    ),
                  ),
                  if (why != null) ...[
                    const SizedBox(height: DS.spacing8),
                    Text(
                      why,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.typo.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.52,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        if (vm.hasGoalContext) ...[
          const SizedBox(height: DS.spacing12),
          _GoalContextRow(vm: vm),
        ],
        if (vm.runIsActive) ...[
          const SizedBox(height: DS.spacing12),
          _CurrentRunStrip(runLabel: vm.runLabel),
        ],
        const SizedBox(height: DS.spacing16),
        // 唯一 primary CTA —— 首屏 filled 按钮只此一个。
        SparkleButton.primary(
          key: const ValueKey('today-cockpit-primary-cta'),
          label: _primaryLabel(l10n),
          icon: Icon(_primaryIcon()),
          expand: true,
          onPressed: () => _executePrimary(context, ref),
        ),
        const SizedBox(height: DS.spacing8),
        // 次级恢复入口：「我卡住了」（J-05 统一恢复旅程的 home 落点）。
        // stalled 态下主 CTA 已是卡点恢复，这里退化为「先看任务」。
        Center(
          child: SparkleButton.ghost(
            key: const ValueKey('today-cockpit-stuck-cta'),
            label: vm.mode == TodayCockpitMode.stalled
                ? l10n.dashboardOpenTasks
                : l10n.todayCockpitStuckButton,
            icon: Icon(
              vm.mode == TodayCockpitMode.stalled
                  ? Icons.list_alt_rounded
                  : Icons.help_outline_rounded,
            ),
            onPressed: () => _executeSecondary(context, ref),
          ),
        ),
        if (vm.mode == TodayCockpitMode.noGoal) ...[
          const SizedBox(height: DS.spacing12),
          _GoalStarters(),
        ],
      ],
    );
  }

  Color _accentColor() => switch (vm.mode) {
        TodayCockpitMode.stalled => DS.warning,
        TodayCockpitMode.active => DS.success,
        TodayCockpitMode.noGoal => DS.info,
        TodayCockpitMode.fresh => DS.brandPrimary,
      };

  String _eyebrow(AppLocalizations l10n) => switch (vm.mode) {
        TodayCockpitMode.noGoal => l10n.dashboardCommandCenterNow,
        TodayCockpitMode.stalled => l10n.todayCockpitEyebrowStalled,
        TodayCockpitMode.active => l10n.todayCockpitEyebrowActive,
        TodayCockpitMode.fresh => l10n.todayCockpitEyebrowFresh,
      };

  String _headline(AppLocalizations l10n) {
    final task = vm.taskToStart;
    if (vm.mode != TodayCockpitMode.noGoal && task != null) {
      return task.title;
    }
    return switch (vm.mode) {
      TodayCockpitMode.noGoal => l10n.dashboardSetFirstGoal,
      TodayCockpitMode.stalled => l10n.todayCockpitStalledHeadline,
      TodayCockpitMode.active =>
        vm.tasksTotal > 0 && vm.tasksCompleted >= vm.tasksTotal
            ? l10n.todayCockpitAllDoneHeadline
            : l10n.todayCockpitActiveHeadline,
      TodayCockpitMode.fresh =>
        vm.tasksTotal > 0
            ? l10n.todayCockpitFreshHeadline
            : l10n.todayCockpitFreshUnarrangedHeadline,
    };
  }

  /// why-now：按信号强度取最相关的一条（瓶颈 > 截止 > 停滞 > 健康度 > 余量）。
  String? _whyLine(AppLocalizations l10n) {
    if (vm.mode == TodayCockpitMode.noGoal) {
      return l10n.dashboardSetFirstGoalSummary;
    }
    final bottleneck = vm.bottleneckTopic;
    if (bottleneck != null) {
      return l10n.todayCockpitWhyBottleneck(bottleneck);
    }
    final deadline = vm.deadlineDays;
    if (deadline != null) {
      if (deadline == 0) return l10n.todayCockpitWhyDueToday;
      if (deadline < 0) return l10n.todayCockpitWhyOverdue(-deadline);
      return l10n.todayCockpitWhyDueIn(deadline);
    }
    if (vm.staleGuard) {
      return l10n.todayCockpitWhyStale;
    }
    final health = vm.planHealthPercent;
    if (health != null) {
      return l10n.todayCockpitWhyHealth(health);
    }
    if (vm.tasksTotal > vm.tasksCompleted) {
      return l10n.todayCockpitWhyRemaining(vm.tasksTotal - vm.tasksCompleted);
    }
    if (vm.tasksTotal > 0) {
      return l10n.todayCockpitWhyAllDone;
    }
    return null;
  }

  String _primaryLabel(AppLocalizations l10n) => switch (vm.action) {
        TodayCockpitAction.setGoal => l10n.dashboardStartWithAI,
        TodayCockpitAction.startTask => l10n.dashboardStartHere,
        TodayCockpitAction.arrangeToday => l10n.todayCockpitCtaArrange,
        TodayCockpitAction.openTasks => l10n.dashboardOpenTasks,
        TodayCockpitAction.stuckRecovery => l10n.todayCockpitCtaStuck,
      };

  IconData _primaryIcon() => switch (vm.action) {
        TodayCockpitAction.setGoal => Icons.auto_awesome_rounded,
        TodayCockpitAction.startTask => Icons.play_arrow_rounded,
        TodayCockpitAction.arrangeToday => Icons.event_note_rounded,
        TodayCockpitAction.openTasks => Icons.list_alt_rounded,
        TodayCockpitAction.stuckRecovery => Icons.healing_rounded,
      };

  void _executePrimary(BuildContext context, WidgetRef ref) {
    switch (vm.action) {
      case TodayCockpitAction.setGoal:
        context.go('/goals/new');
      case TodayCockpitAction.startTask:
        _startTask(context, ref);
      case TodayCockpitAction.arrangeToday:
        unawaited(context.push('/plans/new?type=growth'));
      case TodayCockpitAction.openTasks:
        unawaited(context.push('/tasks'));
      case TodayCockpitAction.stuckRecovery:
        _openStuckChat(context);
    }
  }

  void _executeSecondary(BuildContext context, WidgetRef ref) {
    if (vm.mode == TodayCockpitMode.stalled) {
      unawaited(context.push('/tasks'));
      return;
    }
    _openStuckChat(context);
  }

  /// 与原 dashboard_screen._startNextAction 相同的跳转链路（来源：
  /// /tasks/today → activeTaskProvider → 任务执行页），不另建通道。
  void _startTask(BuildContext context, WidgetRef ref) {
    final growthTask = vm.taskToStart;
    if (growthTask == null || growthTask.id.isEmpty) {
      unawaited(context.push('/tasks'));
      return;
    }
    final taskModel = growthTask.taskModel;
    if (taskModel == null) {
      unawaited(context.push('/tasks/${growthTask.id}'));
      return;
    }
    ref.read(activeTaskProvider.notifier).state = taskModel;
    unawaited(context.push('/tasks/${growthTask.id}/execute?origin=home_growth'));
  }

  /// 「我卡住了」→ 携带真实 context 进入 growth chat
  /// （沿用 dashboard_screen._openBottleneckChat 的 prompt+chat_mode 约定，
  /// J-05 旗舰恢复旅程以此为 home 落点）。
  void _openStuckChat(BuildContext context) {
    final l10n = context.l10n;
    final bottleneck = vm.bottleneckTopic;
    final prompt = bottleneck != null
        ? l10n.dashboardBottleneckPrompt(bottleneck)
        : l10n.todayCockpitStuckPrompt(
            vm.goalTitle ?? vm.planName ?? l10n.todayCockpitGoalWord,
            _stallReason(l10n),
          );
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

  String _stallReason(AppLocalizations l10n) {
    final deadline = vm.deadlineDays;
    if (deadline != null && deadline <= 0) {
      return l10n.todayCockpitStallReasonDeadline;
    }
    if (vm.staleGuard) {
      return l10n.todayCockpitStallReasonStale;
    }
    final health = vm.planHealthPercent;
    if (health != null) {
      return l10n.todayCockpitStallReasonHealth(health);
    }
    return l10n.todayCockpitStallReasonGeneric;
  }
}

class _GoalContextRow extends StatelessWidget {
  const _GoalContextRow({required this.vm});

  final TodayCockpitVm vm;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final goalLabel = vm.goalTitle ?? vm.planName;
    final deadline = vm.deadlineDays;

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        if (goalLabel != null && goalLabel.isNotEmpty)
          SemanticPill(
            label: goalLabel,
            tone: PillTone.info,
            icon: Icons.flag_rounded,
            dense: true,
          ),
        if (vm.goalTasksTotal > 0)
          SemanticPill(
            // F-9：进度 chip 只渲染任务账本口径（goalTasks*），与任务板
            // 头部、多目标看板对同一状态给出同一数字；不再用 /tasks/today
            // 选择流（曾在 1/4 与 0/1 间漂移）。
            label: '${vm.goalTasksCompleted}/${vm.goalTasksTotal}',
            tone: PillTone.neutral,
            icon: Icons.task_alt_rounded,
            dense: true,
          ),
        if (deadline != null && deadline <= 2)
          SemanticPill(
            label: deadline == 0
                ? l10n.todayCockpitWhyDueToday
                : deadline < 0
                    ? l10n.todayCockpitWhyOverdue(-deadline)
                    : l10n.todayCockpitWhyDueIn(deadline),
            tone: PillTone.warning,
            icon: Icons.timelapse_rounded,
            dense: true,
          ),
      ],
    );
  }
}

/// current run 条：agent 正在执行时的轻量进行中提示（点击进入 chat 查看）。
class _CurrentRunStrip extends StatelessWidget {
  const _CurrentRunStrip({this.runLabel});

  final String? runLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return InkWell(
      onTap: () => unawaited(context.push('/chat')),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.16)),
        ),
        child: Row(
          children: [
            // U-01 Step 3：进度/加载一律走 owner LoadingIndicator。
            LoadingIndicator.circular(size: 14, strokeWidth: 2),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                runLabel == null || runLabel!.trim().isEmpty
                    ? l10n.todayCockpitRunOngoing
                    : l10n.todayCockpitRunOngoingDetailed(runLabel!),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.typo.bodySmall.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
            Icon(Icons.chevron_right_rounded, size: 16, color: DS.textSecondary),
          ],
        ),
      ),
    );
  }
}

/// no-goal 态的目标起点建议（复用既有 goal-starter 文案与 chat prompt 通道）。
class _GoalStarters extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final starters = [
      (
        l10n.dashboardGoalExamSprint,
        Icons.local_fire_department_outlined,
        l10n.dashboardGoalExamSprintPrompt,
      ),
      (
        l10n.dashboardGoalLongTerm,
        Icons.school_outlined,
        l10n.dashboardGoalLongTermPrompt,
      ),
      (
        l10n.dashboardGoalProject,
        Icons.rocket_launch_outlined,
        l10n.dashboardGoalProjectPrompt,
      ),
      (
        l10n.dashboardGoalSelfGrowth,
        Icons.psychology_outlined,
        l10n.dashboardGoalSelfGrowthPrompt,
      ),
      (
        l10n.dashboardGoalNotSure,
        Icons.help_outline,
        l10n.dashboardGoalNotSurePrompt,
      ),
    ];

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        for (final (label, icon, prompt) in starters)
          SemanticPill(
            label: label,
            tone: PillTone.brand,
            icon: icon,
            dense: true,
            onTap: () => context.go(
              '/chat?prompt=${Uri.encodeComponent(prompt)}',
            ),
          ),
      ],
    );
  }
}

class _CockpitSkeleton extends StatelessWidget {
  const _CockpitSkeleton();

  @override
  Widget build(BuildContext context) => const Column(
        key: ValueKey('today-cockpit-skeleton'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SparkleSkeleton(width: 44, height: 44, borderRadius: 16),
              SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SparkleSkeleton(width: 112, height: 12, borderRadius: 6),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(height: 22, borderRadius: 11),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 220, height: 14, borderRadius: 7),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: DS.spacing16),
          SparkleSkeleton(height: 44, borderRadius: 22),
        ],
      );
}
