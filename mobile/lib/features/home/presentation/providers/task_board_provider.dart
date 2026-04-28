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

class TaskBoardTodaySummary {
  const TaskBoardTodaySummary({
    required this.totalCount,
    required this.completedCount,
  });

  final int totalCount;
  final int completedCount;

  String get label =>
      totalCount == 0 ? S.taskBoardTodayNoTasks : S.taskBoardTodaySummary(completedCount, totalCount);
}

/// Task board state
class TaskBoardState {
  TaskBoardState({
    this.currentView = TaskViewMode.schedule,
    this.expandedTaskIds = const {},
    this.selectedPlanId,
    this.sprintFilter = SprintTaskFilter.all,
  });

  final TaskViewMode currentView;
  final Set<String> expandedTaskIds;
  final String? selectedPlanId;
  final SprintTaskFilter sprintFilter;

  /// Serialize state to JSON for persistence
  Map<String, dynamic> toJson() => {
        'currentView': currentView.name,
        'expandedTaskIds': expandedTaskIds.toList(),
        'selectedPlanId': selectedPlanId,
        'sprintFilter': sprintFilter.name,
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
    bool clearSelectedPlan = false,
  }) =>
      TaskBoardState(
        currentView: currentView ?? this.currentView,
        expandedTaskIds: expandedTaskIds ?? this.expandedTaskIds,
        selectedPlanId:
            clearSelectedPlan ? null : selectedPlanId ?? this.selectedPlanId,
        sprintFilter: sprintFilter ?? this.sprintFilter,
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
}

/// Task board provider
final taskBoardProvider =
    StateNotifierProvider<TaskBoardNotifier, TaskBoardState>(
  TaskBoardNotifier.new,
);

final taskBoardTodaySummaryProvider = Provider<TaskBoardTodaySummary>((ref) {
  final taskState = ref.watch(taskListProvider);
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);

  bool isSameDay(DateTime? value) =>
      value != null &&
      value.year == today.year &&
      value.month == today.month &&
      value.day == today.day;

  final todayTasks = taskState.tasks
      .where((task) => isSameDay(task.dueDate) || isSameDay(task.completedAt))
      .toList();

  final completedToday = todayTasks
      .where(
        (task) =>
            task.status == TaskStatus.completed && isSameDay(task.completedAt),
      )
      .length;

  return TaskBoardTodaySummary(
    totalCount: todayTasks.length,
    completedCount: completedToday,
  );
});

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
  final today = DateTime(now.year, now.month, now.day);
  final tomorrow = today.add(const Duration(days: 1));
  final weekEnd = today.add(const Duration(days: 7));

  final overDue = <TaskModel>[];
  final todayTasks = <TaskModel>[];
  final tomorrowTasks = <TaskModel>[];
  final thisWeek = <TaskModel>[];
  final later = <TaskModel>[];
  final noDate = <TaskModel>[];

  for (final task in tasks) {
    if (task.dueDate == null) {
      noDate.add(task);
    } else {
      final dueDate = DateTime(
        task.dueDate!.year,
        task.dueDate!.month,
        task.dueDate!.day,
      );
      if (dueDate.isBefore(today)) {
        overDue.add(task);
      } else if (dueDate == today) {
        todayTasks.add(task);
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
              t.status == TaskStatus.inProgress || t.status == TaskStatus.stuck)
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
            t.status == TaskStatus.inProgress || t.status == TaskStatus.stuck)
        .length,
    SprintTaskFilter.done:
        sprintTasks.where((t) => t.status == TaskStatus.completed).length,
  };
});
