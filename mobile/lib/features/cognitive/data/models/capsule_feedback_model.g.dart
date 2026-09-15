// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capsule_feedback_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CapsuleFeedbackModel _$CapsuleFeedbackModelFromJson(
        Map<String, dynamic> json) =>
    CapsuleFeedbackModel(
      id: json['id'] as String,
      capsuleId: json['capsule_id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      rating: (json['rating'] as num?)?.toInt(),
      helpful: json['helpful'] as bool?,
      category: json['category'] as String?,
      comment: json['comment'] as String?,
    );

Map<String, dynamic> _$CapsuleFeedbackModelToJson(
        CapsuleFeedbackModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'capsule_id': instance.capsuleId,
      'rating': instance.rating,
      'helpful': instance.helpful,
      'category': instance.category,
      'comment': instance.comment,
      'created_at': instance.createdAt.toIso8601String(),
    };
