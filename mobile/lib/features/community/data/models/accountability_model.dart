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
    this.partnerCheckedInToday,
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

  // Runtime stats (not from API, loaded separately)
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? myStreakDays;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? partnerStreakDays;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final bool? partnerCheckedInToday;

  Map<String, dynamic> toJson() =>
      _$AccountabilityPartnershipInfoToJson(this);

  AccountabilityPartnershipInfo copyWithStats({
    int? myStreakDays,
    int? partnerStreakDays,
    bool? partnerCheckedInToday,
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
        partnerCheckedInToday:
            partnerCheckedInToday ?? this.partnerCheckedInToday,
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

  Map<String, dynamic> toJson() => _$AccountabilityCheckinInfoToJson(this);
}

@JsonSerializable()
class AccountabilityStatsInfo {
  AccountabilityStatsInfo({
    required this.myStreakDays,
    required this.partnerStreakDays,
    required this.partnerCheckedInToday,
    required this.totalCheckins,
  });

  factory AccountabilityStatsInfo.fromJson(Map<String, dynamic> json) =>
      _$AccountabilityStatsInfoFromJson(json);

  @JsonKey(name: 'my_streak_days')
  final int myStreakDays;
  @JsonKey(name: 'partner_streak_days')
  final int partnerStreakDays;
  @JsonKey(name: 'partner_checked_in_today')
  final bool partnerCheckedInToday;
  @JsonKey(name: 'total_checkins')
  final int totalCheckins;

  Map<String, dynamic> toJson() => _$AccountabilityStatsInfoToJson(this);
}
