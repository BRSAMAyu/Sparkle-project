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
      likes: (json['likes'] as num?)?.toInt() ?? 0,
      encouragements: (json['encouragements'] as List<dynamic>?)
              ?.map((e) =>
                  EncouragementMessage.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      author: json['author'] == null
          ? null
          : UserBrief.fromJson(json['author'] as Map<String, dynamic>),
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
              json['active_partnership'] as Map<String, dynamic>),
      pendingPartnerships: (json['pending_partnerships'] as List<dynamic>?)
              ?.map((e) => AccountabilityPartnershipInfo.fromJson(
                  e as Map<String, dynamic>))
              .toList() ??
          const [],
      achievementsSummary:
          json['achievements_summary'] as Map<String, dynamic>? ?? const {},
      leaderboardSummary:
          json['leaderboard_summary'] as Map<String, dynamic>? ?? const {},
      relationshipSummary:
          json['relationship_summary'] as Map<String, dynamic>?,
      quickActions: json['quick_actions'] as Map<String, dynamic>? ?? const {},
      inAppHints: (json['in_app_hints'] as List<dynamic>?)
              ?.map((e) => AccountabilityInAppHintInfo.fromJson(
                  e as Map<String, dynamic>))
              .toList() ??
          const [],
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
      'in_app_hints': instance.inAppHints,
    };

AccountabilityInAppHintInfo _$AccountabilityInAppHintInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityInAppHintInfo(
      id: json['id'] as String,
      message: json['message'] as String,
      type: json['type'] as String?,
      senderName: json['sender_name'] as String?,
      senderId: json['sender_id'] as String?,
      partnershipId: json['partnership_id'] as String?,
      sourceNotificationId: json['source_notification_id'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$AccountabilityInAppHintInfoToJson(
        AccountabilityInAppHintInfo instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'message': instance.message,
      'sender_name': instance.senderName,
      'sender_id': instance.senderId,
      'partnership_id': instance.partnershipId,
      'source_notification_id': instance.sourceNotificationId,
      'created_at': instance.createdAt?.toIso8601String(),
    };

PendingPoliciesSummaryInfo _$PendingPoliciesSummaryInfoFromJson(
        Map<String, dynamic> json) =>
    PendingPoliciesSummaryInfo(
      count: (json['count'] as num).toInt(),
      nextTriggerAt: json['next_trigger_at'] == null
          ? null
          : DateTime.parse(json['next_trigger_at'] as String),
      policyIds: (json['policy_ids'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
    );

Map<String, dynamic> _$PendingPoliciesSummaryInfoToJson(
        PendingPoliciesSummaryInfo instance) =>
    <String, dynamic>{
      'count': instance.count,
      'next_trigger_at': instance.nextTriggerAt?.toIso8601String(),
      'policy_ids': instance.policyIds,
    };

RecentReflectionsSummaryInfo _$RecentReflectionsSummaryInfoFromJson(
        Map<String, dynamic> json) =>
    RecentReflectionsSummaryInfo(
      count: (json['count'] as num).toInt(),
      lastCategory: json['last_category'] as String?,
      lastAt: json['last_at'] == null
          ? null
          : DateTime.parse(json['last_at'] as String),
    );

Map<String, dynamic> _$RecentReflectionsSummaryInfoToJson(
        RecentReflectionsSummaryInfo instance) =>
    <String, dynamic>{
      'count': instance.count,
      'last_category': instance.lastCategory,
      'last_at': instance.lastAt?.toIso8601String(),
    };

ForesightConfidenceInfo _$ForesightConfidenceInfoFromJson(
        Map<String, dynamic> json) =>
    ForesightConfidenceInfo(
      dim: json['dim'] as String,
      confidence: (json['confidence'] as num).toDouble(),
    );

Map<String, dynamic> _$ForesightConfidenceInfoToJson(
        ForesightConfidenceInfo instance) =>
    <String, dynamic>{
      'dim': instance.dim,
      'confidence': instance.confidence,
    };

ForesightHintSummaryInfo _$ForesightHintSummaryInfoFromJson(
        Map<String, dynamic> json) =>
    ForesightHintSummaryInfo(
      deviationCount: (json['deviation_count'] as num).toInt(),
      hintText: json['hint_text'] as String?,
      generatedAt: json['generated_at'] == null
          ? null
          : DateTime.parse(json['generated_at'] as String),
      attractorConfidences: (json['attractor_confidences'] as List<dynamic>?)
              ?.map((e) =>
                  ForesightConfidenceInfo.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$ForesightHintSummaryInfoToJson(
        ForesightHintSummaryInfo instance) =>
    <String, dynamic>{
      'hint_text': instance.hintText,
      'generated_at': instance.generatedAt?.toIso8601String(),
      'deviation_count': instance.deviationCount,
      'attractor_confidences': instance.attractorConfidences,
    };

AccountabilityDashboardInfo _$AccountabilityDashboardInfoFromJson(
        Map<String, dynamic> json) =>
    AccountabilityDashboardInfo(
      partnership: AccountabilityPartnershipInfo.fromJson(
          json['partnership'] as Map<String, dynamic>),
      stats: AccountabilityStatsInfo.fromJson(
          json['stats'] as Map<String, dynamic>),
      pendingPolicies: json['pending_policies'] == null
          ? null
          : PendingPoliciesSummaryInfo.fromJson(
              json['pending_policies'] as Map<String, dynamic>),
      recentReflections: json['recent_reflections'] == null
          ? null
          : RecentReflectionsSummaryInfo.fromJson(
              json['recent_reflections'] as Map<String, dynamic>),
      foresightHint: json['foresight_hint'] == null
          ? null
          : ForesightHintSummaryInfo.fromJson(
              json['foresight_hint'] as Map<String, dynamic>),
      timeline: (json['timeline'] as List<dynamic>?)
              ?.map((e) =>
                  AccountabilityCheckinInfo.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      heatmap: json['heatmap'] as Map<String, dynamic>? ?? const {},
      achievements: json['achievements'] as Map<String, dynamic>? ?? const {},
      leaderboardSummary:
          json['leaderboard_summary'] as Map<String, dynamic>? ?? const {},
      relationshipSummary:
          json['relationship_summary'] as Map<String, dynamic>? ?? const {},
      recentShares: (json['recent_shares'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
      quickActions: json['quick_actions'] as Map<String, dynamic>? ?? const {},
    );

Map<String, dynamic> _$AccountabilityDashboardInfoToJson(
        AccountabilityDashboardInfo instance) =>
    <String, dynamic>{
      'partnership': instance.partnership,
      'stats': instance.stats,
      'pending_policies': instance.pendingPolicies,
      'recent_reflections': instance.recentReflections,
      'foresight_hint': instance.foresightHint,
      'timeline': instance.timeline,
      'heatmap': instance.heatmap,
      'achievements': instance.achievements,
      'leaderboard_summary': instance.leaderboardSummary,
      'relationship_summary': instance.relationshipSummary,
      'recent_shares': instance.recentShares,
      'quick_actions': instance.quickActions,
    };
