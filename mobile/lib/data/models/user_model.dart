import 'package:json_annotation/json_annotation.dart';

part 'user_model.g.dart';

/// 用户数据模型
@JsonSerializable()
class UserModel {
  final String id;
  final String username;
  final String email;
  final String? nickname;
  final String? avatarUrl;
  @JsonKey(name: 'flame_level')
  final int flameLevel;
  @JsonKey(name: 'flame_brightness')
  final double flameBrightness;
  @JsonKey(name: 'depth_preference')
  final double depthPreference;
  @JsonKey(name: 'curiosity_preference')
  final double curiosityPreference;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'schedule_preferences')
  final Map<String, dynamic>? schedulePreferences;
  @JsonKey(name: 'push_preference')
  final PushPreferences? pushPreferences;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.flameLevel, required this.flameBrightness, required this.depthPreference, required this.curiosityPreference, required this.isActive, required this.createdAt, required this.updatedAt, this.nickname,
    this.avatarUrl,
    this.schedulePreferences,
    this.pushPreferences,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) => _$UserModelFromJson(json);
  Map<String, dynamic> toJson() => _$UserModelToJson(this);
}

/// 推送偏好
@JsonSerializable()
class PushPreferences {
  @JsonKey(name: 'active_slots')
  final List<Map<String, String>>? activeSlots;
  @JsonKey(name: 'timezone')
  final String timezone;
  @JsonKey(name: 'enable_curiosity')
  final bool enableCuriosity;
  @JsonKey(name: 'persona_type')
  final String personaType;
  @JsonKey(name: 'daily_cap')
  final int dailyCap;

  PushPreferences({
    this.activeSlots,
    this.timezone = 'Asia/Shanghai',
    this.enableCuriosity = true,
    this.personaType = 'coach',
    this.dailyCap = 5,
  });

  factory PushPreferences.fromJson(Map<String, dynamic> json) => _$PushPreferencesFromJson(json);
  Map<String, dynamic> toJson() => _$PushPreferencesToJson(this);
}

/// 用户偏好
@JsonSerializable()
class UserPreferences {
  @JsonKey(name: 'depth_preference')
  final double depthPreference;
  @JsonKey(name: 'curiosity_preference')
  final double curiosityPreference;

  UserPreferences({
    required this.depthPreference,
    required this.curiosityPreference,
  });

  factory UserPreferences.fromJson(Map<String, dynamic> json) => _$UserPreferencesFromJson(json);
  Map<String, dynamic> toJson() => _$UserPreferencesToJson(this);
}

/// 火苗状态
@JsonSerializable()
class FlameStatus {
  @JsonKey(name: 'level')
  final int level;
  @JsonKey(name: 'brightness')
  final double brightness;

  FlameStatus({
    required this.level,
    required this.brightness,
  });

  factory FlameStatus.fromJson(Map<String, dynamic> json) => _$FlameStatusFromJson(json);
  Map<String, dynamic> toJson() => _$FlameStatusToJson(this);
}