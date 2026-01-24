// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_brief.dart';

// **************************************************************************
// TypeAdapterGenerator
// **************************************************************************

class UserBriefAdapter extends TypeAdapter<UserBrief> {
  @override
  final int typeId = 12;

  @override
  UserBrief read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return UserBrief(
      id: fields[0] as String,
      username: fields[1] as String,
      nickname: fields[2] as String?,
      avatarUrl: fields[3] as String?,
      flameLevel: fields[4] as int,
      flameBrightness: fields[5] as double,
      status: fields[6] as UserStatus,
    );
  }

  @override
  void write(BinaryWriter writer, UserBrief obj) {
    writer
      ..writeByte(7)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.username)
      ..writeByte(2)
      ..write(obj.nickname)
      ..writeByte(3)
      ..write(obj.avatarUrl)
      ..writeByte(4)
      ..write(obj.flameLevel)
      ..writeByte(5)
      ..write(obj.flameBrightness)
      ..writeByte(6)
      ..write(obj.status);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is UserBriefAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}

class UserStatusAdapter extends TypeAdapter<UserStatus> {
  @override
  final int typeId = 10;

  @override
  UserStatus read(BinaryReader reader) {
    switch (reader.readByte()) {
      case 0:
        return UserStatus.online;
      case 1:
        return UserStatus.offline;
      case 2:
        return UserStatus.invisible;
      default:
        return UserStatus.online;
    }
  }

  @override
  void write(BinaryWriter writer, UserStatus obj) {
    switch (obj) {
      case UserStatus.online:
        writer.writeByte(0);
        break;
      case UserStatus.offline:
        writer.writeByte(1);
        break;
      case UserStatus.invisible:
        writer.writeByte(2);
        break;
    }
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is UserStatusAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserBrief _$UserBriefFromJson(Map<String, dynamic> json) => UserBrief(
      id: json['id'] as String,
      username: json['username'] as String,
      nickname: json['nickname'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      flameLevel: (json['flame_level'] as num?)?.toInt() ?? 1,
      flameBrightness: (json['flame_brightness'] as num?)?.toDouble() ?? 0.5,
      status: $enumDecodeNullable(_$UserStatusEnumMap, json['status']) ??
          UserStatus.offline,
    );

Map<String, dynamic> _$UserBriefToJson(UserBrief instance) => <String, dynamic>{
      'id': instance.id,
      'username': instance.username,
      'nickname': instance.nickname,
      'avatar_url': instance.avatarUrl,
      'flame_level': instance.flameLevel,
      'flame_brightness': instance.flameBrightness,
      'status': _$UserStatusEnumMap[instance.status]!,
    };

const _$UserStatusEnumMap = {
  UserStatus.online: 'online',
  UserStatus.offline: 'offline',
  UserStatus.invisible: 'invisible',
};
