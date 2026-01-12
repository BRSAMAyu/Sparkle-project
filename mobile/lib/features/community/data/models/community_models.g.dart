// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'community_models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$PostUserImpl _$$PostUserImplFromJson(Map<String, dynamic> json) =>
    _$PostUserImpl(
      id: json['id'] as String,
      username: json['username'] as String,
      avatarUrl: json['avatar_url'] as String?,
    );

Map<String, dynamic> _$$PostUserImplToJson(_$PostUserImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'avatar_url': instance.avatarUrl,
    };

_$PostImpl _$$PostImplFromJson(Map<String, dynamic> json) => _$PostImpl(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      content: json['content'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      user: PostUser.fromJson(json['user'] as Map<String, dynamic>),
      imageUrls: (json['image_urls'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      topic: json['topic'] as String?,
      likeCount: (json['like_count'] as num?)?.toInt() ?? 0,
      isOptimistic: json['isOptimistic'] as bool? ?? false,
    );

Map<String, dynamic> _$$PostImplToJson(_$PostImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'content': instance.content,
      'created_at': instance.createdAt.toIso8601String(),
      'user': instance.user,
      'image_urls': instance.imageUrls,
      'topic': instance.topic,
      'like_count': instance.likeCount,
      'isOptimistic': instance.isOptimistic,
    };

_$CreatePostRequestImpl _$$CreatePostRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$CreatePostRequestImpl(
      userId: json['user_id'] as String,
      content: json['content'] as String,
      imageUrls: (json['image_urls'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      topic: json['topic'] as String?,
    );

Map<String, dynamic> _$$CreatePostRequestImplToJson(
        _$CreatePostRequestImpl instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'content': instance.content,
      'image_urls': instance.imageUrls,
      'topic': instance.topic,
    };
