import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/prediction_attribution_service.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    show
        TaskNotificationScheduler,
        taskNotificationSchedulerProvider,
        taskReminderConfigProvider;
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
import 'package:sparkle/features/task/data/models/execution_template_model.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/next_action_selection_submission.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/shared/entities/task_model.dart';

// A dummy filter class for now
class TaskFilter {}

// 1. TaskListState Class
class TaskListState {
  TaskListState({
    this.isLoading = false,
    this.tasks = const [],
    this.todayTasks = const [],
    this.recommendedTasks = const [],
    this.taskExecutions = const {},
    this.taskExecutionRecords = const {},
    this.taskExecutionTemplates = const {},
    this.selectedExecutionTemplateIds = const {},
    this.taskGuidance = const {},
    this.taskGuidanceInFlight = const <String>{},
    this.handoffInFlight = const <String>{},
    this.executionDecisionInFlight = const <String>{},
    this.currentFilter,
    this.error,
  });
  final bool isLoading;
  final List<TaskModel> tasks;
  final List<TaskModel> todayTasks;
  final List<TaskModel> recommendedTasks;
  final Map<String, ExecutionIntentModel> taskExecutions;
  final Map<String, ExecutionRecordModel> taskExecutionRecords;
  final Map<String, List<ExecutionTemplateModel>> taskExecutionTemplates;
  final Map<String, String> selectedExecutionTemplateIds;
  final Map<String, TaskGuidanceModel> taskGuidance;
  final Set<String> taskGuidanceInFlight;
  final Set<String> handoffInFlight;
  final Set<String> executionDecisionInFlight;
  final TaskFilter? currentFilter;
  final String? error;

  TaskListState copyWith({
    bool? isLoading,
    List<TaskModel>? tasks,
    List<TaskModel>? todayTasks,
    List<TaskModel>? recommendedTasks,
    Map<String, ExecutionIntentModel>? taskExecutions,
    Map<String, ExecutionRecordModel>? taskExecutionRecords,
    Map<String, List<ExecutionTemplateModel>>? taskExecutionTemplates,
    Map<String, String>? selectedExecutionTemplateIds,
    Map<String, TaskGuidanceModel>? taskGuidance,
    Set<String>? taskGuidanceInFlight,
    Set<String>? handoffInFlight,
    Set<String>? executionDecisionInFlight,
    TaskFilter? currentFilter,
    String? error,
    bool clearError = false,
  }) =>
      TaskListState(
        isLoading: isLoading ?? this.isLoading,
        tasks: tasks ?? this.tasks,
        todayTasks: todayTasks ?? this.todayTasks,
        recommendedTasks: recommendedTasks ?? this.recommendedTasks,
        taskExecutions: taskExecutions ?? this.taskExecutions,
        taskExecutionRecords: taskExecutionRecords ?? this.taskExecutionRecords,
        taskExecutionTemplates:
            taskExecutionTemplates ?? this.taskExecutionTemplates,
        selectedExecutionTemplateIds:
            selectedExecutionTemplateIds ?? this.selectedExecutionTemplateIds,
        taskGuidance: taskGuidance ?? this.taskGuidance,
        taskGuidanceInFlight: taskGuidanceInFlight ?? this.taskGuidanceInFlight,
        handoffInFlight: handoffInFlight ?? this.handoffInFlight,
        executionDecisionInFlight:
            executionDecisionInFlight ?? this.executionDecisionInFlight,
        currentFilter: currentFilter ?? this.currentFilter,
        error: clearError ? null : error ?? this.error,
      );
}

// 2. TaskNotifier Class
class TaskNotifier extends StateNotifier<TaskListState> {
  TaskNotifier(this._taskRepository, this._notificationScheduler, this._ref)
      : super(TaskListState()) {
    // Load initial data
    unawaited(loadTodayTasks());
    unawaited(loadRecommendedTasks());
    unawaited(loadTasks());
  }
  final TaskRepository _taskRepository;
  final TaskNotificationScheduler _notificationScheduler;
  final Ref _ref;

