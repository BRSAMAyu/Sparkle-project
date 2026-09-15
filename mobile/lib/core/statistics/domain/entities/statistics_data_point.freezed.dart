// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'statistics_data_point.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

StatisticsDataPoint _$StatisticsDataPointFromJson(Map<String, dynamic> json) {
  return _StatisticsDataPoint.fromJson(json);
}

/// @nodoc
mixin _$StatisticsDataPoint {
  /// The timestamp for this data point
  DateTime get timestamp => throw _privateConstructorUsedError;

  /// The primary value (e.g., minutes, count, score)
  double get value => throw _privateConstructorUsedError;

  /// Optional secondary value for dual-axis charts
  double? get secondaryValue => throw _privateConstructorUsedError;

  /// Optional label for this data point (e.g., "Mon", "Jan 1")
  String? get label => throw _privateConstructorUsedError;

  /// Optional metadata (for tooltips, etc.)
  Map<String, dynamic> get metadata => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $StatisticsDataPointCopyWith<StatisticsDataPoint> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $StatisticsDataPointCopyWith<$Res> {
  factory $StatisticsDataPointCopyWith(
          StatisticsDataPoint value, $Res Function(StatisticsDataPoint) then) =
      _$StatisticsDataPointCopyWithImpl<$Res, StatisticsDataPoint>;
  @useResult
  $Res call(
      {DateTime timestamp,
      double value,
      double? secondaryValue,
      String? label,
      Map<String, dynamic> metadata});
}

/// @nodoc
class _$StatisticsDataPointCopyWithImpl<$Res, $Val extends StatisticsDataPoint>
    implements $StatisticsDataPointCopyWith<$Res> {
  _$StatisticsDataPointCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? timestamp = null,
    Object? value = null,
    Object? secondaryValue = freezed,
    Object? label = freezed,
    Object? metadata = null,
  }) {
    return _then(_value.copyWith(
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as DateTime,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as double,
      secondaryValue: freezed == secondaryValue
          ? _value.secondaryValue
          : secondaryValue // ignore: cast_nullable_to_non_nullable
              as double?,
      label: freezed == label
          ? _value.label
          : label // ignore: cast_nullable_to_non_nullable
              as String?,
      metadata: null == metadata
          ? _value.metadata
          : metadata // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$StatisticsDataPointImplCopyWith<$Res>
    implements $StatisticsDataPointCopyWith<$Res> {
  factory _$$StatisticsDataPointImplCopyWith(_$StatisticsDataPointImpl value,
          $Res Function(_$StatisticsDataPointImpl) then) =
      __$$StatisticsDataPointImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {DateTime timestamp,
      double value,
      double? secondaryValue,
      String? label,
      Map<String, dynamic> metadata});
}

/// @nodoc
class __$$StatisticsDataPointImplCopyWithImpl<$Res>
    extends _$StatisticsDataPointCopyWithImpl<$Res, _$StatisticsDataPointImpl>
    implements _$$StatisticsDataPointImplCopyWith<$Res> {
  __$$StatisticsDataPointImplCopyWithImpl(_$StatisticsDataPointImpl _value,
      $Res Function(_$StatisticsDataPointImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? timestamp = null,
    Object? value = null,
    Object? secondaryValue = freezed,
    Object? label = freezed,
    Object? metadata = null,
  }) {
    return _then(_$StatisticsDataPointImpl(
      timestamp: null == timestamp
          ? _value.timestamp
          : timestamp // ignore: cast_nullable_to_non_nullable
              as DateTime,
      value: null == value
          ? _value.value
          : value // ignore: cast_nullable_to_non_nullable
              as double,
      secondaryValue: freezed == secondaryValue
          ? _value.secondaryValue
          : secondaryValue // ignore: cast_nullable_to_non_nullable
              as double?,
      label: freezed == label
          ? _value.label
          : label // ignore: cast_nullable_to_non_nullable
              as String?,
      metadata: null == metadata
          ? _value._metadata
          : metadata // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$StatisticsDataPointImpl implements _StatisticsDataPoint {
  const _$StatisticsDataPointImpl(
      {required this.timestamp,
      required this.value,
      this.secondaryValue,
      this.label,
      final Map<String, dynamic> metadata = const {}})
      : _metadata = metadata;

  factory _$StatisticsDataPointImpl.fromJson(Map<String, dynamic> json) =>
      _$$StatisticsDataPointImplFromJson(json);

  /// The timestamp for this data point
  @override
  final DateTime timestamp;

  /// The primary value (e.g., minutes, count, score)
  @override
  final double value;

  /// Optional secondary value for dual-axis charts
  @override
  final double? secondaryValue;

  /// Optional label for this data point (e.g., "Mon", "Jan 1")
  @override
  final String? label;

  /// Optional metadata (for tooltips, etc.)
  final Map<String, dynamic> _metadata;

  /// Optional metadata (for tooltips, etc.)
  @override
  @JsonKey()
  Map<String, dynamic> get metadata {
    if (_metadata is EqualUnmodifiableMapView) return _metadata;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_metadata);
  }

  @override
  String toString() {
    return 'StatisticsDataPoint(timestamp: $timestamp, value: $value, secondaryValue: $secondaryValue, label: $label, metadata: $metadata)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$StatisticsDataPointImpl &&
            (identical(other.timestamp, timestamp) ||
                other.timestamp == timestamp) &&
            (identical(other.value, value) || other.value == value) &&
            (identical(other.secondaryValue, secondaryValue) ||
                other.secondaryValue == secondaryValue) &&
            (identical(other.label, label) || other.label == label) &&
            const DeepCollectionEquality().equals(other._metadata, _metadata));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(runtimeType, timestamp, value, secondaryValue,
      label, const DeepCollectionEquality().hash(_metadata));

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$StatisticsDataPointImplCopyWith<_$StatisticsDataPointImpl> get copyWith =>
      __$$StatisticsDataPointImplCopyWithImpl<_$StatisticsDataPointImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$StatisticsDataPointImplToJson(
      this,
    );
  }
}

abstract class _StatisticsDataPoint implements StatisticsDataPoint {
  const factory _StatisticsDataPoint(
      {required final DateTime timestamp,
      required final double value,
      final double? secondaryValue,
      final String? label,
      final Map<String, dynamic> metadata}) = _$StatisticsDataPointImpl;

  factory _StatisticsDataPoint.fromJson(Map<String, dynamic> json) =
      _$StatisticsDataPointImpl.fromJson;

  @override

  /// The timestamp for this data point
  DateTime get timestamp;
  @override

  /// The primary value (e.g., minutes, count, score)
  double get value;
  @override

  /// Optional secondary value for dual-axis charts
  double? get secondaryValue;
  @override

  /// Optional label for this data point (e.g., "Mon", "Jan 1")
  String? get label;
  @override

  /// Optional metadata (for tooltips, etc.)
  Map<String, dynamic> get metadata;
  @override
  @JsonKey(ignore: true)
  _$$StatisticsDataPointImplCopyWith<_$StatisticsDataPointImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

StatisticsDataSeries _$StatisticsDataSeriesFromJson(Map<String, dynamic> json) {
  return _StatisticsDataSeries.fromJson(json);
}

/// @nodoc
mixin _$StatisticsDataSeries {
  /// Unique identifier for this series
  String get id => throw _privateConstructorUsedError;

  /// Display name for this series
  String get name => throw _privateConstructorUsedError;

  /// The data points in chronological order
  List<StatisticsDataPoint> get points => throw _privateConstructorUsedError;

  /// Color code for this series (hex or named)
  String? get color => throw _privateConstructorUsedError;

  /// Unit label for values (e.g., "分钟", "次", "分")
  String? get unit => throw _privateConstructorUsedError;

  /// Maximum value in the series
  double? get maxValue => throw _privateConstructorUsedError;

  /// Minimum value in the series
  double? get minValue => throw _privateConstructorUsedError;

  /// Average value across all points
  double? get averageValue => throw _privateConstructorUsedError;

  /// Total/sum of all values
  double? get totalValue => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $StatisticsDataSeriesCopyWith<StatisticsDataSeries> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $StatisticsDataSeriesCopyWith<$Res> {
  factory $StatisticsDataSeriesCopyWith(StatisticsDataSeries value,
          $Res Function(StatisticsDataSeries) then) =
      _$StatisticsDataSeriesCopyWithImpl<$Res, StatisticsDataSeries>;
  @useResult
  $Res call(
      {String id,
      String name,
      List<StatisticsDataPoint> points,
      String? color,
      String? unit,
      double? maxValue,
      double? minValue,
      double? averageValue,
      double? totalValue});
}

/// @nodoc
class _$StatisticsDataSeriesCopyWithImpl<$Res,
        $Val extends StatisticsDataSeries>
    implements $StatisticsDataSeriesCopyWith<$Res> {
  _$StatisticsDataSeriesCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? points = null,
    Object? color = freezed,
    Object? unit = freezed,
    Object? maxValue = freezed,
    Object? minValue = freezed,
    Object? averageValue = freezed,
    Object? totalValue = freezed,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value.points
          : points // ignore: cast_nullable_to_non_nullable
              as List<StatisticsDataPoint>,
      color: freezed == color
          ? _value.color
          : color // ignore: cast_nullable_to_non_nullable
              as String?,
      unit: freezed == unit
          ? _value.unit
          : unit // ignore: cast_nullable_to_non_nullable
              as String?,
      maxValue: freezed == maxValue
          ? _value.maxValue
          : maxValue // ignore: cast_nullable_to_non_nullable
              as double?,
      minValue: freezed == minValue
          ? _value.minValue
          : minValue // ignore: cast_nullable_to_non_nullable
              as double?,
      averageValue: freezed == averageValue
          ? _value.averageValue
          : averageValue // ignore: cast_nullable_to_non_nullable
              as double?,
      totalValue: freezed == totalValue
          ? _value.totalValue
          : totalValue // ignore: cast_nullable_to_non_nullable
              as double?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$StatisticsDataSeriesImplCopyWith<$Res>
    implements $StatisticsDataSeriesCopyWith<$Res> {
  factory _$$StatisticsDataSeriesImplCopyWith(_$StatisticsDataSeriesImpl value,
          $Res Function(_$StatisticsDataSeriesImpl) then) =
      __$$StatisticsDataSeriesImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      String name,
      List<StatisticsDataPoint> points,
      String? color,
      String? unit,
      double? maxValue,
      double? minValue,
      double? averageValue,
      double? totalValue});
}

/// @nodoc
class __$$StatisticsDataSeriesImplCopyWithImpl<$Res>
    extends _$StatisticsDataSeriesCopyWithImpl<$Res, _$StatisticsDataSeriesImpl>
    implements _$$StatisticsDataSeriesImplCopyWith<$Res> {
  __$$StatisticsDataSeriesImplCopyWithImpl(_$StatisticsDataSeriesImpl _value,
      $Res Function(_$StatisticsDataSeriesImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? name = null,
    Object? points = null,
    Object? color = freezed,
    Object? unit = freezed,
    Object? maxValue = freezed,
    Object? minValue = freezed,
    Object? averageValue = freezed,
    Object? totalValue = freezed,
  }) {
    return _then(_$StatisticsDataSeriesImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      points: null == points
          ? _value._points
          : points // ignore: cast_nullable_to_non_nullable
              as List<StatisticsDataPoint>,
      color: freezed == color
          ? _value.color
          : color // ignore: cast_nullable_to_non_nullable
              as String?,
      unit: freezed == unit
          ? _value.unit
          : unit // ignore: cast_nullable_to_non_nullable
              as String?,
      maxValue: freezed == maxValue
          ? _value.maxValue
          : maxValue // ignore: cast_nullable_to_non_nullable
              as double?,
      minValue: freezed == minValue
          ? _value.minValue
          : minValue // ignore: cast_nullable_to_non_nullable
              as double?,
      averageValue: freezed == averageValue
          ? _value.averageValue
          : averageValue // ignore: cast_nullable_to_non_nullable
              as double?,
      totalValue: freezed == totalValue
          ? _value.totalValue
          : totalValue // ignore: cast_nullable_to_non_nullable
              as double?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$StatisticsDataSeriesImpl extends _StatisticsDataSeries {
  const _$StatisticsDataSeriesImpl(
      {required this.id,
      required this.name,
      required final List<StatisticsDataPoint> points,
      this.color,
      this.unit,
      this.maxValue,
      this.minValue,
      this.averageValue,
      this.totalValue})
      : _points = points,
        super._();

  factory _$StatisticsDataSeriesImpl.fromJson(Map<String, dynamic> json) =>
      _$$StatisticsDataSeriesImplFromJson(json);

  /// Unique identifier for this series
  @override
  final String id;

  /// Display name for this series
  @override
  final String name;

  /// The data points in chronological order
  final List<StatisticsDataPoint> _points;

  /// The data points in chronological order
  @override
  List<StatisticsDataPoint> get points {
    if (_points is EqualUnmodifiableListView) return _points;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_points);
  }

  /// Color code for this series (hex or named)
  @override
  final String? color;

  /// Unit label for values (e.g., "分钟", "次", "分")
  @override
  final String? unit;

  /// Maximum value in the series
  @override
  final double? maxValue;

  /// Minimum value in the series
  @override
  final double? minValue;

  /// Average value across all points
  @override
  final double? averageValue;

  /// Total/sum of all values
  @override
  final double? totalValue;

  @override
  String toString() {
    return 'StatisticsDataSeries(id: $id, name: $name, points: $points, color: $color, unit: $unit, maxValue: $maxValue, minValue: $minValue, averageValue: $averageValue, totalValue: $totalValue)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$StatisticsDataSeriesImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            const DeepCollectionEquality().equals(other._points, _points) &&
            (identical(other.color, color) || other.color == color) &&
            (identical(other.unit, unit) || other.unit == unit) &&
            (identical(other.maxValue, maxValue) ||
                other.maxValue == maxValue) &&
            (identical(other.minValue, minValue) ||
                other.minValue == minValue) &&
            (identical(other.averageValue, averageValue) ||
                other.averageValue == averageValue) &&
            (identical(other.totalValue, totalValue) ||
                other.totalValue == totalValue));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      name,
      const DeepCollectionEquality().hash(_points),
      color,
      unit,
      maxValue,
      minValue,
      averageValue,
      totalValue);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$StatisticsDataSeriesImplCopyWith<_$StatisticsDataSeriesImpl>
      get copyWith =>
          __$$StatisticsDataSeriesImplCopyWithImpl<_$StatisticsDataSeriesImpl>(
              this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$StatisticsDataSeriesImplToJson(
      this,
    );
  }
}

abstract class _StatisticsDataSeries extends StatisticsDataSeries {
  const factory _StatisticsDataSeries(
      {required final String id,
      required final String name,
      required final List<StatisticsDataPoint> points,
      final String? color,
      final String? unit,
      final double? maxValue,
      final double? minValue,
      final double? averageValue,
      final double? totalValue}) = _$StatisticsDataSeriesImpl;
  const _StatisticsDataSeries._() : super._();

  factory _StatisticsDataSeries.fromJson(Map<String, dynamic> json) =
      _$StatisticsDataSeriesImpl.fromJson;

  @override

  /// Unique identifier for this series
  String get id;
  @override

  /// Display name for this series
  String get name;
  @override

  /// The data points in chronological order
  List<StatisticsDataPoint> get points;
  @override

  /// Color code for this series (hex or named)
  String? get color;
  @override

  /// Unit label for values (e.g., "分钟", "次", "分")
  String? get unit;
  @override

  /// Maximum value in the series
  double? get maxValue;
  @override

  /// Minimum value in the series
  double? get minValue;
  @override

  /// Average value across all points
  double? get averageValue;
  @override

  /// Total/sum of all values
  double? get totalValue;
  @override
  @JsonKey(ignore: true)
  _$$StatisticsDataSeriesImplCopyWith<_$StatisticsDataSeriesImpl>
      get copyWith => throw _privateConstructorUsedError;
}
