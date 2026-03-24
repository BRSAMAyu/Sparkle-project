import 'package:hive/hive.dart';
import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

export 'package:sparkle/shared/entities/user_brief.dart';

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

enum GroupDirectorySort {
  @JsonValue('hot')
  hot,
  @JsonValue('latest')
  latest,
  @JsonValue('random')
  random,
}

@HiveType(typeId: 11)
enum MessageType {
  @JsonValue('text')
  @HiveField(0)
  text,
  @JsonValue('task_share')
  @HiveField(1)
  taskShare,
  @JsonValue('plan_share')
  @HiveField(6)
  planShare,
  @JsonValue('fragment_share')
  @HiveField(7)
  fragmentShare,
  @JsonValue('capsule_share')
  @HiveField(8)
  capsuleShare,
  @JsonValue('prism_share')
  @HiveField(9)
  prismShare,
  @JsonValue('file_share')
  @HiveField(10)
  fileShare,
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

enum FriendMatchStrategy {
  @JsonValue('compatibility')
  compatibility,
  @JsonValue('complementary')
  complementary,
}

enum FriendRecommendationTarget {
  @JsonValue('friend')
  friend,
  @JsonValue('accountability')
  accountability,
}

enum RecommendationItemType {
  @JsonValue('friend')
  friend,
  @JsonValue('group')
  group,
}

enum RecommendationFeedbackStage {
  @JsonValue('immediate')
  immediate,
  @JsonValue('follow_up')
  followUp,
  @JsonValue('outcome')
  outcome,
}

// ============ 举报相关枚举 ============

enum ReportReason {
  @JsonValue('spam')
  spam,
  @JsonValue('harassment')
  harassment,
  @JsonValue('violence')
  violence,
  @JsonValue('hate_speech')
  hateSpeech,
  @JsonValue('misinformation')
  misinformation,
  @JsonValue('other')
  other,
}

enum ReportStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('reviewed')
  reviewed,
  @JsonValue('dismissed')
  dismissed,
  @JsonValue('actioned')
  actioned,
}

enum ModerationAction {
  @JsonValue('warn')
  warn,
  @JsonValue('mute')
  mute,
  @JsonValue('kick')
  kick,
  @JsonValue('ban')
  ban,
}

// ============ 离线队列状态 ============

enum OfflineMessageStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('sent')
  sent,
  @JsonValue('failed')
  failed,
  @JsonValue('expired')
  expired,
}

// ============ 好友系统 ============

@JsonSerializable()
class AccountabilityFriendSummary {
  AccountabilityFriendSummary({
    required this.partnershipId,
    required this.slotType,
    required this.status,
    this.myRole,
    this.myCheckedInToday,
    this.partnerCheckedInToday,
    this.myStreakDays,
    this.partnerStreakDays,
    this.lastCheckinAt,
    this.goalPreview,
  });

  factory AccountabilityFriendSummary.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityFriendSummaryFromJson(json);

  @JsonKey(name: 'partnership_id')
  final String partnershipId;
  @JsonKey(name: 'slot_type')
  final String slotType;
  final String status;
  @JsonKey(name: 'my_role')
  final String? myRole;
  @JsonKey(name: 'my_checked_in_today')
  final bool? myCheckedInToday;
  @JsonKey(name: 'partner_checked_in_today')
  final bool? partnerCheckedInToday;
  @JsonKey(name: 'my_streak_days')
  final int? myStreakDays;
  @JsonKey(name: 'partner_streak_days')
  final int? partnerStreakDays;
  @JsonKey(name: 'last_checkin_at')
  final DateTime? lastCheckinAt;
  @JsonKey(name: 'goal_preview')
  final String? goalPreview;

  Map<String, dynamic> toJson() => _$AccountabilityFriendSummaryToJson(this);

  bool get isActive => status == 'active';
  bool get isPending => status == 'pending';
}

@JsonSerializable()
class FriendshipInfo {
  FriendshipInfo({
    required this.id,
    required this.friend,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.matchReason,
    this.initiatedByMe = false,
    this.accountability,
  });

  factory FriendshipInfo.fromJson(Map<String, dynamic> json) =>
      _$FriendshipInfoFromJson(json);
  final String id;
  final UserBrief friend;
  final FriendshipStatus status;
  @JsonKey(name: 'match_reason')
  final Map<String, dynamic>? matchReason;
  @JsonKey(name: 'initiated_by_me')
  final bool initiatedByMe;
  final AccountabilityFriendSummary? accountability;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  Map<String, dynamic> toJson() => _$FriendshipInfoToJson(this);
}

@JsonSerializable()
class FriendProfileDetail {
  FriendProfileDetail({
    required this.user,
    required this.friendship,
    this.accountability,
    this.relationshipSummary,
    this.achievementsSummary,
    this.leaderboardSummary,
    this.recentShares = const [],
    this.quickActions = const {},
  });

  factory FriendProfileDetail.fromJson(Map<String, dynamic> json) =>
      _$FriendProfileDetailFromJson(json);

  final UserBrief user;
  final Map<String, dynamic> friendship;
  final Map<String, dynamic>? accountability;
  @JsonKey(name: 'relationship_summary')
  final Map<String, dynamic>? relationshipSummary;
  @JsonKey(name: 'achievements_summary')
  final Map<String, dynamic>? achievementsSummary;
  @JsonKey(name: 'leaderboard_summary')
  final Map<String, dynamic>? leaderboardSummary;
  @JsonKey(name: 'recent_shares')
  final List<Map<String, dynamic>> recentShares;
  @JsonKey(name: 'quick_actions')
  final Map<String, dynamic> quickActions;

  Map<String, dynamic> toJson() => _$FriendProfileDetailToJson(this);
}

