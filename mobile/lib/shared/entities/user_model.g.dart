// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserModel _$UserModelFromJson(Map<String, dynamic> json) => UserModel(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      flameLevel: (json['flame_level'] as num).toInt(),
      flameBrightness: (json['flame_brightness'] as num).toDouble(),
      depthPreference: (json['depth_preference'] as num).toDouble(),
      curiosityPreference: (json['curiosity_preference'] as num).toDouble(),
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      nickname: json['nickname'] as String?,
      avatarUrl: json['avatarUrl'] as String?,
      avatarStatus:
          $enumDecodeNullable(_$AvatarStatusEnumMap, json['avatar_status']) ??
              AvatarStatus.approved,
      pendingAvatarUrl: json['pending_avatar_url'] as String?,
      status: $enumDecodeNullable(_$UserStatusEnumMap, json['status']) ??
          UserStatus.offline,
      schedulePreferences:
          json['schedule_preferences'] as Map<String, dynamic>?,
      pushPreferences: json['push_preference'] == null
          ? null
          : PushPreferences.fromJson(
              json['push_preference'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$UserModelToJson(UserModel instance) => <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'email': instance.email,
      'nickname': instance.nickname,
      'avatarUrl': instance.avatarUrl,
      'avatar_status': _$AvatarStatusEnumMap[instance.avatarStatus]!,
      'pending_avatar_url': instance.pendingAvatarUrl,
      'flame_level': instance.flameLevel,
      'flame_brightness': instance.flameBrightness,
      'depth_preference': instance.depthPreference,
      'curiosity_preference': instance.curiosityPreference,
      'is_active': instance.isActive,
      'status': _$UserStatusEnumMap[instance.status]!,
      'schedule_preferences': instance.schedulePreferences,
      'push_preference': instance.pushPreferences,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$AvatarStatusEnumMap = {
  AvatarStatus.approved: 'approved',
  AvatarStatus.pending: 'pending',
  AvatarStatus.rejected: 'rejected',
};

const _$UserStatusEnumMap = {
  UserStatus.online: 'online',
  UserStatus.offline: 'offline',
  UserStatus.invisible: 'invisible',
};

PushPreferences _$PushPreferencesFromJson(Map<String, dynamic> json) =>
    PushPreferences(
      activeSlots: (json['active_slots'] as List<dynamic>?)
          ?.map((e) => Map<String, String>.from(e as Map))
          .toList(),
      timezone: json['timezone'] as String? ?? 'Asia/Shanghai',
      enableCuriosity: json['enable_curiosity'] as bool? ?? true,
      personaType: json['persona_type'] as String? ?? 'coach',
      dailyCap: (json['daily_cap'] as num?)?.toInt() ?? 5,
    );

Map<String, dynamic> _$PushPreferencesToJson(PushPreferences instance) =>
    <String, dynamic>{
      'active_slots': instance.activeSlots,
      'timezone': instance.timezone,
      'enable_curiosity': instance.enableCuriosity,
      'persona_type': instance.personaType,
      'daily_cap': instance.dailyCap,
    };

UserPreferences _$UserPreferencesFromJson(Map<String, dynamic> json) =>
    UserPreferences(
      depthPreference: (json['depth_preference'] as num).toDouble(),
      curiosityPreference: (json['curiosity_preference'] as num).toDouble(),
    );

Map<String, dynamic> _$UserPreferencesToJson(UserPreferences instance) =>
    <String, dynamic>{
      'depth_preference': instance.depthPreference,
      'curiosity_preference': instance.curiosityPreference,
    };

FlameStatus _$FlameStatusFromJson(Map<String, dynamic> json) => FlameStatus(
      level: (json['level'] as num).toInt(),
      brightness: (json['brightness'] as num).toDouble(),
    );

Map<String, dynamic> _$FlameStatusToJson(FlameStatus instance) =>
    <String, dynamic>{
      'level': instance.level,
      'brightness': instance.brightness,
    };
