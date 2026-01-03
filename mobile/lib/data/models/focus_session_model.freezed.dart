// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'focus_session_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

FocusSessionRequest _$FocusSessionRequestFromJson(Map<String, dynamic> json) {
  return _FocusSessionRequest.fromJson(json);
}

/// @nodoc
mixin _$FocusSessionRequest {
  @JsonKey(name: 'task_id')
  String? get taskId => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_time')
  DateTime get startTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_time')
  DateTime get endTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'duration_minutes')
  int get durationMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'focus_type')
  String get focusType => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'white_noise_type')
  String? get whiteNoiseType => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusSessionRequestCopyWith<FocusSessionRequest> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusSessionRequestCopyWith<$Res> {
  factory $FocusSessionRequestCopyWith(
          FocusSessionRequest value, $Res Function(FocusSessionRequest) then) =
      _$FocusSessionRequestCopyWithImpl<$Res, FocusSessionRequest>;
  @useResult
  $Res call(
      {@JsonKey(name: 'task_id') String? taskId,
      @JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'white_noise_type') String? whiteNoiseType});
}

/// @nodoc
class _$FocusSessionRequestCopyWithImpl<$Res, $Val extends FocusSessionRequest>
    implements $FocusSessionRequestCopyWith<$Res> {
  _$FocusSessionRequestCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? taskId = freezed,
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_value.copyWith(
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as DateTime,
      endTime: null == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as DateTime,
      durationMinutes: null == durationMinutes
          ? _value.durationMinutes
          : durationMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      focusType: null == focusType
          ? _value.focusType
          : focusType // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      whiteNoiseType: freezed == whiteNoiseType
          ? _value.whiteNoiseType
          : whiteNoiseType // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusSessionRequestImplCopyWith<$Res>
    implements $FocusSessionRequestCopyWith<$Res> {
  factory _$$FocusSessionRequestImplCopyWith(_$FocusSessionRequestImpl value,
          $Res Function(_$FocusSessionRequestImpl) then) =
      __$$FocusSessionRequestImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'task_id') String? taskId,
      @JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'white_noise_type') String? whiteNoiseType});
}

/// @nodoc
class __$$FocusSessionRequestImplCopyWithImpl<$Res>
    extends _$FocusSessionRequestCopyWithImpl<$Res, _$FocusSessionRequestImpl>
    implements _$$FocusSessionRequestImplCopyWith<$Res> {
  __$$FocusSessionRequestImplCopyWithImpl(_$FocusSessionRequestImpl _value,
      $Res Function(_$FocusSessionRequestImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? taskId = freezed,
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_$FocusSessionRequestImpl(
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
      startTime: null == startTime
          ? _value.startTime
          : startTime // ignore: cast_nullable_to_non_nullable
              as DateTime,
      endTime: null == endTime
          ? _value.endTime
          : endTime // ignore: cast_nullable_to_non_nullable
              as DateTime,
      durationMinutes: null == durationMinutes
          ? _value.durationMinutes
          : durationMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      focusType: null == focusType
          ? _value.focusType
          : focusType // ignore: cast_nullable_to_non_nullable
              as String,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      whiteNoiseType: freezed == whiteNoiseType
          ? _value.whiteNoiseType
          : whiteNoiseType // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusSessionRequestImpl implements _FocusSessionRequest {
  const _$FocusSessionRequestImpl(
      {@JsonKey(name: 'task_id') this.taskId,
      @JsonKey(name: 'start_time') required this.startTime,
      @JsonKey(name: 'end_time') required this.endTime,
      @JsonKey(name: 'duration_minutes') required this.durationMinutes,
      @JsonKey(name: 'focus_type') required this.focusType,
      required this.status,
      @JsonKey(name: 'white_noise_type') this.whiteNoiseType});

  factory _$FocusSessionRequestImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusSessionRequestImplFromJson(json);

  @override
  @JsonKey(name: 'task_id')
  final String? taskId;
  @override
  @JsonKey(name: 'start_time')
  final DateTime startTime;
  @override
  @JsonKey(name: 'end_time')
  final DateTime endTime;
  @override
  @JsonKey(name: 'duration_minutes')
  final int durationMinutes;
  @override
  @JsonKey(name: 'focus_type')
  final String focusType;
  @override
  final String status;
  @override
  @JsonKey(name: 'white_noise_type')
  final String? whiteNoiseType;

  @override
  String toString() {
    return 'FocusSessionRequest(taskId: $taskId, startTime: $startTime, endTime: $endTime, durationMinutes: $durationMinutes, focusType: $focusType, status: $status, whiteNoiseType: $whiteNoiseType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionRequestImpl &&
            (identical(other.taskId, taskId) || other.taskId == taskId) &&
            (identical(other.startTime, startTime) ||
                other.startTime == startTime) &&
            (identical(other.endTime, endTime) || other.endTime == endTime) &&
            (identical(other.durationMinutes, durationMinutes) ||
                other.durationMinutes == durationMinutes) &&
            (identical(other.focusType, focusType) ||
                other.focusType == focusType) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.whiteNoiseType, whiteNoiseType) ||
                other.whiteNoiseType == whiteNoiseType));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, taskId, startTime, endTime,
      durationMinutes, focusType, status, whiteNoiseType);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusSessionRequestImplCopyWith<_$FocusSessionRequestImpl> get copyWith =>
      __$$FocusSessionRequestImplCopyWithImpl<_$FocusSessionRequestImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusSessionRequestImplToJson(
      this,
    );
  }
}

