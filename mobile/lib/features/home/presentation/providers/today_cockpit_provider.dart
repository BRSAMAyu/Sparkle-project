import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/spine_status_band_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

/// J-03 Today Cockpit —「现在最值得做什么」的唯一派生视图模型。
///
/// 本文件**不新建任何权威真源**（B-02 lineage 契约）：所有字段均由既有
/// provider 派生，展示层（today_cockpit_card.dart）只消费这里的事实字段，
/// 再用 l10n 渲染文案。逐字段来源链路：
///
/// | VM 字段          | 权威真源（链路）                                              |
/// |------------------|---------------------------------------------------------------|
/// | hasGoals         | multiGoalOverviewProvider ← GET /growth/spine/goals + GET /plans |
/// | goalTitle        | 同上（selected goal title）                                    |
/// | goalProgress     | 同上（healthScore 为 0~1）                                     |
/// | planName         | homeGrowthStateProvider ← GET /growth/dashboard.active_plan_progress（兜底 GET /plans/active） |
/// | goalTasksTotal/Done | taskListProvider（GET /tasks 任务账本）← ledgerProgressOf（F-9 口径：选中目标名下非 abandoned 任务的 completed/total，选中目标无账本任务时回落全账本）。进度 chip 一律用这里——`/tasks/today` 是随「今日相关」判定漂移的选择流，不能当进度真源（WT324 F-9） |
/// | tasksTotal/Done  | homeGrowthStateProvider ← GET /tasks/today（仅用于 fresh/active 态判定与 why 文案，不再渲染为进度数字） |
/// | taskToStart      | homeGrowthStateProvider.nextAction ← /tasks/today 派生（优先级→瓶颈关联→截止日） |
/// | bottleneckTopic  | homeGrowthStateProvider.activeBottleneck ← /growth/dashboard.active_bottleneck（兜底 /plans/{id}/bottlenecks，仅 high severity） |
/// | planHealth       | homeGrowthStateProvider.planHealth ← active_plan_progress.health_score |
/// | deadlineDays     | dashboardProvider.mostImportantTask.daysToDeadline ?? activePlanProgress.daysToDeadline（沿用原 Command Center 口径） |
/// | staleGuard       | spineStatusBandProvider ← GET /aurora/spine/status-band.stale_guard |
/// | runIsActive 等   | chatProvider.runPhase/activeRunSummary ← WS 流式运行态（keep-alive，只读不触发连接） |
enum TodayCockpitMode {
  /// 没有任何目标：唯一出路是设定第一个目标。
  noGoal,

  /// 有目标但今天还没动：要么有待办没开始，要么今天还没排布。
  fresh,

  /// 今天已有推进：继续下一个。
  active,

  /// 有客观卡点信号：瓶颈 / 截止临期或逾期 / 计划健康度低 / stale guard。
  stalled,
}

/// 主行动类型（展示层据此渲染唯一 primary CTA 的文案与跳转）。
enum TodayCockpitAction {
  setGoal,
  startTask,
  arrangeToday,
  openTasks,
  stuckRecovery,
}

@immutable
class TodayCockpitVm {
  const TodayCockpitVm({
    required this.mode,
    required this.action,
    this.isLoading = false,
    this.taskToStart,
    this.goalTitle,
    this.goalProgress,
    this.planName,
    this.tasksTotal = 0,
    this.tasksCompleted = 0,
    this.goalTasksTotal = 0,
    this.goalTasksCompleted = 0,
    this.bottleneckTopic,
    this.planHealthPercent,
    this.deadlineDays,
    this.staleGuard = false,
    this.runIsActive = false,
    this.runLabel,
  });

  /// growth / goals 尚在首次加载（展示骨架，不做状态判定）。
  final bool isLoading;

  final TodayCockpitMode mode;
  final TodayCockpitAction action;

  /// 来自 /tasks/today 的下一个行动（可能为 null → CTA 退化为开任务/排计划）。
  final HomeGrowthTask? taskToStart;

  /// 当前选中目标（spine arbitration 或 plan 兜底）。
  final String? goalTitle;
  final double? goalProgress;
  final String? planName;

  final int tasksTotal;
  final int tasksCompleted;

