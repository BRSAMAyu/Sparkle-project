// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'focus_session_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$FocusSessionRequestImpl _$$FocusSessionRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$FocusSessionRequestImpl(
      taskId: json['task_id'] as String?,
      startTime: DateTime.parse(json['start_time'] as String),
      endTime: DateTime.parse(json['end_time'] as String),
      durationMinutes: (json['duration_minutes'] as num).toInt(),
      focusType: json['focus_type'] as String,
      status: json['status'] as String,
      whiteNoiseType: json['white_noise_type'] as String?,
    );

Map<String, dynamic> _$$FocusSessionRequestImplToJson(
        _$FocusSessionRequestImpl instance) =>
    <String, dynamic>{
      'task_id': instance.taskId,
      'start_time': instance.startTime.toIso8601String(),
      'end_time': instance.endTime.toIso8601String(),
      'duration_minutes': instance.durationMinutes,
      'focus_type': instance.focusType,
      'status': instance.status,
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
