import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// J-05 ·「我卡住了」旗舰恢复旅程——中断回流的最小闭环。
///
/// 产品意图（v3/07_tasks/cards/J-05.md）：用户在任务中卡住（分心/畏难/
/// 中断多日）时，产品的恢复体验**不是推送提醒，而是回到 app 时的第一屏
/// 承接**——把用户拉回轨道：上次任务 + 一行共情 + 一个 5 分钟最小重启
/// 动作，动作完成后给正反馈收口。
///
/// 检测口径（只消费既有信号定义，零算法改动）：
/// - 停滞阈值 48h 对齐后端 absence_detector 的 extended 档
///   （backend/app/signals/absence_detector.py `_ABSENCE_THRESHOLDS` 48h+
///   =「disengaged」）。推送侧（spine/celery/wake_policy）负责「用户不
///   开 app」的召回；本面负责「用户已回流」的承接，两半合一人；
/// - 停滞对象 = 任务域未完成且已启动（inProgress/paused/stuck）的任务，
///   最后触碰（updatedAt 与 pausedAt 取较晚者）早于阈值——任务态集合与
///   guest_conversion_provider._isTaskInFlight 的「进行中」口径同源；
///   pending（从未开始）不算卡住，计划里的未来任务不该被当成中断；
/// - predictive_service（/predictive/engagement、dropout 风险算法）本身
///   不动，本 provider 是其「低活跃/停滞」信号在客户端的纯派生消费。
///
/// 状态机：idle → detected（卡片可见）→ restarted（CTA 已点，执行中）→
/// reconnected（正反馈卡，粘滞直到用户 ack）；任何时刻执行中任务
/// （activeTaskProvider 非空）卡片一律退场（N40「永不打断进行中任务」
/// 同款红线）；「暂不」= 本会话内不再出现。
enum StuckRecoveryPhase { idle, detected, restarted, reconnected }

/// 停滞阈值：48h，对齐 absence_detector extended 档（2880min）。
const Duration kStuckRecoveryStallThreshold = Duration(hours: 48);

/// 参与停滞判定的已启动未完成任务态。
const Set<TaskStatus> _stallableStatuses = {
  TaskStatus.inProgress,
  TaskStatus.paused,
  TaskStatus.stuck,
};

DateTime _lastTouchOf(TaskModel task) {
  final pausedAt = task.pausedAt;
  if (pausedAt != null && pausedAt.isAfter(task.updatedAt)) return pausedAt;
  return task.updatedAt;
}

/// 「进行中」口径（与 guest_conversion_provider._isTaskInFlight 同源）：
/// 执行屏退出/完成后 activeTaskProvider 会残留原任务快照（任务完成流
/// 不清位），所以执行态守门只认真正在飞的 inProgress/stuck——刚完成的
/// 任务不该挡住正反馈卡，刚暂停的任务不该挡住别的恢复承接。
bool isTaskInFlight(TaskModel? task) =>
    task != null &&
    (task.status == TaskStatus.inProgress || task.status == TaskStatus.stuck);

/// 执行态守门的真源修正：activeTaskProvider 是会话态快照，完成/暂停后
/// 不清位，其 status 会滞后——以任务列表（sprint_task_ledger 的客户端
/// 投影）里的当前状态为准解析「是否真的在飞」。
bool isActiveTaskInFlight(Iterable<TaskModel> pool, TaskModel? activeTask) {
  if (activeTask == null) return false;
  for (final task in pool) {
    if (task.id == activeTask.id) return isTaskInFlight(task);
  }
  return isTaskInFlight(activeTask);
}

/// 纯函数检测：从任务集里找出「停滞」的恢复对象（最后触碰最早 = 卡得
/// 最久的那个优先）。可单测（now 注入），demo/离线/访客态同样可用——
/// 检测不依赖网络，回流承接不因弱网失约。
TaskModel? findStalledTask(
  Iterable<TaskModel> tasks, {
  required DateTime now,
  Duration threshold = kStuckRecoveryStallThreshold,
}) {
  TaskModel? best;
  for (final task in tasks) {
    if (!_stallableStatuses.contains(task.status)) continue;
    final lastTouch = _lastTouchOf(task);
    if (now.difference(lastTouch) < threshold) continue;
    if (best == null || lastTouch.isAfter(_lastTouchOf(best))) best = task;
  }
  return best;
}

class StuckRecoveryState {
  const StuckRecoveryState({
    this.phase = StuckRecoveryPhase.idle,
    this.task,
    this.absentDays = 0,
    this.reconnectedTaskTitle,
    this.dismissedThisSession = false,
  });

  final StuckRecoveryPhase phase;

  /// detected/restarted 相的恢复对象快照。
  final TaskModel? task;

  /// 检测时刻距最后-touch 的天数（≥1），供共情文案。
  final int absentDays;

  /// reconnected 相展示的任务名（完成时刻快照，防任务列表后续变动）。
  final String? reconnectedTaskTitle;

  /// 「暂不」= 本会话硬关（会话结束自然失效，不跨会话记仇）。
  final bool dismissedThisSession;
}

class StuckRecoveryController extends StateNotifier<StuckRecoveryState> {
  StuckRecoveryController(this._ref) : super(const StuckRecoveryState()) {
    // 任务列表 / 执行中任务任一变化即重派生；构造时先同步一次，
    // 保证「先有停滞任务、后建 provider」的挂载顺序也能立即出卡。
    _ref
      ..listen<TaskListState>(taskListProvider, (_, __) => _sync())
      ..listen<TaskModel?>(activeTaskProvider, (_, __) => _sync());
    _sync();
  }

  final Ref _ref;

