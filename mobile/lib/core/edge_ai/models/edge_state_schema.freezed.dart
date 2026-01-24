// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'edge_state_schema.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

RawStateVector _$RawStateVectorFromJson(Map<String, dynamic> json) {
  return _RawStateVector.fromJson(json);
}

/// @nodoc
mixin _$RawStateVector {
  /// 注意力集中度 (0-100)
  @JsonKey(name: 'a')
  int get attention => throw _privateConstructorUsedError;

  /// 疲劳度 (0-100)
  @JsonKey(name: 'f')
  int get fatigue => throw _privateConstructorUsedError;

  /// 压力值 (0-100)
  @JsonKey(name: 's')
  int get stress => throw _privateConstructorUsedError;

  /// 拖延风险 (0-100)
  @JsonKey(name: 'p')
  int get procrastination => throw _privateConstructorUsedError;

  /// 推荐打断指数 (0-100, >60 建议打断)
  @JsonKey(name: 'i')
  int get interruptScore => throw _privateConstructorUsedError;

  /// 最佳介入时间窗口 (分钟, 0-120)
  @JsonKey(name: 'w')
  int get windowMinutes => throw _privateConstructorUsedError;

  /// 语气枚举 (0: gentle, 1: firm, 2: direct, 3: silent)
  @JsonKey(name: 't')
  int get toneEnum => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $RawStateVectorCopyWith<RawStateVector> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RawStateVectorCopyWith<$Res> {
  factory $RawStateVectorCopyWith(
          RawStateVector value, $Res Function(RawStateVector) then) =
      _$RawStateVectorCopyWithImpl<$Res, RawStateVector>;
  @useResult
  $Res call(
      {@JsonKey(name: 'a') int attention,
      @JsonKey(name: 'f') int fatigue,
      @JsonKey(name: 's') int stress,
      @JsonKey(name: 'p') int procrastination,
      @JsonKey(name: 'i') int interruptScore,
      @JsonKey(name: 'w') int windowMinutes,
      @JsonKey(name: 't') int toneEnum});
}

/// @nodoc
class _$RawStateVectorCopyWithImpl<$Res, $Val extends RawStateVector>
    implements $RawStateVectorCopyWith<$Res> {
  _$RawStateVectorCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attention = null,
    Object? fatigue = null,
    Object? stress = null,
    Object? procrastination = null,
    Object? interruptScore = null,
    Object? windowMinutes = null,
    Object? toneEnum = null,
  }) {
    return _then(_value.copyWith(
      attention: null == attention
          ? _value.attention
          : attention // ignore: cast_nullable_to_non_nullable
              as int,
      fatigue: null == fatigue
          ? _value.fatigue
          : fatigue // ignore: cast_nullable_to_non_nullable
              as int,
      stress: null == stress
          ? _value.stress
          : stress // ignore: cast_nullable_to_non_nullable
              as int,
      procrastination: null == procrastination
          ? _value.procrastination
          : procrastination // ignore: cast_nullable_to_non_nullable
              as int,
      interruptScore: null == interruptScore
          ? _value.interruptScore
          : interruptScore // ignore: cast_nullable_to_non_nullable
              as int,
      windowMinutes: null == windowMinutes
          ? _value.windowMinutes
          : windowMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      toneEnum: null == toneEnum
          ? _value.toneEnum
          : toneEnum // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$RawStateVectorImplCopyWith<$Res>
    implements $RawStateVectorCopyWith<$Res> {
  factory _$$RawStateVectorImplCopyWith(_$RawStateVectorImpl value,
          $Res Function(_$RawStateVectorImpl) then) =
      __$$RawStateVectorImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'a') int attention,
      @JsonKey(name: 'f') int fatigue,
      @JsonKey(name: 's') int stress,
      @JsonKey(name: 'p') int procrastination,
      @JsonKey(name: 'i') int interruptScore,
      @JsonKey(name: 'w') int windowMinutes,
      @JsonKey(name: 't') int toneEnum});
}

