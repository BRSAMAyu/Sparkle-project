import 'package:json_annotation/json_annotation.dart';
import 'package:hive/hive.dart';

part 'community_model.g.dart';

// ============ 枚举类型 ============

enum GroupType {
  @JsonValue('squad')
  squad,
  @JsonValue('sprint')
  sprint,
}

enum GroupRole {
  @JsonValue('owner')
  owner,
  @JsonValue('admin')
  admin,
  @JsonValue('member')
  member,
}

@HiveType(typeId: 11)
enum MessageType {
  @JsonValue('text')
  @HiveField(0)
  text,
  @JsonValue('task_share')
  @HiveField(1)
  taskShare,
  @JsonValue('progress')
  @HiveField(2)
  progress,
  @JsonValue('achievement')
  @HiveField(3)
  achievement,
  @JsonValue('checkin')
  @HiveField(4)
  checkin,
  @JsonValue('system')
  @HiveField(5)
  system,
}

enum FriendshipStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('accepted')
  accepted,
  @JsonValue('blocked')
  blocked,
}

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

// ============ 用户简要信息 ============

@JsonSerializable()
@HiveType(typeId: 12)
class UserBrief {
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
  Map<String, dynamic> toJson() => _$UserBriefToJson(this);

  String get displayName => nickname ?? username;
}

// ============ 好友系统 ============

@JsonSerializable()
class FriendshipInfo {
  final String id;
  final UserBrief friend;
  final FriendshipStatus status;
  @JsonKey(name: 'match_reason')
  final Map<String, dynamic>? matchReason;
  @JsonKey(name: 'initiated_by_me')
  final bool initiatedByMe;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  FriendshipInfo({
    required this.id,
    required this.friend,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.matchReason,
    this.initiatedByMe = false,
  });

  factory FriendshipInfo.fromJson(Map<String, dynamic> json) =>
      _$FriendshipInfoFromJson(json);
  Map<String, dynamic> toJson() => _$FriendshipInfoToJson(this);
}

@JsonSerializable()
class FriendRecommendation {
  final UserBrief user;
  @JsonKey(name: 'match_score')
  final double matchScore;
  @JsonKey(name: 'match_reasons')
  final List<String> matchReasons;

  FriendRecommendation({
    required this.user,
    required this.matchScore,
    required this.matchReasons,
  });

  factory FriendRecommendation.fromJson(Map<String, dynamic> json) =>
      _$FriendRecommendationFromJson(json);
  Map<String, dynamic> toJson() => _$FriendRecommendationToJson(this);
}

// ============ 群组 ============

@JsonSerializable()
class GroupInfo {
  final String id;
  final String name;
  final String? description;
  @JsonKey(name: 'avatar_url')
  final String? avatarUrl;
  final GroupType type;
  @JsonKey(name: 'focus_tags')
  final List<String> focusTags;
  final DateTime? deadline;
  @JsonKey(name: 'sprint_goal')
  final String? sprintGoal;
  @JsonKey(name: 'days_remaining')
  final int? daysRemaining;
  @JsonKey(name: 'member_count')
  final int memberCount;
  @JsonKey(name: 'total_flame_power')
  final int totalFlamePower;
  @JsonKey(name: 'today_checkin_count')
  final int todayCheckinCount;
  @JsonKey(name: 'total_tasks_completed')
  final int totalTasksCompleted;
  @JsonKey(name: 'max_members')
  final int maxMembers;
  @JsonKey(name: 'is_public')
  final bool isPublic;
  @JsonKey(name: 'join_requires_approval')
  final bool joinRequiresApproval;
  @JsonKey(name: 'my_role')
  final GroupRole? myRole;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  GroupInfo({
    required this.id,
    required this.name,
    required this.type,
    required this.focusTags,
    required this.memberCount,
    required this.totalFlamePower,
    required this.todayCheckinCount,
    required this.totalTasksCompleted,
    required this.maxMembers,
    required this.isPublic,
    required this.joinRequiresApproval,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.avatarUrl,
    this.deadline,
    this.sprintGoal,
    this.daysRemaining,
    this.myRole,
  });

  factory GroupInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupInfoFromJson(json);
  Map<String, dynamic> toJson() => _$GroupInfoToJson(this);

  bool get isSprint => type == GroupType.sprint;
  bool get isOwner => myRole == GroupRole.owner;
  bool get isAdmin => myRole == GroupRole.admin || myRole == GroupRole.owner;
}

