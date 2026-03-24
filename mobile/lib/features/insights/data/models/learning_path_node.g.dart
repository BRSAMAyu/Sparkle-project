// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'learning_path_node.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LearningPathNode _$LearningPathNodeFromJson(Map<String, dynamic> json) =>
    LearningPathNode(
      id: json['id'] as String,
      name: json['name'] as String,
      status: json['status'] as String,
      isTarget: json['is_target'] as bool? ?? false,
      isOptional: json['is_optional'] as bool? ?? false,
      relationType: json['relation_type'] as String?,
      sourceType: json['source_type'] as String?,
    );

Map<String, dynamic> _$LearningPathNodeToJson(LearningPathNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'status': instance.status,
      'is_target': instance.isTarget,
      'is_optional': instance.isOptional,
      'relation_type': instance.relationType,
      'source_type': instance.sourceType,
    };
