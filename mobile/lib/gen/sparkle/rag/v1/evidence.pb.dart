// This is a generated file - do not edit.
//
// Generated from sparkle/rag/v1/evidence.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

class EvidenceNode extends $pb.GeneratedMessage {
  factory EvidenceNode({
    $core.String? nodeId,
    $core.String? sourceId,
    $core.String? snippet,
    $core.double? score,
    $core.String? sourceUri,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
    $core.String? sourceType,
  }) {
    final result = create();
    if (nodeId != null) result.nodeId = nodeId;
    if (sourceId != null) result.sourceId = sourceId;
    if (snippet != null) result.snippet = snippet;
    if (score != null) result.score = score;
    if (sourceUri != null) result.sourceUri = sourceUri;
    if (metadata != null) result.metadata.addEntries(metadata);
    if (sourceType != null) result.sourceType = sourceType;
    return result;
  }

  EvidenceNode._();

  factory EvidenceNode.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EvidenceNode.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EvidenceNode',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.rag.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nodeId')
    ..aOS(2, _omitFieldNames ? '' : 'sourceId')
    ..aOS(3, _omitFieldNames ? '' : 'snippet')
    ..aD(4, _omitFieldNames ? '' : 'score', fieldType: $pb.PbFieldType.OF)
    ..aOS(5, _omitFieldNames ? '' : 'sourceUri')
    ..m<$core.String, $core.String>(6, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'EvidenceNode.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.rag.v1'))
    ..aOS(7, _omitFieldNames ? '' : 'sourceType')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidenceNode clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidenceNode copyWith(void Function(EvidenceNode) updates) =>
      super.copyWith((message) => updates(message as EvidenceNode))
          as EvidenceNode;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidenceNode create() => EvidenceNode._();
  @$core.override
  EvidenceNode createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EvidenceNode getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EvidenceNode>(create);
  static EvidenceNode? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get nodeId => $_getSZ(0);
  @$pb.TagNumber(1)
  set nodeId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasNodeId() => $_has(0);
  @$pb.TagNumber(1)
  void clearNodeId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get sourceId => $_getSZ(1);
  @$pb.TagNumber(2)
  set sourceId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSourceId() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get snippet => $_getSZ(2);
  @$pb.TagNumber(3)
  set snippet($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSnippet() => $_has(2);
  @$pb.TagNumber(3)
  void clearSnippet() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.double get score => $_getN(3);
  @$pb.TagNumber(4)
  set score($core.double value) => $_setFloat(3, value);
  @$pb.TagNumber(4)
  $core.bool hasScore() => $_has(3);
  @$pb.TagNumber(4)
  void clearScore() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get sourceUri => $_getSZ(4);
  @$pb.TagNumber(5)
  set sourceUri($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasSourceUri() => $_has(4);
  @$pb.TagNumber(5)
  void clearSourceUri() => $_clearField(5);

  @$pb.TagNumber(6)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(5);

  @$pb.TagNumber(7)
  $core.String get sourceType => $_getSZ(6);
  @$pb.TagNumber(7)
  set sourceType($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasSourceType() => $_has(6);
  @$pb.TagNumber(7)
  void clearSourceType() => $_clearField(7);
}

class EvidencePack extends $pb.GeneratedMessage {
  factory EvidencePack({
    $core.String? requestId,
    $core.String? traceId,
    $core.Iterable<EvidenceNode>? nodes,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (traceId != null) result.traceId = traceId;
    if (nodes != null) result.nodes.addAll(nodes);
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  EvidencePack._();

  factory EvidencePack.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EvidencePack.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EvidencePack',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.rag.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..pPM<EvidenceNode>(3, _omitFieldNames ? '' : 'nodes',
        subBuilder: EvidenceNode.create)
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'EvidencePack.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.rag.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidencePack clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidencePack copyWith(void Function(EvidencePack) updates) =>
      super.copyWith((message) => updates(message as EvidencePack))
          as EvidencePack;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidencePack create() => EvidencePack._();
  @$core.override
  EvidencePack createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EvidencePack getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EvidencePack>(create);
  static EvidencePack? _defaultInstance;

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
  $pb.PbList<EvidenceNode> get nodes => $_getList(2);

  @$pb.TagNumber(4)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(3);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
