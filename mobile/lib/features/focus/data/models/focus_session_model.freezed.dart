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
  @JsonKey(name: 'start_time')
  DateTime get startTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_time')
  DateTime get endTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'duration_minutes')
  int get durationMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'focus_type')
  String get focusType => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'task_id')
  String? get taskId => throw _privateConstructorUsedError;
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
      {@JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'task_id') String? taskId,
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
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? taskId = freezed,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_value.copyWith(
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
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
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
      {@JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'task_id') String? taskId,
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
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? taskId = freezed,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_$FocusSessionRequestImpl(
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
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
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
      {@JsonKey(name: 'start_time') required this.startTime,
      @JsonKey(name: 'end_time') required this.endTime,
      @JsonKey(name: 'duration_minutes') required this.durationMinutes,
      @JsonKey(name: 'focus_type') required this.focusType,
      required this.status,
      @JsonKey(name: 'task_id') this.taskId,
      @JsonKey(name: 'white_noise_type') this.whiteNoiseType});

  factory _$FocusSessionRequestImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusSessionRequestImplFromJson(json);

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
  @JsonKey(name: 'task_id')
  final String? taskId;
  @override
  @JsonKey(name: 'white_noise_type')
  final String? whiteNoiseType;

  @override
  String toString() {
    return 'FocusSessionRequest(startTime: $startTime, endTime: $endTime, durationMinutes: $durationMinutes, focusType: $focusType, status: $status, taskId: $taskId, whiteNoiseType: $whiteNoiseType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionRequestImpl &&
            (identical(other.startTime, startTime) ||
                other.startTime == startTime) &&
            (identical(other.endTime, endTime) || other.endTime == endTime) &&
            (identical(other.durationMinutes, durationMinutes) ||
                other.durationMinutes == durationMinutes) &&
            (identical(other.focusType, focusType) ||
                other.focusType == focusType) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.taskId, taskId) || other.taskId == taskId) &&
            (identical(other.whiteNoiseType, whiteNoiseType) ||
                other.whiteNoiseType == whiteNoiseType));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, startTime, endTime,
      durationMinutes, focusType, status, taskId, whiteNoiseType);

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
          {@JsonKey(name: 'start_time') required final DateTime startTime,
          @JsonKey(name: 'end_time') required final DateTime endTime,
          @JsonKey(name: 'duration_minutes') required final int durationMinutes,
          @JsonKey(name: 'focus_type') required final String focusType,
          required final String status,
          @JsonKey(name: 'task_id') final String? taskId,
          @JsonKey(name: 'white_noise_type') final String? whiteNoiseType}) =
      _$FocusSessionRequestImpl;

  factory _FocusSessionRequest.fromJson(Map<String, dynamic> json) =
      _$FocusSessionRequestImpl.fromJson;

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
  @JsonKey(name: 'task_id')
  String? get taskId;
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

DailyFocusStats _$DailyFocusStatsFromJson(Map<String, dynamic> json) {
  return _DailyFocusStats.fromJson(json);
}

/// @nodoc
mixin _$DailyFocusStats {
  String get date => throw _privateConstructorUsedError;
  int get minutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'session_count')
  int? get sessionCount => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $DailyFocusStatsCopyWith<DailyFocusStats> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DailyFocusStatsCopyWith<$Res> {
  factory $DailyFocusStatsCopyWith(
          DailyFocusStats value, $Res Function(DailyFocusStats) then) =
      _$DailyFocusStatsCopyWithImpl<$Res, DailyFocusStats>;
  @useResult
  $Res call(
      {String date,
      int minutes,
      @JsonKey(name: 'session_count') int? sessionCount});
}

