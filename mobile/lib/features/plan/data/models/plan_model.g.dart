// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'plan_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PlanModel _$PlanModelFromJson(Map<String, dynamic> json) => PlanModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      name: json['name'] as String,
      type: $enumDecode(_$PlanTypeEnumMap, json['type']),
      dailyAvailableMinutes: (json['daily_available_minutes'] as num).toInt(),
      masteryLevel: (json['mastery_level'] as num).toDouble(),
      progress: (json['progress'] as num).toDouble(),
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      targetDate: json['target_date'] == null
          ? null
          : DateTime.parse(json['target_date'] as String),
      subject: json['subject'] as String?,
      totalEstimatedHours: (json['total_estimated_hours'] as num?)?.toDouble(),
      tasks: (json['tasks'] as List<dynamic>?)
          ?.map((e) => TaskModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      source: json['source'] as String?,
      sourceMetadata: json['source_metadata'] as Map<String, dynamic>?,
      planStage: $enumDecodeNullable(_$PlanStageEnumMap, json['plan_stage']) ??
          PlanStage.sprint,
      priority: $enumDecodeNullable(_$PlanPriorityEnumMap, json['priority']) ??
          PlanPriority.normal,
      isPrimary: json['is_primary'] as bool? ?? false,
    );

Map<String, dynamic> _$PlanModelToJson(PlanModel instance) => <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'name': instance.name,
      'type': _$PlanTypeEnumMap[instance.type]!,
      'description': instance.description,
      'target_date': instance.targetDate?.toIso8601String(),
      'subject': instance.subject,
      'daily_available_minutes': instance.dailyAvailableMinutes,
      'total_estimated_hours': instance.totalEstimatedHours,
      'mastery_level': instance.masteryLevel,
      'progress': instance.progress,
      'is_active': instance.isActive,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'tasks': instance.tasks,
      'source': instance.source,
      'source_metadata': instance.sourceMetadata,
      'plan_stage': _$PlanStageEnumMap[instance.planStage]!,
      'priority': _$PlanPriorityEnumMap[instance.priority]!,
      'is_primary': instance.isPrimary,
    };

const _$PlanTypeEnumMap = {
  PlanType.sprint: 'sprint',
  PlanType.growth: 'growth',
};

const _$PlanStageEnumMap = {
  PlanStage.sprint: 'sprint',
  PlanStage.daily: 'daily',
  PlanStage.review: 'review',
  PlanStage.paused: 'paused',
};

const _$PlanPriorityEnumMap = {
  PlanPriority.critical: 'critical',
  PlanPriority.high: 'high',
  PlanPriority.normal: 'normal',
  PlanPriority.low: 'low',
};

PlanCreate _$PlanCreateFromJson(Map<String, dynamic> json) => PlanCreate(
      name: json['name'] as String,
      type: $enumDecode(_$PlanTypeEnumMap, json['type']),
      dailyAvailableMinutes: (json['daily_available_minutes'] as num).toInt(),
      description: json['description'] as String?,
      targetDate: json['target_date'] == null
          ? null
          : DateTime.parse(json['target_date'] as String),
      subject: json['subject'] as String?,
      totalEstimatedHours: (json['total_estimated_hours'] as num?)?.toDouble(),
      priority: $enumDecodeNullable(_$PlanPriorityEnumMap, json['priority']) ??
          PlanPriority.normal,
      planStage: $enumDecodeNullable(_$PlanStageEnumMap, json['plan_stage']),
    );

Map<String, dynamic> _$PlanCreateToJson(PlanCreate instance) =>
    <String, dynamic>{
      'name': instance.name,
      'type': _$PlanTypeEnumMap[instance.type]!,
      'description': instance.description,
      'target_date': instance.targetDate?.toIso8601String(),
      'subject': instance.subject,
      'daily_available_minutes': instance.dailyAvailableMinutes,
      'total_estimated_hours': instance.totalEstimatedHours,
      'priority': _$PlanPriorityEnumMap[instance.priority]!,
      'plan_stage': _$PlanStageEnumMap[instance.planStage],
    };

PlanUpdate _$PlanUpdateFromJson(Map<String, dynamic> json) => PlanUpdate(
      name: json['name'] as String?,
      description: json['description'] as String?,
      targetDate: json['target_date'] == null
          ? null
          : DateTime.parse(json['target_date'] as String),
      dailyAvailableMinutes: (json['daily_available_minutes'] as num?)?.toInt(),
      totalEstimatedHours: (json['total_estimated_hours'] as num?)?.toDouble(),
      isActive: json['is_active'] as bool?,
      priority: $enumDecodeNullable(_$PlanPriorityEnumMap, json['priority']),
      planStage: $enumDecodeNullable(_$PlanStageEnumMap, json['plan_stage']),
    );

Map<String, dynamic> _$PlanUpdateToJson(PlanUpdate instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'target_date': instance.targetDate?.toIso8601String(),
      'daily_available_minutes': instance.dailyAvailableMinutes,
      'total_estimated_hours': instance.totalEstimatedHours,
      'is_active': instance.isActive,
      'priority': _$PlanPriorityEnumMap[instance.priority],
      'plan_stage': _$PlanStageEnumMap[instance.planStage],
    };

PlanProgress _$PlanProgressFromJson(Map<String, dynamic> json) => PlanProgress(
      planId: json['plan_id'] as String,
      progress: (json['progress'] as num).toDouble(),
      completedTasks: (json['completed_tasks'] as num).toInt(),
      totalTasks: (json['total_tasks'] as num).toInt(),
      totalMinutesSpent: (json['total_minutes_spent'] as num?)?.toInt() ?? 0,
      estimatedRemainingHours:
          (json['estimated_remaining_hours'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$PlanProgressToJson(PlanProgress instance) =>
    <String, dynamic>{
      'plan_id': instance.planId,
      'progress': instance.progress,
      'completed_tasks': instance.completedTasks,
      'total_tasks': instance.totalTasks,
      'total_minutes_spent': instance.totalMinutesSpent,
      'estimated_remaining_hours': instance.estimatedRemainingHours,
    };
