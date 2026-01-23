// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'curiosity_capsule_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CuriosityCapsuleModel _$CuriosityCapsuleModelFromJson(
        Map<String, dynamic> json) =>
    CuriosityCapsuleModel(
      id: json['id'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      isRead: json['is_read'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      relatedSubject: json['related_subject'] as String?,
      depthLevel: json['depth_level'] as String?,
      generationMethod: json['generation_method'] as String?,
      sourceContext: json['source_context'] as Map<String, dynamic>?,
      qualityScore: (json['quality_score'] as num?)?.toDouble(),
      feedbackCount: (json['feedback_count'] as num?)?.toInt() ?? 0,
      shareCount: (json['share_count'] as num?)?.toInt() ?? 0,
      isFavorite: json['is_favorite'] as bool? ?? false,
    );

Map<String, dynamic> _$CuriosityCapsuleModelToJson(
        CuriosityCapsuleModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'content': instance.content,
      'is_read': instance.isRead,
      'created_at': instance.createdAt.toIso8601String(),
      'related_subject': instance.relatedSubject,
      'depth_level': instance.depthLevel,
      'generation_method': instance.generationMethod,
      'source_context': instance.sourceContext,
      'quality_score': instance.qualityScore,
      'feedback_count': instance.feedbackCount,
      'share_count': instance.shareCount,
      'is_favorite': instance.isFavorite,
    };