@JsonSerializable()
class FriendRecommendation {
  FriendRecommendation({
    required this.user,
    required this.matchScore,
    required this.matchReasons,
    this.strategy = 'compatibility',
    this.target = 'accountability',
    this.summary,
    this.relationshipStatus = 'none',
    this.isExistingFriend = false,
    this.canInviteAccountability = false,
    this.recommendedAction = 'send_friend_request',
    this.scoreBreakdown = const {},
  });

  factory FriendRecommendation.fromJson(Map<String, dynamic> json) =>
      _$FriendRecommendationFromJson(json);
  final UserBrief user;
  @JsonKey(name: 'match_score')
  final double matchScore;
  @JsonKey(name: 'match_reasons')
  final List<String> matchReasons;
  final String strategy;
  final String target;
  final String? summary;
  @JsonKey(name: 'relationship_status')
  final String relationshipStatus;
  @JsonKey(name: 'is_existing_friend')
  final bool isExistingFriend;
  @JsonKey(name: 'can_invite_accountability')
  final bool canInviteAccountability;
  @JsonKey(name: 'recommended_action')
  final String recommendedAction;
  @JsonKey(name: 'score_breakdown')
  final Map<String, double> scoreBreakdown;
  Map<String, dynamic> toJson() => _$FriendRecommendationToJson(this);
}

@JsonSerializable()
class RecommendationFeedbackPrompt {
  RecommendationFeedbackPrompt({
    required this.promptId,
    required this.itemType,
    required this.itemId,
    required this.stage,
    required this.triggerAction,
    required this.title,
    required this.dueAt,
    this.subtitle,
    this.strategy,
    this.target,
    this.user,
    this.group,
    this.reasonTags = const [],
  });

  factory RecommendationFeedbackPrompt.fromJson(Map<String, dynamic> json) =>
      _$RecommendationFeedbackPromptFromJson(json);

  @JsonKey(name: 'prompt_id')
  final String promptId;
  @JsonKey(name: 'item_type')
  final RecommendationItemType itemType;
  @JsonKey(name: 'item_id')
  final String itemId;
  final RecommendationFeedbackStage stage;
  @JsonKey(name: 'trigger_action')
  final String triggerAction;
  final String title;
  final String? subtitle;
  @JsonKey(name: 'due_at')
  final DateTime dueAt;
  final String? strategy;
  final String? target;
  final UserBrief? user;
  final GroupListItem? group;
  @JsonKey(name: 'reason_tags')
  final List<String> reasonTags;

  Map<String, dynamic> toJson() => _$RecommendationFeedbackPromptToJson(this);

  bool get isFriend => itemType == RecommendationItemType.friend;
  bool get isGroup => itemType == RecommendationItemType.group;
}

@JsonSerializable()
class RecommendationFeedbackInsight {
  RecommendationFeedbackInsight({
    required this.itemType,
    required this.recentFeedbackCount,
    this.averageScores = const {},
    this.topPositiveSignals = const [],
    this.topNegativeSignals = const [],
    this.userTuning = const {},
    this.globalAdjustments = const {},
  });

  factory RecommendationFeedbackInsight.fromJson(Map<String, dynamic> json) =>
      _$RecommendationFeedbackInsightFromJson(json);

  @JsonKey(name: 'item_type')
  final RecommendationItemType itemType;
  @JsonKey(name: 'recent_feedback_count')
  final int recentFeedbackCount;
  @JsonKey(name: 'average_scores')
  final Map<String, double> averageScores;
  @JsonKey(name: 'top_positive_signals')
  final List<String> topPositiveSignals;
  @JsonKey(name: 'top_negative_signals')
  final List<String> topNegativeSignals;
  @JsonKey(name: 'user_tuning')
  final Map<String, dynamic> userTuning;
  @JsonKey(name: 'global_adjustments')
  final Map<String, double> globalAdjustments;

  Map<String, dynamic> toJson() => _$RecommendationFeedbackInsightToJson(this);
}

// ============ 群组 ============

@JsonSerializable()
class GroupInfo {
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
    this.announcement,
  });

  factory GroupInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupInfoFromJson(json);
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
  final String? announcement;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  Map<String, dynamic> toJson() => _$GroupInfoToJson(this);

  bool get isSprint => type == GroupType.sprint;
  bool get isOwner => myRole == GroupRole.owner;
  bool get isAdmin => myRole == GroupRole.admin || myRole == GroupRole.owner;
}

@JsonSerializable()
class GroupListItem {
  GroupListItem({
    required this.id,
    required this.name,
    required this.type,
    required this.memberCount,
    required this.totalFlamePower,
    required this.focusTags,
    this.description,
    this.todayCheckinCount = 0,
    this.deadline,
    this.daysRemaining,
    this.isPublic = true,
    this.joinRequiresApproval = false,
    this.activityScore,
    this.myRole,
  });

  factory GroupListItem.fromJson(Map<String, dynamic> json) =>
      _$GroupListItemFromJson(json);
  final String id;
  final String name;
  final String? description;
  final GroupType type;
  @JsonKey(name: 'member_count')
  final int memberCount;
  @JsonKey(name: 'total_flame_power')
  final int totalFlamePower;
  @JsonKey(name: 'today_checkin_count')
  final int todayCheckinCount;
  final DateTime? deadline;
  @JsonKey(name: 'days_remaining')
  final int? daysRemaining;
  @JsonKey(name: 'focus_tags')
  final List<String> focusTags;
  @JsonKey(name: 'is_public')
  final bool isPublic;
  @JsonKey(name: 'join_requires_approval')
  final bool joinRequiresApproval;
  @JsonKey(name: 'activity_score')
  final double? activityScore;
  @JsonKey(name: 'my_role')
  final GroupRole? myRole;
  Map<String, dynamic> toJson() => _$GroupListItemToJson(this);

  bool get isSprint => type == GroupType.sprint;
  bool get isJoined => myRole != null;
}

@JsonSerializable()
class GroupRecommendationReason {
  GroupRecommendationReason({
    required this.type,
    this.data,
  });