  Future<void> _runWithErrorHandling(Future<void> Function() action) async {
    if (!mounted) return;
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await action();
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadTasks({TaskFilter? filter}) async {
    await _runWithErrorHandling(() async {
      final paginatedResponse =
          await _taskRepository.getTasks(filters: {}); // Add filter logic later
      if (!mounted) return;
      state = state.copyWith(
        isLoading: false,
        tasks: paginatedResponse.items,
        currentFilter: filter,
      );
    });
  }

  Future<void> loadTodayTasks() async {
    await _runWithErrorHandling(() async {
      final tasks = await _taskRepository.getTodayTasks();
      if (!mounted) return;
      state = state.copyWith(isLoading: false, todayTasks: tasks);
    });
  }

  Future<void> loadRecommendedTasks() async {
    await _runWithErrorHandling(() async {
      final tasks = await _taskRepository.getRecommendedTasks();
      if (!mounted) return;
      state = state.copyWith(isLoading: false, recommendedTasks: tasks);
    });
  }

  Future<void> createTask(TaskCreate task, {bool generateGuide = false}) async {
    await _runWithErrorHandling(() async {
      final newTask = await _taskRepository.createTask(
        task,
        generateGuide: generateGuide,
      );

      // Schedule reminders if due date is set
      if (newTask.dueDate != null) {
        final config = _ref.read(taskReminderConfigProvider);
        try {
          await _notificationScheduler.scheduleTaskReminders(
            newTask,
            config: config,
          );
        } catch (e) {
          // Don't fail task creation if notification scheduling fails
          // Log but continue
        }
      }

      await _syncCalendarForTask(newTask);

      // 🔧 修复：先将新任务添加到本地状态，确保立即显示
      state = state.copyWith(
        tasks: [...state.tasks, newTask],
        todayTasks: _shouldIncludeInToday(newTask)
            ? [...state.todayTasks, newTask]
            : state.todayTasks,
      );

      // 然后异步刷新完整列表（不阻塞UI）
      await refreshTasks();
    });
  }

  // 判断任务是否应该包含在今日任务中
  bool _shouldIncludeInToday(TaskModel task) {
    if (task.dueDate == null) return false;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final taskDay = DateTime(
      task.dueDate!.year,
      task.dueDate!.month,
      task.dueDate!.day,
    );
    return taskDay == today;
  }

  Future<void> updateTask(
    String id,
    TaskUpdate taskUpdate, {
    bool refresh = true,
  }) async {
    await _runWithErrorHandling(() async {
      final previousTask = state.tasks.cast<TaskModel?>().firstWhere(
            (task) => task?.id == id,
            orElse: () => null,
          );
      final updatedTask = await _taskRepository.updateTask(id, taskUpdate);

      // Reschedule reminders if due date changed
      if (taskUpdate.dueDate != null && updatedTask.dueDate != null) {
        final config = _ref.read(taskReminderConfigProvider);
        try {
          await _notificationScheduler.rescheduleTaskReminders(
            updatedTask,
            config: config,
          );
        } catch (e) {
          // Don't fail task update if notification scheduling fails
        }
      } else if (taskUpdate.dueDate == null) {
        // Cancel reminders if due date was removed
        try {
          await _notificationScheduler.cancelTaskReminders(id);
        } catch (e) {
          // Ignore errors
        }
      }

      await _syncCalendarForTask(updatedTask);
      if (previousTask?.dueDate != null &&
          updatedTask.dueDate != previousTask!.dueDate) {
        await _refreshCalendarSurfacesForDate(previousTask.dueDate!);
      }

      if (refresh) await refreshTasks();
    });
  }

  /// Generate or regenerate AI guide for an existing task.
  Future<TaskModel> generateGuide(String id) async {
    final updated = await _taskRepository.generateGuide(id);
    // Update the task in local state
    state = state.copyWith(
      tasks: state.tasks.map((t) => t.id == id ? updated : t).toList(),
      todayTasks:
          state.todayTasks.map((t) => t.id == id ? updated : t).toList(),
    );
    unawaited(
      loadTaskGuidance(id),
    );
    return updated;
  }

  String _taskGuidanceKey(String taskId, TaskGuidanceAudience audience) =>
      '$taskId::${audience.wireValue}';

  void _setTaskGuidance(
    String taskId,
    TaskGuidanceAudience audience,
    TaskGuidanceModel? guidance,
  ) {
    final key = _taskGuidanceKey(taskId, audience);
    final next = Map<String, TaskGuidanceModel>.from(state.taskGuidance);
    if (guidance == null) {
      next.remove(key);
    } else {
      next[key] = guidance;
    }
    state = state.copyWith(taskGuidance: next);
  }

  void _setTaskGuidanceLoading(
    String taskId,
    TaskGuidanceAudience audience,
    bool isLoading,
  ) {
    final key = _taskGuidanceKey(taskId, audience);
    final next = Set<String>.from(state.taskGuidanceInFlight);
    if (isLoading) {
      next.add(key);
    } else {
      next.remove(key);
    }
    state = state.copyWith(taskGuidanceInFlight: next);
  }

  Future<TaskGuidanceModel?> loadTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
  }) async {
    _setTaskGuidanceLoading(taskId, audience, true);
    try {
      final guidance = await _taskRepository.getTaskGuidance(
        taskId,
        audience: audience,
      );
      if (guidance != null) {
        _setTaskGuidance(taskId, audience, guidance);
      }
      return guidance;
    } finally {
      _setTaskGuidanceLoading(taskId, audience, false);
    }
  }

  Future<TaskGuidanceModel> createOrRefreshTaskGuidance(
    String taskId, {
    TaskGuidanceAudience audience = TaskGuidanceAudience.human,
    bool regenerate = false,
  }) async {
    _setTaskGuidanceLoading(taskId, audience, true);
    try {
      final guidance = await _taskRepository.createOrRefreshTaskGuidance(
        taskId,
        audience: audience,
        regenerate: regenerate,
      );
      _setTaskGuidance(taskId, audience, guidance);
      if (audience == TaskGuidanceAudience.human) {
        await _refreshTaskFromServer(taskId);
      }
      return guidance;
    } finally {
      _setTaskGuidanceLoading(taskId, audience, false);
    }
  }

  Future<void> deleteTask(String id) async {
    await _runWithErrorHandling(() async {
      final existingTask = state.tasks.cast<TaskModel?>().firstWhere(
            (task) => task?.id == id,
            orElse: () => null,
          );
      // Cancel reminders before deleting
      try {
        await _notificationScheduler.cancelTaskReminders(id);
      } catch (e) {
        // Ignore errors
      }

      await _taskRepository.deleteTask(id);
      await _ref.read(calendarRepositoryProvider).removeTaskLinkedEvent(id);
      if (existingTask?.dueDate != null) {
        await _refreshCalendarSurfacesForDate(existingTask!.dueDate!);
      } else {
        unawaited(_ref.read(calendarProvider.notifier).loadEvents());
      }
      await refreshTasks();
    });
  }

  Future<void> startTask(String id) async {
    await _runWithErrorHandling(() async {
      final updatedTask = await _taskRepository.startTask(id);
      // Also update the task in the list locally to avoid a full refresh
      _updateTaskInState(updatedTask);
      state = state.copyWith(isLoading: false);
    });
  }

  /// 完成任务 - 乐观更新（v2.1 增强）
  Future<TaskCompletionResult?> completeTask(
    String id,
    int minutes,
    String? note,
  ) async {
    // Cancel reminders when completing task
    try {
      await _notificationScheduler.cancelTaskReminders(id);
    } catch (e) {
      // Ignore errors
    }

    // 1. 乐观更新 UI
    _updateTask(
      id,
      (task) => task.copyWith(
        status: TaskStatus.completed,
        completedAt: DateTime.now(),
        actualMinutes: minutes,
        userNote: note,
        syncStatus: TaskSyncStatus.pending, // 🆕 标记为同步中
      ),
    );

    // 2. 后台发送
    try {
      final result = await _taskRepository.completeTask(id, minutes, note);
      final updatedTask = TaskModel.fromJson(result.task);

      // 3. 成功：更新为已同步
      _updateTask(
        id,
        (task) => updatedTask.copyWith(
          syncStatus: TaskSyncStatus.synced,
          // retryToken: updatedTask.retryToken, // Repo needs to return this or we assume updatedTask has it
        ),
      );
      if (updatedTask.planId != null) {
        _ref.invalidate(planDetailProvider(updatedTask.planId!));
      }

      final linkedPrediction = await _ref
          .read(predictionAttributionServiceProvider)
          .consumeForExecution(
            executionType: 'task',
            entityType: 'task',
            entityId: id,
          );
      await _ref.read(appEventStreamServiceProvider).recordEntityExecution(
        entityType: 'task',
        entityId: id,
        actionType: 'complete_task',
        source: 'task_provider',
        payload: {
          'minutes': minutes,
          if (note != null && note.isNotEmpty) 'note': note,
          if (linkedPrediction != null) ...{
            'prediction_id': linkedPrediction['prediction_id'],
            'candidate_id': linkedPrediction['candidate_id'],
            'prediction_action_type': linkedPrediction['action_type'],
            'prediction_surface': linkedPrediction['surface'],
            'prediction_horizon': linkedPrediction['horizon'],
            'prediction_source': linkedPrediction['source'],
          },
        },
      );

      return result;
    } catch (e) {
      // 4. 🆕 失败：标记为失败状态（不直接回滚）
      var errorMsg = '操作失败';
      if (e is DioException) {
        errorMsg = e.message ?? '网络错误';
      }

      _updateTask(
        id,
        (task) => task.copyWith(
          syncStatus: TaskSyncStatus.failed,
          syncError: errorMsg,
        ),
      );
      return null;
    }
  }

  Future<void> _syncCalendarForTask(TaskModel task) async {
    try {
      await _ref.read(calendarRepositoryProvider).syncTaskLinkedEvent(task);
      if (task.dueDate != null) {
        await _refreshCalendarSurfacesForDate(task.dueDate!);
      } else {
        unawaited(_ref.read(calendarProvider.notifier).loadEvents());
      }
    } catch (e) {
      debugPrint('Failed to sync task to calendar: $e');
    }
  }

  Future<void> _refreshCalendarSurfacesForDate(DateTime date) async {
    await _ref.read(taskCalendarProvider.notifier).loadTasksForMonth(
          date,
          force: true,
        );
    await _ref.read(calendarProvider.notifier).loadEvents();
    unawaited(_ref.read(unifiedCalendarProvider.notifier).refreshMonth(date));
  }

  /// 🆕 重试完成任务
  Future<void> retryCompleteTask(String id, int minutes, String? note) async {
    _updateTask(
      id,
      (task) => task.copyWith(
        syncStatus: TaskSyncStatus.pending,
      ),
    );

    try {
      final result = await _taskRepository.completeTask(id, minutes, note);
      final updatedTask = TaskModel.fromJson(result.task);

      _updateTask(
        id,
        (task) => updatedTask.copyWith(
          syncStatus: TaskSyncStatus.synced,
        ),
      );
      if (updatedTask.planId != null) {
        _ref.invalidate(planDetailProvider(updatedTask.planId!));
      }
      final linkedPrediction = await _ref
          .read(predictionAttributionServiceProvider)
          .consumeForExecution(
            executionType: 'task',
            entityType: 'task',
            entityId: id,
          );
      await _ref.read(appEventStreamServiceProvider).recordEntityExecution(
        entityType: 'task',
        entityId: id,
        actionType: 'complete_task',
        source: 'task_provider',
        payload: {
          'minutes': minutes,
          if (note != null && note.isNotEmpty) 'note': note,
          if (linkedPrediction != null) ...{
            'prediction_id': linkedPrediction['prediction_id'],
            'candidate_id': linkedPrediction['candidate_id'],
            'prediction_action_type': linkedPrediction['action_type'],
            'prediction_surface': linkedPrediction['surface'],
            'prediction_horizon': linkedPrediction['horizon'],
            'prediction_source': linkedPrediction['source'],
          },
        },
      );
    } catch (e) {
      var errorMsg = '重试失败';
      if (e is DioException) {
        errorMsg = e.message ?? '网络错误';
      }
      _updateTask(
        id,
        (task) => task.copyWith(
          syncStatus: TaskSyncStatus.failed,
          syncError: errorMsg,
        ),
      );
    }
  }

  /// 🆕 放弃更改（回滚）
  void discardChange(String id) {
    // 从服务器重新加载任务状态 (或者简单地 revert 到某个已知状态 if we stored it)
    // 这里简单地 refresh entire list for simplicity or reload single task
    // _ref.invalidate(taskDetailProvider(id)); // If we had access to ref

    // For now, simple reload
    unawaited(loadTasks());
    unawaited(loadTodayTasks());
  }

  Future<void> abandonTask(String id) async {
    await _runWithErrorHandling(() async {
      final updatedTask = await _taskRepository.abandonTask(id);
      _updateTaskInState(updatedTask);
      state = state.copyWith(isLoading: false);
    });
  }

  Future<TaskQuickActionResult> snoozeTask(String id) async {
    final previousTask = _findTaskInState(id);
    final result = await _taskRepository.snoozeTask(id);

    if (result.task.dueDate != null) {
      final config = _ref.read(taskReminderConfigProvider);
      try {
        await _notificationScheduler.rescheduleTaskReminders(
          result.task,
          config: config,
        );
      } catch (e) {
        debugPrint('Failed to reschedule snoozed task reminders: $e');
      }
    }

    await _syncCalendarForTask(result.task);
    if (previousTask?.dueDate != null &&
        result.task.dueDate != previousTask!.dueDate) {
      await _refreshCalendarSurfacesForDate(previousTask.dueDate!);
    }

    if (!mounted) return result;
    _applyQuickAction(result);
    return result;
  }

  Future<TaskQuickActionResult> markTaskTooHard(
    String id, {
    String? reason,
  }) async {
    final result = await _taskRepository.markTaskTooHard(id, reason: reason);
    if (!mounted) return result;
    _applyQuickAction(result);
    return result;
  }

  Future<TaskQuickActionResult> skipTask(String id) async {
    final previousTask = _findTaskInState(id);
    final result = await _taskRepository.skipTask(id);

    try {
      await _notificationScheduler.cancelTaskReminders(id);
    } catch (e) {
      debugPrint('Failed to cancel skipped task reminders: $e');
    }

    try {
      await _ref.read(calendarRepositoryProvider).removeTaskLinkedEvent(id);
      if (previousTask?.dueDate != null) {
        await _refreshCalendarSurfacesForDate(previousTask!.dueDate!);
      } else {
        unawaited(_ref.read(calendarProvider.notifier).loadEvents());
      }
    } catch (e) {
      debugPrint('Failed to remove skipped task from calendar: $e');
    }

    if (!mounted) return result;
    _applyQuickAction(result);
    return result;
  }

  Future<void> moveTaskToPlan(
    String taskId,
    String? targetPlanId, {
    String? previousPlanId,
  }) async {
    await _runWithErrorHandling(() async {
      await _taskRepository.moveTaskToPlan(taskId, targetPlanId);
      await refreshTasks();
      _ref.invalidate(taskDetailProvider(taskId));
      await _ref.read(planListProvider.notifier).refresh();
      if (previousPlanId != null && previousPlanId.isNotEmpty) {
        _ref.invalidate(planDetailProvider(previousPlanId));
      }
      if (targetPlanId != null && targetPlanId.isNotEmpty) {
        _ref.invalidate(planDetailProvider(targetPlanId));
      }
    });
  }

  Future<void> refreshTasks() async {
    // This could be smarter by only refreshing the lists that are currently visible
    await loadTasks(filter: state.currentFilter);
    await loadTodayTasks();
    await loadRecommendedTasks();
  }

  Future<ExecutionIntentModel?> loadTaskExecutionState(
    String taskId, {
    bool includeRecord = true,
  }) async {
    if (!isServerTaskId(taskId)) return null;

    try {
      final intents = await _taskRepository.listExecutionIntents(taskId);
      final latest = intents.isEmpty ? null : intents.first;
      if (!mounted) return latest;
      _setTaskExecution(taskId, latest);
      if (includeRecord && latest != null) {
        final record = await _taskRepository.getExecutionRecord(latest.id);
        if (!mounted) return latest;
        _setTaskExecutionRecord(taskId, record);
      } else if (latest == null) {
        _setTaskExecutionRecord(taskId, null);
      }
      return latest;
    } catch (e) {
      debugPrint('Failed to load execution intents for $taskId: $e');
      return null;
    }
  }

  Future<List<ExecutionTemplateModel>> loadTaskExecutionTemplates(
    String taskId,
  ) async {
    if (!isServerTaskId(taskId)) return const [];

    try {
      final templates = await _taskRepository.listExecutionTemplates(taskId);
      if (!mounted) return templates;
      final nextTemplates = Map<String, List<ExecutionTemplateModel>>.from(
        state.taskExecutionTemplates,
      );
      nextTemplates[taskId] = templates;

      final nextSelected = Map<String, String>.from(
        state.selectedExecutionTemplateIds,
      );
      final existingSelection = nextSelected[taskId];
      if (templates.isEmpty) {
        nextSelected.remove(taskId);
      } else if (existingSelection == null ||
          templates
              .every((template) => template.templateId != existingSelection)) {
        nextSelected[taskId] = templates.first.templateId;
      }

      state = state.copyWith(
        taskExecutionTemplates: nextTemplates,
        selectedExecutionTemplateIds: nextSelected,
      );
      return templates;
    } catch (e) {
      debugPrint('Failed to load execution templates for $taskId: $e');
      return const [];
    }
  }

  void selectExecutionTemplate(String taskId, String templateId) {
    final nextSelected = Map<String, String>.from(
      state.selectedExecutionTemplateIds,
    );
    nextSelected[taskId] = templateId;
    state = state.copyWith(selectedExecutionTemplateIds: nextSelected);
  }

  Future<ExecutionIntentModel?> handoffTaskToAi(
    String taskId, {
    String? goal,
    String? source,
  }) async {
    if (!isServerTaskId(taskId)) {
      state = state.copyWith(error: '本地任务暂不支持 AI 执行');
      return null;
    }

    if (state.handoffInFlight.contains(taskId)) {
      return state.taskExecutions[taskId];
    }

    final currentIntent = state.taskExecutions[taskId];
    if (currentIntent != null && !currentIntent.isTerminal) {
      return currentIntent;
    }

    _setHandoffLoading(taskId, true);
    if (mounted) {
      state = state.copyWith(clearError: true);
    }

    try {
      final selectedTemplateId = state.selectedExecutionTemplateIds[taskId];
      final connection = _ref.read(openClawConnectionProvider);
      if (!connection.isConnected) {
        if (connection.config.isConfigured) {
          await connection.queueExecutionRequest(
            taskId: taskId,
            goal: goal,
            templateId: selectedTemplateId,
            source: 'task_provider',
            priority: 1,
          );
          if (mounted) {
            state =
                state.copyWith(error: ExecutionCopy.engineOfflineQueuedMessage);
          }
          return null;
        }
        if (mounted) {
          state =
              state.copyWith(error: ExecutionCopy.engineNotConnectedMessage);
        }
        return null;
      }
      final intent = await _taskRepository.handoffTask(
        taskId,
        goal: goal,
        templateId: selectedTemplateId,
        source: source,
      );
      if (!mounted) return intent;

      if (connection.config.isConfigured) {
        connection.markExecutionAvailable();
      }

      _setTaskExecution(taskId, intent);
      final record = await _taskRepository.getExecutionRecord(intent.id);
      if (mounted) {
        _setTaskExecutionRecord(taskId, record);
      }

      try {
        await _refreshTaskFromServer(taskId);
      } catch (e) {
        debugPrint('Failed to refresh task after AI handoff: $e');
      }

      return intent;
    } catch (e) {
      final selectedTemplateId = state.selectedExecutionTemplateIds[taskId];
      final queued = await _handleExecutionDispatchFailure(
        taskId: taskId,
        goal: goal,
        templateId: selectedTemplateId,
        error: e,
      );
      if (!queued && mounted) {
        state = state.copyWith(error: _normalizeErrorMessage(e));
      }
      return null;
    } finally {
      if (mounted) {
        _setHandoffLoading(taskId, false);
      }
    }
  }

  Future<int> drainQueuedAiHandoffs() async {
    final connection = _ref.read(openClawConnectionProvider);
    if (!connection.isConnected || connection.queuedRequests.isEmpty) {
      return 0;
    }

    var dispatched = 0;
    for (final request in connection.queuedRequests) {
      try {
        final intent = await _taskRepository.handoffTask(
          request.taskId,
          goal: request.goal,
          templateId: request.templateId,
          source: request.source,
        );
        if (!mounted) return dispatched;
        _setTaskExecution(request.taskId, intent);
        final record = await _taskRepository.getExecutionRecord(intent.id);
        if (mounted) {
          _setTaskExecutionRecord(request.taskId, record);
        }
        connection.markExecutionAvailable();
        await connection.removeQueuedRequest(request.id);
        dispatched += 1;
      } catch (e) {
        connection.markExecutionUnavailable(_normalizeErrorMessage(e));
        if (mounted) {
          state = state.copyWith(error: _normalizeErrorMessage(e));
        }
        break;
      }
    }
    return dispatched;
  }

  Future<ExecutionIntentModel?> retryExecutionIntent(String intentId) async {
    try {
      final intent = await _taskRepository.retryExecution(intentId);
      if (!mounted) return intent;
      if (intent.taskId.isNotEmpty) {
        _setTaskExecution(intent.taskId, intent);
        final record = await _taskRepository.getExecutionRecord(intent.id);
        if (mounted) {
          _setTaskExecutionRecord(intent.taskId, record);
        }
      }
      return intent;
    } catch (e) {
      if (mounted) {
        state = state.copyWith(error: _normalizeErrorMessage(e));
      }
      return null;
    }
  }

  String _normalizeErrorMessage(Object error) =>
      error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();

  bool _looksLikeExecutionInfrastructureIssue(String message) {
    final normalized = message.toLowerCase();
    return normalized.contains('openclaw') ||
        normalized.contains('operator.write') ||
        normalized.contains('scope') ||
        normalized.contains('网关') ||
        normalized.contains('执行引擎') ||
        normalized.contains('无法连接') ||
        normalized.contains('连接失败') ||
        normalized.contains('authentication failed') ||
        normalized.contains('not enabled') ||
        normalized.contains('temporarily degraded');
  }

  Future<bool> _handleExecutionDispatchFailure({
    required String taskId,
    required String? goal,
    required String? templateId,
    required Object error,
  }) async {
    final connection = _ref.read(openClawConnectionProvider);
    final message = _normalizeErrorMessage(error);
    if (!connection.config.isConfigured ||
        !_looksLikeExecutionInfrastructureIssue(message)) {
      return false;
    }

    await connection.queueExecutionRequest(
      taskId: taskId,
      goal: goal,
      templateId: templateId,
      source: 'task_provider_retry',
      priority: 2,
    );
    connection.markExecutionUnavailable(message);
    if (mounted) {
      state = state.copyWith(error: '$message，已加入等待队列。');
    }
    return true;
  }

  Future<void> reorderTasks(int oldIndex, int newIndex) async {
    final originalTasks = List<TaskModel>.from(state.tasks);
    final normalizedNewIndex = newIndex > oldIndex ? newIndex - 1 : newIndex;
    final reordered = List<TaskModel>.from(state.tasks);
    final moved = reordered.removeAt(oldIndex);
    reordered.insert(normalizedNewIndex, moved);

    state = state.copyWith(
      tasks: [
        for (var i = 0; i < reordered.length; i++)
          reordered[i].copyWith(orderIndex: (i + 1) * 1000),
      ],
      clearError: true,
    );

    try {
      final persisted = await _taskRepository.reorderTasks(
        state.tasks.map((task) => task.id).toList(),
      );
      state = state.copyWith(tasks: persisted);
    } catch (e) {
      state = state.copyWith(tasks: originalTasks, error: e.toString());
    }
  }

  void _updateTaskInState(TaskModel task) {
    state = state.copyWith(
      tasks: state.tasks.map((t) => t.id == task.id ? task : t).toList(),
      todayTasks:
          state.todayTasks.map((t) => t.id == task.id ? task : t).toList(),
      recommendedTasks: state.recommendedTasks
          .map((t) => t.id == task.id ? task : t)
          .toList(),
    );
  }

  Future<ExecutionRecordModel?> confirmTaskExecutionResult(String taskId) =>
      _decideExecutionResult(
        taskId,
        decision: _taskRepository.confirmExecutionResult,
      );

  Future<ExecutionRecordModel?> rejectTaskExecutionResult(
    String taskId, {
    String? reason,
  }) =>
      _decideExecutionResult(
        taskId,
        decision: (recordId) =>
            _taskRepository.rejectExecutionResult(recordId, reason: reason),
      );

  void _updateTask(String taskId, TaskModel Function(TaskModel) updater) {
    state = state.copyWith(
      tasks: state.tasks.map((t) => t.id == taskId ? updater(t) : t).toList(),
      todayTasks:
          state.todayTasks.map((t) => t.id == taskId ? updater(t) : t).toList(),
      recommendedTasks: state.recommendedTasks
          .map((t) => t.id == taskId ? updater(t) : t)
          .toList(),
    );
  }

  TaskModel? _findTaskInState(String taskId) {
    for (final task in state.tasks) {
      if (task.id == taskId) return task;
    }
    for (final task in state.todayTasks) {
      if (task.id == taskId) return task;
    }
    for (final task in state.recommendedTasks) {
      if (task.id == taskId) return task;
    }
    final activeTask = _ref.read(activeTaskProvider);
    if (activeTask?.id == taskId) {
      return activeTask;
    }
    return null;
  }

  List<TaskModel> _replaceTaskInList(
    List<TaskModel> tasks,
    TaskModel task, {
    required bool keep,
  }) {
    final index = tasks.indexWhere((item) => item.id == task.id);
    if (index == -1) return tasks;

    final next = List<TaskModel>.from(tasks);
    if (keep) {
      next[index] = task;
    } else {
      next.removeAt(index);
    }
    return next;
  }

  void _applyQuickAction(TaskQuickActionResult result) {
    final task = result.task;
    final keepTask = task.status != TaskStatus.abandoned;
    final keepInToday = keepTask && _shouldIncludeInToday(task);
    final keepInRecommended = keepTask && result.action == 'too_hard';

    state = state.copyWith(
      tasks: _replaceTaskInList(state.tasks, task, keep: keepTask),
      todayTasks: _replaceTaskInList(
        state.todayTasks,
        task,
        keep: keepInToday,
      ),
      recommendedTasks: _replaceTaskInList(
        state.recommendedTasks,
        task,
        keep: keepInRecommended,
      ),
      clearError: true,
    );

    final activeTask = _ref.read(activeTaskProvider);
    if (activeTask?.id == task.id) {
      _ref.read(activeTaskProvider.notifier).state = keepTask ? task : null;
    }
  }

  void _setTaskExecution(String taskId, ExecutionIntentModel? intent) {
    final nextExecutions = Map<String, ExecutionIntentModel>.from(
      state.taskExecutions,
    );
    if (intent == null) {
      nextExecutions.remove(taskId);
    } else {
      nextExecutions[taskId] = intent;
    }
    state = state.copyWith(taskExecutions: nextExecutions);
  }

  void _setTaskExecutionRecord(String taskId, ExecutionRecordModel? record) {
    final nextRecords = Map<String, ExecutionRecordModel>.from(
      state.taskExecutionRecords,
    );
    if (record == null) {
      nextRecords.remove(taskId);
    } else {
      nextRecords[taskId] = record;
    }
    state = state.copyWith(taskExecutionRecords: nextRecords);
  }

  void _setHandoffLoading(String taskId, bool isLoading) {
    final nextLoading = Set<String>.from(state.handoffInFlight);
    if (isLoading) {
      nextLoading.add(taskId);
    } else {
      nextLoading.remove(taskId);
    }
    state = state.copyWith(handoffInFlight: nextLoading);
  }

  void _setExecutionDecisionLoading(String taskId, bool isLoading) {
    final nextLoading = Set<String>.from(state.executionDecisionInFlight);
    if (isLoading) {
      nextLoading.add(taskId);
    } else {
      nextLoading.remove(taskId);
    }
    state = state.copyWith(executionDecisionInFlight: nextLoading);
  }

  Future<ExecutionRecordModel?> _decideExecutionResult(
    String taskId, {
    required Future<ExecutionRecordModel> Function(String recordId) decision,
  }) async {
    if (state.executionDecisionInFlight.contains(taskId)) {
      return state.taskExecutionRecords[taskId];
    }

    final intent =
        state.taskExecutions[taskId] ?? await loadTaskExecutionState(taskId);
    if (intent == null) {
      state = state.copyWith(error: '没有可处理的 AI 执行记录');
      return null;
    }

    var record = state.taskExecutionRecords[taskId];
    record ??= await _taskRepository.getExecutionRecord(intent.id);
    if (record == null) {
      state = state.copyWith(error: '执行记录暂不可用');
      return null;
    }

    _setExecutionDecisionLoading(taskId, true);
    if (mounted) {
      state = state.copyWith(clearError: true);
    }

    try {
      final updatedRecord = await decision(record.id);
      if (!mounted) return updatedRecord;
      _setTaskExecutionRecord(taskId, updatedRecord);
      await loadTaskExecutionState(taskId);
      await _refreshTaskFromServer(taskId);
      return updatedRecord;
    } catch (e) {
      if (mounted) {
        state = state.copyWith(error: e.toString());
      }
      return null;
    } finally {
      if (mounted) {
        _setExecutionDecisionLoading(taskId, false);
      }
    }
  }

  Future<void> _refreshTaskFromServer(String taskId) async {
    final updatedTask = await _taskRepository.getTask(taskId);
    if (!mounted) return;
    _updateTaskInState(updatedTask);
    final activeTask = _ref.read(activeTaskProvider);
    if (activeTask?.id == taskId) {
      _ref.read(activeTaskProvider.notifier).state = updatedTask;
    }
  }

  /// Submit optional feedback after task completion
  Future<void> submitTaskFeedback(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) =>
      _taskRepository.submitTaskFeedback(taskId, feedback);

  /// Submit task feedback and get response with preference updates
  Future<TaskFeedbackResponse?> submitTaskFeedbackWithResponse(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) =>
      _taskRepository.submitTaskFeedbackWithResponse(taskId, feedback);

  /// Record user interaction with a next action suggestion
  Future<void> recordNextActionSelection(
    String taskId,
    NextAction action,
    int position,
    bool selected,
    int displayedActionsCount,
  ) async {
    try {
      final selection = NextActionSelectionSubmission.fromAction(
        taskId: taskId,
        action: action,
        selected: selected,
        displayPosition: position,
        displayedActionsCount: displayedActionsCount,
      );
      await _taskRepository.recordNextActionSelection(taskId, selection);
    } catch (e) {
      // Selection tracking is optional - fail silently
    }
  }

  /// Record that user skipped all next action suggestions
  Future<void> recordNextActionsSkip(
    String taskId,
    List<NextAction> actions,
  ) async {
    try {
      await _taskRepository.recordNextActionsSkip(taskId, actions);
    } catch (e) {
      // Selection tracking is optional - fail silently
    }
  }
}

