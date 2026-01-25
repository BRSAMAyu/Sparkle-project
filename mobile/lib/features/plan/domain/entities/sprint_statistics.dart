import 'package:json_annotation/json_annotation.dart';

part 'sprint_statistics.g.dart';

/// Daily progress data for sprint statistics
@JsonSerializable()
class DailyProgress {
  DailyProgress({
    required this.date,
    required this.tasksCompleted,
    required this.focusMinutes,
  });

  factory DailyProgress.fromJson(Map<String, dynamic> json) =>
      _$DailyProgressFromJson(json);

  final DateTime date;
  @JsonKey(name: 'tasks_completed')
  final int tasksCompleted;
  @JsonKey(name: 'focus_minutes')
  final int focusMinutes;

  Map<String, dynamic> toJson() => _$DailyProgressToJson(this);

  DailyProgress copyWith({
    DateTime? date,
    int? tasksCompleted,
    int? focusMinutes,
  }) =>
      DailyProgress(
        date: date ?? this.date,
        tasksCompleted: tasksCompleted ?? this.tasksCompleted,
        focusMinutes: focusMinutes ?? this.focusMinutes,
      );
}

/// Sprint statistics data model
@JsonSerializable()
class SprintStatistics {
  SprintStatistics({
    required this.completionRate,
    required this.totalTasks,
    required this.completedTasks,
    required this.inProgressTasks,
    required this.todoTasks,
    required this.dailyProgress,
    required this.averageFocusMinutes,
    this.startDate,
    this.endDate,
  });

  factory SprintStatistics.fromJson(Map<String, dynamic> json) =>
      _$SprintStatisticsFromJson(json);

  /// Overall completion rate (0.0 - 1.0)
  final double completionRate;

  /// Total number of tasks in the sprint
  final int totalTasks;

  /// Number of completed tasks
  @JsonKey(name: 'completed_tasks')
  final int completedTasks;

  /// Number of in-progress tasks
  @JsonKey(name: 'in_progress_tasks')
  final int inProgressTasks;

  /// Number of todo tasks
  final int todoTasks;

  /// Daily progress data
  final List<DailyProgress> dailyProgress;

  /// Average focus time in minutes per day
  @JsonKey(name: 'average_focus_minutes')
  final double averageFocusMinutes;

  /// Sprint start date
  @JsonKey(name: 'start_date')
  final DateTime? startDate;

  /// Sprint end date (null if ongoing)
  @JsonKey(name: 'end_date')
  final DateTime? endDate;

  Map<String, dynamic> toJson() => _$SprintStatisticsToJson(this);

  /// Calculate remaining tasks
  int get remainingTasks => totalTasks - completedTasks;

  /// Calculate sprint duration in days
  int get durationDays {
    if (startDate == null) return 0;
    final end = endDate ?? DateTime.now();
    return end.difference(startDate!).inDays + 1;
  }

  /// Calculate average tasks completed per day
  double get averageTasksPerDay {
    if (durationDays == 0) return 0;
    return completedTasks / durationDays;
  }

  SprintStatistics copyWith({
    double? completionRate,
    int? totalTasks,
    int? completedTasks,
    int? inProgressTasks,
    int? todoTasks,
    List<DailyProgress>? dailyProgress,
    double? averageFocusMinutes,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      SprintStatistics(
        completionRate: completionRate ?? this.completionRate,
        totalTasks: totalTasks ?? this.totalTasks,
        completedTasks: completedTasks ?? this.completedTasks,
        inProgressTasks: inProgressTasks ?? this.inProgressTasks,
        todoTasks: todoTasks ?? this.todoTasks,
        dailyProgress: dailyProgress ?? this.dailyProgress,
        averageFocusMinutes: averageFocusMinutes ?? this.averageFocusMinutes,
        startDate: startDate ?? this.startDate,
        endDate: endDate ?? this.endDate,
      );
}

/// Sprint statistics with plan information
@JsonSerializable()
class SprintStatisticsWithPlan {
  SprintStatisticsWithPlan({
    required this.planId,
    required this.planName,
    required this.statistics,
  });

  factory SprintStatisticsWithPlan.fromJson(Map<String, dynamic> json) =>
      _$SprintStatisticsWithPlanFromJson(json);

  @JsonKey(name: 'plan_id')
  final String planId;
  @JsonKey(name: 'plan_name')
  final String planName;
  final SprintStatistics statistics;

  Map<String, dynamic> toJson() => _$SprintStatisticsWithPlanToJson(this);

  SprintStatisticsWithPlan copyWith({
    String? planId,
    String? planName,
    SprintStatistics? statistics,
  }) =>
      SprintStatisticsWithPlan(
        planId: planId ?? this.planId,
        planName: planName ?? this.planName,
        statistics: statistics ?? this.statistics,
      );
}
