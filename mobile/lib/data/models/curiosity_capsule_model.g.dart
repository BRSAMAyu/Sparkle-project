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
    };