/// @nodoc
class _$DailyFocusStatsCopyWithImpl<$Res, $Val extends DailyFocusStats>
    implements $DailyFocusStatsCopyWith<$Res> {
  _$DailyFocusStatsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? date = null,
    Object? minutes = null,
    Object? sessionCount = freezed,
  }) {
    return _then(_value.copyWith(
      date: null == date
          ? _value.date
          : date // ignore: cast_nullable_to_non_nullable
              as String,
      minutes: null == minutes
          ? _value.minutes
          : minutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: freezed == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$DailyFocusStatsImplCopyWith<$Res>
    implements $DailyFocusStatsCopyWith<$Res> {
  factory _$$DailyFocusStatsImplCopyWith(_$DailyFocusStatsImpl value,
          $Res Function(_$DailyFocusStatsImpl) then) =
      __$$DailyFocusStatsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String date,
      int minutes,
      @JsonKey(name: 'session_count') int? sessionCount});
}

/// @nodoc
class __$$DailyFocusStatsImplCopyWithImpl<$Res>
    extends _$DailyFocusStatsCopyWithImpl<$Res, _$DailyFocusStatsImpl>
    implements _$$DailyFocusStatsImplCopyWith<$Res> {
  __$$DailyFocusStatsImplCopyWithImpl(
      _$DailyFocusStatsImpl _value, $Res Function(_$DailyFocusStatsImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? date = null,
    Object? minutes = null,
    Object? sessionCount = freezed,
  }) {
    return _then(_$DailyFocusStatsImpl(
      date: null == date
          ? _value.date
          : date // ignore: cast_nullable_to_non_nullable
              as String,
      minutes: null == minutes
          ? _value.minutes
          : minutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: freezed == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$DailyFocusStatsImpl implements _DailyFocusStats {
  const _$DailyFocusStatsImpl(
      {required this.date,
      required this.minutes,
      @JsonKey(name: 'session_count') this.sessionCount});

  factory _$DailyFocusStatsImpl.fromJson(Map<String, dynamic> json) =>
      _$$DailyFocusStatsImplFromJson(json);

  @override
  final String date;
  @override
  final int minutes;
  @override
  @JsonKey(name: 'session_count')
  final int? sessionCount;

  @override
  String toString() {
    return 'DailyFocusStats(date: $date, minutes: $minutes, sessionCount: $sessionCount)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DailyFocusStatsImpl &&
            (identical(other.date, date) || other.date == date) &&
            (identical(other.minutes, minutes) || other.minutes == minutes) &&
            (identical(other.sessionCount, sessionCount) ||
                other.sessionCount == sessionCount));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, date, minutes, sessionCount);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$DailyFocusStatsImplCopyWith<_$DailyFocusStatsImpl> get copyWith =>
      __$$DailyFocusStatsImplCopyWithImpl<_$DailyFocusStatsImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$DailyFocusStatsImplToJson(
      this,
    );
  }
}

abstract class _DailyFocusStats implements DailyFocusStats {
  const factory _DailyFocusStats(
          {required final String date,
          required final int minutes,
          @JsonKey(name: 'session_count') final int? sessionCount}) =
      _$DailyFocusStatsImpl;

  factory _DailyFocusStats.fromJson(Map<String, dynamic> json) =
      _$DailyFocusStatsImpl.fromJson;

  @override
  String get date;
  @override
  int get minutes;
  @override
  @JsonKey(name: 'session_count')
  int? get sessionCount;
  @override
  @JsonKey(ignore: true)
  _$$DailyFocusStatsImplCopyWith<_$DailyFocusStatsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

FocusWeeklyStatsResponse _$FocusWeeklyStatsResponseFromJson(
    Map<String, dynamic> json) {
  return _FocusWeeklyStatsResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusWeeklyStatsResponse {
  @JsonKey(name: 'period_start')
  String get periodStart => throw _privateConstructorUsedError;
  @JsonKey(name: 'period_end')
  String get periodEnd => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_minutes')
  int get totalMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'session_count')
  int get sessionCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'avg_duration')
  int get avgDuration => throw _privateConstructorUsedError;
  @JsonKey(name: 'best_day')
  String? get bestDay => throw _privateConstructorUsedError;
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown => throw _privateConstructorUsedError;
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'streak_days')
  int get streakDays => throw _privateConstructorUsedError;
  @JsonKey(name: 'longest_streak')
  int get longestStreak => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusWeeklyStatsResponseCopyWith<FocusWeeklyStatsResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusWeeklyStatsResponseCopyWith<$Res> {
  factory $FocusWeeklyStatsResponseCopyWith(FocusWeeklyStatsResponse value,
          $Res Function(FocusWeeklyStatsResponse) then) =
      _$FocusWeeklyStatsResponseCopyWithImpl<$Res, FocusWeeklyStatsResponse>;
  @useResult
  $Res call(
      {@JsonKey(name: 'period_start') String periodStart,
      @JsonKey(name: 'period_end') String periodEnd,
      @JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'session_count') int sessionCount,
      @JsonKey(name: 'avg_duration') int avgDuration,
      @JsonKey(name: 'best_day') String? bestDay,
      @JsonKey(name: 'daily_breakdown') Map<String, int> dailyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') int streakDays,
      @JsonKey(name: 'longest_streak') int longestStreak});
}

/// @nodoc
class _$FocusWeeklyStatsResponseCopyWithImpl<$Res,
        $Val extends FocusWeeklyStatsResponse>
    implements $FocusWeeklyStatsResponseCopyWith<$Res> {
  _$FocusWeeklyStatsResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? periodStart = null,
    Object? periodEnd = null,
    Object? totalMinutes = null,
    Object? sessionCount = null,
    Object? avgDuration = null,
    Object? bestDay = freezed,
    Object? dailyBreakdown = null,
    Object? focusTypeDistribution = null,
    Object? streakDays = null,
    Object? longestStreak = null,
  }) {
    return _then(_value.copyWith(
      periodStart: null == periodStart
          ? _value.periodStart
          : periodStart // ignore: cast_nullable_to_non_nullable
              as String,
      periodEnd: null == periodEnd
          ? _value.periodEnd
          : periodEnd // ignore: cast_nullable_to_non_nullable
              as String,
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: null == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int,
      avgDuration: null == avgDuration
          ? _value.avgDuration
          : avgDuration // ignore: cast_nullable_to_non_nullable
              as int,
      bestDay: freezed == bestDay
          ? _value.bestDay
          : bestDay // ignore: cast_nullable_to_non_nullable
              as String?,
      dailyBreakdown: null == dailyBreakdown
          ? _value.dailyBreakdown
          : dailyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      focusTypeDistribution: null == focusTypeDistribution
          ? _value.focusTypeDistribution
          : focusTypeDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      streakDays: null == streakDays
          ? _value.streakDays
          : streakDays // ignore: cast_nullable_to_non_nullable
              as int,
      longestStreak: null == longestStreak
          ? _value.longestStreak
          : longestStreak // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusWeeklyStatsResponseImplCopyWith<$Res>
    implements $FocusWeeklyStatsResponseCopyWith<$Res> {
  factory _$$FocusWeeklyStatsResponseImplCopyWith(
          _$FocusWeeklyStatsResponseImpl value,
          $Res Function(_$FocusWeeklyStatsResponseImpl) then) =
      __$$FocusWeeklyStatsResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'period_start') String periodStart,
      @JsonKey(name: 'period_end') String periodEnd,
      @JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'session_count') int sessionCount,
      @JsonKey(name: 'avg_duration') int avgDuration,
      @JsonKey(name: 'best_day') String? bestDay,
      @JsonKey(name: 'daily_breakdown') Map<String, int> dailyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') int streakDays,
      @JsonKey(name: 'longest_streak') int longestStreak});
}