  factory GroupRecommendationReason.fromJson(Map<String, dynamic> json) =>
      _$GroupRecommendationReasonFromJson(json);
  final String type;
  final Map<String, dynamic>? data;
  Map<String, dynamic> toJson() => _$GroupRecommendationReasonToJson(this);
}

@JsonSerializable()
class GroupRecommendationItem {
  GroupRecommendationItem({
    required this.group,
    required this.score,
    required this.reasons,
    required this.requiresApproval,
  });

  factory GroupRecommendationItem.fromJson(Map<String, dynamic> json) =>
      _$GroupRecommendationItemFromJson(json);
  final GroupListItem group;
  final double score;
  final List<GroupRecommendationReason> reasons;
  @JsonKey(name: 'requires_approval')
  final bool requiresApproval;
  Map<String, dynamic> toJson() => _$GroupRecommendationItemToJson(this);
}

@JsonSerializable()
class GroupDirectoryInfo {
  GroupDirectoryInfo({
    required this.sortBy,
    required this.availableTags,
    required this.totalCount,
    required this.recommendations,
    required this.groups,
    this.keyword,
    this.appliedTags = const [],
  });

  factory GroupDirectoryInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupDirectoryInfoFromJson(json);

  @JsonKey(name: 'sort_by')
  final GroupDirectorySort sortBy;
  final String? keyword;
  @JsonKey(name: 'applied_tags')
  final List<String> appliedTags;
  @JsonKey(name: 'available_tags')
  final List<String> availableTags;
  @JsonKey(name: 'total_count')
  final int totalCount;
  final List<GroupRecommendationItem> recommendations;
  final List<GroupListItem> groups;

  Map<String, dynamic> toJson() => _$GroupDirectoryInfoToJson(this);
}

@JsonSerializable()
class GroupCreate {
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
  Map<String, dynamic> toJson() => _$GroupCreateToJson(this);
}

// ============ 群成员 ============

@JsonSerializable()
class GroupMemberInfo {
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
  Map<String, dynamic> toJson() => _$GroupMemberInfoToJson(this);
}

// ============ 消息 ============

@JsonSerializable()
@HiveType(typeId: 13)
class MessageInfo {
  MessageInfo({
    required this.id,
    required this.messageType,
    required this.createdAt,
    required this.updatedAt,
    this.sender,
    this.content,
    this.contentData,
    this.replyToId,
    this.threadRootId,
    this.mentionUserIds,
    this.reactions,
    this.isRevoked = false,
    this.revokedAt,
    this.editedAt,
    this.readBy,
    this.quotedMessage,
    this.readByUsers,
  });

  factory MessageInfo.fromJson(Map<String, dynamic> json) =>
      _$MessageInfoFromJson(json);
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
  @JsonKey(name: 'thread_root_id')
  @HiveField(11)
  final String? threadRootId;
  @JsonKey(name: 'mention_user_ids')
  @HiveField(12)
  final List<String>? mentionUserIds;
  @JsonKey(name: 'reactions')
  @HiveField(13)
  final Map<String, dynamic>? reactions;
  @JsonKey(name: 'created_at')
  @HiveField(6)
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  @HiveField(7)
  final DateTime updatedAt;
  @JsonKey(name: 'is_revoked')
  @HiveField(8)
  final bool isRevoked;
  @JsonKey(name: 'revoked_at')
  @HiveField(14)
  final DateTime? revokedAt;
  @JsonKey(name: 'edited_at')
  @HiveField(15)
  final DateTime? editedAt;

  // Group chat read-by tracking
  @JsonKey(name: 'read_by')
  @HiveField(9)
  final List<String>? readBy;

  // Quoted message
  @JsonKey(name: 'quoted_message')
  @HiveField(10)
  final MessageInfo? quotedMessage;

  // Rich read-by user info for avatar and display rendering.
  @JsonKey(name: 'read_by_users')
  final List<UserBrief>? readByUsers;
  Map<String, dynamic> toJson() => _$MessageInfoToJson(this);

  bool get isSystemMessage => sender == null;

  int get readCount => readBy?.length ?? 0;

  bool get isEdited => editedAt != null;
}

@JsonSerializable()
@HiveType(typeId: 14)
class PrivateMessageInfo {
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
    this.threadRootId,
    this.mentionUserIds,
    this.reactions,
    this.readAt,
    this.isSending = false,
    this.hasError = false,
    this.isRevoked = false,
    this.revokedAt,
    this.editedAt,
    this.quotedMessage,
  });

  factory PrivateMessageInfo.fromJson(Map<String, dynamic> json) =>
      _$PrivateMessageInfoFromJson(json);
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
  @JsonKey(name: 'thread_root_id')
  @HiveField(12)
  final String? threadRootId;
  @JsonKey(name: 'mention_user_ids')
  @HiveField(13)
  final List<String>? mentionUserIds;
  @JsonKey(name: 'reactions')
  @HiveField(14)
  final Map<String, dynamic>? reactions;
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
  @JsonKey(name: 'revoked_at')
  @HiveField(15)
  final DateTime? revokedAt;
  @JsonKey(name: 'edited_at')
  @HiveField(16)
  final DateTime? editedAt;

  // Client-side transient status
  @JsonKey(includeFromJson: false, includeToJson: false)
  final bool isSending;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final bool hasError;

  // Quote support
  @JsonKey(name: 'quoted_message')
  final PrivateMessageInfo? quotedMessage;
  Map<String, dynamic> toJson() => _$PrivateMessageInfoToJson(this);

  PrivateMessageInfo copyWith({
    String? id,
    UserBrief? sender,
    UserBrief? receiver,
    MessageType? messageType,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
    Map<String, dynamic>? reactions,
    bool? isRead,
    DateTime? readAt,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isSending,
    bool? hasError,
    bool? isRevoked,
    DateTime? revokedAt,
    DateTime? editedAt,
    PrivateMessageInfo? quotedMessage,
  }) =>
      PrivateMessageInfo(
        id: id ?? this.id,
        sender: sender ?? this.sender,
        receiver: receiver ?? this.receiver,
        messageType: messageType ?? this.messageType,
        content: content ?? this.content,
        contentData: contentData ?? this.contentData,
        replyToId: replyToId ?? this.replyToId,
        threadRootId: threadRootId ?? this.threadRootId,
        mentionUserIds: mentionUserIds ?? this.mentionUserIds,
        reactions: reactions ?? this.reactions,
        isRead: isRead ?? this.isRead,
        readAt: readAt ?? this.readAt,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        isSending: isSending ?? this.isSending,
        hasError: hasError ?? this.hasError,
        isRevoked: isRevoked ?? this.isRevoked,
        revokedAt: revokedAt ?? this.revokedAt,
        editedAt: editedAt ?? this.editedAt,
        quotedMessage: quotedMessage ?? this.quotedMessage,
      );

  bool get isEdited => editedAt != null;
}

