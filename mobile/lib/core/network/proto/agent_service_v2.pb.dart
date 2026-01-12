//
//  Generated code. Do not modify.
//  source: agent_service_v2.proto
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

class ChatRequestV2 extends $pb.GeneratedMessage {
  factory ChatRequestV2({
    $core.String? userId,
    $core.String? message,
    $core.String? sessionId,
    $core.Iterable<$core.String>? activeTools,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (message != null) {
      $result.message = message;
    }
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (activeTools != null) {
      $result.activeTools.addAll(activeTools);
    }
    return $result;
  }
  ChatRequestV2._() : super();
  factory ChatRequestV2.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatRequestV2.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatRequestV2', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'sessionId')
    ..pPS(4, _omitFieldNames ? '' : 'activeTools')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatRequestV2 clone() => ChatRequestV2()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatRequestV2 copyWith(void Function(ChatRequestV2) updates) => super.copyWith((message) => updates(message as ChatRequestV2)) as ChatRequestV2;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatRequestV2 create() => ChatRequestV2._();
  ChatRequestV2 createEmptyInstance() => create();
  static $pb.PbList<ChatRequestV2> createRepeated() => $pb.PbList<ChatRequestV2>();
  @$core.pragma('dart2js:noInline')
  static ChatRequestV2 getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatRequestV2>(create);
  static ChatRequestV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get sessionId => $_getSZ(2);
  @$pb.TagNumber(3)
  set sessionId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasSessionId() => $_has(2);
  @$pb.TagNumber(3)
  void clearSessionId() => clearField(3);

  /// 新增字段
  @$pb.TagNumber(4)
  $core.List<$core.String> get activeTools => $_getList(3);
}

class ChatResponseV2 extends $pb.GeneratedMessage {
  factory ChatResponseV2({
    $core.String? content,
    $core.String? type,
    $fixnum.Int64? timestamp,
  }) {
    final $result = create();
    if (content != null) {
      $result.content = content;
    }
    if (type != null) {
      $result.type = type;
    }
    if (timestamp != null) {
      $result.timestamp = timestamp;
    }
    return $result;
  }
  ChatResponseV2._() : super();
  factory ChatResponseV2.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatResponseV2.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatResponseV2', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'content')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..aInt64(3, _omitFieldNames ? '' : 'timestamp')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatResponseV2 clone() => ChatResponseV2()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatResponseV2 copyWith(void Function(ChatResponseV2) updates) => super.copyWith((message) => updates(message as ChatResponseV2)) as ChatResponseV2;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatResponseV2 create() => ChatResponseV2._();
  ChatResponseV2 createEmptyInstance() => create();
  static $pb.PbList<ChatResponseV2> createRepeated() => $pb.PbList<ChatResponseV2>();
  @$core.pragma('dart2js:noInline')
  static ChatResponseV2 getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatResponseV2>(create);
  static ChatResponseV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get content => $_getSZ(0);
  @$pb.TagNumber(1)
  set content($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasContent() => $_has(0);
  @$pb.TagNumber(1)
  void clearContent() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => clearField(2);

  /// 新增字段
  @$pb.TagNumber(3)
  $fixnum.Int64 get timestamp => $_getI64(2);
  @$pb.TagNumber(3)
  set timestamp($fixnum.Int64 v) { $_setInt64(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTimestamp() => $_has(2);
  @$pb.TagNumber(3)
  void clearTimestamp() => clearField(3);
}

class WeeklyReportRequest extends $pb.GeneratedMessage {
  factory WeeklyReportRequest({
    $core.String? userId,
    $core.String? weekId,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (weekId != null) {
      $result.weekId = weekId;
    }
    return $result;
  }
  WeeklyReportRequest._() : super();
  factory WeeklyReportRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory WeeklyReportRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'WeeklyReportRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'weekId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  WeeklyReportRequest clone() => WeeklyReportRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  WeeklyReportRequest copyWith(void Function(WeeklyReportRequest) updates) => super.copyWith((message) => updates(message as WeeklyReportRequest)) as WeeklyReportRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WeeklyReportRequest create() => WeeklyReportRequest._();
  WeeklyReportRequest createEmptyInstance() => create();
  static $pb.PbList<WeeklyReportRequest> createRepeated() => $pb.PbList<WeeklyReportRequest>();
  @$core.pragma('dart2js:noInline')
  static WeeklyReportRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WeeklyReportRequest>(create);
  static WeeklyReportRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get weekId => $_getSZ(1);
  @$pb.TagNumber(2)
  set weekId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasWeekId() => $_has(1);
  @$pb.TagNumber(2)
  void clearWeekId() => clearField(2);
}

class WeeklyReport extends $pb.GeneratedMessage {
  factory WeeklyReport({
    $core.String? summary,
    $core.int? tasksCompleted,
  }) {
    final $result = create();
    if (summary != null) {
      $result.summary = summary;
    }
    if (tasksCompleted != null) {
      $result.tasksCompleted = tasksCompleted;
    }
    return $result;
  }
  WeeklyReport._() : super();
  factory WeeklyReport.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory WeeklyReport.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'WeeklyReport', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'summary')
    ..a<$core.int>(2, _omitFieldNames ? '' : 'tasksCompleted', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  WeeklyReport clone() => WeeklyReport()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  WeeklyReport copyWith(void Function(WeeklyReport) updates) => super.copyWith((message) => updates(message as WeeklyReport)) as WeeklyReport;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WeeklyReport create() => WeeklyReport._();
  WeeklyReport createEmptyInstance() => create();
  static $pb.PbList<WeeklyReport> createRepeated() => $pb.PbList<WeeklyReport>();
  @$core.pragma('dart2js:noInline')
  static WeeklyReport getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WeeklyReport>(create);
  static WeeklyReport? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get summary => $_getSZ(0);
  @$pb.TagNumber(1)
  set summary($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSummary() => $_has(0);
  @$pb.TagNumber(1)
  void clearSummary() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get tasksCompleted => $_getIZ(1);
  @$pb.TagNumber(2)
  set tasksCompleted($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTasksCompleted() => $_has(1);
  @$pb.TagNumber(2)
  void clearTasksCompleted() => clearField(2);
}

class ProfileRequestV2 extends $pb.GeneratedMessage {
  factory ProfileRequestV2({
    $core.String? userId,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    return $result;
  }
  ProfileRequestV2._() : super();
  factory ProfileRequestV2.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ProfileRequestV2.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ProfileRequestV2', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ProfileRequestV2 clone() => ProfileRequestV2()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ProfileRequestV2 copyWith(void Function(ProfileRequestV2) updates) => super.copyWith((message) => updates(message as ProfileRequestV2)) as ProfileRequestV2;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileRequestV2 create() => ProfileRequestV2._();
  ProfileRequestV2 createEmptyInstance() => create();
  static $pb.PbList<ProfileRequestV2> createRepeated() => $pb.PbList<ProfileRequestV2>();
  @$core.pragma('dart2js:noInline')
  static ProfileRequestV2 getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ProfileRequestV2>(create);
  static ProfileRequestV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);
}

class ProfileResponseV2 extends $pb.GeneratedMessage {
  factory ProfileResponseV2({
    $core.String? userId,
    $core.String? nickname,
    $core.int? level,
    $core.String? avatarUrl,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (nickname != null) {
      $result.nickname = nickname;
    }
    if (level != null) {
      $result.level = level;
    }
    if (avatarUrl != null) {
      $result.avatarUrl = avatarUrl;
    }
    return $result;
  }
  ProfileResponseV2._() : super();
  factory ProfileResponseV2.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ProfileResponseV2.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ProfileResponseV2', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'nickname')
    ..a<$core.int>(3, _omitFieldNames ? '' : 'level', $pb.PbFieldType.O3)
    ..aOS(4, _omitFieldNames ? '' : 'avatarUrl')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ProfileResponseV2 clone() => ProfileResponseV2()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ProfileResponseV2 copyWith(void Function(ProfileResponseV2) updates) => super.copyWith((message) => updates(message as ProfileResponseV2)) as ProfileResponseV2;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileResponseV2 create() => ProfileResponseV2._();
  ProfileResponseV2 createEmptyInstance() => create();
  static $pb.PbList<ProfileResponseV2> createRepeated() => $pb.PbList<ProfileResponseV2>();
  @$core.pragma('dart2js:noInline')
  static ProfileResponseV2 getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ProfileResponseV2>(create);
  static ProfileResponseV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get nickname => $_getSZ(1);
  @$pb.TagNumber(2)
  set nickname($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasNickname() => $_has(1);
  @$pb.TagNumber(2)
  void clearNickname() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get level => $_getIZ(2);
  @$pb.TagNumber(3)
  set level($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasLevel() => $_has(2);
  @$pb.TagNumber(3)
  void clearLevel() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get avatarUrl => $_getSZ(3);
  @$pb.TagNumber(4)
  set avatarUrl($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasAvatarUrl() => $_has(3);
  @$pb.TagNumber(4)
  void clearAvatarUrl() => clearField(4);
}

class AgentServiceV2Api {
  $pb.RpcClient _client;
  AgentServiceV2Api(this._client);

  $async.Future<ChatResponseV2> streamChat($pb.ClientContext? ctx, ChatRequestV2 request) =>
    _client.invoke<ChatResponseV2>(ctx, 'AgentServiceV2', 'StreamChat', request, ChatResponseV2())
  ;
  $async.Future<ProfileResponseV2> getUserProfile($pb.ClientContext? ctx, ProfileRequestV2 request) =>
    _client.invoke<ProfileResponseV2>(ctx, 'AgentServiceV2', 'GetUserProfile', request, ProfileResponseV2())
  ;
  $async.Future<WeeklyReport> getWeeklyReport($pb.ClientContext? ctx, WeeklyReportRequest request) =>
    _client.invoke<WeeklyReport>(ctx, 'AgentServiceV2', 'GetWeeklyReport', request, WeeklyReport())
  ;
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