/// @nodoc
class __$$FocusWeeklyStatsResponseImplCopyWithImpl<$Res>
    extends _$FocusWeeklyStatsResponseCopyWithImpl<$Res,
        _$FocusWeeklyStatsResponseImpl>
    implements _$$FocusWeeklyStatsResponseImplCopyWith<$Res> {
  __$$FocusWeeklyStatsResponseImplCopyWithImpl(
      _$FocusWeeklyStatsResponseImpl _value,
      $Res Function(_$FocusWeeklyStatsResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? periodStart = null,
    Object? periodEnd = null,
    Object? totalMinutes = null,
    Object? sessionCount = null,
    Object? avgDuration = null,
    Object? bestDay = freezed,
    Object? dailyBreakdown = null,
    Object? focusTypeDistribution = null,
    Object? streakDays = null,
    Object? longestStreak = null,
  }) {
    return _then(_$FocusWeeklyStatsResponseImpl(
      periodStart: null == periodStart
          ? _value.periodStart
          : periodStart // ignore: cast_nullable_to_non_nullable
              as String,
      periodEnd: null == periodEnd
          ? _value.periodEnd
          : periodEnd // ignore: cast_nullable_to_non_nullable
              as String,
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: null == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int,
      avgDuration: null == avgDuration
          ? _value.avgDuration
          : avgDuration // ignore: cast_nullable_to_non_nullable
              as int,
      bestDay: freezed == bestDay
          ? _value.bestDay
          : bestDay // ignore: cast_nullable_to_non_nullable
              as String?,
      dailyBreakdown: null == dailyBreakdown
          ? _value._dailyBreakdown
          : dailyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      focusTypeDistribution: null == focusTypeDistribution
          ? _value._focusTypeDistribution
          : focusTypeDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      streakDays: null == streakDays
          ? _value.streakDays
          : streakDays // ignore: cast_nullable_to_non_nullable
              as int,
      longestStreak: null == longestStreak
          ? _value.longestStreak
          : longestStreak // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusWeeklyStatsResponseImpl implements _FocusWeeklyStatsResponse {
  const _$FocusWeeklyStatsResponseImpl(
      {@JsonKey(name: 'period_start') required this.periodStart,
      @JsonKey(name: 'period_end') required this.periodEnd,
      @JsonKey(name: 'total_minutes') required this.totalMinutes,
      @JsonKey(name: 'session_count') required this.sessionCount,
      @JsonKey(name: 'avg_duration') required this.avgDuration,
      @JsonKey(name: 'best_day') this.bestDay,
      @JsonKey(name: 'daily_breakdown')
      required final Map<String, int> dailyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      required final Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') required this.streakDays,
      @JsonKey(name: 'longest_streak') required this.longestStreak})
      : _dailyBreakdown = dailyBreakdown,
        _focusTypeDistribution = focusTypeDistribution;

  factory _$FocusWeeklyStatsResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusWeeklyStatsResponseImplFromJson(json);

  @override
  @JsonKey(name: 'period_start')
  final String periodStart;
  @override
  @JsonKey(name: 'period_end')
  final String periodEnd;
  @override
  @JsonKey(name: 'total_minutes')
  final int totalMinutes;
  @override
  @JsonKey(name: 'session_count')
  final int sessionCount;
  @override
  @JsonKey(name: 'avg_duration')
  final int avgDuration;
  @override
  @JsonKey(name: 'best_day')
  final String? bestDay;
  final Map<String, int> _dailyBreakdown;
  @override
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown {
    if (_dailyBreakdown is EqualUnmodifiableMapView) return _dailyBreakdown;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_dailyBreakdown);
  }

  final Map<String, int> _focusTypeDistribution;
  @override
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution {
    if (_focusTypeDistribution is EqualUnmodifiableMapView)
      return _focusTypeDistribution;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_focusTypeDistribution);
  }

  @override
  @JsonKey(name: 'streak_days')
  final int streakDays;
  @override
  @JsonKey(name: 'longest_streak')
  final int longestStreak;

  @override
  String toString() {
    return 'FocusWeeklyStatsResponse(periodStart: $periodStart, periodEnd: $periodEnd, totalMinutes: $totalMinutes, sessionCount: $sessionCount, avgDuration: $avgDuration, bestDay: $bestDay, dailyBreakdown: $dailyBreakdown, focusTypeDistribution: $focusTypeDistribution, streakDays: $streakDays, longestStreak: $longestStreak)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusWeeklyStatsResponseImpl &&
            (identical(other.periodStart, periodStart) ||
                other.periodStart == periodStart) &&
            (identical(other.periodEnd, periodEnd) ||
                other.periodEnd == periodEnd) &&
            (identical(other.totalMinutes, totalMinutes) ||
                other.totalMinutes == totalMinutes) &&
            (identical(other.sessionCount, sessionCount) ||
                other.sessionCount == sessionCount) &&
            (identical(other.avgDuration, avgDuration) ||
                other.avgDuration == avgDuration) &&
            (identical(other.bestDay, bestDay) || other.bestDay == bestDay) &&
            const DeepCollectionEquality()
                .equals(other._dailyBreakdown, _dailyBreakdown) &&
            const DeepCollectionEquality()
                .equals(other._focusTypeDistribution, _focusTypeDistribution) &&
            (identical(other.streakDays, streakDays) ||
                other.streakDays == streakDays) &&
            (identical(other.longestStreak, longestStreak) ||
                other.longestStreak == longestStreak));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      periodStart,
      periodEnd,
      totalMinutes,
      sessionCount,
      avgDuration,
      bestDay,
      const DeepCollectionEquality().hash(_dailyBreakdown),
      const DeepCollectionEquality().hash(_focusTypeDistribution),
      streakDays,
      longestStreak);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusWeeklyStatsResponseImplCopyWith<_$FocusWeeklyStatsResponseImpl>
      get copyWith => __$$FocusWeeklyStatsResponseImplCopyWithImpl<
          _$FocusWeeklyStatsResponseImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusWeeklyStatsResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusWeeklyStatsResponse implements FocusWeeklyStatsResponse {
  const factory _FocusWeeklyStatsResponse(
          {@JsonKey(name: 'period_start') required final String periodStart,
          @JsonKey(name: 'period_end') required final String periodEnd,
          @JsonKey(name: 'total_minutes') required final int totalMinutes,
          @JsonKey(name: 'session_count') required final int sessionCount,
          @JsonKey(name: 'avg_duration') required final int avgDuration,
          @JsonKey(name: 'best_day') final String? bestDay,
          @JsonKey(name: 'daily_breakdown')
          required final Map<String, int> dailyBreakdown,
          @JsonKey(name: 'focus_type_distribution')
          required final Map<String, int> focusTypeDistribution,
          @JsonKey(name: 'streak_days') required final int streakDays,
          @JsonKey(name: 'longest_streak') required final int longestStreak}) =
      _$FocusWeeklyStatsResponseImpl;

  factory _FocusWeeklyStatsResponse.fromJson(Map<String, dynamic> json) =
      _$FocusWeeklyStatsResponseImpl.fromJson;

  @override
  @JsonKey(name: 'period_start')
  String get periodStart;
  @override
  @JsonKey(name: 'period_end')
  String get periodEnd;
  @override
  @JsonKey(name: 'total_minutes')
  int get totalMinutes;
  @override
  @JsonKey(name: 'session_count')
  int get sessionCount;
  @override
  @JsonKey(name: 'avg_duration')
  int get avgDuration;
  @override
  @JsonKey(name: 'best_day')
  String? get bestDay;
  @override
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown;
  @override
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution;
  @override
  @JsonKey(name: 'streak_days')
  int get streakDays;
  @override
  @JsonKey(name: 'longest_streak')
  int get longestStreak;
  @override
  @JsonKey(ignore: true)
  _$$FocusWeeklyStatsResponseImplCopyWith<_$FocusWeeklyStatsResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}

FocusMonthlyStatsResponse _$FocusMonthlyStatsResponseFromJson(
    Map<String, dynamic> json) {
  return _FocusMonthlyStatsResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusMonthlyStatsResponse {
  @JsonKey(name: 'period_start')
  String get periodStart => throw _privateConstructorUsedError;
  @JsonKey(name: 'period_end')
  String get periodEnd => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_minutes')
  int get totalMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'session_count')
  int get sessionCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'avg_duration')
  int get avgDuration => throw _privateConstructorUsedError;
  @JsonKey(name: 'best_day')
  String? get bestDay => throw _privateConstructorUsedError;
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown => throw _privateConstructorUsedError;
  @JsonKey(name: 'weekly_breakdown')
  Map<String, int> get weeklyBreakdown => throw _privateConstructorUsedError;
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'streak_days')
  int get streakDays => throw _privateConstructorUsedError;
  @JsonKey(name: 'longest_streak')
  int get longestStreak => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusMonthlyStatsResponseCopyWith<FocusMonthlyStatsResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusMonthlyStatsResponseCopyWith<$Res> {
  factory $FocusMonthlyStatsResponseCopyWith(FocusMonthlyStatsResponse value,
          $Res Function(FocusMonthlyStatsResponse) then) =
      _$FocusMonthlyStatsResponseCopyWithImpl<$Res, FocusMonthlyStatsResponse>;
  @useResult
  $Res call(
      {@JsonKey(name: 'period_start') String periodStart,
      @JsonKey(name: 'period_end') String periodEnd,
      @JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'session_count') int sessionCount,
      @JsonKey(name: 'avg_duration') int avgDuration,
      @JsonKey(name: 'best_day') String? bestDay,
      @JsonKey(name: 'daily_breakdown') Map<String, int> dailyBreakdown,
      @JsonKey(name: 'weekly_breakdown') Map<String, int> weeklyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') int streakDays,
      @JsonKey(name: 'longest_streak') int longestStreak});
}