@JsonSerializable()
class PrivateMessageSend {
  PrivateMessageSend({
    required this.targetUserId,
    this.messageType = MessageType.text,
    this.content,
    this.contentData,
    this.replyToId,
    this.threadRootId,
    this.mentionUserIds,
    this.nonce,
  });

  factory PrivateMessageSend.fromJson(Map<String, dynamic> json) =>
      _$PrivateMessageSendFromJson(json);
  @JsonKey(name: 'target_user_id')
  final String targetUserId;
  @JsonKey(name: 'message_type')
  final MessageType messageType;
  final String? content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  final String? replyToId;
  @JsonKey(name: 'thread_root_id')
  final String? threadRootId;
  @JsonKey(name: 'mention_user_ids')
  final List<String>? mentionUserIds;
  final String? nonce;
  Map<String, dynamic> toJson() => _$PrivateMessageSendToJson(this);
}

@JsonSerializable()
class MessageSend {
  MessageSend({
    this.messageType = MessageType.text,
    this.content,
    this.contentData,
    this.replyToId,
    this.threadRootId,
    this.mentionUserIds,
    this.nonce,
  });

  factory MessageSend.fromJson(Map<String, dynamic> json) =>
      _$MessageSendFromJson(json);
  @JsonKey(name: 'message_type')
  final MessageType messageType;
  final String? content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'reply_to_id')
  final String? replyToId;
  @JsonKey(name: 'thread_root_id')
  final String? threadRootId;
  @JsonKey(name: 'mention_user_ids')
  final List<String>? mentionUserIds;
  final String? nonce;
  Map<String, dynamic> toJson() => _$MessageSendToJson(this);
}

// ============ 群任务 ============

@JsonSerializable()
class GroupTaskInfo {
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
  Map<String, dynamic> toJson() => _$GroupTaskInfoToJson(this);
}

@JsonSerializable()
class GroupTaskCreate {
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
  final String title;
  final String? description;
  final List<String> tags;
  @JsonKey(name: 'estimated_minutes')
  final int estimatedMinutes;
  final int difficulty;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  Map<String, dynamic> toJson() => _$GroupTaskCreateToJson(this);
}

// ============ 打卡 ============

@JsonSerializable()
class CheckinRequest {
  CheckinRequest({
    required this.groupId,
    required this.todayDurationMinutes,
    this.message,
  });

  factory CheckinRequest.fromJson(Map<String, dynamic> json) =>
      _$CheckinRequestFromJson(json);
  @JsonKey(name: 'group_id')
  final String groupId;
  final String? message;
  @JsonKey(name: 'today_duration_minutes')
  final int todayDurationMinutes;
  Map<String, dynamic> toJson() => _$CheckinRequestToJson(this);
}

@JsonSerializable()
class CheckinResponse {
  CheckinResponse({
    required this.success,
    required this.newStreak,
    required this.flameEarned,
    required this.rankInGroup,
    required this.groupCheckinCount,
  });

  factory CheckinResponse.fromJson(Map<String, dynamic> json) =>
      _$CheckinResponseFromJson(json);
  final bool success;
  @JsonKey(name: 'new_streak')
  final int newStreak;
  @JsonKey(name: 'flame_earned')
  final int flameEarned;
  @JsonKey(name: 'rank_in_group')
  final int rankInGroup;
  @JsonKey(name: 'group_checkin_count')
  final int groupCheckinCount;
  Map<String, dynamic> toJson() => _$CheckinResponseToJson(this);
}

// ============ 火堆可视化 ============

@JsonSerializable()
class FlameStatus {
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
  Map<String, dynamic> toJson() => _$FlameStatusToJson(this);
}

@JsonSerializable()
class GroupFlameStatus {
  GroupFlameStatus({
    required this.groupId,
    required this.totalPower,
    required this.flames,
    required this.bonfireLevel,
  });

  factory GroupFlameStatus.fromJson(Map<String, dynamic> json) =>
      _$GroupFlameStatusFromJson(json);
  @JsonKey(name: 'group_id')
  final String groupId;
  @JsonKey(name: 'total_power')
  final int totalPower;
  final List<FlameStatus> flames;
  @JsonKey(name: 'bonfire_level')
  final int bonfireLevel;
  Map<String, dynamic> toJson() => _$GroupFlameStatusToJson(this);
}

// ============ 加密密钥 ============

@JsonSerializable()
class EncryptionKeyInfo {
  EncryptionKeyInfo({
    required this.id,
    required this.userId,
    required this.publicKey,
    required this.keyType,
    required this.isActive,
    required this.createdAt,
    this.deviceId,
    this.expiresAt,
  });

  factory EncryptionKeyInfo.fromJson(Map<String, dynamic> json) =>
      _$EncryptionKeyInfoFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'public_key')
  final String publicKey;
  @JsonKey(name: 'key_type')
  final String keyType;
  @JsonKey(name: 'device_id')
  final String? deviceId;
  @JsonKey(name: 'is_active')
  final bool isActive;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'expires_at')
  final DateTime? expiresAt;
  Map<String, dynamic> toJson() => _$EncryptionKeyInfoToJson(this);
}

