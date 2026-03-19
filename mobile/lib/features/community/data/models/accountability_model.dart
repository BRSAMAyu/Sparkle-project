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

  Map<String, dynamic> toJson() =>
      _$AccountabilityPartnershipInfoToJson(this);

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