  /// 任务账本进度（F-9 口径）：选中目标名下非 abandoned 任务的
  /// completed/total；选中目标在账本中无任务时回落为全账本进度。
  /// 进度 chip（`x/y`）渲染这里，与任务板头部、多目标看板同行同数。
  final int goalTasksTotal;
  final int goalTasksCompleted;

  /// high-severity 瓶颈主题（stalled why 的第一信号）。
  final String? bottleneckTopic;

  /// 0~100 的计划健康度（仅在有计划且 >0 时有值）。
  final int? planHealthPercent;

  /// 正数=剩余天数；0=今天截止；负数=已逾期天数。
  final int? deadlineDays;

  /// Aurora spine stale guard 信号。
  final bool staleGuard;

  /// 当前是否有 agent run 在执行（chat WS 运行态）。
  final bool runIsActive;

  /// run 的摘要文案素材（details 或 agentName），无则展示通用进行中。
  final String? runLabel;

  bool get hasGoalContext => goalTitle != null || planName != null;
}

/// 派生 provider：纯组合既有真源，永不抛异常（各源自身已兜底）。
///
/// `dependencies` 声明全部上游（Riverpod 2 作用域化解析要求，测试中以
/// 嵌套 ProviderScope 覆盖上游时必需；应用内非作用域场景无影响）。
final todayCockpitProvider = Provider<TodayCockpitVm>((ref) {
  final goalsAsync = ref.watch(multiGoalOverviewProvider);
  final growthAsync = ref.watch(homeGrowthStateProvider);
  final bandAsync = ref.watch(spineStatusBandProvider);
  final dashboardState = ref.watch(dashboardProvider);
  final chatState = ref.watch(chatProvider);
  // F-9：进度数字的唯一来源 = 任务账本（与任务板/多目标看板共用口径）。
  final ledgerProgress = ref.watch(taskBoardLedgerSummaryProvider);
  final ledgerProgressByPlan = ref.watch(ledgerProgressByPlanProvider);

  final isLoading =
      (goalsAsync.isLoading || growthAsync.isLoading) && !goalsAsync.hasValue;

  final goals = goalsAsync.valueOrNull;
  final growth = growthAsync.valueOrNull ?? const HomeGrowthState.empty();
  final band = bandAsync.valueOrNull;

  // ── 目标上下文（no-goal 判定与 goal 行展示）───────────────────────────
  final selectedGoal = goals?.selectedGoal;
  final goalTitle = _nonEmpty(selectedGoal?.title);
  final goalProgress = selectedGoal?.healthScore;
  final planName = _nonEmpty(growth.activePlan?.name) ??
      _nonEmpty(dashboardState.activePlanProgress?.name);
  final hasGoals = goals == null ? planName != null : goals.goals.isNotEmpty;

  // 选中目标的账本进度：目标名下有任务用目标口径，否则回落全账本
  // （目标 id 与任务 plan_id 同一 id 空间：goal 行/cockpit 的 goal 即 plan）。
  final selectedPlanProgress =
      selectedGoal == null ? null : ledgerProgressByPlan[selectedGoal.id];
  final goalTasksProgress = (selectedPlanProgress != null &&
          selectedPlanProgress.totalCount > 0)
      ? selectedPlanProgress
      : ledgerProgress;

  if (isLoading) {
    return TodayCockpitVm(
      mode: TodayCockpitMode.fresh,
      action: TodayCockpitAction.openTasks,
      isLoading: true,
      goalTitle: goalTitle,
      planName: planName,
    );
  }

  // ── 状态 1：no-goal ──────────────────────────────────────────────────
  if (!hasGoals) {
    return TodayCockpitVm(
      mode: TodayCockpitMode.noGoal,
      action: TodayCockpitAction.setGoal,
      goalTitle: goalTitle,
      planName: planName,
      runIsActive: chatState.runPhase.isActive,
      runLabel: chatState.activeRunSummary?.details ??
          chatState.activeRunSummary?.agentName,
    );
  }

  final deadlineDays = dashboardState.mostImportantTask?.daysToDeadline ??
      dashboardState.activePlanProgress?.daysToDeadline;

  // ── stalled 信号（全部为真实字段，任一命中即判卡）────────────────────
  final bottleneck = growth.activeBottleneck;
  final health = growth.planHealth;
  final overdueOrDueToday = deadlineDays != null && deadlineDays <= 0;
  final nextTaskOverdue = _isOverdue(growth.nextAction);
  final stalled = bottleneck != null ||
      (band?.staleGuard ?? false) ||
      overdueOrDueToday ||
      nextTaskOverdue ||
      (health > 0 && health < 0.45);

  // ── 状态 4：stalled ──────────────────────────────────────────────────
  if (stalled) {
    return _buildVm(
      mode: TodayCockpitMode.stalled,
      action: TodayCockpitAction.stuckRecovery,
      growth: growth,
      goalTitle: goalTitle,
      goalProgress: goalProgress,
      planName: planName,
      goalTasksProgress: goalTasksProgress,
      bottleneckTopic: bottleneck?.topic,
      planHealthPercent: health > 0 ? (health * 100).round() : null,
      deadlineDays: deadlineDays,
      staleGuard: band?.staleGuard ?? false,
      chatState: chatState,
    );
  }

  // ── 状态 2：fresh（今天还没动）／状态 3：active（已有推进）────────────
  final startedToday = growth.tasksCompleted > 0;
  final hasSomethingToDo = growth.nextAction != null || growth.tasksTotal > 0;
  final mode =
      startedToday ? TodayCockpitMode.active : TodayCockpitMode.fresh;
  final action = growth.nextAction != null
      ? TodayCockpitAction.startTask
      : (hasSomethingToDo ? TodayCockpitAction.openTasks
          : TodayCockpitAction.arrangeToday);

  return _buildVm(
    mode: mode,
    action: action,
    growth: growth,
    goalTitle: goalTitle,
    goalProgress: goalProgress,
    planName: planName,
    goalTasksProgress: goalTasksProgress,
    bottleneckTopic: null,
    planHealthPercent:
        health > 0 && health < 1 ? (health * 100).round() : null,
    deadlineDays: deadlineDays,
    staleGuard: band?.staleGuard ?? false,
    chatState: chatState,
  );
}, dependencies: [
  multiGoalOverviewProvider,
  homeGrowthStateProvider,
  spineStatusBandProvider,
  dashboardProvider,
  chatProvider,
  taskBoardLedgerSummaryProvider,
  ledgerProgressByPlanProvider,
],);