/// @nodoc
class _$FocusMonthlyStatsResponseCopyWithImpl<$Res,
        $Val extends FocusMonthlyStatsResponse>
    implements $FocusMonthlyStatsResponseCopyWith<$Res> {
  _$FocusMonthlyStatsResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? periodStart = null,
    Object? periodEnd = null,
    Object? totalMinutes = null,
    Object? sessionCount = null,
    Object? avgDuration = null,
    Object? bestDay = freezed,
    Object? dailyBreakdown = null,
    Object? weeklyBreakdown = null,
    Object? focusTypeDistribution = null,
    Object? streakDays = null,
    Object? longestStreak = null,
  }) {
    return _then(_value.copyWith(
      periodStart: null == periodStart
          ? _value.periodStart
          : periodStart // ignore: cast_nullable_to_non_nullable
              as String,
      periodEnd: null == periodEnd
          ? _value.periodEnd
          : periodEnd // ignore: cast_nullable_to_non_nullable
              as String,
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: null == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int,
      avgDuration: null == avgDuration
          ? _value.avgDuration
          : avgDuration // ignore: cast_nullable_to_non_nullable
              as int,
      bestDay: freezed == bestDay
          ? _value.bestDay
          : bestDay // ignore: cast_nullable_to_non_nullable
              as String?,
      dailyBreakdown: null == dailyBreakdown
          ? _value.dailyBreakdown
          : dailyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      weeklyBreakdown: null == weeklyBreakdown
          ? _value.weeklyBreakdown
          : weeklyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      focusTypeDistribution: null == focusTypeDistribution
          ? _value.focusTypeDistribution
          : focusTypeDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      streakDays: null == streakDays
          ? _value.streakDays
          : streakDays // ignore: cast_nullable_to_non_nullable
              as int,
      longestStreak: null == longestStreak
          ? _value.longestStreak
          : longestStreak // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusMonthlyStatsResponseImplCopyWith<$Res>
    implements $FocusMonthlyStatsResponseCopyWith<$Res> {
  factory _$$FocusMonthlyStatsResponseImplCopyWith(
          _$FocusMonthlyStatsResponseImpl value,
          $Res Function(_$FocusMonthlyStatsResponseImpl) then) =
      __$$FocusMonthlyStatsResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'period_start') String periodStart,
      @JsonKey(name: 'period_end') String periodEnd,
      @JsonKey(name: 'total_minutes') int totalMinutes,
      @JsonKey(name: 'session_count') int sessionCount,
      @JsonKey(name: 'avg_duration') int avgDuration,
      @JsonKey(name: 'best_day') String? bestDay,
      @JsonKey(name: 'daily_breakdown') Map<String, int> dailyBreakdown,
      @JsonKey(name: 'weekly_breakdown') Map<String, int> weeklyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') int streakDays,
      @JsonKey(name: 'longest_streak') int longestStreak});
}

