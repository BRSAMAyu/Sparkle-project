import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/next_action_selection_submission.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart' show TaskNotificationScheduler, TaskReminderConfig, taskNotificationSchedulerProvider, taskReminderConfigProvider;

// A dummy filter class for now
class TaskFilter {}

// 1. TaskListState Class
class TaskListState {
  TaskListState({
    this.isLoading = false,
    this.tasks = const [],
    this.todayTasks = const [],
    this.recommendedTasks = const [],
    this.currentFilter,
    this.error,
  });
  final bool isLoading;
  final List<TaskModel> tasks;
  final List<TaskModel> todayTasks;
  final List<TaskModel> recommendedTasks;
  final TaskFilter? currentFilter;
  final String? error;

  TaskListState copyWith({
    bool? isLoading,
    List<TaskModel>? tasks,
    List<TaskModel>? todayTasks,
    List<TaskModel>? recommendedTasks,
    TaskFilter? currentFilter,
    String? error,
    bool clearError = false,
  }) =>
      TaskListState(
        isLoading: isLoading ?? this.isLoading,
        tasks: tasks ?? this.tasks,
        todayTasks: todayTasks ?? this.todayTasks,
        recommendedTasks: recommendedTasks ?? this.recommendedTasks,
        currentFilter: currentFilter ?? this.currentFilter,
        error: clearError ? null : error ?? this.error,
      );
}

// 2. TaskNotifier Class
class TaskNotifier extends StateNotifier<TaskListState> {
  TaskNotifier(this._taskRepository, this._notificationScheduler, this._ref)
      : super(TaskListState()) {
    // Load initial data
    loadTodayTasks();
    loadRecommendedTasks();
    loadTasks();
  }
  final TaskRepository _taskRepository;
  final TaskNotificationScheduler _notificationScheduler;
  final Ref _ref;

  Future<void> _runWithErrorHandling(Future<void> Function() action) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      await action();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadTasks({TaskFilter? filter}) async {
    await _runWithErrorHandling(() async {
      final paginatedResponse =
          await _taskRepository.getTasks(filters: {}); // Add filter logic later
      state = state.copyWith(
          isLoading: false,
          tasks: paginatedResponse.items,
          currentFilter: filter,);
    });
  }

  Future<void> loadTodayTasks() async {
    await _runWithErrorHandling(() async {
      final tasks = await _taskRepository.getTodayTasks();
      state = state.copyWith(isLoading: false, todayTasks: tasks);
    });
  }

  Future<void> loadRecommendedTasks() async {
    await _runWithErrorHandling(() async {
      final tasks = await _taskRepository.getRecommendedTasks();
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

      await refreshTasks();
    });
  }

  Future<void> updateTask(String id, TaskUpdate taskUpdate,
      {bool refresh = true,}) async {
    await _runWithErrorHandling(() async {
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

      if (refresh) await refreshTasks();
    });
  }

  Future<void> deleteTask(String id) async {
    await _runWithErrorHandling(() async {
      // Cancel reminders before deleting
      try {
        await _notificationScheduler.cancelTaskReminders(id);
      } catch (e) {
        // Ignore errors
      }

      await _taskRepository.deleteTask(id);
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
      String id, int minutes, String? note,) async {
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
    loadTasks();
    loadTodayTasks();
  }

  Future<void> abandonTask(String id) async {
    await _runWithErrorHandling(() async {
      final updatedTask = await _taskRepository.abandonTask(id);
      _updateTaskInState(updatedTask);
      state = state.copyWith(isLoading: false);
    });
  }

  Future<void> refreshTasks() async {
    // This could be smarter by only refreshing the lists that are currently visible
    await loadTasks(filter: state.currentFilter);
    await loadTodayTasks();
    await loadRecommendedTasks();
  }

  void _updateTaskInState(TaskModel task) {
    state = state.copyWith(
      tasks: state.tasks.map((t) => t.id == task.id ? task : t).toList(),
      todayTasks:
          state.todayTasks.map((t) => t.id == task.id ? task : t).toList(),
    );
  }

  void _updateTask(String taskId, TaskModel Function(TaskModel) updater) {
    state = state.copyWith(
      tasks: state.tasks.map((t) => t.id == taskId ? updater(t) : t).toList(),
      todayTasks:
          state.todayTasks.map((t) => t.id == taskId ? updater(t) : t).toList(),
    );
  }

  /// Submit optional feedback after task completion
  Future<void> submitTaskFeedback(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) async {
    try {
      await _taskRepository.submitTaskFeedback(taskId, feedback);
    } catch (e) {
      // Feedback is optional - fail silently
      // Don't update state or show errors
    }
  }

  /// Submit task feedback and get response with preference updates
  Future<TaskFeedbackResponse?> submitTaskFeedbackWithResponse(
    String taskId,
    TaskFeedbackSubmission feedback,
  ) async {
    try {
      return await _taskRepository.submitTaskFeedbackWithResponse(
        taskId,
        feedback,
      );
    } catch (e) {
      // Feedback is optional - fail silently
      return null;
    }
  }

  /// Record user interaction with a next action suggestion
  Future<void> recordNextActionSelection(
    String taskId,
    NextAction action,
    int position,
    bool selected,
  ) async {
    try {
      final selection = NextActionSelectionSubmission.fromAction(
        taskId: taskId,
        action: action,
        selected: selected,
        displayPosition: position,
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
    ),);

final taskDetailProvider = FutureProvider.family<TaskModel, String>((ref, id) {
  final taskRepo = ref.watch(taskRepositoryProvider);
  return taskRepo.getTask(id);
});

final activeTaskProvider = StateProvider<TaskModel?>((ref) => null);
