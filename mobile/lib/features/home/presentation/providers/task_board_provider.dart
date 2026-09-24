import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/plan_name_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Task board view mode
enum TaskViewMode { schedule, priority, plan, sprint }

/// Sprint task filter options
enum SprintTaskFilter { all, todo, inProgress, done }

/// F-9 ·「任务进度」展示口径 · 单一定义点。
///
/// 权威真源 = 任务账本（`taskListProvider`，GET /tasks 全量列表），
/// 不再用 `/tasks/today` 选择流或 due-today 过滤派生进度数字：
/// 选择流的构成随「今日相关」判定逐日漂移（cockpit chip 曾在 1/4 与
/// 0/1 间跳变，WT324 F-9），due-today 口径则与账本可见的「共 4 项、
/// 已完成 1」同屏矛盾。
///
/// 口径：total = 非 abandoned 账本任务数；completed = 其中 status ==
/// completed 的数量。多目标看板 goal 行（按 planId）、cockpit 进度
/// chip（选中目标，缺配回落全账本）、任务板头部汇总（全账本）一律
/// 引用本文件，禁止各自再写一套计数。
class TaskLedgerProgress {
  const TaskLedgerProgress({
    required this.totalCount,
    required this.completedCount,
  });

  const TaskLedgerProgress.empty()
      : totalCount = 0,
        completedCount = 0;

  final int totalCount;
  final int completedCount;
}

/// 账本进度计数的唯一实现（展示投影，不另立完成判定语义——
/// 完成与否以 `TaskStatus.completed` 为准，与引擎一致）。
TaskLedgerProgress ledgerProgressOf(
  List<TaskModel> tasks, {
  String? planId,
}) {
  final scoped = planId == null
      ? tasks.where((t) => t.status != TaskStatus.abandoned).toList()
      : tasks
          .where(
            (t) => t.planId == planId && t.status != TaskStatus.abandoned,
          )
          .toList();
  final completed = scoped.where((t) => t.status == TaskStatus.completed).length;
  return TaskLedgerProgress(
    totalCount: scoped.length,
    completedCount: completed,
  );
}

/// 任务板头部汇总：全账本进度（非 abandoned）。
final taskBoardLedgerSummaryProvider = Provider<TaskLedgerProgress>((ref) {
  final taskState = ref.watch(taskListProvider);
  return ledgerProgressOf(taskState.tasks);
});

/// 按计划（=目标）分组的账本进度，供多目标看板逐行展示。
/// `null` 键收纳无归属计划的任务（无目标任务不挂在任何 goal 行上）。
final ledgerProgressByPlanProvider =
    Provider<Map<String?, TaskLedgerProgress>>((ref) {
  final taskState = ref.watch(taskListProvider);
  final byPlan = <String?, TaskLedgerProgress>{};
  final planIds = taskState.tasks
      .where((t) => t.status != TaskStatus.abandoned)
      .map((t) => t.planId)
      .toSet();
  for (final planId in planIds) {
    byPlan[planId] = ledgerProgressOf(taskState.tasks, planId: planId);
  }
  return byPlan;
});

/// S7「今日」分组口径 · 单一定义点。
///
/// 真假判定以引擎 `backend/app/services/goal_today_view.py` 为唯一事实源
/// （due_date == today 且状态非 COMPLETED/ABANDONED 即「今日待执行」）。
/// 客户端此函数仅作看板「今日/逾期」分组的展示投影，不另立判定语义；
/// 进度类数字（头部汇总、cockpit chip、多目标看板）走本文件的
/// `ledgerProgressOf` 账本口径（F-9），不再经由今日过滤派生。
List<TaskModel> tasksDueOn(List<TaskModel> tasks, DateTime day) {
  bool isSameDay(DateTime? value) =>
      value != null &&
      value.year == day.year &&
      value.month == day.month &&
      value.day == day.day;
  return tasks.where((task) => isSameDay(task.dueDate)).toList();
}

DateTime dateOnlyOf(DateTime value) => DateTime(value.year, value.month, value.day);

