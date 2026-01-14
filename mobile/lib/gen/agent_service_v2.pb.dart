// This is a generated file - do not edit.
//
// Generated from agent_service_v2.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

class ChatRequestV2 extends $pb.GeneratedMessage {
  factory ChatRequestV2({
    $core.String? userId,
    $core.String? message,
    $core.String? sessionId,
    $core.Iterable<$core.String>? activeTools,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (message != null) result.message = message;
    if (sessionId != null) result.sessionId = sessionId;
    if (activeTools != null) result.activeTools.addAll(activeTools);
    return result;
  }

  ChatRequestV2._();

  factory ChatRequestV2.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatRequestV2.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatRequestV2',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'sessionId')
    ..pPS(4, _omitFieldNames ? '' : 'activeTools')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatRequestV2 clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatRequestV2 copyWith(void Function(ChatRequestV2) updates) =>
      super.copyWith((message) => updates(message as ChatRequestV2))
          as ChatRequestV2;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatRequestV2 create() => ChatRequestV2._();
  @$core.override
  ChatRequestV2 createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatRequestV2 getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatRequestV2>(create);
  static ChatRequestV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get sessionId => $_getSZ(2);
  @$pb.TagNumber(3)
  set sessionId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSessionId() => $_has(2);
  @$pb.TagNumber(3)
  void clearSessionId() => $_clearField(3);

  /// 新增字段
  @$pb.TagNumber(4)
  $pb.PbList<$core.String> get activeTools => $_getList(3);
}

class ChatResponseV2 extends $pb.GeneratedMessage {
  factory ChatResponseV2({
    $core.String? content,
    $core.String? type,
    $fixnum.Int64? timestamp,
  }) {
    final result = create();
    if (content != null) result.content = content;
    if (type != null) result.type = type;
    if (timestamp != null) result.timestamp = timestamp;
    return result;
  }

  ChatResponseV2._();

  factory ChatResponseV2.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatResponseV2.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatResponseV2',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'content')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..aInt64(3, _omitFieldNames ? '' : 'timestamp')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatResponseV2 clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatResponseV2 copyWith(void Function(ChatResponseV2) updates) =>
      super.copyWith((message) => updates(message as ChatResponseV2))
          as ChatResponseV2;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatResponseV2 create() => ChatResponseV2._();
  @$core.override
  ChatResponseV2 createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatResponseV2 getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatResponseV2>(create);
  static ChatResponseV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get content => $_getSZ(0);
  @$pb.TagNumber(1)
  set content($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasContent() => $_has(0);
  @$pb.TagNumber(1)
  void clearContent() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => $_clearField(2);

  /// 新增字段
  @$pb.TagNumber(3)
  $fixnum.Int64 get timestamp => $_getI64(2);
  @$pb.TagNumber(3)
  set timestamp($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTimestamp() => $_has(2);
  @$pb.TagNumber(3)
  void clearTimestamp() => $_clearField(3);
}

class WeeklyReportRequest extends $pb.GeneratedMessage {
  factory WeeklyReportRequest({
    $core.String? userId,
    $core.String? weekId,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (weekId != null) result.weekId = weekId;
    return result;
  }

  WeeklyReportRequest._();

  factory WeeklyReportRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory WeeklyReportRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WeeklyReportRequest',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'weekId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WeeklyReportRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WeeklyReportRequest copyWith(void Function(WeeklyReportRequest) updates) =>
      super.copyWith((message) => updates(message as WeeklyReportRequest))
          as WeeklyReportRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WeeklyReportRequest create() => WeeklyReportRequest._();
  @$core.override
  WeeklyReportRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static WeeklyReportRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WeeklyReportRequest>(create);
  static WeeklyReportRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get weekId => $_getSZ(1);
  @$pb.TagNumber(2)
  set weekId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasWeekId() => $_has(1);
  @$pb.TagNumber(2)
  void clearWeekId() => $_clearField(2);
}

class WeeklyReport extends $pb.GeneratedMessage {
  factory WeeklyReport({
    $core.String? summary,
    $core.int? tasksCompleted,
  }) {
    final result = create();
    if (summary != null) result.summary = summary;
    if (tasksCompleted != null) result.tasksCompleted = tasksCompleted;
    return result;
  }

  WeeklyReport._();

  factory WeeklyReport.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory WeeklyReport.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WeeklyReport',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'summary')
    ..aI(2, _omitFieldNames ? '' : 'tasksCompleted')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WeeklyReport clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WeeklyReport copyWith(void Function(WeeklyReport) updates) =>
      super.copyWith((message) => updates(message as WeeklyReport))
          as WeeklyReport;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WeeklyReport create() => WeeklyReport._();
  @$core.override
  WeeklyReport createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static WeeklyReport getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WeeklyReport>(create);
  static WeeklyReport? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get summary => $_getSZ(0);
  @$pb.TagNumber(1)
  set summary($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSummary() => $_has(0);
  @$pb.TagNumber(1)
  void clearSummary() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get tasksCompleted => $_getIZ(1);
  @$pb.TagNumber(2)
  set tasksCompleted($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTasksCompleted() => $_has(1);
  @$pb.TagNumber(2)
  void clearTasksCompleted() => $_clearField(2);
}

class ProfileRequestV2 extends $pb.GeneratedMessage {
  factory ProfileRequestV2({
    $core.String? userId,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    return result;
  }

  ProfileRequestV2._();

  factory ProfileRequestV2.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ProfileRequestV2.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ProfileRequestV2',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileRequestV2 clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileRequestV2 copyWith(void Function(ProfileRequestV2) updates) =>
      super.copyWith((message) => updates(message as ProfileRequestV2))
          as ProfileRequestV2;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileRequestV2 create() => ProfileRequestV2._();
  @$core.override
  ProfileRequestV2 createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ProfileRequestV2 getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ProfileRequestV2>(create);
  static ProfileRequestV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);
}

class ProfileResponseV2 extends $pb.GeneratedMessage {
  factory ProfileResponseV2({
    $core.String? userId,
    $core.String? nickname,
    $core.int? level,
    $core.String? avatarUrl,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (nickname != null) result.nickname = nickname;
    if (level != null) result.level = level;
    if (avatarUrl != null) result.avatarUrl = avatarUrl;
    return result;
  }

  ProfileResponseV2._();

  factory ProfileResponseV2.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ProfileResponseV2.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ProfileResponseV2',
      package:
          const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.agent.v2'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'nickname')
    ..aI(3, _omitFieldNames ? '' : 'level')
    ..aOS(4, _omitFieldNames ? '' : 'avatarUrl')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileResponseV2 clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileResponseV2 copyWith(void Function(ProfileResponseV2) updates) =>
      super.copyWith((message) => updates(message as ProfileResponseV2))
          as ProfileResponseV2;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileResponseV2 create() => ProfileResponseV2._();
  @$core.override
  ProfileResponseV2 createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ProfileResponseV2 getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ProfileResponseV2>(create);
  static ProfileResponseV2? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get nickname => $_getSZ(1);
  @$pb.TagNumber(2)
  set nickname($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasNickname() => $_has(1);
  @$pb.TagNumber(2)
  void clearNickname() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get level => $_getIZ(2);
  @$pb.TagNumber(3)
  set level($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLevel() => $_has(2);
  @$pb.TagNumber(3)
  void clearLevel() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get avatarUrl => $_getSZ(3);
  @$pb.TagNumber(4)
  set avatarUrl($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasAvatarUrl() => $_has(3);
  @$pb.TagNumber(4)
  void clearAvatarUrl() => $_clearField(4);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