@JsonSerializable()
class EncryptionKeyCreate {
  EncryptionKeyCreate({
    required this.publicKey,
    this.keyType = 'x25519',
    this.deviceId,
    this.expiresAt,
  });

  factory EncryptionKeyCreate.fromJson(Map<String, dynamic> json) =>
      _$EncryptionKeyCreateFromJson(json);
  @JsonKey(name: 'public_key')
  final String publicKey;
  @JsonKey(name: 'key_type')
  final String keyType;
  @JsonKey(name: 'device_id')
  final String? deviceId;
  @JsonKey(name: 'expires_at')
  final DateTime? expiresAt;
  Map<String, dynamic> toJson() => _$EncryptionKeyCreateToJson(this);
}

// ============ 消息举报 ============

@JsonSerializable()
class MessageReportInfo {
  MessageReportInfo({
    required this.id,
    required this.reporterId,
    required this.reason,
    required this.status,
    required this.createdAt,
    this.groupMessageId,
    this.privateMessageId,
    this.description,
    this.reviewedBy,
    this.reviewedAt,
    this.actionTaken,
    this.reporter,
  });

  factory MessageReportInfo.fromJson(Map<String, dynamic> json) =>
      _$MessageReportInfoFromJson(json);
  final String id;
  @JsonKey(name: 'reporter_id')
  final String reporterId;
  @JsonKey(name: 'group_message_id')
  final String? groupMessageId;
  @JsonKey(name: 'private_message_id')
  final String? privateMessageId;
  final ReportReason reason;
  final String? description;
  final ReportStatus status;
  @JsonKey(name: 'reviewed_by')
  final String? reviewedBy;
  @JsonKey(name: 'reviewed_at')
  final DateTime? reviewedAt;
  @JsonKey(name: 'action_taken')
  final ModerationAction? actionTaken;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  final UserBrief? reporter;
  Map<String, dynamic> toJson() => _$MessageReportInfoToJson(this);
}

@JsonSerializable()
class MessageReportCreate {
  MessageReportCreate({
    required this.reason,
    this.groupMessageId,
    this.privateMessageId,
    this.description,
  });

  factory MessageReportCreate.fromJson(Map<String, dynamic> json) =>
      _$MessageReportCreateFromJson(json);
  @JsonKey(name: 'group_message_id')
  final String? groupMessageId;
  @JsonKey(name: 'private_message_id')
  final String? privateMessageId;
  final ReportReason reason;
  final String? description;
  Map<String, dynamic> toJson() => _$MessageReportCreateToJson(this);
}

@JsonSerializable()
class MessageReportReview {
  MessageReportReview({
    required this.status,
    this.actionTaken,
  });

  factory MessageReportReview.fromJson(Map<String, dynamic> json) =>
      _$MessageReportReviewFromJson(json);
  final ReportStatus status;
  @JsonKey(name: 'action_taken')
  final ModerationAction? actionTaken;
  Map<String, dynamic> toJson() => _$MessageReportReviewToJson(this);
}

// ============ 消息收藏 ============

@JsonSerializable()
class MessageFavoriteInfo {
  MessageFavoriteInfo({
    required this.id,
    required this.userId,
    required this.createdAt,
    this.groupMessageId,
    this.privateMessageId,
    this.note,
    this.tags,
    this.groupMessage,
    this.privateMessage,
  });

  factory MessageFavoriteInfo.fromJson(Map<String, dynamic> json) =>
      _$MessageFavoriteInfoFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'group_message_id')
  final String? groupMessageId;
  @JsonKey(name: 'private_message_id')
  final String? privateMessageId;
  final String? note;
  final List<String>? tags;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'group_message')
  final MessageInfo? groupMessage;
  @JsonKey(name: 'private_message')
  final PrivateMessageInfo? privateMessage;
  Map<String, dynamic> toJson() => _$MessageFavoriteInfoToJson(this);
}

@JsonSerializable()
class MessageFavoriteCreate {
  MessageFavoriteCreate({
    this.groupMessageId,
    this.privateMessageId,
    this.note,
    this.tags,
  });

  factory MessageFavoriteCreate.fromJson(Map<String, dynamic> json) =>
      _$MessageFavoriteCreateFromJson(json);
  @JsonKey(name: 'group_message_id')
  final String? groupMessageId;
  @JsonKey(name: 'private_message_id')
  final String? privateMessageId;
  final String? note;
  final List<String>? tags;
  Map<String, dynamic> toJson() => _$MessageFavoriteCreateToJson(this);
}

// ============ 消息转发 ============

@JsonSerializable()
class MessageForwardRequest {
  MessageForwardRequest({
    this.sourceGroupMessageId,
    this.sourcePrivateMessageId,
    this.targetGroupId,
    this.targetUserId,
    this.additionalContent,
  });

  factory MessageForwardRequest.fromJson(Map<String, dynamic> json) =>
      _$MessageForwardRequestFromJson(json);
  @JsonKey(name: 'source_group_message_id')
  final String? sourceGroupMessageId;
  @JsonKey(name: 'source_private_message_id')
  final String? sourcePrivateMessageId;
  @JsonKey(name: 'target_group_id')
  final String? targetGroupId;
  @JsonKey(name: 'target_user_id')
  final String? targetUserId;
  @JsonKey(name: 'additional_content')
  final String? additionalContent;
  Map<String, dynamic> toJson() => _$MessageForwardRequestToJson(this);
}

// ============ 跨群广播 ============

@JsonSerializable()
class BroadcastMessageInfo {
  BroadcastMessageInfo({
    required this.id,
    required this.senderId,
    required this.content,
    required this.targetGroupIds,
    required this.deliveredCount,
    required this.createdAt,
    this.contentData,
    this.sender,
  });

