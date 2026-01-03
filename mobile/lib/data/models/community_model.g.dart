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
      threadRootId: fields[11] as String?,
      mentionUserIds: (fields[12] as List?)?.cast<String>(),
      reactions: (fields[13] as Map?)?.cast<String, dynamic>(),
      isRevoked: fields[8] as bool,
      revokedAt: fields[14] as DateTime?,
      editedAt: fields[15] as DateTime?,
      readBy: (fields[9] as List?)?.cast<String>(),
      quotedMessage: fields[10] as MessageInfo?,
    );
  }

  @override
  void write(BinaryWriter writer, MessageInfo obj) {
    writer
      ..writeByte(16)
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
      ..writeByte(11)
      ..write(obj.threadRootId)
      ..writeByte(12)
      ..write(obj.mentionUserIds)
      ..writeByte(13)
      ..write(obj.reactions)
      ..writeByte(6)
      ..write(obj.createdAt)
      ..writeByte(7)
      ..write(obj.updatedAt)
      ..writeByte(8)
      ..write(obj.isRevoked)
      ..writeByte(14)
      ..write(obj.revokedAt)
      ..writeByte(15)
      ..write(obj.editedAt)
      ..writeByte(9)
      ..write(obj.readBy)
      ..writeByte(10)
      ..write(obj.quotedMessage);
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
      threadRootId: fields[12] as String?,
      mentionUserIds: (fields[13] as List?)?.cast<String>(),
      reactions: (fields[14] as Map?)?.cast<String, dynamic>(),
      readAt: fields[8] as DateTime?,
      isRevoked: fields[11] as bool,
      revokedAt: fields[15] as DateTime?,
      editedAt: fields[16] as DateTime?,
    );
  }

  @override
  void write(BinaryWriter writer, PrivateMessageInfo obj) {
    writer
      ..writeByte(17)
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
      ..writeByte(12)
      ..write(obj.threadRootId)
      ..writeByte(13)
      ..write(obj.mentionUserIds)
      ..writeByte(14)
      ..write(obj.reactions)
      ..writeByte(7)
      ..write(obj.isRead)
      ..writeByte(8)
      ..write(obj.readAt)
      ..writeByte(9)
      ..write(obj.createdAt)
      ..writeByte(10)
      ..write(obj.updatedAt)
      ..writeByte(11)
      ..write(obj.isRevoked)
      ..writeByte(15)
      ..write(obj.revokedAt)
      ..writeByte(16)
      ..write(obj.editedAt);
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
      case 6:
        return MessageType.planShare;
      case 7:
        return MessageType.fragmentShare;
      case 8:
        return MessageType.capsuleShare;
      case 9:
        return MessageType.prismShare;
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
      case MessageType.planShare:
        writer.writeByte(6);
        break;
      case MessageType.fragmentShare:
        writer.writeByte(7);
        break;
      case MessageType.capsuleShare:
        writer.writeByte(8);
        break;
      case MessageType.prismShare:
        writer.writeByte(9);
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
      threadRootId: json['thread_root_id'] as String?,
      mentionUserIds: (json['mention_user_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      reactions: json['reactions'] as Map<String, dynamic>?,
      isRevoked: json['is_revoked'] as bool? ?? false,
      revokedAt: json['revoked_at'] == null
          ? null
          : DateTime.parse(json['revoked_at'] as String),
      editedAt: json['edited_at'] == null
          ? null
          : DateTime.parse(json['edited_at'] as String),
      readBy:
          (json['read_by'] as List<dynamic>?)?.map((e) => e as String).toList(),
      quotedMessage: json['quoted_message'] == null
          ? null
          : MessageInfo.fromJson(
              json['quoted_message'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MessageInfoToJson(MessageInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'sender': instance.sender,
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'thread_root_id': instance.threadRootId,
      'mention_user_ids': instance.mentionUserIds,
      'reactions': instance.reactions,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'is_revoked': instance.isRevoked,
      'revoked_at': instance.revokedAt?.toIso8601String(),
      'edited_at': instance.editedAt?.toIso8601String(),
      'read_by': instance.readBy,
      'quoted_message': instance.quotedMessage,
    };

const _$MessageTypeEnumMap = {
  MessageType.text: 'text',
  MessageType.taskShare: 'task_share',
  MessageType.planShare: 'plan_share',
  MessageType.fragmentShare: 'fragment_share',
  MessageType.capsuleShare: 'capsule_share',
  MessageType.prismShare: 'prism_share',
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
      threadRootId: json['thread_root_id'] as String?,
      mentionUserIds: (json['mention_user_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      reactions: json['reactions'] as Map<String, dynamic>?,
      readAt: json['read_at'] == null
          ? null
          : DateTime.parse(json['read_at'] as String),
      isRevoked: json['is_revoked'] as bool? ?? false,
      revokedAt: json['revoked_at'] == null
          ? null
          : DateTime.parse(json['revoked_at'] as String),
      editedAt: json['edited_at'] == null
          ? null
          : DateTime.parse(json['edited_at'] as String),
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
      'thread_root_id': instance.threadRootId,
      'mention_user_ids': instance.mentionUserIds,
      'reactions': instance.reactions,
      'is_read': instance.isRead,
      'read_at': instance.readAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
      'is_revoked': instance.isRevoked,
      'revoked_at': instance.revokedAt?.toIso8601String(),
      'edited_at': instance.editedAt?.toIso8601String(),
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
      threadRootId: json['thread_root_id'] as String?,
      mentionUserIds: (json['mention_user_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      nonce: json['nonce'] as String?,
    );

Map<String, dynamic> _$PrivateMessageSendToJson(PrivateMessageSend instance) =>
    <String, dynamic>{
      'target_user_id': instance.targetUserId,
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'thread_root_id': instance.threadRootId,
      'mention_user_ids': instance.mentionUserIds,
      'nonce': instance.nonce,
    };

MessageSend _$MessageSendFromJson(Map<String, dynamic> json) => MessageSend(
      messageType:
          $enumDecodeNullable(_$MessageTypeEnumMap, json['message_type']) ??
              MessageType.text,
      content: json['content'] as String?,
      contentData: json['content_data'] as Map<String, dynamic>?,
      replyToId: json['reply_to_id'] as String?,
      threadRootId: json['thread_root_id'] as String?,
      mentionUserIds: (json['mention_user_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      nonce: json['nonce'] as String?,
    );

Map<String, dynamic> _$MessageSendToJson(MessageSend instance) =>
    <String, dynamic>{
      'message_type': _$MessageTypeEnumMap[instance.messageType]!,
      'content': instance.content,
      'content_data': instance.contentData,
      'reply_to_id': instance.replyToId,
      'thread_root_id': instance.threadRootId,
      'mention_user_ids': instance.mentionUserIds,
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

EncryptionKeyInfo _$EncryptionKeyInfoFromJson(Map<String, dynamic> json) =>
    EncryptionKeyInfo(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      publicKey: json['public_key'] as String,
      keyType: json['key_type'] as String,
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
      deviceId: json['device_id'] as String?,
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
    );

Map<String, dynamic> _$EncryptionKeyInfoToJson(EncryptionKeyInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'public_key': instance.publicKey,
      'key_type': instance.keyType,
      'device_id': instance.deviceId,
      'is_active': instance.isActive,
      'created_at': instance.createdAt.toIso8601String(),
      'expires_at': instance.expiresAt?.toIso8601String(),
    };

EncryptionKeyCreate _$EncryptionKeyCreateFromJson(Map<String, dynamic> json) =>
    EncryptionKeyCreate(
      publicKey: json['public_key'] as String,
      keyType: json['key_type'] as String? ?? 'x25519',
      deviceId: json['device_id'] as String?,
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
    );

Map<String, dynamic> _$EncryptionKeyCreateToJson(
        EncryptionKeyCreate instance) =>
    <String, dynamic>{
      'public_key': instance.publicKey,
      'key_type': instance.keyType,
      'device_id': instance.deviceId,
      'expires_at': instance.expiresAt?.toIso8601String(),
    };

MessageReportInfo _$MessageReportInfoFromJson(Map<String, dynamic> json) =>
    MessageReportInfo(
      id: json['id'] as String,
      reporterId: json['reporter_id'] as String,
      reason: $enumDecode(_$ReportReasonEnumMap, json['reason']),
      status: $enumDecode(_$ReportStatusEnumMap, json['status']),
      createdAt: DateTime.parse(json['created_at'] as String),
      groupMessageId: json['group_message_id'] as String?,
      privateMessageId: json['private_message_id'] as String?,
      description: json['description'] as String?,
      reviewedBy: json['reviewed_by'] as String?,
      reviewedAt: json['reviewed_at'] == null
          ? null
          : DateTime.parse(json['reviewed_at'] as String),
      actionTaken:
          $enumDecodeNullable(_$ModerationActionEnumMap, json['action_taken']),
      reporter: json['reporter'] == null
          ? null
          : UserBrief.fromJson(json['reporter'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MessageReportInfoToJson(MessageReportInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'reporter_id': instance.reporterId,
      'group_message_id': instance.groupMessageId,
      'private_message_id': instance.privateMessageId,
      'reason': _$ReportReasonEnumMap[instance.reason]!,
      'description': instance.description,
      'status': _$ReportStatusEnumMap[instance.status]!,
      'reviewed_by': instance.reviewedBy,
      'reviewed_at': instance.reviewedAt?.toIso8601String(),
      'action_taken': _$ModerationActionEnumMap[instance.actionTaken],
      'created_at': instance.createdAt.toIso8601String(),
      'reporter': instance.reporter,
    };

const _$ReportReasonEnumMap = {
  ReportReason.spam: 'spam',
  ReportReason.harassment: 'harassment',
  ReportReason.violence: 'violence',
  ReportReason.hateSpeech: 'hate_speech',
  ReportReason.misinformation: 'misinformation',
  ReportReason.other: 'other',
};

const _$ReportStatusEnumMap = {
  ReportStatus.pending: 'pending',
  ReportStatus.reviewed: 'reviewed',
  ReportStatus.dismissed: 'dismissed',
  ReportStatus.actioned: 'actioned',
};

const _$ModerationActionEnumMap = {
  ModerationAction.warn: 'warn',
  ModerationAction.mute: 'mute',
  ModerationAction.kick: 'kick',
  ModerationAction.ban: 'ban',
};

MessageReportCreate _$MessageReportCreateFromJson(Map<String, dynamic> json) =>
    MessageReportCreate(
      reason: $enumDecode(_$ReportReasonEnumMap, json['reason']),
      groupMessageId: json['group_message_id'] as String?,
      privateMessageId: json['private_message_id'] as String?,
      description: json['description'] as String?,
    );

Map<String, dynamic> _$MessageReportCreateToJson(
        MessageReportCreate instance) =>
    <String, dynamic>{
      'group_message_id': instance.groupMessageId,
      'private_message_id': instance.privateMessageId,
      'reason': _$ReportReasonEnumMap[instance.reason]!,
      'description': instance.description,
    };

MessageReportReview _$MessageReportReviewFromJson(Map<String, dynamic> json) =>
    MessageReportReview(
      status: $enumDecode(_$ReportStatusEnumMap, json['status']),
      actionTaken:
          $enumDecodeNullable(_$ModerationActionEnumMap, json['action_taken']),
    );

Map<String, dynamic> _$MessageReportReviewToJson(
        MessageReportReview instance) =>
    <String, dynamic>{
      'status': _$ReportStatusEnumMap[instance.status]!,
      'action_taken': _$ModerationActionEnumMap[instance.actionTaken],
    };

MessageFavoriteInfo _$MessageFavoriteInfoFromJson(Map<String, dynamic> json) =>
    MessageFavoriteInfo(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      groupMessageId: json['group_message_id'] as String?,
      privateMessageId: json['private_message_id'] as String?,
      note: json['note'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      groupMessage: json['group_message'] == null
          ? null
          : MessageInfo.fromJson(json['group_message'] as Map<String, dynamic>),
      privateMessage: json['private_message'] == null
          ? null
          : PrivateMessageInfo.fromJson(
              json['private_message'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$MessageFavoriteInfoToJson(
        MessageFavoriteInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'group_message_id': instance.groupMessageId,
      'private_message_id': instance.privateMessageId,
      'note': instance.note,
      'tags': instance.tags,
      'created_at': instance.createdAt.toIso8601String(),
      'group_message': instance.groupMessage,
      'private_message': instance.privateMessage,
    };

MessageFavoriteCreate _$MessageFavoriteCreateFromJson(
        Map<String, dynamic> json) =>
    MessageFavoriteCreate(
      groupMessageId: json['group_message_id'] as String?,
      privateMessageId: json['private_message_id'] as String?,
      note: json['note'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
    );

Map<String, dynamic> _$MessageFavoriteCreateToJson(
        MessageFavoriteCreate instance) =>
    <String, dynamic>{
      'group_message_id': instance.groupMessageId,
      'private_message_id': instance.privateMessageId,
      'note': instance.note,
      'tags': instance.tags,
    };

MessageForwardRequest _$MessageForwardRequestFromJson(
        Map<String, dynamic> json) =>
    MessageForwardRequest(
      sourceGroupMessageId: json['source_group_message_id'] as String?,
      sourcePrivateMessageId: json['source_private_message_id'] as String?,
      targetGroupId: json['target_group_id'] as String?,
      targetUserId: json['target_user_id'] as String?,
      additionalContent: json['additional_content'] as String?,
    );

Map<String, dynamic> _$MessageForwardRequestToJson(
        MessageForwardRequest instance) =>
    <String, dynamic>{
      'source_group_message_id': instance.sourceGroupMessageId,
      'source_private_message_id': instance.sourcePrivateMessageId,
      'target_group_id': instance.targetGroupId,
      'target_user_id': instance.targetUserId,
      'additional_content': instance.additionalContent,
    };

BroadcastMessageInfo _$BroadcastMessageInfoFromJson(
        Map<String, dynamic> json) =>
    BroadcastMessageInfo(
      id: json['id'] as String,
      senderId: json['sender_id'] as String,
      content: json['content'] as String,
      targetGroupIds: (json['target_group_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      deliveredCount: (json['delivered_count'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      contentData: json['content_data'] as Map<String, dynamic>?,
      sender: json['sender'] == null
          ? null
          : UserBrief.fromJson(json['sender'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$BroadcastMessageInfoToJson(
        BroadcastMessageInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'sender_id': instance.senderId,
      'content': instance.content,
      'content_data': instance.contentData,
      'target_group_ids': instance.targetGroupIds,
      'delivered_count': instance.deliveredCount,
      'created_at': instance.createdAt.toIso8601String(),
      'sender': instance.sender,
    };

BroadcastMessageCreate _$BroadcastMessageCreateFromJson(
        Map<String, dynamic> json) =>
    BroadcastMessageCreate(
      content: json['content'] as String,
      targetGroupIds: (json['target_group_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      contentData: json['content_data'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$BroadcastMessageCreateToJson(
        BroadcastMessageCreate instance) =>
    <String, dynamic>{
      'content': instance.content,
      'content_data': instance.contentData,
      'target_group_ids': instance.targetGroupIds,
    };

GroupModerationSettings _$GroupModerationSettingsFromJson(
        Map<String, dynamic> json) =>
    GroupModerationSettings(
      keywordFilters: (json['keyword_filters'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      muteAll: json['mute_all'] as bool?,
      slowModeSeconds: (json['slow_mode_seconds'] as num?)?.toInt(),
    );

Map<String, dynamic> _$GroupModerationSettingsToJson(
        GroupModerationSettings instance) =>
    <String, dynamic>{
      'keyword_filters': instance.keywordFilters,
      'mute_all': instance.muteAll,
      'slow_mode_seconds': instance.slowModeSeconds,
    };

GroupAnnouncementUpdate _$GroupAnnouncementUpdateFromJson(
        Map<String, dynamic> json) =>
    GroupAnnouncementUpdate(
      announcement: json['announcement'] as String?,
    );

Map<String, dynamic> _$GroupAnnouncementUpdateToJson(
        GroupAnnouncementUpdate instance) =>
    <String, dynamic>{
      'announcement': instance.announcement,
    };

MemberMuteRequest _$MemberMuteRequestFromJson(Map<String, dynamic> json) =>
    MemberMuteRequest(
      durationMinutes: (json['duration_minutes'] as num).toInt(),
      reason: json['reason'] as String?,
    );

Map<String, dynamic> _$MemberMuteRequestToJson(MemberMuteRequest instance) =>
    <String, dynamic>{
      'duration_minutes': instance.durationMinutes,
      'reason': instance.reason,
    };

MemberWarnRequest _$MemberWarnRequestFromJson(Map<String, dynamic> json) =>
    MemberWarnRequest(
      reason: json['reason'] as String,
    );

Map<String, dynamic> _$MemberWarnRequestToJson(MemberWarnRequest instance) =>
    <String, dynamic>{
      'reason': instance.reason,
    };

MessageSearchRequest _$MessageSearchRequestFromJson(
        Map<String, dynamic> json) =>
    MessageSearchRequest(
      keyword: json['keyword'] as String?,
      groupId: json['group_id'] as String?,
      friendId: json['friend_id'] as String?,
      senderId: json['sender_id'] as String?,
      messageTypes: (json['message_types'] as List<dynamic>?)
          ?.map((e) => $enumDecode(_$MessageTypeEnumMap, e))
          .toList(),
      startDate: json['start_date'] == null
          ? null
          : DateTime.parse(json['start_date'] as String),
      endDate: json['end_date'] == null
          ? null
          : DateTime.parse(json['end_date'] as String),
      topic: json['topic'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList(),
      useFullText: json['use_full_text'] as bool? ?? false,
      limit: (json['limit'] as num?)?.toInt() ?? 50,
      offset: (json['offset'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$MessageSearchRequestToJson(
        MessageSearchRequest instance) =>
    <String, dynamic>{
      'keyword': instance.keyword,
      'group_id': instance.groupId,
      'friend_id': instance.friendId,
      'sender_id': instance.senderId,
      'message_types':
          instance.messageTypes?.map((e) => _$MessageTypeEnumMap[e]!).toList(),
      'start_date': instance.startDate?.toIso8601String(),
      'end_date': instance.endDate?.toIso8601String(),
      'topic': instance.topic,
      'tags': instance.tags,
      'use_full_text': instance.useFullText,
      'limit': instance.limit,
      'offset': instance.offset,
    };

MessageSearchResult _$MessageSearchResultFromJson(Map<String, dynamic> json) =>
    MessageSearchResult(
      totalCount: (json['total_count'] as num).toInt(),
      groupMessages: (json['group_messages'] as List<dynamic>)
          .map((e) => MessageInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      privateMessages: (json['private_messages'] as List<dynamic>)
          .map((e) => PrivateMessageInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasMore: json['has_more'] as bool? ?? false,
    );

Map<String, dynamic> _$MessageSearchResultToJson(
        MessageSearchResult instance) =>
    <String, dynamic>{
      'total_count': instance.totalCount,
      'group_messages': instance.groupMessages,
      'private_messages': instance.privateMessages,
      'has_more': instance.hasMore,
    };

OfflineMessageInfo _$OfflineMessageInfoFromJson(Map<String, dynamic> json) =>
    OfflineMessageInfo(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      clientNonce: json['client_nonce'] as String,
      messageType: json['message_type'] as String,
      targetId: json['target_id'] as String,
      payload: json['payload'] as Map<String, dynamic>,
      status: $enumDecode(_$OfflineMessageStatusEnumMap, json['status']),
      retryCount: (json['retry_count'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      lastRetryAt: json['last_retry_at'] == null
          ? null
          : DateTime.parse(json['last_retry_at'] as String),
      errorMessage: json['error_message'] as String?,
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.parse(json['expires_at'] as String),
    );

Map<String, dynamic> _$OfflineMessageInfoToJson(OfflineMessageInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'client_nonce': instance.clientNonce,
      'message_type': instance.messageType,
      'target_id': instance.targetId,
      'payload': instance.payload,
      'status': _$OfflineMessageStatusEnumMap[instance.status]!,
      'retry_count': instance.retryCount,
      'last_retry_at': instance.lastRetryAt?.toIso8601String(),
      'error_message': instance.errorMessage,
      'created_at': instance.createdAt.toIso8601String(),
      'expires_at': instance.expiresAt?.toIso8601String(),
    };

const _$OfflineMessageStatusEnumMap = {
  OfflineMessageStatus.pending: 'pending',
  OfflineMessageStatus.sent: 'sent',
  OfflineMessageStatus.failed: 'failed',
  OfflineMessageStatus.expired: 'expired',
};

OfflineMessageRetryRequest _$OfflineMessageRetryRequestFromJson(
        Map<String, dynamic> json) =>
    OfflineMessageRetryRequest(
      messageIds: (json['message_ids'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$OfflineMessageRetryRequestToJson(
        OfflineMessageRetryRequest instance) =>
    <String, dynamic>{
      'message_ids': instance.messageIds,
    };