  void _sync() {
    // 正反馈粘滞：直到用户 ack（或新会话），不被任务列表变动冲掉。
    if (state.phase == StuckRecoveryPhase.reconnected) return;

    final tasksState = _ref.read(taskListProvider);
    final pool = <TaskModel>{...tasksState.tasks, ...tasksState.todayTasks};
    final activeTask = _ref.read(activeTaskProvider);

    if (state.phase == StuckRecoveryPhase.restarted) {
      final task = _byId(pool, state.task?.id);
      if (task == null) {
        _resetToIdle();
        return;
      }
      if (task.status == TaskStatus.completed) {
        // 闭环收口：经本卡重启的任务完成 → 正反馈。
        state = StuckRecoveryState(
          phase: StuckRecoveryPhase.reconnected,
          task: task,
          reconnectedTaskTitle: task.title,
        );
        return;
      }
      // 未完成：执行中不动作；若又回落到停滞（用户中途退出且再未触碰），
      // 重新给卡（温柔重邀）；刚触碰过则静默待机，不纠缠。
      if (!isActiveTaskInFlight(pool, activeTask) &&
          findStalledTask([task], now: DateTime.now()) != null) {
        state = StuckRecoveryState(
          phase: StuckRecoveryPhase.detected,
          task: task,
          absentDays: _absentDaysOf(task),
          dismissedThisSession: state.dismissedThisSession,
        );
      }
      return;
    }

    // idle / detected：执行中绝不打断（与 N40 守门同款红线）。
    if (isActiveTaskInFlight(pool, activeTask)) return;
    final candidate = findStalledTask(pool, now: DateTime.now());
    if (candidate == null) {
      if (state.phase == StuckRecoveryPhase.detected) _resetToIdle();
      return;
    }
    if (state.dismissedThisSession) return;
    if (state.phase == StuckRecoveryPhase.detected &&
        state.task?.id == candidate.id) {
      state = StuckRecoveryState(
        phase: StuckRecoveryPhase.detected,
        task: candidate,
        absentDays: _absentDaysOf(candidate),
        dismissedThisSession: state.dismissedThisSession,
      );
      return;
    }
    state = StuckRecoveryState(
      phase: StuckRecoveryPhase.detected,
      task: candidate,
      absentDays: _absentDaysOf(candidate),
    );
  }

  /// CTA「先做 5 分钟」按下：进入 restarted 相——此后该任务完成即触发
  /// 正反馈，卡片本体交给执行屏（不再占首屏）。
  void markRestartStarted() {
    if (state.phase != StuckRecoveryPhase.detected || state.task == null) {
      return;
    }
    state = StuckRecoveryState(
      phase: StuckRecoveryPhase.restarted,
      task: state.task,
      absentDays: state.absentDays,
      dismissedThisSession: state.dismissedThisSession,
    );
  }

  /// 「暂不」：本会话硬关；回 idle（会话内不再出现，跨会话不记仇）。
  void dismissForSession() {
    state = const StuckRecoveryState(dismissedThisSession: true);
  }

  /// 正反馈 ack：整个状态机归零。
  void ackReconnect() {
    state = const StuckRecoveryState();
  }

  void _resetToIdle() {
    state = StuckRecoveryState(dismissedThisSession: state.dismissedThisSession);
  }

  int _absentDaysOf(TaskModel task) {
    final days = DateTime.now().difference(_lastTouchOf(task)).inDays;
    // 48h 起步按「1 天」起算：共情文案里「等你 1 天」比「0 天」诚实可感。
    return days.clamp(1, 999);
  }

  TaskModel? _byId(Iterable<TaskModel> tasks, String? id) {
    if (id == null) return null;
    for (final task in tasks) {
      if (task.id == id) return task;
    }
    return null;
  }
}

final stuckRecoveryControllerProvider =
    StateNotifierProvider<StuckRecoveryController, StuckRecoveryState>(
  StuckRecoveryController.new,
);

/// 卡片渲染视图（null = 不渲染）。守门四条与 GuestConversionCard /
/// OnboardingResumeCard 同款形制：
/// ① 已认证（未登录不渲染）；② 控制器处于可渲染相；
/// ③ 执行中任务退场（双保险：控制器已挡，渲染侧再挡一次）；
/// ④ 内联卡非弹窗——不可见即 SizedBox.shrink，零布局残留。
class StuckRecoveryCardView {
  const StuckRecoveryCardView.detected(this.task, this.absentDays)
      : phase = StuckRecoveryPhase.detected,
        reconnectedTaskTitle = null;

  const StuckRecoveryCardView.reconnected(String title)
      : phase = StuckRecoveryPhase.reconnected,
        task = null,
        absentDays = 0,
        reconnectedTaskTitle = title;

  final StuckRecoveryPhase phase;
  final TaskModel? task;
  final int absentDays;
  final String? reconnectedTaskTitle;
}

final stuckRecoveryCardProvider = Provider<StuckRecoveryCardView?>((ref) {
  final authState = ref.watch(authProvider);
  if (!authState.isAuthenticated || authState.user == null) return null;

  final tasksState = ref.watch(taskListProvider);
  final activeTask = ref.watch(activeTaskProvider);
  if (isActiveTaskInFlight(
    {...tasksState.tasks, ...tasksState.todayTasks},
    activeTask,
  )) {
    return null;
  }

  final state = ref.watch(stuckRecoveryControllerProvider);
  switch (state.phase) {
    case StuckRecoveryPhase.detected:
      final task = state.task;
      if (task == null) return null;
      return StuckRecoveryCardView.detected(task, state.absentDays);
    case StuckRecoveryPhase.reconnected:
      return StuckRecoveryCardView.reconnected(
        state.reconnectedTaskTitle ?? state.task?.title ?? '',
      );
    case StuckRecoveryPhase.idle:
    case StuckRecoveryPhase.restarted:
      return null;
  }
});
