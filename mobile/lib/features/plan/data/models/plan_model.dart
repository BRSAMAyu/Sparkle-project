import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/entities/task_model.dart';

part 'plan_model.g.dart';

enum PlanType {
  sprint,
  growth,
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
  Map<String, dynamic> toJson() => _$PlanCreateToJson(this);
}

@JsonSerializable()
class PlanUpdate {
  PlanUpdate({
    this.name,
    this.description,
    this.dailyAvailableMinutes,
    this.isActive,
  });

  factory PlanUpdate.fromJson(Map<String, dynamic> json) =>
      _$PlanUpdateFromJson(json);
  final String? name;
  final String? description;
  @JsonKey(name: 'daily_available_minutes')
  final int? dailyAvailableMinutes;
  @JsonKey(name: 'is_active')
  final bool? isActive;
  Map<String, dynamic> toJson() => _$PlanUpdateToJson(this);
}

@JsonSerializable()
class PlanProgress {
  PlanProgress({
    required this.planId,
    required this.progress,
    required this.completedTasks,
    required this.totalTasks,
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
  Map<String, dynamic> toJson() => _$PlanProgressToJson(this);
}