/// @nodoc
class __$$RawStateVectorImplCopyWithImpl<$Res>
    extends _$RawStateVectorCopyWithImpl<$Res, _$RawStateVectorImpl>
    implements _$$RawStateVectorImplCopyWith<$Res> {
  __$$RawStateVectorImplCopyWithImpl(
      _$RawStateVectorImpl _value, $Res Function(_$RawStateVectorImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attention = null,
    Object? fatigue = null,
    Object? stress = null,
    Object? procrastination = null,
    Object? interruptScore = null,
    Object? windowMinutes = null,
    Object? toneEnum = null,
  }) {
    return _then(_$RawStateVectorImpl(
      attention: null == attention
          ? _value.attention
          : attention // ignore: cast_nullable_to_non_nullable
              as int,
      fatigue: null == fatigue
          ? _value.fatigue
          : fatigue // ignore: cast_nullable_to_non_nullable
              as int,
      stress: null == stress
          ? _value.stress
          : stress // ignore: cast_nullable_to_non_nullable
              as int,
      procrastination: null == procrastination
          ? _value.procrastination
          : procrastination // ignore: cast_nullable_to_non_nullable
              as int,
      interruptScore: null == interruptScore
          ? _value.interruptScore
          : interruptScore // ignore: cast_nullable_to_non_nullable
              as int,
      windowMinutes: null == windowMinutes
          ? _value.windowMinutes
          : windowMinutes // ignore: cast_nullable_to_non_nullable
              as int,
      toneEnum: null == toneEnum
          ? _value.toneEnum
          : toneEnum // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$RawStateVectorImpl implements _RawStateVector {
  const _$RawStateVectorImpl(
      {@JsonKey(name: 'a') required this.attention,
      @JsonKey(name: 'f') required this.fatigue,
      @JsonKey(name: 's') required this.stress,
      @JsonKey(name: 'p') required this.procrastination,
      @JsonKey(name: 'i') required this.interruptScore,
      @JsonKey(name: 'w') required this.windowMinutes,
      @JsonKey(name: 't') required this.toneEnum});

  factory _$RawStateVectorImpl.fromJson(Map<String, dynamic> json) =>
      _$$RawStateVectorImplFromJson(json);

  /// 注意力集中度 (0-100)
  @override
  @JsonKey(name: 'a')
  final int attention;

  /// 疲劳度 (0-100)
  @override
  @JsonKey(name: 'f')
  final int fatigue;

  /// 压力值 (0-100)
  @override
  @JsonKey(name: 's')
  final int stress;

  /// 拖延风险 (0-100)
  @override
  @JsonKey(name: 'p')
  final int procrastination;

  /// 推荐打断指数 (0-100, >60 建议打断)
  @override
  @JsonKey(name: 'i')
  final int interruptScore;

  /// 最佳介入时间窗口 (分钟, 0-120)
  @override
  @JsonKey(name: 'w')
  final int windowMinutes;

  /// 语气枚举 (0: gentle, 1: firm, 2: direct, 3: silent)
  @override
  @JsonKey(name: 't')
  final int toneEnum;

  @override
  String toString() {
    return 'RawStateVector(attention: $attention, fatigue: $fatigue, stress: $stress, procrastination: $procrastination, interruptScore: $interruptScore, windowMinutes: $windowMinutes, toneEnum: $toneEnum)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RawStateVectorImpl &&
            (identical(other.attention, attention) ||
                other.attention == attention) &&
            (identical(other.fatigue, fatigue) || other.fatigue == fatigue) &&
            (identical(other.stress, stress) || other.stress == stress) &&
            (identical(other.procrastination, procrastination) ||
                other.procrastination == procrastination) &&
            (identical(other.interruptScore, interruptScore) ||
                other.interruptScore == interruptScore) &&
            (identical(other.windowMinutes, windowMinutes) ||
                other.windowMinutes == windowMinutes) &&
            (identical(other.toneEnum, toneEnum) ||
                other.toneEnum == toneEnum));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, attention, fatigue, stress,
      procrastination, interruptScore, windowMinutes, toneEnum);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$RawStateVectorImplCopyWith<_$RawStateVectorImpl> get copyWith =>
      __$$RawStateVectorImplCopyWithImpl<_$RawStateVectorImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RawStateVectorImplToJson(
      this,
    );
  }
}

abstract class _RawStateVector implements RawStateVector {
  const factory _RawStateVector(
      {@JsonKey(name: 'a') required final int attention,
      @JsonKey(name: 'f') required final int fatigue,
      @JsonKey(name: 's') required final int stress,
      @JsonKey(name: 'p') required final int procrastination,
      @JsonKey(name: 'i') required final int interruptScore,
      @JsonKey(name: 'w') required final int windowMinutes,
      @JsonKey(name: 't') required final int toneEnum}) = _$RawStateVectorImpl;

  factory _RawStateVector.fromJson(Map<String, dynamic> json) =
      _$RawStateVectorImpl.fromJson;

  @override

  /// 注意力集中度 (0-100)
  @JsonKey(name: 'a')
  int get attention;
  @override

  /// 疲劳度 (0-100)
  @JsonKey(name: 'f')
  int get fatigue;
  @override

  /// 压力值 (0-100)
  @JsonKey(name: 's')
  int get stress;
  @override

  /// 拖延风险 (0-100)
  @JsonKey(name: 'p')
  int get procrastination;
  @override

  /// 推荐打断指数 (0-100, >60 建议打断)
  @JsonKey(name: 'i')
  int get interruptScore;
  @override

  /// 最佳介入时间窗口 (分钟, 0-120)
  @JsonKey(name: 'w')
  int get windowMinutes;
  @override

  /// 语气枚举 (0: gentle, 1: firm, 2: direct, 3: silent)
  @JsonKey(name: 't')
  int get toneEnum;
  @override
  @JsonKey(ignore: true)
  _$$RawStateVectorImplCopyWith<_$RawStateVectorImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

EdgeState _$EdgeStateFromJson(Map<String, dynamic> json) {
  return _EdgeState.fromJson(json);
}

/// @nodoc
mixin _$EdgeState {
  double get attentionScore => throw _privateConstructorUsedError; // 0.0 - 1.0
  double get fatigueScore => throw _privateConstructorUsedError; // 0.0 - 1.0
  double get stressScore => throw _privateConstructorUsedError; // 0.0 - 1.0
  bool get shouldInterrupt => throw _privateConstructorUsedError;
  String get nudgeTone =>
      throw _privateConstructorUsedError; // 'gentle', 'firm', etc.
  Duration get bestWindow => throw _privateConstructorUsedError;
  int get timestamp => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $EdgeStateCopyWith<EdgeState> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $EdgeStateCopyWith<$Res> {
  factory $EdgeStateCopyWith(EdgeState value, $Res Function(EdgeState) then) =
      _$EdgeStateCopyWithImpl<$Res, EdgeState>;
  @useResult
  $Res call(
      {double attentionScore,
      double fatigueScore,
      double stressScore,
      bool shouldInterrupt,
      String nudgeTone,
      Duration bestWindow,
      int timestamp});
}

/// @nodoc
class _$EdgeStateCopyWithImpl<$Res, $Val extends EdgeState>
    implements $EdgeStateCopyWith<$Res> {
  _$EdgeStateCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attentionScore = null,
    Object? fatigueScore = null,
    Object? stressScore = null,
    Object? shouldInterrupt = null,
    Object? nudgeTone = null,
    Object? bestWindow = null,
    Object? timestamp = null,
  }) {
    return _then(_value.copyWith(
      attentionScore: null == attentionScore
          ? _value.attentionScore
          : attentionScore // ignore: cast_nullable_to_non_nullable
              as double,
      fatigueScore: null == fatigueScore
          ? _value.fatigueScore
          : fatigueScore // ignore: cast_nullable_to_non_nullable
              as double,
      stressScore: null == stressScore
          ? _value.stressScore
          : stressScore // ignore: cast_nullable_to_non_nullable
              as double,
      shouldInterrupt: null == shouldInterrupt
          ? _value.shouldInterrupt
          : shouldInterrupt // ignore: cast_nullable_to_non_nullable
              as bool,
      nudgeTone: null == nudgeTone
          ? _value.nudgeTone
          : nudgeTone // ignore: cast_nullable_to_non_nullable
              as String,
      bestWindow: null == bestWindow
          ? _value.bestWindow
          : bestWindow // ignore: cast_nullable_to_non_nullable
              as Duration,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as int,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$EdgeStateImplCopyWith<$Res>
    implements $EdgeStateCopyWith<$Res> {
  factory _$$EdgeStateImplCopyWith(
          _$EdgeStateImpl value, $Res Function(_$EdgeStateImpl) then) =
      __$$EdgeStateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {double attentionScore,
      double fatigueScore,
      double stressScore,
      bool shouldInterrupt,
      String nudgeTone,
      Duration bestWindow,
      int timestamp});
}

/// @nodoc
class __$$EdgeStateImplCopyWithImpl<$Res>
    extends _$EdgeStateCopyWithImpl<$Res, _$EdgeStateImpl>
    implements _$$EdgeStateImplCopyWith<$Res> {
  __$$EdgeStateImplCopyWithImpl(
      _$EdgeStateImpl _value, $Res Function(_$EdgeStateImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? attentionScore = null,
    Object? fatigueScore = null,
    Object? stressScore = null,
    Object? shouldInterrupt = null,
    Object? nudgeTone = null,
    Object? bestWindow = null,
    Object? timestamp = null,
  }) {
    return _then(_$EdgeStateImpl(
      attentionScore: null == attentionScore
          ? _value.attentionScore
          : attentionScore // ignore: cast_nullable_to_non_nullable
              as double,
      fatigueScore: null == fatigueScore
          ? _value.fatigueScore
          : fatigueScore // ignore: cast_nullable_to_non_nullable
              as double,
      stressScore: null == stressScore
          ? _value.stressScore
          : stressScore // ignore: cast_nullable_to_non_nullable
              as double,
      shouldInterrupt: null == shouldInterrupt
          ? _value.shouldInterrupt
          : shouldInterrupt // ignore: cast_nullable_to_non_nullable
              as bool,
      nudgeTone: null == nudgeTone
          ? _value.nudgeTone
          : nudgeTone // ignore: cast_nullable_to_non_nullable
              as String,
      bestWindow: null == bestWindow
          ? _value.bestWindow
          : bestWindow // ignore: cast_nullable_to_non_nullable
              as Duration,
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as int,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$EdgeStateImpl implements _EdgeState {
  const _$EdgeStateImpl(
      {required this.attentionScore,
      required this.fatigueScore,
      required this.stressScore,
      required this.shouldInterrupt,
      required this.nudgeTone,
      required this.bestWindow,
      required this.timestamp});

  factory _$EdgeStateImpl.fromJson(Map<String, dynamic> json) =>
      _$$EdgeStateImplFromJson(json);

  @override
  final double attentionScore;
// 0.0 - 1.0
  @override
  final double fatigueScore;
// 0.0 - 1.0
  @override
  final double stressScore;
// 0.0 - 1.0
  @override
  final bool shouldInterrupt;
  @override
  final String nudgeTone;
// 'gentle', 'firm', etc.
  @override
  final Duration bestWindow;
  @override
  final int timestamp;

  @override
  String toString() {
    return 'EdgeState(attentionScore: $attentionScore, fatigueScore: $fatigueScore, stressScore: $stressScore, shouldInterrupt: $shouldInterrupt, nudgeTone: $nudgeTone, bestWindow: $bestWindow, timestamp: $timestamp)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$EdgeStateImpl &&
            (identical(other.attentionScore, attentionScore) ||
                other.attentionScore == attentionScore) &&
            (identical(other.fatigueScore, fatigueScore) ||
                other.fatigueScore == fatigueScore) &&
            (identical(other.stressScore, stressScore) ||
                other.stressScore == stressScore) &&
            (identical(other.shouldInterrupt, shouldInterrupt) ||
                other.shouldInterrupt == shouldInterrupt) &&
            (identical(other.nudgeTone, nudgeTone) ||
                other.nudgeTone == nudgeTone) &&
            (identical(other.bestWindow, bestWindow) ||
                other.bestWindow == bestWindow) &&
            (identical(other.timestamp, timestamp) ||
                other.timestamp == timestamp));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, attentionScore, fatigueScore,
      stressScore, shouldInterrupt, nudgeTone, bestWindow, timestamp);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$EdgeStateImplCopyWith<_$EdgeStateImpl> get copyWith =>
      __$$EdgeStateImplCopyWithImpl<_$EdgeStateImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$EdgeStateImplToJson(
      this,
    );
  }
}

abstract class _EdgeState implements EdgeState {
  const factory _EdgeState(
      {required final double attentionScore,
      required final double fatigueScore,
      required final double stressScore,
      required final bool shouldInterrupt,
      required final String nudgeTone,
      required final Duration bestWindow,
      required final int timestamp}) = _$EdgeStateImpl;

  factory _EdgeState.fromJson(Map<String, dynamic> json) =
      _$EdgeStateImpl.fromJson;

  @override
  double get attentionScore;
  @override // 0.0 - 1.0
  double get fatigueScore;
  @override // 0.0 - 1.0
  double get stressScore;
  @override // 0.0 - 1.0
  bool get shouldInterrupt;
  @override
  String get nudgeTone;
  @override // 'gentle', 'firm', etc.
  Duration get bestWindow;
  @override
  int get timestamp;
  @override
  @JsonKey(ignore: true)
  _$$EdgeStateImplCopyWith<_$EdgeStateImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