abstract class _FocusSessionRequest implements FocusSessionRequest {
  const factory _FocusSessionRequest(
          {@JsonKey(name: 'task_id') final String? taskId,
          @JsonKey(name: 'start_time') required final DateTime startTime,
          @JsonKey(name: 'end_time') required final DateTime endTime,
          @JsonKey(name: 'duration_minutes') required final int durationMinutes,
          @JsonKey(name: 'focus_type') required final String focusType,
          required final String status,
          @JsonKey(name: 'white_noise_type') final String? whiteNoiseType}) =
      _$FocusSessionRequestImpl;

  factory _FocusSessionRequest.fromJson(Map<String, dynamic> json) =
      _$FocusSessionRequestImpl.fromJson;

  @override
  @JsonKey(name: 'task_id')
  String? get taskId;
  @override
  @JsonKey(name: 'start_time')
  DateTime get startTime;
  @override
  @JsonKey(name: 'end_time')
  DateTime get endTime;
  @override
  @JsonKey(name: 'duration_minutes')
  int get durationMinutes;
  @override
  @JsonKey(name: 'focus_type')
  String get focusType;
  @override
  String get status;
  @override
  @JsonKey(name: 'white_noise_type')
  String? get whiteNoiseType;
  @override
  @JsonKey(ignore: true)
  _$$FocusSessionRequestImplCopyWith<_$FocusSessionRequestImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

FocusSessionRewards _$FocusSessionRewardsFromJson(Map<String, dynamic> json) {
  return _FocusSessionRewards.fromJson(json);
}

/// @nodoc
mixin _$FocusSessionRewards {
  @JsonKey(name: 'flame_earned')
  int get flameEarned => throw _privateConstructorUsedError;
  @JsonKey(name: 'leveled_up')
  bool get leveledUp => throw _privateConstructorUsedError;
  @JsonKey(name: 'new_level')
  int get newLevel => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusSessionRewardsCopyWith<FocusSessionRewards> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusSessionRewardsCopyWith<$Res> {
  factory $FocusSessionRewardsCopyWith(
          FocusSessionRewards value, $Res Function(FocusSessionRewards) then) =
      _$FocusSessionRewardsCopyWithImpl<$Res, FocusSessionRewards>;
  @useResult
  $Res call(
      {@JsonKey(name: 'flame_earned') int flameEarned,
      @JsonKey(name: 'leveled_up') bool leveledUp,
      @JsonKey(name: 'new_level') int newLevel});
}

/// @nodoc
class _$FocusSessionRewardsCopyWithImpl<$Res, $Val extends FocusSessionRewards>
    implements $FocusSessionRewardsCopyWith<$Res> {
  _$FocusSessionRewardsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? flameEarned = null,
    Object? leveledUp = null,
    Object? newLevel = null,
  }) {
    return _then(_value.copyWith(
      flameEarned: null == flameEarned
          ? _value.flameEarned
          : flameEarned // ignore: cast_nullable_to_non_nullable
              as int,
      leveledUp: null == leveledUp
          ? _value.leveledUp
          : leveledUp // ignore: cast_nullable_to_non_nullable
              as bool,
      newLevel: null == newLevel
          ? _value.newLevel
          : newLevel // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusSessionRewardsImplCopyWith<$Res>
    implements $FocusSessionRewardsCopyWith<$Res> {
  factory _$$FocusSessionRewardsImplCopyWith(_$FocusSessionRewardsImpl value,
          $Res Function(_$FocusSessionRewardsImpl) then) =
      __$$FocusSessionRewardsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'flame_earned') int flameEarned,
      @JsonKey(name: 'leveled_up') bool leveledUp,
      @JsonKey(name: 'new_level') int newLevel});
}

/// @nodoc
class __$$FocusSessionRewardsImplCopyWithImpl<$Res>
    extends _$FocusSessionRewardsCopyWithImpl<$Res, _$FocusSessionRewardsImpl>
    implements _$$FocusSessionRewardsImplCopyWith<$Res> {
  __$$FocusSessionRewardsImplCopyWithImpl(_$FocusSessionRewardsImpl _value,
      $Res Function(_$FocusSessionRewardsImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? flameEarned = null,
    Object? leveledUp = null,
    Object? newLevel = null,
  }) {
    return _then(_$FocusSessionRewardsImpl(
      flameEarned: null == flameEarned
          ? _value.flameEarned
          : flameEarned // ignore: cast_nullable_to_non_nullable
              as int,
      leveledUp: null == leveledUp
          ? _value.leveledUp
          : leveledUp // ignore: cast_nullable_to_non_nullable
              as bool,
      newLevel: null == newLevel
          ? _value.newLevel
          : newLevel // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusSessionRewardsImpl implements _FocusSessionRewards {
  const _$FocusSessionRewardsImpl(
      {@JsonKey(name: 'flame_earned') required this.flameEarned,
      @JsonKey(name: 'leveled_up') required this.leveledUp,
      @JsonKey(name: 'new_level') required this.newLevel});

  factory _$FocusSessionRewardsImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusSessionRewardsImplFromJson(json);

  @override
  @JsonKey(name: 'flame_earned')
  final int flameEarned;
  @override
  @JsonKey(name: 'leveled_up')
  final bool leveledUp;
  @override
  @JsonKey(name: 'new_level')
  final int newLevel;

  @override
  String toString() {
    return 'FocusSessionRewards(flameEarned: $flameEarned, leveledUp: $leveledUp, newLevel: $newLevel)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionRewardsImpl &&
            (identical(other.flameEarned, flameEarned) ||
                other.flameEarned == flameEarned) &&
            (identical(other.leveledUp, leveledUp) ||
                other.leveledUp == leveledUp) &&
            (identical(other.newLevel, newLevel) ||
                other.newLevel == newLevel));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, flameEarned, leveledUp, newLevel);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusSessionRewardsImplCopyWith<_$FocusSessionRewardsImpl> get copyWith =>
      __$$FocusSessionRewardsImplCopyWithImpl<_$FocusSessionRewardsImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusSessionRewardsImplToJson(
      this,
    );
  }
}

abstract class _FocusSessionRewards implements FocusSessionRewards {
  const factory _FocusSessionRewards(
          {@JsonKey(name: 'flame_earned') required final int flameEarned,
          @JsonKey(name: 'leveled_up') required final bool leveledUp,
          @JsonKey(name: 'new_level') required final int newLevel}) =
      _$FocusSessionRewardsImpl;

  factory _FocusSessionRewards.fromJson(Map<String, dynamic> json) =
      _$FocusSessionRewardsImpl.fromJson;

  @override
  @JsonKey(name: 'flame_earned')
  int get flameEarned;
  @override
  @JsonKey(name: 'leveled_up')
  bool get leveledUp;
  @override
  @JsonKey(name: 'new_level')
  int get newLevel;
  @override
  @JsonKey(ignore: true)
  _$$FocusSessionRewardsImplCopyWith<_$FocusSessionRewardsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

FocusSessionResponse _$FocusSessionResponseFromJson(Map<String, dynamic> json) {
  return _FocusSessionResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusSessionResponse {
  bool get success => throw _privateConstructorUsedError;
  String get id => throw _privateConstructorUsedError;
  FocusSessionRewards get rewards => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusSessionResponseCopyWith<FocusSessionResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusSessionResponseCopyWith<$Res> {
  factory $FocusSessionResponseCopyWith(FocusSessionResponse value,
          $Res Function(FocusSessionResponse) then) =
      _$FocusSessionResponseCopyWithImpl<$Res, FocusSessionResponse>;
  @useResult
  $Res call({bool success, String id, FocusSessionRewards rewards});

  $FocusSessionRewardsCopyWith<$Res> get rewards;
}

/// @nodoc
class _$FocusSessionResponseCopyWithImpl<$Res,
        $Val extends FocusSessionResponse>
    implements $FocusSessionResponseCopyWith<$Res> {
  _$FocusSessionResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? success = null,
    Object? id = null,
    Object? rewards = null,
  }) {
    return _then(_value.copyWith(
      success: null == success
          ? _value.success
          : success // ignore: cast_nullable_to_non_nullable
              as bool,
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      rewards: null == rewards
          ? _value.rewards
          : rewards // ignore: cast_nullable_to_non_nullable
              as FocusSessionRewards,
    ) as $Val);
  }

  @override
  @pragma('vm:prefer-inline')
  $FocusSessionRewardsCopyWith<$Res> get rewards {
    return $FocusSessionRewardsCopyWith<$Res>(_value.rewards, (value) {
      return _then(_value.copyWith(rewards: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$FocusSessionResponseImplCopyWith<$Res>
    implements $FocusSessionResponseCopyWith<$Res> {
  factory _$$FocusSessionResponseImplCopyWith(_$FocusSessionResponseImpl value,
          $Res Function(_$FocusSessionResponseImpl) then) =
      __$$FocusSessionResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({bool success, String id, FocusSessionRewards rewards});

  @override
  $FocusSessionRewardsCopyWith<$Res> get rewards;
}

/// @nodoc
class __$$FocusSessionResponseImplCopyWithImpl<$Res>
    extends _$FocusSessionResponseCopyWithImpl<$Res, _$FocusSessionResponseImpl>
    implements _$$FocusSessionResponseImplCopyWith<$Res> {
  __$$FocusSessionResponseImplCopyWithImpl(_$FocusSessionResponseImpl _value,
      $Res Function(_$FocusSessionResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? success = null,
    Object? id = null,
    Object? rewards = null,
  }) {
    return _then(_$FocusSessionResponseImpl(
      success: null == success
          ? _value.success
          : success // ignore: cast_nullable_to_non_nullable
              as bool,
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      rewards: null == rewards
          ? _value.rewards
          : rewards // ignore: cast_nullable_to_non_nullable
              as FocusSessionRewards,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusSessionResponseImpl implements _FocusSessionResponse {
  const _$FocusSessionResponseImpl(
      {required this.success, required this.id, required this.rewards});

  factory _$FocusSessionResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusSessionResponseImplFromJson(json);

  @override
  final bool success;
  @override
  final String id;
  @override
  final FocusSessionRewards rewards;

  @override
  String toString() {
    return 'FocusSessionResponse(success: $success, id: $id, rewards: $rewards)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionResponseImpl &&
            (identical(other.success, success) || other.success == success) &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.rewards, rewards) || other.rewards == rewards));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, success, id, rewards);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusSessionResponseImplCopyWith<_$FocusSessionResponseImpl>
      get copyWith =>
          __$$FocusSessionResponseImplCopyWithImpl<_$FocusSessionResponseImpl>(
              this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusSessionResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusSessionResponse implements FocusSessionResponse {
  const factory _FocusSessionResponse(
      {required final bool success,
      required final String id,
      required final FocusSessionRewards rewards}) = _$FocusSessionResponseImpl;

  factory _FocusSessionResponse.fromJson(Map<String, dynamic> json) =
      _$FocusSessionResponseImpl.fromJson;

  @override
  bool get success;
  @override
  String get id;
  @override
  FocusSessionRewards get rewards;
  @override
  @JsonKey(ignore: true)
  _$$FocusSessionResponseImplCopyWith<_$FocusSessionResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}

FocusStatsResponse _$FocusStatsResponseFromJson(Map<String, dynamic> json) {
  return _FocusStatsResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusStatsResponse {
  @JsonKey(name: 'total_minutes')
  int get totalMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'pomodoro_count')
  int get pomodoroCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'today_date')
  String get todayDate => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusStatsResponseCopyWith<FocusStatsResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusStatsResponseCopyWith<$Res> {
  factory $FocusStatsResponseCopyWith(
          FocusStatsResponse value, $Res Function(FocusStatsResponse) then) =
      _$FocusStatsResponseCopyWithImpl<$Res, FocusStatsResponse>;
  @useResult
  $Res call(
      {@JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'pomodoro_count') int pomodoroCount,
      @JsonKey(name: 'today_date') String todayDate});
}

/// @nodoc
class _$FocusStatsResponseCopyWithImpl<$Res, $Val extends FocusStatsResponse>
    implements $FocusStatsResponseCopyWith<$Res> {
  _$FocusStatsResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalMinutes = null,
    Object? pomodoroCount = null,
    Object? todayDate = null,
  }) {
    return _then(_value.copyWith(
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      pomodoroCount: null == pomodoroCount
          ? _value.pomodoroCount
          : pomodoroCount // ignore: cast_nullable_to_non_nullable
              as int,
      todayDate: null == todayDate
          ? _value.todayDate
          : todayDate // ignore: cast_nullable_to_non_nullable
              as String,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusStatsResponseImplCopyWith<$Res>
    implements $FocusStatsResponseCopyWith<$Res> {
  factory _$$FocusStatsResponseImplCopyWith(_$FocusStatsResponseImpl value,
          $Res Function(_$FocusStatsResponseImpl) then) =
      __$$FocusStatsResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'pomodoro_count') int pomodoroCount,
      @JsonKey(name: 'today_date') String todayDate});
}

/// @nodoc
class __$$FocusStatsResponseImplCopyWithImpl<$Res>
    extends _$FocusStatsResponseCopyWithImpl<$Res, _$FocusStatsResponseImpl>
    implements _$$FocusStatsResponseImplCopyWith<$Res> {
  __$$FocusStatsResponseImplCopyWithImpl(_$FocusStatsResponseImpl _value,
      $Res Function(_$FocusStatsResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalMinutes = null,
    Object? pomodoroCount = null,
    Object? todayDate = null,
  }) {
    return _then(_$FocusStatsResponseImpl(
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      pomodoroCount: null == pomodoroCount
          ? _value.pomodoroCount
          : pomodoroCount // ignore: cast_nullable_to_non_nullable
              as int,
      todayDate: null == todayDate
          ? _value.todayDate
          : todayDate // ignore: cast_nullable_to_non_nullable
              as String,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusStatsResponseImpl implements _FocusStatsResponse {
  const _$FocusStatsResponseImpl(
      {@JsonKey(name: 'total_minutes') required this.totalMinutes,
      @JsonKey(name: 'pomodoro_count') required this.pomodoroCount,
      @JsonKey(name: 'today_date') required this.todayDate});

  factory _$FocusStatsResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusStatsResponseImplFromJson(json);

  @override
  @JsonKey(name: 'total_minutes')
  final int totalMinutes;
  @override
  @JsonKey(name: 'pomodoro_count')
  final int pomodoroCount;
  @override
  @JsonKey(name: 'today_date')
  final String todayDate;

  @override
  String toString() {
    return 'FocusStatsResponse(totalMinutes: $totalMinutes, pomodoroCount: $pomodoroCount, todayDate: $todayDate)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusStatsResponseImpl &&
            (identical(other.totalMinutes, totalMinutes) ||
                other.totalMinutes == totalMinutes) &&
            (identical(other.pomodoroCount, pomodoroCount) ||
                other.pomodoroCount == pomodoroCount) &&
            (identical(other.todayDate, todayDate) ||
                other.todayDate == todayDate));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, totalMinutes, pomodoroCount, todayDate);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusStatsResponseImplCopyWith<_$FocusStatsResponseImpl> get copyWith =>
      __$$FocusStatsResponseImplCopyWithImpl<_$FocusStatsResponseImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusStatsResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusStatsResponse implements FocusStatsResponse {
  const factory _FocusStatsResponse(
          {@JsonKey(name: 'total_minutes') required final int totalMinutes,
          @JsonKey(name: 'pomodoro_count') required final int pomodoroCount,
          @JsonKey(name: 'today_date') required final String todayDate}) =
      _$FocusStatsResponseImpl;

  factory _FocusStatsResponse.fromJson(Map<String, dynamic> json) =
      _$FocusStatsResponseImpl.fromJson;

  @override
  @JsonKey(name: 'total_minutes')
  int get totalMinutes;
  @override
  @JsonKey(name: 'pomodoro_count')
  int get pomodoroCount;
  @override
  @JsonKey(name: 'today_date')
  String get todayDate;
  @override
  @JsonKey(ignore: true)
  _$$FocusStatsResponseImplCopyWith<_$FocusStatsResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
