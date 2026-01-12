//
//  Generated code. Do not modify.
//  source: galaxy_service.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:async' as $async;
import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'google/protobuf/timestamp.pb.dart' as $2;

class CollaborativeGalaxyUpdate extends $pb.GeneratedMessage {
  factory CollaborativeGalaxyUpdate({
    $core.String? galaxyId,
    $core.List<$core.int>? yjsUpdate,
    $core.String? userId,
    $fixnum.Int64? timestamp,
  }) {
    final $result = create();
    if (galaxyId != null) {
      $result.galaxyId = galaxyId;
    }
    if (yjsUpdate != null) {
      $result.yjsUpdate = yjsUpdate;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    if (timestamp != null) {
      $result.timestamp = timestamp;
    }
    return $result;
  }
  CollaborativeGalaxyUpdate._() : super();
  factory CollaborativeGalaxyUpdate.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory CollaborativeGalaxyUpdate.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'CollaborativeGalaxyUpdate', package: const $pb.PackageName(_omitMessageNames ? '' : 'galaxy.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'galaxyId')
    ..a<$core.List<$core.int>>(2, _omitFieldNames ? '' : 'yjsUpdate', $pb.PbFieldType.OY)
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..aInt64(4, _omitFieldNames ? '' : 'timestamp')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  CollaborativeGalaxyUpdate clone() => CollaborativeGalaxyUpdate()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  CollaborativeGalaxyUpdate copyWith(void Function(CollaborativeGalaxyUpdate) updates) => super.copyWith((message) => updates(message as CollaborativeGalaxyUpdate)) as CollaborativeGalaxyUpdate;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CollaborativeGalaxyUpdate create() => CollaborativeGalaxyUpdate._();
  CollaborativeGalaxyUpdate createEmptyInstance() => create();
  static $pb.PbList<CollaborativeGalaxyUpdate> createRepeated() => $pb.PbList<CollaborativeGalaxyUpdate>();
  @$core.pragma('dart2js:noInline')
  static CollaborativeGalaxyUpdate getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CollaborativeGalaxyUpdate>(create);
  static CollaborativeGalaxyUpdate? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get galaxyId => $_getSZ(0);
  @$pb.TagNumber(1)
  set galaxyId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasGalaxyId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGalaxyId() => clearField(1);

  @$pb.TagNumber(2)
  $core.List<$core.int> get yjsUpdate => $_getN(1);
  @$pb.TagNumber(2)
  set yjsUpdate($core.List<$core.int> v) { $_setBytes(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasYjsUpdate() => $_has(1);
  @$pb.TagNumber(2)
  void clearYjsUpdate() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get timestamp => $_getI64(3);
  @$pb.TagNumber(4)
  set timestamp($fixnum.Int64 v) { $_setInt64(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasTimestamp() => $_has(3);
  @$pb.TagNumber(4)
  void clearTimestamp() => clearField(4);
}

class SyncCollaborativeGalaxyRequest extends $pb.GeneratedMessage {
  factory SyncCollaborativeGalaxyRequest({
    $core.String? galaxyId,
    $core.List<$core.int>? partialUpdate,
    $core.String? userId,
  }) {
    final $result = create();
    if (galaxyId != null) {
      $result.galaxyId = galaxyId;
    }
    if (partialUpdate != null) {
      $result.partialUpdate = partialUpdate;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    return $result;
  }
  SyncCollaborativeGalaxyRequest._() : super();
  factory SyncCollaborativeGalaxyRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory SyncCollaborativeGalaxyRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'SyncCollaborativeGalaxyRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'galaxy.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'galaxyId')
    ..a<$core.List<$core.int>>(2, _omitFieldNames ? '' : 'partialUpdate', $pb.PbFieldType.OY)
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  SyncCollaborativeGalaxyRequest clone() => SyncCollaborativeGalaxyRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  SyncCollaborativeGalaxyRequest copyWith(void Function(SyncCollaborativeGalaxyRequest) updates) => super.copyWith((message) => updates(message as SyncCollaborativeGalaxyRequest)) as SyncCollaborativeGalaxyRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SyncCollaborativeGalaxyRequest create() => SyncCollaborativeGalaxyRequest._();
  SyncCollaborativeGalaxyRequest createEmptyInstance() => create();
  static $pb.PbList<SyncCollaborativeGalaxyRequest> createRepeated() => $pb.PbList<SyncCollaborativeGalaxyRequest>();
  @$core.pragma('dart2js:noInline')
  static SyncCollaborativeGalaxyRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<SyncCollaborativeGalaxyRequest>(create);
  static SyncCollaborativeGalaxyRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get galaxyId => $_getSZ(0);
  @$pb.TagNumber(1)
  set galaxyId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasGalaxyId() => $_has(0);
  @$pb.TagNumber(1)
  void clearGalaxyId() => clearField(1);

  @$pb.TagNumber(2)
  $core.List<$core.int> get partialUpdate => $_getN(1);
  @$pb.TagNumber(2)
  set partialUpdate($core.List<$core.int> v) { $_setBytes(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasPartialUpdate() => $_has(1);
  @$pb.TagNumber(2)
  void clearPartialUpdate() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => clearField(3);
}

class SyncCollaborativeGalaxyResponse extends $pb.GeneratedMessage {
  factory SyncCollaborativeGalaxyResponse({
    $core.bool? success,
    $core.List<$core.int>? serverUpdate,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (serverUpdate != null) {
      $result.serverUpdate = serverUpdate;
    }
    return $result;
  }
  SyncCollaborativeGalaxyResponse._() : super();
  factory SyncCollaborativeGalaxyResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory SyncCollaborativeGalaxyResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'SyncCollaborativeGalaxyResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'galaxy.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..a<$core.List<$core.int>>(2, _omitFieldNames ? '' : 'serverUpdate', $pb.PbFieldType.OY)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  SyncCollaborativeGalaxyResponse clone() => SyncCollaborativeGalaxyResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  SyncCollaborativeGalaxyResponse copyWith(void Function(SyncCollaborativeGalaxyResponse) updates) => super.copyWith((message) => updates(message as SyncCollaborativeGalaxyResponse)) as SyncCollaborativeGalaxyResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SyncCollaborativeGalaxyResponse create() => SyncCollaborativeGalaxyResponse._();
  SyncCollaborativeGalaxyResponse createEmptyInstance() => create();
  static $pb.PbList<SyncCollaborativeGalaxyResponse> createRepeated() => $pb.PbList<SyncCollaborativeGalaxyResponse>();
  @$core.pragma('dart2js:noInline')
  static SyncCollaborativeGalaxyResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<SyncCollaborativeGalaxyResponse>(create);
  static SyncCollaborativeGalaxyResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.List<$core.int> get serverUpdate => $_getN(1);
  @$pb.TagNumber(2)
  set serverUpdate($core.List<$core.int> v) { $_setBytes(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasServerUpdate() => $_has(1);
  @$pb.TagNumber(2)
  void clearServerUpdate() => clearField(2);
}

class UpdateNodeMasteryRequest extends $pb.GeneratedMessage {
  factory UpdateNodeMasteryRequest({
    $core.String? userId,
    $core.String? nodeId,
    $core.int? mastery,
    $2.Timestamp? version,
    $core.String? reason,
    $core.String? requestId,
    $fixnum.Int64? revision,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (nodeId != null) {
      $result.nodeId = nodeId;
    }
    if (mastery != null) {
      $result.mastery = mastery;
    }
    if (version != null) {
      $result.version = version;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (revision != null) {
      $result.revision = revision;
    }
    return $result;
  }
  UpdateNodeMasteryRequest._() : super();
  factory UpdateNodeMasteryRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory UpdateNodeMasteryRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'UpdateNodeMasteryRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'galaxy.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'nodeId')
    ..a<$core.int>(3, _omitFieldNames ? '' : 'mastery', $pb.PbFieldType.O3)
    ..aOM<$2.Timestamp>(4, _omitFieldNames ? '' : 'version', subBuilder: $2.Timestamp.create)
    ..aOS(5, _omitFieldNames ? '' : 'reason')
    ..aOS(6, _omitFieldNames ? '' : 'requestId')
    ..aInt64(7, _omitFieldNames ? '' : 'revision')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  UpdateNodeMasteryRequest clone() => UpdateNodeMasteryRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  UpdateNodeMasteryRequest copyWith(void Function(UpdateNodeMasteryRequest) updates) => super.copyWith((message) => updates(message as UpdateNodeMasteryRequest)) as UpdateNodeMasteryRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryRequest create() => UpdateNodeMasteryRequest._();
  UpdateNodeMasteryRequest createEmptyInstance() => create();
  static $pb.PbList<UpdateNodeMasteryRequest> createRepeated() => $pb.PbList<UpdateNodeMasteryRequest>();
  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UpdateNodeMasteryRequest>(create);
  static UpdateNodeMasteryRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get nodeId => $_getSZ(1);
  @$pb.TagNumber(2)
  set nodeId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasNodeId() => $_has(1);
  @$pb.TagNumber(2)
  void clearNodeId() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get mastery => $_getIZ(2);
  @$pb.TagNumber(3)
  set mastery($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMastery() => $_has(2);
  @$pb.TagNumber(3)
  void clearMastery() => clearField(3);

  @$pb.TagNumber(4)
  $2.Timestamp get version => $_getN(3);
  @$pb.TagNumber(4)
  set version($2.Timestamp v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasVersion() => $_has(3);
  @$pb.TagNumber(4)
  void clearVersion() => clearField(4);
  @$pb.TagNumber(4)
  $2.Timestamp ensureVersion() => $_ensure(3);

  @$pb.TagNumber(5)
  $core.String get reason => $_getSZ(4);
  @$pb.TagNumber(5)
  set reason($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasReason() => $_has(4);
  @$pb.TagNumber(5)
  void clearReason() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get requestId => $_getSZ(5);
  @$pb.TagNumber(6)
  set requestId($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasRequestId() => $_has(5);
  @$pb.TagNumber(6)
  void clearRequestId() => clearField(6);

  @$pb.TagNumber(7)
  $fixnum.Int64 get revision => $_getI64(6);
  @$pb.TagNumber(7)
  set revision($fixnum.Int64 v) { $_setInt64(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasRevision() => $_has(6);
  @$pb.TagNumber(7)
  void clearRevision() => clearField(7);
}

class UpdateNodeMasteryResponse extends $pb.GeneratedMessage {
  factory UpdateNodeMasteryResponse({
    $core.bool? success,
    $core.int? oldMastery,
    $core.int? newMastery,
    $core.String? reason,
    $core.String? requestId,
    $fixnum.Int64? currentRevision,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (oldMastery != null) {
      $result.oldMastery = oldMastery;
    }
    if (newMastery != null) {
      $result.newMastery = newMastery;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (currentRevision != null) {
      $result.currentRevision = currentRevision;
    }
    return $result;
  }
  UpdateNodeMasteryResponse._() : super();
  factory UpdateNodeMasteryResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory UpdateNodeMasteryResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'UpdateNodeMasteryResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'galaxy.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..a<$core.int>(2, _omitFieldNames ? '' : 'oldMastery', $pb.PbFieldType.O3)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'newMastery', $pb.PbFieldType.O3)
    ..aOS(4, _omitFieldNames ? '' : 'reason')
    ..aOS(5, _omitFieldNames ? '' : 'requestId')
    ..aInt64(6, _omitFieldNames ? '' : 'currentRevision')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  UpdateNodeMasteryResponse clone() => UpdateNodeMasteryResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  UpdateNodeMasteryResponse copyWith(void Function(UpdateNodeMasteryResponse) updates) => super.copyWith((message) => updates(message as UpdateNodeMasteryResponse)) as UpdateNodeMasteryResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryResponse create() => UpdateNodeMasteryResponse._();
  UpdateNodeMasteryResponse createEmptyInstance() => create();
  static $pb.PbList<UpdateNodeMasteryResponse> createRepeated() => $pb.PbList<UpdateNodeMasteryResponse>();
  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UpdateNodeMasteryResponse>(create);
  static UpdateNodeMasteryResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get oldMastery => $_getIZ(1);
  @$pb.TagNumber(2)
  set oldMastery($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasOldMastery() => $_has(1);
  @$pb.TagNumber(2)
  void clearOldMastery() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get newMastery => $_getIZ(2);
  @$pb.TagNumber(3)
  set newMastery($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasNewMastery() => $_has(2);
  @$pb.TagNumber(3)
  void clearNewMastery() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get reason => $_getSZ(3);
  @$pb.TagNumber(4)
  set reason($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasReason() => $_has(3);
  @$pb.TagNumber(4)
  void clearReason() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get requestId => $_getSZ(4);
  @$pb.TagNumber(5)
  set requestId($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasRequestId() => $_has(4);
  @$pb.TagNumber(5)
  void clearRequestId() => clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get currentRevision => $_getI64(5);
  @$pb.TagNumber(6)
  set currentRevision($fixnum.Int64 v) { $_setInt64(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasCurrentRevision() => $_has(5);
  @$pb.TagNumber(6)
  void clearCurrentRevision() => clearField(6);
}

class GalaxyServiceApi {
  $pb.RpcClient _client;
  GalaxyServiceApi(this._client);

  $async.Future<UpdateNodeMasteryResponse> updateNodeMastery($pb.ClientContext? ctx, UpdateNodeMasteryRequest request) =>
    _client.invoke<UpdateNodeMasteryResponse>(ctx, 'GalaxyService', 'UpdateNodeMastery', request, UpdateNodeMasteryResponse())
  ;
  $async.Future<SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy($pb.ClientContext? ctx, SyncCollaborativeGalaxyRequest request) =>
    _client.invoke<SyncCollaborativeGalaxyResponse>(ctx, 'GalaxyService', 'SyncCollaborativeGalaxy', request, SyncCollaborativeGalaxyResponse())
  ;
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