/// @nodoc
class __$$FocusMonthlyStatsResponseImplCopyWithImpl<$Res>
    extends _$FocusMonthlyStatsResponseCopyWithImpl<$Res,
        _$FocusMonthlyStatsResponseImpl>
    implements _$$FocusMonthlyStatsResponseImplCopyWith<$Res> {
  __$$FocusMonthlyStatsResponseImplCopyWithImpl(
      _$FocusMonthlyStatsResponseImpl _value,
      $Res Function(_$FocusMonthlyStatsResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? periodStart = null,
    Object? periodEnd = null,
    Object? totalMinutes = null,
    Object? sessionCount = null,
    Object? avgDuration = null,
    Object? bestDay = freezed,
    Object? dailyBreakdown = null,
    Object? weeklyBreakdown = null,
    Object? focusTypeDistribution = null,
    Object? streakDays = null,
    Object? longestStreak = null,
  }) {
    return _then(_$FocusMonthlyStatsResponseImpl(
      periodStart: null == periodStart
          ? _value.periodStart
          : periodStart // ignore: cast_nullable_to_non_nullable
              as String,
      periodEnd: null == periodEnd
          ? _value.periodEnd
          : periodEnd // ignore: cast_nullable_to_non_nullable
              as String,
      totalMinutes: null == totalMinutes
          ? _value.totalMinutes
          : totalMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      sessionCount: null == sessionCount
          ? _value.sessionCount
          : sessionCount // ignore: cast_nullable_to_non_nullable
              as int,
      avgDuration: null == avgDuration
          ? _value.avgDuration
          : avgDuration // ignore: cast_nullable_to_non_nullable
              as int,
      bestDay: freezed == bestDay
          ? _value.bestDay
          : bestDay // ignore: cast_nullable_to_non_nullable
              as String?,
      dailyBreakdown: null == dailyBreakdown
          ? _value._dailyBreakdown
          : dailyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      weeklyBreakdown: null == weeklyBreakdown
          ? _value._weeklyBreakdown
          : weeklyBreakdown // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      focusTypeDistribution: null == focusTypeDistribution
          ? _value._focusTypeDistribution
          : focusTypeDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
      streakDays: null == streakDays
          ? _value.streakDays
          : streakDays // ignore: cast_nullable_to_non_nullable
              as int,
      longestStreak: null == longestStreak
          ? _value.longestStreak
          : longestStreak // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusMonthlyStatsResponseImpl implements _FocusMonthlyStatsResponse {
  const _$FocusMonthlyStatsResponseImpl(
      {@JsonKey(name: 'period_start') required this.periodStart,
      @JsonKey(name: 'period_end') required this.periodEnd,
      @JsonKey(name: 'total_minutes') required this.totalMinutes,
      @JsonKey(name: 'session_count') required this.sessionCount,
      @JsonKey(name: 'avg_duration') required this.avgDuration,
      @JsonKey(name: 'best_day') this.bestDay,
      @JsonKey(name: 'daily_breakdown')
      required final Map<String, int> dailyBreakdown,
      @JsonKey(name: 'weekly_breakdown')
      required final Map<String, int> weeklyBreakdown,
      @JsonKey(name: 'focus_type_distribution')
      required final Map<String, int> focusTypeDistribution,
      @JsonKey(name: 'streak_days') required this.streakDays,
      @JsonKey(name: 'longest_streak') required this.longestStreak})
      : _dailyBreakdown = dailyBreakdown,
        _weeklyBreakdown = weeklyBreakdown,
        _focusTypeDistribution = focusTypeDistribution;

  factory _$FocusMonthlyStatsResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusMonthlyStatsResponseImplFromJson(json);

  @override
  @JsonKey(name: 'period_start')
  final String periodStart;
  @override
  @JsonKey(name: 'period_end')
  final String periodEnd;
  @override
  @JsonKey(name: 'total_minutes')
  final int totalMinutes;
  @override
  @JsonKey(name: 'session_count')
  final int sessionCount;
  @override
  @JsonKey(name: 'avg_duration')
  final int avgDuration;
  @override
  @JsonKey(name: 'best_day')
  final String? bestDay;
  final Map<String, int> _dailyBreakdown;
  @override
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown {
    if (_dailyBreakdown is EqualUnmodifiableMapView) return _dailyBreakdown;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_dailyBreakdown);
  }

  final Map<String, int> _weeklyBreakdown;
  @override
  @JsonKey(name: 'weekly_breakdown')
  Map<String, int> get weeklyBreakdown {
    if (_weeklyBreakdown is EqualUnmodifiableMapView) return _weeklyBreakdown;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_weeklyBreakdown);
  }

  final Map<String, int> _focusTypeDistribution;
  @override
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution {
    if (_focusTypeDistribution is EqualUnmodifiableMapView)
      return _focusTypeDistribution;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_focusTypeDistribution);
  }

  @override
  @JsonKey(name: 'streak_days')
  final int streakDays;
  @override
  @JsonKey(name: 'longest_streak')
  final int longestStreak;

  @override
  String toString() {
    return 'FocusMonthlyStatsResponse(periodStart: $periodStart, periodEnd: $periodEnd, totalMinutes: $totalMinutes, sessionCount: $sessionCount, avgDuration: $avgDuration, bestDay: $bestDay, dailyBreakdown: $dailyBreakdown, weeklyBreakdown: $weeklyBreakdown, focusTypeDistribution: $focusTypeDistribution, streakDays: $streakDays, longestStreak: $longestStreak)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusMonthlyStatsResponseImpl &&
            (identical(other.periodStart, periodStart) ||
                other.periodStart == periodStart) &&
            (identical(other.periodEnd, periodEnd) ||
                other.periodEnd == periodEnd) &&
            (identical(other.totalMinutes, totalMinutes) ||
                other.totalMinutes == totalMinutes) &&
            (identical(other.sessionCount, sessionCount) ||
                other.sessionCount == sessionCount) &&
            (identical(other.avgDuration, avgDuration) ||
                other.avgDuration == avgDuration) &&
            (identical(other.bestDay, bestDay) || other.bestDay == bestDay) &&
            const DeepCollectionEquality()
                .equals(other._dailyBreakdown, _dailyBreakdown) &&
            const DeepCollectionEquality()
                .equals(other._weeklyBreakdown, _weeklyBreakdown) &&
            const DeepCollectionEquality()
                .equals(other._focusTypeDistribution, _focusTypeDistribution) &&
            (identical(other.streakDays, streakDays) ||
                other.streakDays == streakDays) &&
            (identical(other.longestStreak, longestStreak) ||
                other.longestStreak == longestStreak));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      periodStart,
      periodEnd,
      totalMinutes,
      sessionCount,
      avgDuration,
      bestDay,
      const DeepCollectionEquality().hash(_dailyBreakdown),
      const DeepCollectionEquality().hash(_weeklyBreakdown),
      const DeepCollectionEquality().hash(_focusTypeDistribution),
      streakDays,
      longestStreak);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusMonthlyStatsResponseImplCopyWith<_$FocusMonthlyStatsResponseImpl>
      get copyWith => __$$FocusMonthlyStatsResponseImplCopyWithImpl<
          _$FocusMonthlyStatsResponseImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusMonthlyStatsResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusMonthlyStatsResponse implements FocusMonthlyStatsResponse {
  const factory _FocusMonthlyStatsResponse(
          {@JsonKey(name: 'period_start') required final String periodStart,
          @JsonKey(name: 'period_end') required final String periodEnd,
          @JsonKey(name: 'total_minutes') required final int totalMinutes,
          @JsonKey(name: 'session_count') required final int sessionCount,
          @JsonKey(name: 'avg_duration') required final int avgDuration,
          @JsonKey(name: 'best_day') final String? bestDay,
          @JsonKey(name: 'daily_breakdown')
          required final Map<String, int> dailyBreakdown,
          @JsonKey(name: 'weekly_breakdown')
          required final Map<String, int> weeklyBreakdown,
          @JsonKey(name: 'focus_type_distribution')
          required final Map<String, int> focusTypeDistribution,
          @JsonKey(name: 'streak_days') required final int streakDays,
          @JsonKey(name: 'longest_streak') required final int longestStreak}) =
      _$FocusMonthlyStatsResponseImpl;

  factory _FocusMonthlyStatsResponse.fromJson(Map<String, dynamic> json) =
      _$FocusMonthlyStatsResponseImpl.fromJson;

  @override
  @JsonKey(name: 'period_start')
  String get periodStart;
  @override
  @JsonKey(name: 'period_end')
  String get periodEnd;
  @override
  @JsonKey(name: 'total_minutes')
  int get totalMinutes;
  @override
  @JsonKey(name: 'session_count')
  int get sessionCount;
  @override
  @JsonKey(name: 'avg_duration')
  int get avgDuration;
  @override
  @JsonKey(name: 'best_day')
  String? get bestDay;
  @override
  @JsonKey(name: 'daily_breakdown')
  Map<String, int> get dailyBreakdown;
  @override
  @JsonKey(name: 'weekly_breakdown')
  Map<String, int> get weeklyBreakdown;
  @override
  @JsonKey(name: 'focus_type_distribution')
  Map<String, int> get focusTypeDistribution;
  @override
  @JsonKey(name: 'streak_days')
  int get streakDays;
  @override
  @JsonKey(name: 'longest_streak')
  int get longestStreak;
  @override
  @JsonKey(ignore: true)
  _$$FocusMonthlyStatsResponseImplCopyWith<_$FocusMonthlyStatsResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}

