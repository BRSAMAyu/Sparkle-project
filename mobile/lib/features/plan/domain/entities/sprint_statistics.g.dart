// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'sprint_statistics.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DailyProgress _$DailyProgressFromJson(Map<String, dynamic> json) =>
    DailyProgress(
      date: DateTime.parse(json['date'] as String),
      tasksCompleted: (json['tasks_completed'] as num).toInt(),
      focusMinutes: (json['focus_minutes'] as num).toInt(),
    );

Map<String, dynamic> _$DailyProgressToJson(DailyProgress instance) =>
    <String, dynamic>{
      'date': instance.date.toIso8601String(),
      'tasks_completed': instance.tasksCompleted,
      'focus_minutes': instance.focusMinutes,
    };

SprintStatistics _$SprintStatisticsFromJson(Map<String, dynamic> json) =>
    SprintStatistics(
      completionRate: (json['completionRate'] as num).toDouble(),
      totalTasks: (json['totalTasks'] as num).toInt(),
      completedTasks: (json['completed_tasks'] as num).toInt(),
      inProgressTasks: (json['in_progress_tasks'] as num).toInt(),
      todoTasks: (json['todoTasks'] as num).toInt(),
      dailyProgress: (json['dailyProgress'] as List<dynamic>)
          .map((e) => DailyProgress.fromJson(e as Map<String, dynamic>))
          .toList(),
      averageFocusMinutes: (json['average_focus_minutes'] as num).toDouble(),
      startDate: json['start_date'] == null
          ? null
          : DateTime.parse(json['start_date'] as String),
      endDate: json['end_date'] == null
          ? null
          : DateTime.parse(json['end_date'] as String),
    );

Map<String, dynamic> _$SprintStatisticsToJson(SprintStatistics instance) =>
    <String, dynamic>{
      'completionRate': instance.completionRate,
      'totalTasks': instance.totalTasks,
      'completed_tasks': instance.completedTasks,
      'in_progress_tasks': instance.inProgressTasks,
      'todoTasks': instance.todoTasks,
      'dailyProgress': instance.dailyProgress,
      'average_focus_minutes': instance.averageFocusMinutes,
      'start_date': instance.startDate?.toIso8601String(),
      'end_date': instance.endDate?.toIso8601String(),
    };

SprintStatisticsWithPlan _$SprintStatisticsWithPlanFromJson(
        Map<String, dynamic> json) =>
    SprintStatisticsWithPlan(
      planId: json['plan_id'] as String,
      planName: json['plan_name'] as String,
      statistics:
          SprintStatistics.fromJson(json['statistics'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$SprintStatisticsWithPlanToJson(
        SprintStatisticsWithPlan instance) =>
    <String, dynamic>{
      'plan_id': instance.planId,
      'plan_name': instance.planName,
      'statistics': instance.statistics,
    };
