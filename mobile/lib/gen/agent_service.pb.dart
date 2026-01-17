// This is a generated file - do not edit.
//
// Generated from agent_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;
import 'package:protobuf/well_known_types/google/protobuf/struct.pb.dart' as $1;
import 'package:protobuf/well_known_types/google/protobuf/timestamp.pb.dart'
    as $2;

import 'agent_service.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'agent_service.pbenum.dart';

enum ChatRequest_Input { message, toolResult, notSet }

/// ChatRequest encapsulates the user's input and necessary context for the AI.
class ChatRequest extends $pb.GeneratedMessage {
  factory ChatRequest({
    $core.String? userId,
    $core.String? sessionId,
    $core.String? message,
    UserProfile? userProfile,
    $1.Struct? extraContext,
    $core.Iterable<ChatMessage>? history,
    ToolResult? toolResult,
    ChatConfig? config,
    $core.String? requestId,
    $core.Iterable<$core.String>? fileIds,
    $core.bool? includeReferences,
    $core.Iterable<$core.String>? activeTools,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (sessionId != null) result.sessionId = sessionId;
    if (message != null) result.message = message;
    if (userProfile != null) result.userProfile = userProfile;
    if (extraContext != null) result.extraContext = extraContext;
    if (history != null) result.history.addAll(history);
    if (toolResult != null) result.toolResult = toolResult;
    if (config != null) result.config = config;
    if (requestId != null) result.requestId = requestId;
    if (fileIds != null) result.fileIds.addAll(fileIds);
    if (includeReferences != null) result.includeReferences = includeReferences;
    if (activeTools != null) result.activeTools.addAll(activeTools);
    return result;
  }

  ChatRequest._();

  factory ChatRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, ChatRequest_Input> _ChatRequest_InputByTag =
      {
    3: ChatRequest_Input.message,
    7: ChatRequest_Input.toolResult,
    0: ChatRequest_Input.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..oo(0, [3, 7])
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'sessionId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..aOM<UserProfile>(4, _omitFieldNames ? '' : 'userProfile',
        subBuilder: UserProfile.create)
    ..aOM<$1.Struct>(5, _omitFieldNames ? '' : 'extraContext',
        subBuilder: $1.Struct.create)
    ..pPM<ChatMessage>(6, _omitFieldNames ? '' : 'history',
        subBuilder: ChatMessage.create)
    ..aOM<ToolResult>(7, _omitFieldNames ? '' : 'toolResult',
        subBuilder: ToolResult.create)
    ..aOM<ChatConfig>(8, _omitFieldNames ? '' : 'config',
        subBuilder: ChatConfig.create)
    ..aOS(9, _omitFieldNames ? '' : 'requestId')
    ..pPS(10, _omitFieldNames ? '' : 'fileIds')
    ..aOB(11, _omitFieldNames ? '' : 'includeReferences')
    ..pPS(12, _omitFieldNames ? '' : 'activeTools')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatRequest copyWith(void Function(ChatRequest) updates) =>
      super.copyWith((message) => updates(message as ChatRequest))
          as ChatRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatRequest create() => ChatRequest._();
  @$core.override
  ChatRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatRequest>(create);
  static ChatRequest? _defaultInstance;

  @$pb.TagNumber(3)
  @$pb.TagNumber(7)
  ChatRequest_Input whichInput() => _ChatRequest_InputByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(3)
  @$pb.TagNumber(7)
  void clearInput() => $_clearField($_whichOneof(0));

  /// Unique identifier of the user interacting with the agent.
  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  /// Session ID to track the conversation thread.
  /// If empty, the agent may treat it as a new stateless interaction or generate a new session.
  @$pb.TagNumber(2)
  $core.String get sessionId => $_getSZ(1);
  @$pb.TagNumber(2)
  set sessionId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSessionId() => $_has(1);
  @$pb.TagNumber(2)
  void clearSessionId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => $_clearField(3);

  /// Core user profile context (Strongly Typed).
  /// This data is usually fetched from the primary DB by the Gateway.
  @$pb.TagNumber(4)
  UserProfile get userProfile => $_getN(3);
  @$pb.TagNumber(4)
  set userProfile(UserProfile value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasUserProfile() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserProfile() => $_clearField(4);
  @$pb.TagNumber(4)
  UserProfile ensureUserProfile() => $_ensure(3);

  /// Extra dynamic context (Flexible).
  /// Used for temporary or extension data (e.g. "current_weather", "frontend_version").
  @$pb.TagNumber(5)
  $1.Struct get extraContext => $_getN(4);
  @$pb.TagNumber(5)
  set extraContext($1.Struct value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasExtraContext() => $_has(4);
  @$pb.TagNumber(5)
  void clearExtraContext() => $_clearField(5);
  @$pb.TagNumber(5)
  $1.Struct ensureExtraContext() => $_ensure(4);

  /// Optional: Recent conversation history if the client/gateway manages state.
  /// This history field is mainly for passing frontend temporary context, or when Session is stateless.
  /// By default, Python should prioritize reading history from the database.
  @$pb.TagNumber(6)
  $pb.PbList<ChatMessage> get history => $_getList(5);

  @$pb.TagNumber(7)
  ToolResult get toolResult => $_getN(6);
  @$pb.TagNumber(7)
  set toolResult(ToolResult value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasToolResult() => $_has(6);
  @$pb.TagNumber(7)
  void clearToolResult() => $_clearField(7);
  @$pb.TagNumber(7)
  ToolResult ensureToolResult() => $_ensure(6);

  /// Configuration for this specific request.
  @$pb.TagNumber(8)
  ChatConfig get config => $_getN(7);
  @$pb.TagNumber(8)
  set config(ChatConfig value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasConfig() => $_has(7);
  @$pb.TagNumber(8)
  void clearConfig() => $_clearField(8);
  @$pb.TagNumber(8)
  ChatConfig ensureConfig() => $_ensure(7);

  /// Unique identifier for this specific request/message (Trace ID).
  @$pb.TagNumber(9)
  $core.String get requestId => $_getSZ(8);
  @$pb.TagNumber(9)
  set requestId($core.String value) => $_setString(8, value);
  @$pb.TagNumber(9)
  $core.bool hasRequestId() => $_has(8);
  @$pb.TagNumber(9)
  void clearRequestId() => $_clearField(9);

  /// Optional: document IDs to scope RAG retrieval to specific files.
  @$pb.TagNumber(10)
  $pb.PbList<$core.String> get fileIds => $_getList(9);

  /// Optional: include document references in streaming responses.
  @$pb.TagNumber(11)
  $core.bool get includeReferences => $_getBF(10);
  @$pb.TagNumber(11)
  set includeReferences($core.bool value) => $_setBool(10, value);
  @$pb.TagNumber(11)
  $core.bool hasIncludeReferences() => $_has(10);
  @$pb.TagNumber(11)
  void clearIncludeReferences() => $_clearField(11);

  /// Optional: List of tools currently active/available for this request
  @$pb.TagNumber(12)
  $pb.PbList<$core.String> get activeTools => $_getList(11);
}

/// UserProfile defines key user attributes for personalization.
class UserProfile extends $pb.GeneratedMessage {
  factory UserProfile({
    $core.String? nickname,
    $core.String? timezone,
    $core.String? language,
    $core.bool? isPro,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? preferences,
    $core.String? extraContext,
    $core.int? level,
    $core.String? avatarUrl,
  }) {
    final result = create();
    if (nickname != null) result.nickname = nickname;
    if (timezone != null) result.timezone = timezone;
    if (language != null) result.language = language;
    if (isPro != null) result.isPro = isPro;
    if (preferences != null) result.preferences.addEntries(preferences);
    if (extraContext != null) result.extraContext = extraContext;
    if (level != null) result.level = level;
    if (avatarUrl != null) result.avatarUrl = avatarUrl;
    return result;
  }

  UserProfile._();

  factory UserProfile.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UserProfile.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UserProfile',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nickname')
    ..aOS(2, _omitFieldNames ? '' : 'timezone')
    ..aOS(3, _omitFieldNames ? '' : 'language')
    ..aOB(4, _omitFieldNames ? '' : 'isPro')
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'preferences',
        entryClassName: 'UserProfile.PreferencesEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('agent.v1'))
    ..aOS(6, _omitFieldNames ? '' : 'extraContext')
    ..aI(7, _omitFieldNames ? '' : 'level')
    ..aOS(8, _omitFieldNames ? '' : 'avatarUrl')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserProfile clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UserProfile copyWith(void Function(UserProfile) updates) =>
      super.copyWith((message) => updates(message as UserProfile))
          as UserProfile;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UserProfile create() => UserProfile._();
  @$core.override
  UserProfile createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UserProfile getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UserProfile>(create);
  static UserProfile? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get nickname => $_getSZ(0);
  @$pb.TagNumber(1)
  set nickname($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasNickname() => $_has(0);
  @$pb.TagNumber(1)
  void clearNickname() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get timezone => $_getSZ(1);
  @$pb.TagNumber(2)
  set timezone($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTimezone() => $_has(1);
  @$pb.TagNumber(2)
  void clearTimezone() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get language => $_getSZ(2);
  @$pb.TagNumber(3)
  set language($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLanguage() => $_has(2);
  @$pb.TagNumber(3)
  void clearLanguage() => $_clearField(3);

  /// Pro status might determine access to advanced models or tools.
  @$pb.TagNumber(4)
  $core.bool get isPro => $_getBF(3);
  @$pb.TagNumber(4)
  set isPro($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasIsPro() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsPro() => $_clearField(4);

  /// Dynamic preferences (e.g., "concise_mode", "role_play_enabled")
  @$pb.TagNumber(5)
  $pb.PbMap<$core.String, $core.String> get preferences => $_getMap(4);

  /// P0: Extra context (JSON string) containing user state for context propagation
  /// Includes pending_tasks, active_plans, focus_stats, recent_progress (set by Go Gateway)
  @$pb.TagNumber(6)
  $core.String get extraContext => $_getSZ(5);
  @$pb.TagNumber(6)
  set extraContext($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasExtraContext() => $_has(5);
  @$pb.TagNumber(6)
  void clearExtraContext() => $_clearField(6);

  /// User level/experience
  @$pb.TagNumber(7)
  $core.int get level => $_getIZ(6);
  @$pb.TagNumber(7)
  set level($core.int value) => $_setSignedInt32(6, value);
  @$pb.TagNumber(7)
  $core.bool hasLevel() => $_has(6);
  @$pb.TagNumber(7)
  void clearLevel() => $_clearField(7);

  /// URL to user's avatar image
  @$pb.TagNumber(8)
  $core.String get avatarUrl => $_getSZ(7);
  @$pb.TagNumber(8)
  set avatarUrl($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasAvatarUrl() => $_has(7);
  @$pb.TagNumber(8)
  void clearAvatarUrl() => $_clearField(8);
}

/// Request to get user profile
class ProfileRequest extends $pb.GeneratedMessage {
  factory ProfileRequest({
    $core.String? userId,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    return result;
  }

  ProfileRequest._();

  factory ProfileRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ProfileRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ProfileRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ProfileRequest copyWith(void Function(ProfileRequest) updates) =>
      super.copyWith((message) => updates(message as ProfileRequest))
          as ProfileRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileRequest create() => ProfileRequest._();
  @$core.override
  ProfileRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ProfileRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ProfileRequest>(create);
  static ProfileRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);
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
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
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
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
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

/// ToolResult represents the output of a tool execution performed by the Client/Gateway.
class ToolResult extends $pb.GeneratedMessage {
  factory ToolResult({
    $core.String? toolCallId,
    $core.String? toolName,
    $core.String? resultJson,
    $core.bool? isError,
    $core.String? errorMessage,
  }) {
    final result = create();
    if (toolCallId != null) result.toolCallId = toolCallId;
    if (toolName != null) result.toolName = toolName;
    if (resultJson != null) result.resultJson = resultJson;
    if (isError != null) result.isError = isError;
    if (errorMessage != null) result.errorMessage = errorMessage;
    return result;
  }

  ToolResult._();

  factory ToolResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ToolResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ToolResult',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'toolCallId')
    ..aOS(2, _omitFieldNames ? '' : 'toolName')
    ..aOS(3, _omitFieldNames ? '' : 'resultJson')
    ..aOB(4, _omitFieldNames ? '' : 'isError')
    ..aOS(5, _omitFieldNames ? '' : 'errorMessage')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolResult copyWith(void Function(ToolResult) updates) =>
      super.copyWith((message) => updates(message as ToolResult)) as ToolResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolResult create() => ToolResult._();
  @$core.override
  ToolResult createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ToolResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ToolResult>(create);
  static ToolResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get toolCallId => $_getSZ(0);
  @$pb.TagNumber(1)
  set toolCallId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasToolCallId() => $_has(0);
  @$pb.TagNumber(1)
  void clearToolCallId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get toolName => $_getSZ(1);
  @$pb.TagNumber(2)
  set toolName($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasToolName() => $_has(1);
  @$pb.TagNumber(2)
  void clearToolName() => $_clearField(2);

  /// The result payload, typically JSON.
  @$pb.TagNumber(3)
  $core.String get resultJson => $_getSZ(2);
  @$pb.TagNumber(3)
  set resultJson($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasResultJson() => $_has(2);
  @$pb.TagNumber(3)
  void clearResultJson() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get isError => $_getBF(3);
  @$pb.TagNumber(4)
  set isError($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasIsError() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsError() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get errorMessage => $_getSZ(4);
  @$pb.TagNumber(5)
  set errorMessage($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasErrorMessage() => $_has(4);
  @$pb.TagNumber(5)
  void clearErrorMessage() => $_clearField(5);
}

/// ChatConfig allows overriding default behaviors for a specific request.
class ChatConfig extends $pb.GeneratedMessage {
  factory ChatConfig({
    $core.String? model,
    $core.double? temperature,
    $core.int? maxTokens,
    $core.bool? toolsEnabled,
  }) {
    final result = create();
    if (model != null) result.model = model;
    if (temperature != null) result.temperature = temperature;
    if (maxTokens != null) result.maxTokens = maxTokens;
    if (toolsEnabled != null) result.toolsEnabled = toolsEnabled;
    return result;
  }

  ChatConfig._();

  factory ChatConfig.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatConfig.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatConfig',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..aD(2, _omitFieldNames ? '' : 'temperature', fieldType: $pb.PbFieldType.OF)
    ..aI(3, _omitFieldNames ? '' : 'maxTokens')
    ..aOB(4, _omitFieldNames ? '' : 'toolsEnabled')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatConfig clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatConfig copyWith(void Function(ChatConfig) updates) =>
      super.copyWith((message) => updates(message as ChatConfig)) as ChatConfig;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatConfig create() => ChatConfig._();
  @$core.override
  ChatConfig createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatConfig getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatConfig>(create);
  static ChatConfig? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.double get temperature => $_getN(1);
  @$pb.TagNumber(2)
  set temperature($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTemperature() => $_has(1);
  @$pb.TagNumber(2)
  void clearTemperature() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get maxTokens => $_getIZ(2);
  @$pb.TagNumber(3)
  set maxTokens($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasMaxTokens() => $_has(2);
  @$pb.TagNumber(3)
  void clearMaxTokens() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get toolsEnabled => $_getBF(3);
  @$pb.TagNumber(4)
  set toolsEnabled($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasToolsEnabled() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolsEnabled() => $_clearField(4);
}

/// ChatMessage represents a single message in the conversation history.
class ChatMessage extends $pb.GeneratedMessage {
  factory ChatMessage({
    $core.String? role,
    $core.String? content,
    $core.String? name,
    $core.String? toolCallId,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (role != null) result.role = role;
    if (content != null) result.content = content;
    if (name != null) result.name = name;
    if (toolCallId != null) result.toolCallId = toolCallId;
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  ChatMessage._();

  factory ChatMessage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatMessage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatMessage',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'role')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aOS(3, _omitFieldNames ? '' : 'name')
    ..aOS(4, _omitFieldNames ? '' : 'toolCallId')
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'ChatMessage.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatMessage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatMessage copyWith(void Function(ChatMessage) updates) =>
      super.copyWith((message) => updates(message as ChatMessage))
          as ChatMessage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatMessage create() => ChatMessage._();
  @$core.override
  ChatMessage createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatMessage getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatMessage>(create);
  static ChatMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get role => $_getSZ(0);
  @$pb.TagNumber(1)
  set role($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRole() => $_has(0);
  @$pb.TagNumber(1)
  void clearRole() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get name => $_getSZ(2);
  @$pb.TagNumber(3)
  set name($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasName() => $_has(2);
  @$pb.TagNumber(3)
  void clearName() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get toolCallId => $_getSZ(3);
  @$pb.TagNumber(4)
  set toolCallId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasToolCallId() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolCallId() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(4);
}

enum ChatResponse_Content {
  delta,
  toolCall,
  statusUpdate,
  fullText,
  error,
  usage,
  citations,
  toolResult,
  intervention,
  notSet
}

/// ChatResponse represents a chunk of the stream from the Agent.
class ChatResponse extends $pb.GeneratedMessage {
  factory ChatResponse({
    $core.String? responseId,
    $fixnum.Int64? createdAt,
    $core.String? delta,
    ToolCall? toolCall,
    AgentStatus? statusUpdate,
    $core.String? fullText,
    Error? error,
    Usage? usage,
    FinishReason? finishReason,
    $core.String? requestId,
    CitationBlock? citations,
    ToolResultPayload? toolResult,
    $fixnum.Int64? timestamp,
    InterventionPayload? intervention,
  }) {
    final result = create();
    if (responseId != null) result.responseId = responseId;
    if (createdAt != null) result.createdAt = createdAt;
    if (delta != null) result.delta = delta;
    if (toolCall != null) result.toolCall = toolCall;
    if (statusUpdate != null) result.statusUpdate = statusUpdate;
    if (fullText != null) result.fullText = fullText;
    if (error != null) result.error = error;
    if (usage != null) result.usage = usage;
    if (finishReason != null) result.finishReason = finishReason;
    if (requestId != null) result.requestId = requestId;
    if (citations != null) result.citations = citations;
    if (toolResult != null) result.toolResult = toolResult;
    if (timestamp != null) result.timestamp = timestamp;
    if (intervention != null) result.intervention = intervention;
    return result;
  }

  ChatResponse._();

  factory ChatResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ChatResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static const $core.Map<$core.int, ChatResponse_Content>
      _ChatResponse_ContentByTag = {
    3: ChatResponse_Content.delta,
    4: ChatResponse_Content.toolCall,
    5: ChatResponse_Content.statusUpdate,
    6: ChatResponse_Content.fullText,
    7: ChatResponse_Content.error,
    8: ChatResponse_Content.usage,
    11: ChatResponse_Content.citations,
    12: ChatResponse_Content.toolResult,
    14: ChatResponse_Content.intervention,
    0: ChatResponse_Content.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ChatResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..oo(0, [3, 4, 5, 6, 7, 8, 11, 12, 14])
    ..aOS(1, _omitFieldNames ? '' : 'responseId')
    ..aInt64(2, _omitFieldNames ? '' : 'createdAt')
    ..aOS(3, _omitFieldNames ? '' : 'delta')
    ..aOM<ToolCall>(4, _omitFieldNames ? '' : 'toolCall',
        subBuilder: ToolCall.create)
    ..aOM<AgentStatus>(5, _omitFieldNames ? '' : 'statusUpdate',
        subBuilder: AgentStatus.create)
    ..aOS(6, _omitFieldNames ? '' : 'fullText')
    ..aOM<Error>(7, _omitFieldNames ? '' : 'error', subBuilder: Error.create)
    ..aOM<Usage>(8, _omitFieldNames ? '' : 'usage', subBuilder: Usage.create)
    ..aE<FinishReason>(9, _omitFieldNames ? '' : 'finishReason',
        enumValues: FinishReason.values)
    ..aOS(10, _omitFieldNames ? '' : 'requestId')
    ..aOM<CitationBlock>(11, _omitFieldNames ? '' : 'citations',
        subBuilder: CitationBlock.create)
    ..aOM<ToolResultPayload>(12, _omitFieldNames ? '' : 'toolResult',
        subBuilder: ToolResultPayload.create)
    ..aInt64(13, _omitFieldNames ? '' : 'timestamp')
    ..aOM<InterventionPayload>(14, _omitFieldNames ? '' : 'intervention',
        subBuilder: InterventionPayload.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ChatResponse copyWith(void Function(ChatResponse) updates) =>
      super.copyWith((message) => updates(message as ChatResponse))
          as ChatResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatResponse create() => ChatResponse._();
  @$core.override
  ChatResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ChatResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ChatResponse>(create);
  static ChatResponse? _defaultInstance;

  @$pb.TagNumber(3)
  @$pb.TagNumber(4)
  @$pb.TagNumber(5)
  @$pb.TagNumber(6)
  @$pb.TagNumber(7)
  @$pb.TagNumber(8)
  @$pb.TagNumber(11)
  @$pb.TagNumber(12)
  @$pb.TagNumber(14)
  ChatResponse_Content whichContent() =>
      _ChatResponse_ContentByTag[$_whichOneof(0)]!;
  @$pb.TagNumber(3)
  @$pb.TagNumber(4)
  @$pb.TagNumber(5)
  @$pb.TagNumber(6)
  @$pb.TagNumber(7)
  @$pb.TagNumber(8)
  @$pb.TagNumber(11)
  @$pb.TagNumber(12)
  @$pb.TagNumber(14)
  void clearContent() => $_clearField($_whichOneof(0));

  @$pb.TagNumber(1)
  $core.String get responseId => $_getSZ(0);
  @$pb.TagNumber(1)
  set responseId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasResponseId() => $_has(0);
  @$pb.TagNumber(1)
  void clearResponseId() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get createdAt => $_getI64(1);
  @$pb.TagNumber(2)
  set createdAt($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasCreatedAt() => $_has(1);
  @$pb.TagNumber(2)
  void clearCreatedAt() => $_clearField(2);

  /// Text delta for the typewriter effect.
  @$pb.TagNumber(3)
  $core.String get delta => $_getSZ(2);
  @$pb.TagNumber(3)
  set delta($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasDelta() => $_has(2);
  @$pb.TagNumber(3)
  void clearDelta() => $_clearField(3);

  /// Request for the client/gateway to execute a tool.
  /// Note: If the model supports parallel function calling, multiple ToolCall frames may be streamed.
  @$pb.TagNumber(4)
  ToolCall get toolCall => $_getN(3);
  @$pb.TagNumber(4)
  set toolCall(ToolCall value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasToolCall() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolCall() => $_clearField(4);
  @$pb.TagNumber(4)
  ToolCall ensureToolCall() => $_ensure(3);

  /// Log message for internal agent actions/thoughts.
  @$pb.TagNumber(5)
  AgentStatus get statusUpdate => $_getN(4);
  @$pb.TagNumber(5)
  set statusUpdate(AgentStatus value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasStatusUpdate() => $_has(4);
  @$pb.TagNumber(5)
  void clearStatusUpdate() => $_clearField(5);
  @$pb.TagNumber(5)
  AgentStatus ensureStatusUpdate() => $_ensure(4);

  /// Final complete response text.
  @$pb.TagNumber(6)
  $core.String get fullText => $_getSZ(5);
  @$pb.TagNumber(6)
  set fullText($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasFullText() => $_has(5);
  @$pb.TagNumber(6)
  void clearFullText() => $_clearField(6);

  /// Error information.
  @$pb.TagNumber(7)
  Error get error => $_getN(6);
  @$pb.TagNumber(7)
  set error(Error value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasError() => $_has(6);
  @$pb.TagNumber(7)
  void clearError() => $_clearField(7);
  @$pb.TagNumber(7)
  Error ensureError() => $_ensure(6);

  /// Usage statistics.
  @$pb.TagNumber(8)
  Usage get usage => $_getN(7);
  @$pb.TagNumber(8)
  set usage(Usage value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasUsage() => $_has(7);
  @$pb.TagNumber(8)
  void clearUsage() => $_clearField(8);
  @$pb.TagNumber(8)
  Usage ensureUsage() => $_ensure(7);

  /// Indicates why the generation finished.
  @$pb.TagNumber(9)
  FinishReason get finishReason => $_getN(8);
  @$pb.TagNumber(9)
  set finishReason(FinishReason value) => $_setField(9, value);
  @$pb.TagNumber(9)
  $core.bool hasFinishReason() => $_has(8);
  @$pb.TagNumber(9)
  void clearFinishReason() => $_clearField(9);

  /// The ID of the request that triggered this response (for tracing).
  @$pb.TagNumber(10)
  $core.String get requestId => $_getSZ(9);
  @$pb.TagNumber(10)
  set requestId($core.String value) => $_setString(9, value);
  @$pb.TagNumber(10)
  $core.bool hasRequestId() => $_has(9);
  @$pb.TagNumber(10)
  void clearRequestId() => $_clearField(10);

  /// Citations from RAG.
  @$pb.TagNumber(11)
  CitationBlock get citations => $_getN(10);
  @$pb.TagNumber(11)
  set citations(CitationBlock value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasCitations() => $_has(10);
  @$pb.TagNumber(11)
  void clearCitations() => $_clearField(11);
  @$pb.TagNumber(11)
  CitationBlock ensureCitations() => $_ensure(10);

  /// Tool execution result (for UI rendering).
  @$pb.TagNumber(12)
  ToolResultPayload get toolResult => $_getN(11);
  @$pb.TagNumber(12)
  set toolResult(ToolResultPayload value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasToolResult() => $_has(11);
  @$pb.TagNumber(12)
  void clearToolResult() => $_clearField(12);
  @$pb.TagNumber(12)
  ToolResultPayload ensureToolResult() => $_ensure(11);

  /// Timestamp of response generation
  @$pb.TagNumber(13)
  $fixnum.Int64 get timestamp => $_getI64(12);
  @$pb.TagNumber(13)
  set timestamp($fixnum.Int64 value) => $_setInt64(12, value);
  @$pb.TagNumber(13)
  $core.bool hasTimestamp() => $_has(12);
  @$pb.TagNumber(13)
  void clearTimestamp() => $_clearField(13);

  /// Intervention payload (contract-based UI).
  @$pb.TagNumber(14)
  InterventionPayload get intervention => $_getN(13);
  @$pb.TagNumber(14)
  set intervention(InterventionPayload value) => $_setField(14, value);
  @$pb.TagNumber(14)
  $core.bool hasIntervention() => $_has(13);
  @$pb.TagNumber(14)
  void clearIntervention() => $_clearField(14);
  @$pb.TagNumber(14)
  InterventionPayload ensureIntervention() => $_ensure(13);
}

class CitationBlock extends $pb.GeneratedMessage {
  factory CitationBlock({
    $core.Iterable<Citation>? citations,
  }) {
    final result = create();
    if (citations != null) result.citations.addAll(citations);
    return result;
  }

  CitationBlock._();

  factory CitationBlock.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CitationBlock.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CitationBlock',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..pPM<Citation>(1, _omitFieldNames ? '' : 'citations',
        subBuilder: Citation.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CitationBlock clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CitationBlock copyWith(void Function(CitationBlock) updates) =>
      super.copyWith((message) => updates(message as CitationBlock))
          as CitationBlock;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CitationBlock create() => CitationBlock._();
  @$core.override
  CitationBlock createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CitationBlock getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CitationBlock>(create);
  static CitationBlock? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<Citation> get citations => $_getList(0);
}

class Citation extends $pb.GeneratedMessage {
  factory Citation({
    $core.String? id,
    $core.String? title,
    $core.String? content,
    $core.String? sourceType,
    $core.String? url,
    $core.double? score,
    $core.String? fileId,
    $core.int? pageNumber,
    $core.int? chunkIndex,
    $core.String? sectionTitle,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (title != null) result.title = title;
    if (content != null) result.content = content;
    if (sourceType != null) result.sourceType = sourceType;
    if (url != null) result.url = url;
    if (score != null) result.score = score;
    if (fileId != null) result.fileId = fileId;
    if (pageNumber != null) result.pageNumber = pageNumber;
    if (chunkIndex != null) result.chunkIndex = chunkIndex;
    if (sectionTitle != null) result.sectionTitle = sectionTitle;
    return result;
  }

  Citation._();

  factory Citation.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Citation.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Citation',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'title')
    ..aOS(3, _omitFieldNames ? '' : 'content')
    ..aOS(4, _omitFieldNames ? '' : 'sourceType')
    ..aOS(5, _omitFieldNames ? '' : 'url')
    ..aD(6, _omitFieldNames ? '' : 'score', fieldType: $pb.PbFieldType.OF)
    ..aOS(7, _omitFieldNames ? '' : 'fileId')
    ..aI(8, _omitFieldNames ? '' : 'pageNumber')
    ..aI(9, _omitFieldNames ? '' : 'chunkIndex')
    ..aOS(10, _omitFieldNames ? '' : 'sectionTitle')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Citation clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Citation copyWith(void Function(Citation) updates) =>
      super.copyWith((message) => updates(message as Citation)) as Citation;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Citation create() => Citation._();
  @$core.override
  Citation createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Citation getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Citation>(create);
  static Citation? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get title => $_getSZ(1);
  @$pb.TagNumber(2)
  set title($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTitle() => $_has(1);
  @$pb.TagNumber(2)
  void clearTitle() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get content => $_getSZ(2);
  @$pb.TagNumber(3)
  set content($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearContent() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get sourceType => $_getSZ(3);
  @$pb.TagNumber(4)
  set sourceType($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSourceType() => $_has(3);
  @$pb.TagNumber(4)
  void clearSourceType() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get url => $_getSZ(4);
  @$pb.TagNumber(5)
  set url($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasUrl() => $_has(4);
  @$pb.TagNumber(5)
  void clearUrl() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.double get score => $_getN(5);
  @$pb.TagNumber(6)
  set score($core.double value) => $_setFloat(5, value);
  @$pb.TagNumber(6)
  $core.bool hasScore() => $_has(5);
  @$pb.TagNumber(6)
  void clearScore() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get fileId => $_getSZ(6);
  @$pb.TagNumber(7)
  set fileId($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasFileId() => $_has(6);
  @$pb.TagNumber(7)
  void clearFileId() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.int get pageNumber => $_getIZ(7);
  @$pb.TagNumber(8)
  set pageNumber($core.int value) => $_setSignedInt32(7, value);
  @$pb.TagNumber(8)
  $core.bool hasPageNumber() => $_has(7);
  @$pb.TagNumber(8)
  void clearPageNumber() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.int get chunkIndex => $_getIZ(8);
  @$pb.TagNumber(9)
  set chunkIndex($core.int value) => $_setSignedInt32(8, value);
  @$pb.TagNumber(9)
  $core.bool hasChunkIndex() => $_has(8);
  @$pb.TagNumber(9)
  void clearChunkIndex() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.String get sectionTitle => $_getSZ(9);
  @$pb.TagNumber(10)
  set sectionTitle($core.String value) => $_setString(9, value);
  @$pb.TagNumber(10)
  $core.bool hasSectionTitle() => $_has(9);
  @$pb.TagNumber(10)
  void clearSectionTitle() => $_clearField(10);
}

class ToolCall extends $pb.GeneratedMessage {
  factory ToolCall({
    $core.String? id,
    $core.String? name,
    $core.String? arguments,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (name != null) result.name = name;
    if (arguments != null) result.arguments = arguments;
    return result;
  }

  ToolCall._();

  factory ToolCall.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ToolCall.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ToolCall',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'name')
    ..aOS(3, _omitFieldNames ? '' : 'arguments')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolCall clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolCall copyWith(void Function(ToolCall) updates) =>
      super.copyWith((message) => updates(message as ToolCall)) as ToolCall;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolCall create() => ToolCall._();
  @$core.override
  ToolCall createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ToolCall getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ToolCall>(create);
  static ToolCall? _defaultInstance;

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
  $core.String get arguments => $_getSZ(2);
  @$pb.TagNumber(3)
  set arguments($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasArguments() => $_has(2);
  @$pb.TagNumber(3)
  void clearArguments() => $_clearField(3);
}

class ToolResultPayload extends $pb.GeneratedMessage {
  factory ToolResultPayload({
    $core.String? toolName,
    $core.bool? success,
    $1.Struct? data,
    $core.String? errorMessage,
    $core.String? suggestion,
    $core.String? widgetType,
    $1.Struct? widgetData,
    $core.String? toolCallId,
  }) {
    final result = create();
    if (toolName != null) result.toolName = toolName;
    if (success != null) result.success = success;
    if (data != null) result.data = data;
    if (errorMessage != null) result.errorMessage = errorMessage;
    if (suggestion != null) result.suggestion = suggestion;
    if (widgetType != null) result.widgetType = widgetType;
    if (widgetData != null) result.widgetData = widgetData;
    if (toolCallId != null) result.toolCallId = toolCallId;
    return result;
  }

  ToolResultPayload._();

  factory ToolResultPayload.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ToolResultPayload.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ToolResultPayload',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'toolName')
    ..aOB(2, _omitFieldNames ? '' : 'success')
    ..aOM<$1.Struct>(3, _omitFieldNames ? '' : 'data',
        subBuilder: $1.Struct.create)
    ..aOS(4, _omitFieldNames ? '' : 'errorMessage')
    ..aOS(5, _omitFieldNames ? '' : 'suggestion')
    ..aOS(6, _omitFieldNames ? '' : 'widgetType')
    ..aOM<$1.Struct>(7, _omitFieldNames ? '' : 'widgetData',
        subBuilder: $1.Struct.create)
    ..aOS(8, _omitFieldNames ? '' : 'toolCallId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolResultPayload clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolResultPayload copyWith(void Function(ToolResultPayload) updates) =>
      super.copyWith((message) => updates(message as ToolResultPayload))
          as ToolResultPayload;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolResultPayload create() => ToolResultPayload._();
  @$core.override
  ToolResultPayload createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ToolResultPayload getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ToolResultPayload>(create);
  static ToolResultPayload? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get toolName => $_getSZ(0);
  @$pb.TagNumber(1)
  set toolName($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasToolName() => $_has(0);
  @$pb.TagNumber(1)
  void clearToolName() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.bool get success => $_getBF(1);
  @$pb.TagNumber(2)
  set success($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSuccess() => $_has(1);
  @$pb.TagNumber(2)
  void clearSuccess() => $_clearField(2);

  @$pb.TagNumber(3)
  $1.Struct get data => $_getN(2);
  @$pb.TagNumber(3)
  set data($1.Struct value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasData() => $_has(2);
  @$pb.TagNumber(3)
  void clearData() => $_clearField(3);
  @$pb.TagNumber(3)
  $1.Struct ensureData() => $_ensure(2);

  @$pb.TagNumber(4)
  $core.String get errorMessage => $_getSZ(3);
  @$pb.TagNumber(4)
  set errorMessage($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasErrorMessage() => $_has(3);
  @$pb.TagNumber(4)
  void clearErrorMessage() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get suggestion => $_getSZ(4);
  @$pb.TagNumber(5)
  set suggestion($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasSuggestion() => $_has(4);
  @$pb.TagNumber(5)
  void clearSuggestion() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get widgetType => $_getSZ(5);
  @$pb.TagNumber(6)
  set widgetType($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasWidgetType() => $_has(5);
  @$pb.TagNumber(6)
  void clearWidgetType() => $_clearField(6);

  @$pb.TagNumber(7)
  $1.Struct get widgetData => $_getN(6);
  @$pb.TagNumber(7)
  set widgetData($1.Struct value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasWidgetData() => $_has(6);
  @$pb.TagNumber(7)
  void clearWidgetData() => $_clearField(7);
  @$pb.TagNumber(7)
  $1.Struct ensureWidgetData() => $_ensure(6);

  @$pb.TagNumber(8)
  $core.String get toolCallId => $_getSZ(7);
  @$pb.TagNumber(8)
  set toolCallId($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasToolCallId() => $_has(7);
  @$pb.TagNumber(8)
  void clearToolCallId() => $_clearField(8);
}

class EvidenceRef extends $pb.GeneratedMessage {
  factory EvidenceRef({
    $core.String? type,
    $core.String? id,
    $core.String? schemaVersion,
    $core.bool? userDeleted,
  }) {
    final result = create();
    if (type != null) result.type = type;
    if (id != null) result.id = id;
    if (schemaVersion != null) result.schemaVersion = schemaVersion;
    if (userDeleted != null) result.userDeleted = userDeleted;
    return result;
  }

  EvidenceRef._();

  factory EvidenceRef.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EvidenceRef.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EvidenceRef',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'type')
    ..aOS(2, _omitFieldNames ? '' : 'id')
    ..aOS(3, _omitFieldNames ? '' : 'schemaVersion')
    ..aOB(4, _omitFieldNames ? '' : 'userDeleted')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidenceRef clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EvidenceRef copyWith(void Function(EvidenceRef) updates) =>
      super.copyWith((message) => updates(message as EvidenceRef))
          as EvidenceRef;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidenceRef create() => EvidenceRef._();
  @$core.override
  EvidenceRef createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EvidenceRef getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EvidenceRef>(create);
  static EvidenceRef? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get type => $_getSZ(0);
  @$pb.TagNumber(1)
  set type($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get id => $_getSZ(1);
  @$pb.TagNumber(2)
  set id($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasId() => $_has(1);
  @$pb.TagNumber(2)
  void clearId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get schemaVersion => $_getSZ(2);
  @$pb.TagNumber(3)
  set schemaVersion($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSchemaVersion() => $_has(2);
  @$pb.TagNumber(3)
  void clearSchemaVersion() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get userDeleted => $_getBF(3);
  @$pb.TagNumber(4)
  set userDeleted($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasUserDeleted() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserDeleted() => $_clearField(4);
}

class CoolDownPolicy extends $pb.GeneratedMessage {
  factory CoolDownPolicy({
    $core.String? policy,
    $fixnum.Int64? untilMs,
  }) {
    final result = create();
    if (policy != null) result.policy = policy;
    if (untilMs != null) result.untilMs = untilMs;
    return result;
  }

  CoolDownPolicy._();

  factory CoolDownPolicy.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory CoolDownPolicy.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'CoolDownPolicy',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'policy')
    ..aInt64(2, _omitFieldNames ? '' : 'untilMs')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CoolDownPolicy clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  CoolDownPolicy copyWith(void Function(CoolDownPolicy) updates) =>
      super.copyWith((message) => updates(message as CoolDownPolicy))
          as CoolDownPolicy;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CoolDownPolicy create() => CoolDownPolicy._();
  @$core.override
  CoolDownPolicy createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static CoolDownPolicy getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<CoolDownPolicy>(create);
  static CoolDownPolicy? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get policy => $_getSZ(0);
  @$pb.TagNumber(1)
  set policy($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPolicy() => $_has(0);
  @$pb.TagNumber(1)
  void clearPolicy() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get untilMs => $_getI64(1);
  @$pb.TagNumber(2)
  set untilMs($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUntilMs() => $_has(1);
  @$pb.TagNumber(2)
  void clearUntilMs() => $_clearField(2);
}

class InterventionReason extends $pb.GeneratedMessage {
  factory InterventionReason({
    $core.String? triggerEventId,
    $core.String? explanationText,
    $core.double? confidence,
    $core.Iterable<EvidenceRef>? evidenceRefs,
    $core.Iterable<$core.String>? decisionTrace,
  }) {
    final result = create();
    if (triggerEventId != null) result.triggerEventId = triggerEventId;
    if (explanationText != null) result.explanationText = explanationText;
    if (confidence != null) result.confidence = confidence;
    if (evidenceRefs != null) result.evidenceRefs.addAll(evidenceRefs);
    if (decisionTrace != null) result.decisionTrace.addAll(decisionTrace);
    return result;
  }

  InterventionReason._();

  factory InterventionReason.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionReason.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionReason',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'triggerEventId')
    ..aOS(2, _omitFieldNames ? '' : 'explanationText')
    ..aD(3, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..pPM<EvidenceRef>(4, _omitFieldNames ? '' : 'evidenceRefs',
        subBuilder: EvidenceRef.create)
    ..pPS(5, _omitFieldNames ? '' : 'decisionTrace')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionReason clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionReason copyWith(void Function(InterventionReason) updates) =>
      super.copyWith((message) => updates(message as InterventionReason))
          as InterventionReason;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionReason create() => InterventionReason._();
  @$core.override
  InterventionReason createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionReason getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionReason>(create);
  static InterventionReason? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get triggerEventId => $_getSZ(0);
  @$pb.TagNumber(1)
  set triggerEventId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTriggerEventId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTriggerEventId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get explanationText => $_getSZ(1);
  @$pb.TagNumber(2)
  set explanationText($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasExplanationText() => $_has(1);
  @$pb.TagNumber(2)
  void clearExplanationText() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double value) => $_setFloat(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbList<EvidenceRef> get evidenceRefs => $_getList(3);

  @$pb.TagNumber(5)
  $pb.PbList<$core.String> get decisionTrace => $_getList(4);
}

class InterventionRequest extends $pb.GeneratedMessage {
  factory InterventionRequest({
    $core.String? id,
    $core.String? dedupeKey,
    $core.String? topic,
    $fixnum.Int64? createdAtMs,
    $fixnum.Int64? expiresAtMs,
    $core.bool? isRetractable,
    $core.String? supersedesId,
    $core.String? schemaVersion,
    $core.String? policyVersion,
    $core.String? modelVersion,
    InterventionReason? reason,
    InterventionLevel? level,
    CoolDownPolicy? onReject,
    $1.Struct? content,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (dedupeKey != null) result.dedupeKey = dedupeKey;
    if (topic != null) result.topic = topic;
    if (createdAtMs != null) result.createdAtMs = createdAtMs;
    if (expiresAtMs != null) result.expiresAtMs = expiresAtMs;
    if (isRetractable != null) result.isRetractable = isRetractable;
    if (supersedesId != null) result.supersedesId = supersedesId;
    if (schemaVersion != null) result.schemaVersion = schemaVersion;
    if (policyVersion != null) result.policyVersion = policyVersion;
    if (modelVersion != null) result.modelVersion = modelVersion;
    if (reason != null) result.reason = reason;
    if (level != null) result.level = level;
    if (onReject != null) result.onReject = onReject;
    if (content != null) result.content = content;
    return result;
  }

  InterventionRequest._();

  factory InterventionRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'dedupeKey')
    ..aOS(3, _omitFieldNames ? '' : 'topic')
    ..aInt64(4, _omitFieldNames ? '' : 'createdAtMs')
    ..aInt64(5, _omitFieldNames ? '' : 'expiresAtMs')
    ..aOB(6, _omitFieldNames ? '' : 'isRetractable')
    ..aOS(7, _omitFieldNames ? '' : 'supersedesId')
    ..aOS(8, _omitFieldNames ? '' : 'schemaVersion')
    ..aOS(9, _omitFieldNames ? '' : 'policyVersion')
    ..aOS(10, _omitFieldNames ? '' : 'modelVersion')
    ..aOM<InterventionReason>(11, _omitFieldNames ? '' : 'reason',
        subBuilder: InterventionReason.create)
    ..aE<InterventionLevel>(12, _omitFieldNames ? '' : 'level',
        enumValues: InterventionLevel.values)
    ..aOM<CoolDownPolicy>(13, _omitFieldNames ? '' : 'onReject',
        subBuilder: CoolDownPolicy.create)
    ..aOM<$1.Struct>(14, _omitFieldNames ? '' : 'content',
        subBuilder: $1.Struct.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionRequest copyWith(void Function(InterventionRequest) updates) =>
      super.copyWith((message) => updates(message as InterventionRequest))
          as InterventionRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionRequest create() => InterventionRequest._();
  @$core.override
  InterventionRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionRequest>(create);
  static InterventionRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get dedupeKey => $_getSZ(1);
  @$pb.TagNumber(2)
  set dedupeKey($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDedupeKey() => $_has(1);
  @$pb.TagNumber(2)
  void clearDedupeKey() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get topic => $_getSZ(2);
  @$pb.TagNumber(3)
  set topic($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTopic() => $_has(2);
  @$pb.TagNumber(3)
  void clearTopic() => $_clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get createdAtMs => $_getI64(3);
  @$pb.TagNumber(4)
  set createdAtMs($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCreatedAtMs() => $_has(3);
  @$pb.TagNumber(4)
  void clearCreatedAtMs() => $_clearField(4);

  @$pb.TagNumber(5)
  $fixnum.Int64 get expiresAtMs => $_getI64(4);
  @$pb.TagNumber(5)
  set expiresAtMs($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasExpiresAtMs() => $_has(4);
  @$pb.TagNumber(5)
  void clearExpiresAtMs() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.bool get isRetractable => $_getBF(5);
  @$pb.TagNumber(6)
  set isRetractable($core.bool value) => $_setBool(5, value);
  @$pb.TagNumber(6)
  $core.bool hasIsRetractable() => $_has(5);
  @$pb.TagNumber(6)
  void clearIsRetractable() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get supersedesId => $_getSZ(6);
  @$pb.TagNumber(7)
  set supersedesId($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasSupersedesId() => $_has(6);
  @$pb.TagNumber(7)
  void clearSupersedesId() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get schemaVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set schemaVersion($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasSchemaVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearSchemaVersion() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.String get policyVersion => $_getSZ(8);
  @$pb.TagNumber(9)
  set policyVersion($core.String value) => $_setString(8, value);
  @$pb.TagNumber(9)
  $core.bool hasPolicyVersion() => $_has(8);
  @$pb.TagNumber(9)
  void clearPolicyVersion() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.String get modelVersion => $_getSZ(9);
  @$pb.TagNumber(10)
  set modelVersion($core.String value) => $_setString(9, value);
  @$pb.TagNumber(10)
  $core.bool hasModelVersion() => $_has(9);
  @$pb.TagNumber(10)
  void clearModelVersion() => $_clearField(10);

  @$pb.TagNumber(11)
  InterventionReason get reason => $_getN(10);
  @$pb.TagNumber(11)
  set reason(InterventionReason value) => $_setField(11, value);
  @$pb.TagNumber(11)
  $core.bool hasReason() => $_has(10);
  @$pb.TagNumber(11)
  void clearReason() => $_clearField(11);
  @$pb.TagNumber(11)
  InterventionReason ensureReason() => $_ensure(10);

  @$pb.TagNumber(12)
  InterventionLevel get level => $_getN(11);
  @$pb.TagNumber(12)
  set level(InterventionLevel value) => $_setField(12, value);
  @$pb.TagNumber(12)
  $core.bool hasLevel() => $_has(11);
  @$pb.TagNumber(12)
  void clearLevel() => $_clearField(12);

  @$pb.TagNumber(13)
  CoolDownPolicy get onReject => $_getN(12);
  @$pb.TagNumber(13)
  set onReject(CoolDownPolicy value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasOnReject() => $_has(12);
  @$pb.TagNumber(13)
  void clearOnReject() => $_clearField(13);
  @$pb.TagNumber(13)
  CoolDownPolicy ensureOnReject() => $_ensure(12);

  @$pb.TagNumber(14)
  $1.Struct get content => $_getN(13);
  @$pb.TagNumber(14)
  set content($1.Struct value) => $_setField(14, value);
  @$pb.TagNumber(14)
  $core.bool hasContent() => $_has(13);
  @$pb.TagNumber(14)
  void clearContent() => $_clearField(14);
  @$pb.TagNumber(14)
  $1.Struct ensureContent() => $_ensure(13);
}

class InterventionPayload extends $pb.GeneratedMessage {
  factory InterventionPayload({
    InterventionRequest? request,
  }) {
    final result = create();
    if (request != null) result.request = request;
    return result;
  }

  InterventionPayload._();

  factory InterventionPayload.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionPayload.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionPayload',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOM<InterventionRequest>(1, _omitFieldNames ? '' : 'request',
        subBuilder: InterventionRequest.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionPayload clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionPayload copyWith(void Function(InterventionPayload) updates) =>
      super.copyWith((message) => updates(message as InterventionPayload))
          as InterventionPayload;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionPayload create() => InterventionPayload._();
  @$core.override
  InterventionPayload createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionPayload getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionPayload>(create);
  static InterventionPayload? _defaultInstance;

  @$pb.TagNumber(1)
  InterventionRequest get request => $_getN(0);
  @$pb.TagNumber(1)
  set request(InterventionRequest value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasRequest() => $_has(0);
  @$pb.TagNumber(1)
  void clearRequest() => $_clearField(1);
  @$pb.TagNumber(1)
  InterventionRequest ensureRequest() => $_ensure(0);
}

class AgentStatus extends $pb.GeneratedMessage {
  factory AgentStatus({
    AgentStatus_State? state,
    $core.String? details,
    $core.String? currentAgentName,
    AgentType? activeAgent,
  }) {
    final result = create();
    if (state != null) result.state = state;
    if (details != null) result.details = details;
    if (currentAgentName != null) result.currentAgentName = currentAgentName;
    if (activeAgent != null) result.activeAgent = activeAgent;
    return result;
  }

  AgentStatus._();

  factory AgentStatus.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory AgentStatus.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'AgentStatus',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aE<AgentStatus_State>(1, _omitFieldNames ? '' : 'state',
        enumValues: AgentStatus_State.values)
    ..aOS(2, _omitFieldNames ? '' : 'details')
    ..aOS(3, _omitFieldNames ? '' : 'currentAgentName')
    ..aE<AgentType>(4, _omitFieldNames ? '' : 'activeAgent',
        enumValues: AgentType.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AgentStatus clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AgentStatus copyWith(void Function(AgentStatus) updates) =>
      super.copyWith((message) => updates(message as AgentStatus))
          as AgentStatus;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AgentStatus create() => AgentStatus._();
  @$core.override
  AgentStatus createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static AgentStatus getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<AgentStatus>(create);
  static AgentStatus? _defaultInstance;

  @$pb.TagNumber(1)
  AgentStatus_State get state => $_getN(0);
  @$pb.TagNumber(1)
  set state(AgentStatus_State value) => $_setField(1, value);
  @$pb.TagNumber(1)
  $core.bool hasState() => $_has(0);
  @$pb.TagNumber(1)
  void clearState() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get details => $_getSZ(1);
  @$pb.TagNumber(2)
  set details($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDetails() => $_has(1);
  @$pb.TagNumber(2)
  void clearDetails() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get currentAgentName => $_getSZ(2);
  @$pb.TagNumber(3)
  set currentAgentName($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasCurrentAgentName() => $_has(2);
  @$pb.TagNumber(3)
  void clearCurrentAgentName() => $_clearField(3);

  @$pb.TagNumber(4)
  AgentType get activeAgent => $_getN(3);
  @$pb.TagNumber(4)
  set activeAgent(AgentType value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasActiveAgent() => $_has(3);
  @$pb.TagNumber(4)
  void clearActiveAgent() => $_clearField(4);
}

class Error extends $pb.GeneratedMessage {
  factory Error({
    $core.String? code,
    $core.String? message,
    $core.bool? retryable,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? details,
  }) {
    final result = create();
    if (code != null) result.code = code;
    if (message != null) result.message = message;
    if (retryable != null) result.retryable = retryable;
    if (details != null) result.details.addEntries(details);
    return result;
  }

  Error._();

  factory Error.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Error.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Error',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'code')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOB(3, _omitFieldNames ? '' : 'retryable')
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'details',
        entryClassName: 'Error.DetailsEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Error clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Error copyWith(void Function(Error) updates) =>
      super.copyWith((message) => updates(message as Error)) as Error;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Error create() => Error._();
  @$core.override
  Error createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Error getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Error>(create);
  static Error? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get code => $_getSZ(0);
  @$pb.TagNumber(1)
  set code($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasCode() => $_has(0);
  @$pb.TagNumber(1)
  void clearCode() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.bool get retryable => $_getBF(2);
  @$pb.TagNumber(3)
  set retryable($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasRetryable() => $_has(2);
  @$pb.TagNumber(3)
  void clearRetryable() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbMap<$core.String, $core.String> get details => $_getMap(3);
}

class Usage extends $pb.GeneratedMessage {
  factory Usage({
    $core.int? promptTokens,
    $core.int? completionTokens,
    $core.int? totalTokens,
    $fixnum.Int64? costMicroUsd,
  }) {
    final result = create();
    if (promptTokens != null) result.promptTokens = promptTokens;
    if (completionTokens != null) result.completionTokens = completionTokens;
    if (totalTokens != null) result.totalTokens = totalTokens;
    if (costMicroUsd != null) result.costMicroUsd = costMicroUsd;
    return result;
  }

  Usage._();

  factory Usage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Usage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Usage',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'promptTokens')
    ..aI(2, _omitFieldNames ? '' : 'completionTokens')
    ..aI(3, _omitFieldNames ? '' : 'totalTokens')
    ..aInt64(4, _omitFieldNames ? '' : 'costMicroUsd')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Usage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Usage copyWith(void Function(Usage) updates) =>
      super.copyWith((message) => updates(message as Usage)) as Usage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Usage create() => Usage._();
  @$core.override
  Usage createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Usage getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Usage>(create);
  static Usage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get promptTokens => $_getIZ(0);
  @$pb.TagNumber(1)
  set promptTokens($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasPromptTokens() => $_has(0);
  @$pb.TagNumber(1)
  void clearPromptTokens() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get completionTokens => $_getIZ(1);
  @$pb.TagNumber(2)
  set completionTokens($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasCompletionTokens() => $_has(1);
  @$pb.TagNumber(2)
  void clearCompletionTokens() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get totalTokens => $_getIZ(2);
  @$pb.TagNumber(3)
  set totalTokens($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTotalTokens() => $_has(2);
  @$pb.TagNumber(3)
  void clearTotalTokens() => $_clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get costMicroUsd => $_getI64(3);
  @$pb.TagNumber(4)
  set costMicroUsd($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCostMicroUsd() => $_has(3);
  @$pb.TagNumber(4)
  void clearCostMicroUsd() => $_clearField(4);
}

class MemoryQuery extends $pb.GeneratedMessage {
  factory MemoryQuery({
    $core.String? userId,
    $core.String? queryText,
    $core.int? limit,
    $core.double? minScore,
    MemoryFilter? filter,
    $core.double? hybridAlpha,
  }) {
    final result = create();
    if (userId != null) result.userId = userId;
    if (queryText != null) result.queryText = queryText;
    if (limit != null) result.limit = limit;
    if (minScore != null) result.minScore = minScore;
    if (filter != null) result.filter = filter;
    if (hybridAlpha != null) result.hybridAlpha = hybridAlpha;
    return result;
  }

  MemoryQuery._();

  factory MemoryQuery.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MemoryQuery.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MemoryQuery',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'queryText')
    ..aI(3, _omitFieldNames ? '' : 'limit')
    ..aD(4, _omitFieldNames ? '' : 'minScore', fieldType: $pb.PbFieldType.OF)
    ..aOM<MemoryFilter>(5, _omitFieldNames ? '' : 'filter',
        subBuilder: MemoryFilter.create)
    ..aD(6, _omitFieldNames ? '' : 'hybridAlpha', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryQuery clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryQuery copyWith(void Function(MemoryQuery) updates) =>
      super.copyWith((message) => updates(message as MemoryQuery))
          as MemoryQuery;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryQuery create() => MemoryQuery._();
  @$core.override
  MemoryQuery createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MemoryQuery getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MemoryQuery>(create);
  static MemoryQuery? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get queryText => $_getSZ(1);
  @$pb.TagNumber(2)
  set queryText($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasQueryText() => $_has(1);
  @$pb.TagNumber(2)
  void clearQueryText() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get limit => $_getIZ(2);
  @$pb.TagNumber(3)
  set limit($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLimit() => $_has(2);
  @$pb.TagNumber(3)
  void clearLimit() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.double get minScore => $_getN(3);
  @$pb.TagNumber(4)
  set minScore($core.double value) => $_setFloat(3, value);
  @$pb.TagNumber(4)
  $core.bool hasMinScore() => $_has(3);
  @$pb.TagNumber(4)
  void clearMinScore() => $_clearField(4);

  @$pb.TagNumber(5)
  MemoryFilter get filter => $_getN(4);
  @$pb.TagNumber(5)
  set filter(MemoryFilter value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasFilter() => $_has(4);
  @$pb.TagNumber(5)
  void clearFilter() => $_clearField(5);
  @$pb.TagNumber(5)
  MemoryFilter ensureFilter() => $_ensure(4);

  /// Hybrid search parameter.
  /// 0.0 = Keyword Search (BM25)
  /// 1.0 = Vector Search (Dense)
  /// 0.5 = Hybrid
  @$pb.TagNumber(6)
  $core.double get hybridAlpha => $_getN(5);
  @$pb.TagNumber(6)
  set hybridAlpha($core.double value) => $_setFloat(5, value);
  @$pb.TagNumber(6)
  $core.bool hasHybridAlpha() => $_has(5);
  @$pb.TagNumber(6)
  void clearHybridAlpha() => $_clearField(6);
}

class MemoryFilter extends $pb.GeneratedMessage {
  factory MemoryFilter({
    $core.Iterable<$core.String>? tags,
    $2.Timestamp? startTime,
    $2.Timestamp? endTime,
    $core.Iterable<$core.String>? sourceTypes,
  }) {
    final result = create();
    if (tags != null) result.tags.addAll(tags);
    if (startTime != null) result.startTime = startTime;
    if (endTime != null) result.endTime = endTime;
    if (sourceTypes != null) result.sourceTypes.addAll(sourceTypes);
    return result;
  }

  MemoryFilter._();

  factory MemoryFilter.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MemoryFilter.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MemoryFilter',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..pPS(1, _omitFieldNames ? '' : 'tags')
    ..aOM<$2.Timestamp>(2, _omitFieldNames ? '' : 'startTime',
        subBuilder: $2.Timestamp.create)
    ..aOM<$2.Timestamp>(3, _omitFieldNames ? '' : 'endTime',
        subBuilder: $2.Timestamp.create)
    ..pPS(4, _omitFieldNames ? '' : 'sourceTypes')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryFilter clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryFilter copyWith(void Function(MemoryFilter) updates) =>
      super.copyWith((message) => updates(message as MemoryFilter))
          as MemoryFilter;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryFilter create() => MemoryFilter._();
  @$core.override
  MemoryFilter createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MemoryFilter getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MemoryFilter>(create);
  static MemoryFilter? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<$core.String> get tags => $_getList(0);

  @$pb.TagNumber(2)
  $2.Timestamp get startTime => $_getN(1);
  @$pb.TagNumber(2)
  set startTime($2.Timestamp value) => $_setField(2, value);
  @$pb.TagNumber(2)
  $core.bool hasStartTime() => $_has(1);
  @$pb.TagNumber(2)
  void clearStartTime() => $_clearField(2);
  @$pb.TagNumber(2)
  $2.Timestamp ensureStartTime() => $_ensure(1);

  @$pb.TagNumber(3)
  $2.Timestamp get endTime => $_getN(2);
  @$pb.TagNumber(3)
  set endTime($2.Timestamp value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasEndTime() => $_has(2);
  @$pb.TagNumber(3)
  void clearEndTime() => $_clearField(3);
  @$pb.TagNumber(3)
  $2.Timestamp ensureEndTime() => $_ensure(2);

  @$pb.TagNumber(4)
  $pb.PbList<$core.String> get sourceTypes => $_getList(3);
}

class MemoryResult extends $pb.GeneratedMessage {
  factory MemoryResult({
    $core.Iterable<MemoryItem>? items,
    $core.int? totalFound,
  }) {
    final result = create();
    if (items != null) result.items.addAll(items);
    if (totalFound != null) result.totalFound = totalFound;
    return result;
  }

  MemoryResult._();

  factory MemoryResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MemoryResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MemoryResult',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..pPM<MemoryItem>(1, _omitFieldNames ? '' : 'items',
        subBuilder: MemoryItem.create)
    ..aI(2, _omitFieldNames ? '' : 'totalFound')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryResult copyWith(void Function(MemoryResult) updates) =>
      super.copyWith((message) => updates(message as MemoryResult))
          as MemoryResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryResult create() => MemoryResult._();
  @$core.override
  MemoryResult createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MemoryResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MemoryResult>(create);
  static MemoryResult? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<MemoryItem> get items => $_getList(0);

  @$pb.TagNumber(2)
  $core.int get totalFound => $_getIZ(1);
  @$pb.TagNumber(2)
  set totalFound($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTotalFound() => $_has(1);
  @$pb.TagNumber(2)
  void clearTotalFound() => $_clearField(2);
}

class MemoryItem extends $pb.GeneratedMessage {
  factory MemoryItem({
    $core.String? id,
    $core.String? content,
    $core.double? score,
    $2.Timestamp? createdAt,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (content != null) result.content = content;
    if (score != null) result.score = score;
    if (createdAt != null) result.createdAt = createdAt;
    if (metadata != null) result.metadata.addEntries(metadata);
    return result;
  }

  MemoryItem._();

  factory MemoryItem.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MemoryItem.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MemoryItem',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aD(3, _omitFieldNames ? '' : 'score', fieldType: $pb.PbFieldType.OF)
    ..aOM<$2.Timestamp>(4, _omitFieldNames ? '' : 'createdAt',
        subBuilder: $2.Timestamp.create)
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'MemoryItem.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryItem clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MemoryItem copyWith(void Function(MemoryItem) updates) =>
      super.copyWith((message) => updates(message as MemoryItem)) as MemoryItem;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryItem create() => MemoryItem._();
  @$core.override
  MemoryItem createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MemoryItem getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MemoryItem>(create);
  static MemoryItem? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.double get score => $_getN(2);
  @$pb.TagNumber(3)
  set score($core.double value) => $_setFloat(2, value);
  @$pb.TagNumber(3)
  $core.bool hasScore() => $_has(2);
  @$pb.TagNumber(3)
  void clearScore() => $_clearField(3);

  @$pb.TagNumber(4)
  $2.Timestamp get createdAt => $_getN(3);
  @$pb.TagNumber(4)
  set createdAt($2.Timestamp value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasCreatedAt() => $_has(3);
  @$pb.TagNumber(4)
  void clearCreatedAt() => $_clearField(4);
  @$pb.TagNumber(4)
  $2.Timestamp ensureCreatedAt() => $_ensure(3);

  @$pb.TagNumber(5)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(4);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