FocusSessionDetail _$FocusSessionDetailFromJson(Map<String, dynamic> json) {
  return _FocusSessionDetail.fromJson(json);
}

/// @nodoc
mixin _$FocusSessionDetail {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_time')
  DateTime get startTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_time')
  DateTime get endTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'duration_minutes')
  int get durationMinutes => throw _privateConstructorUsedError;
  @JsonKey(name: 'focus_type')
  String get focusType => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'task_id')
  String? get taskId => throw _privateConstructorUsedError;
  @JsonKey(name: 'task_title')
  String? get taskTitle => throw _privateConstructorUsedError;
  @JsonKey(name: 'white_noise_type')
  int? get whiteNoiseType => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusSessionDetailCopyWith<FocusSessionDetail> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusSessionDetailCopyWith<$Res> {
  factory $FocusSessionDetailCopyWith(
          FocusSessionDetail value, $Res Function(FocusSessionDetail) then) =
      _$FocusSessionDetailCopyWithImpl<$Res, FocusSessionDetail>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'task_id') String? taskId,
      @JsonKey(name: 'task_title') String? taskTitle,
      @JsonKey(name: 'white_noise_type') int? whiteNoiseType});
}

/// @nodoc
class _$FocusSessionDetailCopyWithImpl<$Res, $Val extends FocusSessionDetail>
    implements $FocusSessionDetailCopyWith<$Res> {
  _$FocusSessionDetailCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? taskId = freezed,
    Object? taskTitle = freezed,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
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
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
      taskTitle: freezed == taskTitle
          ? _value.taskTitle
          : taskTitle // ignore: cast_nullable_to_non_nullable
              as String?,
      whiteNoiseType: freezed == whiteNoiseType
          ? _value.whiteNoiseType
          : whiteNoiseType // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusSessionDetailImplCopyWith<$Res>
    implements $FocusSessionDetailCopyWith<$Res> {
  factory _$$FocusSessionDetailImplCopyWith(_$FocusSessionDetailImpl value,
          $Res Function(_$FocusSessionDetailImpl) then) =
      __$$FocusSessionDetailImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'start_time') DateTime startTime,
      @JsonKey(name: 'end_time') DateTime endTime,
      @JsonKey(name: 'duration_minutes') int durationMinutes,
      @JsonKey(name: 'focus_type') String focusType,
      String status,
      @JsonKey(name: 'task_id') String? taskId,
      @JsonKey(name: 'task_title') String? taskTitle,
      @JsonKey(name: 'white_noise_type') int? whiteNoiseType});
}