  factory BroadcastMessageInfo.fromJson(Map<String, dynamic> json) =>
      _$BroadcastMessageInfoFromJson(json);
  final String id;
  @JsonKey(name: 'sender_id')
  final String senderId;
  final String content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'target_group_ids')
  final List<String> targetGroupIds;
  @JsonKey(name: 'delivered_count')
  final int deliveredCount;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  final UserBrief? sender;
  Map<String, dynamic> toJson() => _$BroadcastMessageInfoToJson(this);
}

@JsonSerializable()
class BroadcastMessageCreate {
  BroadcastMessageCreate({
    required this.content,
    required this.targetGroupIds,
    this.contentData,
  });

  factory BroadcastMessageCreate.fromJson(Map<String, dynamic> json) =>
      _$BroadcastMessageCreateFromJson(json);
  final String content;
  @JsonKey(name: 'content_data')
  final Map<String, dynamic>? contentData;
  @JsonKey(name: 'target_group_ids')
  final List<String> targetGroupIds;
  Map<String, dynamic> toJson() => _$BroadcastMessageCreateToJson(this);
}

// ============ 群管理设置 ============

@JsonSerializable()
class GroupModerationSettings {
  const GroupModerationSettings({
    this.keywordFilters,
    this.muteAll,
    this.slowModeSeconds,
  });

  factory GroupModerationSettings.fromJson(Map<String, dynamic> json) =>
      _$GroupModerationSettingsFromJson(json);
  @JsonKey(name: 'keyword_filters')
  final List<String>? keywordFilters;
  @JsonKey(name: 'mute_all')
  final bool? muteAll;
  @JsonKey(name: 'slow_mode_seconds')
  final int? slowModeSeconds;
  Map<String, dynamic> toJson() => _$GroupModerationSettingsToJson(this);
}

@JsonSerializable()
class GroupAnnouncementUpdate {
  GroupAnnouncementUpdate({
    this.announcement,
  });

  factory GroupAnnouncementUpdate.fromJson(Map<String, dynamic> json) =>
      _$GroupAnnouncementUpdateFromJson(json);
  final String? announcement;
  Map<String, dynamic> toJson() => _$GroupAnnouncementUpdateToJson(this);
}

@JsonSerializable()
class MemberMuteRequest {
  MemberMuteRequest({
    required this.durationMinutes,
    this.reason,
  });

  factory MemberMuteRequest.fromJson(Map<String, dynamic> json) =>
      _$MemberMuteRequestFromJson(json);
  @JsonKey(name: 'duration_minutes')
  final int durationMinutes;
  final String? reason;
  Map<String, dynamic> toJson() => _$MemberMuteRequestToJson(this);
}

@JsonSerializable()
class MemberWarnRequest {
  MemberWarnRequest({
    required this.reason,
  });

  factory MemberWarnRequest.fromJson(Map<String, dynamic> json) =>
      _$MemberWarnRequestFromJson(json);
  final String reason;
  Map<String, dynamic> toJson() => _$MemberWarnRequestToJson(this);
}

// ============ 高级搜索 ============

@JsonSerializable()
class MessageSearchRequest {
  MessageSearchRequest({
    this.keyword,
    this.groupId,
    this.friendId,
    this.senderId,
    this.messageTypes,
    this.startDate,
    this.endDate,
    this.topic,
    this.tags,
    this.useFullText = false,
    this.limit = 50,
    this.offset = 0,
  });

  factory MessageSearchRequest.fromJson(Map<String, dynamic> json) =>
      _$MessageSearchRequestFromJson(json);
  final String? keyword;
  @JsonKey(name: 'group_id')
  final String? groupId;
  @JsonKey(name: 'friend_id')
  final String? friendId;
  @JsonKey(name: 'sender_id')
  final String? senderId;
  @JsonKey(name: 'message_types')
  final List<MessageType>? messageTypes;
  @JsonKey(name: 'start_date')
  final DateTime? startDate;
  @JsonKey(name: 'end_date')
  final DateTime? endDate;
  final String? topic;
  final List<String>? tags;
  @JsonKey(name: 'use_full_text')
  final bool useFullText;
  final int limit;
  final int offset;
  Map<String, dynamic> toJson() => _$MessageSearchRequestToJson(this);
}

@JsonSerializable()
class MessageSearchResult {
  MessageSearchResult({
    required this.totalCount,
    required this.groupMessages,
    required this.privateMessages,
    this.hasMore = false,
  });

  factory MessageSearchResult.fromJson(Map<String, dynamic> json) =>
      _$MessageSearchResultFromJson(json);
  @JsonKey(name: 'total_count')
  final int totalCount;
  @JsonKey(name: 'group_messages')
  final List<MessageInfo> groupMessages;
  @JsonKey(name: 'private_messages')
  final List<PrivateMessageInfo> privateMessages;
  @JsonKey(name: 'has_more')
  final bool hasMore;
  Map<String, dynamic> toJson() => _$MessageSearchResultToJson(this);
}

// ============ 离线队列 ============

@JsonSerializable()
class OfflineMessageInfo {
  OfflineMessageInfo({
    required this.id,
    required this.userId,
    required this.clientNonce,
    required this.messageType,
    required this.targetId,
    required this.payload,
    required this.status,
    required this.retryCount,
    required this.createdAt,
    this.lastRetryAt,
    this.errorMessage,
    this.expiresAt,
  });

  factory OfflineMessageInfo.fromJson(Map<String, dynamic> json) =>
      _$OfflineMessageInfoFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'client_nonce')
  final String clientNonce;
  @JsonKey(name: 'message_type')
  final String messageType;
  @JsonKey(name: 'target_id')
  final String targetId;
  final Map<String, dynamic> payload;
  final OfflineMessageStatus status;
  @JsonKey(name: 'retry_count')
  final int retryCount;
  @JsonKey(name: 'last_retry_at')
  final DateTime? lastRetryAt;
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'expires_at')
  final DateTime? expiresAt;
  Map<String, dynamic> toJson() => _$OfflineMessageInfoToJson(this);
}

