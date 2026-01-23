// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capsule_generation_job_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CapsuleGenerationJobModel _$CapsuleGenerationJobModelFromJson(
        Map<String, dynamic> json) =>
    CapsuleGenerationJobModel(
      id: json['id'] as String,
      status: json['status'] as String,
      generationType: json['generation_type'] as String,
      depthPreference: (json['depth_preference'] as num).toDouble(),
      curiosityPreference: (json['curiosity_preference'] as num).toDouble(),
      requestedCount: (json['requested_count'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      actualCount: (json['actual_count'] as num?)?.toInt(),
      capsuleIds: (json['capsule_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      progress: (json['progress'] as num?)?.toDouble() ?? 0.0,
      errorMessage: json['error_message'] as String?,
      durationMs: (json['duration_ms'] as num?)?.toInt(),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
    );

Map<String, dynamic> _$CapsuleGenerationJobModelToJson(
        CapsuleGenerationJobModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'status': instance.status,
      'generation_type': instance.generationType,
      'depth_preference': instance.depthPreference,
      'curiosity_preference': instance.curiosityPreference,
      'requested_count': instance.requestedCount,
      'actual_count': instance.actualCount,
      'capsule_ids': instance.capsuleIds,
      'progress': instance.progress,
      'error_message': instance.errorMessage,
      'duration_ms': instance.durationMs,
      'created_at': instance.createdAt.toIso8601String(),
      'completed_at': instance.completedAt?.toIso8601String(),
    };
