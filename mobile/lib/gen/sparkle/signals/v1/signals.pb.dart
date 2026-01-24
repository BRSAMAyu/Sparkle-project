// This is a generated file - do not edit.
//
// Generated from sparkle/signals/v1/signals.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

class CandidateAction extends $pb.GeneratedMessage {
  factory CandidateAction({
    $core.String? id,
    $core.String? type,
    $core.String? trigger,
    $core.String? contentSeed,
    $core.double? priority,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (type != null) result.type = type;
    if (trigger != null) result.trigger = trigger;
    if (contentSeed != null) result.contentSeed = contentSeed;
    if (priority != null) result.priority = priority;
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  CandidateAction._();

  factory CandidateAction.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CandidateAction.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CandidateAction',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..aOS(3, _omitFieldNames ? '' : 'trigger')
    ..aOS(4, _omitFieldNames ? '' : 'contentSeed')
    ..aD(5, _omitFieldNames ? '' : 'priority', fieldType: $pb.PbFieldType.OF)
    ..m<$core.String, $core.String>(6, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'CandidateAction.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CandidateAction clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CandidateAction copyWith(void Function(CandidateAction) updates) =>
      super.copyWith((message) => updates(message as CandidateAction))
          as CandidateAction;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CandidateAction create() => CandidateAction._();
  @$core.override
  CandidateAction createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CandidateAction getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CandidateAction>(create);
  static CandidateAction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get trigger => $_getSZ(2);
  @$pb.TagNumber(3)
  set trigger($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTrigger() => $_has(2);
  @$pb.TagNumber(3)
  void clearTrigger() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get contentSeed => $_getSZ(3);
  @$pb.TagNumber(4)
  set contentSeed($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasContentSeed() => $_has(3);
  @$pb.TagNumber(4)
  void clearContentSeed() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.double get priority => $_getN(4);
  @$pb.TagNumber(5)
  set priority($core.double value) => $_setFloat(4, value);
  @$pb.TagNumber(5)
  $core.bool hasPriority() => $_has(4);
  @$pb.TagNumber(5)
  void clearPriority() => $_clearField(5);

  @$pb.TagNumber(6)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(5);
}

class NextActionsCandidateSet extends $pb.GeneratedMessage {
  factory NextActionsCandidateSet({
    $core.String? requestId,
    $core.String? traceId,
    $core.String? userId,
    $core.String? schemaVersion,
    $core.String? idempotencyKey,
    $core.Iterable<CandidateAction>? candidates,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (traceId != null) result.traceId = traceId;
    if (userId != null) result.userId = userId;
    if (schemaVersion != null) result.schemaVersion = schemaVersion;
    if (idempotencyKey != null) result.idempotencyKey = idempotencyKey;
    if (candidates != null) result.candidates.addAll(candidates);
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  NextActionsCandidateSet._();

  factory NextActionsCandidateSet.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory NextActionsCandidateSet.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'NextActionsCandidateSet',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..aOS(4, _omitFieldNames ? '' : 'schemaVersion')
    ..aOS(5, _omitFieldNames ? '' : 'idempotencyKey')
    ..pPM<CandidateAction>(6, _omitFieldNames ? '' : 'candidates',
        subBuilder: CandidateAction.create)
    ..m<$core.String, $core.String>(7, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'NextActionsCandidateSet.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NextActionsCandidateSet clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  NextActionsCandidateSet copyWith(
          void Function(NextActionsCandidateSet) updates) =>
      super.copyWith((message) => updates(message as NextActionsCandidateSet))
          as NextActionsCandidateSet;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static NextActionsCandidateSet create() => NextActionsCandidateSet._();
  @$core.override
  NextActionsCandidateSet createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static NextActionsCandidateSet getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<NextActionsCandidateSet>(create);
  static NextActionsCandidateSet? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get requestId => $_getSZ(0);
  @$pb.TagNumber(1)
  set requestId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRequestId() => $_has(0);
  @$pb.TagNumber(1)
  void clearRequestId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get traceId => $_getSZ(1);
  @$pb.TagNumber(2)
  set traceId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTraceId() => $_has(1);
  @$pb.TagNumber(2)
  void clearTraceId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get schemaVersion => $_getSZ(3);
  @$pb.TagNumber(4)
  set schemaVersion($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSchemaVersion() => $_has(3);
  @$pb.TagNumber(4)
  void clearSchemaVersion() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get idempotencyKey => $_getSZ(4);
  @$pb.TagNumber(5)
  set idempotencyKey($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasIdempotencyKey() => $_has(4);
  @$pb.TagNumber(5)
  void clearIdempotencyKey() => $_clearField(5);

  @$pb.TagNumber(6)
  $pb.PbList<CandidateAction> get candidates => $_getList(5);

  @$pb.TagNumber(7)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(6);
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
    final result = create();
    if (contextVersion != null) result.contextVersion = contextVersion;
    if (window != null) result.window = window;
    if (focus != null) result.focus = focus;
    if (comprehension != null) result.comprehension = comprehension;
    if (time != null) result.time = time;
    if (content != null) result.content = content;
    if (piiScrubbed != null) result.piiScrubbed = piiScrubbed;
    return result;
  }

  ContextEnvelope._();

  factory ContextEnvelope.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ContextEnvelope.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ContextEnvelope',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'contextVersion')
    ..aOS(2, _omitFieldNames ? '' : 'window')
    ..aOM<FocusMetrics>(3, _omitFieldNames ? '' : 'focus',
        subBuilder: FocusMetrics.create)
    ..aOM<ComprehensionMetrics>(4, _omitFieldNames ? '' : 'comprehension',
        subBuilder: ComprehensionMetrics.create)
    ..aOM<TimeContext>(5, _omitFieldNames ? '' : 'time',
        subBuilder: TimeContext.create)
    ..aOM<ContentContext>(6, _omitFieldNames ? '' : 'content',
        subBuilder: ContentContext.create)
    ..aOB(7, _omitFieldNames ? '' : 'piiScrubbed')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ContextEnvelope clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ContextEnvelope copyWith(void Function(ContextEnvelope) updates) =>
      super.copyWith((message) => updates(message as ContextEnvelope))
          as ContextEnvelope;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContextEnvelope create() => ContextEnvelope._();
  @$core.override
  ContextEnvelope createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ContextEnvelope getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ContextEnvelope>(create);
  static ContextEnvelope? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get contextVersion => $_getSZ(0);
  @$pb.TagNumber(1)
  set contextVersion($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasContextVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearContextVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get window => $_getSZ(1);
  @$pb.TagNumber(2)
  set window($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasWindow() => $_has(1);
  @$pb.TagNumber(2)
  void clearWindow() => $_clearField(2);

  @$pb.TagNumber(3)
  FocusMetrics get focus => $_getN(2);
  @$pb.TagNumber(3)
  set focus(FocusMetrics value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasFocus() => $_has(2);
  @$pb.TagNumber(3)
  void clearFocus() => $_clearField(3);
  @$pb.TagNumber(3)
  FocusMetrics ensureFocus() => $_ensure(2);

  @$pb.TagNumber(4)
  ComprehensionMetrics get comprehension => $_getN(3);
  @$pb.TagNumber(4)
  set comprehension(ComprehensionMetrics value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasComprehension() => $_has(3);
  @$pb.TagNumber(4)
  void clearComprehension() => $_clearField(4);
  @$pb.TagNumber(4)
  ComprehensionMetrics ensureComprehension() => $_ensure(3);

  @$pb.TagNumber(5)
  TimeContext get time => $_getN(4);
  @$pb.TagNumber(5)
  set time(TimeContext value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasTime() => $_has(4);
  @$pb.TagNumber(5)
  void clearTime() => $_clearField(5);
  @$pb.TagNumber(5)
  TimeContext ensureTime() => $_ensure(4);

  @$pb.TagNumber(6)
  ContentContext get content => $_getN(5);
  @$pb.TagNumber(6)
  set content(ContentContext value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasContent() => $_has(5);
  @$pb.TagNumber(6)
  void clearContent() => $_clearField(6);
  @$pb.TagNumber(6)
  ContentContext ensureContent() => $_ensure(5);

  @$pb.TagNumber(7)
  $core.bool get piiScrubbed => $_getBF(6);
  @$pb.TagNumber(7)
  set piiScrubbed($core.bool value) => $_setBool(6, value);
  @$pb.TagNumber(7)
  $core.bool hasPiiScrubbed() => $_has(6);
  @$pb.TagNumber(7)
  void clearPiiScrubbed() => $_clearField(7);
}

class FocusMetrics extends $pb.GeneratedMessage {
  factory FocusMetrics({
    $core.int? plannedMin,
    $core.int? actualMin,
    $core.int? interruptions,
    $core.double? completion,
  }) {
    final result = create();
    if (plannedMin != null) result.plannedMin = plannedMin;
    if (actualMin != null) result.actualMin = actualMin;
    if (interruptions != null) result.interruptions = interruptions;
    if (completion != null) result.completion = completion;
    return result;
  }

  FocusMetrics._();

  factory FocusMetrics.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory FocusMetrics.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'FocusMetrics',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'plannedMin')
    ..aI(2, _omitFieldNames ? '' : 'actualMin')
    ..aI(3, _omitFieldNames ? '' : 'interruptions')
    ..aD(4, _omitFieldNames ? '' : 'completion', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FocusMetrics clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FocusMetrics copyWith(void Function(FocusMetrics) updates) =>
      super.copyWith((message) => updates(message as FocusMetrics))
          as FocusMetrics;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FocusMetrics create() => FocusMetrics._();
  @$core.override
  FocusMetrics createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static FocusMetrics getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<FocusMetrics>(create);
  static FocusMetrics? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get plannedMin => $_getIZ(0);
  @$pb.TagNumber(1)
  set plannedMin($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPlannedMin() => $_has(0);
  @$pb.TagNumber(1)
  void clearPlannedMin() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get actualMin => $_getIZ(1);
  @$pb.TagNumber(2)
  set actualMin($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasActualMin() => $_has(1);
  @$pb.TagNumber(2)
  void clearActualMin() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get interruptions => $_getIZ(2);
  @$pb.TagNumber(3)
  set interruptions($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasInterruptions() => $_has(2);
  @$pb.TagNumber(3)
  void clearInterruptions() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.double get completion => $_getN(3);
  @$pb.TagNumber(4)
  set completion($core.double value) => $_setFloat(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCompletion() => $_has(3);
  @$pb.TagNumber(4)
  void clearCompletion() => $_clearField(4);
}

class ComprehensionMetrics extends $pb.GeneratedMessage {
  factory ComprehensionMetrics({
    $core.int? translationRequests,
    $core.String? translationGranularity,
    $core.int? unknownTermsSaved,
  }) {
    final result = create();
    if (translationRequests != null)
      result.translationRequests = translationRequests;
    if (translationGranularity != null)
      result.translationGranularity = translationGranularity;
    if (unknownTermsSaved != null) result.unknownTermsSaved = unknownTermsSaved;
    return result;
  }

  ComprehensionMetrics._();

  factory ComprehensionMetrics.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ComprehensionMetrics.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ComprehensionMetrics',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'translationRequests')
    ..aOS(2, _omitFieldNames ? '' : 'translationGranularity')
    ..aI(3, _omitFieldNames ? '' : 'unknownTermsSaved')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ComprehensionMetrics clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ComprehensionMetrics copyWith(void Function(ComprehensionMetrics) updates) =>
      super.copyWith((message) => updates(message as ComprehensionMetrics))
          as ComprehensionMetrics;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ComprehensionMetrics create() => ComprehensionMetrics._();
  @$core.override
  ComprehensionMetrics createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ComprehensionMetrics getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ComprehensionMetrics>(create);
  static ComprehensionMetrics? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get translationRequests => $_getIZ(0);
  @$pb.TagNumber(1)
  set translationRequests($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTranslationRequests() => $_has(0);
  @$pb.TagNumber(1)
  void clearTranslationRequests() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get translationGranularity => $_getSZ(1);
  @$pb.TagNumber(2)
  set translationGranularity($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTranslationGranularity() => $_has(1);
  @$pb.TagNumber(2)
  void clearTranslationGranularity() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get unknownTermsSaved => $_getIZ(2);
  @$pb.TagNumber(3)
  set unknownTermsSaved($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasUnknownTermsSaved() => $_has(2);
  @$pb.TagNumber(3)
  void clearUnknownTermsSaved() => $_clearField(3);
}

class TimeContext extends $pb.GeneratedMessage {
  factory TimeContext({
    $core.int? localHour,
    $core.String? dayOfWeek,
  }) {
    final result = create();
    if (localHour != null) result.localHour = localHour;
    if (dayOfWeek != null) result.dayOfWeek = dayOfWeek;
    return result;
  }

  TimeContext._();

  factory TimeContext.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TimeContext.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TimeContext',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'localHour')
    ..aOS(2, _omitFieldNames ? '' : 'dayOfWeek')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TimeContext clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TimeContext copyWith(void Function(TimeContext) updates) =>
      super.copyWith((message) => updates(message as TimeContext))
          as TimeContext;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TimeContext create() => TimeContext._();
  @$core.override
  TimeContext createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TimeContext getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TimeContext>(create);
  static TimeContext? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get localHour => $_getIZ(0);
  @$pb.TagNumber(1)
  set localHour($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasLocalHour() => $_has(0);
  @$pb.TagNumber(1)
  void clearLocalHour() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get dayOfWeek => $_getSZ(1);
  @$pb.TagNumber(2)
  set dayOfWeek($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDayOfWeek() => $_has(1);
  @$pb.TagNumber(2)
  void clearDayOfWeek() => $_clearField(2);
}

class ContentContext extends $pb.GeneratedMessage {
  factory ContentContext({
    $core.String? language,
    $core.String? domain,
  }) {
    final result = create();
    if (language != null) result.language = language;
    if (domain != null) result.domain = domain;
    return result;
  }

  ContentContext._();

  factory ContentContext.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ContentContext.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ContentContext',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'language')
    ..aOS(2, _omitFieldNames ? '' : 'domain')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ContentContext clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ContentContext copyWith(void Function(ContentContext) updates) =>
      super.copyWith((message) => updates(message as ContentContext))
          as ContentContext;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContentContext create() => ContentContext._();
  @$core.override
  ContentContext createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ContentContext getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ContentContext>(create);
  static ContentContext? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get language => $_getSZ(0);
  @$pb.TagNumber(1)
  set language($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasLanguage() => $_has(0);
  @$pb.TagNumber(1)
  void clearLanguage() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get domain => $_getSZ(1);
  @$pb.TagNumber(2)
  set domain($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDomain() => $_has(1);
  @$pb.TagNumber(2)
  void clearDomain() => $_clearField(2);
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
    final result = create();
    if (version != null) result.version = version;
    if (rhythm != null) result.rhythm = rhythm;
    if (friction != null) result.friction = friction;
    if (energy != null) result.energy = energy;
    if (risk != null) result.risk = risk;
    return result;
  }

  FeatureExtractResult._();

  factory FeatureExtractResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory FeatureExtractResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'FeatureExtractResult',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..aOM<LearningRhythm>(2, _omitFieldNames ? '' : 'rhythm',
        subBuilder: LearningRhythm.create)
    ..aOM<UnderstandingFriction>(3, _omitFieldNames ? '' : 'friction',
        subBuilder: UnderstandingFriction.create)
    ..aOM<EnergyState>(4, _omitFieldNames ? '' : 'energy',
        subBuilder: EnergyState.create)
    ..aOM<TaskRisk>(5, _omitFieldNames ? '' : 'risk',
        subBuilder: TaskRisk.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FeatureExtractResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  FeatureExtractResult copyWith(void Function(FeatureExtractResult) updates) =>
      super.copyWith((message) => updates(message as FeatureExtractResult))
          as FeatureExtractResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FeatureExtractResult create() => FeatureExtractResult._();
  @$core.override
  FeatureExtractResult createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static FeatureExtractResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<FeatureExtractResult>(create);
  static FeatureExtractResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  LearningRhythm get rhythm => $_getN(1);
  @$pb.TagNumber(2)
  set rhythm(LearningRhythm value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasRhythm() => $_has(1);
  @$pb.TagNumber(2)
  void clearRhythm() => $_clearField(2);
  @$pb.TagNumber(2)
  LearningRhythm ensureRhythm() => $_ensure(1);

  @$pb.TagNumber(3)
  UnderstandingFriction get friction => $_getN(2);
  @$pb.TagNumber(3)
  set friction(UnderstandingFriction value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasFriction() => $_has(2);
  @$pb.TagNumber(3)
  void clearFriction() => $_clearField(3);
  @$pb.TagNumber(3)
  UnderstandingFriction ensureFriction() => $_ensure(2);

  @$pb.TagNumber(4)
  EnergyState get energy => $_getN(3);
  @$pb.TagNumber(4)
  set energy(EnergyState value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasEnergy() => $_has(3);
  @$pb.TagNumber(4)
  void clearEnergy() => $_clearField(4);
  @$pb.TagNumber(4)
  EnergyState ensureEnergy() => $_ensure(3);

  @$pb.TagNumber(5)
  TaskRisk get risk => $_getN(4);
  @$pb.TagNumber(5)
  set risk(TaskRisk value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasRisk() => $_has(4);
  @$pb.TagNumber(5)
  void clearRisk() => $_clearField(5);
  @$pb.TagNumber(5)
  TaskRisk ensureRisk() => $_ensure(4);
}

class LearningRhythm extends $pb.GeneratedMessage {
  factory LearningRhythm({
    $core.bool? deviatingFromPlan,
    $core.int? interruptionFrequency,
  }) {
    final result = create();
    if (deviatingFromPlan != null) result.deviatingFromPlan = deviatingFromPlan;
    if (interruptionFrequency != null)
      result.interruptionFrequency = interruptionFrequency;
    return result;
  }

  LearningRhythm._();

  factory LearningRhythm.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory LearningRhythm.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'LearningRhythm',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'deviatingFromPlan')
    ..aI(2, _omitFieldNames ? '' : 'interruptionFrequency')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  LearningRhythm clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  LearningRhythm copyWith(void Function(LearningRhythm) updates) =>
      super.copyWith((message) => updates(message as LearningRhythm))
          as LearningRhythm;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static LearningRhythm create() => LearningRhythm._();
  @$core.override
  LearningRhythm createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static LearningRhythm getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<LearningRhythm>(create);
  static LearningRhythm? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get deviatingFromPlan => $_getBF(0);
  @$pb.TagNumber(1)
  set deviatingFromPlan($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasDeviatingFromPlan() => $_has(0);
  @$pb.TagNumber(1)
  void clearDeviatingFromPlan() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get interruptionFrequency => $_getIZ(1);
  @$pb.TagNumber(2)
  set interruptionFrequency($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasInterruptionFrequency() => $_has(1);
  @$pb.TagNumber(2)
  void clearInterruptionFrequency() => $_clearField(2);
}

class UnderstandingFriction extends $pb.GeneratedMessage {
  factory UnderstandingFriction({
    $core.int? translationDensity,
    $core.bool? escalatingGranularity,
  }) {
    final result = create();
    if (translationDensity != null)
      result.translationDensity = translationDensity;
    if (escalatingGranularity != null)
      result.escalatingGranularity = escalatingGranularity;
    return result;
  }

  UnderstandingFriction._();

  factory UnderstandingFriction.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UnderstandingFriction.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UnderstandingFriction',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'translationDensity')
    ..aOB(2, _omitFieldNames ? '' : 'escalatingGranularity')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UnderstandingFriction clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UnderstandingFriction copyWith(
          void Function(UnderstandingFriction) updates) =>
      super.copyWith((message) => updates(message as UnderstandingFriction))
          as UnderstandingFriction;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UnderstandingFriction create() => UnderstandingFriction._();
  @$core.override
  UnderstandingFriction createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UnderstandingFriction getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UnderstandingFriction>(create);
  static UnderstandingFriction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get translationDensity => $_getIZ(0);
  @$pb.TagNumber(1)
  set translationDensity($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTranslationDensity() => $_has(0);
  @$pb.TagNumber(1)
  void clearTranslationDensity() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.bool get escalatingGranularity => $_getBF(1);
  @$pb.TagNumber(2)
  set escalatingGranularity($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasEscalatingGranularity() => $_has(1);
  @$pb.TagNumber(2)
  void clearEscalatingGranularity() => $_clearField(2);
}

class EnergyState extends $pb.GeneratedMessage {
  factory EnergyState({
    $core.bool? lateNightFatigue,
    $core.bool? shortSessionTrend,
  }) {
    final result = create();
    if (lateNightFatigue != null) result.lateNightFatigue = lateNightFatigue;
    if (shortSessionTrend != null) result.shortSessionTrend = shortSessionTrend;
    return result;
  }

  EnergyState._();

  factory EnergyState.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EnergyState.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EnergyState',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'lateNightFatigue')
    ..aOB(2, _omitFieldNames ? '' : 'shortSessionTrend')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnergyState clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnergyState copyWith(void Function(EnergyState) updates) =>
      super.copyWith((message) => updates(message as EnergyState))
          as EnergyState;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EnergyState create() => EnergyState._();
  @$core.override
  EnergyState createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EnergyState getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EnergyState>(create);
  static EnergyState? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get lateNightFatigue => $_getBF(0);
  @$pb.TagNumber(1)
  set lateNightFatigue($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasLateNightFatigue() => $_has(0);
  @$pb.TagNumber(1)
  void clearLateNightFatigue() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.bool get shortSessionTrend => $_getBF(1);
  @$pb.TagNumber(2)
  set shortSessionTrend($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasShortSessionTrend() => $_has(1);
  @$pb.TagNumber(2)
  void clearShortSessionTrend() => $_clearField(2);
}

class TaskRisk extends $pb.GeneratedMessage {
  factory TaskRisk({
    $core.bool? consecutiveFailures,
    $core.bool? procrastinationDetected,
  }) {
    final result = create();
    if (consecutiveFailures != null)
      result.consecutiveFailures = consecutiveFailures;
    if (procrastinationDetected != null)
      result.procrastinationDetected = procrastinationDetected;
    return result;
  }

  TaskRisk._();

  factory TaskRisk.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TaskRisk.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TaskRisk',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'consecutiveFailures')
    ..aOB(2, _omitFieldNames ? '' : 'procrastinationDetected')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TaskRisk clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TaskRisk copyWith(void Function(TaskRisk) updates) =>
      super.copyWith((message) => updates(message as TaskRisk)) as TaskRisk;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TaskRisk create() => TaskRisk._();
  @$core.override
  TaskRisk createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TaskRisk getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TaskRisk>(create);
  static TaskRisk? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get consecutiveFailures => $_getBF(0);
  @$pb.TagNumber(1)
  set consecutiveFailures($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasConsecutiveFailures() => $_has(0);
  @$pb.TagNumber(1)
  void clearConsecutiveFailures() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.bool get procrastinationDetected => $_getBF(1);
  @$pb.TagNumber(2)
  set procrastinationDetected($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasProcrastinationDetected() => $_has(1);
  @$pb.TagNumber(2)
  void clearProcrastinationDetected() => $_clearField(2);
}

/// Signal generation (decision-ready)
class Signals extends $pb.GeneratedMessage {
  factory Signals({
    $core.String? version,
    $core.Iterable<Signal>? signals,
  }) {
    final result = create();
    if (version != null) result.version = version;
    if (signals != null) result.signals.addAll(signals);
    return result;
  }

  Signals._();

  factory Signals.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Signals.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Signals',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..pPM<Signal>(2, _omitFieldNames ? '' : 'signals',
        subBuilder: Signal.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Signals clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Signals copyWith(void Function(Signals) updates) =>
      super.copyWith((message) => updates(message as Signals)) as Signals;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Signals create() => Signals._();
  @$core.override
  Signals createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Signals getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Signals>(create);
  static Signals? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  $pb.PbList<Signal> get signals => $_getList(1);
}

class Signal extends $pb.GeneratedMessage {
  factory Signal({
    $core.String? type,
    $core.double? confidence,
    $core.String? reason,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (type != null) result.type = type;
    if (confidence != null) result.confidence = confidence;
    if (reason != null) result.reason = reason;
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  Signal._();

  factory Signal.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Signal.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Signal',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'type')
    ..aD(2, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..aOS(3, _omitFieldNames ? '' : 'reason')
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'Signal.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Signal clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Signal copyWith(void Function(Signal) updates) =>
      super.copyWith((message) => updates(message as Signal)) as Signal;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Signal create() => Signal._();
  @$core.override
  Signal createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Signal getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Signal>(create);
  static Signal? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get type => $_getSZ(0);
  @$pb.TagNumber(1)
  set type($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.double get confidence => $_getN(1);
  @$pb.TagNumber(2)
  set confidence($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasConfidence() => $_has(1);
  @$pb.TagNumber(2)
  void clearConfidence() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get reason => $_getSZ(2);
  @$pb.TagNumber(3)
  set reason($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasReason() => $_has(2);
  @$pb.TagNumber(3)
  void clearReason() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(3);
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
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (actionType != null) result.actionType = actionType;
    if (title != null) result.title = title;
    if (reason != null) result.reason = reason;
    if (confidence != null) result.confidence = confidence;
    if (timingHint != null) result.timingHint = timingHint;
    if (payloadSeed != null) result.payloadSeed = payloadSeed;
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  CandidateActionV2._();

  factory CandidateActionV2.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CandidateActionV2.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CandidateActionV2',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.signals.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'actionType')
    ..aOS(3, _omitFieldNames ? '' : 'title')
    ..aOS(4, _omitFieldNames ? '' : 'reason')
    ..aD(5, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..aOS(6, _omitFieldNames ? '' : 'timingHint')
    ..aOS(7, _omitFieldNames ? '' : 'payloadSeed')
    ..m<$core.String, $core.String>(8, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'CandidateActionV2.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.signals.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CandidateActionV2 clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CandidateActionV2 copyWith(void Function(CandidateActionV2) updates) =>
      super.copyWith((message) => updates(message as CandidateActionV2))
          as CandidateActionV2;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CandidateActionV2 create() => CandidateActionV2._();
  @$core.override
  CandidateActionV2 createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CandidateActionV2 getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CandidateActionV2>(create);
  static CandidateActionV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get actionType => $_getSZ(1);
  @$pb.TagNumber(2)
  set actionType($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasActionType() => $_has(1);
  @$pb.TagNumber(2)
  void clearActionType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get title => $_getSZ(2);
  @$pb.TagNumber(3)
  set title($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTitle() => $_has(2);
  @$pb.TagNumber(3)
  void clearTitle() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get reason => $_getSZ(3);
  @$pb.TagNumber(4)
  set reason($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasReason() => $_has(3);
  @$pb.TagNumber(4)
  void clearReason() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.double get confidence => $_getN(4);
  @$pb.TagNumber(5)
  set confidence($core.double value) => $_setFloat(4, value);
  @$pb.TagNumber(5)
  $core.bool hasConfidence() => $_has(4);
  @$pb.TagNumber(5)
  void clearConfidence() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get timingHint => $_getSZ(5);
  @$pb.TagNumber(6)
  set timingHint($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasTimingHint() => $_has(5);
  @$pb.TagNumber(6)
  void clearTimingHint() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get payloadSeed => $_getSZ(6);
  @$pb.TagNumber(7)
  set payloadSeed($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasPayloadSeed() => $_has(6);
  @$pb.TagNumber(7)
  void clearPayloadSeed() => $_clearField(7);

  @$pb.TagNumber(8)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(7);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
