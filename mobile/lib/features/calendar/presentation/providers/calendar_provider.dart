import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart' show taskRepositoryProvider;

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
      pending.hashCode ^ inProgress.hashCode ^ completed.hashCode ^ overdue.hashCode;
}

class CalendarState {
  CalendarState({this.events = const [], this.isLoading = false});
  final List<CalendarEventModel> events;
  final bool isLoading;
}

class CalendarNotifier extends StateNotifier<CalendarState> {
  CalendarNotifier(this._repository) : super(CalendarState()) {
    loadEvents();
  }
  final CalendarRepository _repository;

  Future<void> loadEvents() async {
    state = CalendarState(events: state.events, isLoading: true);
    final events = await _repository.getEvents();
    state = CalendarState(events: events);
  }

  Future<void> addEvent(CalendarEventModel event) async {
    await _repository.addEvent(event);
    loadEvents();
  }

  Future<void> updateEvent(CalendarEventModel event) async {
    await _repository.updateEvent(event);
    loadEvents();
  }

  Future<void> deleteEvent(String id) async {
    await _repository.deleteEvent(id);
    loadEvents();
  }

  List<CalendarEventModel> getEventsForDay(DateTime day) =>
      state.events.where((event) => isSameDay(event.startTime, day)).toList();

  bool isSameDay(DateTime? a, DateTime? b) {
    if (a == null || b == null) return false;
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

final calendarProvider =
    StateNotifierProvider<CalendarNotifier, CalendarState>((ref) {
  final repository = ref.watch(calendarRepositoryProvider);
  return CalendarNotifier(repository);
});

/// Task calendar state
class TaskCalendarState {
  TaskCalendarState({this.taskSummaries = const {}});

  final Map<DateTime, TaskDaySummary> taskSummaries;

  TaskCalendarState copyWith(Map<DateTime, TaskDaySummary>? taskSummaries) =>
      TaskCalendarState(taskSummaries: taskSummaries ?? this.taskSummaries);
}

/// Task calendar notifier for loading task summaries
class TaskCalendarNotifier extends StateNotifier<TaskCalendarState> {
  TaskCalendarNotifier(this._taskRepository) : super(TaskCalendarState());

  final TaskRepository _taskRepository;

  /// Load tasks for a specific month and calculate summaries
  Future<void> loadTasksForMonth(DateTime month) async {
    try {
      final start = DateTime(month.year, month.month, 1);
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
            break;
          case TaskStatus.inProgress:
            newSummary = existing.copyWith(
              inProgress: existing.inProgress + 1,
              overdue: isOverdue ? existing.overdue + 1 : existing.overdue,
            );
            break;
          case TaskStatus.completed:
            newSummary = existing.copyWith(
              completed: existing.completed + 1,
            );
            break;
          case TaskStatus.abandoned:
            // Don't show abandoned tasks
            newSummary = existing;
            break;
        }

        summaries[dueDate] = newSummary;
      }

      state = TaskCalendarState(taskSummaries: summaries);
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