TodayCockpitVm _buildVm({
  required TodayCockpitMode mode,
  required TodayCockpitAction action,
  required HomeGrowthState growth,
  required String? goalTitle,
  required double? goalProgress,
  required String? planName,
  required TaskLedgerProgress goalTasksProgress,
  required String? bottleneckTopic,
  required int? planHealthPercent,
  required int? deadlineDays,
  required bool staleGuard,
  required ChatState chatState,
}) =>
    TodayCockpitVm(
      mode: mode,
      action: action,
      taskToStart: growth.nextAction,
      goalTitle: goalTitle,
      goalProgress: goalProgress,
      planName: planName,
      tasksTotal: growth.tasksTotal,
      tasksCompleted: growth.tasksCompleted,
      goalTasksTotal: goalTasksProgress.totalCount,
      goalTasksCompleted: goalTasksProgress.completedCount,
      bottleneckTopic: _nonEmpty(bottleneckTopic),
      planHealthPercent: planHealthPercent,
      deadlineDays: deadlineDays,
      staleGuard: staleGuard,
      runIsActive: chatState.runPhase.isActive,
      runLabel: chatState.activeRunSummary?.details ??
          chatState.activeRunSummary?.agentName,
    );

bool _isOverdue(HomeGrowthTask? task) {
  final due = task?.dueDate;
  if (due == null || task!.isCompleted) return false;
  final today = DateTime.now();
  final endOfDue = DateTime(due.year, due.month, due.day);
  final startOfToday = DateTime(today.year, today.month, today.day);
  return endOfDue.isBefore(startOfToday);
}

String? _nonEmpty(String? value) {
  final trimmed = value?.trim();
  return trimmed == null || trimmed.isEmpty ? null : trimmed;
}
