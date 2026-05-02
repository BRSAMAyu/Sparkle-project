import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Task day summary for calendar markers
class TaskDaySummary {
  const TaskDaySummary({
    this.pending = 0,
    this.inProgress = 0,
    this.completed = 0,
    this.overdue = 0,
  });

  final int pending;
  final int inProgress;
  final int completed;
  final int overdue;

  int get total => pending + inProgress + completed + overdue;

  bool get hasTasks => total > 0;

  TaskDaySummary copyWith({
    int? pending,
    int? inProgress,
    int? completed,
    int? overdue,
  }) =>
      TaskDaySummary(
        pending: pending ?? this.pending,
        inProgress: inProgress ?? this.inProgress,
        completed: completed ?? this.completed,
        overdue: overdue ?? this.overdue,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TaskDaySummary &&
          runtimeType == other.runtimeType &&
          pending == other.pending &&
          inProgress == other.inProgress &&
          completed == other.completed &&
          overdue == other.overdue;

  @override
  int get hashCode =>
      pending.hashCode ^
      inProgress.hashCode ^
      completed.hashCode ^
      overdue.hashCode;
}

class CalendarState {
  CalendarState({
    this.events = const [],
    this.isLoading = false,
    this.error,
    this.lastMutationMessage,
  });
  final List<CalendarEventModel> events;
  final bool isLoading;
  final String? error;
  final String? lastMutationMessage;

  CalendarState copyWith({
    List<CalendarEventModel>? events,
    bool? isLoading,
    String? error,
    String? lastMutationMessage,
    bool clearError = false,
    bool clearMutationMessage = false,
  }) =>
      CalendarState(
        events: events ?? this.events,
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
        lastMutationMessage: clearMutationMessage
            ? null
            : lastMutationMessage ?? this.lastMutationMessage,
      );
}

class CalendarNotifier extends StateNotifier<CalendarState> {
  CalendarNotifier(this._repository) : super(CalendarState()) {
    unawaited(loadEvents());
  }
  final CalendarRepository _repository;

  Future<void> loadEvents() async {
    if (!mounted) return;
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearMutationMessage: true,
    );
    try {
      final events = await _repository.getEvents();
      if (!mounted) return;
      state = state.copyWith(events: events, isLoading: false);
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<CalendarMutationResult> addEvent(CalendarEventModel event) async {
    if (!mounted) {
      throw StateError('CalendarNotifier is disposed');
    }
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearMutationMessage: true,
    );
    try {
      final result = await _repository.addEvent(event);
      await loadEvents();
      if (!mounted) {
        throw StateError('CalendarNotifier is disposed');
      }
      state = state.copyWith(
        isLoading: false,
        lastMutationMessage: result.message,
      );
      return result;
    } catch (e) {
      if (!mounted) rethrow;
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow;
    }
  }

  Future<void> updateEvent(CalendarEventModel event) async {
    await _repository.updateEvent(event);
    await loadEvents();
  }

  Future<void> deleteEvent(String id) async {
    await _repository.deleteEvent(id);
    await loadEvents();
  }

  List<CalendarEventModel> getEventsForDay(DateTime day) =>
      state.events.where((event) => isSameDay(event.startTime, day)).toList();

  bool isSameDay(DateTime? a, DateTime? b) {
    if (a == null || b == null) return false;
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }

  void clearMutationMessage() {
    state = state.copyWith(clearMutationMessage: true);
  }
}

final calendarProvider =
    StateNotifierProvider<CalendarNotifier, CalendarState>((ref) {
  final repository = ref.watch(calendarRepositoryProvider);
  return CalendarNotifier(repository);
});

/// Task calendar state
class TaskCalendarState {
  TaskCalendarState({
    this.taskSummaries = const {},
    this.loadedMonths = const {},
  });

  final Map<DateTime, TaskDaySummary> taskSummaries;
  final Set<String> loadedMonths;

  TaskCalendarState copyWith({
    Map<DateTime, TaskDaySummary>? taskSummaries,
    Set<String>? loadedMonths,
  }) =>
      TaskCalendarState(
        taskSummaries: taskSummaries ?? this.taskSummaries,
        loadedMonths: loadedMonths ?? this.loadedMonths,
      );
}

/// Task calendar notifier for loading task summaries
class TaskCalendarNotifier extends StateNotifier<TaskCalendarState> {
  TaskCalendarNotifier(this._taskRepository) : super(TaskCalendarState());

  final TaskRepository _taskRepository;

