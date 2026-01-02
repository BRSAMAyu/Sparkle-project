// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'error_record.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ErrorRecord _$ErrorRecordFromJson(Map<String, dynamic> json) {
  return _ErrorRecord.fromJson(json);
}

/// @nodoc
mixin _$ErrorRecord {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'question_text')
  String get questionText => throw _privateConstructorUsedError;
  @JsonKey(name: 'question_image_url')
  String? get questionImageUrl => throw _privateConstructorUsedError;
  @JsonKey(name: 'user_answer')
  String get userAnswer => throw _privateConstructorUsedError;
  @JsonKey(name: 'correct_answer')
  String get correctAnswer => throw _privateConstructorUsedError;
  String get subject => throw _privateConstructorUsedError;
  String? get chapter => throw _privateConstructorUsedError;
  int? get difficulty => throw _privateConstructorUsedError;
  @JsonKey(name: 'mastery_level')
  double get masteryLevel => throw _privateConstructorUsedError;
  @JsonKey(name: 'review_count')
  int get reviewCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'next_review_at')
  DateTime? get nextReviewAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'last_reviewed_at')
  DateTime? get lastReviewedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'latest_analysis')
  ErrorAnalysis? get latestAnalysis => throw _privateConstructorUsedError;
  @JsonKey(name: 'knowledge_links')
  List<KnowledgeLink> get knowledgeLinks => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  DateTime get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'updated_at')
  DateTime get updatedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $ErrorRecordCopyWith<ErrorRecord> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ErrorRecordCopyWith<$Res> {
  factory $ErrorRecordCopyWith(
          ErrorRecord value, $Res Function(ErrorRecord) then) =
      _$ErrorRecordCopyWithImpl<$Res, ErrorRecord>;
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'question_text') String questionText,
      @JsonKey(name: 'question_image_url') String? questionImageUrl,
      @JsonKey(name: 'user_answer') String userAnswer,
      @JsonKey(name: 'correct_answer') String correctAnswer,
      String subject,
      String? chapter,
      int? difficulty,
      @JsonKey(name: 'mastery_level') double masteryLevel,
      @JsonKey(name: 'review_count') int reviewCount,
      @JsonKey(name: 'next_review_at') DateTime? nextReviewAt,
      @JsonKey(name: 'last_reviewed_at') DateTime? lastReviewedAt,
      @JsonKey(name: 'latest_analysis') ErrorAnalysis? latestAnalysis,
      @JsonKey(name: 'knowledge_links') List<KnowledgeLink> knowledgeLinks,
      @JsonKey(name: 'created_at') DateTime createdAt,
      @JsonKey(name: 'updated_at') DateTime updatedAt});

  $ErrorAnalysisCopyWith<$Res>? get latestAnalysis;
}

