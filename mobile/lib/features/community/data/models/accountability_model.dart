import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

part 'accountability_model.g.dart';

// ─── Enums ────────────────────────────────────────────────────────────────────

enum AccountabilityStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('active')
  active,
  @JsonValue('paused')
  paused,
  @JsonValue('ended')
  ended,
}

// ─── Models ───────────────────────────────────────────────────────────────────

@JsonSerializable()
class AccountabilityPartnershipInfo {
  AccountabilityPartnershipInfo({
    required this.id,
    required this.initiatorId,
    required this.partnerId,
    required this.initiatorGoal,
    required this.checkInDays,
    this.slotType = 'core',
    required this.status,
    required this.createdAt,
    this.partnerGoal,
    this.startedAt,
    this.endedAt,
    this.initiator,
    this.partner,
    // Runtime stats (populated from /stats endpoint)
    this.myStreakDays,
    this.partnerStreakDays,
    this.myCheckedInToday,
    this.partnerCheckedInToday,
    this.lastCheckinAt,
  });

  factory AccountabilityPartnershipInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityPartnershipInfoFromJson(json);

  final String id;
  @JsonKey(name: 'initiator_id')
  final String initiatorId;
  @JsonKey(name: 'partner_id')
  final String partnerId;
  @JsonKey(name: 'initiator_goal')
  final String initiatorGoal;
  @JsonKey(name: 'partner_goal')
  final String? partnerGoal;
  @JsonKey(name: 'check_in_days')
  final int checkInDays;
  @JsonKey(name: 'slot_type')
  final String slotType;
  final AccountabilityStatus status;
  @JsonKey(name: 'started_at')
  final DateTime? startedAt;
  @JsonKey(name: 'ended_at')
  final DateTime? endedAt;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  // Populated from relationship in API response
  final UserBrief? initiator;
  final UserBrief? partner;

  // Runtime stats and summary fields
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? myStreakDays;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? partnerStreakDays;
  @JsonKey(name: 'my_checked_in_today')
  final bool? myCheckedInToday;
  @JsonKey(name: 'partner_checked_in_today')
  final bool? partnerCheckedInToday;
  @JsonKey(name: 'last_checkin_at')
  final DateTime? lastCheckinAt;

  Map<String, dynamic> toJson() => _$AccountabilityPartnershipInfoToJson(this);

  AccountabilityPartnershipInfo copyWithStats({
    int? myStreakDays,
    int? partnerStreakDays,
    bool? myCheckedInToday,
    bool? partnerCheckedInToday,
    DateTime? lastCheckinAt,
  }) =>
      AccountabilityPartnershipInfo(
        id: id,
        initiatorId: initiatorId,
        partnerId: partnerId,
        initiatorGoal: initiatorGoal,
        partnerGoal: partnerGoal,
        checkInDays: checkInDays,
        slotType: slotType,
        status: status,
        startedAt: startedAt,
        endedAt: endedAt,
        createdAt: createdAt,
        initiator: initiator,
        partner: partner,
        myStreakDays: myStreakDays ?? this.myStreakDays,
        partnerStreakDays: partnerStreakDays ?? this.partnerStreakDays,
        myCheckedInToday: myCheckedInToday ?? this.myCheckedInToday,
        partnerCheckedInToday:
            partnerCheckedInToday ?? this.partnerCheckedInToday,
        lastCheckinAt: lastCheckinAt ?? this.lastCheckinAt,
      );
}

@JsonSerializable()
class AccountabilityCheckinInfo {
  AccountabilityCheckinInfo({
    required this.id,
    required this.partnershipId,
    required this.userId,
    required this.content,
    required this.mood,
    required this.minutes,
    required this.createdAt,
    this.likes = 0,
    this.encouragements = const [],
    this.author,
  });

  factory AccountabilityCheckinInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityCheckinInfoFromJson(json);

  final String id;
  @JsonKey(name: 'partnership_id')
  final String partnershipId;
  @JsonKey(name: 'user_id')
  final String userId;
  final String content;
  final int mood;
  final int minutes;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  final UserBrief? author;

