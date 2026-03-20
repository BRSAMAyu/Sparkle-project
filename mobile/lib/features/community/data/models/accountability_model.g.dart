// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'accountability_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AccountabilityPartnershipInfo _$AccountabilityPartnershipInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityPartnershipInfo(
      id: json['id'] as String,
      initiatorId: json['initiator_id'] as String,
      partnerId: json['partner_id'] as String,
      initiatorGoal: json['initiator_goal'] as String,
      checkInDays: (json['check_in_days'] as num).toInt(),
      slotType: json['slot_type'] as String? ?? 'core',
      status: $enumDecode(_$AccountabilityStatusEnumMap, json['status']),
      createdAt: DateTime.parse(json['created_at'] as String),
      partnerGoal: json['partner_goal'] as String?,
      startedAt: json['started_at'] == null
          ? null
          : DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] == null
          ? null
          : DateTime.parse(json['ended_at'] as String),
      initiator: json['initiator'] == null
          ? null
          : UserBrief.fromJson(json['initiator'] as Map<String, dynamic>),
      partner: json['partner'] == null
          ? null
          : UserBrief.fromJson(json['partner'] as Map<String, dynamic>),
      myCheckedInToday: json['my_checked_in_today'] as bool?,
      partnerCheckedInToday: json['partner_checked_in_today'] as bool?,
      lastCheckinAt: json['last_checkin_at'] == null
          ? null
          : DateTime.parse(json['last_checkin_at'] as String),
    );

Map<String, dynamic> _$AccountabilityPartnershipInfoToJson(
        AccountabilityPartnershipInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'initiator_id': instance.initiatorId,
      'partner_id': instance.partnerId,
      'initiator_goal': instance.initiatorGoal,
      'partner_goal': instance.partnerGoal,
      'check_in_days': instance.checkInDays,
      'slot_type': instance.slotType,
      'status': _$AccountabilityStatusEnumMap[instance.status]!,
      'started_at': instance.startedAt?.toIso8601String(),
      'ended_at': instance.endedAt?.toIso8601String(),
      'created_at': instance.createdAt.toIso8601String(),
      'initiator': instance.initiator,
      'partner': instance.partner,
      'my_checked_in_today': instance.myCheckedInToday,
      'partner_checked_in_today': instance.partnerCheckedInToday,
      'last_checkin_at': instance.lastCheckinAt?.toIso8601String(),
    };

const _$AccountabilityStatusEnumMap = {
  AccountabilityStatus.pending: 'pending',
  AccountabilityStatus.active: 'active',
  AccountabilityStatus.paused: 'paused',
  AccountabilityStatus.ended: 'ended',
};

