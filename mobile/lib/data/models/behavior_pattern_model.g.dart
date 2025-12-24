// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'behavior_pattern_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

BehaviorPatternModel _$BehaviorPatternModelFromJson(
        Map<String, dynamic> json) =>
    BehaviorPatternModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      patternName: json['pattern_name'] as String,
      patternType: json['pattern_type'] as String,
      isArchived: json['is_archived'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      solutionText: json['solution_text'] as String?,
      evidenceIds: (json['evidence_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$BehaviorPatternModelToJson(
        BehaviorPatternModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'pattern_name': instance.patternName,
      'pattern_type': instance.patternType,
      'description': instance.description,
      'solution_text': instance.solutionText,
      'evidence_ids': instance.evidenceIds,
      'is_archived': instance.isArchived,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };
