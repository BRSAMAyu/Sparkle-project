// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cognitive_fragment_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CognitiveFragmentModel _$CognitiveFragmentModelFromJson(
        Map<String, dynamic> json) =>
    CognitiveFragmentModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      sourceType: json['source_type'] as String,
      content: json['content'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      taskId: json['task_id'] as String?,
      sentiment: json['sentiment'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
    );

Map<String, dynamic> _$CognitiveFragmentModelToJson(
        CognitiveFragmentModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'task_id': instance.taskId,
      'source_type': instance.sourceType,
      'content': instance.content,
      'sentiment': instance.sentiment,
      'tags': instance.tags,
      'created_at': instance.createdAt.toIso8601String(),
    };

CognitiveFragmentCreate _$CognitiveFragmentCreateFromJson(
        Map<String, dynamic> json) =>
    CognitiveFragmentCreate(
      content: json['content'] as String,
      sourceType: json['source_type'] as String,
      id: json['id'] as String?,
      taskId: json['task_id'] as String?,
    );

Map<String, dynamic> _$CognitiveFragmentCreateToJson(
        CognitiveFragmentCreate instance) =>
    <String, dynamic>{
      'id': instance.id,
      'content': instance.content,
      'source_type': instance.sourceType,
      'task_id': instance.taskId,
    };