  // 互动字段
  final int likes;
  final List<EncouragementMessage> encouragements;

  Map<String, dynamic> toJson() => _$AccountabilityCheckinInfoToJson(this);
}

/// 鼓励消息模型
@JsonSerializable()
class EncouragementMessage {
  EncouragementMessage({
    required this.id,
    required this.userId,
    required this.message,
    required this.createdAt,
  });

  factory EncouragementMessage.fromJson(Map<String, dynamic> json) =>
      _$EncouragementMessageFromJson(json);

  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  final String message;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  Map<String, dynamic> toJson() => _$EncouragementMessageToJson(this);
}

@JsonSerializable()
class AccountabilityStatsInfo {
  AccountabilityStatsInfo({
    required this.myStreakDays,
    required this.partnerStreakDays,
    required this.myCheckedInToday,
    required this.partnerCheckedInToday,
    required this.totalCheckins,
  });

  factory AccountabilityStatsInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityStatsInfoFromJson(json);

  @JsonKey(name: 'my_streak_days')
  final int myStreakDays;
  @JsonKey(name: 'partner_streak_days')
  final int partnerStreakDays;
  @JsonKey(name: 'my_checked_in_today')
  final bool myCheckedInToday;
  @JsonKey(name: 'partner_checked_in_today')
  final bool partnerCheckedInToday;
  @JsonKey(name: 'total_checkins')
  final int totalCheckins;

  Map<String, dynamic> toJson() => _$AccountabilityStatsInfoToJson(this);
}

@JsonSerializable()
class AccountabilityOverviewInfo {
  AccountabilityOverviewInfo({
    required this.slotType,
    this.activePartnership,
    this.pendingPartnerships = const [],
    this.achievementsSummary = const {},
    this.leaderboardSummary = const {},
    this.relationshipSummary,
    this.quickActions = const {},
    this.inAppHints = const [],
  });

  factory AccountabilityOverviewInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityOverviewInfoFromJson(json);

  @JsonKey(name: 'slot_type')
  final String slotType;
  @JsonKey(name: 'active_partnership')
  final AccountabilityPartnershipInfo? activePartnership;
  @JsonKey(name: 'pending_partnerships')
  final List<AccountabilityPartnershipInfo> pendingPartnerships;
  @JsonKey(name: 'achievements_summary')
  final Map<String, dynamic> achievementsSummary;
  @JsonKey(name: 'leaderboard_summary')
  final Map<String, dynamic> leaderboardSummary;
  @JsonKey(name: 'relationship_summary')
  final Map<String, dynamic>? relationshipSummary;
  @JsonKey(name: 'quick_actions')
  final Map<String, dynamic> quickActions;
  @JsonKey(name: 'in_app_hints')
  final List<AccountabilityInAppHintInfo> inAppHints;

  Map<String, dynamic> toJson() => _$AccountabilityOverviewInfoToJson(this);
}

@JsonSerializable()
class AccountabilityInAppHintInfo {
  AccountabilityInAppHintInfo({
    required this.id,
    required this.message,
    this.type,
    this.senderName,
    this.senderId,
    this.partnershipId,
    this.sourceNotificationId,
    this.createdAt,
  });

  factory AccountabilityInAppHintInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityInAppHintInfoFromJson(json);

  final String id;
  final String? type;
  final String message;
  @JsonKey(name: 'sender_name')
  final String? senderName;
  @JsonKey(name: 'sender_id')
  final String? senderId;
  @JsonKey(name: 'partnership_id')
  final String? partnershipId;
  @JsonKey(name: 'source_notification_id')
  final String? sourceNotificationId;
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  Map<String, dynamic> toJson() => _$AccountabilityInAppHintInfoToJson(this);
}

@JsonSerializable()
class PendingPoliciesSummaryInfo {
  PendingPoliciesSummaryInfo({
    required this.count,
    this.nextTriggerAt,
    this.policyIds = const [],
  });