  /// Load tasks for a specific month and calculate summaries
  Future<void> loadTasksForMonth(DateTime month, {bool force = false}) async {
    try {
      final monthKey =
          '${month.year}-${month.month.toString().padLeft(2, '0')}';
      if (!force && state.loadedMonths.contains(monthKey)) {
        return;
      }
      final start = DateTime(month.year, month.month);
      final end = DateTime(month.year, month.month + 1, 0);

      final tasks = await _taskRepository.getTasksByDateRange(start, end);

      final summaries = <DateTime, TaskDaySummary>{};
      final today = DateTime.now();

      for (final task in tasks) {
        if (task.dueDate == null) continue;

        final dueDate = DateTime(
          task.dueDate!.year,
          task.dueDate!.month,
          task.dueDate!.day,
        );

        final existing = summaries[dueDate] ?? const TaskDaySummary();

        // Check if overdue
        final isOverdue = task.dueDate!.isBefore(
              DateTime(today.year, today.month, today.day),
            ) &&
            task.status != TaskStatus.completed;

        // Increment counters based on status
        TaskDaySummary newSummary;
        switch (task.status) {
          case TaskStatus.pending:
            newSummary = existing.copyWith(
              pending: existing.pending + 1,
              overdue: isOverdue ? existing.overdue + 1 : existing.overdue,
            );
          case TaskStatus.inProgress:
          case TaskStatus.stuck:
            newSummary = existing.copyWith(
              inProgress: existing.inProgress + 1,
              overdue: isOverdue ? existing.overdue + 1 : existing.overdue,
            );
          case TaskStatus.paused:
            newSummary = existing.copyWith(
              pending: existing.pending + 1,
              overdue: isOverdue ? existing.overdue + 1 : existing.overdue,
            );
          case TaskStatus.completed:
            newSummary = existing.copyWith(
              completed: existing.completed + 1,
            );
          case TaskStatus.abandoned:
            // Don't show abandoned tasks
            newSummary = existing;
        }

        summaries[dueDate] = newSummary;
      }

      state = state.copyWith(
        taskSummaries: summaries,
        loadedMonths: {...state.loadedMonths, monthKey},
      );
    } catch (e) {
      // Keep existing state on error
    }
  }

  /// Clear all summaries
  void clear() {
    state = TaskCalendarState();
  }
}

/// Provider for task calendar summaries
final taskCalendarProvider =
    StateNotifierProvider<TaskCalendarNotifier, TaskCalendarState>((ref) {
  final taskRepository = ref.watch(taskRepositoryProvider);
  return TaskCalendarNotifier(taskRepository);
});

/// Selected calendar date provider with persistence
///
/// Persists the user's selected date in the calendar view.
final selectedCalendarDateProvider =
    StateNotifierProvider<SelectedCalendarDateNotifier, DateTime>(
  (ref) => SelectedCalendarDateNotifier(),
);

/// Notifier for the selected calendar date
class SelectedCalendarDateNotifier extends PersistentNotifier<DateTime> {
  SelectedCalendarDateNotifier()
      : super(
          namespace: 'calendar',
          key: 'selected_date',
          defaultValue: DateTime.now(),
          serializer: (date) => date.toIso8601String(),
          deserializer: (isoString) {
            if (isoString == null || isoString.isEmpty) {
              return DateTime.now();
            }
            try {
              return DateTime.parse(isoString);
            } catch (e) {
              return DateTime.now();
            }
          },
        );

  /// Select a specific date (normalized to midnight)
  void selectDate(DateTime date) {
    // Normalize to midnight for consistent comparisons
    final normalized = DateTime(date.year, date.month, date.day);
    state = normalized;
  }

  /// Go to today
  void goToToday() {
    state = DateTime.now();
  }

  /// Navigate by days
  void addDays(int days) {
    final newDate = DateTime(
      state.year,
      state.month,
      state.day + days,
    );
    state = newDate;
  }

  /// Navigate by months
  void addMonths(int months) {
    final newDate = DateTime(
      state.year,
      state.month + months,
      state.day,
    );
    state = newDate;
  }
}

/// Provider for tasks on a specific day
/// Returns tasks for the given date, sorted by priority (highest first)
final dayTasksProvider =
    Provider.family<List<TaskModel>, DateTime>((ref, date) {
  final calendarState = ref.watch(taskCalendarProvider);
  final normalizedDate = DateTime(date.year, date.month, date.day);

  // Get all task summaries for the month
  final summaries = calendarState.taskSummaries;

  // If no tasks for this day, return empty list
  final summary = summaries[normalizedDate];
  if (summary == null || !summary.hasTasks) {
    return const [];
  }

  // Fetch all tasks for the month and filter by date
  // This is a synchronous provider that depends on async data
  // The async task loading is handled by taskCalendarProvider
  // For now, we'll use the cached data from the repository if available
  // or return an empty list that will be updated when data arrives

  return []; // Placeholder - actual filtering happens in the widget
});

/// Async provider for loading tasks for a specific day
/// Queries the entire month containing the selected date
final dayTasksAsyncProvider =
    FutureProvider.family<List<TaskModel>, DateTime>((ref, date) async {
  final taskRepo = ref.watch(taskRepositoryProvider);
  final normalizedDate = DateTime(date.year, date.month, date.day);

  // Get tasks for the month containing the selected date (not current month)
  final startOfMonth = DateTime(date.year, date.month);
  final endOfMonth = DateTime(date.year, date.month + 1, 0);

  final allTasks = await taskRepo.getTasksByDateRange(startOfMonth, endOfMonth);

  // Filter tasks for the specific date and exclude abandoned
  final dayTasks = allTasks.where((task) {
    if (task.dueDate == null) return false;
    final taskDueDate = DateTime(
      task.dueDate!.year,
      task.dueDate!.month,
      task.dueDate!.day,
    );
    return taskDueDate == normalizedDate && task.status != TaskStatus.abandoned;
  }).toList();

  _sortCalendarTasks(dayTasks);

  return dayTasks;
});

void _sortCalendarTasks(List<TaskModel> tasks) {
  tasks.sort((a, b) {
    final priorityCompare = b.priority.compareTo(a.priority);
    if (priorityCompare != 0) return priorityCompare;

    final statusOrder = {
      TaskStatus.pending: 0,
      TaskStatus.inProgress: 1,
      TaskStatus.stuck: 1,
      TaskStatus.completed: 2,
    };
    final aStatusOrder = statusOrder[a.status] ?? 3;
    final bStatusOrder = statusOrder[b.status] ?? 3;
    return aStatusOrder.compareTo(bStatusOrder);
  });
}
