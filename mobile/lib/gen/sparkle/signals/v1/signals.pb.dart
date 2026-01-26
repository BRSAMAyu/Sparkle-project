//
//  Generated code. Do not modify.
//  source: sparkle/signals/v1/signals.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class CandidateAction extends $pb.GeneratedMessage {
  factory CandidateAction({
    $core.String? id,
    $core.String? type,
    $core.String? trigger,
    $core.String? contentSeed,
    $core.double? priority,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (type != null) {
      $result.type = type;
    }
    if (trigger != null) {
      $result.trigger = trigger;
    }
    if (contentSeed != null) {
      $result.contentSeed = contentSeed;
    }
    if (priority != null) {
      $result.priority = priority;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  CandidateAction._() : super();
  factory CandidateAction.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory CandidateAction.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'CandidateAction', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..aOS(3, _omitFieldNames ? '' : 'trigger')
    ..aOS(4, _omitFieldNames ? '' : 'contentSeed')
    ..a<$core.double>(5, _omitFieldNames ? '' : 'priority', $pb.PbFieldType.OF)
    ..m<$core.String, $core.String>(6, _omitFieldNames ? '' : 'metadata', entryClassName: 'CandidateAction.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  CandidateAction clone() => CandidateAction()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  CandidateAction copyWith(void Function(CandidateAction) updates) => super.copyWith((message) => updates(message as CandidateAction)) as CandidateAction;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CandidateAction create() => CandidateAction._();
  CandidateAction createEmptyInstance() => create();
  static $pb.PbList<CandidateAction> createRepeated() => $pb.PbList<CandidateAction>();
  @$core.pragma('dart2js:noInline')
  static CandidateAction getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CandidateAction>(create);
  static CandidateAction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get trigger => $_getSZ(2);
  @$pb.TagNumber(3)
  set trigger($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTrigger() => $_has(2);
  @$pb.TagNumber(3)
  void clearTrigger() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get contentSeed => $_getSZ(3);
  @$pb.TagNumber(4)
  set contentSeed($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasContentSeed() => $_has(3);
  @$pb.TagNumber(4)
  void clearContentSeed() => clearField(4);

  @$pb.TagNumber(5)
  $core.double get priority => $_getN(4);
  @$pb.TagNumber(5)
  set priority($core.double v) { $_setFloat(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasPriority() => $_has(4);
  @$pb.TagNumber(5)
  void clearPriority() => clearField(5);

  @$pb.TagNumber(6)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(5);
}

class NextActionsCandidateSet extends $pb.GeneratedMessage {
  factory NextActionsCandidateSet({
    $core.String? requestId,
    $core.String? traceId,
    $core.String? userId,
    $core.String? schemaVersion,
    $core.String? idempotencyKey,
    $core.Iterable<CandidateAction>? candidates,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    if (schemaVersion != null) {
      $result.schemaVersion = schemaVersion;
    }
    if (idempotencyKey != null) {
      $result.idempotencyKey = idempotencyKey;
    }
    if (candidates != null) {
      $result.candidates.addAll(candidates);
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  NextActionsCandidateSet._() : super();
  factory NextActionsCandidateSet.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory NextActionsCandidateSet.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'NextActionsCandidateSet', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..aOS(4, _omitFieldNames ? '' : 'schemaVersion')
    ..aOS(5, _omitFieldNames ? '' : 'idempotencyKey')
    ..pc<CandidateAction>(6, _omitFieldNames ? '' : 'candidates', $pb.PbFieldType.PM, subBuilder: CandidateAction.create)
    ..m<$core.String, $core.String>(7, _omitFieldNames ? '' : 'metadata', entryClassName: 'NextActionsCandidateSet.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  NextActionsCandidateSet clone() => NextActionsCandidateSet()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  NextActionsCandidateSet copyWith(void Function(NextActionsCandidateSet) updates) => super.copyWith((message) => updates(message as NextActionsCandidateSet)) as NextActionsCandidateSet;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static NextActionsCandidateSet create() => NextActionsCandidateSet._();
  NextActionsCandidateSet createEmptyInstance() => create();
  static $pb.PbList<NextActionsCandidateSet> createRepeated() => $pb.PbList<NextActionsCandidateSet>();
  @$core.pragma('dart2js:noInline')
  static NextActionsCandidateSet getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<NextActionsCandidateSet>(create);
  static NextActionsCandidateSet? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get requestId => $_getSZ(0);
  @$pb.TagNumber(1)
  set requestId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasRequestId() => $_has(0);
  @$pb.TagNumber(1)
  void clearRequestId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get traceId => $_getSZ(1);
  @$pb.TagNumber(2)
  set traceId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTraceId() => $_has(1);
  @$pb.TagNumber(2)
  void clearTraceId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get schemaVersion => $_getSZ(3);
  @$pb.TagNumber(4)
  set schemaVersion($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasSchemaVersion() => $_has(3);
  @$pb.TagNumber(4)
  void clearSchemaVersion() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get idempotencyKey => $_getSZ(4);
  @$pb.TagNumber(5)
  set idempotencyKey($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasIdempotencyKey() => $_has(4);
  @$pb.TagNumber(5)
  void clearIdempotencyKey() => clearField(5);

  @$pb.TagNumber(6)
  $core.List<CandidateAction> get candidates => $_getList(5);

  @$pb.TagNumber(7)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(6);
}

/// Mobile sends compressed context, not raw events
class ContextEnvelope extends $pb.GeneratedMessage {
  factory ContextEnvelope({
    $core.String? contextVersion,
    $core.String? window,
    FocusMetrics? focus,
    ComprehensionMetrics? comprehension,
    TimeContext? time,
    ContentContext? content,
    $core.bool? piiScrubbed,
  }) {
    final $result = create();
    if (contextVersion != null) {
      $result.contextVersion = contextVersion;
    }
    if (window != null) {
      $result.window = window;
    }
    if (focus != null) {
      $result.focus = focus;
    }
    if (comprehension != null) {
      $result.comprehension = comprehension;
    }
    if (time != null) {
      $result.time = time;
    }
    if (content != null) {
      $result.content = content;
    }
    if (piiScrubbed != null) {
      $result.piiScrubbed = piiScrubbed;
    }
    return $result;
  }
  ContextEnvelope._() : super();
  factory ContextEnvelope.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ContextEnvelope.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ContextEnvelope', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'contextVersion')
    ..aOS(2, _omitFieldNames ? '' : 'window')
    ..aOM<FocusMetrics>(3, _omitFieldNames ? '' : 'focus', subBuilder: FocusMetrics.create)
    ..aOM<ComprehensionMetrics>(4, _omitFieldNames ? '' : 'comprehension', subBuilder: ComprehensionMetrics.create)
    ..aOM<TimeContext>(5, _omitFieldNames ? '' : 'time', subBuilder: TimeContext.create)
    ..aOM<ContentContext>(6, _omitFieldNames ? '' : 'content', subBuilder: ContentContext.create)
    ..aOB(7, _omitFieldNames ? '' : 'piiScrubbed')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ContextEnvelope clone() => ContextEnvelope()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ContextEnvelope copyWith(void Function(ContextEnvelope) updates) => super.copyWith((message) => updates(message as ContextEnvelope)) as ContextEnvelope;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContextEnvelope create() => ContextEnvelope._();
  ContextEnvelope createEmptyInstance() => create();
  static $pb.PbList<ContextEnvelope> createRepeated() => $pb.PbList<ContextEnvelope>();
  @$core.pragma('dart2js:noInline')
  static ContextEnvelope getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ContextEnvelope>(create);
  static ContextEnvelope? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get contextVersion => $_getSZ(0);
  @$pb.TagNumber(1)
  set contextVersion($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasContextVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearContextVersion() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get window => $_getSZ(1);
  @$pb.TagNumber(2)
  set window($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasWindow() => $_has(1);
  @$pb.TagNumber(2)
  void clearWindow() => clearField(2);

  @$pb.TagNumber(3)
  FocusMetrics get focus => $_getN(2);
  @$pb.TagNumber(3)
  set focus(FocusMetrics v) { setField(3, v); }
  @$pb.TagNumber(3)
  $core.bool hasFocus() => $_has(2);
  @$pb.TagNumber(3)
  void clearFocus() => clearField(3);
  @$pb.TagNumber(3)
  FocusMetrics ensureFocus() => $_ensure(2);

  @$pb.TagNumber(4)
  ComprehensionMetrics get comprehension => $_getN(3);
  @$pb.TagNumber(4)
  set comprehension(ComprehensionMetrics v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasComprehension() => $_has(3);
  @$pb.TagNumber(4)
  void clearComprehension() => clearField(4);
  @$pb.TagNumber(4)
  ComprehensionMetrics ensureComprehension() => $_ensure(3);

  @$pb.TagNumber(5)
  TimeContext get time => $_getN(4);
  @$pb.TagNumber(5)
  set time(TimeContext v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasTime() => $_has(4);
  @$pb.TagNumber(5)
  void clearTime() => clearField(5);
  @$pb.TagNumber(5)
  TimeContext ensureTime() => $_ensure(4);

  @$pb.TagNumber(6)
  ContentContext get content => $_getN(5);
  @$pb.TagNumber(6)
  set content(ContentContext v) { setField(6, v); }
  @$pb.TagNumber(6)
  $core.bool hasContent() => $_has(5);
  @$pb.TagNumber(6)
  void clearContent() => clearField(6);
  @$pb.TagNumber(6)
  ContentContext ensureContent() => $_ensure(5);

  @$pb.TagNumber(7)
  $core.bool get piiScrubbed => $_getBF(6);
  @$pb.TagNumber(7)
  set piiScrubbed($core.bool v) { $_setBool(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasPiiScrubbed() => $_has(6);
  @$pb.TagNumber(7)
  void clearPiiScrubbed() => clearField(7);
}

class FocusMetrics extends $pb.GeneratedMessage {
  factory FocusMetrics({
    $core.int? plannedMin,
    $core.int? actualMin,
    $core.int? interruptions,
    $core.double? completion,
  }) {
    final $result = create();
    if (plannedMin != null) {
      $result.plannedMin = plannedMin;
    }
    if (actualMin != null) {
      $result.actualMin = actualMin;
    }
    if (interruptions != null) {
      $result.interruptions = interruptions;
    }
    if (completion != null) {
      $result.completion = completion;
    }
    return $result;
  }
  FocusMetrics._() : super();
  factory FocusMetrics.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory FocusMetrics.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'FocusMetrics', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'plannedMin', $pb.PbFieldType.O3)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'actualMin', $pb.PbFieldType.O3)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'interruptions', $pb.PbFieldType.O3)
    ..a<$core.double>(4, _omitFieldNames ? '' : 'completion', $pb.PbFieldType.OF)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  FocusMetrics clone() => FocusMetrics()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  FocusMetrics copyWith(void Function(FocusMetrics) updates) => super.copyWith((message) => updates(message as FocusMetrics)) as FocusMetrics;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FocusMetrics create() => FocusMetrics._();
  FocusMetrics createEmptyInstance() => create();
  static $pb.PbList<FocusMetrics> createRepeated() => $pb.PbList<FocusMetrics>();
  @$core.pragma('dart2js:noInline')
  static FocusMetrics getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<FocusMetrics>(create);
  static FocusMetrics? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get plannedMin => $_getIZ(0);
  @$pb.TagNumber(1)
  set plannedMin($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasPlannedMin() => $_has(0);
  @$pb.TagNumber(1)
  void clearPlannedMin() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get actualMin => $_getIZ(1);
  @$pb.TagNumber(2)
  set actualMin($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasActualMin() => $_has(1);
  @$pb.TagNumber(2)
  void clearActualMin() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get interruptions => $_getIZ(2);
  @$pb.TagNumber(3)
  set interruptions($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasInterruptions() => $_has(2);
  @$pb.TagNumber(3)
  void clearInterruptions() => clearField(3);

  @$pb.TagNumber(4)
  $core.double get completion => $_getN(3);
  @$pb.TagNumber(4)
  set completion($core.double v) { $_setFloat(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasCompletion() => $_has(3);
  @$pb.TagNumber(4)
  void clearCompletion() => clearField(4);
}

class ComprehensionMetrics extends $pb.GeneratedMessage {
  factory ComprehensionMetrics({
    $core.int? translationRequests,
    $core.String? translationGranularity,
    $core.int? unknownTermsSaved,
  }) {
    final $result = create();
    if (translationRequests != null) {
      $result.translationRequests = translationRequests;
    }
    if (translationGranularity != null) {
      $result.translationGranularity = translationGranularity;
    }
    if (unknownTermsSaved != null) {
      $result.unknownTermsSaved = unknownTermsSaved;
    }
    return $result;
  }
  ComprehensionMetrics._() : super();
  factory ComprehensionMetrics.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ComprehensionMetrics.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ComprehensionMetrics', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'translationRequests', $pb.PbFieldType.O3)
    ..aOS(2, _omitFieldNames ? '' : 'translationGranularity')
    ..a<$core.int>(3, _omitFieldNames ? '' : 'unknownTermsSaved', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ComprehensionMetrics clone() => ComprehensionMetrics()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ComprehensionMetrics copyWith(void Function(ComprehensionMetrics) updates) => super.copyWith((message) => updates(message as ComprehensionMetrics)) as ComprehensionMetrics;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ComprehensionMetrics create() => ComprehensionMetrics._();
  ComprehensionMetrics createEmptyInstance() => create();
  static $pb.PbList<ComprehensionMetrics> createRepeated() => $pb.PbList<ComprehensionMetrics>();
  @$core.pragma('dart2js:noInline')
  static ComprehensionMetrics getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ComprehensionMetrics>(create);
  static ComprehensionMetrics? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get translationRequests => $_getIZ(0);
  @$pb.TagNumber(1)
  set translationRequests($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasTranslationRequests() => $_has(0);
  @$pb.TagNumber(1)
  void clearTranslationRequests() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get translationGranularity => $_getSZ(1);
  @$pb.TagNumber(2)
  set translationGranularity($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTranslationGranularity() => $_has(1);
  @$pb.TagNumber(2)
  void clearTranslationGranularity() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get unknownTermsSaved => $_getIZ(2);
  @$pb.TagNumber(3)
  set unknownTermsSaved($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasUnknownTermsSaved() => $_has(2);
  @$pb.TagNumber(3)
  void clearUnknownTermsSaved() => clearField(3);
}

class TimeContext extends $pb.GeneratedMessage {
  factory TimeContext({
    $core.int? localHour,
    $core.String? dayOfWeek,
  }) {
    final $result = create();
    if (localHour != null) {
      $result.localHour = localHour;
    }
    if (dayOfWeek != null) {
      $result.dayOfWeek = dayOfWeek;
    }
    return $result;
  }
  TimeContext._() : super();
  factory TimeContext.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TimeContext.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TimeContext', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'localHour', $pb.PbFieldType.O3)
    ..aOS(2, _omitFieldNames ? '' : 'dayOfWeek')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TimeContext clone() => TimeContext()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TimeContext copyWith(void Function(TimeContext) updates) => super.copyWith((message) => updates(message as TimeContext)) as TimeContext;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TimeContext create() => TimeContext._();
  TimeContext createEmptyInstance() => create();
  static $pb.PbList<TimeContext> createRepeated() => $pb.PbList<TimeContext>();
  @$core.pragma('dart2js:noInline')
  static TimeContext getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TimeContext>(create);
  static TimeContext? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get localHour => $_getIZ(0);
  @$pb.TagNumber(1)
  set localHour($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasLocalHour() => $_has(0);
  @$pb.TagNumber(1)
  void clearLocalHour() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get dayOfWeek => $_getSZ(1);
  @$pb.TagNumber(2)
  set dayOfWeek($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDayOfWeek() => $_has(1);
  @$pb.TagNumber(2)
  void clearDayOfWeek() => clearField(2);
}

class ContentContext extends $pb.GeneratedMessage {
  factory ContentContext({
    $core.String? language,
    $core.String? domain,
  }) {
    final $result = create();
    if (language != null) {
      $result.language = language;
    }
    if (domain != null) {
      $result.domain = domain;
    }
    return $result;
  }
  ContentContext._() : super();
  factory ContentContext.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ContentContext.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ContentContext', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'language')
    ..aOS(2, _omitFieldNames ? '' : 'domain')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ContentContext clone() => ContentContext()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ContentContext copyWith(void Function(ContentContext) updates) => super.copyWith((message) => updates(message as ContentContext)) as ContentContext;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContentContext create() => ContentContext._();
  ContentContext createEmptyInstance() => create();
  static $pb.PbList<ContentContext> createRepeated() => $pb.PbList<ContentContext>();
  @$core.pragma('dart2js:noInline')
  static ContentContext getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ContentContext>(create);
  static ContentContext? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get language => $_getSZ(0);
  @$pb.TagNumber(1)
  set language($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasLanguage() => $_has(0);
  @$pb.TagNumber(1)
  void clearLanguage() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get domain => $_getSZ(1);
  @$pb.TagNumber(2)
  set domain($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDomain() => $_has(1);
  @$pb.TagNumber(2)
  void clearDomain() => clearField(2);
}

/// Feature extraction output (objective)
class FeatureExtractResult extends $pb.GeneratedMessage {
  factory FeatureExtractResult({
    $core.String? version,
    LearningRhythm? rhythm,
    UnderstandingFriction? friction,
    EnergyState? energy,
    TaskRisk? risk,
  }) {
    final $result = create();
    if (version != null) {
      $result.version = version;
    }
    if (rhythm != null) {
      $result.rhythm = rhythm;
    }
    if (friction != null) {
      $result.friction = friction;
    }
    if (energy != null) {
      $result.energy = energy;
    }
    if (risk != null) {
      $result.risk = risk;
    }
    return $result;
  }
  FeatureExtractResult._() : super();
  factory FeatureExtractResult.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory FeatureExtractResult.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'FeatureExtractResult', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..aOM<LearningRhythm>(2, _omitFieldNames ? '' : 'rhythm', subBuilder: LearningRhythm.create)
    ..aOM<UnderstandingFriction>(3, _omitFieldNames ? '' : 'friction', subBuilder: UnderstandingFriction.create)
    ..aOM<EnergyState>(4, _omitFieldNames ? '' : 'energy', subBuilder: EnergyState.create)
    ..aOM<TaskRisk>(5, _omitFieldNames ? '' : 'risk', subBuilder: TaskRisk.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  FeatureExtractResult clone() => FeatureExtractResult()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  FeatureExtractResult copyWith(void Function(FeatureExtractResult) updates) => super.copyWith((message) => updates(message as FeatureExtractResult)) as FeatureExtractResult;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FeatureExtractResult create() => FeatureExtractResult._();
  FeatureExtractResult createEmptyInstance() => create();
  static $pb.PbList<FeatureExtractResult> createRepeated() => $pb.PbList<FeatureExtractResult>();
  @$core.pragma('dart2js:noInline')
  static FeatureExtractResult getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<FeatureExtractResult>(create);
  static FeatureExtractResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => clearField(1);

  @$pb.TagNumber(2)
  LearningRhythm get rhythm => $_getN(1);
  @$pb.TagNumber(2)
  set rhythm(LearningRhythm v) { setField(2, v); }
  @$pb.TagNumber(2)
  $core.bool hasRhythm() => $_has(1);
  @$pb.TagNumber(2)
  void clearRhythm() => clearField(2);
  @$pb.TagNumber(2)
  LearningRhythm ensureRhythm() => $_ensure(1);

  @$pb.TagNumber(3)
  UnderstandingFriction get friction => $_getN(2);
  @$pb.TagNumber(3)
  set friction(UnderstandingFriction v) { setField(3, v); }
  @$pb.TagNumber(3)
  $core.bool hasFriction() => $_has(2);
  @$pb.TagNumber(3)
  void clearFriction() => clearField(3);
  @$pb.TagNumber(3)
  UnderstandingFriction ensureFriction() => $_ensure(2);

  @$pb.TagNumber(4)
  EnergyState get energy => $_getN(3);
  @$pb.TagNumber(4)
  set energy(EnergyState v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasEnergy() => $_has(3);
  @$pb.TagNumber(4)
  void clearEnergy() => clearField(4);
  @$pb.TagNumber(4)
  EnergyState ensureEnergy() => $_ensure(3);

  @$pb.TagNumber(5)
  TaskRisk get risk => $_getN(4);
  @$pb.TagNumber(5)
  set risk(TaskRisk v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasRisk() => $_has(4);
  @$pb.TagNumber(5)
  void clearRisk() => clearField(5);
  @$pb.TagNumber(5)
  TaskRisk ensureRisk() => $_ensure(4);
}

class LearningRhythm extends $pb.GeneratedMessage {
  factory LearningRhythm({
    $core.bool? deviatingFromPlan,
    $core.int? interruptionFrequency,
  }) {
    final $result = create();
    if (deviatingFromPlan != null) {
      $result.deviatingFromPlan = deviatingFromPlan;
    }
    if (interruptionFrequency != null) {
      $result.interruptionFrequency = interruptionFrequency;
    }
    return $result;
  }
  LearningRhythm._() : super();
  factory LearningRhythm.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory LearningRhythm.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'LearningRhythm', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'deviatingFromPlan')
    ..a<$core.int>(2, _omitFieldNames ? '' : 'interruptionFrequency', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  LearningRhythm clone() => LearningRhythm()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  LearningRhythm copyWith(void Function(LearningRhythm) updates) => super.copyWith((message) => updates(message as LearningRhythm)) as LearningRhythm;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static LearningRhythm create() => LearningRhythm._();
  LearningRhythm createEmptyInstance() => create();
  static $pb.PbList<LearningRhythm> createRepeated() => $pb.PbList<LearningRhythm>();
  @$core.pragma('dart2js:noInline')
  static LearningRhythm getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<LearningRhythm>(create);
  static LearningRhythm? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get deviatingFromPlan => $_getBF(0);
  @$pb.TagNumber(1)
  set deviatingFromPlan($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasDeviatingFromPlan() => $_has(0);
  @$pb.TagNumber(1)
  void clearDeviatingFromPlan() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get interruptionFrequency => $_getIZ(1);
  @$pb.TagNumber(2)
  set interruptionFrequency($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasInterruptionFrequency() => $_has(1);
  @$pb.TagNumber(2)
  void clearInterruptionFrequency() => clearField(2);
}

class UnderstandingFriction extends $pb.GeneratedMessage {
  factory UnderstandingFriction({
    $core.int? translationDensity,
    $core.bool? escalatingGranularity,
  }) {
    final $result = create();
    if (translationDensity != null) {
      $result.translationDensity = translationDensity;
    }
    if (escalatingGranularity != null) {
      $result.escalatingGranularity = escalatingGranularity;
    }
    return $result;
  }
  UnderstandingFriction._() : super();
  factory UnderstandingFriction.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory UnderstandingFriction.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'UnderstandingFriction', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'translationDensity', $pb.PbFieldType.O3)
    ..aOB(2, _omitFieldNames ? '' : 'escalatingGranularity')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  UnderstandingFriction clone() => UnderstandingFriction()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  UnderstandingFriction copyWith(void Function(UnderstandingFriction) updates) => super.copyWith((message) => updates(message as UnderstandingFriction)) as UnderstandingFriction;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UnderstandingFriction create() => UnderstandingFriction._();
  UnderstandingFriction createEmptyInstance() => create();
  static $pb.PbList<UnderstandingFriction> createRepeated() => $pb.PbList<UnderstandingFriction>();
  @$core.pragma('dart2js:noInline')
  static UnderstandingFriction getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UnderstandingFriction>(create);
  static UnderstandingFriction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get translationDensity => $_getIZ(0);
  @$pb.TagNumber(1)
  set translationDensity($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasTranslationDensity() => $_has(0);
  @$pb.TagNumber(1)
  void clearTranslationDensity() => clearField(1);

  @$pb.TagNumber(2)
  $core.bool get escalatingGranularity => $_getBF(1);
  @$pb.TagNumber(2)
  set escalatingGranularity($core.bool v) { $_setBool(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasEscalatingGranularity() => $_has(1);
  @$pb.TagNumber(2)
  void clearEscalatingGranularity() => clearField(2);
}

class EnergyState extends $pb.GeneratedMessage {
  factory EnergyState({
    $core.bool? lateNightFatigue,
    $core.bool? shortSessionTrend,
  }) {
    final $result = create();
    if (lateNightFatigue != null) {
      $result.lateNightFatigue = lateNightFatigue;
    }
    if (shortSessionTrend != null) {
      $result.shortSessionTrend = shortSessionTrend;
    }
    return $result;
  }
  EnergyState._() : super();
  factory EnergyState.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory EnergyState.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'EnergyState', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'lateNightFatigue')
    ..aOB(2, _omitFieldNames ? '' : 'shortSessionTrend')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  EnergyState clone() => EnergyState()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  EnergyState copyWith(void Function(EnergyState) updates) => super.copyWith((message) => updates(message as EnergyState)) as EnergyState;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EnergyState create() => EnergyState._();
  EnergyState createEmptyInstance() => create();
  static $pb.PbList<EnergyState> createRepeated() => $pb.PbList<EnergyState>();
  @$core.pragma('dart2js:noInline')
  static EnergyState getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<EnergyState>(create);
  static EnergyState? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get lateNightFatigue => $_getBF(0);
  @$pb.TagNumber(1)
  set lateNightFatigue($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasLateNightFatigue() => $_has(0);
  @$pb.TagNumber(1)
  void clearLateNightFatigue() => clearField(1);

  @$pb.TagNumber(2)
  $core.bool get shortSessionTrend => $_getBF(1);
  @$pb.TagNumber(2)
  set shortSessionTrend($core.bool v) { $_setBool(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasShortSessionTrend() => $_has(1);
  @$pb.TagNumber(2)
  void clearShortSessionTrend() => clearField(2);
}

class TaskRisk extends $pb.GeneratedMessage {
  factory TaskRisk({
    $core.bool? consecutiveFailures,
    $core.bool? procrastinationDetected,
  }) {
    final $result = create();
    if (consecutiveFailures != null) {
      $result.consecutiveFailures = consecutiveFailures;
    }
    if (procrastinationDetected != null) {
      $result.procrastinationDetected = procrastinationDetected;
    }
    return $result;
  }
  TaskRisk._() : super();
  factory TaskRisk.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TaskRisk.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TaskRisk', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'consecutiveFailures')
    ..aOB(2, _omitFieldNames ? '' : 'procrastinationDetected')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TaskRisk clone() => TaskRisk()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TaskRisk copyWith(void Function(TaskRisk) updates) => super.copyWith((message) => updates(message as TaskRisk)) as TaskRisk;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TaskRisk create() => TaskRisk._();
  TaskRisk createEmptyInstance() => create();
  static $pb.PbList<TaskRisk> createRepeated() => $pb.PbList<TaskRisk>();
  @$core.pragma('dart2js:noInline')
  static TaskRisk getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TaskRisk>(create);
  static TaskRisk? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get consecutiveFailures => $_getBF(0);
  @$pb.TagNumber(1)
  set consecutiveFailures($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasConsecutiveFailures() => $_has(0);
  @$pb.TagNumber(1)
  void clearConsecutiveFailures() => clearField(1);

  @$pb.TagNumber(2)
  $core.bool get procrastinationDetected => $_getBF(1);
  @$pb.TagNumber(2)
  set procrastinationDetected($core.bool v) { $_setBool(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasProcrastinationDetected() => $_has(1);
  @$pb.TagNumber(2)
  void clearProcrastinationDetected() => clearField(2);
}

/// Signal generation (decision-ready)
class Signals extends $pb.GeneratedMessage {
  factory Signals({
    $core.String? version,
    $core.Iterable<Signal>? signals,
  }) {
    final $result = create();
    if (version != null) {
      $result.version = version;
    }
    if (signals != null) {
      $result.signals.addAll(signals);
    }
    return $result;
  }
  Signals._() : super();
  factory Signals.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Signals.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Signals', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..pc<Signal>(2, _omitFieldNames ? '' : 'signals', $pb.PbFieldType.PM, subBuilder: Signal.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Signals clone() => Signals()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Signals copyWith(void Function(Signals) updates) => super.copyWith((message) => updates(message as Signals)) as Signals;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Signals create() => Signals._();
  Signals createEmptyInstance() => create();
  static $pb.PbList<Signals> createRepeated() => $pb.PbList<Signals>();
  @$core.pragma('dart2js:noInline')
  static Signals getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Signals>(create);
  static Signals? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => clearField(1);

  @$pb.TagNumber(2)
  $core.List<Signal> get signals => $_getList(1);
}

class Signal extends $pb.GeneratedMessage {
  factory Signal({
    $core.String? type,
    $core.double? confidence,
    $core.String? reason,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (type != null) {
      $result.type = type;
    }
    if (confidence != null) {
      $result.confidence = confidence;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  Signal._() : super();
  factory Signal.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Signal.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Signal', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'type')
    ..a<$core.double>(2, _omitFieldNames ? '' : 'confidence', $pb.PbFieldType.OF)
    ..aOS(3, _omitFieldNames ? '' : 'reason')
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'metadata', entryClassName: 'Signal.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Signal clone() => Signal()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Signal copyWith(void Function(Signal) updates) => super.copyWith((message) => updates(message as Signal)) as Signal;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Signal create() => Signal._();
  Signal createEmptyInstance() => create();
  static $pb.PbList<Signal> createRepeated() => $pb.PbList<Signal>();
  @$core.pragma('dart2js:noInline')
  static Signal getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Signal>(create);
  static Signal? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get type => $_getSZ(0);
  @$pb.TagNumber(1)
  set type($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => clearField(1);

  @$pb.TagNumber(2)
  $core.double get confidence => $_getN(1);
  @$pb.TagNumber(2)
  set confidence($core.double v) { $_setFloat(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasConfidence() => $_has(1);
  @$pb.TagNumber(2)
  void clearConfidence() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get reason => $_getSZ(2);
  @$pb.TagNumber(3)
  set reason($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasReason() => $_has(2);
  @$pb.TagNumber(3)
  void clearReason() => clearField(3);

  @$pb.TagNumber(4)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(3);
}

/// Enhanced candidate action (v2)
class CandidateActionV2 extends $pb.GeneratedMessage {
  factory CandidateActionV2({
    $core.String? id,
    $core.String? actionType,
    $core.String? title,
    $core.String? reason,
    $core.double? confidence,
    $core.String? timingHint,
    $core.String? payloadSeed,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (actionType != null) {
      $result.actionType = actionType;
    }
    if (title != null) {
      $result.title = title;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (confidence != null) {
      $result.confidence = confidence;
    }
    if (timingHint != null) {
      $result.timingHint = timingHint;
    }
    if (payloadSeed != null) {
      $result.payloadSeed = payloadSeed;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  CandidateActionV2._() : super();
  factory CandidateActionV2.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory CandidateActionV2.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'CandidateActionV2', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'actionType')
    ..aOS(3, _omitFieldNames ? '' : 'title')
    ..aOS(4, _omitFieldNames ? '' : 'reason')
    ..a<$core.double>(5, _omitFieldNames ? '' : 'confidence', $pb.PbFieldType.OF)
    ..aOS(6, _omitFieldNames ? '' : 'timingHint')
    ..aOS(7, _omitFieldNames ? '' : 'payloadSeed')
    ..m<$core.String, $core.String>(8, _omitFieldNames ? '' : 'metadata', entryClassName: 'CandidateActionV2.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  CandidateActionV2 clone() => CandidateActionV2()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  CandidateActionV2 copyWith(void Function(CandidateActionV2) updates) => super.copyWith((message) => updates(message as CandidateActionV2)) as CandidateActionV2;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CandidateActionV2 create() => CandidateActionV2._();
  CandidateActionV2 createEmptyInstance() => create();
  static $pb.PbList<CandidateActionV2> createRepeated() => $pb.PbList<CandidateActionV2>();
  @$core.pragma('dart2js:noInline')
  static CandidateActionV2 getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CandidateActionV2>(create);
  static CandidateActionV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get actionType => $_getSZ(1);
  @$pb.TagNumber(2)
  set actionType($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasActionType() => $_has(1);
  @$pb.TagNumber(2)
  void clearActionType() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get title => $_getSZ(2);
  @$pb.TagNumber(3)
  set title($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTitle() => $_has(2);
  @$pb.TagNumber(3)
  void clearTitle() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get reason => $_getSZ(3);
  @$pb.TagNumber(4)
  set reason($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasReason() => $_has(3);
  @$pb.TagNumber(4)
  void clearReason() => clearField(4);

  @$pb.TagNumber(5)
  $core.double get confidence => $_getN(4);
  @$pb.TagNumber(5)
  set confidence($core.double v) { $_setFloat(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasConfidence() => $_has(4);
  @$pb.TagNumber(5)
  void clearConfidence() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get timingHint => $_getSZ(5);
  @$pb.TagNumber(6)
  set timingHint($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasTimingHint() => $_has(5);
  @$pb.TagNumber(6)
  void clearTimingHint() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get payloadSeed => $_getSZ(6);
  @$pb.TagNumber(7)
  set payloadSeed($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasPayloadSeed() => $_has(6);
  @$pb.TagNumber(7)
  void clearPayloadSeed() => clearField(7);

  @$pb.TagNumber(8)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(7);
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
