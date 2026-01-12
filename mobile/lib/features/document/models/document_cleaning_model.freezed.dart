// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'document_cleaning_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

CleaningTaskStatus _$CleaningTaskStatusFromJson(Map<String, dynamic> json) {
  return _CleaningTaskStatus.fromJson(json);
}

/// @nodoc
mixin _$CleaningTaskStatus {
  String get status =>
      throw _privateConstructorUsedError; // queued, processing, completed, failed
  int get percent => throw _privateConstructorUsedError;
  String get message => throw _privateConstructorUsedError;
  CleaningResult? get result => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CleaningTaskStatusCopyWith<CleaningTaskStatus> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CleaningTaskStatusCopyWith<$Res> {
  factory $CleaningTaskStatusCopyWith(
          CleaningTaskStatus value, $Res Function(CleaningTaskStatus) then) =
      _$CleaningTaskStatusCopyWithImpl<$Res, CleaningTaskStatus>;
  @useResult
  $Res call(
      {String status, int percent, String message, CleaningResult? result});

  $CleaningResultCopyWith<$Res>? get result;
}

/// @nodoc
class _$CleaningTaskStatusCopyWithImpl<$Res, $Val extends CleaningTaskStatus>
    implements $CleaningTaskStatusCopyWith<$Res> {
  _$CleaningTaskStatusCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? percent = null,
    Object? message = null,
    Object? result = freezed,
  }) {
    return _then(_value.copyWith(
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      percent: null == percent
          ? _value.percent
          : percent // ignore: cast_nullable_to_non_nullable
              as int,
      message: null == message
          ? _value.message
          : message // ignore: cast_nullable_to_non_nullable
              as String,
      result: freezed == result
          ? _value.result
          : result // ignore: cast_nullable_to_non_nullable
              as CleaningResult?,
    ) as $Val);
  }

  @override
  @pragma('vm:prefer-inline')
  $CleaningResultCopyWith<$Res>? get result {
    if (_value.result == null) {
      return null;
    }

    return $CleaningResultCopyWith<$Res>(_value.result!, (value) {
      return _then(_value.copyWith(result: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$CleaningTaskStatusImplCopyWith<$Res>
    implements $CleaningTaskStatusCopyWith<$Res> {
  factory _$$CleaningTaskStatusImplCopyWith(_$CleaningTaskStatusImpl value,
          $Res Function(_$CleaningTaskStatusImpl) then) =
      __$$CleaningTaskStatusImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String status, int percent, String message, CleaningResult? result});

  @override
  $CleaningResultCopyWith<$Res>? get result;
}

/// @nodoc
class __$$CleaningTaskStatusImplCopyWithImpl<$Res>
    extends _$CleaningTaskStatusCopyWithImpl<$Res, _$CleaningTaskStatusImpl>
    implements _$$CleaningTaskStatusImplCopyWith<$Res> {
  __$$CleaningTaskStatusImplCopyWithImpl(_$CleaningTaskStatusImpl _value,
      $Res Function(_$CleaningTaskStatusImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? percent = null,
    Object? message = null,
    Object? result = freezed,
  }) {
    return _then(_$CleaningTaskStatusImpl(
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      percent: null == percent
          ? _value.percent
          : percent // ignore: cast_nullable_to_non_nullable
              as int,
      message: null == message
          ? _value.message
          : message // ignore: cast_nullable_to_non_nullable
              as String,
      result: freezed == result
          ? _value.result
          : result // ignore: cast_nullable_to_non_nullable
              as CleaningResult?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CleaningTaskStatusImpl implements _CleaningTaskStatus {
  const _$CleaningTaskStatusImpl(
      {required this.status,
      required this.percent,
      required this.message,
      this.result});

  factory _$CleaningTaskStatusImpl.fromJson(Map<String, dynamic> json) =>
      _$$CleaningTaskStatusImplFromJson(json);

  @override
  final String status;
// queued, processing, completed, failed
  @override
  final int percent;
  @override
  final String message;
  @override
  final CleaningResult? result;

  @override
  String toString() {
    return 'CleaningTaskStatus(status: $status, percent: $percent, message: $message, result: $result)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CleaningTaskStatusImpl &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.percent, percent) || other.percent == percent) &&
            (identical(other.message, message) || other.message == message) &&
            (identical(other.result, result) || other.result == result));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, status, percent, message, result);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CleaningTaskStatusImplCopyWith<_$CleaningTaskStatusImpl> get copyWith =>
      __$$CleaningTaskStatusImplCopyWithImpl<_$CleaningTaskStatusImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CleaningTaskStatusImplToJson(
      this,
    );
  }
}

abstract class _CleaningTaskStatus implements CleaningTaskStatus {
  const factory _CleaningTaskStatus(
      {required final String status,
      required final int percent,
      required final String message,
      final CleaningResult? result}) = _$CleaningTaskStatusImpl;

  factory _CleaningTaskStatus.fromJson(Map<String, dynamic> json) =
      _$CleaningTaskStatusImpl.fromJson;

  @override
  String get status;
  @override // queued, processing, completed, failed
  int get percent;
  @override
  String get message;
  @override
  CleaningResult? get result;
  @override
  @JsonKey(ignore: true)
  _$$CleaningTaskStatusImplCopyWith<_$CleaningTaskStatusImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

CleaningResult _$CleaningResultFromJson(Map<String, dynamic> json) {
  return _CleaningResult.fromJson(json);
}

/// @nodoc
mixin _$CleaningResult {
  String get status => throw _privateConstructorUsedError;
  String get mode =>
      throw _privateConstructorUsedError; // full_text, map_reduce
  String get summary => throw _privateConstructorUsedError;
  @JsonKey(name: 'full_text')
  String? get fullText => throw _privateConstructorUsedError;
  @JsonKey(name: 'full_text_preview')
  String? get fullTextPreview => throw _privateConstructorUsedError;
  @JsonKey(name: 'char_count')
  int? get charCount => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $CleaningResultCopyWith<CleaningResult> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CleaningResultCopyWith<$Res> {
  factory $CleaningResultCopyWith(
          CleaningResult value, $Res Function(CleaningResult) then) =
      _$CleaningResultCopyWithImpl<$Res, CleaningResult>;
  @useResult
  $Res call(
      {String status,
      String mode,
      String summary,
      @JsonKey(name: 'full_text') String? fullText,
      @JsonKey(name: 'full_text_preview') String? fullTextPreview,
      @JsonKey(name: 'char_count') int? charCount});
}

/// @nodoc
class _$CleaningResultCopyWithImpl<$Res, $Val extends CleaningResult>
    implements $CleaningResultCopyWith<$Res> {
  _$CleaningResultCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? mode = null,
    Object? summary = null,
    Object? fullText = freezed,
    Object? fullTextPreview = freezed,
    Object? charCount = freezed,
  }) {
    return _then(_value.copyWith(
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      mode: null == mode
          ? _value.mode
          : mode // ignore: cast_nullable_to_non_nullable
              as String,
      summary: null == summary
          ? _value.summary
          : summary // ignore: cast_nullable_to_non_nullable
              as String,
      fullText: freezed == fullText
          ? _value.fullText
          : fullText // ignore: cast_nullable_to_non_nullable
              as String?,
      fullTextPreview: freezed == fullTextPreview
          ? _value.fullTextPreview
          : fullTextPreview // ignore: cast_nullable_to_non_nullable
              as String?,
      charCount: freezed == charCount
          ? _value.charCount
          : charCount // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$CleaningResultImplCopyWith<$Res>
    implements $CleaningResultCopyWith<$Res> {
  factory _$$CleaningResultImplCopyWith(_$CleaningResultImpl value,
          $Res Function(_$CleaningResultImpl) then) =
      __$$CleaningResultImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String status,
      String mode,
      String summary,
      @JsonKey(name: 'full_text') String? fullText,
      @JsonKey(name: 'full_text_preview') String? fullTextPreview,
      @JsonKey(name: 'char_count') int? charCount});
}

/// @nodoc
class __$$CleaningResultImplCopyWithImpl<$Res>
    extends _$CleaningResultCopyWithImpl<$Res, _$CleaningResultImpl>
    implements _$$CleaningResultImplCopyWith<$Res> {
  __$$CleaningResultImplCopyWithImpl(
      _$CleaningResultImpl _value, $Res Function(_$CleaningResultImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? mode = null,
    Object? summary = null,
    Object? fullText = freezed,
    Object? fullTextPreview = freezed,
    Object? charCount = freezed,
  }) {
    return _then(_$CleaningResultImpl(
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      mode: null == mode
          ? _value.mode
          : mode // ignore: cast_nullable_to_non_nullable
              as String,
      summary: null == summary
          ? _value.summary
          : summary // ignore: cast_nullable_to_non_nullable
              as String,
      fullText: freezed == fullText
          ? _value.fullText
          : fullText // ignore: cast_nullable_to_non_nullable
              as String?,
      fullTextPreview: freezed == fullTextPreview
          ? _value.fullTextPreview
          : fullTextPreview // ignore: cast_nullable_to_non_nullable
              as String?,
      charCount: freezed == charCount
          ? _value.charCount
          : charCount // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$CleaningResultImpl implements _CleaningResult {
  const _$CleaningResultImpl(
      {required this.status,
      required this.mode,
      required this.summary,
      @JsonKey(name: 'full_text') this.fullText,
      @JsonKey(name: 'full_text_preview') this.fullTextPreview,
      @JsonKey(name: 'char_count') this.charCount});

  factory _$CleaningResultImpl.fromJson(Map<String, dynamic> json) =>
      _$$CleaningResultImplFromJson(json);

  @override
  final String status;
  @override
  final String mode;
// full_text, map_reduce
  @override
  final String summary;
  @override
  @JsonKey(name: 'full_text')
  final String? fullText;
  @override
  @JsonKey(name: 'full_text_preview')
  final String? fullTextPreview;
  @override
  @JsonKey(name: 'char_count')
  final int? charCount;

  @override
  String toString() {
    return 'CleaningResult(status: $status, mode: $mode, summary: $summary, fullText: $fullText, fullTextPreview: $fullTextPreview, charCount: $charCount)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CleaningResultImpl &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.mode, mode) || other.mode == mode) &&
            (identical(other.summary, summary) || other.summary == summary) &&
            (identical(other.fullText, fullText) ||
                other.fullText == fullText) &&
            (identical(other.fullTextPreview, fullTextPreview) ||
                other.fullTextPreview == fullTextPreview) &&
            (identical(other.charCount, charCount) ||
                other.charCount == charCount));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType, status, mode, summary, fullText, fullTextPreview, charCount);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$CleaningResultImplCopyWith<_$CleaningResultImpl> get copyWith =>
      __$$CleaningResultImplCopyWithImpl<_$CleaningResultImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CleaningResultImplToJson(
      this,
    );
  }
}

abstract class _CleaningResult implements CleaningResult {
  const factory _CleaningResult(
          {required final String status,
          required final String mode,
          required final String summary,
          @JsonKey(name: 'full_text') final String? fullText,
          @JsonKey(name: 'full_text_preview') final String? fullTextPreview,
          @JsonKey(name: 'char_count') final int? charCount}) =
      _$CleaningResultImpl;

  factory _CleaningResult.fromJson(Map<String, dynamic> json) =
      _$CleaningResultImpl.fromJson;

  @override
  String get status;
  @override
  String get mode;
  @override // full_text, map_reduce
  String get summary;
  @override
  @JsonKey(name: 'full_text')
  String? get fullText;
  @override
  @JsonKey(name: 'full_text_preview')
  String? get fullTextPreview;
  @override
  @JsonKey(name: 'char_count')
  int? get charCount;
  @override
  @JsonKey(ignore: true)
  _$$CleaningResultImplCopyWith<_$CleaningResultImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