@JsonSerializable()
class GroupListItem {
  final String id;
  final String name;
  final GroupType type;
  @JsonKey(name: 'member_count')
  final int memberCount;
  @JsonKey(name: 'total_flame_power')
  final int totalFlamePower;
  final DateTime? deadline;
  @JsonKey(name: 'days_remaining')
  final int? daysRemaining;
  @JsonKey(name: 'focus_tags')
  final List<String> focusTags;
  @JsonKey(name: 'my_role')
  final GroupRole? myRole;

  GroupListItem({
    required this.id,
    required this.name,
    required this.type,
    required this.memberCount,
    required this.totalFlamePower,
    required this.focusTags,
    this.deadline,
    this.daysRemaining,
    this.myRole,
  });

  factory GroupListItem.fromJson(Map<String, dynamic> json) =>
      _$GroupListItemFromJson(json);
  Map<String, dynamic> toJson() => _$GroupListItemToJson(this);

  bool get isSprint => type == GroupType.sprint;
}

@JsonSerializable()
class GroupCreate {
  final String name;
  final String? description;
  final GroupType type;
  @JsonKey(name: 'focus_tags')
  final List<String> focusTags;
  final DateTime? deadline;
  @JsonKey(name: 'sprint_goal')
  final String? sprintGoal;
  @JsonKey(name: 'max_members')
  final int maxMembers;
  @JsonKey(name: 'is_public')
  final bool isPublic;
  @JsonKey(name: 'join_requires_approval')
  final bool joinRequiresApproval;

  GroupCreate({
    required this.name,
    required this.type,
    this.description,
    this.focusTags = const [],
    this.deadline,
    this.sprintGoal,
    this.maxMembers = 50,
    this.isPublic = true,
    this.joinRequiresApproval = false,
  });

  factory GroupCreate.fromJson(Map<String, dynamic> json) =>
      _$GroupCreateFromJson(json);
  Map<String, dynamic> toJson() => _$GroupCreateToJson(this);
}

// ============ 群成员 ============

@JsonSerializable()
class GroupMemberInfo {
  final UserBrief user;
  final GroupRole role;
  @JsonKey(name: 'flame_contribution')
  final int flameContribution;
  @JsonKey(name: 'tasks_completed')
  final int tasksCompleted;
  @JsonKey(name: 'checkin_streak')
  final int checkinStreak;
  @JsonKey(name: 'joined_at')
  final DateTime joinedAt;
  @JsonKey(name: 'last_active_at')
  final DateTime lastActiveAt;

  GroupMemberInfo({
    required this.user,
    required this.role,
    required this.flameContribution,
    required this.tasksCompleted,
    required this.checkinStreak,
    required this.joinedAt,
    required this.lastActiveAt,
  });

  factory GroupMemberInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupMemberInfoFromJson(json);
  Map<String, dynamic> toJson() => _$GroupMemberInfoToJson(this);
}

// ============ 消息 ============

@JsonSerializable()
@HiveType(typeId: 13)
class MessageInfo {
  @HiveField(0)
  final String id;
  @HiveField(1)
  final UserBrief? sender;
  @JsonKey(name: 'message_type')
  @HiveField(2)
  final MessageType messageType;
  @HiveField(3)
  final String? content;
  @JsonKey(name: 'content_data')
  @HiveField(4)
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  @HiveField(5)
  final String? replyToId;
  @JsonKey(name: 'created_at')
  @HiveField(6)
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  @HiveField(7)
  final DateTime updatedAt;
  @JsonKey(name: 'is_revoked')
  @HiveField(8)
  final bool isRevoked;

  // Group chat read-by tracking
  @JsonKey(name: 'read_by')
  @HiveField(9)
  final List<String>? readBy;

  // Quoted message
  @JsonKey(name: 'quoted_message')
  @HiveField(10)
  final MessageInfo? quotedMessage;

  // Avatar URLs for read-by users (populated by service layer)
  @JsonKey(name: 'read_by_avatars', includeFromJson: false, includeToJson: false)
  final List<UserBrief>? readByUsers;

  MessageInfo({
    required this.id,
    required this.messageType,
    required this.createdAt,
    required this.updatedAt,
    this.sender,
    this.content,
    this.contentData,
    this.replyToId,
    this.isRevoked = false,
    this.readBy,
    this.quotedMessage,
    this.readByUsers,
  });

