import 'package:hive/hive.dart';
import 'package:json_annotation/json_annotation.dart';

part 'user_brief.g.dart';

@HiveType(typeId: 10)
enum UserStatus {
  @JsonValue('online')
  @HiveField(0)
  online,
  @JsonValue('offline')
  @HiveField(1)
  offline,
  @JsonValue('invisible')
  @HiveField(2)
  invisible,
}

/// 用户简要信息
@JsonSerializable()
@HiveType(typeId: 12)
class UserBrief {
  UserBrief({
    required this.id,
    required this.username,
    this.nickname,
    this.avatarUrl,
    this.flameLevel = 1,
    this.flameBrightness = 0.5,
    this.status = UserStatus.offline,
  });

  factory UserBrief.fromJson(Map<String, dynamic> json) =>
      _$UserBriefFromJson(json);
  @HiveField(0)
  final String id;
  @HiveField(1)
  final String username;
  @HiveField(2)
  final String? nickname;
  @JsonKey(name: 'avatar_url')
  @HiveField(3)
  final String? avatarUrl;
  @JsonKey(name: 'flame_level')
  @HiveField(4)
  final int flameLevel;
  @JsonKey(name: 'flame_brightness')
  @HiveField(5)
  final double flameBrightness;
  @HiveField(6)
  final UserStatus status;
  Map<String, dynamic> toJson() => _$UserBriefToJson(this);

  String get displayName => nickname ?? username;
}