@JsonSerializable()
class OfflineMessageRetryRequest {
  OfflineMessageRetryRequest({
    required this.messageIds,
  });

  factory OfflineMessageRetryRequest.fromJson(Map<String, dynamic> json) =>
      _$OfflineMessageRetryRequestFromJson(json);
  @JsonKey(name: 'message_ids')
  final List<String> messageIds;
  Map<String, dynamic> toJson() => _$OfflineMessageRetryRequestToJson(this);
}

// ============ 黑名单管理 ============

@JsonSerializable()
class BlockUserInfo {
  BlockUserInfo({
    required this.blockedUser,
    this.reason,
  });

  factory BlockUserInfo.fromJson(Map<String, dynamic> json) =>
      _$BlockUserInfoFromJson(json);
  @JsonKey(name: 'blocked_user')
  final UserBrief blockedUser;
  final String? reason;
  Map<String, dynamic> toJson() => _$BlockUserInfoToJson(this);
}

// ============ 隐私设置 ============

enum SearchVisibility {
  @JsonValue('everyone')
  everyone,
  @JsonValue('friends')
  friends,
  @JsonValue('nobody')
  nobody,
}

@JsonSerializable()
class UserPrivacySettings {
  UserPrivacySettings({
    required this.searchableBy,
  });

  factory UserPrivacySettings.fromJson(Map<String, dynamic> json) =>
      _$UserPrivacySettingsFromJson(json);
  @JsonKey(name: 'searchable_by')
  final SearchVisibility searchableBy;
  Map<String, dynamic> toJson() => _$UserPrivacySettingsToJson(this);
}

// ============ 群文件 ============

@JsonSerializable()
class GroupFileInfo {
  GroupFileInfo({
    required this.id,
    required this.groupId,
    required this.uploaderId,
    required this.fileName,
    required this.fileSize,
    required this.mimeType,
    required this.fileUrl,
    required this.permissions,
    required this.createdAt,
    this.description,
    this.category,
    this.tags,
    this.uploader,
  });

  factory GroupFileInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupFileInfoFromJson(json);
  final String id;
  @JsonKey(name: 'group_id')
  final String groupId;
  @JsonKey(name: 'uploader_id')
  final String uploaderId;
  @JsonKey(name: 'file_name')
  final String fileName;
  @JsonKey(name: 'file_size')
  final int fileSize;
  @JsonKey(name: 'mime_type')
  final String mimeType;
  @JsonKey(name: 'file_url')
  final String fileUrl;
  final String? description;
  final String? category;
  final List<String>? tags;
  final GroupFilePermissions permissions;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  final UserBrief? uploader;
  Map<String, dynamic> toJson() => _$GroupFileInfoToJson(this);
}

@JsonSerializable()
class GroupFilePermissions {
  GroupFilePermissions({
    this.canView = const [],
    this.canDownload = const [],
    this.canDelete = const [],
  });

  factory GroupFilePermissions.fromJson(Map<String, dynamic> json) =>
      _$GroupFilePermissionsFromJson(json);
  @JsonKey(name: 'can_view')
  final List<String> canView;
  @JsonKey(name: 'can_download')
  final List<String> canDownload;
  @JsonKey(name: 'can_delete')
  final List<String> canDelete;
  Map<String, dynamic> toJson() => _$GroupFilePermissionsToJson(this);
}

@JsonSerializable()
class GroupFilePermissionUpdate {
  GroupFilePermissionUpdate({
    this.canView,
    this.canDownload,
    this.canDelete,
  });

  factory GroupFilePermissionUpdate.fromJson(Map<String, dynamic> json) =>
      _$GroupFilePermissionUpdateFromJson(json);
  @JsonKey(name: 'can_view')
  final List<String>? canView;
  @JsonKey(name: 'can_download')
  final List<String>? canDownload;
  @JsonKey(name: 'can_delete')
  final List<String>? canDelete;
  Map<String, dynamic> toJson() => _$GroupFilePermissionUpdateToJson(this);
}

@JsonSerializable()
class GroupFileCategoryStat {
  GroupFileCategoryStat({
    required this.category,
    required this.count,
    required this.totalSize,
  });

  factory GroupFileCategoryStat.fromJson(Map<String, dynamic> json) =>
      _$GroupFileCategoryStatFromJson(json);
  final String category;
  final int count;
  @JsonKey(name: 'total_size')
  final int totalSize;
  Map<String, dynamic> toJson() => _$GroupFileCategoryStatToJson(this);
}

@JsonSerializable()
class GroupFileShareRequest {
  GroupFileShareRequest({
    required this.fileId,
    this.description,
    this.category,
    this.tags,
  });

  factory GroupFileShareRequest.fromJson(Map<String, dynamic> json) =>
      _$GroupFileShareRequestFromJson(json);
  @JsonKey(name: 'file_id')
  final String fileId;
  final String? description;
  final String? category;
  final List<String>? tags;
  Map<String, dynamic> toJson() => _$GroupFileShareRequestToJson(this);
}

// ============ 共享资源 ============

enum SharedResourceType {
  @JsonValue('task')
  task,
  @JsonValue('plan')
  plan,
  @JsonValue('knowledge_node')
  knowledgeNode,
  @JsonValue('seed_library')
  seedLibrary,
  @JsonValue('seed_item')
  seedItem,
  @JsonValue('cognitive_fragment')
  cognitiveFragment,
  @JsonValue('curiosity_capsule')
  curiosityCapsule,
  @JsonValue('cognitive_prism_pattern')
  cognitivePrismPattern,
  @JsonValue('fragment')
  fragment,
  @JsonValue('capsule')
  capsule,
  @JsonValue('achievement')
  achievement,
  @JsonValue('file')
  file,
}

