import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/domain/entities/sprint_statistics.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Sprint statistics provider
///
/// Calculates statistics for the current active sprint based on task data.
final sprintStatisticsProvider = Provider<SprintStatistics>((ref) {
  final dashboardState = ref.watch(dashboardProvider);
  final taskState = ref.watch(taskListProvider);

  // No active sprint - return empty statistics
  if (dashboardState.sprint == null) {
    return SprintStatistics(
      completionRate: 0.0,
      totalTasks: 0,
      completedTasks: 0,
      inProgressTasks: 0,
      todoTasks: 0,
      dailyProgress: [],
      averageFocusMinutes: 0.0,
    );
  }

  final sprintPlanId = dashboardState.sprint!.id;

  // Get all tasks for this sprint
  final sprintTasks = taskState.tasks.where((t) => t.planId == sprintPlanId).toList();

  // Count by status
  final totalTasks = sprintTasks.length;
  final completedTasks = sprintTasks.where((t) => t.status == TaskStatus.completed).length;
  final inProgressTasks = sprintTasks.where((t) => t.status == TaskStatus.inProgress).length;
  final todoTasks = sprintTasks.where((t) => t.status == TaskStatus.pending).length;

  // Calculate completion rate
  final completionRate = totalTasks > 0 ? completedTasks / totalTasks : 0.0;

  // Calculate average focus time from completed tasks
  final completedTasksWithTime = sprintTasks
      .where((t) => t.status == TaskStatus.completed && t.actualMinutes != null)
      .toList();
  final totalFocusMinutes = completedTasksWithTime.fold<int>(
    0,
    (sum, t) => sum + (t.actualMinutes ?? 0),
  );
  final averageFocusMinutes = completedTasksWithTime.isNotEmpty
      ? totalFocusMinutes / completedTasksWithTime.length
      : 0.0;

  // Generate daily progress data from completed tasks
  final dailyProgress = _calculateDailyProgress(sprintTasks);

  return SprintStatistics(
    completionRate: completionRate,
    totalTasks: totalTasks,
    completedTasks: completedTasks,
    inProgressTasks: inProgressTasks,
    todoTasks: todoTasks,
    dailyProgress: dailyProgress,
    averageFocusMinutes: averageFocusMinutes,
    startDate: _calculateStartDate(sprintTasks),
    endDate: DateTime.now(),
  );
});

/// Calculate daily progress from tasks
List<DailyProgress> _calculateDailyProgress(List<TaskModel> tasks) {
  final completedByDate = <String, List<DateTime>>{};

  // Group completed tasks by completion date
  for (final task in tasks) {
    if (task.status == TaskStatus.completed && task.completedAt != null) {
      final dateKey = '${task.completedAt!.year}-${task.completedAt!.month}-${task.completedAt!.day}';
      completedByDate.putIfAbsent(dateKey, () => []).add(task.completedAt!);
    }
  }

  // Convert to DailyProgress objects
  final progress = <DailyProgress>[];
  final sortedDates = completedByDate.keys.toList()..sort();

  for (final dateKey in sortedDates) {
    final parts = dateKey.split('-');
    final date = DateTime(
      int.parse(parts[0]),
      int.parse(parts[1]),
      int.parse(parts[2]),
    );
    final completedTasks = completedByDate[dateKey]!;

    // Calculate actual focus minutes from tasks
    final actualFocusMinutes = tasks
        .where((t) =>
            t.status == TaskStatus.completed &&
            t.completedAt != null &&
            t.completedAt!.year == date.year &&
            t.completedAt!.month == date.month &&
            t.completedAt!.day == date.day,)
        .fold<int>(0, (sum, t) => sum + (t.actualMinutes ?? 0));

    progress.add(DailyProgress(
      date: date,
      tasksCompleted: completedTasks.length,
      focusMinutes: actualFocusMinutes > 0
          ? actualFocusMinutes
          : completedTasks.length * 30, // Fallback to estimate
    ),);
  }

  return progress;
}

/// Calculate approximate start date from the oldest task
DateTime? _calculateStartDate(List<TaskModel> tasks) {
  if (tasks.isEmpty) return null;

  // Find the oldest created date
  DateTime? oldestDate;
  for (final task in tasks) {
    if (oldestDate == null || task.createdAt.isBefore(oldestDate)) {
      oldestDate = task.createdAt;
    }
  }

  return oldestDate;
}
