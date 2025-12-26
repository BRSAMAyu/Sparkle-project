// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'community_model.dart';

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

class MessageInfoAdapter extends TypeAdapter<MessageInfo> {
  @override
  final int typeId = 13;

  @override
  MessageInfo read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return MessageInfo(
      id: fields[0] as String,
      messageType: fields[2] as MessageType,
      createdAt: fields[6] as DateTime,
      updatedAt: fields[7] as DateTime,
      sender: fields[1] as UserBrief?,
      content: fields[3] as String?,
      contentData: (fields[4] as Map?)?.cast<String, dynamic>(),
      replyToId: fields[5] as String?,
      isRevoked: fields[8] as bool,
    );
  }

  @override
  void write(BinaryWriter writer, MessageInfo obj) {
    writer
      ..writeByte(9)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.sender)
      ..writeByte(2)
      ..write(obj.messageType)
      ..writeByte(3)
      ..write(obj.content)
      ..writeByte(4)
      ..write(obj.contentData)
      ..writeByte(5)
      ..write(obj.replyToId)
      ..writeByte(6)
      ..write(obj.createdAt)
      ..writeByte(7)
      ..write(obj.updatedAt)
      ..writeByte(8)
      ..write(obj.isRevoked);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MessageInfoAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}

class PrivateMessageInfoAdapter extends TypeAdapter<PrivateMessageInfo> {
  @override
  final int typeId = 14;

  @override
  PrivateMessageInfo read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return PrivateMessageInfo(
      id: fields[0] as String,
      sender: fields[1] as UserBrief,
      receiver: fields[2] as UserBrief,
      messageType: fields[3] as MessageType,
      isRead: fields[7] as bool,
      createdAt: fields[9] as DateTime,
      updatedAt: fields[10] as DateTime,
      content: fields[4] as String?,
      contentData: (fields[5] as Map?)?.cast<String, dynamic>(),
      replyToId: fields[6] as String?,
      readAt: fields[8] as DateTime?,
      isRevoked: fields[11] as bool,
    );
  }

  @override
  void write(BinaryWriter writer, PrivateMessageInfo obj) {
    writer
      ..writeByte(12)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.sender)
      ..writeByte(2)
      ..write(obj.receiver)
      ..writeByte(3)
      ..write(obj.messageType)
      ..writeByte(4)
      ..write(obj.content)
      ..writeByte(5)
      ..write(obj.contentData)
      ..writeByte(6)
      ..write(obj.replyToId)
      ..writeByte(7)
      ..write(obj.isRead)
      ..writeByte(8)
      ..write(obj.readAt)
      ..writeByte(9)
      ..write(obj.createdAt)
      ..writeByte(10)
      ..write(obj.updatedAt)
      ..writeByte(11)
      ..write(obj.isRevoked);
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PrivateMessageInfoAdapter &&
          runtimeType == other.runtimeType &&
          typeId == other.typeId;
}

class MessageTypeAdapter extends TypeAdapter<MessageType> {
  @override
  final int typeId = 11;

  @override
  MessageType read(BinaryReader reader) {
    switch (reader.readByte()) {
      case 0:
        return MessageType.text;
      case 1:
        return MessageType.taskShare;
      case 2:
        return MessageType.progress;
      case 3:
        return MessageType.achievement;
      case 4:
        return MessageType.checkin;
      case 5:
        return MessageType.system;
      default:
        return MessageType.text;
    }
  }

  @override
  void write(BinaryWriter writer, MessageType obj) {
    switch (obj) {
      case MessageType.text:
        writer.writeByte(0);
        break;
      case MessageType.taskShare:
        writer.writeByte(1);
        break;
      case MessageType.progress:
        writer.writeByte(2);
        break;
      case MessageType.achievement:
        writer.writeByte(3);
        break;
      case MessageType.checkin:
        writer.writeByte(4);
        break;
      case MessageType.system:
        writer.writeByte(5);
        break;
    }
  }

