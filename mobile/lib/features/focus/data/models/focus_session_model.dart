import 'package:freezed_annotation/freezed_annotation.dart';

part 'focus_session_model.freezed.dart';
part 'focus_session_model.g.dart';

/// Focus session request (P0.3: Backend persistence)
@freezed
class FocusSessionRequest with _$FocusSessionRequest {
  const factory FocusSessionRequest({
    @JsonKey(name: 'start_time') required DateTime startTime,
    @JsonKey(name: 'end_time') required DateTime endTime,
    @JsonKey(name: 'duration_minutes') required int durationMinutes,
    @JsonKey(name: 'focus_type') required String focusType,
    required String status,
    @JsonKey(name: 'task_id') String? taskId,
    @JsonKey(name: 'white_noise_type') String? whiteNoiseType,
  }) = _FocusSessionRequest;

  factory FocusSessionRequest.fromJson(Map<String, dynamic> json) =>
      _$FocusSessionRequestFromJson(json);
}

/// Focus session rewards
@freezed
class FocusSessionRewards with _$FocusSessionRewards {
  const factory FocusSessionRewards({
    @JsonKey(name: 'flame_earned') required int flameEarned,
    @JsonKey(name: 'leveled_up') required bool leveledUp,
    @JsonKey(name: 'new_level') required int newLevel,
  }) = _FocusSessionRewards;

  factory FocusSessionRewards.fromJson(Map<String, dynamic> json) =>
      _$FocusSessionRewardsFromJson(json);
}

/// Focus session response
@freezed
class FocusSessionResponse with _$FocusSessionResponse {
  const factory FocusSessionResponse({
    required bool success,
    required String id,
    required FocusSessionRewards rewards,
  }) = _FocusSessionResponse;

  factory FocusSessionResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusSessionResponseFromJson(json);
}

/// Focus stats response
@freezed
class FocusStatsResponse with _$FocusStatsResponse {
  const factory FocusStatsResponse({
    @JsonKey(name: 'total_minutes') required int totalMinutes,
    @JsonKey(name: 'pomodoro_count') required int pomodoroCount,
    @JsonKey(name: 'today_date') required String todayDate,
  }) = _FocusStatsResponse;

  factory FocusStatsResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusStatsResponseFromJson(json);
}

/// Daily focus stats for breakdown
@freezed
class DailyFocusStats with _$DailyFocusStats {
  const factory DailyFocusStats({
    required String date,
    required int minutes,
    @JsonKey(name: 'session_count') int? sessionCount,
  }) = _DailyFocusStats;

  factory DailyFocusStats.fromJson(Map<String, dynamic> json) =>
      _$DailyFocusStatsFromJson(json);
}

/// Weekly focus stats response
@freezed
class FocusWeeklyStatsResponse with _$FocusWeeklyStatsResponse {
  const factory FocusWeeklyStatsResponse({
    @JsonKey(name: 'period_start') required String periodStart,
    @JsonKey(name: 'period_end') required String periodEnd,
    @JsonKey(name: 'total_minutes') required int totalMinutes,
    @JsonKey(name: 'session_count') required int sessionCount,
    @JsonKey(name: 'avg_duration') required int avgDuration,
    @JsonKey(name: 'daily_breakdown') required Map<String, int> dailyBreakdown, @JsonKey(name: 'focus_type_distribution') required Map<String, int> focusTypeDistribution, @JsonKey(name: 'streak_days') required int streakDays, @JsonKey(name: 'longest_streak') required int longestStreak, @JsonKey(name: 'best_day') String? bestDay,
  }) = _FocusWeeklyStatsResponse;

  factory FocusWeeklyStatsResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusWeeklyStatsResponseFromJson(json);
}

/// Monthly focus stats response
@freezed
class FocusMonthlyStatsResponse with _$FocusMonthlyStatsResponse {
  const factory FocusMonthlyStatsResponse({
    @JsonKey(name: 'period_start') required String periodStart,
    @JsonKey(name: 'period_end') required String periodEnd,
    @JsonKey(name: 'total_minutes') required int totalMinutes,
    @JsonKey(name: 'session_count') required int sessionCount,
    @JsonKey(name: 'avg_duration') required int avgDuration,
    @JsonKey(name: 'daily_breakdown') required Map<String, int> dailyBreakdown, @JsonKey(name: 'weekly_breakdown') required Map<String, int> weeklyBreakdown, @JsonKey(name: 'focus_type_distribution') required Map<String, int> focusTypeDistribution, @JsonKey(name: 'streak_days') required int streakDays, @JsonKey(name: 'longest_streak') required int longestStreak, @JsonKey(name: 'best_day') String? bestDay,
  }) = _FocusMonthlyStatsResponse;

  factory FocusMonthlyStatsResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusMonthlyStatsResponseFromJson(json);
}

/// Focus session detail
@freezed
class FocusSessionDetail with _$FocusSessionDetail {
  const factory FocusSessionDetail({
    required String id,
    @JsonKey(name: 'start_time') required DateTime startTime,
    @JsonKey(name: 'end_time') required DateTime endTime,
    @JsonKey(name: 'duration_minutes') required int durationMinutes,
    @JsonKey(name: 'focus_type') required String focusType,
    required String status,
    @JsonKey(name: 'task_id') String? taskId,
    @JsonKey(name: 'task_title') String? taskTitle,
    @JsonKey(name: 'white_noise_type') int? whiteNoiseType,
  }) = _FocusSessionDetail;

  factory FocusSessionDetail.fromJson(Map<String, dynamic> json) =>
      _$FocusSessionDetailFromJson(json);
}

/// Focus session history response
@freezed
class FocusSessionHistoryResponse with _$FocusSessionHistoryResponse {
  const factory FocusSessionHistoryResponse({
    required List<FocusSessionDetail> sessions,
    @JsonKey(name: 'total_count') required int totalCount,
    required int limit,
    required int offset,
  }) = _FocusSessionHistoryResponse;

  factory FocusSessionHistoryResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusSessionHistoryResponseFromJson(json);
}

/// Focus heatmap data response
@freezed
class FocusHeatmapResponse with _$FocusHeatmapResponse {
  const factory FocusHeatmapResponse({
    required Map<String, double> data,
  }) = _FocusHeatmapResponse;

  factory FocusHeatmapResponse.fromJson(Map<String, dynamic> json) =>
      _$FocusHeatmapResponseFromJson(json);
}