/// @nodoc
class __$$FocusSessionDetailImplCopyWithImpl<$Res>
    extends _$FocusSessionDetailCopyWithImpl<$Res, _$FocusSessionDetailImpl>
    implements _$$FocusSessionDetailImplCopyWith<$Res> {
  __$$FocusSessionDetailImplCopyWithImpl(_$FocusSessionDetailImpl _value,
      $Res Function(_$FocusSessionDetailImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? startTime = null,
    Object? endTime = null,
    Object? durationMinutes = null,
    Object? focusType = null,
    Object? status = null,
    Object? taskId = freezed,
    Object? taskTitle = freezed,
    Object? whiteNoiseType = freezed,
  }) {
    return _then(_$FocusSessionDetailImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
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
      taskId: freezed == taskId
          ? _value.taskId
          : taskId // ignore: cast_nullable_to_non_nullable
              as String?,
      taskTitle: freezed == taskTitle
          ? _value.taskTitle
          : taskTitle // ignore: cast_nullable_to_non_nullable
              as String?,
      whiteNoiseType: freezed == whiteNoiseType
          ? _value.whiteNoiseType
          : whiteNoiseType // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusSessionDetailImpl implements _FocusSessionDetail {
  const _$FocusSessionDetailImpl(
      {required this.id,
      @JsonKey(name: 'start_time') required this.startTime,
      @JsonKey(name: 'end_time') required this.endTime,
      @JsonKey(name: 'duration_minutes') required this.durationMinutes,
      @JsonKey(name: 'focus_type') required this.focusType,
      required this.status,
      @JsonKey(name: 'task_id') this.taskId,
      @JsonKey(name: 'task_title') this.taskTitle,
      @JsonKey(name: 'white_noise_type') this.whiteNoiseType});

  factory _$FocusSessionDetailImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusSessionDetailImplFromJson(json);

  @override
  final String id;
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
  @JsonKey(name: 'task_id')
  final String? taskId;
  @override
  @JsonKey(name: 'task_title')
  final String? taskTitle;
  @override
  @JsonKey(name: 'white_noise_type')
  final int? whiteNoiseType;

  @override
  String toString() {
    return 'FocusSessionDetail(id: $id, startTime: $startTime, endTime: $endTime, durationMinutes: $durationMinutes, focusType: $focusType, status: $status, taskId: $taskId, taskTitle: $taskTitle, whiteNoiseType: $whiteNoiseType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionDetailImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.startTime, startTime) ||
                other.startTime == startTime) &&
            (identical(other.endTime, endTime) || other.endTime == endTime) &&
            (identical(other.durationMinutes, durationMinutes) ||
                other.durationMinutes == durationMinutes) &&
            (identical(other.focusType, focusType) ||
                other.focusType == focusType) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.taskId, taskId) || other.taskId == taskId) &&
            (identical(other.taskTitle, taskTitle) ||
                other.taskTitle == taskTitle) &&
            (identical(other.whiteNoiseType, whiteNoiseType) ||
                other.whiteNoiseType == whiteNoiseType));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, id, startTime, endTime,
      durationMinutes, focusType, status, taskId, taskTitle, whiteNoiseType);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusSessionDetailImplCopyWith<_$FocusSessionDetailImpl> get copyWith =>
      __$$FocusSessionDetailImplCopyWithImpl<_$FocusSessionDetailImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusSessionDetailImplToJson(
      this,
    );
  }
}

abstract class _FocusSessionDetail implements FocusSessionDetail {
  const factory _FocusSessionDetail(
          {required final String id,
          @JsonKey(name: 'start_time') required final DateTime startTime,
          @JsonKey(name: 'end_time') required final DateTime endTime,
          @JsonKey(name: 'duration_minutes') required final int durationMinutes,
          @JsonKey(name: 'focus_type') required final String focusType,
          required final String status,
          @JsonKey(name: 'task_id') final String? taskId,
          @JsonKey(name: 'task_title') final String? taskTitle,
          @JsonKey(name: 'white_noise_type') final int? whiteNoiseType}) =
      _$FocusSessionDetailImpl;

  factory _FocusSessionDetail.fromJson(Map<String, dynamic> json) =
      _$FocusSessionDetailImpl.fromJson;