/// @nodoc
class _$ErrorRecordCopyWithImpl<$Res, $Val extends ErrorRecord>
    implements $ErrorRecordCopyWith<$Res> {
  _$ErrorRecordCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? questionText = null,
    Object? questionImageUrl = freezed,
    Object? userAnswer = null,
    Object? correctAnswer = null,
    Object? subject = null,
    Object? chapter = freezed,
    Object? difficulty = freezed,
    Object? masteryLevel = null,
    Object? reviewCount = null,
    Object? nextReviewAt = freezed,
    Object? lastReviewedAt = freezed,
    Object? latestAnalysis = freezed,
    Object? knowledgeLinks = null,
    Object? createdAt = null,
    Object? updatedAt = null,
  }) {
    return _then(_value.copyWith(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      questionText: null == questionText
          ? _value.questionText
          : questionText // ignore: cast_nullable_to_non_nullable
              as String,
      questionImageUrl: freezed == questionImageUrl
          ? _value.questionImageUrl
          : questionImageUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      userAnswer: null == userAnswer
          ? _value.userAnswer
          : userAnswer // ignore: cast_nullable_to_non_nullable
              as String,
      correctAnswer: null == correctAnswer
          ? _value.correctAnswer
          : correctAnswer // ignore: cast_nullable_to_non_nullable
              as String,
      subject: null == subject
          ? _value.subject
          : subject // ignore: cast_nullable_to_non_nullable
              as String,
      chapter: freezed == chapter
          ? _value.chapter
          : chapter // ignore: cast_nullable_to_non_nullable
              as String?,
      difficulty: freezed == difficulty
          ? _value.difficulty
          : difficulty // ignore: cast_nullable_to_non_nullable
              as int?,
      masteryLevel: null == masteryLevel
          ? _value.masteryLevel
          : masteryLevel // ignore: cast_nullable_to_non_nullable
              as double,
      reviewCount: null == reviewCount
          ? _value.reviewCount
          : reviewCount // ignore: cast_nullable_to_non_nullable
              as int,
      nextReviewAt: freezed == nextReviewAt
          ? _value.nextReviewAt
          : nextReviewAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      lastReviewedAt: freezed == lastReviewedAt
          ? _value.lastReviewedAt
          : lastReviewedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      latestAnalysis: freezed == latestAnalysis
          ? _value.latestAnalysis
          : latestAnalysis // ignore: cast_nullable_to_non_nullable
              as ErrorAnalysis?,
      knowledgeLinks: null == knowledgeLinks
          ? _value.knowledgeLinks
          : knowledgeLinks // ignore: cast_nullable_to_non_nullable
              as List<KnowledgeLink>,
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ) as $Val);
  }

  @override
  @pragma('vm:prefer-inline')
  $ErrorAnalysisCopyWith<$Res>? get latestAnalysis {
    if (_value.latestAnalysis == null) {
      return null;
    }

    return $ErrorAnalysisCopyWith<$Res>(_value.latestAnalysis!, (value) {
      return _then(_value.copyWith(latestAnalysis: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$ErrorRecordImplCopyWith<$Res>
    implements $ErrorRecordCopyWith<$Res> {
  factory _$$ErrorRecordImplCopyWith(
          _$ErrorRecordImpl value, $Res Function(_$ErrorRecordImpl) then) =
      __$$ErrorRecordImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {String id,
      @JsonKey(name: 'question_text') String questionText,
      @JsonKey(name: 'question_image_url') String? questionImageUrl,
      @JsonKey(name: 'user_answer') String userAnswer,
      @JsonKey(name: 'correct_answer') String correctAnswer,
      String subject,
      String? chapter,
      int? difficulty,
      @JsonKey(name: 'mastery_level') double masteryLevel,
      @JsonKey(name: 'review_count') int reviewCount,
      @JsonKey(name: 'next_review_at') DateTime? nextReviewAt,
      @JsonKey(name: 'last_reviewed_at') DateTime? lastReviewedAt,
      @JsonKey(name: 'latest_analysis') ErrorAnalysis? latestAnalysis,
      @JsonKey(name: 'knowledge_links') List<KnowledgeLink> knowledgeLinks,
      @JsonKey(name: 'created_at') DateTime createdAt,
      @JsonKey(name: 'updated_at') DateTime updatedAt});

  @override
  $ErrorAnalysisCopyWith<$Res>? get latestAnalysis;
}

/// @nodoc
class __$$ErrorRecordImplCopyWithImpl<$Res>
    extends _$ErrorRecordCopyWithImpl<$Res, _$ErrorRecordImpl>
    implements _$$ErrorRecordImplCopyWith<$Res> {
  __$$ErrorRecordImplCopyWithImpl(
      _$ErrorRecordImpl _value, $Res Function(_$ErrorRecordImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? questionText = null,
    Object? questionImageUrl = freezed,
    Object? userAnswer = null,
    Object? correctAnswer = null,
    Object? subject = null,
    Object? chapter = freezed,
    Object? difficulty = freezed,
    Object? masteryLevel = null,
    Object? reviewCount = null,
    Object? nextReviewAt = freezed,
    Object? lastReviewedAt = freezed,
    Object? latestAnalysis = freezed,
    Object? knowledgeLinks = null,
    Object? createdAt = null,
    Object? updatedAt = null,
  }) {
    return _then(_$ErrorRecordImpl(
      id: null == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as String,
      questionText: null == questionText
          ? _value.questionText
          : questionText // ignore: cast_nullable_to_non_nullable
              as String,
      questionImageUrl: freezed == questionImageUrl
          ? _value.questionImageUrl
          : questionImageUrl // ignore: cast_nullable_to_non_nullable
              as String?,
      userAnswer: null == userAnswer
          ? _value.userAnswer
          : userAnswer // ignore: cast_nullable_to_non_nullable
              as String,
      correctAnswer: null == correctAnswer
          ? _value.correctAnswer
          : correctAnswer // ignore: cast_nullable_to_non_nullable
              as String,
      subject: null == subject
          ? _value.subject
          : subject // ignore: cast_nullable_to_non_nullable
              as String,
      chapter: freezed == chapter
          ? _value.chapter
          : chapter // ignore: cast_nullable_to_non_nullable
              as String?,
      difficulty: freezed == difficulty
          ? _value.difficulty
          : difficulty // ignore: cast_nullable_to_non_nullable
              as int?,
      masteryLevel: null == masteryLevel
          ? _value.masteryLevel
          : masteryLevel // ignore: cast_nullable_to_non_nullable
              as double,
      reviewCount: null == reviewCount
          ? _value.reviewCount
          : reviewCount // ignore: cast_nullable_to_non_nullable
              as int,
      nextReviewAt: freezed == nextReviewAt
          ? _value.nextReviewAt
          : nextReviewAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      lastReviewedAt: freezed == lastReviewedAt
          ? _value.lastReviewedAt
          : lastReviewedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      latestAnalysis: freezed == latestAnalysis
          ? _value.latestAnalysis
          : latestAnalysis // ignore: cast_nullable_to_non_nullable
              as ErrorAnalysis?,
      knowledgeLinks: null == knowledgeLinks
          ? _value._knowledgeLinks
          : knowledgeLinks // ignore: cast_nullable_to_non_nullable
              as List<KnowledgeLink>,
      createdAt: null == createdAt
          ? _value.createdAt
          : createdAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      updatedAt: null == updatedAt
          ? _value.updatedAt
          : updatedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ErrorRecordImpl implements _ErrorRecord {
  const _$ErrorRecordImpl(
      {required this.id,
      @JsonKey(name: 'question_text') required this.questionText,
      @JsonKey(name: 'question_image_url') this.questionImageUrl,
      @JsonKey(name: 'user_answer') required this.userAnswer,
      @JsonKey(name: 'correct_answer') required this.correctAnswer,
      required this.subject,
      this.chapter,
      this.difficulty,
      @JsonKey(name: 'mastery_level') required this.masteryLevel,
      @JsonKey(name: 'review_count') required this.reviewCount,
      @JsonKey(name: 'next_review_at') this.nextReviewAt,
      @JsonKey(name: 'last_reviewed_at') this.lastReviewedAt,
      @JsonKey(name: 'latest_analysis') this.latestAnalysis,
      @JsonKey(name: 'knowledge_links')
      final List<KnowledgeLink> knowledgeLinks = const [],
      @JsonKey(name: 'created_at') required this.createdAt,
      @JsonKey(name: 'updated_at') required this.updatedAt})
      : _knowledgeLinks = knowledgeLinks;

  factory _$ErrorRecordImpl.fromJson(Map<String, dynamic> json) =>
      _$$ErrorRecordImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'question_text')
  final String questionText;
  @override
  @JsonKey(name: 'question_image_url')
  final String? questionImageUrl;
  @override
  @JsonKey(name: 'user_answer')
  final String userAnswer;
  @override
  @JsonKey(name: 'correct_answer')
  final String correctAnswer;
  @override
  final String subject;
  @override
  final String? chapter;
  @override
  final int? difficulty;
  @override
  @JsonKey(name: 'mastery_level')
  final double masteryLevel;
  @override
  @JsonKey(name: 'review_count')
  final int reviewCount;
  @override
  @JsonKey(name: 'next_review_at')
  final DateTime? nextReviewAt;
  @override
  @JsonKey(name: 'last_reviewed_at')
  final DateTime? lastReviewedAt;
  @override
  @JsonKey(name: 'latest_analysis')
  final ErrorAnalysis? latestAnalysis;
  final List<KnowledgeLink> _knowledgeLinks;
  @override
  @JsonKey(name: 'knowledge_links')
  List<KnowledgeLink> get knowledgeLinks {
    if (_knowledgeLinks is EqualUnmodifiableListView) return _knowledgeLinks;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_knowledgeLinks);
  }

  @override
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @override
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  @override
  String toString() {
    return 'ErrorRecord(id: $id, questionText: $questionText, questionImageUrl: $questionImageUrl, userAnswer: $userAnswer, correctAnswer: $correctAnswer, subject: $subject, chapter: $chapter, difficulty: $difficulty, masteryLevel: $masteryLevel, reviewCount: $reviewCount, nextReviewAt: $nextReviewAt, lastReviewedAt: $lastReviewedAt, latestAnalysis: $latestAnalysis, knowledgeLinks: $knowledgeLinks, createdAt: $createdAt, updatedAt: $updatedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ErrorRecordImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.questionText, questionText) ||
                other.questionText == questionText) &&
            (identical(other.questionImageUrl, questionImageUrl) ||
                other.questionImageUrl == questionImageUrl) &&
            (identical(other.userAnswer, userAnswer) ||
                other.userAnswer == userAnswer) &&
            (identical(other.correctAnswer, correctAnswer) ||
                other.correctAnswer == correctAnswer) &&
            (identical(other.subject, subject) || other.subject == subject) &&
            (identical(other.chapter, chapter) || other.chapter == chapter) &&
            (identical(other.difficulty, difficulty) ||
                other.difficulty == difficulty) &&
            (identical(other.masteryLevel, masteryLevel) ||
                other.masteryLevel == masteryLevel) &&
            (identical(other.reviewCount, reviewCount) ||
                other.reviewCount == reviewCount) &&
            (identical(other.nextReviewAt, nextReviewAt) ||
                other.nextReviewAt == nextReviewAt) &&
            (identical(other.lastReviewedAt, lastReviewedAt) ||
                other.lastReviewedAt == lastReviewedAt) &&
            (identical(other.latestAnalysis, latestAnalysis) ||
                other.latestAnalysis == latestAnalysis) &&
            const DeepCollectionEquality()
                .equals(other._knowledgeLinks, _knowledgeLinks) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.updatedAt, updatedAt) ||
                other.updatedAt == updatedAt));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      questionText,
      questionImageUrl,
      userAnswer,
      correctAnswer,
      subject,
      chapter,
      difficulty,
      masteryLevel,
      reviewCount,
      nextReviewAt,
      lastReviewedAt,
      latestAnalysis,
      const DeepCollectionEquality().hash(_knowledgeLinks),
      createdAt,
      updatedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$ErrorRecordImplCopyWith<_$ErrorRecordImpl> get copyWith =>
      __$$ErrorRecordImplCopyWithImpl<_$ErrorRecordImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ErrorRecordImplToJson(
      this,
    );
  }
}

abstract class _ErrorRecord implements ErrorRecord {
  const factory _ErrorRecord(
          {required final String id,
          @JsonKey(name: 'question_text') required final String questionText,
          @JsonKey(name: 'question_image_url') final String? questionImageUrl,
          @JsonKey(name: 'user_answer') required final String userAnswer,
          @JsonKey(name: 'correct_answer') required final String correctAnswer,
          required final String subject,
          final String? chapter,
          final int? difficulty,
          @JsonKey(name: 'mastery_level') required final double masteryLevel,
          @JsonKey(name: 'review_count') required final int reviewCount,
          @JsonKey(name: 'next_review_at') final DateTime? nextReviewAt,
          @JsonKey(name: 'last_reviewed_at') final DateTime? lastReviewedAt,
          @JsonKey(name: 'latest_analysis') final ErrorAnalysis? latestAnalysis,
          @JsonKey(name: 'knowledge_links')
          final List<KnowledgeLink> knowledgeLinks,
          @JsonKey(name: 'created_at') required final DateTime createdAt,
          @JsonKey(name: 'updated_at') required final DateTime updatedAt}) =
      _$ErrorRecordImpl;

  factory _ErrorRecord.fromJson(Map<String, dynamic> json) =
      _$ErrorRecordImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'question_text')
  String get questionText;
  @override
  @JsonKey(name: 'question_image_url')
  String? get questionImageUrl;
  @override
  @JsonKey(name: 'user_answer')
  String get userAnswer;
  @override
  @JsonKey(name: 'correct_answer')
  String get correctAnswer;
  @override
  String get subject;
  @override
  String? get chapter;
  @override
  int? get difficulty;
  @override
  @JsonKey(name: 'mastery_level')
  double get masteryLevel;
  @override
  @JsonKey(name: 'review_count')
  int get reviewCount;
  @override
  @JsonKey(name: 'next_review_at')
  DateTime? get nextReviewAt;
  @override
  @JsonKey(name: 'last_reviewed_at')
  DateTime? get lastReviewedAt;
  @override
  @JsonKey(name: 'latest_analysis')
  ErrorAnalysis? get latestAnalysis;
  @override
  @JsonKey(name: 'knowledge_links')
  List<KnowledgeLink> get knowledgeLinks;
  @override
  @JsonKey(name: 'created_at')
  DateTime get createdAt;
  @override
  @JsonKey(name: 'updated_at')
  DateTime get updatedAt;
  @override
  @JsonKey(ignore: true)
  _$$ErrorRecordImplCopyWith<_$ErrorRecordImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

ErrorAnalysis _$ErrorAnalysisFromJson(Map<String, dynamic> json) {
  return _ErrorAnalysis.fromJson(json);
}

/// @nodoc
mixin _$ErrorAnalysis {
  @JsonKey(name: 'error_type')
  String get errorType => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_type_label')
  String get errorTypeLabel => throw _privateConstructorUsedError;
  @JsonKey(name: 'root_cause')
  String get rootCause => throw _privateConstructorUsedError;
  @JsonKey(name: 'correct_approach')
  String get correctApproach => throw _privateConstructorUsedError;
  @JsonKey(name: 'similar_traps')
  List<String> get similarTraps => throw _privateConstructorUsedError;
  @JsonKey(name: 'recommended_knowledge')
  List<String> get recommendedKnowledge => throw _privateConstructorUsedError;
  @JsonKey(name: 'study_suggestion')
  String get studySuggestion => throw _privateConstructorUsedError;
  @JsonKey(name: 'analyzed_at')
  DateTime get analyzedAt => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $ErrorAnalysisCopyWith<ErrorAnalysis> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ErrorAnalysisCopyWith<$Res> {
  factory $ErrorAnalysisCopyWith(
          ErrorAnalysis value, $Res Function(ErrorAnalysis) then) =
      _$ErrorAnalysisCopyWithImpl<$Res, ErrorAnalysis>;
  @useResult
  $Res call(
      {@JsonKey(name: 'error_type') String errorType,
      @JsonKey(name: 'error_type_label') String errorTypeLabel,
      @JsonKey(name: 'root_cause') String rootCause,
      @JsonKey(name: 'correct_approach') String correctApproach,
      @JsonKey(name: 'similar_traps') List<String> similarTraps,
      @JsonKey(name: 'recommended_knowledge') List<String> recommendedKnowledge,
      @JsonKey(name: 'study_suggestion') String studySuggestion,
      @JsonKey(name: 'analyzed_at') DateTime analyzedAt});
}

/// @nodoc
class _$ErrorAnalysisCopyWithImpl<$Res, $Val extends ErrorAnalysis>
    implements $ErrorAnalysisCopyWith<$Res> {
  _$ErrorAnalysisCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? errorType = null,
    Object? errorTypeLabel = null,
    Object? rootCause = null,
    Object? correctApproach = null,
    Object? similarTraps = null,
    Object? recommendedKnowledge = null,
    Object? studySuggestion = null,
    Object? analyzedAt = null,
  }) {
    return _then(_value.copyWith(
      errorType: null == errorType
          ? _value.errorType
          : errorType // ignore: cast_nullable_to_non_nullable
              as String,
      errorTypeLabel: null == errorTypeLabel
          ? _value.errorTypeLabel
          : errorTypeLabel // ignore: cast_nullable_to_non_nullable
              as String,
      rootCause: null == rootCause
          ? _value.rootCause
          : rootCause // ignore: cast_nullable_to_non_nullable
              as String,
      correctApproach: null == correctApproach
          ? _value.correctApproach
          : correctApproach // ignore: cast_nullable_to_non_nullable
              as String,
      similarTraps: null == similarTraps
          ? _value.similarTraps
          : similarTraps // ignore: cast_nullable_to_non_nullable
              as List<String>,
      recommendedKnowledge: null == recommendedKnowledge
          ? _value.recommendedKnowledge
          : recommendedKnowledge // ignore: cast_nullable_to_non_nullable
              as List<String>,
      studySuggestion: null == studySuggestion
          ? _value.studySuggestion
          : studySuggestion // ignore: cast_nullable_to_non_nullable
              as String,
      analyzedAt: null == analyzedAt
          ? _value.analyzedAt
          : analyzedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ErrorAnalysisImplCopyWith<$Res>
    implements $ErrorAnalysisCopyWith<$Res> {
  factory _$$ErrorAnalysisImplCopyWith(
          _$ErrorAnalysisImpl value, $Res Function(_$ErrorAnalysisImpl) then) =
      __$$ErrorAnalysisImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'error_type') String errorType,
      @JsonKey(name: 'error_type_label') String errorTypeLabel,
      @JsonKey(name: 'root_cause') String rootCause,
      @JsonKey(name: 'correct_approach') String correctApproach,
      @JsonKey(name: 'similar_traps') List<String> similarTraps,
      @JsonKey(name: 'recommended_knowledge') List<String> recommendedKnowledge,
      @JsonKey(name: 'study_suggestion') String studySuggestion,
      @JsonKey(name: 'analyzed_at') DateTime analyzedAt});
}

/// @nodoc
class __$$ErrorAnalysisImplCopyWithImpl<$Res>
    extends _$ErrorAnalysisCopyWithImpl<$Res, _$ErrorAnalysisImpl>
    implements _$$ErrorAnalysisImplCopyWith<$Res> {
  __$$ErrorAnalysisImplCopyWithImpl(
      _$ErrorAnalysisImpl _value, $Res Function(_$ErrorAnalysisImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? errorType = null,
    Object? errorTypeLabel = null,
    Object? rootCause = null,
    Object? correctApproach = null,
    Object? similarTraps = null,
    Object? recommendedKnowledge = null,
    Object? studySuggestion = null,
    Object? analyzedAt = null,
  }) {
    return _then(_$ErrorAnalysisImpl(
      errorType: null == errorType
          ? _value.errorType
          : errorType // ignore: cast_nullable_to_non_nullable
              as String,
      errorTypeLabel: null == errorTypeLabel
          ? _value.errorTypeLabel
          : errorTypeLabel // ignore: cast_nullable_to_non_nullable
              as String,
      rootCause: null == rootCause
          ? _value.rootCause
          : rootCause // ignore: cast_nullable_to_non_nullable
              as String,
      correctApproach: null == correctApproach
          ? _value.correctApproach
          : correctApproach // ignore: cast_nullable_to_non_nullable
              as String,
      similarTraps: null == similarTraps
          ? _value._similarTraps
          : similarTraps // ignore: cast_nullable_to_non_nullable
              as List<String>,
      recommendedKnowledge: null == recommendedKnowledge
          ? _value._recommendedKnowledge
          : recommendedKnowledge // ignore: cast_nullable_to_non_nullable
              as List<String>,
      studySuggestion: null == studySuggestion
          ? _value.studySuggestion
          : studySuggestion // ignore: cast_nullable_to_non_nullable
              as String,
      analyzedAt: null == analyzedAt
          ? _value.analyzedAt
          : analyzedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ErrorAnalysisImpl implements _ErrorAnalysis {
  const _$ErrorAnalysisImpl(
      {@JsonKey(name: 'error_type') required this.errorType,
      @JsonKey(name: 'error_type_label') required this.errorTypeLabel,
      @JsonKey(name: 'root_cause') required this.rootCause,
      @JsonKey(name: 'correct_approach') required this.correctApproach,
      @JsonKey(name: 'similar_traps')
      final List<String> similarTraps = const [],
      @JsonKey(name: 'recommended_knowledge')
      final List<String> recommendedKnowledge = const [],
      @JsonKey(name: 'study_suggestion') required this.studySuggestion,
      @JsonKey(name: 'analyzed_at') required this.analyzedAt})
      : _similarTraps = similarTraps,
        _recommendedKnowledge = recommendedKnowledge;

  factory _$ErrorAnalysisImpl.fromJson(Map<String, dynamic> json) =>
      _$$ErrorAnalysisImplFromJson(json);

  @override
  @JsonKey(name: 'error_type')
  final String errorType;
  @override
  @JsonKey(name: 'error_type_label')
  final String errorTypeLabel;
  @override
  @JsonKey(name: 'root_cause')
  final String rootCause;
  @override
  @JsonKey(name: 'correct_approach')
  final String correctApproach;
  final List<String> _similarTraps;
  @override
  @JsonKey(name: 'similar_traps')
  List<String> get similarTraps {
    if (_similarTraps is EqualUnmodifiableListView) return _similarTraps;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_similarTraps);
  }

  final List<String> _recommendedKnowledge;
  @override
  @JsonKey(name: 'recommended_knowledge')
  List<String> get recommendedKnowledge {
    if (_recommendedKnowledge is EqualUnmodifiableListView)
      return _recommendedKnowledge;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_recommendedKnowledge);
  }

  @override
  @JsonKey(name: 'study_suggestion')
  final String studySuggestion;
  @override
  @JsonKey(name: 'analyzed_at')
  final DateTime analyzedAt;

  @override
  String toString() {
    return 'ErrorAnalysis(errorType: $errorType, errorTypeLabel: $errorTypeLabel, rootCause: $rootCause, correctApproach: $correctApproach, similarTraps: $similarTraps, recommendedKnowledge: $recommendedKnowledge, studySuggestion: $studySuggestion, analyzedAt: $analyzedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ErrorAnalysisImpl &&
            (identical(other.errorType, errorType) ||
                other.errorType == errorType) &&
            (identical(other.errorTypeLabel, errorTypeLabel) ||
                other.errorTypeLabel == errorTypeLabel) &&
            (identical(other.rootCause, rootCause) ||
                other.rootCause == rootCause) &&
            (identical(other.correctApproach, correctApproach) ||
                other.correctApproach == correctApproach) &&
            const DeepCollectionEquality()
                .equals(other._similarTraps, _similarTraps) &&
            const DeepCollectionEquality()
                .equals(other._recommendedKnowledge, _recommendedKnowledge) &&
            (identical(other.studySuggestion, studySuggestion) ||
                other.studySuggestion == studySuggestion) &&
            (identical(other.analyzedAt, analyzedAt) ||
                other.analyzedAt == analyzedAt));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      errorType,
      errorTypeLabel,
      rootCause,
      correctApproach,
      const DeepCollectionEquality().hash(_similarTraps),
      const DeepCollectionEquality().hash(_recommendedKnowledge),
      studySuggestion,
      analyzedAt);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$ErrorAnalysisImplCopyWith<_$ErrorAnalysisImpl> get copyWith =>
      __$$ErrorAnalysisImplCopyWithImpl<_$ErrorAnalysisImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ErrorAnalysisImplToJson(
      this,
    );
  }
}

abstract class _ErrorAnalysis implements ErrorAnalysis {
  const factory _ErrorAnalysis(
      {@JsonKey(name: 'error_type') required final String errorType,
      @JsonKey(name: 'error_type_label') required final String errorTypeLabel,
      @JsonKey(name: 'root_cause') required final String rootCause,
      @JsonKey(name: 'correct_approach') required final String correctApproach,
      @JsonKey(name: 'similar_traps') final List<String> similarTraps,
      @JsonKey(name: 'recommended_knowledge')
      final List<String> recommendedKnowledge,
      @JsonKey(name: 'study_suggestion') required final String studySuggestion,
      @JsonKey(name: 'analyzed_at')
      required final DateTime analyzedAt}) = _$ErrorAnalysisImpl;

  factory _ErrorAnalysis.fromJson(Map<String, dynamic> json) =
      _$ErrorAnalysisImpl.fromJson;

  @override
  @JsonKey(name: 'error_type')
  String get errorType;
  @override
  @JsonKey(name: 'error_type_label')
  String get errorTypeLabel;
  @override
  @JsonKey(name: 'root_cause')
  String get rootCause;
  @override
  @JsonKey(name: 'correct_approach')
  String get correctApproach;
  @override
  @JsonKey(name: 'similar_traps')
  List<String> get similarTraps;
  @override
  @JsonKey(name: 'recommended_knowledge')
  List<String> get recommendedKnowledge;
  @override
  @JsonKey(name: 'study_suggestion')
  String get studySuggestion;
  @override
  @JsonKey(name: 'analyzed_at')
  DateTime get analyzedAt;
  @override
  @JsonKey(ignore: true)
  _$$ErrorAnalysisImplCopyWith<_$ErrorAnalysisImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

KnowledgeLink _$KnowledgeLinkFromJson(Map<String, dynamic> json) {
  return _KnowledgeLink.fromJson(json);
}

/// @nodoc
mixin _$KnowledgeLink {
  @JsonKey(name: 'knowledge_node_id')
  String get nodeId => throw _privateConstructorUsedError;
  @JsonKey(name: 'node_name')
  String get nodeName => throw _privateConstructorUsedError;
  double get relevance => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_primary')
  bool get isPrimary => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $KnowledgeLinkCopyWith<KnowledgeLink> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $KnowledgeLinkCopyWith<$Res> {
  factory $KnowledgeLinkCopyWith(
          KnowledgeLink value, $Res Function(KnowledgeLink) then) =
      _$KnowledgeLinkCopyWithImpl<$Res, KnowledgeLink>;
  @useResult
  $Res call(
      {@JsonKey(name: 'knowledge_node_id') String nodeId,
      @JsonKey(name: 'node_name') String nodeName,
      double relevance,
      @JsonKey(name: 'is_primary') bool isPrimary});
}

/// @nodoc
class _$KnowledgeLinkCopyWithImpl<$Res, $Val extends KnowledgeLink>
    implements $KnowledgeLinkCopyWith<$Res> {
  _$KnowledgeLinkCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? nodeId = null,
    Object? nodeName = null,
    Object? relevance = null,
    Object? isPrimary = null,
  }) {
    return _then(_value.copyWith(
      nodeId: null == nodeId
          ? _value.nodeId
          : nodeId // ignore: cast_nullable_to_non_nullable
              as String,
      nodeName: null == nodeName
          ? _value.nodeName
          : nodeName // ignore: cast_nullable_to_non_nullable
              as String,
      relevance: null == relevance
          ? _value.relevance
          : relevance // ignore: cast_nullable_to_non_nullable
              as double,
      isPrimary: null == isPrimary
          ? _value.isPrimary
          : isPrimary // ignore: cast_nullable_to_non_nullable
              as bool,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$KnowledgeLinkImplCopyWith<$Res>
    implements $KnowledgeLinkCopyWith<$Res> {
  factory _$$KnowledgeLinkImplCopyWith(
          _$KnowledgeLinkImpl value, $Res Function(_$KnowledgeLinkImpl) then) =
      __$$KnowledgeLinkImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'knowledge_node_id') String nodeId,
      @JsonKey(name: 'node_name') String nodeName,
      double relevance,
      @JsonKey(name: 'is_primary') bool isPrimary});
}

/// @nodoc
class __$$KnowledgeLinkImplCopyWithImpl<$Res>
    extends _$KnowledgeLinkCopyWithImpl<$Res, _$KnowledgeLinkImpl>
    implements _$$KnowledgeLinkImplCopyWith<$Res> {
  __$$KnowledgeLinkImplCopyWithImpl(
      _$KnowledgeLinkImpl _value, $Res Function(_$KnowledgeLinkImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? nodeId = null,
    Object? nodeName = null,
    Object? relevance = null,
    Object? isPrimary = null,
  }) {
    return _then(_$KnowledgeLinkImpl(
      nodeId: null == nodeId
          ? _value.nodeId
          : nodeId // ignore: cast_nullable_to_non_nullable
              as String,
      nodeName: null == nodeName
          ? _value.nodeName
          : nodeName // ignore: cast_nullable_to_non_nullable
              as String,
      relevance: null == relevance
          ? _value.relevance
          : relevance // ignore: cast_nullable_to_non_nullable
              as double,
      isPrimary: null == isPrimary
          ? _value.isPrimary
          : isPrimary // ignore: cast_nullable_to_non_nullable
              as bool,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$KnowledgeLinkImpl implements _KnowledgeLink {
  const _$KnowledgeLinkImpl(
      {@JsonKey(name: 'knowledge_node_id') required this.nodeId,
      @JsonKey(name: 'node_name') required this.nodeName,
      required this.relevance,
      @JsonKey(name: 'is_primary') required this.isPrimary});

  factory _$KnowledgeLinkImpl.fromJson(Map<String, dynamic> json) =>
      _$$KnowledgeLinkImplFromJson(json);

  @override
  @JsonKey(name: 'knowledge_node_id')
  final String nodeId;
  @override
  @JsonKey(name: 'node_name')
  final String nodeName;
  @override
  final double relevance;
  @override
  @JsonKey(name: 'is_primary')
  final bool isPrimary;

  @override
  String toString() {
    return 'KnowledgeLink(nodeId: $nodeId, nodeName: $nodeName, relevance: $relevance, isPrimary: $isPrimary)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$KnowledgeLinkImpl &&
            (identical(other.nodeId, nodeId) || other.nodeId == nodeId) &&
            (identical(other.nodeName, nodeName) ||
                other.nodeName == nodeName) &&
            (identical(other.relevance, relevance) ||
                other.relevance == relevance) &&
            (identical(other.isPrimary, isPrimary) ||
                other.isPrimary == isPrimary));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode =>
      Object.hash(runtimeType, nodeId, nodeName, relevance, isPrimary);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$KnowledgeLinkImplCopyWith<_$KnowledgeLinkImpl> get copyWith =>
      __$$KnowledgeLinkImplCopyWithImpl<_$KnowledgeLinkImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$KnowledgeLinkImplToJson(
      this,
    );
  }
}

abstract class _KnowledgeLink implements KnowledgeLink {
  const factory _KnowledgeLink(
          {@JsonKey(name: 'knowledge_node_id') required final String nodeId,
          @JsonKey(name: 'node_name') required final String nodeName,
          required final double relevance,
          @JsonKey(name: 'is_primary') required final bool isPrimary}) =
      _$KnowledgeLinkImpl;

  factory _KnowledgeLink.fromJson(Map<String, dynamic> json) =
      _$KnowledgeLinkImpl.fromJson;

  @override
  @JsonKey(name: 'knowledge_node_id')
  String get nodeId;
  @override
  @JsonKey(name: 'node_name')
  String get nodeName;
  @override
  double get relevance;
  @override
  @JsonKey(name: 'is_primary')
  bool get isPrimary;
  @override
  @JsonKey(ignore: true)
  _$$KnowledgeLinkImplCopyWith<_$KnowledgeLinkImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

ErrorListResponse _$ErrorListResponseFromJson(Map<String, dynamic> json) {
  return _ErrorListResponse.fromJson(json);
}

/// @nodoc
mixin _$ErrorListResponse {
  List<ErrorRecord> get items => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;
  int get page => throw _privateConstructorUsedError;
  @JsonKey(name: 'page_size')
  int get pageSize => throw _privateConstructorUsedError;
  @JsonKey(name: 'has_next')
  bool get hasNext => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $ErrorListResponseCopyWith<ErrorListResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ErrorListResponseCopyWith<$Res> {
  factory $ErrorListResponseCopyWith(
          ErrorListResponse value, $Res Function(ErrorListResponse) then) =
      _$ErrorListResponseCopyWithImpl<$Res, ErrorListResponse>;
  @useResult
  $Res call(
      {List<ErrorRecord> items,
      int total,
      int page,
      @JsonKey(name: 'page_size') int pageSize,
      @JsonKey(name: 'has_next') bool hasNext});
}

/// @nodoc
class _$ErrorListResponseCopyWithImpl<$Res, $Val extends ErrorListResponse>
    implements $ErrorListResponseCopyWith<$Res> {
  _$ErrorListResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? page = null,
    Object? pageSize = null,
    Object? hasNext = null,
  }) {
    return _then(_value.copyWith(
      items: null == items
          ? _value.items
          : items // ignore: cast_nullable_to_non_nullable
              as List<ErrorRecord>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      page: null == page
          ? _value.page
          : page // ignore: cast_nullable_to_non_nullable
              as int,
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
      hasNext: null == hasNext
          ? _value.hasNext
          : hasNext // ignore: cast_nullable_to_non_nullable
              as bool,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ErrorListResponseImplCopyWith<$Res>
    implements $ErrorListResponseCopyWith<$Res> {
  factory _$$ErrorListResponseImplCopyWith(_$ErrorListResponseImpl value,
          $Res Function(_$ErrorListResponseImpl) then) =
      __$$ErrorListResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {List<ErrorRecord> items,
      int total,
      int page,
      @JsonKey(name: 'page_size') int pageSize,
      @JsonKey(name: 'has_next') bool hasNext});
}

/// @nodoc
class __$$ErrorListResponseImplCopyWithImpl<$Res>
    extends _$ErrorListResponseCopyWithImpl<$Res, _$ErrorListResponseImpl>
    implements _$$ErrorListResponseImplCopyWith<$Res> {
  __$$ErrorListResponseImplCopyWithImpl(_$ErrorListResponseImpl _value,
      $Res Function(_$ErrorListResponseImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
    Object? page = null,
    Object? pageSize = null,
    Object? hasNext = null,
  }) {
    return _then(_$ErrorListResponseImpl(
      items: null == items
          ? _value._items
          : items // ignore: cast_nullable_to_non_nullable
              as List<ErrorRecord>,
      total: null == total
          ? _value.total
          : total // ignore: cast_nullable_to_non_nullable
              as int,
      page: null == page
          ? _value.page
          : page // ignore: cast_nullable_to_non_nullable
              as int,
      pageSize: null == pageSize
          ? _value.pageSize
          : pageSize // ignore: cast_nullable_to_non_nullable
              as int,
      hasNext: null == hasNext
          ? _value.hasNext
          : hasNext // ignore: cast_nullable_to_non_nullable
              as bool,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ErrorListResponseImpl implements _ErrorListResponse {
  const _$ErrorListResponseImpl(
      {required final List<ErrorRecord> items,
      required this.total,
      required this.page,
      @JsonKey(name: 'page_size') required this.pageSize,
      @JsonKey(name: 'has_next') required this.hasNext})
      : _items = items;

  factory _$ErrorListResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$ErrorListResponseImplFromJson(json);

  final List<ErrorRecord> _items;
  @override
  List<ErrorRecord> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final int total;
  @override
  final int page;
  @override
  @JsonKey(name: 'page_size')
  final int pageSize;
  @override
  @JsonKey(name: 'has_next')
  final bool hasNext;

  @override
  String toString() {
    return 'ErrorListResponse(items: $items, total: $total, page: $page, pageSize: $pageSize, hasNext: $hasNext)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ErrorListResponseImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.total, total) || other.total == total) &&
            (identical(other.page, page) || other.page == page) &&
            (identical(other.pageSize, pageSize) ||
                other.pageSize == pageSize) &&
            (identical(other.hasNext, hasNext) || other.hasNext == hasNext));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      const DeepCollectionEquality().hash(_items),
      total,
      page,
      pageSize,
      hasNext);

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$ErrorListResponseImplCopyWith<_$ErrorListResponseImpl> get copyWith =>
      __$$ErrorListResponseImplCopyWithImpl<_$ErrorListResponseImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ErrorListResponseImplToJson(
      this,
    );
  }
}

abstract class _ErrorListResponse implements ErrorListResponse {
  const factory _ErrorListResponse(
          {required final List<ErrorRecord> items,
          required final int total,
          required final int page,
          @JsonKey(name: 'page_size') required final int pageSize,
          @JsonKey(name: 'has_next') required final bool hasNext}) =
      _$ErrorListResponseImpl;

  factory _ErrorListResponse.fromJson(Map<String, dynamic> json) =
      _$ErrorListResponseImpl.fromJson;

  @override
  List<ErrorRecord> get items;
  @override
  int get total;
  @override
  int get page;
  @override
  @JsonKey(name: 'page_size')
  int get pageSize;
  @override
  @JsonKey(name: 'has_next')
  bool get hasNext;
  @override
  @JsonKey(ignore: true)
  _$$ErrorListResponseImplCopyWith<_$ErrorListResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

ReviewStats _$ReviewStatsFromJson(Map<String, dynamic> json) {
  return _ReviewStats.fromJson(json);
}

/// @nodoc
mixin _$ReviewStats {
  @JsonKey(name: 'total_errors')
  int get totalErrors => throw _privateConstructorUsedError;
  @JsonKey(name: 'mastered_count')
  int get masteredCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'need_review_count')
  int get needReviewCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'review_streak_days')
  int get reviewStreakDays => throw _privateConstructorUsedError;
  @JsonKey(name: 'subject_distribution')
  Map<String, int> get subjectDistribution =>
      throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;
  @JsonKey(ignore: true)
  $ReviewStatsCopyWith<ReviewStats> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ReviewStatsCopyWith<$Res> {
  factory $ReviewStatsCopyWith(
          ReviewStats value, $Res Function(ReviewStats) then) =
      _$ReviewStatsCopyWithImpl<$Res, ReviewStats>;
  @useResult
  $Res call(
      {@JsonKey(name: 'total_errors') int totalErrors,
      @JsonKey(name: 'mastered_count') int masteredCount,
      @JsonKey(name: 'need_review_count') int needReviewCount,
      @JsonKey(name: 'review_streak_days') int reviewStreakDays,
      @JsonKey(name: 'subject_distribution')
      Map<String, int> subjectDistribution});
}

/// @nodoc
class _$ReviewStatsCopyWithImpl<$Res, $Val extends ReviewStats>
    implements $ReviewStatsCopyWith<$Res> {
  _$ReviewStatsCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalErrors = null,
    Object? masteredCount = null,
    Object? needReviewCount = null,
    Object? reviewStreakDays = null,
    Object? subjectDistribution = null,
  }) {
    return _then(_value.copyWith(
      totalErrors: null == totalErrors
          ? _value.totalErrors
          : totalErrors // ignore: cast_nullable_to_non_nullable
              as int,
      masteredCount: null == masteredCount
          ? _value.masteredCount
          : masteredCount // ignore: cast_nullable_to_non_nullable
              as int,
      needReviewCount: null == needReviewCount
          ? _value.needReviewCount
          : needReviewCount // ignore: cast_nullable_to_non_nullable
              as int,
      reviewStreakDays: null == reviewStreakDays
          ? _value.reviewStreakDays
          : reviewStreakDays // ignore: cast_nullable_to_non_nullable
              as int,
      subjectDistribution: null == subjectDistribution
          ? _value.subjectDistribution
          : subjectDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ReviewStatsImplCopyWith<$Res>
    implements $ReviewStatsCopyWith<$Res> {
  factory _$$ReviewStatsImplCopyWith(
          _$ReviewStatsImpl value, $Res Function(_$ReviewStatsImpl) then) =
      __$$ReviewStatsImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {@JsonKey(name: 'total_errors') int totalErrors,
      @JsonKey(name: 'mastered_count') int masteredCount,
      @JsonKey(name: 'need_review_count') int needReviewCount,
      @JsonKey(name: 'review_streak_days') int reviewStreakDays,
      @JsonKey(name: 'subject_distribution')
      Map<String, int> subjectDistribution});
}

/// @nodoc
class __$$ReviewStatsImplCopyWithImpl<$Res>
    extends _$ReviewStatsCopyWithImpl<$Res, _$ReviewStatsImpl>
    implements _$$ReviewStatsImplCopyWith<$Res> {
  __$$ReviewStatsImplCopyWithImpl(
      _$ReviewStatsImpl _value, $Res Function(_$ReviewStatsImpl) _then)
      : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? totalErrors = null,
    Object? masteredCount = null,
    Object? needReviewCount = null,
    Object? reviewStreakDays = null,
    Object? subjectDistribution = null,
  }) {
    return _then(_$ReviewStatsImpl(
      totalErrors: null == totalErrors
          ? _value.totalErrors
          : totalErrors // ignore: cast_nullable_to_non_nullable
              as int,
      masteredCount: null == masteredCount
          ? _value.masteredCount
          : masteredCount // ignore: cast_nullable_to_non_nullable
              as int,
      needReviewCount: null == needReviewCount
          ? _value.needReviewCount
          : needReviewCount // ignore: cast_nullable_to_non_nullable
              as int,
      reviewStreakDays: null == reviewStreakDays
          ? _value.reviewStreakDays
          : reviewStreakDays // ignore: cast_nullable_to_non_nullable
              as int,
      subjectDistribution: null == subjectDistribution
          ? _value._subjectDistribution
          : subjectDistribution // ignore: cast_nullable_to_non_nullable
              as Map<String, int>,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ReviewStatsImpl implements _ReviewStats {
  const _$ReviewStatsImpl(
      {@JsonKey(name: 'total_errors') required this.totalErrors,
      @JsonKey(name: 'mastered_count') required this.masteredCount,
      @JsonKey(name: 'need_review_count') required this.needReviewCount,
      @JsonKey(name: 'review_streak_days') required this.reviewStreakDays,
      @JsonKey(name: 'subject_distribution')
      required final Map<String, int> subjectDistribution})
      : _subjectDistribution = subjectDistribution;

  factory _$ReviewStatsImpl.fromJson(Map<String, dynamic> json) =>
      _$$ReviewStatsImplFromJson(json);

  @override
  @JsonKey(name: 'total_errors')
  final int totalErrors;
  @override
  @JsonKey(name: 'mastered_count')
  final int masteredCount;
  @override
  @JsonKey(name: 'need_review_count')
  final int needReviewCount;
  @override
  @JsonKey(name: 'review_streak_days')
  final int reviewStreakDays;
  final Map<String, int> _subjectDistribution;
  @override
  @JsonKey(name: 'subject_distribution')
  Map<String, int> get subjectDistribution {
    if (_subjectDistribution is EqualUnmodifiableMapView)
      return _subjectDistribution;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_subjectDistribution);
  }

  @override
  String toString() {
    return 'ReviewStats(totalErrors: $totalErrors, masteredCount: $masteredCount, needReviewCount: $needReviewCount, reviewStreakDays: $reviewStreakDays, subjectDistribution: $subjectDistribution)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ReviewStatsImpl &&
            (identical(other.totalErrors, totalErrors) ||
                other.totalErrors == totalErrors) &&
            (identical(other.masteredCount, masteredCount) ||
                other.masteredCount == masteredCount) &&
            (identical(other.needReviewCount, needReviewCount) ||
                other.needReviewCount == needReviewCount) &&
            (identical(other.reviewStreakDays, reviewStreakDays) ||
                other.reviewStreakDays == reviewStreakDays) &&
            const DeepCollectionEquality()
                .equals(other._subjectDistribution, _subjectDistribution));
  }

  @JsonKey(ignore: true)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      totalErrors,
      masteredCount,
      needReviewCount,
      reviewStreakDays,
      const DeepCollectionEquality().hash(_subjectDistribution));

  @JsonKey(ignore: true)
  @override
  @pragma('vm:prefer-inline')
  _$$ReviewStatsImplCopyWith<_$ReviewStatsImpl> get copyWith =>
      __$$ReviewStatsImplCopyWithImpl<_$ReviewStatsImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ReviewStatsImplToJson(
      this,
    );
  }
}

abstract class _ReviewStats implements ReviewStats {
  const factory _ReviewStats(
      {@JsonKey(name: 'total_errors') required final int totalErrors,
      @JsonKey(name: 'mastered_count') required final int masteredCount,
      @JsonKey(name: 'need_review_count') required final int needReviewCount,
      @JsonKey(name: 'review_streak_days') required final int reviewStreakDays,
      @JsonKey(name: 'subject_distribution')
      required final Map<String, int> subjectDistribution}) = _$ReviewStatsImpl;

  factory _ReviewStats.fromJson(Map<String, dynamic> json) =
      _$ReviewStatsImpl.fromJson;

  @override
  @JsonKey(name: 'total_errors')
  int get totalErrors;
  @override
  @JsonKey(name: 'mastered_count')
  int get masteredCount;
  @override
  @JsonKey(name: 'need_review_count')
  int get needReviewCount;
  @override
  @JsonKey(name: 'review_streak_days')
  int get reviewStreakDays;
  @override
  @JsonKey(name: 'subject_distribution')
  Map<String, int> get subjectDistribution;
  @override
  @JsonKey(ignore: true)
  _$$ReviewStatsImplCopyWith<_$ReviewStatsImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