// 3. Providers

final taskListProvider = StateNotifierProvider<TaskNotifier, TaskListState>(
  (ref) => TaskNotifier(
    ref.watch(taskRepositoryProvider),
    ref.watch(taskNotificationSchedulerProvider),
    ref,
  ),
);

final taskDetailProvider =
    FutureProvider.family<TaskModel, String>((ref, id) async {
  final taskRepo = ref.watch(taskRepositoryProvider);

  try {
    // 尝试从 API 获取任务
    return await taskRepo.getTask(id);
  } catch (e) {
    // 🔧 Demo 模式或任务不存在时，返回默认的"自由专注"任务
    if (DemoDataService.isDemoMode || isLocalOnlyTaskId(id)) {
      debugPrint('🎭 Using default focus task for: $id');
      return TaskModel(
        id: id,
        userId: 'demo_user',
        title: '自由专注',
        type: TaskType.learning,
        tags: [],
        estimatedMinutes: 25,
        difficulty: 1,
        energyCost: 1,
        priority: 0,
        status: TaskStatus.pending,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
    }

    // 其他情况重新抛出错误
    rethrow;
  }
});

@immutable
class TaskGuidanceRequest {
  const TaskGuidanceRequest(
    this.taskId, {
    this.audience = TaskGuidanceAudience.human,
  });

  final String taskId;
  final TaskGuidanceAudience audience;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TaskGuidanceRequest &&
          runtimeType == other.runtimeType &&
          taskId == other.taskId &&
          audience == other.audience;

  @override
  int get hashCode => Object.hash(taskId, audience);
}

final taskGuidanceProvider =
    FutureProvider.family<TaskGuidanceModel?, TaskGuidanceRequest>(
  (ref, request) async {
    final repository = ref.watch(taskRepositoryProvider);
    return repository.getTaskGuidance(
      request.taskId,
      audience: request.audience,
    );
  },
);

final activeTaskProvider = StateProvider<TaskModel?>((ref) => null);