  factory MessageInfo.fromJson(Map<String, dynamic> json) =>
      _$MessageInfoFromJson(json);
  Map<String, dynamic> toJson() => _$MessageInfoToJson(this);

  bool get isSystemMessage => sender == null;

  int get readCount => readBy?.length ?? 0;
}

@JsonSerializable()
@HiveType(typeId: 14)
class PrivateMessageInfo {
  @HiveField(0)
  final String id;
  @HiveField(1)
  final UserBrief sender;
  @HiveField(2)
  final UserBrief receiver;
  @JsonKey(name: 'message_type')
  @HiveField(3)
  final MessageType messageType;
  @HiveField(4)
  final String? content;
  @JsonKey(name: 'content_data')
  @HiveField(5)
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  @HiveField(6)
  final String? replyToId;
  @JsonKey(name: 'is_read')
  @HiveField(7)
  final bool isRead;
  @JsonKey(name: 'read_at')
  @HiveField(8)
  final DateTime? readAt;
  @JsonKey(name: 'created_at')
  @HiveField(9)
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  @HiveField(10)
  final DateTime updatedAt;
  @JsonKey(name: 'is_revoked')
  @HiveField(11)
  final bool isRevoked;
  
  // Client-side transient status
  @JsonKey(includeFromJson: false, includeToJson: false)
  final bool isSending;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final bool hasError;
  
  // Quote support
  @JsonKey(name: 'quoted_message')
  final PrivateMessageInfo? quotedMessage;

  PrivateMessageInfo({
    required this.id,
    required this.sender,
    required this.receiver,
    required this.messageType,
    required this.isRead,
    required this.createdAt,
    required this.updatedAt,
    this.content,
    this.contentData,
    this.replyToId,
    this.readAt,
    this.isSending = false,
    this.hasError = false,
    this.isRevoked = false,
    this.quotedMessage,
  });

  factory PrivateMessageInfo.fromJson(Map<String, dynamic> json) =>
      _$PrivateMessageInfoFromJson(json);
  Map<String, dynamic> toJson() => _$PrivateMessageInfoToJson(this);

  PrivateMessageInfo copyWith({
    String? id,
    UserBrief? sender,
    UserBrief? receiver,
    MessageType? messageType,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    bool? isRead,
    DateTime? readAt,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isSending,
    bool? hasError,
    bool? isRevoked,
    PrivateMessageInfo? quotedMessage,
  }) {
    return PrivateMessageInfo(
      id: id ?? this.id,
      sender: sender ?? this.sender,
      receiver: receiver ?? this.receiver,
      messageType: messageType ?? this.messageType,
      content: content ?? this.content,
      contentData: contentData ?? this.contentData,
      replyToId: replyToId ?? this.replyToId,
      isRead: isRead ?? this.isRead,
      readAt: readAt ?? this.readAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      isSending: isSending ?? this.isSending,
      hasError: hasError ?? this.hasError,
      isRevoked: isRevoked ?? this.isRevoked,
      quotedMessage: quotedMessage ?? this.quotedMessage,
    );
  }
}

@JsonSerializable()
class PrivateMessageSend {
  @JsonKey(name: 'target_user_id')
  final String targetUserId;
  @JsonKey(name: 'message_type')
  final MessageType messageType;
  final String? content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  final String? replyToId;
  final String? nonce;

  PrivateMessageSend({
    required this.targetUserId,
    this.messageType = MessageType.text,
    this.content,
    this.contentData,
    this.replyToId,
    this.nonce,
  });

  factory PrivateMessageSend.fromJson(Map<String, dynamic> json) =>
      _$PrivateMessageSendFromJson(json);
  Map<String, dynamic> toJson() => _$PrivateMessageSendToJson(this);
}

@JsonSerializable()
class MessageSend {
  @JsonKey(name: 'message_type')
  final MessageType messageType;
  final String? content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  final String? replyToId;
  final String? nonce;

  MessageSend({
    this.messageType = MessageType.text,
    this.content,
    this.contentData,
    this.replyToId,
    this.nonce,
  });

  factory MessageSend.fromJson(Map<String, dynamic> json) =>
      _$MessageSendFromJson(json);
  Map<String, dynamic> toJson() => _$MessageSendToJson(this);
}

// ============ 群任务 ============

