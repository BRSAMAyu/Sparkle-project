//
//  Generated code. Do not modify.
//  source: sparkle/rag/v1/evidence.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

class EvidenceNode extends $pb.GeneratedMessage {
  factory EvidenceNode({
    $core.String? nodeId,
    $core.String? sourceId,
    $core.String? snippet,
    $core.double? score,
    $core.String? sourceUri,
    $core.Map<$core.String, $core.String>? metadata,
    $core.String? sourceType,
  }) {
    final $result = create();
    if (nodeId != null) {
      $result.nodeId = nodeId;
    }
    if (sourceId != null) {
      $result.sourceId = sourceId;
    }
    if (snippet != null) {
      $result.snippet = snippet;
    }
    if (score != null) {
      $result.score = score;
    }
    if (sourceUri != null) {
      $result.sourceUri = sourceUri;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    if (sourceType != null) {
      $result.sourceType = sourceType;
    }
    return $result;
  }
  EvidenceNode._() : super();
  factory EvidenceNode.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory EvidenceNode.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'EvidenceNode', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.rag.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nodeId')
    ..aOS(2, _omitFieldNames ? '' : 'sourceId')
    ..aOS(3, _omitFieldNames ? '' : 'snippet')
    ..a<$core.double>(4, _omitFieldNames ? '' : 'score', $pb.PbFieldType.OF)
    ..aOS(5, _omitFieldNames ? '' : 'sourceUri')
    ..m<$core.String, $core.String>(6, _omitFieldNames ? '' : 'metadata', entryClassName: 'EvidenceNode.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.rag.v1'))
    ..aOS(7, _omitFieldNames ? '' : 'sourceType')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  EvidenceNode clone() => EvidenceNode()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  EvidenceNode copyWith(void Function(EvidenceNode) updates) => super.copyWith((message) => updates(message as EvidenceNode)) as EvidenceNode;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidenceNode create() => EvidenceNode._();
  EvidenceNode createEmptyInstance() => create();
  static $pb.PbList<EvidenceNode> createRepeated() => $pb.PbList<EvidenceNode>();
  @$core.pragma('dart2js:noInline')
  static EvidenceNode getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<EvidenceNode>(create);
  static EvidenceNode? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get nodeId => $_getSZ(0);
  @$pb.TagNumber(1)
  set nodeId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasNodeId() => $_has(0);
  @$pb.TagNumber(1)
  void clearNodeId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get sourceId => $_getSZ(1);
  @$pb.TagNumber(2)
  set sourceId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasSourceId() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get snippet => $_getSZ(2);
  @$pb.TagNumber(3)
  set snippet($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasSnippet() => $_has(2);
  @$pb.TagNumber(3)
  void clearSnippet() => clearField(3);

  @$pb.TagNumber(4)
  $core.double get score => $_getN(3);
  @$pb.TagNumber(4)
  set score($core.double v) { $_setFloat(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasScore() => $_has(3);
  @$pb.TagNumber(4)
  void clearScore() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get sourceUri => $_getSZ(4);
  @$pb.TagNumber(5)
  set sourceUri($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasSourceUri() => $_has(4);
  @$pb.TagNumber(5)
  void clearSourceUri() => clearField(5);

  @$pb.TagNumber(6)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(5);

  @$pb.TagNumber(7)
  $core.String get sourceType => $_getSZ(6);
  @$pb.TagNumber(7)
  set sourceType($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasSourceType() => $_has(6);
  @$pb.TagNumber(7)
  void clearSourceType() => clearField(7);
}

class EvidencePack extends $pb.GeneratedMessage {
  factory EvidencePack({
    $core.String? requestId,
    $core.String? traceId,
    $core.Iterable<EvidenceNode>? nodes,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (nodes != null) {
      $result.nodes.addAll(nodes);
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  EvidencePack._() : super();
  factory EvidencePack.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory EvidencePack.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'EvidencePack', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.rag.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..pc<EvidenceNode>(3, _omitFieldNames ? '' : 'nodes', $pb.PbFieldType.PM, subBuilder: EvidenceNode.create)
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'metadata', entryClassName: 'EvidencePack.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.rag.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  EvidencePack clone() => EvidencePack()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  EvidencePack copyWith(void Function(EvidencePack) updates) => super.copyWith((message) => updates(message as EvidencePack)) as EvidencePack;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidencePack create() => EvidencePack._();
  EvidencePack createEmptyInstance() => create();
  static $pb.PbList<EvidencePack> createRepeated() => $pb.PbList<EvidencePack>();
  @$core.pragma('dart2js:noInline')
  static EvidencePack getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<EvidencePack>(create);
  static EvidencePack? _defaultInstance;

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
  $core.List<EvidenceNode> get nodes => $_getList(2);

  @$pb.TagNumber(4)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(3);
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