class SharedResourceInfo {
  SharedResourceInfo({
    required this.id,
    required this.resourceType,
    required this.createdAt,
    this.updatedAt,
    this.planId,
    this.taskId,
    this.knowledgeNodeId,
    this.seedLibraryId,
    this.seedItemId,
    this.cognitiveFragmentId,
    this.curiosityCapsuleId,
    this.behaviorPatternId,
    this.permission,
    this.comment,
    this.viewCount,
    this.saveCount,
    this.sharer,
    this.resourceTitle,
    this.resourceSummary,
    this.entityCard,
  });

  factory SharedResourceInfo.fromJson(Map<String, dynamic> json) {
    SharedResourceType parseResourceType(dynamic raw) {
      final key = raw?.toString();
      return SharedResourceType.values.firstWhere(
        (value) => value.name == key,
        orElse: () => SharedResourceType.task,
      );
    }

    DateTime? parseDate(dynamic raw) {
      final value = raw?.toString();
      if (value == null || value.isEmpty) {
        return null;
      }
      return DateTime.tryParse(value);
    }

    return SharedResourceInfo(
      id: json['id'] as String,
      resourceType: parseResourceType(json['resource_type']),
      createdAt: parseDate(json['created_at']) ?? DateTime.now(),
      updatedAt: parseDate(json['updated_at']),
      planId: json['plan_id'] as String?,
      taskId: json['task_id'] as String?,
      knowledgeNodeId: json['knowledge_node_id'] as String?,
      seedLibraryId: json['seed_library_id'] as String?,
      seedItemId: json['seed_item_id'] as String?,
      cognitiveFragmentId: json['cognitive_fragment_id'] as String?,
      curiosityCapsuleId: json['curiosity_capsule_id'] as String?,
      behaviorPatternId: json['behavior_pattern_id'] as String?,
      permission: json['permission'] as String?,
      comment: json['comment'] as String?,
      viewCount: (json['view_count'] as num?)?.toInt(),
      saveCount: (json['save_count'] as num?)?.toInt(),
      sharer: json['sharer'] is Map<String, dynamic>
          ? UserBrief.fromJson(json['sharer'] as Map<String, dynamic>)
          : json['sharer'] is Map
              ? UserBrief.fromJson(
                  Map<String, dynamic>.from(
                    json['sharer'] as Map<Object?, Object?>,
                  ),
                )
              : null,
      resourceTitle: json['resource_title'] as String?,
      resourceSummary: json['resource_summary'] as String?,
      entityCard: json['entity_card'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['entity_card'] as Map<String, dynamic>)
          : json['entity_card'] is Map
              ? Map<String, dynamic>.from(
                  json['entity_card'] as Map<Object?, Object?>,
                )
              : null,
    );
  }
  final String id;
  @JsonKey(name: 'resource_type')
  final SharedResourceType resourceType;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;
  @JsonKey(name: 'plan_id')
  final String? planId;
  @JsonKey(name: 'task_id')
  final String? taskId;
  @JsonKey(name: 'knowledge_node_id')
  final String? knowledgeNodeId;
  @JsonKey(name: 'seed_library_id')
  final String? seedLibraryId;
  @JsonKey(name: 'seed_item_id')
  final String? seedItemId;
  @JsonKey(name: 'cognitive_fragment_id')
  final String? cognitiveFragmentId;
  @JsonKey(name: 'curiosity_capsule_id')
  final String? curiosityCapsuleId;
  @JsonKey(name: 'behavior_pattern_id')
  final String? behaviorPatternId;
  final String? permission;
  final String? comment;
  @JsonKey(name: 'view_count')
  final int? viewCount;
  @JsonKey(name: 'save_count')
  final int? saveCount;
  final UserBrief? sharer;
  @JsonKey(name: 'resource_title')
  final String? resourceTitle;
  @JsonKey(name: 'resource_summary')
  final String? resourceSummary;
  @JsonKey(name: 'entity_card')
  final Map<String, dynamic>? entityCard;

  String? get resourceId =>
      planId ??
      taskId ??
      knowledgeNodeId ??
      seedLibraryId ??
      seedItemId ??
      cognitiveFragmentId ??
      curiosityCapsuleId ??
      behaviorPatternId;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'resource_type': resourceType.name,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
        'plan_id': planId,
        'task_id': taskId,
        'knowledge_node_id': knowledgeNodeId,
        'seed_library_id': seedLibraryId,
        'seed_item_id': seedItemId,
        'cognitive_fragment_id': cognitiveFragmentId,
        'curiosity_capsule_id': curiosityCapsuleId,
        'behavior_pattern_id': behaviorPatternId,
        'permission': permission,
        'comment': comment,
        'view_count': viewCount,
        'save_count': saveCount,
        'sharer': sharer?.toJson(),
        'resource_title': resourceTitle,
        'resource_summary': resourceSummary,
        'entity_card': entityCard,
      };
}

@JsonSerializable()
class SharedResourceCreate {
  SharedResourceCreate({
    required this.resourceType,
    required this.resourceId,
    required this.groupIds,
  });

  factory SharedResourceCreate.fromJson(Map<String, dynamic> json) =>
      _$SharedResourceCreateFromJson(json);
  @JsonKey(name: 'resource_type')
  final SharedResourceType resourceType;
  @JsonKey(name: 'resource_id')
  final String resourceId;
  @JsonKey(name: 'group_ids')
  final List<String> groupIds;
  Map<String, dynamic> toJson() => _$SharedResourceCreateToJson(this);
}

@JsonSerializable()
class UserStatusUpdate {
  UserStatusUpdate({
    required this.status,
  });

  factory UserStatusUpdate.fromJson(Map<String, dynamic> json) =>
      _$UserStatusUpdateFromJson(json);
  final String status;
  Map<String, dynamic> toJson() => _$UserStatusUpdateToJson(this);
}
