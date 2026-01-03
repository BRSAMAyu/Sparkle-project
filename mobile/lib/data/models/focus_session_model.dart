import 'package:freezed_annotation/freezed_annotation.dart';

part 'focus_session_model.freezed.dart';
part 'focus_session_model.g.dart';

/// Focus session request (P0.3: Backend persistence)
@freezed
class FocusSessionRequest with _$FocusSessionRequest {
  const factory FocusSessionRequest({
    @JsonKey(name: 'start_time') required DateTime startTime, @JsonKey(name: 'end_time') required DateTime endTime, @JsonKey(name: 'duration_minutes') required int durationMinutes, @JsonKey(name: 'focus_type') required String focusType, required String status, @JsonKey(name: 'task_id') String? taskId,
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
