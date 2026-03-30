import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/entities/task_model.dart';

part 'plan_model.g.dart';

/// 计划类型
enum PlanType {
  @JsonValue('sprint')
  sprint,
  @JsonValue('growth')
  growth,
}

/// 计划阶段
enum PlanStage {
  @JsonValue('sprint')
  sprint,
  @JsonValue('daily')
  daily,
  @JsonValue('review')
  review,
  @JsonValue('paused')
  paused,
}

/// 计划优先级
enum PlanPriority {
  @JsonValue('critical')
  critical,
  @JsonValue('high')
  high,
  @JsonValue('normal')
  normal,
  @JsonValue('low')
  low,
}

@JsonSerializable()
class PlanModel {
  PlanModel({
    required this.id,
    required this.userId,
    required this.name,
    required this.type,
    required this.dailyAvailableMinutes,
    required this.masteryLevel,
    required this.progress,
    required this.isActive,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.targetDate,
    this.subject,
    this.totalEstimatedHours,
    this.tasks,
    this.source,
    this.sourceMetadata,
    this.planStage = PlanStage.sprint,
    this.priority = PlanPriority.normal,
    this.isPrimary = false,
  });

  factory PlanModel.fromJson(Map<String, dynamic> json) =>
      _$PlanModelFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  final String name;
  final PlanType type;
  final String? description;
  @JsonKey(name: 'target_date')
  final DateTime? targetDate;
  final String? subject;
  @JsonKey(name: 'daily_available_minutes')
  final int dailyAvailableMinutes;
  @JsonKey(name: 'total_estimated_hours')
  final double? totalEstimatedHours;
  @JsonKey(name: 'mastery_level')
  final double masteryLevel;
  final double progress;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  final List<TaskModel>? tasks;
  final String? source;
  @JsonKey(name: 'source_metadata')
  final Map<String, dynamic>? sourceMetadata;
  @JsonKey(name: 'plan_stage')
  final PlanStage planStage;
  final PlanPriority priority;
  @JsonKey(name: 'is_primary')
  final bool isPrimary;
  Map<String, dynamic> toJson() => _$PlanModelToJson(this);
}

@JsonSerializable()
class PlanCreate {
  PlanCreate({
    required this.name,
    required this.type,
    required this.dailyAvailableMinutes,
    this.description,
    this.targetDate,
    this.subject,
    this.totalEstimatedHours,
    this.priority = PlanPriority.normal,
    this.planStage,
  });

  factory PlanCreate.fromJson(Map<String, dynamic> json) =>
      _$PlanCreateFromJson(json);
  final String name;
  final PlanType type;
  final String? description;
  @JsonKey(name: 'target_date')
  final DateTime? targetDate;
  final String? subject;
  @JsonKey(name: 'daily_available_minutes')
  final int dailyAvailableMinutes;
  @JsonKey(name: 'total_estimated_hours')
  final double? totalEstimatedHours;
  final PlanPriority priority;
  @JsonKey(name: 'plan_stage')
  final PlanStage? planStage;
  Map<String, dynamic> toJson() => _$PlanCreateToJson(this);
}

@JsonSerializable()
class PlanUpdate {
  PlanUpdate({
    this.name,
    this.description,
    this.targetDate,
    this.dailyAvailableMinutes,
    this.totalEstimatedHours,
    this.isActive,
    this.priority,
    this.planStage,
  });

  factory PlanUpdate.fromJson(Map<String, dynamic> json) =>
      _$PlanUpdateFromJson(json);
  final String? name;
  final String? description;
  @JsonKey(name: 'target_date')
  final DateTime? targetDate;
  @JsonKey(name: 'daily_available_minutes')
  final int? dailyAvailableMinutes;
  @JsonKey(name: 'total_estimated_hours')
  final double? totalEstimatedHours;
  @JsonKey(name: 'is_active')
  final bool? isActive;
  final PlanPriority? priority;
  @JsonKey(name: 'plan_stage')
  final PlanStage? planStage;
  Map<String, dynamic> toJson() => _$PlanUpdateToJson(this);
}

@JsonSerializable()
class PlanProgress {
  PlanProgress({
    required this.planId,
    required this.progress,
    required this.completedTasks,
    required this.totalTasks,
    this.totalMinutesSpent = 0,
    this.estimatedRemainingHours,
  });

  factory PlanProgress.fromJson(Map<String, dynamic> json) =>
      _$PlanProgressFromJson(json);
  @JsonKey(name: 'plan_id')
  final String planId;
  final double progress;
  @JsonKey(name: 'completed_tasks')
  final int completedTasks;
  @JsonKey(name: 'total_tasks')
  final int totalTasks;
  @JsonKey(name: 'total_minutes_spent')
  final int totalMinutesSpent;
  @JsonKey(name: 'estimated_remaining_hours')
  final double? estimatedRemainingHours;
  Map<String, dynamic> toJson() => _$PlanProgressToJson(this);
}
