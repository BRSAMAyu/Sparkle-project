// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'learning_path_progress_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LearningPathProgressModel _$LearningPathProgressModelFromJson(
        Map<String, dynamic> json) =>
    LearningPathProgressModel(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) =>
              LearningPathNodeProgress.fromJson(e as Map<String, dynamic>))
          .toList(),
      overallProgress: (json['overall_progress'] as num).toDouble(),
      targetNode: json['target_node'] == null
          ? null
          : LearningPathNodeProgress.fromJson(
              json['target_node'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$LearningPathProgressModelToJson(
        LearningPathProgressModel instance) =>
    <String, dynamic>{
      'target_node': instance.targetNode,
      'nodes': instance.nodes,
      'overall_progress': instance.overallProgress,
    };

LearningPathNodeProgress _$LearningPathNodeProgressFromJson(
        Map<String, dynamic> json) =>
    LearningPathNodeProgress(
      id: json['id'] as String,
      name: json['name'] as String,
      status: json['status'] as String,
      mastery: (json['mastery'] as num).toInt(),
      isTarget: json['is_target'] as bool? ?? false,
    );

Map<String, dynamic> _$LearningPathNodeProgressToJson(
        LearningPathNodeProgress instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'status': instance.status,
      'mastery': instance.mastery,
      'is_target': instance.isTarget,
    };
