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

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