  @override
  String get id;
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
  @JsonKey(name: 'task_id')
  String? get taskId;
  @override
  @JsonKey(name: 'task_title')
  String? get taskTitle;
  @override
  @JsonKey(name: 'white_noise_type')
  int? get whiteNoiseType;
  @override
  @JsonKey(ignore: true)
  _$$FocusSessionDetailImplCopyWith<_$FocusSessionDetailImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

FocusSessionHistoryResponse _$FocusSessionHistoryResponseFromJson(
    Map<String, dynamic> json) {
  return _FocusSessionHistoryResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusSessionHistoryResponse {
  List<FocusSessionDetail> get sessions => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_count')
  int get totalCount => throw _privateConstructorUsedError;
  int get limit => throw _privateConstructorUsedError;
  int get offset => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusSessionHistoryResponseCopyWith<FocusSessionHistoryResponse>
      get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusSessionHistoryResponseCopyWith<$Res> {
  factory $FocusSessionHistoryResponseCopyWith(
          FocusSessionHistoryResponse value,
          $Res Function(FocusSessionHistoryResponse) then) =
      _$FocusSessionHistoryResponseCopyWithImpl<$Res,
          FocusSessionHistoryResponse>;
  @useResult
  $Res call(
      {List<FocusSessionDetail> sessions,
      @JsonKey(name: 'total_count') int totalCount,
      int limit,
      int offset});
}

/// @nodoc
class _$FocusSessionHistoryResponseCopyWithImpl<$Res,
        $Val extends FocusSessionHistoryResponse>
    implements $FocusSessionHistoryResponseCopyWith<$Res> {
  _$FocusSessionHistoryResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? sessions = null,
    Object? totalCount = null,
    Object? limit = null,
    Object? offset = null,
  }) {
    return _then(_value.copyWith(
      sessions: null == sessions
          ? _value.sessions
          : sessions // ignore: cast_nullable_to_non_nullable
              as List<FocusSessionDetail>,
      totalCount: null == totalCount
          ? _value.totalCount
          : totalCount // ignore: cast_nullable_to_non_nullable
              as int,
      limit: null == limit
          ? _value.limit
          : limit // ignore: cast_nullable_to_non_nullable
              as int,
      offset: null == offset
          ? _value.offset
          : offset // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusSessionHistoryResponseImplCopyWith<$Res>
    implements $FocusSessionHistoryResponseCopyWith<$Res> {
  factory _$$FocusSessionHistoryResponseImplCopyWith(
          _$FocusSessionHistoryResponseImpl value,
          $Res Function(_$FocusSessionHistoryResponseImpl) then) =
      __$$FocusSessionHistoryResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<FocusSessionDetail> sessions,
      @JsonKey(name: 'total_count') int totalCount,
      int limit,
      int offset});
}

/// @nodoc
class __$$FocusSessionHistoryResponseImplCopyWithImpl<$Res>
    extends _$FocusSessionHistoryResponseCopyWithImpl<$Res,
        _$FocusSessionHistoryResponseImpl>
    implements _$$FocusSessionHistoryResponseImplCopyWith<$Res> {
  __$$FocusSessionHistoryResponseImplCopyWithImpl(
      _$FocusSessionHistoryResponseImpl _value,
      $Res Function(_$FocusSessionHistoryResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? sessions = null,
    Object? totalCount = null,
    Object? limit = null,
    Object? offset = null,
  }) {
    return _then(_$FocusSessionHistoryResponseImpl(
      sessions: null == sessions
          ? _value._sessions
          : sessions // ignore: cast_nullable_to_non_nullable
              as List<FocusSessionDetail>,
      totalCount: null == totalCount
          ? _value.totalCount
          : totalCount // ignore: cast_nullable_to_non_nullable
              as int,
      limit: null == limit
          ? _value.limit
          : limit // ignore: cast_nullable_to_non_nullable
              as int,
      offset: null == offset
          ? _value.offset
          : offset // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusSessionHistoryResponseImpl
    implements _FocusSessionHistoryResponse {
  const _$FocusSessionHistoryResponseImpl(
      {required final List<FocusSessionDetail> sessions,
      @JsonKey(name: 'total_count') required this.totalCount,
      required this.limit,
      required this.offset})
      : _sessions = sessions;

  factory _$FocusSessionHistoryResponseImpl.fromJson(
          Map<String, dynamic> json) =>
      _$$FocusSessionHistoryResponseImplFromJson(json);

  final List<FocusSessionDetail> _sessions;
  @override
  List<FocusSessionDetail> get sessions {
    if (_sessions is EqualUnmodifiableListView) return _sessions;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_sessions);
  }

  @override
  @JsonKey(name: 'total_count')
  final int totalCount;
  @override
  final int limit;
  @override
  final int offset;

  @override
  String toString() {
    return 'FocusSessionHistoryResponse(sessions: $sessions, totalCount: $totalCount, limit: $limit, offset: $offset)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusSessionHistoryResponseImpl &&
            const DeepCollectionEquality().equals(other._sessions, _sessions) &&
            (identical(other.totalCount, totalCount) ||
                other.totalCount == totalCount) &&
            (identical(other.limit, limit) || other.limit == limit) &&
            (identical(other.offset, offset) || other.offset == offset));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_sessions),
      totalCount,
      limit,
      offset);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusSessionHistoryResponseImplCopyWith<_$FocusSessionHistoryResponseImpl>
      get copyWith => __$$FocusSessionHistoryResponseImplCopyWithImpl<
          _$FocusSessionHistoryResponseImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusSessionHistoryResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusSessionHistoryResponse
    implements FocusSessionHistoryResponse {
  const factory _FocusSessionHistoryResponse(
      {required final List<FocusSessionDetail> sessions,
      @JsonKey(name: 'total_count') required final int totalCount,
      required final int limit,
      required final int offset}) = _$FocusSessionHistoryResponseImpl;

  factory _FocusSessionHistoryResponse.fromJson(Map<String, dynamic> json) =
      _$FocusSessionHistoryResponseImpl.fromJson;

  @override
  List<FocusSessionDetail> get sessions;
  @override
  @JsonKey(name: 'total_count')
  int get totalCount;
  @override
  int get limit;
  @override
  int get offset;
  @override
  @JsonKey(ignore: true)
  _$$FocusSessionHistoryResponseImplCopyWith<_$FocusSessionHistoryResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}

FocusHeatmapResponse _$FocusHeatmapResponseFromJson(Map<String, dynamic> json) {
  return _FocusHeatmapResponse.fromJson(json);
}

/// @nodoc
mixin _$FocusHeatmapResponse {
  Map<String, double> get data => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $FocusHeatmapResponseCopyWith<FocusHeatmapResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $FocusHeatmapResponseCopyWith<$Res> {
  factory $FocusHeatmapResponseCopyWith(FocusHeatmapResponse value,
          $Res Function(FocusHeatmapResponse) then) =
      _$FocusHeatmapResponseCopyWithImpl<$Res, FocusHeatmapResponse>;
  @useResult
  $Res call({Map<String, double> data});
}

/// @nodoc
class _$FocusHeatmapResponseCopyWithImpl<$Res,
        $Val extends FocusHeatmapResponse>
    implements $FocusHeatmapResponseCopyWith<$Res> {
  _$FocusHeatmapResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? data = null,
  }) {
    return _then(_value.copyWith(
      data: null == data
          ? _value.data
          : data // ignore: cast_nullable_to_non_nullable
              as Map<String, double>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$FocusHeatmapResponseImplCopyWith<$Res>
    implements $FocusHeatmapResponseCopyWith<$Res> {
  factory _$$FocusHeatmapResponseImplCopyWith(_$FocusHeatmapResponseImpl value,
          $Res Function(_$FocusHeatmapResponseImpl) then) =
      __$$FocusHeatmapResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({Map<String, double> data});
}

/// @nodoc
class __$$FocusHeatmapResponseImplCopyWithImpl<$Res>
    extends _$FocusHeatmapResponseCopyWithImpl<$Res, _$FocusHeatmapResponseImpl>
    implements _$$FocusHeatmapResponseImplCopyWith<$Res> {
  __$$FocusHeatmapResponseImplCopyWithImpl(_$FocusHeatmapResponseImpl _value,
      $Res Function(_$FocusHeatmapResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? data = null,
  }) {
    return _then(_$FocusHeatmapResponseImpl(
      data: null == data
          ? _value._data
          : data // ignore: cast_nullable_to_non_nullable
              as Map<String, double>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$FocusHeatmapResponseImpl implements _FocusHeatmapResponse {
  const _$FocusHeatmapResponseImpl({required final Map<String, double> data})
      : _data = data;

  factory _$FocusHeatmapResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$FocusHeatmapResponseImplFromJson(json);

  final Map<String, double> _data;
  @override
  Map<String, double> get data {
    if (_data is EqualUnmodifiableMapView) return _data;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_data);
  }

  @override
  String toString() {
    return 'FocusHeatmapResponse(data: $data)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$FocusHeatmapResponseImpl &&
            const DeepCollectionEquality().equals(other._data, _data));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, const DeepCollectionEquality().hash(_data));

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$FocusHeatmapResponseImplCopyWith<_$FocusHeatmapResponseImpl>
      get copyWith =>
          __$$FocusHeatmapResponseImplCopyWithImpl<_$FocusHeatmapResponseImpl>(
              this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$FocusHeatmapResponseImplToJson(
      this,
    );
  }
}

abstract class _FocusHeatmapResponse implements FocusHeatmapResponse {
  const factory _FocusHeatmapResponse(
      {required final Map<String, double> data}) = _$FocusHeatmapResponseImpl;

  factory _FocusHeatmapResponse.fromJson(Map<String, dynamic> json) =
      _$FocusHeatmapResponseImpl.fromJson;

  @override
  Map<String, double> get data;
  @override
  @JsonKey(ignore: true)
  _$$FocusHeatmapResponseImplCopyWith<_$FocusHeatmapResponseImpl>
      get copyWith => throw _privateConstructorUsedError;
}