  factory PendingPoliciesSummaryInfo.fromJson(Map<String, dynamic> json) =>
      _$PendingPoliciesSummaryInfoFromJson(json);

  final int count;
  @JsonKey(name: 'next_trigger_at')
  final DateTime? nextTriggerAt;
  @JsonKey(name: 'policy_ids')
  final List<String> policyIds;

  Map<String, dynamic> toJson() => _$PendingPoliciesSummaryInfoToJson(this);
}

@JsonSerializable()
class RecentReflectionsSummaryInfo {
  RecentReflectionsSummaryInfo({
    required this.count,
    this.lastCategory,
    this.lastAt,
  });

  factory RecentReflectionsSummaryInfo.fromJson(Map<String, dynamic> json) =>
      _$RecentReflectionsSummaryInfoFromJson(json);

  final int count;
  @JsonKey(name: 'last_category')
  final String? lastCategory;
  @JsonKey(name: 'last_at')
  final DateTime? lastAt;

  Map<String, dynamic> toJson() => _$RecentReflectionsSummaryInfoToJson(this);
}

@JsonSerializable()
class ForesightConfidenceInfo {
  ForesightConfidenceInfo({
    required this.dim,
    required this.confidence,
  });

  factory ForesightConfidenceInfo.fromJson(Map<String, dynamic> json) =>
      _$ForesightConfidenceInfoFromJson(json);

  final String dim;
  final double confidence;

  Map<String, dynamic> toJson() => _$ForesightConfidenceInfoToJson(this);
}

@JsonSerializable()
class ForesightHintSummaryInfo {
  ForesightHintSummaryInfo({
    required this.deviationCount,
    this.hintText,
    this.generatedAt,
    this.attractorConfidences = const [],
  });

  factory ForesightHintSummaryInfo.fromJson(Map<String, dynamic> json) =>
      _$ForesightHintSummaryInfoFromJson(json);

  @JsonKey(name: 'hint_text')
  final String? hintText;
  @JsonKey(name: 'generated_at')
  final DateTime? generatedAt;
  @JsonKey(name: 'deviation_count')
  final int deviationCount;
  @JsonKey(name: 'attractor_confidences')
  final List<ForesightConfidenceInfo> attractorConfidences;

  Map<String, dynamic> toJson() => _$ForesightHintSummaryInfoToJson(this);
}

@JsonSerializable()
class AccountabilityDashboardInfo {
  AccountabilityDashboardInfo({
    required this.partnership,
    required this.stats,
    this.pendingPolicies,
    this.recentReflections,
    this.foresightHint,
    this.timeline = const [],
    this.heatmap = const {},
    this.achievements = const {},
    this.leaderboardSummary = const {},
    this.relationshipSummary = const {},
    this.recentShares = const [],
    this.quickActions = const {},
  });

  factory AccountabilityDashboardInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityDashboardInfoFromJson(json);

  final AccountabilityPartnershipInfo partnership;
  final AccountabilityStatsInfo stats;
  @JsonKey(name: 'pending_policies')
  final PendingPoliciesSummaryInfo? pendingPolicies;
  @JsonKey(name: 'recent_reflections')
  final RecentReflectionsSummaryInfo? recentReflections;
  @JsonKey(name: 'foresight_hint')
  final ForesightHintSummaryInfo? foresightHint;
  final List<AccountabilityCheckinInfo> timeline;
  final Map<String, dynamic> heatmap;
  final Map<String, dynamic> achievements;
  @JsonKey(name: 'leaderboard_summary')
  final Map<String, dynamic> leaderboardSummary;
  @JsonKey(name: 'relationship_summary')
  final Map<String, dynamic> relationshipSummary;
  @JsonKey(name: 'recent_shares')
  final List<Map<String, dynamic>> recentShares;
  @JsonKey(name: 'quick_actions')
  final Map<String, dynamic> quickActions;

  Map<String, dynamic> toJson() => _$AccountabilityDashboardInfoToJson(this);
}