/// Task board state
class TaskBoardState {
  TaskBoardState({
    this.currentView = TaskViewMode.schedule,
    this.expandedTaskIds = const {},
    this.selectedPlanId,
    this.sprintFilter = SprintTaskFilter.all,
    this.isCollapsed = true,
  });

  final TaskViewMode currentView;
  final Set<String> expandedTaskIds;
  final String? selectedPlanId;
  final SprintTaskFilter sprintFilter;
  final bool isCollapsed;

  /// Serialize state to JSON for persistence
  Map<String, dynamic> toJson() => {
        'currentView': currentView.name,
        'expandedTaskIds': expandedTaskIds.toList(),
        'selectedPlanId': selectedPlanId,
        'sprintFilter': sprintFilter.name,
        'isCollapsed': isCollapsed,
      };

  /// Create state from JSON (for persistence)
  static TaskBoardState? fromJson(Map<String, dynamic> json) {
    try {
      return TaskBoardState(
        currentView: TaskViewMode.values.firstWhere(
          (e) => e.name == json['currentView'],
          orElse: () => TaskViewMode.schedule,
        ),
        expandedTaskIds: (json['expandedTaskIds'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toSet() ??
            const {},
        selectedPlanId: json['selectedPlanId'] as String?,
        sprintFilter: SprintTaskFilter.values.firstWhere(
          (e) => e.name == json['sprintFilter'],
          orElse: () => SprintTaskFilter.all,
        ),
        isCollapsed: json['isCollapsed'] as bool? ?? true,
      );
    } catch (e) {
      return null;
    }
  }

  TaskBoardState copyWith({
    TaskViewMode? currentView,
    Set<String>? expandedTaskIds,
    String? selectedPlanId,
    SprintTaskFilter? sprintFilter,
    bool? isCollapsed,
    bool clearSelectedPlan = false,
  }) =>
      TaskBoardState(
        currentView: currentView ?? this.currentView,
        expandedTaskIds: expandedTaskIds ?? this.expandedTaskIds,
        selectedPlanId:
            clearSelectedPlan ? null : selectedPlanId ?? this.selectedPlanId,
        sprintFilter: sprintFilter ?? this.sprintFilter,
        isCollapsed: isCollapsed ?? this.isCollapsed,
      );
}

/// Task board notifier with persistence
class TaskBoardNotifier extends PersistentStateNotifier<TaskBoardState> {
  TaskBoardNotifier(this._ref)
      : super(
          _ref,
          namespace: 'task_board',
          key: 'state',
          defaultValue: TaskBoardState(),
          toJson: (s) => s.toJson(),
          fromJson: TaskBoardState.fromJson,
        ) {
    // Initialize default view based on sprint status
    _initializeDefaultView();
    _ref.listen<PlanListState>(planListProvider, (_, next) {
      _reconcileSelectedPlan(next);
    });
  }

  final Ref _ref;

  void _reconcileSelectedPlan(PlanListState planState) {
    final selectedPlanId = state.selectedPlanId;
    if (selectedPlanId == null) {
      return;
    }

    if (planState.isLoading &&
        planState.plans.isEmpty &&
        planState.activePlans.isEmpty) {
      return;
    }

    final activePlanIds = planState.activePlans.map((plan) => plan.id).toSet();
    if (!activePlanIds.contains(selectedPlanId)) {
      clearPlanSelection();
    }
  }

  void _initializeDefaultView() {
    final dashboardState = _ref.read(dashboardProvider);
    // If sprint is active, default to sprint view (only if currently on schedule)
    final defaultView = dashboardState.sprint != null
        ? TaskViewMode.sprint
        : TaskViewMode.schedule;
    // Only update if state is still default (schedule view)
    if (state.currentView == TaskViewMode.schedule &&
        defaultView == TaskViewMode.sprint) {
      state = state.copyWith(currentView: defaultView);
    }
  }

  void switchView(TaskViewMode view) {
    state = state.copyWith(currentView: view);
  }

  void toggleTaskExpansion(String taskId) {
    final newExpanded = Set<String>.from(state.expandedTaskIds);
    if (newExpanded.contains(taskId)) {
      newExpanded.remove(taskId);
    } else {
      newExpanded.add(taskId);
    }
    state = state.copyWith(expandedTaskIds: newExpanded);
  }

  void expandTask(String taskId) {
    if (!state.expandedTaskIds.contains(taskId)) {
      final newExpanded = Set<String>.from(state.expandedTaskIds)..add(taskId);
      state = state.copyWith(expandedTaskIds: newExpanded);
    }
  }

  void collapseTask(String taskId) {
    if (state.expandedTaskIds.contains(taskId)) {
      final newExpanded = Set<String>.from(state.expandedTaskIds)
        ..remove(taskId);
      state = state.copyWith(expandedTaskIds: newExpanded);
    }
  }

  void selectPlan(String planId) {
    state = state.copyWith(selectedPlanId: planId);
  }

  void clearPlanSelection() {
    state = state.copyWith(clearSelectedPlan: true);
  }

  void collapseAll() {
    state = state.copyWith(expandedTaskIds: {});
  }

  void setSprintFilter(SprintTaskFilter filter) {
    state = state.copyWith(sprintFilter: filter);
  }

  void toggleCollapsed() {
    state = state.copyWith(isCollapsed: !state.isCollapsed);
  }
}

/// Task board provider
final taskBoardProvider =
    StateNotifierProvider<TaskBoardNotifier, TaskBoardState>(
  TaskBoardNotifier.new,
);

/// Grouped tasks for schedule view
class ScheduleGroup {
  ScheduleGroup({
    required this.title,
    required this.tasks,
    this.isEmpty = false,
  });

  final String title;
  final List<TaskModel> tasks;
  final bool isEmpty;
}

/// Schedule view grouped tasks provider
final scheduleGroupsProvider = Provider<List<ScheduleGroup>>((ref) {
  final taskState = ref.watch(taskListProvider);
  final tasks = taskState.tasks
      .where(
        (t) =>
            t.status != TaskStatus.completed &&
            t.status != TaskStatus.abandoned,
      )
      .toList();

  final now = DateTime.now();
  final today = dateOnlyOf(now);
  final tomorrow = today.add(const Duration(days: 1));
  final weekEnd = today.add(const Duration(days: 7));

  final overDue = <TaskModel>[];
  // 与头部汇总共用 tasksDueOn 单一口径（S7）：今日分组 = 到期日为今天的待执行任务。
  final todayTasks = tasksDueOn(tasks, now);
  final todayDueDates = todayTasks.map((t) => t.id).toSet();
  final tomorrowTasks = <TaskModel>[];
  final thisWeek = <TaskModel>[];
  final later = <TaskModel>[];
  final noDate = <TaskModel>[];

  for (final task in tasks) {
    if (task.dueDate == null) {
      noDate.add(task);
    } else if (todayDueDates.contains(task.id)) {
      // 已在今日分组，跳过
      continue;
    } else {
      final dueDate = DateTime(
        task.dueDate!.year,
        task.dueDate!.month,
        task.dueDate!.day,
      );
      if (dueDate.isBefore(today)) {
        overDue.add(task);
      } else if (dueDate == tomorrow) {
        tomorrowTasks.add(task);
      } else if (dueDate.isBefore(weekEnd)) {
        thisWeek.add(task);
      } else {
        later.add(task);
      }
    }
  }

  // Sort by priority within each group
  int sortByPriority(TaskModel a, TaskModel b) =>
      b.priority.compareTo(a.priority);

  overDue.sort(sortByPriority);
  todayTasks.sort(sortByPriority);
  tomorrowTasks.sort(sortByPriority);
  thisWeek.sort(sortByPriority);
  later.sort(sortByPriority);
  noDate.sort(sortByPriority);

  return [
    if (overDue.isNotEmpty) ScheduleGroup(title: S.taskBoardOverdue, tasks: overDue),
    if (todayTasks.isNotEmpty) ScheduleGroup(title: S.taskBoardToday, tasks: todayTasks),
    if (tomorrowTasks.isNotEmpty)
      ScheduleGroup(title: S.taskBoardTomorrow, tasks: tomorrowTasks),
    if (thisWeek.isNotEmpty) ScheduleGroup(title: S.taskBoardThisWeek, tasks: thisWeek),
    if (later.isNotEmpty) ScheduleGroup(title: S.taskBoardLater, tasks: later),
    if (noDate.isNotEmpty) ScheduleGroup(title: S.taskBoardNoDate, tasks: noDate),
    if (tasks.isEmpty) ScheduleGroup(title: '', tasks: [], isEmpty: true),
  ];
});

/// Priority view sorted tasks provider
final priorityTasksProvider = Provider<List<TaskModel>>((ref) {
  final taskState = ref.watch(taskListProvider);
  final tasks = taskState.tasks
      .where(
        (t) =>
            t.status != TaskStatus.completed &&
            t.status != TaskStatus.abandoned,
      )
      .toList()
    ..sort((a, b) => b.priority.compareTo(a.priority));
  return tasks;
});

/// Plan view grouped tasks provider
final planGroupsProvider = Provider<Map<String?, List<TaskModel>>>((ref) {
  final taskState = ref.watch(taskListProvider);

  // 监听计划名称映射，以便在计划变更时触发刷新
  ref.watch(planNameMapProvider);

  final tasks = taskState.tasks
      .where(
        (t) =>
            t.status != TaskStatus.completed &&
            t.status != TaskStatus.abandoned,
      )
      .toList();

  final groups = <String?, List<TaskModel>>{};

  for (final task in tasks) {
    final planId = task.planId;
    if (!groups.containsKey(planId)) {
      groups[planId] = [];
    }
    groups[planId]!.add(task);
  }

  // Sort tasks within each plan by priority
  for (final planTasks in groups.values) {
    planTasks.sort((a, b) => b.priority.compareTo(a.priority));
  }

  return groups;
});

/// Sprint view tasks provider - 只显示当前活跃冲刺的任务
final sprintTasksProvider = Provider<List<TaskModel>>((ref) {
  final dashboardState = ref.watch(dashboardProvider);
  final taskState = ref.watch(taskListProvider);
  final boardState = ref.watch(taskBoardProvider);

  // 没有活跃冲刺时返回空列表
  if (dashboardState.sprint == null) return [];

  final sprintPlanId = dashboardState.sprint!.id;

  // 筛选属于当前冲刺的任务
  var tasks = taskState.tasks.where((t) => t.planId == sprintPlanId).toList();

  // 根据过滤器进一步筛选
  switch (boardState.sprintFilter) {
    case SprintTaskFilter.todo:
      tasks = tasks.where((t) => t.status == TaskStatus.pending).toList();
    case SprintTaskFilter.inProgress:
      tasks = tasks
          .where((t) =>
              t.status == TaskStatus.inProgress || t.status == TaskStatus.stuck,)
          .toList();
    case SprintTaskFilter.done:
      tasks = tasks.where((t) => t.status == TaskStatus.completed).toList();
    case SprintTaskFilter.all:
      // 全部显示所有任务（包括已完成，排除已放弃）
      tasks = tasks.where((t) => t.status != TaskStatus.abandoned).toList();
  }

  // 按优先级排序
  tasks.sort((a, b) => b.priority.compareTo(a.priority));
  return tasks;
});

/// Sprint task counts provider - 用于显示过滤器的任务数量
final sprintTaskCountsProvider = Provider<Map<SprintTaskFilter, int>>((ref) {
  final dashboardState = ref.watch(dashboardProvider);
  final taskState = ref.watch(taskListProvider);

  if (dashboardState.sprint == null) {
    return {for (final filter in SprintTaskFilter.values) filter: 0};
  }

  final sprintPlanId = dashboardState.sprint!.id;
  final sprintTasks =
      taskState.tasks.where((t) => t.planId == sprintPlanId).toList();

  return {
    SprintTaskFilter.all:
        sprintTasks.where((t) => t.status != TaskStatus.abandoned).length,
    SprintTaskFilter.todo:
        sprintTasks.where((t) => t.status == TaskStatus.pending).length,
    SprintTaskFilter.inProgress: sprintTasks
        .where((t) =>
            t.status == TaskStatus.inProgress || t.status == TaskStatus.stuck,)
        .length,
    SprintTaskFilter.done:
        sprintTasks.where((t) => t.status == TaskStatus.completed).length,
  };
});
