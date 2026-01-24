// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_session_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$FocusSessionRequestImpl _$$FocusSessionRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionRequestImpl(
      startTime: DateTime.parse(json['start_time'] as String),
      endTime: DateTime.parse(json['end_time'] as String),
      durationMinutes: (json['duration_minutes'] as num).toInt(),
      focusType: json['focus_type'] as String,
      status: json['status'] as String,
      taskId: json['task_id'] as String?,
      whiteNoiseType: json['white_noise_type'] as String?,
    );

Map<String, dynamic> _$$FocusSessionRequestImplToJson(
        _$FocusSessionRequestImpl instance) =>
    <String, dynamic>{
      'start_time': instance.startTime.toIso8601String(),
      'end_time': instance.endTime.toIso8601String(),
      'duration_minutes': instance.durationMinutes,
      'focus_type': instance.focusType,
      'status': instance.status,
      'task_id': instance.taskId,
      'white_noise_type': instance.whiteNoiseType,
    };

_$FocusSessionRewardsImpl _$$FocusSessionRewardsImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionRewardsImpl(
      flameEarned: (json['flame_earned'] as num).toInt(),
      leveledUp: json['leveled_up'] as bool,
      newLevel: (json['new_level'] as num).toInt(),
    );

Map<String, dynamic> _$$FocusSessionRewardsImplToJson(
        _$FocusSessionRewardsImpl instance) =>
    <String, dynamic>{
      'flame_earned': instance.flameEarned,
      'leveled_up': instance.leveledUp,
      'new_level': instance.newLevel,
    };