  @override
  int get hashCode => typeId.hashCode;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MessageTypeAdapter &&
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

FriendshipInfo _$FriendshipInfoFromJson(Map<String, dynamic> json) =>
    FriendshipInfo(
      id: json['id'] as String,
      friend: UserBrief.fromJson(json['friend'] as Map<String, dynamic>),
      status: $enumDecode(_$FriendshipStatusEnumMap, json['status']),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      matchReason: json['match_reason'] as Map<String, dynamic>?,
      initiatedByMe: json['initiated_by_me'] as bool? ?? false,
    );

Map<String, dynamic> _$FriendshipInfoToJson(FriendshipInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'friend': instance.friend,
      'status': _$FriendshipStatusEnumMap[instance.status]!,
      'match_reason': instance.matchReason,
      'initiated_by_me': instance.initiatedByMe,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$FriendshipStatusEnumMap = {
  FriendshipStatus.pending: 'pending',
  FriendshipStatus.accepted: 'accepted',
  FriendshipStatus.blocked: 'blocked',
};

FriendRecommendation _$FriendRecommendationFromJson(
        Map<String, dynamic> json) =>
    FriendRecommendation(
      user: UserBrief.fromJson(json['user'] as Map<String, dynamic>),
      matchScore: (json['match_score'] as num).toDouble(),
      matchReasons: (json['match_reasons'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$FriendRecommendationToJson(
        FriendRecommendation instance) =>
    <String, dynamic>{
      'user': instance.user,
      'match_score': instance.matchScore,
      'match_reasons': instance.matchReasons,
    };

GroupInfo _$GroupInfoFromJson(Map<String, dynamic> json) => GroupInfo(
      id: json['id'] as String,
      name: json['name'] as String,
      type: $enumDecode(_$GroupTypeEnumMap, json['type']),
      focusTags: (json['focus_tags'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      memberCount: (json['member_count'] as num).toInt(),
      totalFlamePower: (json['total_flame_power'] as num).toInt(),
      todayCheckinCount: (json['today_checkin_count'] as num).toInt(),
      totalTasksCompleted: (json['total_tasks_completed'] as num).toInt(),
      maxMembers: (json['max_members'] as num).toInt(),
      isPublic: json['is_public'] as bool,
      joinRequiresApproval: json['join_requires_approval'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      deadline: json['deadline'] == null
          ? null
          : DateTime.parse(json['deadline'] as String),
      sprintGoal: json['sprint_goal'] as String?,
      daysRemaining: (json['days_remaining'] as num?)?.toInt(),
      myRole: $enumDecodeNullable(_$GroupRoleEnumMap, json['my_role']),
    );

Map<String, dynamic> _$GroupInfoToJson(GroupInfo instance) => <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'description': instance.description,
      'avatar_url': instance.avatarUrl,
      'type': _$GroupTypeEnumMap[instance.type]!,
      'focus_tags': instance.focusTags,
      'deadline': instance.deadline?.toIso8601String(),
      'sprint_goal': instance.sprintGoal,
      'days_remaining': instance.daysRemaining,
      'member_count': instance.memberCount,
      'total_flame_power': instance.totalFlamePower,
      'today_checkin_count': instance.todayCheckinCount,
      'total_tasks_completed': instance.totalTasksCompleted,
      'max_members': instance.maxMembers,
      'is_public': instance.isPublic,
      'join_requires_approval': instance.joinRequiresApproval,
      'my_role': _$GroupRoleEnumMap[instance.myRole],
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$GroupTypeEnumMap = {
  GroupType.squad: 'squad',
  GroupType.sprint: 'sprint',
};

const _$GroupRoleEnumMap = {
  GroupRole.owner: 'owner',
  GroupRole.admin: 'admin',
  GroupRole.member: 'member',
};

GroupListItem _$GroupListItemFromJson(Map<String, dynamic> json) =>
    GroupListItem(
      id: json['id'] as String,
      name: json['name'] as String,
      type: $enumDecode(_$GroupTypeEnumMap, json['type']),
      memberCount: (json['member_count'] as num).toInt(),
      totalFlamePower: (json['total_flame_power'] as num).toInt(),
      focusTags: (json['focus_tags'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      deadline: json['deadline'] == null
          ? null
          : DateTime.parse(json['deadline'] as String),
      daysRemaining: (json['days_remaining'] as num?)?.toInt(),
      myRole: $enumDecodeNullable(_$GroupRoleEnumMap, json['my_role']),
    );

Map<String, dynamic> _$GroupListItemToJson(GroupListItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'type': _$GroupTypeEnumMap[instance.type]!,
      'member_count': instance.memberCount,
      'total_flame_power': instance.totalFlamePower,
      'deadline': instance.deadline?.toIso8601String(),
      'days_remaining': instance.daysRemaining,
      'focus_tags': instance.focusTags,
      'my_role': _$GroupRoleEnumMap[instance.myRole],
    };

GroupCreate _$GroupCreateFromJson(Map<String, dynamic> json) => GroupCreate(
      name: json['name'] as String,
      type: $enumDecode(_$GroupTypeEnumMap, json['type']),
      description: json['description'] as String?,
      focusTags: (json['focus_tags'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      deadline: json['deadline'] == null
          ? null
          : DateTime.parse(json['deadline'] as String),
      sprintGoal: json['sprint_goal'] as String?,
      maxMembers: (json['max_members'] as num?)?.toInt() ?? 50,
      isPublic: json['is_public'] as bool? ?? true,
      joinRequiresApproval: json['join_requires_approval'] as bool? ?? false,
    );

Map<String, dynamic> _$GroupCreateToJson(GroupCreate instance) =>
    <String, dynamic>{
      'name': instance.name,
      'description': instance.description,
      'type': _$GroupTypeEnumMap[instance.type]!,
      'focus_tags': instance.focusTags,
      'deadline': instance.deadline?.toIso8601String(),
      'sprint_goal': instance.sprintGoal,
      'max_members': instance.maxMembers,
      'is_public': instance.isPublic,
      'join_requires_approval': instance.joinRequiresApproval,
    };

GroupMemberInfo _$GroupMemberInfoFromJson(Map<String, dynamic> json) =>
    GroupMemberInfo(
      user: UserBrief.fromJson(json['user'] as Map<String, dynamic>),
      role: $enumDecode(_$GroupRoleEnumMap, json['role']),
      flameContribution: (json['flame_contribution'] as num).toInt(),
      tasksCompleted: (json['tasks_completed'] as num).toInt(),
      checkinStreak: (json['checkin_streak'] as num).toInt(),
      joinedAt: DateTime.parse(json['joined_at'] as String),
      lastActiveAt: DateTime.parse(json['last_active_at'] as String),
    );

Map<String, dynamic> _$GroupMemberInfoToJson(GroupMemberInfo instance) =>
    <String, dynamic>{
      'user': instance.user,
      'role': _$GroupRoleEnumMap[instance.role]!,
      'flame_contribution': instance.flameContribution,
      'tasks_completed': instance.tasksCompleted,
      'checkin_streak': instance.checkinStreak,
      'joined_at': instance.joinedAt.toIso8601String(),
      'last_active_at': instance.lastActiveAt.toIso8601String(),
    };

MessageInfo _$MessageInfoFromJson(Map<String, dynamic> json) => MessageInfo(
      id: json['id'] as String,
      messageType: $enumDecode(_$MessageTypeEnumMap, json['message_type']),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      sender: json['sender'] == null
          ? null
          : UserBrief.fromJson(json['sender'] as Map<String, dynamic>),
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      replyToId: json['reply_to_id'] as String?,
      isRevoked: json['is_revoked'] as bool? ?? false,
    );

Map<String, dynamic> _$MessageInfoToJson(MessageInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'sender': instance.sender,
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'is_revoked': instance.isRevoked,
    };

const _$MessageTypeEnumMap = {
  MessageType.text: 'text',
  MessageType.taskShare: 'task_share',
  MessageType.progress: 'progress',
  MessageType.achievement: 'achievement',
  MessageType.checkin: 'checkin',
  MessageType.system: 'system',
};

PrivateMessageInfo _$PrivateMessageInfoFromJson(Map<String, dynamic> json) =>
    PrivateMessageInfo(
      id: json['id'] as String,
      sender: UserBrief.fromJson(json['sender'] as Map<String, dynamic>),
      receiver: UserBrief.fromJson(json['receiver'] as Map<String, dynamic>),
      messageType: $enumDecode(_$MessageTypeEnumMap, json['message_type']),
      isRead: json['is_read'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      replyToId: json['reply_to_id'] as String?,
      readAt: json['read_at'] == null
          ? null
          : DateTime.parse(json['read_at'] as String),
      isRevoked: json['is_revoked'] as bool? ?? false,
      quotedMessage: json['quoted_message'] == null
          ? null
          : PrivateMessageInfo.fromJson(
              json['quoted_message'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$PrivateMessageInfoToJson(PrivateMessageInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'sender': instance.sender,
      'receiver': instance.receiver,
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'is_read': instance.isRead,
      'read_at': instance.readAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'is_revoked': instance.isRevoked,
      'quoted_message': instance.quotedMessage,
    };

PrivateMessageSend _$PrivateMessageSendFromJson(Map<String, dynamic> json) =>
    PrivateMessageSend(
      targetUserId: json['target_user_id'] as String,
      messageType:
          $enumDecodeNullable(_$MessageTypeEnumMap, json['message_type']) ??
              MessageType.text,
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      replyToId: json['reply_to_id'] as String?,
      nonce: json['nonce'] as String?,
    );

Map<String, dynamic> _$PrivateMessageSendToJson(PrivateMessageSend instance) =>
    <String, dynamic>{
      'target_user_id': instance.targetUserId,
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'nonce': instance.nonce,
    };

MessageSend _$MessageSendFromJson(Map<String, dynamic> json) => MessageSend(
      messageType:
          $enumDecodeNullable(_$MessageTypeEnumMap, json['message_type']) ??
              MessageType.text,
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      replyToId: json['reply_to_id'] as String?,
      nonce: json['nonce'] as String?,
    );

Map<String, dynamic> _$MessageSendToJson(MessageSend instance) =>
    <String, dynamic>{
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'nonce': instance.nonce,
    };

GroupTaskInfo _$GroupTaskInfoFromJson(Map<String, dynamic> json) =>
    GroupTaskInfo(
      id: json['id'] as String,
      title: json['title'] as String,
      tags: (json['tags'] as List<dynamic>).map((e) => e as String).toList(),
      estimatedMinutes: (json['estimated_minutes'] as num).toInt(),
      difficulty: (json['difficulty'] as num).toInt(),
      totalClaims: (json['total_claims'] as num).toInt(),
      totalCompletions: (json['total_completions'] as num).toInt(),
      completionRate: (json['completion_rate'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      description: json['description'] as String?,
      dueDate: json['due_date'] == null
          ? null
          : DateTime.parse(json['due_date'] as String),
      creator: json['creator'] == null
          ? null
          : UserBrief.fromJson(json['creator'] as Map<String, dynamic>),
      isClaimedByMe: json['is_claimed_by_me'] as bool? ?? false,
      myCompletionStatus: json['my_completion_status'] as bool?,
    );

Map<String, dynamic> _$GroupTaskInfoToJson(GroupTaskInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'description': instance.description,
      'tags': instance.tags,
      'estimated_minutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
      'total_claims': instance.totalClaims,
      'total_completions': instance.totalCompletions,
      'completion_rate': instance.completionRate,
      'due_date': instance.dueDate?.toIso8601String(),
      'creator': instance.creator,
      'is_claimed_by_me': instance.isClaimedByMe,
      'my_completion_status': instance.myCompletionStatus,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

GroupTaskCreate _$GroupTaskCreateFromJson(Map<String, dynamic> json) =>
    GroupTaskCreate(
      title: json['title'] as String,
      description: json['description'] as String?,
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
              const [],
      estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 10,
      difficulty: (json['difficulty'] as num?)?.toInt() ?? 1,
      dueDate: json['due_date'] == null
          ? null
          : DateTime.parse(json['due_date'] as String),
    );

Map<String, dynamic> _$GroupTaskCreateToJson(GroupTaskCreate instance) =>
    <String, dynamic>{
      'title': instance.title,
      'description': instance.description,
      'tags': instance.tags,
      'estimated_minutes': instance.estimatedMinutes,
      'difficulty': instance.difficulty,
      'due_date': instance.dueDate?.toIso8601String(),
    };

CheckinRequest _$CheckinRequestFromJson(Map<String, dynamic> json) =>
    CheckinRequest(
      groupId: json['group_id'] as String,
      todayDurationMinutes: (json['today_duration_minutes'] as num).toInt(),
      message: json['message'] as String?,
    );

Map<String, dynamic> _$CheckinRequestToJson(CheckinRequest instance) =>
    <String, dynamic>{
      'group_id': instance.groupId,
      'message': instance.message,
      'today_duration_minutes': instance.todayDurationMinutes,
    };

CheckinResponse _$CheckinResponseFromJson(Map<String, dynamic> json) =>
    CheckinResponse(
      success: json['success'] as bool,
      newStreak: (json['new_streak'] as num).toInt(),
      flameEarned: (json['flame_earned'] as num).toInt(),
      rankInGroup: (json['rank_in_group'] as num).toInt(),
      groupCheckinCount: (json['group_checkin_count'] as num).toInt(),
    );

Map<String, dynamic> _$CheckinResponseToJson(CheckinResponse instance) =>
    <String, dynamic>{
      'success': instance.success,
      'new_streak': instance.newStreak,
      'flame_earned': instance.flameEarned,
      'rank_in_group': instance.rankInGroup,
      'group_checkin_count': instance.groupCheckinCount,
    };

FlameStatus _$FlameStatusFromJson(Map<String, dynamic> json) => FlameStatus(
      userId: json['user_id'] as String,
      flamePower: (json['flame_power'] as num).toInt(),
      flameColor: json['flame_color'] as String,
      flameSize: (json['flame_size'] as num).toDouble(),
      positionX: (json['position_x'] as num).toDouble(),
      positionY: (json['position_y'] as num).toDouble(),
    );

Map<String, dynamic> _$FlameStatusToJson(FlameStatus instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'flame_power': instance.flamePower,
      'flame_color': instance.flameColor,
      'flame_size': instance.flameSize,
      'position_x': instance.positionX,
      'position_y': instance.positionY,
    };

GroupFlameStatus _$GroupFlameStatusFromJson(Map<String, dynamic> json) =>
    GroupFlameStatus(
      groupId: json['group_id'] as String,
      totalPower: (json['total_power'] as num).toInt(),
      flames: (json['flames'] as List<dynamic>)
          .map((e) => FlameStatus.fromJson(e as Map<String, dynamic>))
          .toList(),
      bonfireLevel: (json['bonfire_level'] as num).toInt(),
    );

Map<String, dynamic> _$GroupFlameStatusToJson(GroupFlameStatus instance) =>
    <String, dynamic>{
      'group_id': instance.groupId,
      'total_power': instance.totalPower,
      'flames': instance.flames,
      'bonfire_level': instance.bonfireLevel,
    };
