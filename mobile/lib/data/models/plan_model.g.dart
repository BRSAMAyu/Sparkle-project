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
    };

const _$PlanTypeEnumMap = {
  PlanType.sprint: 'sprint',
  PlanType.growth: 'growth',
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
    );

Map<String, dynamic> _$PlanCreateToJson(PlanCreate instance) =>
    <String, dynamic>{
      'name': instance.name,
      'type': _$PlanTypeEnumMap[instance.type]!,
      'description': instance.description,
      'target_date': instance.targetDate?.toIso8601String(),
      'subject': instance.subject,
      'daily_available_minutes': instance.dailyAvailableMinutes,
    };

PlanUpdate _$PlanUpdateFromJson(Map<String, dynamic> json) => PlanUpdate(
      name: json['name'] as String?,
      description: json['description'] as String?,
      dailyAvailableMinutes: (json['daily_available_minutes'] as num?)?.toInt(),
      isActive: json['is_active'] as bool?,
    );

Map<String, dynamic> _$PlanUpdateToJson(PlanUpdate instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'daily_available_minutes': instance.dailyAvailableMinutes,
      'is_active': instance.isActive,
    };

PlanProgress _$PlanProgressFromJson(Map<String, dynamic> json) => PlanProgress(
      planId: json['plan_id'] as String,
      progress: (json['progress'] as num).toDouble(),
      completedTasks: (json['completed_tasks'] as num).toInt(),
      totalTasks: (json['total_tasks'] as num).toInt(),
    );

Map<String, dynamic> _$PlanProgressToJson(PlanProgress instance) =>
    <String, dynamic>{
      'plan_id': instance.planId,
      'progress': instance.progress,
      'completed_tasks': instance.completedTasks,
      'total_tasks': instance.totalTasks,
    };
