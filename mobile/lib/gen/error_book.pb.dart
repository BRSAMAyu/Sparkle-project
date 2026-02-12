// This is a generated file - do not edit.
//
// Generated from error_book.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;
import 'package:protobuf/well_known_types/google/protobuf/timestamp.pb.dart'
    as $1;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

class ErrorRecord extends $pb.GeneratedMessage {
  factory ErrorRecord({
    $core.String? id,
    $core.String? userId,
    $core.String? subjectCode,
    $core.String? chapter,
    $core.String? questionText,
    $core.String? questionImageUrl,
    $core.String? userAnswer,
    $core.String? correctAnswer,
    $core.double? masteryLevel,
    $core.int? reviewCount,
    $1.Timestamp? nextReviewAt,
    $1.Timestamp? lastReviewedAt,
    ErrorAnalysisResult? latestAnalysis,
    $core.Iterable<KnowledgeLinkBrief>? knowledgeLinks,
    $1.Timestamp? createdAt,
    $1.Timestamp? updatedAt,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (userId != null) result.userId = userId;
    if (subjectCode != null) result.subjectCode = subjectCode;
    if (chapter != null) result.chapter = chapter;
    if (questionText != null) result.questionText = questionText;
    if (questionImageUrl != null) result.questionImageUrl = questionImageUrl;
    if (userAnswer != null) result.userAnswer = userAnswer;
    if (correctAnswer != null) result.correctAnswer = correctAnswer;
    if (masteryLevel != null) result.masteryLevel = masteryLevel;
    if (reviewCount != null) result.reviewCount = reviewCount;
    if (nextReviewAt != null) result.nextReviewAt = nextReviewAt;
    if (lastReviewedAt != null) result.lastReviewedAt = lastReviewedAt;
    if (latestAnalysis != null) result.latestAnalysis = latestAnalysis;
    if (knowledgeLinks != null) result.knowledgeLinks.addAll(knowledgeLinks);
    if (createdAt != null) result.createdAt = createdAt;
    if (updatedAt != null) result.updatedAt = updatedAt;
    return result;
  }

  ErrorRecord._();

  factory ErrorRecord.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ErrorRecord.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ErrorRecord',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOS(3, _omitFieldNames ? '' : 'subjectCode')
    ..aOS(4, _omitFieldNames ? '' : 'chapter')
    ..aOS(5, _omitFieldNames ? '' : 'questionText')
    ..aOS(6, _omitFieldNames ? '' : 'questionImageUrl')
    ..aOS(7, _omitFieldNames ? '' : 'userAnswer')
    ..aOS(8, _omitFieldNames ? '' : 'correctAnswer')
    ..aD(9, _omitFieldNames ? '' : 'masteryLevel')
    ..aI(10, _omitFieldNames ? '' : 'reviewCount')
    ..aOM<$1.Timestamp>(11, _omitFieldNames ? '' : 'nextReviewAt',
        subBuilder: $1.Timestamp.create)
    ..aOM<$1.Timestamp>(12, _omitFieldNames ? '' : 'lastReviewedAt',
        subBuilder: $1.Timestamp.create)
    ..aOM<ErrorAnalysisResult>(13, _omitFieldNames ? '' : 'latestAnalysis',
        subBuilder: ErrorAnalysisResult.create)
    ..pPM<KnowledgeLinkBrief>(14, _omitFieldNames ? '' : 'knowledgeLinks',
        subBuilder: KnowledgeLinkBrief.create)
    ..aOM<$1.Timestamp>(15, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $1.Timestamp.create)
    ..aOM<$1.Timestamp>(16, _omitFieldNames ? '' : 'updatedAt',
        subBuilder: $1.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ErrorRecord clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ErrorRecord copyWith(void Function(ErrorRecord) updates) =>
      super.copyWith((message) => updates(message as ErrorRecord))
          as ErrorRecord;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ErrorRecord create() => ErrorRecord._();
  @$core.override
  ErrorRecord createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ErrorRecord getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ErrorRecord>(create);
  static ErrorRecord? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get subjectCode => $_getSZ(2);
  @$pb.TagNumber(3)
  set subjectCode($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSubjectCode() => $_has(2);
  @$pb.TagNumber(3)
  void clearSubjectCode() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get chapter => $_getSZ(3);
  @$pb.TagNumber(4)
  set chapter($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasChapter() => $_has(3);
  @$pb.TagNumber(4)
  void clearChapter() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get questionText => $_getSZ(4);
  @$pb.TagNumber(5)
  set questionText($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasQuestionText() => $_has(4);
  @$pb.TagNumber(5)
  void clearQuestionText() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get questionImageUrl => $_getSZ(5);
  @$pb.TagNumber(6)
  set questionImageUrl($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasQuestionImageUrl() => $_has(5);
  @$pb.TagNumber(6)
  void clearQuestionImageUrl() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get userAnswer => $_getSZ(6);
  @$pb.TagNumber(7)
  set userAnswer($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasUserAnswer() => $_has(6);
  @$pb.TagNumber(7)
  void clearUserAnswer() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get correctAnswer => $_getSZ(7);
  @$pb.TagNumber(8)
  set correctAnswer($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasCorrectAnswer() => $_has(7);
  @$pb.TagNumber(8)
  void clearCorrectAnswer() => $_clearField(8);

  /// Review Status
  @$pb.TagNumber(9)
  $core.double get masteryLevel => $_getN(8);
  @$pb.TagNumber(9)
  set masteryLevel($core.double value) => $_setDouble(8, value);
  @$pb.TagNumber(9)
  $core.bool hasMasteryLevel() => $_has(8);
  @$pb.TagNumber(9)
  void clearMasteryLevel() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.int get reviewCount => $_getIZ(9);
  @$pb.TagNumber(10)
  set reviewCount($core.int value) => $_setSignedInt32(9, value);
  @$pb.TagNumber(10)
  $core.bool hasReviewCount() => $_has(9);
  @$pb.TagNumber(10)
  void clearReviewCount() => $_clearField(10);

  @$pb.TagNumber(11)
  $1.Timestamp get nextReviewAt => $_getN(10);
  @$pb.TagNumber(11)
  set nextReviewAt($1.Timestamp value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasNextReviewAt() => $_has(10);
  @$pb.TagNumber(11)
  void clearNextReviewAt() => $_clearField(11);
  @$pb.TagNumber(11)
  $1.Timestamp ensureNextReviewAt() => $_ensure(10);

  @$pb.TagNumber(12)
  $1.Timestamp get lastReviewedAt => $_getN(11);
  @$pb.TagNumber(12)
  set lastReviewedAt($1.Timestamp value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasLastReviewedAt() => $_has(11);
  @$pb.TagNumber(12)
  void clearLastReviewedAt() => $_clearField(12);
  @$pb.TagNumber(12)
  $1.Timestamp ensureLastReviewedAt() => $_ensure(11);

  /// Analysis & Links
  @$pb.TagNumber(13)
  ErrorAnalysisResult get latestAnalysis => $_getN(12);
  @$pb.TagNumber(13)
  set latestAnalysis(ErrorAnalysisResult value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasLatestAnalysis() => $_has(12);
  @$pb.TagNumber(13)
  void clearLatestAnalysis() => $_clearField(13);
  @$pb.TagNumber(13)
  ErrorAnalysisResult ensureLatestAnalysis() => $_ensure(12);

  @$pb.TagNumber(14)
  $pb.PbList<KnowledgeLinkBrief> get knowledgeLinks => $_getList(13);

  @$pb.TagNumber(15)
  $1.Timestamp get createdAt => $_getN(14);
  @$pb.TagNumber(15)
  set createdAt($1.Timestamp value) => $_setField(15, value);
  @$pb.TagNumber(15)
  $core.bool hasCreatedAt() => $_has(14);
  @$pb.TagNumber(15)
  void clearCreatedAt() => $_clearField(15);
  @$pb.TagNumber(15)
  $1.Timestamp ensureCreatedAt() => $_ensure(14);

  @$pb.TagNumber(16)
  $1.Timestamp get updatedAt => $_getN(15);
  @$pb.TagNumber(16)
  set updatedAt($1.Timestamp value) => $_setField(16, value);
  @$pb.TagNumber(16)
  $core.bool hasUpdatedAt() => $_has(15);
  @$pb.TagNumber(16)
  void clearUpdatedAt() => $_clearField(16);
  @$pb.TagNumber(16)
  $1.Timestamp ensureUpdatedAt() => $_ensure(15);
}

class ErrorAnalysisResult extends $pb.GeneratedMessage {
  factory ErrorAnalysisResult({
    $core.String? errorType,
    $core.String? errorTypeLabel,
    $core.String? rootCause,
    $core.String? correctApproach,
    $core.Iterable<$core.String>? similarTraps,
    $core.Iterable<$core.String>? recommendedKnowledge,
    $core.String? studySuggestion,
    $core.String? ocrText,
  }) {
    final result = create();
    if (errorType != null) result.errorType = errorType;
    if (errorTypeLabel != null) result.errorTypeLabel = errorTypeLabel;
    if (rootCause != null) result.rootCause = rootCause;
    if (correctApproach != null) result.correctApproach = correctApproach;
    if (similarTraps != null) result.similarTraps.addAll(similarTraps);
    if (recommendedKnowledge != null)
      result.recommendedKnowledge.addAll(recommendedKnowledge);
    if (studySuggestion != null) result.studySuggestion = studySuggestion;
    if (ocrText != null) result.ocrText = ocrText;
    return result;
  }

  ErrorAnalysisResult._();

  factory ErrorAnalysisResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ErrorAnalysisResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ErrorAnalysisResult',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorType')
    ..aOS(2, _omitFieldNames ? '' : 'errorTypeLabel')
    ..aOS(3, _omitFieldNames ? '' : 'rootCause')
    ..aOS(4, _omitFieldNames ? '' : 'correctApproach')
    ..pPS(5, _omitFieldNames ? '' : 'similarTraps')
    ..pPS(6, _omitFieldNames ? '' : 'recommendedKnowledge')
    ..aOS(7, _omitFieldNames ? '' : 'studySuggestion')
    ..aOS(8, _omitFieldNames ? '' : 'ocrText')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ErrorAnalysisResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ErrorAnalysisResult copyWith(void Function(ErrorAnalysisResult) updates) =>
      super.copyWith((message) => updates(message as ErrorAnalysisResult))
          as ErrorAnalysisResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ErrorAnalysisResult create() => ErrorAnalysisResult._();
  @$core.override
  ErrorAnalysisResult createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ErrorAnalysisResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ErrorAnalysisResult>(create);
  static ErrorAnalysisResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorType => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorType($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorType() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorType() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get errorTypeLabel => $_getSZ(1);
  @$pb.TagNumber(2)
  set errorTypeLabel($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasErrorTypeLabel() => $_has(1);
  @$pb.TagNumber(2)
  void clearErrorTypeLabel() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get rootCause => $_getSZ(2);
  @$pb.TagNumber(3)
  set rootCause($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasRootCause() => $_has(2);
  @$pb.TagNumber(3)
  void clearRootCause() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get correctApproach => $_getSZ(3);
  @$pb.TagNumber(4)
  set correctApproach($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCorrectApproach() => $_has(3);
  @$pb.TagNumber(4)
  void clearCorrectApproach() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbList<$core.String> get similarTraps => $_getList(4);

  @$pb.TagNumber(6)
  $pb.PbList<$core.String> get recommendedKnowledge => $_getList(5);

  @$pb.TagNumber(7)
  $core.String get studySuggestion => $_getSZ(6);
  @$pb.TagNumber(7)
  set studySuggestion($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasStudySuggestion() => $_has(6);
  @$pb.TagNumber(7)
  void clearStudySuggestion() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get ocrText => $_getSZ(7);
  @$pb.TagNumber(8)
  set ocrText($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasOcrText() => $_has(7);
  @$pb.TagNumber(8)
  void clearOcrText() => $_clearField(8);
}

class KnowledgeLinkBrief extends $pb.GeneratedMessage {
  factory KnowledgeLinkBrief({
    $core.String? id,
    $core.String? name,
    $core.double? relevance,
    $core.bool? isPrimary,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (name != null) result.name = name;
    if (relevance != null) result.relevance = relevance;
    if (isPrimary != null) result.isPrimary = isPrimary;
    return result;
  }

  KnowledgeLinkBrief._();

  factory KnowledgeLinkBrief.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory KnowledgeLinkBrief.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'KnowledgeLinkBrief',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'name')
    ..aD(3, _omitFieldNames ? '' : 'relevance')
    ..aOB(4, _omitFieldNames ? '' : 'isPrimary')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  KnowledgeLinkBrief clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  KnowledgeLinkBrief copyWith(void Function(KnowledgeLinkBrief) updates) =>
      super.copyWith((message) => updates(message as KnowledgeLinkBrief))
          as KnowledgeLinkBrief;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static KnowledgeLinkBrief create() => KnowledgeLinkBrief._();
  @$core.override
  KnowledgeLinkBrief createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static KnowledgeLinkBrief getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<KnowledgeLinkBrief>(create);
  static KnowledgeLinkBrief? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get name => $_getSZ(1);
  @$pb.TagNumber(2)
  set name($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasName() => $_has(1);
  @$pb.TagNumber(2)
  void clearName() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.double get relevance => $_getN(2);
  @$pb.TagNumber(3)
  set relevance($core.double value) => $_setDouble(2, value);
  @$pb.TagNumber(3)
  $core.bool hasRelevance() => $_has(2);
  @$pb.TagNumber(3)
  void clearRelevance() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get isPrimary => $_getBF(3);
  @$pb.TagNumber(4)
  set isPrimary($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasIsPrimary() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsPrimary() => $_clearField(4);
}

class CreateErrorRequest extends $pb.GeneratedMessage {
  factory CreateErrorRequest({
    $core.String? userId,
    $core.String? questionText,
    $core.String? questionImageUrl,
    $core.String? userAnswer,
    $core.String? correctAnswer,
    $core.String? subjectCode,
    $core.String? chapter,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (questionText != null) result.questionText = questionText;
    if (questionImageUrl != null) result.questionImageUrl = questionImageUrl;
    if (userAnswer != null) result.userAnswer = userAnswer;
    if (correctAnswer != null) result.correctAnswer = correctAnswer;
    if (subjectCode != null) result.subjectCode = subjectCode;
    if (chapter != null) result.chapter = chapter;
    return result;
  }

  CreateErrorRequest._();

  factory CreateErrorRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CreateErrorRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CreateErrorRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'questionText')
    ..aOS(3, _omitFieldNames ? '' : 'questionImageUrl')
    ..aOS(4, _omitFieldNames ? '' : 'userAnswer')
    ..aOS(5, _omitFieldNames ? '' : 'correctAnswer')
    ..aOS(6, _omitFieldNames ? '' : 'subjectCode')
    ..aOS(7, _omitFieldNames ? '' : 'chapter')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CreateErrorRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CreateErrorRequest copyWith(void Function(CreateErrorRequest) updates) =>
      super.copyWith((message) => updates(message as CreateErrorRequest))
          as CreateErrorRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CreateErrorRequest create() => CreateErrorRequest._();
  @$core.override
  CreateErrorRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CreateErrorRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CreateErrorRequest>(create);
  static CreateErrorRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get questionText => $_getSZ(1);
  @$pb.TagNumber(2)
  set questionText($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasQuestionText() => $_has(1);
  @$pb.TagNumber(2)
  void clearQuestionText() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get questionImageUrl => $_getSZ(2);
  @$pb.TagNumber(3)
  set questionImageUrl($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasQuestionImageUrl() => $_has(2);
  @$pb.TagNumber(3)
  void clearQuestionImageUrl() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get userAnswer => $_getSZ(3);
  @$pb.TagNumber(4)
  set userAnswer($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasUserAnswer() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserAnswer() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get correctAnswer => $_getSZ(4);
  @$pb.TagNumber(5)
  set correctAnswer($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasCorrectAnswer() => $_has(4);
  @$pb.TagNumber(5)
  void clearCorrectAnswer() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get subjectCode => $_getSZ(5);
  @$pb.TagNumber(6)
  set subjectCode($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSubjectCode() => $_has(5);
  @$pb.TagNumber(6)
  void clearSubjectCode() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get chapter => $_getSZ(6);
  @$pb.TagNumber(7)
  set chapter($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasChapter() => $_has(6);
  @$pb.TagNumber(7)
  void clearChapter() => $_clearField(7);
}

class ListErrorsRequest extends $pb.GeneratedMessage {
  factory ListErrorsRequest({
    $core.String? userId,
    $core.String? subjectCode,
    $core.String? chapter,
    $core.String? errorType,
    $core.double? masteryMin,
    $core.double? masteryMax,
    $core.bool? needReview,
    $core.String? keyword,
    $core.int? page,
    $core.int? pageSize,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (subjectCode != null) result.subjectCode = subjectCode;
    if (chapter != null) result.chapter = chapter;
    if (errorType != null) result.errorType = errorType;
    if (masteryMin != null) result.masteryMin = masteryMin;
    if (masteryMax != null) result.masteryMax = masteryMax;
    if (needReview != null) result.needReview = needReview;
    if (keyword != null) result.keyword = keyword;
    if (page != null) result.page = page;
    if (pageSize != null) result.pageSize = pageSize;
    return result;
  }

  ListErrorsRequest._();

  factory ListErrorsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ListErrorsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ListErrorsRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'subjectCode')
    ..aOS(3, _omitFieldNames ? '' : 'chapter')
    ..aOS(4, _omitFieldNames ? '' : 'errorType')
    ..aD(5, _omitFieldNames ? '' : 'masteryMin')
    ..aD(6, _omitFieldNames ? '' : 'masteryMax')
    ..aOB(7, _omitFieldNames ? '' : 'needReview')
    ..aOS(8, _omitFieldNames ? '' : 'keyword')
    ..aI(9, _omitFieldNames ? '' : 'page')
    ..aI(10, _omitFieldNames ? '' : 'pageSize')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ListErrorsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ListErrorsRequest copyWith(void Function(ListErrorsRequest) updates) =>
      super.copyWith((message) => updates(message as ListErrorsRequest))
          as ListErrorsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ListErrorsRequest create() => ListErrorsRequest._();
  @$core.override
  ListErrorsRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ListErrorsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ListErrorsRequest>(create);
  static ListErrorsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get subjectCode => $_getSZ(1);
  @$pb.TagNumber(2)
  set subjectCode($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSubjectCode() => $_has(1);
  @$pb.TagNumber(2)
  void clearSubjectCode() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get chapter => $_getSZ(2);
  @$pb.TagNumber(3)
  set chapter($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasChapter() => $_has(2);
  @$pb.TagNumber(3)
  void clearChapter() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get errorType => $_getSZ(3);
  @$pb.TagNumber(4)
  set errorType($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasErrorType() => $_has(3);
  @$pb.TagNumber(4)
  void clearErrorType() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.double get masteryMin => $_getN(4);
  @$pb.TagNumber(5)
  set masteryMin($core.double value) => $_setDouble(4, value);
  @$pb.TagNumber(5)
  $core.bool hasMasteryMin() => $_has(4);
  @$pb.TagNumber(5)
  void clearMasteryMin() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.double get masteryMax => $_getN(5);
  @$pb.TagNumber(6)
  set masteryMax($core.double value) => $_setDouble(5, value);
  @$pb.TagNumber(6)
  $core.bool hasMasteryMax() => $_has(5);
  @$pb.TagNumber(6)
  void clearMasteryMax() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.bool get needReview => $_getBF(6);
  @$pb.TagNumber(7)
  set needReview($core.bool value) => $_setBool(6, value);
  @$pb.TagNumber(7)
  $core.bool hasNeedReview() => $_has(6);
  @$pb.TagNumber(7)
  void clearNeedReview() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get keyword => $_getSZ(7);
  @$pb.TagNumber(8)
  set keyword($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasKeyword() => $_has(7);
  @$pb.TagNumber(8)
  void clearKeyword() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.int get page => $_getIZ(8);
  @$pb.TagNumber(9)
  set page($core.int value) => $_setSignedInt32(8, value);
  @$pb.TagNumber(9)
  $core.bool hasPage() => $_has(8);
  @$pb.TagNumber(9)
  void clearPage() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.int get pageSize => $_getIZ(9);
  @$pb.TagNumber(10)
  set pageSize($core.int value) => $_setSignedInt32(9, value);
  @$pb.TagNumber(10)
  $core.bool hasPageSize() => $_has(9);
  @$pb.TagNumber(10)
  void clearPageSize() => $_clearField(10);
}

class ListErrorsResponse extends $pb.GeneratedMessage {
  factory ListErrorsResponse({
    $core.Iterable<ErrorRecord>? items,
    $fixnum.Int64? total,
    $core.int? page,
    $core.int? pageSize,
    $core.bool? hasNext,
  }) {
    final result = create();
    if (items != null) result.items.addAll(items);
    if (total != null) result.total = total;
    if (page != null) result.page = page;
    if (pageSize != null) result.pageSize = pageSize;
    if (hasNext != null) result.hasNext = hasNext;
    return result;
  }

  ListErrorsResponse._();

  factory ListErrorsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ListErrorsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ListErrorsResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..pPM<ErrorRecord>(1, _omitFieldNames ? '' : 'items',
        subBuilder: ErrorRecord.create)
    ..aInt64(2, _omitFieldNames ? '' : 'total')
    ..aI(3, _omitFieldNames ? '' : 'page')
    ..aI(4, _omitFieldNames ? '' : 'pageSize')
    ..aOB(5, _omitFieldNames ? '' : 'hasNext')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ListErrorsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ListErrorsResponse copyWith(void Function(ListErrorsResponse) updates) =>
      super.copyWith((message) => updates(message as ListErrorsResponse))
          as ListErrorsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ListErrorsResponse create() => ListErrorsResponse._();
  @$core.override
  ListErrorsResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ListErrorsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ListErrorsResponse>(create);
  static ListErrorsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<ErrorRecord> get items => $_getList(0);

  @$pb.TagNumber(2)
  $fixnum.Int64 get total => $_getI64(1);
  @$pb.TagNumber(2)
  set total($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTotal() => $_has(1);
  @$pb.TagNumber(2)
  void clearTotal() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get page => $_getIZ(2);
  @$pb.TagNumber(3)
  set page($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasPage() => $_has(2);
  @$pb.TagNumber(3)
  void clearPage() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get pageSize => $_getIZ(3);
  @$pb.TagNumber(4)
  set pageSize($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasPageSize() => $_has(3);
  @$pb.TagNumber(4)
  void clearPageSize() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.bool get hasNext => $_getBF(4);
  @$pb.TagNumber(5)
  set hasNext($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(5)
  $core.bool hasHasNext() => $_has(4);
  @$pb.TagNumber(5)
  void clearHasNext() => $_clearField(5);
}

class GetErrorRequest extends $pb.GeneratedMessage {
  factory GetErrorRequest({
    $core.String? errorId,
    $core.String? userId,
  }) {
    final result = create();
    if (errorId != null) result.errorId = errorId;
    if (userId != null) result.userId = userId;
    return result;
  }

  GetErrorRequest._();

  factory GetErrorRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GetErrorRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GetErrorRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetErrorRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetErrorRequest copyWith(void Function(GetErrorRequest) updates) =>
      super.copyWith((message) => updates(message as GetErrorRequest))
          as GetErrorRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetErrorRequest create() => GetErrorRequest._();
  @$core.override
  GetErrorRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GetErrorRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GetErrorRequest>(create);
  static GetErrorRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorId => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorId() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);
}

class UpdateErrorRequest extends $pb.GeneratedMessage {
  factory UpdateErrorRequest({
    $core.String? errorId,
    $core.String? userId,
    $core.String? questionText,
    $core.String? userAnswer,
    $core.String? correctAnswer,
    $core.String? subjectCode,
    $core.String? chapter,
    $core.String? questionImageUrl,
  }) {
    final result = create();
    if (errorId != null) result.errorId = errorId;
    if (userId != null) result.userId = userId;
    if (questionText != null) result.questionText = questionText;
    if (userAnswer != null) result.userAnswer = userAnswer;
    if (correctAnswer != null) result.correctAnswer = correctAnswer;
    if (subjectCode != null) result.subjectCode = subjectCode;
    if (chapter != null) result.chapter = chapter;
    if (questionImageUrl != null) result.questionImageUrl = questionImageUrl;
    return result;
  }

  UpdateErrorRequest._();

  factory UpdateErrorRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UpdateErrorRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UpdateErrorRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOS(3, _omitFieldNames ? '' : 'questionText')
    ..aOS(4, _omitFieldNames ? '' : 'userAnswer')
    ..aOS(5, _omitFieldNames ? '' : 'correctAnswer')
    ..aOS(6, _omitFieldNames ? '' : 'subjectCode')
    ..aOS(7, _omitFieldNames ? '' : 'chapter')
    ..aOS(8, _omitFieldNames ? '' : 'questionImageUrl')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UpdateErrorRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UpdateErrorRequest copyWith(void Function(UpdateErrorRequest) updates) =>
      super.copyWith((message) => updates(message as UpdateErrorRequest))
          as UpdateErrorRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UpdateErrorRequest create() => UpdateErrorRequest._();
  @$core.override
  UpdateErrorRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UpdateErrorRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UpdateErrorRequest>(create);
  static UpdateErrorRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorId => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorId() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get questionText => $_getSZ(2);
  @$pb.TagNumber(3)
  set questionText($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasQuestionText() => $_has(2);
  @$pb.TagNumber(3)
  void clearQuestionText() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get userAnswer => $_getSZ(3);
  @$pb.TagNumber(4)
  set userAnswer($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasUserAnswer() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserAnswer() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get correctAnswer => $_getSZ(4);
  @$pb.TagNumber(5)
  set correctAnswer($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasCorrectAnswer() => $_has(4);
  @$pb.TagNumber(5)
  void clearCorrectAnswer() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get subjectCode => $_getSZ(5);
  @$pb.TagNumber(6)
  set subjectCode($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSubjectCode() => $_has(5);
  @$pb.TagNumber(6)
  void clearSubjectCode() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get chapter => $_getSZ(6);
  @$pb.TagNumber(7)
  set chapter($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasChapter() => $_has(6);
  @$pb.TagNumber(7)
  void clearChapter() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get questionImageUrl => $_getSZ(7);
  @$pb.TagNumber(8)
  set questionImageUrl($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasQuestionImageUrl() => $_has(7);
  @$pb.TagNumber(8)
  void clearQuestionImageUrl() => $_clearField(8);
}

class DeleteErrorRequest extends $pb.GeneratedMessage {
  factory DeleteErrorRequest({
    $core.String? errorId,
    $core.String? userId,
  }) {
    final result = create();
    if (errorId != null) result.errorId = errorId;
    if (userId != null) result.userId = userId;
    return result;
  }

  DeleteErrorRequest._();

  factory DeleteErrorRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory DeleteErrorRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'DeleteErrorRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  DeleteErrorRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  DeleteErrorRequest copyWith(void Function(DeleteErrorRequest) updates) =>
      super.copyWith((message) => updates(message as DeleteErrorRequest))
          as DeleteErrorRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static DeleteErrorRequest create() => DeleteErrorRequest._();
  @$core.override
  DeleteErrorRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static DeleteErrorRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<DeleteErrorRequest>(create);
  static DeleteErrorRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorId => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorId() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);
}

class DeleteErrorResponse extends $pb.GeneratedMessage {
  factory DeleteErrorResponse({
    $core.bool? success,
  }) {
    final result = create();
    if (success != null) result.success = success;
    return result;
  }

  DeleteErrorResponse._();

  factory DeleteErrorResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory DeleteErrorResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'DeleteErrorResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  DeleteErrorResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  DeleteErrorResponse copyWith(void Function(DeleteErrorResponse) updates) =>
      super.copyWith((message) => updates(message as DeleteErrorResponse))
          as DeleteErrorResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static DeleteErrorResponse create() => DeleteErrorResponse._();
  @$core.override
  DeleteErrorResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static DeleteErrorResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<DeleteErrorResponse>(create);
  static DeleteErrorResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => $_clearField(1);
}

class AnalyzeErrorRequest extends $pb.GeneratedMessage {
  factory AnalyzeErrorRequest({
    $core.String? errorId,
    $core.String? userId,
  }) {
    final result = create();
    if (errorId != null) result.errorId = errorId;
    if (userId != null) result.userId = userId;
    return result;
  }

  AnalyzeErrorRequest._();

  factory AnalyzeErrorRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory AnalyzeErrorRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'AnalyzeErrorRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AnalyzeErrorRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AnalyzeErrorRequest copyWith(void Function(AnalyzeErrorRequest) updates) =>
      super.copyWith((message) => updates(message as AnalyzeErrorRequest))
          as AnalyzeErrorRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AnalyzeErrorRequest create() => AnalyzeErrorRequest._();
  @$core.override
  AnalyzeErrorRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static AnalyzeErrorRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<AnalyzeErrorRequest>(create);
  static AnalyzeErrorRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorId => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorId() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);
}

class AnalyzeErrorResponse extends $pb.GeneratedMessage {
  factory AnalyzeErrorResponse({
    $core.String? message,
  }) {
    final result = create();
    if (message != null) result.message = message;
    return result;
  }

  AnalyzeErrorResponse._();

  factory AnalyzeErrorResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory AnalyzeErrorResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'AnalyzeErrorResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AnalyzeErrorResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AnalyzeErrorResponse copyWith(void Function(AnalyzeErrorResponse) updates) =>
      super.copyWith((message) => updates(message as AnalyzeErrorResponse))
          as AnalyzeErrorResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AnalyzeErrorResponse create() => AnalyzeErrorResponse._();
  @$core.override
  AnalyzeErrorResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static AnalyzeErrorResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<AnalyzeErrorResponse>(create);
  static AnalyzeErrorResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get message => $_getSZ(0);
  @$pb.TagNumber(1)
  set message($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasMessage() => $_has(0);
  @$pb.TagNumber(1)
  void clearMessage() => $_clearField(1);
}

class SubmitReviewRequest extends $pb.GeneratedMessage {
  factory SubmitReviewRequest({
    $core.String? errorId,
    $core.String? userId,
    $core.String? performance,
    $core.int? timeSpentSeconds,
  }) {
    final result = create();
    if (errorId != null) result.errorId = errorId;
    if (userId != null) result.userId = userId;
    if (performance != null) result.performance = performance;
    if (timeSpentSeconds != null) result.timeSpentSeconds = timeSpentSeconds;
    return result;
  }

  SubmitReviewRequest._();

  factory SubmitReviewRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory SubmitReviewRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'SubmitReviewRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'errorId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOS(3, _omitFieldNames ? '' : 'performance')
    ..aI(4, _omitFieldNames ? '' : 'timeSpentSeconds')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SubmitReviewRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  SubmitReviewRequest copyWith(void Function(SubmitReviewRequest) updates) =>
      super.copyWith((message) => updates(message as SubmitReviewRequest))
          as SubmitReviewRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SubmitReviewRequest create() => SubmitReviewRequest._();
  @$core.override
  SubmitReviewRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static SubmitReviewRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<SubmitReviewRequest>(create);
  static SubmitReviewRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get errorId => $_getSZ(0);
  @$pb.TagNumber(1)
  set errorId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasErrorId() => $_has(0);
  @$pb.TagNumber(1)
  void clearErrorId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get performance => $_getSZ(2);
  @$pb.TagNumber(3)
  set performance($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasPerformance() => $_has(2);
  @$pb.TagNumber(3)
  void clearPerformance() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get timeSpentSeconds => $_getIZ(3);
  @$pb.TagNumber(4)
  set timeSpentSeconds($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTimeSpentSeconds() => $_has(3);
  @$pb.TagNumber(4)
  void clearTimeSpentSeconds() => $_clearField(4);
}

class GetReviewStatsRequest extends $pb.GeneratedMessage {
  factory GetReviewStatsRequest({
    $core.String? userId,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    return result;
  }

  GetReviewStatsRequest._();

  factory GetReviewStatsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GetReviewStatsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GetReviewStatsRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetReviewStatsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetReviewStatsRequest copyWith(
          void Function(GetReviewStatsRequest) updates) =>
      super.copyWith((message) => updates(message as GetReviewStatsRequest))
          as GetReviewStatsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetReviewStatsRequest create() => GetReviewStatsRequest._();
  @$core.override
  GetReviewStatsRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GetReviewStatsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GetReviewStatsRequest>(create);
  static GetReviewStatsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);
}

class ReviewStatsResponse extends $pb.GeneratedMessage {
  factory ReviewStatsResponse({
    $fixnum.Int64? totalErrors,
    $fixnum.Int64? masteredCount,
    $fixnum.Int64? needReviewCount,
    $core.int? reviewStreakDays,
    $core.Iterable<$core.MapEntry<$core.String, $fixnum.Int64>>?
        subjectDistribution,
  }) {
    final result = create();
    if (totalErrors != null) result.totalErrors = totalErrors;
    if (masteredCount != null) result.masteredCount = masteredCount;
    if (needReviewCount != null) result.needReviewCount = needReviewCount;
    if (reviewStreakDays != null) result.reviewStreakDays = reviewStreakDays;
    if (subjectDistribution != null)
      result.subjectDistribution.addEntries(subjectDistribution);
    return result;
  }

  ReviewStatsResponse._();

  factory ReviewStatsResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ReviewStatsResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ReviewStatsResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aInt64(1, _omitFieldNames ? '' : 'totalErrors')
    ..aInt64(2, _omitFieldNames ? '' : 'masteredCount')
    ..aInt64(3, _omitFieldNames ? '' : 'needReviewCount')
    ..aI(4, _omitFieldNames ? '' : 'reviewStreakDays')
    ..m<$core.String, $fixnum.Int64>(
        5, _omitFieldNames ? '' : 'subjectDistribution',
        entryClassName: 'ReviewStatsResponse.SubjectDistributionEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.O6,
        packageName: const $pb.PackageName('error_book'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ReviewStatsResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ReviewStatsResponse copyWith(void Function(ReviewStatsResponse) updates) =>
      super.copyWith((message) => updates(message as ReviewStatsResponse))
          as ReviewStatsResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewStatsResponse create() => ReviewStatsResponse._();
  @$core.override
  ReviewStatsResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ReviewStatsResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ReviewStatsResponse>(create);
  static ReviewStatsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $fixnum.Int64 get totalErrors => $_getI64(0);
  @$pb.TagNumber(1)
  set totalErrors($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTotalErrors() => $_has(0);
  @$pb.TagNumber(1)
  void clearTotalErrors() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get masteredCount => $_getI64(1);
  @$pb.TagNumber(2)
  set masteredCount($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMasteredCount() => $_has(1);
  @$pb.TagNumber(2)
  void clearMasteredCount() => $_clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get needReviewCount => $_getI64(2);
  @$pb.TagNumber(3)
  set needReviewCount($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasNeedReviewCount() => $_has(2);
  @$pb.TagNumber(3)
  void clearNeedReviewCount() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get reviewStreakDays => $_getIZ(3);
  @$pb.TagNumber(4)
  set reviewStreakDays($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasReviewStreakDays() => $_has(3);
  @$pb.TagNumber(4)
  void clearReviewStreakDays() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbMap<$core.String, $fixnum.Int64> get subjectDistribution => $_getMap(4);
}

class GetTodayReviewsRequest extends $pb.GeneratedMessage {
  factory GetTodayReviewsRequest({
    $core.String? userId,
    $core.int? page,
    $core.int? pageSize,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (page != null) result.page = page;
    if (pageSize != null) result.pageSize = pageSize;
    return result;
  }

  GetTodayReviewsRequest._();

  factory GetTodayReviewsRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory GetTodayReviewsRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'GetTodayReviewsRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'error_book'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aI(2, _omitFieldNames ? '' : 'page')
    ..aI(3, _omitFieldNames ? '' : 'pageSize')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetTodayReviewsRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  GetTodayReviewsRequest copyWith(
          void Function(GetTodayReviewsRequest) updates) =>
      super.copyWith((message) => updates(message as GetTodayReviewsRequest))
          as GetTodayReviewsRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetTodayReviewsRequest create() => GetTodayReviewsRequest._();
  @$core.override
  GetTodayReviewsRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static GetTodayReviewsRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<GetTodayReviewsRequest>(create);
  static GetTodayReviewsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get page => $_getIZ(1);
  @$pb.TagNumber(2)
  set page($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasPage() => $_has(1);
  @$pb.TagNumber(2)
  void clearPage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get pageSize => $_getIZ(2);
  @$pb.TagNumber(3)
  set pageSize($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasPageSize() => $_has(2);
  @$pb.TagNumber(3)
  void clearPageSize() => $_clearField(3);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
