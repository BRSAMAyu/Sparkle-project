// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

TaskModel _$TaskModelFromJson(Map<String, dynamic> json) => TaskModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      title: json['title'] as String,
      type: $enumDecode(_$TaskTypeEnumMap, json['type']),
      tags: (json['tags'] as List<dynamic>).map((e) => e as String).toList(),
      estimatedMinutes: (json['estimated_minutes'] as num).toInt(),
      difficulty: (json['difficulty'] as num).toInt(),
      energyCost: (json['energy_cost'] as num).toInt(),
      status: $enumDecode(_$TaskStatusEnumMap, json['status']),
      priority: (json['priority'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      planId: json['plan_id'] as String?,
      guideContent: json['guide_content'] as String?,
      startedAt: json['started_at'] == null
          ? null
          : DateTime.parse(json['started_at'] as String),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
      actualMinutes: (json['actual_minutes'] as num?)?.toInt(),
      userNote: json['user_note'] as String?,
      dueDate: json['due_date'] == null
          ? null
          : DateTime.parse(json['due_date'] as String),
      knowledgeNodeId: json['knowledge_node_id'] as String?,
    );

Map<String, dynamic> _$TaskModelToJson(TaskModel instance) => <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'plan_id': instance.planId,
      'title': instance.title,
      'type': _$TaskTypeEnumMap[instance.type]!,
      'tags': instance.tags,
      'estimated_minutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
      'energy_cost': instance.energyCost,
      'guide_content': instance.guideContent,
      'status': _$TaskStatusEnumMap[instance.status]!,
      'started_at': instance.startedAt?.toIso8601String(),
      'completed_at': instance.completedAt?.toIso8601String(),
      'actual_minutes': instance.actualMinutes,
      'user_note': instance.userNote,
      'priority': instance.priority,
      'due_date': instance.dueDate?.toIso8601String(),
      'knowledge_node_id': instance.knowledgeNodeId,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$TaskTypeEnumMap = {
  TaskType.learning: 'learning',
  TaskType.training: 'training',
  TaskType.errorFix: 'errorFix',
  TaskType.reflection: 'reflection',
  TaskType.social: 'social',
  TaskType.planning: 'planning',
};

const _$TaskStatusEnumMap = {
  TaskStatus.pending: 'pending',
  TaskStatus.inProgress: 'inProgress',
  TaskStatus.completed: 'completed',
  TaskStatus.abandoned: 'abandoned',
};

TaskCreate _$TaskCreateFromJson(Map<String, dynamic> json) => TaskCreate(
      title: json['title'] as String,
      type: $enumDecode(_$TaskTypeEnumMap, json['type']),
      estimatedMinutes: (json['estimatedMinutes'] as num).toInt(),
      difficulty: (json['difficulty'] as num).toInt(),
      energyCost: (json['energy_cost'] as num?)?.toInt() ?? 1,
      planId: json['plan_id'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      dueDate: json['due_date'] == null
          ? null
          : DateTime.parse(json['due_date'] as String),
      knowledgeNodeId: json['knowledge_node_id'] as String?,
      guideContent: json['guide_content'] as String?,
    );

Map<String, dynamic> _$TaskCreateToJson(TaskCreate instance) =>
    <String, dynamic>{
      'title': instance.title,
      'type': _$TaskTypeEnumMap[instance.type]!,
      'estimatedMinutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
      'energy_cost': instance.energyCost,
      'plan_id': instance.planId,
      'tags': instance.tags,
      'due_date': instance.dueDate?.toIso8601String(),
      'knowledge_node_id': instance.knowledgeNodeId,
      'guide_content': instance.guideContent,
    };

TaskUpdate _$TaskUpdateFromJson(Map<String, dynamic> json) => TaskUpdate(
      title: json['title'] as String?,
      type: $enumDecodeNullable(_$TaskTypeEnumMap, json['type']),
      estimatedMinutes: (json['estimatedMinutes'] as num?)?.toInt(),
      difficulty: (json['difficulty'] as num?)?.toInt(),
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      status: $enumDecodeNullable(_$TaskStatusEnumMap, json['status']),
      dueDate: json['due_date'] == null
          ? null
          : DateTime.parse(json['due_date'] as String),
    );

Map<String, dynamic> _$TaskUpdateToJson(TaskUpdate instance) =>
    <String, dynamic>{
      'title': instance.title,
      'type': _$TaskTypeEnumMap[instance.type],
      'estimatedMinutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
      'tags': instance.tags,
      'status': _$TaskStatusEnumMap[instance.status],
      'due_date': instance.dueDate?.toIso8601String(),
    };

TaskComplete _$TaskCompleteFromJson(Map<String, dynamic> json) => TaskComplete(
      actualMinutes: (json['actual_minutes'] as num).toInt(),
      userNote: json['user_note'] as String?,
    );

Map<String, dynamic> _$TaskCompleteToJson(TaskComplete instance) =>
    <String, dynamic>{
      'actual_minutes': instance.actualMinutes,
      'user_note': instance.userNote,
    };

SuggestedNode _$SuggestedNodeFromJson(Map<String, dynamic> json) =>
    SuggestedNode(
      name: json['name'] as String,
      reason: json['reason'] as String,
      isNew: json['is_new'] as bool,
      id: json['id'] as String?,
    );

Map<String, dynamic> _$SuggestedNodeToJson(SuggestedNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'reason': instance.reason,
      'is_new': instance.isNew,
    };

TaskSuggestionResponse _$TaskSuggestionResponseFromJson(
        Map<String, dynamic> json) =>
    TaskSuggestionResponse(
      intent: json['intent'] as String,
      suggestedNodes: (json['suggested_nodes'] as List<dynamic>)
          .map((e) => SuggestedNode.fromJson(e as Map<String, dynamic>))
          .toList(),
      suggestedTags: (json['suggested_tags'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt(),
      difficulty: (json['difficulty'] as num?)?.toInt(),
    );

Map<String, dynamic> _$TaskSuggestionResponseToJson(
        TaskSuggestionResponse instance) =>
    <String, dynamic>{
      'intent': instance.intent,
      'suggested_nodes': instance.suggestedNodes,
      'suggested_tags': instance.suggestedTags,
      'estimated_minutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
    };