@JsonSerializable()
class GroupTaskInfo {
  final String id;
  final String title;
  final String? description;
  final List<String> tags;
  @JsonKey(name: 'estimated_minutes')
  final int estimatedMinutes;
  final int difficulty;
  @JsonKey(name: 'total_claims')
  final int totalClaims;
  @JsonKey(name: 'total_completions')
  final int totalCompletions;
  @JsonKey(name: 'completion_rate')
  final double completionRate;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  final UserBrief? creator;
  @JsonKey(name: 'is_claimed_by_me')
  final bool isClaimedByMe;
  @JsonKey(name: 'my_completion_status')
  final bool? myCompletionStatus;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  GroupTaskInfo({
    required this.id,
    required this.title,
    required this.tags,
    required this.estimatedMinutes,
    required this.difficulty,
    required this.totalClaims,
    required this.totalCompletions,
    required this.completionRate,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.dueDate,
    this.creator,
    this.isClaimedByMe = false,
    this.myCompletionStatus,
  });

  factory GroupTaskInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupTaskInfoFromJson(json);
  Map<String, dynamic> toJson() => _$GroupTaskInfoToJson(this);
}

@JsonSerializable()
class GroupTaskCreate {
  final String title;
  final String? description;
  final List<String> tags;
  @JsonKey(name: 'estimated_minutes')
  final int estimatedMinutes;
  final int difficulty;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;

  GroupTaskCreate({
    required this.title,
    this.description,
    this.tags = const [],
    this.estimatedMinutes = 10,
    this.difficulty = 1,
    this.dueDate,
  });

  factory GroupTaskCreate.fromJson(Map<String, dynamic> json) =>
      _$GroupTaskCreateFromJson(json);
  Map<String, dynamic> toJson() => _$GroupTaskCreateToJson(this);
}

// ============ 打卡 ============

@JsonSerializable()
class CheckinRequest {
  @JsonKey(name: 'group_id')
  final String groupId;
  final String? message;
  @JsonKey(name: 'today_duration_minutes')
  final int todayDurationMinutes;

  CheckinRequest({
    required this.groupId,
    required this.todayDurationMinutes,
    this.message,
  });

  factory CheckinRequest.fromJson(Map<String, dynamic> json) =>
      _$CheckinRequestFromJson(json);
  Map<String, dynamic> toJson() => _$CheckinRequestToJson(this);
}

@JsonSerializable()
class CheckinResponse {
  final bool success;
  @JsonKey(name: 'new_streak')
  final int newStreak;
  @JsonKey(name: 'flame_earned')
  final int flameEarned;
  @JsonKey(name: 'rank_in_group')
  final int rankInGroup;
  @JsonKey(name: 'group_checkin_count')
  final int groupCheckinCount;

  CheckinResponse({
    required this.success,
    required this.newStreak,
    required this.flameEarned,
    required this.rankInGroup,
    required this.groupCheckinCount,
  });

  factory CheckinResponse.fromJson(Map<String, dynamic> json) =>
      _$CheckinResponseFromJson(json);
  Map<String, dynamic> toJson() => _$CheckinResponseToJson(this);
}

// ============ 火堆可视化 ============

@JsonSerializable()
class FlameStatus {
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'flame_power')
  final int flamePower;
  @JsonKey(name: 'flame_color')
  final String flameColor;
  @JsonKey(name: 'flame_size')
  final double flameSize;
  @JsonKey(name: 'position_x')
  final double positionX;
  @JsonKey(name: 'position_y')
  final double positionY;

  FlameStatus({
    required this.userId,
    required this.flamePower,
    required this.flameColor,
    required this.flameSize,
    required this.positionX,
    required this.positionY,
  });

  factory FlameStatus.fromJson(Map<String, dynamic> json) =>
      _$FlameStatusFromJson(json);
  Map<String, dynamic> toJson() => _$FlameStatusToJson(this);
}

@JsonSerializable()
class GroupFlameStatus {
  @JsonKey(name: 'group_id')
  final String groupId;
  @JsonKey(name: 'total_power')
  final int totalPower;
  final List<FlameStatus> flames;
  @JsonKey(name: 'bonfire_level')
  final int bonfireLevel;

  GroupFlameStatus({
    required this.groupId,
    required this.totalPower,
    required this.flames,
    required this.bonfireLevel,
  });

  factory GroupFlameStatus.fromJson(Map<String, dynamic> json) =>
      _$GroupFlameStatusFromJson(json);
  Map<String, dynamic> toJson() => _$GroupFlameStatusToJson(this);
}