_$FocusSessionResponseImpl _$$FocusSessionResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionResponseImpl(
      success: json['success'] as bool,
      id: json['id'] as String,
      rewards:
          FocusSessionRewards.fromJson(json['rewards'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$$FocusSessionResponseImplToJson(
        _$FocusSessionResponseImpl instance) =>
    <String, dynamic>{
      'success': instance.success,
      'id': instance.id,
      'rewards': instance.rewards,
    };

_$FocusStatsResponseImpl _$$FocusStatsResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusStatsResponseImpl(
      totalMinutes: (json['total_minutes'] as num).toInt(),
      pomodoroCount: (json['pomodoro_count'] as num).toInt(),
      todayDate: json['today_date'] as String,
    );

Map<String, dynamic> _$$FocusStatsResponseImplToJson(
        _$FocusStatsResponseImpl instance) =>
    <String, dynamic>{
      'total_minutes': instance.totalMinutes,
      'pomodoro_count': instance.pomodoroCount,
      'today_date': instance.todayDate,
    };

_$DailyFocusStatsImpl _$$DailyFocusStatsImplFromJson(
        Map<String, dynamic> json) =>
    _$DailyFocusStatsImpl(
      date: json['date'] as String,
      minutes: (json['minutes'] as num).toInt(),
      sessionCount: (json['session_count'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$DailyFocusStatsImplToJson(
        _$DailyFocusStatsImpl instance) =>
    <String, dynamic>{
      'date': instance.date,
      'minutes': instance.minutes,
      'session_count': instance.sessionCount,
    };

_$FocusWeeklyStatsResponseImpl _$$FocusWeeklyStatsResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusWeeklyStatsResponseImpl(
      periodStart: json['period_start'] as String,
      periodEnd: json['period_end'] as String,
      totalMinutes: (json['total_minutes'] as num).toInt(),
      sessionCount: (json['session_count'] as num).toInt(),
      avgDuration: (json['avg_duration'] as num).toInt(),
      bestDay: json['best_day'] as String?,
      dailyBreakdown: Map<String, int>.from(json['daily_breakdown'] as Map),
      focusTypeDistribution:
          Map<String, int>.from(json['focus_type_distribution'] as Map),
      streakDays: (json['streak_days'] as num).toInt(),
      longestStreak: (json['longest_streak'] as num).toInt(),
    );

Map<String, dynamic> _$$FocusWeeklyStatsResponseImplToJson(
        _$FocusWeeklyStatsResponseImpl instance) =>
    <String, dynamic>{
      'period_start': instance.periodStart,
      'period_end': instance.periodEnd,
      'total_minutes': instance.totalMinutes,
      'session_count': instance.sessionCount,
      'avg_duration': instance.avgDuration,
      'best_day': instance.bestDay,
      'daily_breakdown': instance.dailyBreakdown,
      'focus_type_distribution': instance.focusTypeDistribution,
      'streak_days': instance.streakDays,
      'longest_streak': instance.longestStreak,
    };

_$FocusMonthlyStatsResponseImpl _$$FocusMonthlyStatsResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusMonthlyStatsResponseImpl(
      periodStart: json['period_start'] as String,
      periodEnd: json['period_end'] as String,
      totalMinutes: (json['total_minutes'] as num).toInt(),
      sessionCount: (json['session_count'] as num).toInt(),
      avgDuration: (json['avg_duration'] as num).toInt(),
      bestDay: json['best_day'] as String?,
      dailyBreakdown: Map<String, int>.from(json['daily_breakdown'] as Map),
      weeklyBreakdown: Map<String, int>.from(json['weekly_breakdown'] as Map),
      focusTypeDistribution:
          Map<String, int>.from(json['focus_type_distribution'] as Map),
      streakDays: (json['streak_days'] as num).toInt(),
      longestStreak: (json['longest_streak'] as num).toInt(),
    );

Map<String, dynamic> _$$FocusMonthlyStatsResponseImplToJson(
        _$FocusMonthlyStatsResponseImpl instance) =>
    <String, dynamic>{
      'period_start': instance.periodStart,
      'period_end': instance.periodEnd,
      'total_minutes': instance.totalMinutes,
      'session_count': instance.sessionCount,
      'avg_duration': instance.avgDuration,
      'best_day': instance.bestDay,
      'daily_breakdown': instance.dailyBreakdown,
      'weekly_breakdown': instance.weeklyBreakdown,
      'focus_type_distribution': instance.focusTypeDistribution,
      'streak_days': instance.streakDays,
      'longest_streak': instance.longestStreak,
    };

_$FocusSessionDetailImpl _$$FocusSessionDetailImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionDetailImpl(
      id: json['id'] as String,
      startTime: DateTime.parse(json['start_time'] as String),
      endTime: DateTime.parse(json['end_time'] as String),
      durationMinutes: (json['duration_minutes'] as num).toInt(),
      focusType: json['focus_type'] as String,
      status: json['status'] as String,
      taskId: json['task_id'] as String?,
      taskTitle: json['task_title'] as String?,
      whiteNoiseType: (json['white_noise_type'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$FocusSessionDetailImplToJson(
        _$FocusSessionDetailImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'start_time': instance.startTime.toIso8601String(),
      'end_time': instance.endTime.toIso8601String(),
      'duration_minutes': instance.durationMinutes,
      'focus_type': instance.focusType,
      'status': instance.status,
      'task_id': instance.taskId,
      'task_title': instance.taskTitle,
      'white_noise_type': instance.whiteNoiseType,
    };

_$FocusSessionHistoryResponseImpl _$$FocusSessionHistoryResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionHistoryResponseImpl(
      sessions: (json['sessions'] as List<dynamic>)
          .map((e) => FocusSessionDetail.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCount: (json['total_count'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
      offset: (json['offset'] as num).toInt(),
    );

Map<String, dynamic> _$$FocusSessionHistoryResponseImplToJson(
        _$FocusSessionHistoryResponseImpl instance) =>
    <String, dynamic>{
      'sessions': instance.sessions,
      'total_count': instance.totalCount,
      'limit': instance.limit,
      'offset': instance.offset,
    };

_$FocusHeatmapResponseImpl _$$FocusHeatmapResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusHeatmapResponseImpl(
      data: (json['data'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toDouble()),
      ),
    );

Map<String, dynamic> _$$FocusHeatmapResponseImplToJson(
        _$FocusHeatmapResponseImpl instance) =>
    <String, dynamic>{
      'data': instance.data,
    };