AccountabilityCheckinInfo _$AccountabilityCheckinInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityCheckinInfo(
      id: json['id'] as String,
      partnershipId: json['partnership_id'] as String,
      userId: json['user_id'] as String,
      content: json['content'] as String,
      mood: (json['mood'] as num).toInt(),
      minutes: (json['minutes'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      author: json['author'] == null
          ? null
          : UserBrief.fromJson(json['author'] as Map<String, dynamic>),
      likes: (json['likes'] as num?)?.toInt() ?? 0,
      encouragements: (json['encouragements'] as List<dynamic>?)
              ?.map((e) =>
                  EncouragementMessage.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$AccountabilityCheckinInfoToJson(
        AccountabilityCheckinInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'partnership_id': instance.partnershipId,
      'user_id': instance.userId,
      'content': instance.content,
      'mood': instance.mood,
      'minutes': instance.minutes,
      'created_at': instance.createdAt.toIso8601String(),
      'author': instance.author,
      'likes': instance.likes,
      'encouragements': instance.encouragements,
    };

EncouragementMessage _$EncouragementMessageFromJson(
        Map<String, dynamic> json) =>
    EncouragementMessage(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      message: json['message'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$EncouragementMessageToJson(
        EncouragementMessage instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'message': instance.message,
      'created_at': instance.createdAt.toIso8601String(),
    };

AccountabilityStatsInfo _$AccountabilityStatsInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityStatsInfo(
      myStreakDays: (json['my_streak_days'] as num).toInt(),
      partnerStreakDays: (json['partner_streak_days'] as num).toInt(),
      myCheckedInToday: json['my_checked_in_today'] as bool,
      partnerCheckedInToday: json['partner_checked_in_today'] as bool,
      totalCheckins: (json['total_checkins'] as num).toInt(),
    );

Map<String, dynamic> _$AccountabilityStatsInfoToJson(
        AccountabilityStatsInfo instance) =>
    <String, dynamic>{
      'my_streak_days': instance.myStreakDays,
      'partner_streak_days': instance.partnerStreakDays,
      'my_checked_in_today': instance.myCheckedInToday,
      'partner_checked_in_today': instance.partnerCheckedInToday,
      'total_checkins': instance.totalCheckins,
    };

AccountabilityOverviewInfo _$AccountabilityOverviewInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityOverviewInfo(
      slotType: json['slot_type'] as String,
      activePartnership: json['active_partnership'] == null
          ? null
          : AccountabilityPartnershipInfo.fromJson(
              json['active_partnership'] as Map<String, dynamic>,
            ),
      pendingPartnerships: (json['pending_partnerships'] as List<dynamic>?)
              ?.map((e) => AccountabilityPartnershipInfo.fromJson(
                  e as Map<String, dynamic>))
              .toList() ??
          const [],
      achievementsSummary:
          (json['achievements_summary'] as Map?)?.cast<String, dynamic>() ??
              const {},
      leaderboardSummary:
          (json['leaderboard_summary'] as Map?)?.cast<String, dynamic>() ??
              const {},
      relationshipSummary:
          (json['relationship_summary'] as Map?)?.cast<String, dynamic>(),
      quickActions:
          (json['quick_actions'] as Map?)?.cast<String, dynamic>() ?? const {},
    );

Map<String, dynamic> _$AccountabilityOverviewInfoToJson(
        AccountabilityOverviewInfo instance) =>
    <String, dynamic>{
      'slot_type': instance.slotType,
      'active_partnership': instance.activePartnership,
      'pending_partnerships': instance.pendingPartnerships,
      'achievements_summary': instance.achievementsSummary,
      'leaderboard_summary': instance.leaderboardSummary,
      'relationship_summary': instance.relationshipSummary,
      'quick_actions': instance.quickActions,
    };

AccountabilityDashboardInfo _$AccountabilityDashboardInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityDashboardInfo(
      partnership: AccountabilityPartnershipInfo.fromJson(
          json['partnership'] as Map<String, dynamic>),
      stats: AccountabilityStatsInfo.fromJson(
          json['stats'] as Map<String, dynamic>),
      timeline: (json['timeline'] as List<dynamic>?)
              ?.map((e) =>
                  AccountabilityCheckinInfo.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      heatmap: (json['heatmap'] as Map?)?.cast<String, dynamic>() ?? const {},
      achievements:
          (json['achievements'] as Map?)?.cast<String, dynamic>() ?? const {},
      leaderboardSummary:
          (json['leaderboard_summary'] as Map?)?.cast<String, dynamic>() ??
              const {},
      relationshipSummary:
          (json['relationship_summary'] as Map?)?.cast<String, dynamic>() ??
              const {},
      recentShares: (json['recent_shares'] as List<dynamic>?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          const [],
      quickActions:
          (json['quick_actions'] as Map?)?.cast<String, dynamic>() ?? const {},
    );

Map<String, dynamic> _$AccountabilityDashboardInfoToJson(
        AccountabilityDashboardInfo instance) =>
    <String, dynamic>{
      'partnership': instance.partnership,
      'stats': instance.stats,
      'timeline': instance.timeline,
      'heatmap': instance.heatmap,
      'achievements': instance.achievements,
      'leaderboard_summary': instance.leaderboardSummary,
      'relationship_summary': instance.relationshipSummary,
      'recent_shares': instance.recentShares,
      'quick_actions': instance.quickActions,
    };
