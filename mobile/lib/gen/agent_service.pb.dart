//
//  Generated code. Do not modify.
//  source: agent_service.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'agent_service.pbenum.dart';
import 'google/protobuf/struct.pb.dart' as $4;
import 'google/protobuf/timestamp.pb.dart' as $5;

export 'agent_service.pbenum.dart';

enum ChatRequest_Input {
  message, 
  toolResult, 
  notSet
}

/// ChatRequest encapsulates the user's input and necessary context for the AI.
class ChatRequest extends $pb.GeneratedMessage {
  factory ChatRequest({
    $core.String? userId,
    $core.String? sessionId,
    $core.String? message,
    UserProfile? userProfile,
    $4.Struct? extraContext,
    $core.Iterable<ChatMessage>? history,
    ToolResult? toolResult,
    ChatConfig? config,
    $core.String? requestId,
    $core.Iterable<$core.String>? fileIds,
    $core.bool? includeReferences,
    $core.Iterable<$core.String>? activeTools,
    $core.String? chatMode,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (message != null) {
      $result.message = message;
    }
    if (userProfile != null) {
      $result.userProfile = userProfile;
    }
    if (extraContext != null) {
      $result.extraContext = extraContext;
    }
    if (history != null) {
      $result.history.addAll(history);
    }
    if (toolResult != null) {
      $result.toolResult = toolResult;
    }
    if (config != null) {
      $result.config = config;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (fileIds != null) {
      $result.fileIds.addAll(fileIds);
    }
    if (includeReferences != null) {
      $result.includeReferences = includeReferences;
    }
    if (activeTools != null) {
      $result.activeTools.addAll(activeTools);
    }
    if (chatMode != null) {
      $result.chatMode = chatMode;
    }
    return $result;
  }
  ChatRequest._() : super();
  factory ChatRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static const $core.Map<$core.int, ChatRequest_Input> _ChatRequest_InputByTag = {
    3 : ChatRequest_Input.message,
    7 : ChatRequest_Input.toolResult,
    0 : ChatRequest_Input.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..oo(0, [3, 7])
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'sessionId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..aOM<UserProfile>(4, _omitFieldNames ? '' : 'userProfile', subBuilder: UserProfile.create)
    ..aOM<$4.Struct>(5, _omitFieldNames ? '' : 'extraContext', subBuilder: $4.Struct.create)
    ..pc<ChatMessage>(6, _omitFieldNames ? '' : 'history', $pb.PbFieldType.PM, subBuilder: ChatMessage.create)
    ..aOM<ToolResult>(7, _omitFieldNames ? '' : 'toolResult', subBuilder: ToolResult.create)
    ..aOM<ChatConfig>(8, _omitFieldNames ? '' : 'config', subBuilder: ChatConfig.create)
    ..aOS(9, _omitFieldNames ? '' : 'requestId')
    ..pPS(10, _omitFieldNames ? '' : 'fileIds')
    ..aOB(11, _omitFieldNames ? '' : 'includeReferences')
    ..pPS(12, _omitFieldNames ? '' : 'activeTools')
    ..aOS(13, _omitFieldNames ? '' : 'chatMode')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatRequest clone() => ChatRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatRequest copyWith(void Function(ChatRequest) updates) => super.copyWith((message) => updates(message as ChatRequest)) as ChatRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatRequest create() => ChatRequest._();
  ChatRequest createEmptyInstance() => create();
  static $pb.PbList<ChatRequest> createRepeated() => $pb.PbList<ChatRequest>();
  @$core.pragma('dart2js:noInline')
  static ChatRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatRequest>(create);
  static ChatRequest? _defaultInstance;

  ChatRequest_Input whichInput() => _ChatRequest_InputByTag[$_whichOneof(0)]!;
  void clearInput() => clearField($_whichOneof(0));

  /// Unique identifier of the user interacting with the agent.
  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  /// Session ID to track the conversation thread.
  /// If empty, the agent may treat it as a new stateless interaction or generate a new session.
  @$pb.TagNumber(2)
  $core.String get sessionId => $_getSZ(1);
  @$pb.TagNumber(2)
  set sessionId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasSessionId() => $_has(1);
  @$pb.TagNumber(2)
  void clearSessionId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => clearField(3);

  /// Core user profile context (Strongly Typed).
  /// This data is usually fetched from the primary DB by the Gateway.
  @$pb.TagNumber(4)
  UserProfile get userProfile => $_getN(3);
  @$pb.TagNumber(4)
  set userProfile(UserProfile v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasUserProfile() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserProfile() => clearField(4);
  @$pb.TagNumber(4)
  UserProfile ensureUserProfile() => $_ensure(3);

  /// Extra dynamic context (Flexible).
  /// Used for temporary or extension data (e.g. "current_weather", "frontend_version").
  @$pb.TagNumber(5)
  $4.Struct get extraContext => $_getN(4);
  @$pb.TagNumber(5)
  set extraContext($4.Struct v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasExtraContext() => $_has(4);
  @$pb.TagNumber(5)
  void clearExtraContext() => clearField(5);
  @$pb.TagNumber(5)
  $4.Struct ensureExtraContext() => $_ensure(4);

  /// Optional: Recent conversation history if the client/gateway manages state.
  /// This history field is mainly for passing frontend temporary context, or when Session is stateless.
  /// By default, Python should prioritize reading history from the database.
  @$pb.TagNumber(6)
  $core.List<ChatMessage> get history => $_getList(5);

  @$pb.TagNumber(7)
  ToolResult get toolResult => $_getN(6);
  @$pb.TagNumber(7)
  set toolResult(ToolResult v) { setField(7, v); }
  @$pb.TagNumber(7)
  $core.bool hasToolResult() => $_has(6);
  @$pb.TagNumber(7)
  void clearToolResult() => clearField(7);
  @$pb.TagNumber(7)
  ToolResult ensureToolResult() => $_ensure(6);

  /// Configuration for this specific request.
  @$pb.TagNumber(8)
  ChatConfig get config => $_getN(7);
  @$pb.TagNumber(8)
  set config(ChatConfig v) { setField(8, v); }
  @$pb.TagNumber(8)
  $core.bool hasConfig() => $_has(7);
  @$pb.TagNumber(8)
  void clearConfig() => clearField(8);
  @$pb.TagNumber(8)
  ChatConfig ensureConfig() => $_ensure(7);

  /// Unique identifier for this specific request/message (Trace ID).
  @$pb.TagNumber(9)
  $core.String get requestId => $_getSZ(8);
  @$pb.TagNumber(9)
  set requestId($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasRequestId() => $_has(8);
  @$pb.TagNumber(9)
  void clearRequestId() => clearField(9);

  /// Optional: document IDs to scope RAG retrieval to specific files.
  @$pb.TagNumber(10)
  $core.List<$core.String> get fileIds => $_getList(9);

  /// Optional: include document references in streaming responses.
  @$pb.TagNumber(11)
  $core.bool get includeReferences => $_getBF(10);
  @$pb.TagNumber(11)
  set includeReferences($core.bool v) { $_setBool(10, v); }
  @$pb.TagNumber(11)
  $core.bool hasIncludeReferences() => $_has(10);
  @$pb.TagNumber(11)
  void clearIncludeReferences() => clearField(11);

  /// Optional: List of tools currently active/available for this request
  @$pb.TagNumber(12)
  $core.List<$core.String> get activeTools => $_getList(11);

  /// Chat mode for AI collaboration strategy.
  /// Values: "standard" (default), "deep_analysis", "study_plan", "error_diagnosis"
  @$pb.TagNumber(13)
  $core.String get chatMode => $_getSZ(12);
  @$pb.TagNumber(13)
  set chatMode($core.String v) { $_setString(12, v); }
  @$pb.TagNumber(13)
  $core.bool hasChatMode() => $_has(12);
  @$pb.TagNumber(13)
  void clearChatMode() => clearField(13);
}

/// UserProfile defines key user attributes for personalization.
class UserProfile extends $pb.GeneratedMessage {
  factory UserProfile({
    $core.String? nickname,
    $core.String? timezone,
    $core.String? language,
    $core.bool? isPro,
    $core.Map<$core.String, $core.String>? preferences,
    $core.String? extraContext,
    $core.int? level,
    $core.String? avatarUrl,
  }) {
    final $result = create();
    if (nickname != null) {
      $result.nickname = nickname;
    }
    if (timezone != null) {
      $result.timezone = timezone;
    }
    if (language != null) {
      $result.language = language;
    }
    if (isPro != null) {
      $result.isPro = isPro;
    }
    if (preferences != null) {
      $result.preferences.addAll(preferences);
    }
    if (extraContext != null) {
      $result.extraContext = extraContext;
    }
    if (level != null) {
      $result.level = level;
    }
    if (avatarUrl != null) {
      $result.avatarUrl = avatarUrl;
    }
    return $result;
  }
  UserProfile._() : super();
  factory UserProfile.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory UserProfile.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'UserProfile', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nickname')
    ..aOS(2, _omitFieldNames ? '' : 'timezone')
    ..aOS(3, _omitFieldNames ? '' : 'language')
    ..aOB(4, _omitFieldNames ? '' : 'isPro')
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'preferences', entryClassName: 'UserProfile.PreferencesEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..aOS(6, _omitFieldNames ? '' : 'extraContext')
    ..a<$core.int>(7, _omitFieldNames ? '' : 'level', $pb.PbFieldType.O3)
    ..aOS(8, _omitFieldNames ? '' : 'avatarUrl')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  UserProfile clone() => UserProfile()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  UserProfile copyWith(void Function(UserProfile) updates) => super.copyWith((message) => updates(message as UserProfile)) as UserProfile;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UserProfile create() => UserProfile._();
  UserProfile createEmptyInstance() => create();
  static $pb.PbList<UserProfile> createRepeated() => $pb.PbList<UserProfile>();
  @$core.pragma('dart2js:noInline')
  static UserProfile getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<UserProfile>(create);
  static UserProfile? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get nickname => $_getSZ(0);
  @$pb.TagNumber(1)
  set nickname($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasNickname() => $_has(0);
  @$pb.TagNumber(1)
  void clearNickname() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get timezone => $_getSZ(1);
  @$pb.TagNumber(2)
  set timezone($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTimezone() => $_has(1);
  @$pb.TagNumber(2)
  void clearTimezone() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get language => $_getSZ(2);
  @$pb.TagNumber(3)
  set language($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasLanguage() => $_has(2);
  @$pb.TagNumber(3)
  void clearLanguage() => clearField(3);

  /// Pro status might determine access to advanced models or tools.
  @$pb.TagNumber(4)
  $core.bool get isPro => $_getBF(3);
  @$pb.TagNumber(4)
  set isPro($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasIsPro() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsPro() => clearField(4);

  /// Dynamic preferences (e.g., "concise_mode", "role_play_enabled")
  @$pb.TagNumber(5)
  $core.Map<$core.String, $core.String> get preferences => $_getMap(4);

  /// P0: Extra context (JSON string) containing user state for context propagation
  /// Includes pending_tasks, active_plans, focus_stats, recent_progress (set by Go Gateway)
  @$pb.TagNumber(6)
  $core.String get extraContext => $_getSZ(5);
  @$pb.TagNumber(6)
  set extraContext($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasExtraContext() => $_has(5);
  @$pb.TagNumber(6)
  void clearExtraContext() => clearField(6);

  /// User level/experience
  @$pb.TagNumber(7)
  $core.int get level => $_getIZ(6);
  @$pb.TagNumber(7)
  set level($core.int v) { $_setSignedInt32(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasLevel() => $_has(6);
  @$pb.TagNumber(7)
  void clearLevel() => clearField(7);

  /// URL to user's avatar image
  @$pb.TagNumber(8)
  $core.String get avatarUrl => $_getSZ(7);
  @$pb.TagNumber(8)
  set avatarUrl($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasAvatarUrl() => $_has(7);
  @$pb.TagNumber(8)
  void clearAvatarUrl() => clearField(8);
}

/// Request to get user profile
class ProfileRequest extends $pb.GeneratedMessage {
  factory ProfileRequest({
    $core.String? userId,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    return $result;
  }
  ProfileRequest._() : super();
  factory ProfileRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ProfileRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ProfileRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ProfileRequest clone() => ProfileRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ProfileRequest copyWith(void Function(ProfileRequest) updates) => super.copyWith((message) => updates(message as ProfileRequest)) as ProfileRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ProfileRequest create() => ProfileRequest._();
  ProfileRequest createEmptyInstance() => create();
  static $pb.PbList<ProfileRequest> createRepeated() => $pb.PbList<ProfileRequest>();
  @$core.pragma('dart2js:noInline')
  static ProfileRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ProfileRequest>(create);
  static ProfileRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);
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

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'WeeklyReportRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
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

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'WeeklyReport', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
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

/// ToolResult represents the output of a tool execution performed by the Client/Gateway.
class ToolResult extends $pb.GeneratedMessage {
  factory ToolResult({
    $core.String? toolCallId,
    $core.String? toolName,
    $core.String? resultJson,
    $core.bool? isError,
    $core.String? errorMessage,
  }) {
    final $result = create();
    if (toolCallId != null) {
      $result.toolCallId = toolCallId;
    }
    if (toolName != null) {
      $result.toolName = toolName;
    }
    if (resultJson != null) {
      $result.resultJson = resultJson;
    }
    if (isError != null) {
      $result.isError = isError;
    }
    if (errorMessage != null) {
      $result.errorMessage = errorMessage;
    }
    return $result;
  }
  ToolResult._() : super();
  factory ToolResult.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ToolResult.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ToolResult', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'toolCallId')
    ..aOS(2, _omitFieldNames ? '' : 'toolName')
    ..aOS(3, _omitFieldNames ? '' : 'resultJson')
    ..aOB(4, _omitFieldNames ? '' : 'isError')
    ..aOS(5, _omitFieldNames ? '' : 'errorMessage')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ToolResult clone() => ToolResult()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ToolResult copyWith(void Function(ToolResult) updates) => super.copyWith((message) => updates(message as ToolResult)) as ToolResult;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolResult create() => ToolResult._();
  ToolResult createEmptyInstance() => create();
  static $pb.PbList<ToolResult> createRepeated() => $pb.PbList<ToolResult>();
  @$core.pragma('dart2js:noInline')
  static ToolResult getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ToolResult>(create);
  static ToolResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get toolCallId => $_getSZ(0);
  @$pb.TagNumber(1)
  set toolCallId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasToolCallId() => $_has(0);
  @$pb.TagNumber(1)
  void clearToolCallId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get toolName => $_getSZ(1);
  @$pb.TagNumber(2)
  set toolName($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasToolName() => $_has(1);
  @$pb.TagNumber(2)
  void clearToolName() => clearField(2);

  /// The result payload, typically JSON.
  @$pb.TagNumber(3)
  $core.String get resultJson => $_getSZ(2);
  @$pb.TagNumber(3)
  set resultJson($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasResultJson() => $_has(2);
  @$pb.TagNumber(3)
  void clearResultJson() => clearField(3);

  @$pb.TagNumber(4)
  $core.bool get isError => $_getBF(3);
  @$pb.TagNumber(4)
  set isError($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasIsError() => $_has(3);
  @$pb.TagNumber(4)
  void clearIsError() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get errorMessage => $_getSZ(4);
  @$pb.TagNumber(5)
  set errorMessage($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasErrorMessage() => $_has(4);
  @$pb.TagNumber(5)
  void clearErrorMessage() => clearField(5);
}

/// ChatConfig allows overriding default behaviors for a specific request.
class ChatConfig extends $pb.GeneratedMessage {
  factory ChatConfig({
    $core.String? model,
    $core.double? temperature,
    $core.int? maxTokens,
    $core.bool? toolsEnabled,
  }) {
    final $result = create();
    if (model != null) {
      $result.model = model;
    }
    if (temperature != null) {
      $result.temperature = temperature;
    }
    if (maxTokens != null) {
      $result.maxTokens = maxTokens;
    }
    if (toolsEnabled != null) {
      $result.toolsEnabled = toolsEnabled;
    }
    return $result;
  }
  ChatConfig._() : super();
  factory ChatConfig.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatConfig.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatConfig', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'model')
    ..a<$core.double>(2, _omitFieldNames ? '' : 'temperature', $pb.PbFieldType.OF)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'maxTokens', $pb.PbFieldType.O3)
    ..aOB(4, _omitFieldNames ? '' : 'toolsEnabled')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatConfig clone() => ChatConfig()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatConfig copyWith(void Function(ChatConfig) updates) => super.copyWith((message) => updates(message as ChatConfig)) as ChatConfig;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatConfig create() => ChatConfig._();
  ChatConfig createEmptyInstance() => create();
  static $pb.PbList<ChatConfig> createRepeated() => $pb.PbList<ChatConfig>();
  @$core.pragma('dart2js:noInline')
  static ChatConfig getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatConfig>(create);
  static ChatConfig? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get model => $_getSZ(0);
  @$pb.TagNumber(1)
  set model($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasModel() => $_has(0);
  @$pb.TagNumber(1)
  void clearModel() => clearField(1);

  @$pb.TagNumber(2)
  $core.double get temperature => $_getN(1);
  @$pb.TagNumber(2)
  set temperature($core.double v) { $_setFloat(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTemperature() => $_has(1);
  @$pb.TagNumber(2)
  void clearTemperature() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get maxTokens => $_getIZ(2);
  @$pb.TagNumber(3)
  set maxTokens($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMaxTokens() => $_has(2);
  @$pb.TagNumber(3)
  void clearMaxTokens() => clearField(3);

  @$pb.TagNumber(4)
  $core.bool get toolsEnabled => $_getBF(3);
  @$pb.TagNumber(4)
  set toolsEnabled($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasToolsEnabled() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolsEnabled() => clearField(4);
}

/// ChatMessage represents a single message in the conversation history.
class ChatMessage extends $pb.GeneratedMessage {
  factory ChatMessage({
    $core.String? role,
    $core.String? content,
    $core.String? name,
    $core.String? toolCallId,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (role != null) {
      $result.role = role;
    }
    if (content != null) {
      $result.content = content;
    }
    if (name != null) {
      $result.name = name;
    }
    if (toolCallId != null) {
      $result.toolCallId = toolCallId;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  ChatMessage._() : super();
  factory ChatMessage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatMessage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatMessage', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'role')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..aOS(3, _omitFieldNames ? '' : 'name')
    ..aOS(4, _omitFieldNames ? '' : 'toolCallId')
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'metadata', entryClassName: 'ChatMessage.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatMessage clone() => ChatMessage()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatMessage copyWith(void Function(ChatMessage) updates) => super.copyWith((message) => updates(message as ChatMessage)) as ChatMessage;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatMessage create() => ChatMessage._();
  ChatMessage createEmptyInstance() => create();
  static $pb.PbList<ChatMessage> createRepeated() => $pb.PbList<ChatMessage>();
  @$core.pragma('dart2js:noInline')
  static ChatMessage getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatMessage>(create);
  static ChatMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get role => $_getSZ(0);
  @$pb.TagNumber(1)
  set role($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasRole() => $_has(0);
  @$pb.TagNumber(1)
  void clearRole() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get name => $_getSZ(2);
  @$pb.TagNumber(3)
  set name($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasName() => $_has(2);
  @$pb.TagNumber(3)
  void clearName() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get toolCallId => $_getSZ(3);
  @$pb.TagNumber(4)
  set toolCallId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasToolCallId() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolCallId() => clearField(4);

  @$pb.TagNumber(5)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(4);
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
    $core.String? traceId,
    $core.String? workflowId,
    $core.String? promptVersion,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (responseId != null) {
      $result.responseId = responseId;
    }
    if (createdAt != null) {
      $result.createdAt = createdAt;
    }
    if (delta != null) {
      $result.delta = delta;
    }
    if (toolCall != null) {
      $result.toolCall = toolCall;
    }
    if (statusUpdate != null) {
      $result.statusUpdate = statusUpdate;
    }
    if (fullText != null) {
      $result.fullText = fullText;
    }
    if (error != null) {
      $result.error = error;
    }
    if (usage != null) {
      $result.usage = usage;
    }
    if (finishReason != null) {
      $result.finishReason = finishReason;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (citations != null) {
      $result.citations = citations;
    }
    if (toolResult != null) {
      $result.toolResult = toolResult;
    }
    if (timestamp != null) {
      $result.timestamp = timestamp;
    }
    if (intervention != null) {
      $result.intervention = intervention;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (workflowId != null) {
      $result.workflowId = workflowId;
    }
    if (promptVersion != null) {
      $result.promptVersion = promptVersion;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  ChatResponse._() : super();
  factory ChatResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static const $core.Map<$core.int, ChatResponse_Content> _ChatResponse_ContentByTag = {
    3 : ChatResponse_Content.delta,
    4 : ChatResponse_Content.toolCall,
    5 : ChatResponse_Content.statusUpdate,
    6 : ChatResponse_Content.fullText,
    7 : ChatResponse_Content.error,
    8 : ChatResponse_Content.usage,
    11 : ChatResponse_Content.citations,
    12 : ChatResponse_Content.toolResult,
    14 : ChatResponse_Content.intervention,
    0 : ChatResponse_Content.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..oo(0, [3, 4, 5, 6, 7, 8, 11, 12, 14])
    ..aOS(1, _omitFieldNames ? '' : 'responseId')
    ..aInt64(2, _omitFieldNames ? '' : 'createdAt')
    ..aOS(3, _omitFieldNames ? '' : 'delta')
    ..aOM<ToolCall>(4, _omitFieldNames ? '' : 'toolCall', subBuilder: ToolCall.create)
    ..aOM<AgentStatus>(5, _omitFieldNames ? '' : 'statusUpdate', subBuilder: AgentStatus.create)
    ..aOS(6, _omitFieldNames ? '' : 'fullText')
    ..aOM<Error>(7, _omitFieldNames ? '' : 'error', subBuilder: Error.create)
    ..aOM<Usage>(8, _omitFieldNames ? '' : 'usage', subBuilder: Usage.create)
    ..e<FinishReason>(9, _omitFieldNames ? '' : 'finishReason', $pb.PbFieldType.OE, defaultOrMaker: FinishReason.NULL, valueOf: FinishReason.valueOf, enumValues: FinishReason.values)
    ..aOS(10, _omitFieldNames ? '' : 'requestId')
    ..aOM<CitationBlock>(11, _omitFieldNames ? '' : 'citations', subBuilder: CitationBlock.create)
    ..aOM<ToolResultPayload>(12, _omitFieldNames ? '' : 'toolResult', subBuilder: ToolResultPayload.create)
    ..aInt64(13, _omitFieldNames ? '' : 'timestamp')
    ..aOM<InterventionPayload>(14, _omitFieldNames ? '' : 'intervention', subBuilder: InterventionPayload.create)
    ..aOS(15, _omitFieldNames ? '' : 'traceId')
    ..aOS(16, _omitFieldNames ? '' : 'workflowId')
    ..aOS(17, _omitFieldNames ? '' : 'promptVersion')
    ..m<$core.String, $core.String>(18, _omitFieldNames ? '' : 'metadata', entryClassName: 'ChatResponse.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ChatResponse clone() => ChatResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ChatResponse copyWith(void Function(ChatResponse) updates) => super.copyWith((message) => updates(message as ChatResponse)) as ChatResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ChatResponse create() => ChatResponse._();
  ChatResponse createEmptyInstance() => create();
  static $pb.PbList<ChatResponse> createRepeated() => $pb.PbList<ChatResponse>();
  @$core.pragma('dart2js:noInline')
  static ChatResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ChatResponse>(create);
  static ChatResponse? _defaultInstance;

  ChatResponse_Content whichContent() => _ChatResponse_ContentByTag[$_whichOneof(0)]!;
  void clearContent() => clearField($_whichOneof(0));

  @$pb.TagNumber(1)
  $core.String get responseId => $_getSZ(0);
  @$pb.TagNumber(1)
  set responseId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasResponseId() => $_has(0);
  @$pb.TagNumber(1)
  void clearResponseId() => clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get createdAt => $_getI64(1);
  @$pb.TagNumber(2)
  set createdAt($fixnum.Int64 v) { $_setInt64(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasCreatedAt() => $_has(1);
  @$pb.TagNumber(2)
  void clearCreatedAt() => clearField(2);

  /// Text delta for the typewriter effect.
  @$pb.TagNumber(3)
  $core.String get delta => $_getSZ(2);
  @$pb.TagNumber(3)
  set delta($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasDelta() => $_has(2);
  @$pb.TagNumber(3)
  void clearDelta() => clearField(3);

  /// Request for the client/gateway to execute a tool.
  /// Note: If the model supports parallel function calling, multiple ToolCall frames may be streamed.
  @$pb.TagNumber(4)
  ToolCall get toolCall => $_getN(3);
  @$pb.TagNumber(4)
  set toolCall(ToolCall v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasToolCall() => $_has(3);
  @$pb.TagNumber(4)
  void clearToolCall() => clearField(4);
  @$pb.TagNumber(4)
  ToolCall ensureToolCall() => $_ensure(3);

  /// Log message for internal agent actions/thoughts.
  @$pb.TagNumber(5)
  AgentStatus get statusUpdate => $_getN(4);
  @$pb.TagNumber(5)
  set statusUpdate(AgentStatus v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasStatusUpdate() => $_has(4);
  @$pb.TagNumber(5)
  void clearStatusUpdate() => clearField(5);
  @$pb.TagNumber(5)
  AgentStatus ensureStatusUpdate() => $_ensure(4);

  /// Final complete response text.
  @$pb.TagNumber(6)
  $core.String get fullText => $_getSZ(5);
  @$pb.TagNumber(6)
  set fullText($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasFullText() => $_has(5);
  @$pb.TagNumber(6)
  void clearFullText() => clearField(6);

  /// Error information.
  @$pb.TagNumber(7)
  Error get error => $_getN(6);
  @$pb.TagNumber(7)
  set error(Error v) { setField(7, v); }
  @$pb.TagNumber(7)
  $core.bool hasError() => $_has(6);
  @$pb.TagNumber(7)
  void clearError() => clearField(7);
  @$pb.TagNumber(7)
  Error ensureError() => $_ensure(6);

  /// Usage statistics.
  @$pb.TagNumber(8)
  Usage get usage => $_getN(7);
  @$pb.TagNumber(8)
  set usage(Usage v) { setField(8, v); }
  @$pb.TagNumber(8)
  $core.bool hasUsage() => $_has(7);
  @$pb.TagNumber(8)
  void clearUsage() => clearField(8);
  @$pb.TagNumber(8)
  Usage ensureUsage() => $_ensure(7);

  /// Indicates why the generation finished.
  @$pb.TagNumber(9)
  FinishReason get finishReason => $_getN(8);
  @$pb.TagNumber(9)
  set finishReason(FinishReason v) { setField(9, v); }
  @$pb.TagNumber(9)
  $core.bool hasFinishReason() => $_has(8);
  @$pb.TagNumber(9)
  void clearFinishReason() => clearField(9);

  /// The ID of the request that triggered this response (for tracing).
  @$pb.TagNumber(10)
  $core.String get requestId => $_getSZ(9);
  @$pb.TagNumber(10)
  set requestId($core.String v) { $_setString(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasRequestId() => $_has(9);
  @$pb.TagNumber(10)
  void clearRequestId() => clearField(10);

  /// Citations from RAG.
  @$pb.TagNumber(11)
  CitationBlock get citations => $_getN(10);
  @$pb.TagNumber(11)
  set citations(CitationBlock v) { setField(11, v); }
  @$pb.TagNumber(11)
  $core.bool hasCitations() => $_has(10);
  @$pb.TagNumber(11)
  void clearCitations() => clearField(11);
  @$pb.TagNumber(11)
  CitationBlock ensureCitations() => $_ensure(10);

  /// Tool execution result (for UI rendering).
  @$pb.TagNumber(12)
  ToolResultPayload get toolResult => $_getN(11);
  @$pb.TagNumber(12)
  set toolResult(ToolResultPayload v) { setField(12, v); }
  @$pb.TagNumber(12)
  $core.bool hasToolResult() => $_has(11);
  @$pb.TagNumber(12)
  void clearToolResult() => clearField(12);
  @$pb.TagNumber(12)
  ToolResultPayload ensureToolResult() => $_ensure(11);

  /// Timestamp of response generation
  @$pb.TagNumber(13)
  $fixnum.Int64 get timestamp => $_getI64(12);
  @$pb.TagNumber(13)
  set timestamp($fixnum.Int64 v) { $_setInt64(12, v); }
  @$pb.TagNumber(13)
  $core.bool hasTimestamp() => $_has(12);
  @$pb.TagNumber(13)
  void clearTimestamp() => clearField(13);

  /// Intervention payload (contract-based UI).
  @$pb.TagNumber(14)
  InterventionPayload get intervention => $_getN(13);
  @$pb.TagNumber(14)
  set intervention(InterventionPayload v) { setField(14, v); }
  @$pb.TagNumber(14)
  $core.bool hasIntervention() => $_has(13);
  @$pb.TagNumber(14)
  void clearIntervention() => clearField(14);
  @$pb.TagNumber(14)
  InterventionPayload ensureIntervention() => $_ensure(13);

  /// Trace ID for end-to-end logging correlation.
  @$pb.TagNumber(15)
  $core.String get traceId => $_getSZ(14);
  @$pb.TagNumber(15)
  set traceId($core.String v) { $_setString(14, v); }
  @$pb.TagNumber(15)
  $core.bool hasTraceId() => $_has(14);
  @$pb.TagNumber(15)
  void clearTraceId() => clearField(15);

  /// Workflow identifier for this response.
  @$pb.TagNumber(16)
  $core.String get workflowId => $_getSZ(15);
  @$pb.TagNumber(16)
  set workflowId($core.String v) { $_setString(15, v); }
  @$pb.TagNumber(16)
  $core.bool hasWorkflowId() => $_has(15);
  @$pb.TagNumber(16)
  void clearWorkflowId() => clearField(16);

  /// Prompt version used to generate this response.
  @$pb.TagNumber(17)
  $core.String get promptVersion => $_getSZ(16);
  @$pb.TagNumber(17)
  set promptVersion($core.String v) { $_setString(16, v); }
  @$pb.TagNumber(17)
  $core.bool hasPromptVersion() => $_has(16);
  @$pb.TagNumber(17)
  void clearPromptVersion() => clearField(17);

  /// Additional response metadata (e.g., preference version).
  @$pb.TagNumber(18)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(17);
}

class ResponseFeedbackRequest extends $pb.GeneratedMessage {
  factory ResponseFeedbackRequest({
    $core.String? userId,
    $core.String? responseId,
    $core.String? traceId,
    FeedbackType? feedbackType,
    $core.Iterable<FeedbackReason>? reasons,
    $core.String? freeText,
    $core.String? workflowId,
    $core.String? promptVersion,
    $core.Map<$core.String, $core.String>? meta,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (responseId != null) {
      $result.responseId = responseId;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (feedbackType != null) {
      $result.feedbackType = feedbackType;
    }
    if (reasons != null) {
      $result.reasons.addAll(reasons);
    }
    if (freeText != null) {
      $result.freeText = freeText;
    }
    if (workflowId != null) {
      $result.workflowId = workflowId;
    }
    if (promptVersion != null) {
      $result.promptVersion = promptVersion;
    }
    if (meta != null) {
      $result.meta.addAll(meta);
    }
    return $result;
  }
  ResponseFeedbackRequest._() : super();
  factory ResponseFeedbackRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ResponseFeedbackRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ResponseFeedbackRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'responseId')
    ..aOS(3, _omitFieldNames ? '' : 'traceId')
    ..e<FeedbackType>(4, _omitFieldNames ? '' : 'feedbackType', $pb.PbFieldType.OE, defaultOrMaker: FeedbackType.FEEDBACK_TYPE_UP, valueOf: FeedbackType.valueOf, enumValues: FeedbackType.values)
    ..pc<FeedbackReason>(5, _omitFieldNames ? '' : 'reasons', $pb.PbFieldType.KE, valueOf: FeedbackReason.valueOf, enumValues: FeedbackReason.values, defaultEnumValue: FeedbackReason.FEEDBACK_REASON_UNSPECIFIED)
    ..aOS(6, _omitFieldNames ? '' : 'freeText')
    ..aOS(7, _omitFieldNames ? '' : 'workflowId')
    ..aOS(8, _omitFieldNames ? '' : 'promptVersion')
    ..m<$core.String, $core.String>(9, _omitFieldNames ? '' : 'meta', entryClassName: 'ResponseFeedbackRequest.MetaEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ResponseFeedbackRequest clone() => ResponseFeedbackRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ResponseFeedbackRequest copyWith(void Function(ResponseFeedbackRequest) updates) => super.copyWith((message) => updates(message as ResponseFeedbackRequest)) as ResponseFeedbackRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ResponseFeedbackRequest create() => ResponseFeedbackRequest._();
  ResponseFeedbackRequest createEmptyInstance() => create();
  static $pb.PbList<ResponseFeedbackRequest> createRepeated() => $pb.PbList<ResponseFeedbackRequest>();
  @$core.pragma('dart2js:noInline')
  static ResponseFeedbackRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ResponseFeedbackRequest>(create);
  static ResponseFeedbackRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get responseId => $_getSZ(1);
  @$pb.TagNumber(2)
  set responseId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasResponseId() => $_has(1);
  @$pb.TagNumber(2)
  void clearResponseId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get traceId => $_getSZ(2);
  @$pb.TagNumber(3)
  set traceId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTraceId() => $_has(2);
  @$pb.TagNumber(3)
  void clearTraceId() => clearField(3);

  @$pb.TagNumber(4)
  FeedbackType get feedbackType => $_getN(3);
  @$pb.TagNumber(4)
  set feedbackType(FeedbackType v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasFeedbackType() => $_has(3);
  @$pb.TagNumber(4)
  void clearFeedbackType() => clearField(4);

  @$pb.TagNumber(5)
  $core.List<FeedbackReason> get reasons => $_getList(4);

  @$pb.TagNumber(6)
  $core.String get freeText => $_getSZ(5);
  @$pb.TagNumber(6)
  set freeText($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasFreeText() => $_has(5);
  @$pb.TagNumber(6)
  void clearFreeText() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get workflowId => $_getSZ(6);
  @$pb.TagNumber(7)
  set workflowId($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasWorkflowId() => $_has(6);
  @$pb.TagNumber(7)
  void clearWorkflowId() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get promptVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set promptVersion($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasPromptVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearPromptVersion() => clearField(8);

  @$pb.TagNumber(9)
  $core.Map<$core.String, $core.String> get meta => $_getMap(8);
}

class ResponseFeedbackResponse extends $pb.GeneratedMessage {
  factory ResponseFeedbackResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? responseId,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (message != null) {
      $result.message = message;
    }
    if (responseId != null) {
      $result.responseId = responseId;
    }
    return $result;
  }
  ResponseFeedbackResponse._() : super();
  factory ResponseFeedbackResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ResponseFeedbackResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ResponseFeedbackResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'responseId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ResponseFeedbackResponse clone() => ResponseFeedbackResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ResponseFeedbackResponse copyWith(void Function(ResponseFeedbackResponse) updates) => super.copyWith((message) => updates(message as ResponseFeedbackResponse)) as ResponseFeedbackResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ResponseFeedbackResponse create() => ResponseFeedbackResponse._();
  ResponseFeedbackResponse createEmptyInstance() => create();
  static $pb.PbList<ResponseFeedbackResponse> createRepeated() => $pb.PbList<ResponseFeedbackResponse>();
  @$core.pragma('dart2js:noInline')
  static ResponseFeedbackResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ResponseFeedbackResponse>(create);
  static ResponseFeedbackResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get responseId => $_getSZ(2);
  @$pb.TagNumber(3)
  set responseId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasResponseId() => $_has(2);
  @$pb.TagNumber(3)
  void clearResponseId() => clearField(3);
}

class PlanReviewRequest extends $pb.GeneratedMessage {
  factory PlanReviewRequest({
    $core.String? userId,
    $core.String? planId,
    $core.String? reviewId,
    PlanReviewDecision? decision,
    $core.String? userComment,
    $core.String? traceId,
    $core.String? workflowId,
    $core.String? promptVersion,
    $core.Map<$core.String, $core.String>? meta,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (planId != null) {
      $result.planId = planId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (decision != null) {
      $result.decision = decision;
    }
    if (userComment != null) {
      $result.userComment = userComment;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (workflowId != null) {
      $result.workflowId = workflowId;
    }
    if (promptVersion != null) {
      $result.promptVersion = promptVersion;
    }
    if (meta != null) {
      $result.meta.addAll(meta);
    }
    return $result;
  }
  PlanReviewRequest._() : super();
  factory PlanReviewRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory PlanReviewRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'PlanReviewRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'planId')
    ..aOS(3, _omitFieldNames ? '' : 'reviewId')
    ..e<PlanReviewDecision>(4, _omitFieldNames ? '' : 'decision', $pb.PbFieldType.OE, defaultOrMaker: PlanReviewDecision.PLAN_REVIEW_DECISION_UNSPECIFIED, valueOf: PlanReviewDecision.valueOf, enumValues: PlanReviewDecision.values)
    ..aOS(5, _omitFieldNames ? '' : 'userComment')
    ..aOS(6, _omitFieldNames ? '' : 'traceId')
    ..aOS(7, _omitFieldNames ? '' : 'workflowId')
    ..aOS(8, _omitFieldNames ? '' : 'promptVersion')
    ..m<$core.String, $core.String>(9, _omitFieldNames ? '' : 'meta', entryClassName: 'PlanReviewRequest.MetaEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  PlanReviewRequest clone() => PlanReviewRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  PlanReviewRequest copyWith(void Function(PlanReviewRequest) updates) => super.copyWith((message) => updates(message as PlanReviewRequest)) as PlanReviewRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static PlanReviewRequest create() => PlanReviewRequest._();
  PlanReviewRequest createEmptyInstance() => create();
  static $pb.PbList<PlanReviewRequest> createRepeated() => $pb.PbList<PlanReviewRequest>();
  @$core.pragma('dart2js:noInline')
  static PlanReviewRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<PlanReviewRequest>(create);
  static PlanReviewRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get planId => $_getSZ(1);
  @$pb.TagNumber(2)
  set planId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasPlanId() => $_has(1);
  @$pb.TagNumber(2)
  void clearPlanId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get reviewId => $_getSZ(2);
  @$pb.TagNumber(3)
  set reviewId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasReviewId() => $_has(2);
  @$pb.TagNumber(3)
  void clearReviewId() => clearField(3);

  @$pb.TagNumber(4)
  PlanReviewDecision get decision => $_getN(3);
  @$pb.TagNumber(4)
  set decision(PlanReviewDecision v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasDecision() => $_has(3);
  @$pb.TagNumber(4)
  void clearDecision() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get userComment => $_getSZ(4);
  @$pb.TagNumber(5)
  set userComment($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasUserComment() => $_has(4);
  @$pb.TagNumber(5)
  void clearUserComment() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get traceId => $_getSZ(5);
  @$pb.TagNumber(6)
  set traceId($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasTraceId() => $_has(5);
  @$pb.TagNumber(6)
  void clearTraceId() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get workflowId => $_getSZ(6);
  @$pb.TagNumber(7)
  set workflowId($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasWorkflowId() => $_has(6);
  @$pb.TagNumber(7)
  void clearWorkflowId() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get promptVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set promptVersion($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasPromptVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearPromptVersion() => clearField(8);

  @$pb.TagNumber(9)
  $core.Map<$core.String, $core.String> get meta => $_getMap(8);
}

class PlanReviewResponse extends $pb.GeneratedMessage {
  factory PlanReviewResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? reviewId,
    $core.String? updatedPlanId,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (message != null) {
      $result.message = message;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (updatedPlanId != null) {
      $result.updatedPlanId = updatedPlanId;
    }
    return $result;
  }
  PlanReviewResponse._() : super();
  factory PlanReviewResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory PlanReviewResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'PlanReviewResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'reviewId')
    ..aOS(4, _omitFieldNames ? '' : 'updatedPlanId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  PlanReviewResponse clone() => PlanReviewResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  PlanReviewResponse copyWith(void Function(PlanReviewResponse) updates) => super.copyWith((message) => updates(message as PlanReviewResponse)) as PlanReviewResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static PlanReviewResponse create() => PlanReviewResponse._();
  PlanReviewResponse createEmptyInstance() => create();
  static $pb.PbList<PlanReviewResponse> createRepeated() => $pb.PbList<PlanReviewResponse>();
  @$core.pragma('dart2js:noInline')
  static PlanReviewResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<PlanReviewResponse>(create);
  static PlanReviewResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get reviewId => $_getSZ(2);
  @$pb.TagNumber(3)
  set reviewId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasReviewId() => $_has(2);
  @$pb.TagNumber(3)
  void clearReviewId() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get updatedPlanId => $_getSZ(3);
  @$pb.TagNumber(4)
  set updatedPlanId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasUpdatedPlanId() => $_has(3);
  @$pb.TagNumber(4)
  void clearUpdatedPlanId() => clearField(4);
}

class ContentReviewFeedbackRequest extends $pb.GeneratedMessage {
  factory ContentReviewFeedbackRequest({
    $core.String? userId,
    $core.String? reviewId,
    $core.String? responseId,
    ContentReviewFeedbackType? feedbackType,
    $core.int? rating,
    $core.String? comment,
    $core.Iterable<$core.String>? issuesReported,
    $core.String? sessionId,
    $core.Map<$core.String, $core.String>? meta,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (responseId != null) {
      $result.responseId = responseId;
    }
    if (feedbackType != null) {
      $result.feedbackType = feedbackType;
    }
    if (rating != null) {
      $result.rating = rating;
    }
    if (comment != null) {
      $result.comment = comment;
    }
    if (issuesReported != null) {
      $result.issuesReported.addAll(issuesReported);
    }
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (meta != null) {
      $result.meta.addAll(meta);
    }
    return $result;
  }
  ContentReviewFeedbackRequest._() : super();
  factory ContentReviewFeedbackRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ContentReviewFeedbackRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ContentReviewFeedbackRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'reviewId')
    ..aOS(3, _omitFieldNames ? '' : 'responseId')
    ..e<ContentReviewFeedbackType>(4, _omitFieldNames ? '' : 'feedbackType', $pb.PbFieldType.OE, defaultOrMaker: ContentReviewFeedbackType.SATISFIED, valueOf: ContentReviewFeedbackType.valueOf, enumValues: ContentReviewFeedbackType.values)
    ..a<$core.int>(5, _omitFieldNames ? '' : 'rating', $pb.PbFieldType.O3)
    ..aOS(6, _omitFieldNames ? '' : 'comment')
    ..pPS(7, _omitFieldNames ? '' : 'issuesReported')
    ..aOS(8, _omitFieldNames ? '' : 'sessionId')
    ..m<$core.String, $core.String>(9, _omitFieldNames ? '' : 'meta', entryClassName: 'ContentReviewFeedbackRequest.MetaEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ContentReviewFeedbackRequest clone() => ContentReviewFeedbackRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ContentReviewFeedbackRequest copyWith(void Function(ContentReviewFeedbackRequest) updates) => super.copyWith((message) => updates(message as ContentReviewFeedbackRequest)) as ContentReviewFeedbackRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContentReviewFeedbackRequest create() => ContentReviewFeedbackRequest._();
  ContentReviewFeedbackRequest createEmptyInstance() => create();
  static $pb.PbList<ContentReviewFeedbackRequest> createRepeated() => $pb.PbList<ContentReviewFeedbackRequest>();
  @$core.pragma('dart2js:noInline')
  static ContentReviewFeedbackRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ContentReviewFeedbackRequest>(create);
  static ContentReviewFeedbackRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get reviewId => $_getSZ(1);
  @$pb.TagNumber(2)
  set reviewId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasReviewId() => $_has(1);
  @$pb.TagNumber(2)
  void clearReviewId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get responseId => $_getSZ(2);
  @$pb.TagNumber(3)
  set responseId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasResponseId() => $_has(2);
  @$pb.TagNumber(3)
  void clearResponseId() => clearField(3);

  @$pb.TagNumber(4)
  ContentReviewFeedbackType get feedbackType => $_getN(3);
  @$pb.TagNumber(4)
  set feedbackType(ContentReviewFeedbackType v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasFeedbackType() => $_has(3);
  @$pb.TagNumber(4)
  void clearFeedbackType() => clearField(4);

  @$pb.TagNumber(5)
  $core.int get rating => $_getIZ(4);
  @$pb.TagNumber(5)
  set rating($core.int v) { $_setSignedInt32(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasRating() => $_has(4);
  @$pb.TagNumber(5)
  void clearRating() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get comment => $_getSZ(5);
  @$pb.TagNumber(6)
  set comment($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasComment() => $_has(5);
  @$pb.TagNumber(6)
  void clearComment() => clearField(6);

  @$pb.TagNumber(7)
  $core.List<$core.String> get issuesReported => $_getList(6);

  @$pb.TagNumber(8)
  $core.String get sessionId => $_getSZ(7);
  @$pb.TagNumber(8)
  set sessionId($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasSessionId() => $_has(7);
  @$pb.TagNumber(8)
  void clearSessionId() => clearField(8);

  @$pb.TagNumber(9)
  $core.Map<$core.String, $core.String> get meta => $_getMap(8);
}

class ContentReviewFeedbackResponse extends $pb.GeneratedMessage {
  factory ContentReviewFeedbackResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? feedbackId,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (message != null) {
      $result.message = message;
    }
    if (feedbackId != null) {
      $result.feedbackId = feedbackId;
    }
    return $result;
  }
  ContentReviewFeedbackResponse._() : super();
  factory ContentReviewFeedbackResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ContentReviewFeedbackResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ContentReviewFeedbackResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'feedbackId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ContentReviewFeedbackResponse clone() => ContentReviewFeedbackResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ContentReviewFeedbackResponse copyWith(void Function(ContentReviewFeedbackResponse) updates) => super.copyWith((message) => updates(message as ContentReviewFeedbackResponse)) as ContentReviewFeedbackResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ContentReviewFeedbackResponse create() => ContentReviewFeedbackResponse._();
  ContentReviewFeedbackResponse createEmptyInstance() => create();
  static $pb.PbList<ContentReviewFeedbackResponse> createRepeated() => $pb.PbList<ContentReviewFeedbackResponse>();
  @$core.pragma('dart2js:noInline')
  static ContentReviewFeedbackResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ContentReviewFeedbackResponse>(create);
  static ContentReviewFeedbackResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get feedbackId => $_getSZ(2);
  @$pb.TagNumber(3)
  set feedbackId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasFeedbackId() => $_has(2);
  @$pb.TagNumber(3)
  void clearFeedbackId() => clearField(3);
}

/// User overrides review decision
class ReviewOverrideRequest extends $pb.GeneratedMessage {
  factory ReviewOverrideRequest({
    $core.String? userId,
    $core.String? reviewId,
    $core.String? originalDecision,
    $core.String? newDecision,
    $core.String? reason,
    $core.String? sessionId,
    $core.Map<$core.String, $core.String>? meta,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (originalDecision != null) {
      $result.originalDecision = originalDecision;
    }
    if (newDecision != null) {
      $result.newDecision = newDecision;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (meta != null) {
      $result.meta.addAll(meta);
    }
    return $result;
  }
  ReviewOverrideRequest._() : super();
  factory ReviewOverrideRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewOverrideRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewOverrideRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'reviewId')
    ..aOS(3, _omitFieldNames ? '' : 'originalDecision')
    ..aOS(4, _omitFieldNames ? '' : 'newDecision')
    ..aOS(5, _omitFieldNames ? '' : 'reason')
    ..aOS(6, _omitFieldNames ? '' : 'sessionId')
    ..m<$core.String, $core.String>(7, _omitFieldNames ? '' : 'meta', entryClassName: 'ReviewOverrideRequest.MetaEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewOverrideRequest clone() => ReviewOverrideRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewOverrideRequest copyWith(void Function(ReviewOverrideRequest) updates) => super.copyWith((message) => updates(message as ReviewOverrideRequest)) as ReviewOverrideRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewOverrideRequest create() => ReviewOverrideRequest._();
  ReviewOverrideRequest createEmptyInstance() => create();
  static $pb.PbList<ReviewOverrideRequest> createRepeated() => $pb.PbList<ReviewOverrideRequest>();
  @$core.pragma('dart2js:noInline')
  static ReviewOverrideRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewOverrideRequest>(create);
  static ReviewOverrideRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get reviewId => $_getSZ(1);
  @$pb.TagNumber(2)
  set reviewId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasReviewId() => $_has(1);
  @$pb.TagNumber(2)
  void clearReviewId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get originalDecision => $_getSZ(2);
  @$pb.TagNumber(3)
  set originalDecision($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasOriginalDecision() => $_has(2);
  @$pb.TagNumber(3)
  void clearOriginalDecision() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get newDecision => $_getSZ(3);
  @$pb.TagNumber(4)
  set newDecision($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasNewDecision() => $_has(3);
  @$pb.TagNumber(4)
  void clearNewDecision() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get reason => $_getSZ(4);
  @$pb.TagNumber(5)
  set reason($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasReason() => $_has(4);
  @$pb.TagNumber(5)
  void clearReason() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get sessionId => $_getSZ(5);
  @$pb.TagNumber(6)
  set sessionId($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasSessionId() => $_has(5);
  @$pb.TagNumber(6)
  void clearSessionId() => clearField(6);

  @$pb.TagNumber(7)
  $core.Map<$core.String, $core.String> get meta => $_getMap(6);
}

class ReviewOverrideResponse extends $pb.GeneratedMessage {
  factory ReviewOverrideResponse({
    $core.bool? success,
    $core.String? message,
    $core.String? overrideId,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (message != null) {
      $result.message = message;
    }
    if (overrideId != null) {
      $result.overrideId = overrideId;
    }
    return $result;
  }
  ReviewOverrideResponse._() : super();
  factory ReviewOverrideResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewOverrideResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewOverrideResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOS(3, _omitFieldNames ? '' : 'overrideId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewOverrideResponse clone() => ReviewOverrideResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewOverrideResponse copyWith(void Function(ReviewOverrideResponse) updates) => super.copyWith((message) => updates(message as ReviewOverrideResponse)) as ReviewOverrideResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewOverrideResponse create() => ReviewOverrideResponse._();
  ReviewOverrideResponse createEmptyInstance() => create();
  static $pb.PbList<ReviewOverrideResponse> createRepeated() => $pb.PbList<ReviewOverrideResponse>();
  @$core.pragma('dart2js:noInline')
  static ReviewOverrideResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewOverrideResponse>(create);
  static ReviewOverrideResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get overrideId => $_getSZ(2);
  @$pb.TagNumber(3)
  set overrideId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasOverrideId() => $_has(2);
  @$pb.TagNumber(3)
  void clearOverrideId() => clearField(3);
}

/// User appeals against a review
class ReviewAppealRequest extends $pb.GeneratedMessage {
  factory ReviewAppealRequest({
    $core.String? userId,
    $core.String? reviewId,
    $core.String? appealReason,
    $core.Iterable<$core.String>? issuesWithReview,
    $core.String? sessionId,
    $core.Map<$core.String, $core.String>? meta,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (appealReason != null) {
      $result.appealReason = appealReason;
    }
    if (issuesWithReview != null) {
      $result.issuesWithReview.addAll(issuesWithReview);
    }
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (meta != null) {
      $result.meta.addAll(meta);
    }
    return $result;
  }
  ReviewAppealRequest._() : super();
  factory ReviewAppealRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewAppealRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewAppealRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'reviewId')
    ..aOS(3, _omitFieldNames ? '' : 'appealReason')
    ..pPS(4, _omitFieldNames ? '' : 'issuesWithReview')
    ..aOS(5, _omitFieldNames ? '' : 'sessionId')
    ..m<$core.String, $core.String>(6, _omitFieldNames ? '' : 'meta', entryClassName: 'ReviewAppealRequest.MetaEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewAppealRequest clone() => ReviewAppealRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewAppealRequest copyWith(void Function(ReviewAppealRequest) updates) => super.copyWith((message) => updates(message as ReviewAppealRequest)) as ReviewAppealRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewAppealRequest create() => ReviewAppealRequest._();
  ReviewAppealRequest createEmptyInstance() => create();
  static $pb.PbList<ReviewAppealRequest> createRepeated() => $pb.PbList<ReviewAppealRequest>();
  @$core.pragma('dart2js:noInline')
  static ReviewAppealRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewAppealRequest>(create);
  static ReviewAppealRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get reviewId => $_getSZ(1);
  @$pb.TagNumber(2)
  set reviewId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasReviewId() => $_has(1);
  @$pb.TagNumber(2)
  void clearReviewId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get appealReason => $_getSZ(2);
  @$pb.TagNumber(3)
  set appealReason($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasAppealReason() => $_has(2);
  @$pb.TagNumber(3)
  void clearAppealReason() => clearField(3);

  @$pb.TagNumber(4)
  $core.List<$core.String> get issuesWithReview => $_getList(3);

  @$pb.TagNumber(5)
  $core.String get sessionId => $_getSZ(4);
  @$pb.TagNumber(5)
  set sessionId($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasSessionId() => $_has(4);
  @$pb.TagNumber(5)
  void clearSessionId() => clearField(5);

  @$pb.TagNumber(6)
  $core.Map<$core.String, $core.String> get meta => $_getMap(5);
}

class ReviewAppealResponse extends $pb.GeneratedMessage {
  factory ReviewAppealResponse({
    $core.bool? success,
    $core.String? appealId,
    $core.String? status,
    $core.String? message,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (appealId != null) {
      $result.appealId = appealId;
    }
    if (status != null) {
      $result.status = status;
    }
    if (message != null) {
      $result.message = message;
    }
    return $result;
  }
  ReviewAppealResponse._() : super();
  factory ReviewAppealResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewAppealResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewAppealResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'appealId')
    ..aOS(3, _omitFieldNames ? '' : 'status')
    ..aOS(4, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewAppealResponse clone() => ReviewAppealResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewAppealResponse copyWith(void Function(ReviewAppealResponse) updates) => super.copyWith((message) => updates(message as ReviewAppealResponse)) as ReviewAppealResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewAppealResponse create() => ReviewAppealResponse._();
  ReviewAppealResponse createEmptyInstance() => create();
  static $pb.PbList<ReviewAppealResponse> createRepeated() => $pb.PbList<ReviewAppealResponse>();
  @$core.pragma('dart2js:noInline')
  static ReviewAppealResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewAppealResponse>(create);
  static ReviewAppealResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get appealId => $_getSZ(1);
  @$pb.TagNumber(2)
  set appealId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasAppealId() => $_has(1);
  @$pb.TagNumber(2)
  void clearAppealId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get status => $_getSZ(2);
  @$pb.TagNumber(3)
  set status($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasStatus() => $_has(2);
  @$pb.TagNumber(3)
  void clearStatus() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get message => $_getSZ(3);
  @$pb.TagNumber(4)
  set message($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasMessage() => $_has(3);
  @$pb.TagNumber(4)
  void clearMessage() => clearField(4);
}

/// Get appeal status
class AppealStatusRequest extends $pb.GeneratedMessage {
  factory AppealStatusRequest({
    $core.String? userId,
    $core.String? appealId,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (appealId != null) {
      $result.appealId = appealId;
    }
    return $result;
  }
  AppealStatusRequest._() : super();
  factory AppealStatusRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AppealStatusRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AppealStatusRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'appealId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AppealStatusRequest clone() => AppealStatusRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AppealStatusRequest copyWith(void Function(AppealStatusRequest) updates) => super.copyWith((message) => updates(message as AppealStatusRequest)) as AppealStatusRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AppealStatusRequest create() => AppealStatusRequest._();
  AppealStatusRequest createEmptyInstance() => create();
  static $pb.PbList<AppealStatusRequest> createRepeated() => $pb.PbList<AppealStatusRequest>();
  @$core.pragma('dart2js:noInline')
  static AppealStatusRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AppealStatusRequest>(create);
  static AppealStatusRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get appealId => $_getSZ(1);
  @$pb.TagNumber(2)
  set appealId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasAppealId() => $_has(1);
  @$pb.TagNumber(2)
  void clearAppealId() => clearField(2);
}

class AppealStatusResponse extends $pb.GeneratedMessage {
  factory AppealStatusResponse({
    $core.String? appealId,
    $core.String? reviewId,
    $core.String? status,
    $core.String? submittedAt,
    $core.String? appealReason,
    $core.String? resolution,
    $core.String? resolvedBy,
    $core.String? resolvedAt,
    $core.String? secondaryDecision,
    $core.double? secondaryScore,
  }) {
    final $result = create();
    if (appealId != null) {
      $result.appealId = appealId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (status != null) {
      $result.status = status;
    }
    if (submittedAt != null) {
      $result.submittedAt = submittedAt;
    }
    if (appealReason != null) {
      $result.appealReason = appealReason;
    }
    if (resolution != null) {
      $result.resolution = resolution;
    }
    if (resolvedBy != null) {
      $result.resolvedBy = resolvedBy;
    }
    if (resolvedAt != null) {
      $result.resolvedAt = resolvedAt;
    }
    if (secondaryDecision != null) {
      $result.secondaryDecision = secondaryDecision;
    }
    if (secondaryScore != null) {
      $result.secondaryScore = secondaryScore;
    }
    return $result;
  }
  AppealStatusResponse._() : super();
  factory AppealStatusResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AppealStatusResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AppealStatusResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'appealId')
    ..aOS(2, _omitFieldNames ? '' : 'reviewId')
    ..aOS(3, _omitFieldNames ? '' : 'status')
    ..aOS(4, _omitFieldNames ? '' : 'submittedAt')
    ..aOS(5, _omitFieldNames ? '' : 'appealReason')
    ..aOS(6, _omitFieldNames ? '' : 'resolution')
    ..aOS(7, _omitFieldNames ? '' : 'resolvedBy')
    ..aOS(8, _omitFieldNames ? '' : 'resolvedAt')
    ..aOS(9, _omitFieldNames ? '' : 'secondaryDecision')
    ..a<$core.double>(10, _omitFieldNames ? '' : 'secondaryScore', $pb.PbFieldType.OD)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AppealStatusResponse clone() => AppealStatusResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AppealStatusResponse copyWith(void Function(AppealStatusResponse) updates) => super.copyWith((message) => updates(message as AppealStatusResponse)) as AppealStatusResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AppealStatusResponse create() => AppealStatusResponse._();
  AppealStatusResponse createEmptyInstance() => create();
  static $pb.PbList<AppealStatusResponse> createRepeated() => $pb.PbList<AppealStatusResponse>();
  @$core.pragma('dart2js:noInline')
  static AppealStatusResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AppealStatusResponse>(create);
  static AppealStatusResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get appealId => $_getSZ(0);
  @$pb.TagNumber(1)
  set appealId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasAppealId() => $_has(0);
  @$pb.TagNumber(1)
  void clearAppealId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get reviewId => $_getSZ(1);
  @$pb.TagNumber(2)
  set reviewId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasReviewId() => $_has(1);
  @$pb.TagNumber(2)
  void clearReviewId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get status => $_getSZ(2);
  @$pb.TagNumber(3)
  set status($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasStatus() => $_has(2);
  @$pb.TagNumber(3)
  void clearStatus() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get submittedAt => $_getSZ(3);
  @$pb.TagNumber(4)
  set submittedAt($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasSubmittedAt() => $_has(3);
  @$pb.TagNumber(4)
  void clearSubmittedAt() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get appealReason => $_getSZ(4);
  @$pb.TagNumber(5)
  set appealReason($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasAppealReason() => $_has(4);
  @$pb.TagNumber(5)
  void clearAppealReason() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get resolution => $_getSZ(5);
  @$pb.TagNumber(6)
  set resolution($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasResolution() => $_has(5);
  @$pb.TagNumber(6)
  void clearResolution() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get resolvedBy => $_getSZ(6);
  @$pb.TagNumber(7)
  set resolvedBy($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasResolvedBy() => $_has(6);
  @$pb.TagNumber(7)
  void clearResolvedBy() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get resolvedAt => $_getSZ(7);
  @$pb.TagNumber(8)
  set resolvedAt($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasResolvedAt() => $_has(7);
  @$pb.TagNumber(8)
  void clearResolvedAt() => clearField(8);

  @$pb.TagNumber(9)
  $core.String get secondaryDecision => $_getSZ(8);
  @$pb.TagNumber(9)
  set secondaryDecision($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasSecondaryDecision() => $_has(8);
  @$pb.TagNumber(9)
  void clearSecondaryDecision() => clearField(9);

  @$pb.TagNumber(10)
  $core.double get secondaryScore => $_getN(9);
  @$pb.TagNumber(10)
  set secondaryScore($core.double v) { $_setDouble(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasSecondaryScore() => $_has(9);
  @$pb.TagNumber(10)
  void clearSecondaryScore() => clearField(10);
}

/// ReviewFeedbackRequest - submit feedback on a review
class ReviewFeedbackRequest extends $pb.GeneratedMessage {
  factory ReviewFeedbackRequest({
    $core.String? userId,
    $core.String? reviewId,
    $core.String? feedbackType,
    $core.int? rating,
    $core.bool? wasHelpful,
    $core.bool? wasAccurate,
    $core.Iterable<$core.String>? inaccuratePoints,
    $core.String? specificityLevel,
    $core.String? comments,
    $core.Iterable<$core.String>? tags,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (feedbackType != null) {
      $result.feedbackType = feedbackType;
    }
    if (rating != null) {
      $result.rating = rating;
    }
    if (wasHelpful != null) {
      $result.wasHelpful = wasHelpful;
    }
    if (wasAccurate != null) {
      $result.wasAccurate = wasAccurate;
    }
    if (inaccuratePoints != null) {
      $result.inaccuratePoints.addAll(inaccuratePoints);
    }
    if (specificityLevel != null) {
      $result.specificityLevel = specificityLevel;
    }
    if (comments != null) {
      $result.comments = comments;
    }
    if (tags != null) {
      $result.tags.addAll(tags);
    }
    return $result;
  }
  ReviewFeedbackRequest._() : super();
  factory ReviewFeedbackRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewFeedbackRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewFeedbackRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'reviewId')
    ..aOS(3, _omitFieldNames ? '' : 'feedbackType')
    ..a<$core.int>(4, _omitFieldNames ? '' : 'rating', $pb.PbFieldType.O3)
    ..aOB(5, _omitFieldNames ? '' : 'wasHelpful')
    ..aOB(6, _omitFieldNames ? '' : 'wasAccurate')
    ..pPS(7, _omitFieldNames ? '' : 'inaccuratePoints')
    ..aOS(8, _omitFieldNames ? '' : 'specificityLevel')
    ..aOS(9, _omitFieldNames ? '' : 'comments')
    ..pPS(10, _omitFieldNames ? '' : 'tags')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewFeedbackRequest clone() => ReviewFeedbackRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewFeedbackRequest copyWith(void Function(ReviewFeedbackRequest) updates) => super.copyWith((message) => updates(message as ReviewFeedbackRequest)) as ReviewFeedbackRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewFeedbackRequest create() => ReviewFeedbackRequest._();
  ReviewFeedbackRequest createEmptyInstance() => create();
  static $pb.PbList<ReviewFeedbackRequest> createRepeated() => $pb.PbList<ReviewFeedbackRequest>();
  @$core.pragma('dart2js:noInline')
  static ReviewFeedbackRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewFeedbackRequest>(create);
  static ReviewFeedbackRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get reviewId => $_getSZ(1);
  @$pb.TagNumber(2)
  set reviewId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasReviewId() => $_has(1);
  @$pb.TagNumber(2)
  void clearReviewId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get feedbackType => $_getSZ(2);
  @$pb.TagNumber(3)
  set feedbackType($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasFeedbackType() => $_has(2);
  @$pb.TagNumber(3)
  void clearFeedbackType() => clearField(3);

  /// Rating feedback (1-5)
  @$pb.TagNumber(4)
  $core.int get rating => $_getIZ(3);
  @$pb.TagNumber(4)
  set rating($core.int v) { $_setSignedInt32(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasRating() => $_has(3);
  @$pb.TagNumber(4)
  void clearRating() => clearField(4);

  /// Quality feedback
  @$pb.TagNumber(5)
  $core.bool get wasHelpful => $_getBF(4);
  @$pb.TagNumber(5)
  set wasHelpful($core.bool v) { $_setBool(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasWasHelpful() => $_has(4);
  @$pb.TagNumber(5)
  void clearWasHelpful() => clearField(5);

  /// Accuracy feedback
  @$pb.TagNumber(6)
  $core.bool get wasAccurate => $_getBF(5);
  @$pb.TagNumber(6)
  set wasAccurate($core.bool v) { $_setBool(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasWasAccurate() => $_has(5);
  @$pb.TagNumber(6)
  void clearWasAccurate() => clearField(6);

  @$pb.TagNumber(7)
  $core.List<$core.String> get inaccuratePoints => $_getList(6);

  /// Specificity feedback: too_vague, appropriate, too_detailed
  @$pb.TagNumber(8)
  $core.String get specificityLevel => $_getSZ(7);
  @$pb.TagNumber(8)
  set specificityLevel($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasSpecificityLevel() => $_has(7);
  @$pb.TagNumber(8)
  void clearSpecificityLevel() => clearField(8);

  /// Free-form comments
  @$pb.TagNumber(9)
  $core.String get comments => $_getSZ(8);
  @$pb.TagNumber(9)
  set comments($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasComments() => $_has(8);
  @$pb.TagNumber(9)
  void clearComments() => clearField(9);

  /// Tags
  @$pb.TagNumber(10)
  $core.List<$core.String> get tags => $_getList(9);
}

/// ReviewFeedbackResponse - response to feedback submission
class ReviewFeedbackResponse extends $pb.GeneratedMessage {
  factory ReviewFeedbackResponse({
    $core.bool? success,
    $core.String? feedbackId,
    $core.String? message,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (feedbackId != null) {
      $result.feedbackId = feedbackId;
    }
    if (message != null) {
      $result.message = message;
    }
    return $result;
  }
  ReviewFeedbackResponse._() : super();
  factory ReviewFeedbackResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ReviewFeedbackResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ReviewFeedbackResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'feedbackId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ReviewFeedbackResponse clone() => ReviewFeedbackResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ReviewFeedbackResponse copyWith(void Function(ReviewFeedbackResponse) updates) => super.copyWith((message) => updates(message as ReviewFeedbackResponse)) as ReviewFeedbackResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ReviewFeedbackResponse create() => ReviewFeedbackResponse._();
  ReviewFeedbackResponse createEmptyInstance() => create();
  static $pb.PbList<ReviewFeedbackResponse> createRepeated() => $pb.PbList<ReviewFeedbackResponse>();
  @$core.pragma('dart2js:noInline')
  static ReviewFeedbackResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ReviewFeedbackResponse>(create);
  static ReviewFeedbackResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get feedbackId => $_getSZ(1);
  @$pb.TagNumber(2)
  set feedbackId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasFeedbackId() => $_has(1);
  @$pb.TagNumber(2)
  void clearFeedbackId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => clearField(3);
}

/// RegenerationRequest - request content regeneration
class RegenerationRequest extends $pb.GeneratedMessage {
  factory RegenerationRequest({
    $core.String? userId,
    $core.String? originalContentId,
    $core.String? reviewId,
    $core.String? regenerationType,
    $core.Iterable<$core.String>? improvementHints,
    $core.Iterable<$core.String>? focusAreas,
    $core.String? customInstructions,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (originalContentId != null) {
      $result.originalContentId = originalContentId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (regenerationType != null) {
      $result.regenerationType = regenerationType;
    }
    if (improvementHints != null) {
      $result.improvementHints.addAll(improvementHints);
    }
    if (focusAreas != null) {
      $result.focusAreas.addAll(focusAreas);
    }
    if (customInstructions != null) {
      $result.customInstructions = customInstructions;
    }
    return $result;
  }
  RegenerationRequest._() : super();
  factory RegenerationRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory RegenerationRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'RegenerationRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'originalContentId')
    ..aOS(3, _omitFieldNames ? '' : 'reviewId')
    ..aOS(4, _omitFieldNames ? '' : 'regenerationType')
    ..pPS(5, _omitFieldNames ? '' : 'improvementHints')
    ..pPS(6, _omitFieldNames ? '' : 'focusAreas')
    ..aOS(7, _omitFieldNames ? '' : 'customInstructions')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  RegenerationRequest clone() => RegenerationRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  RegenerationRequest copyWith(void Function(RegenerationRequest) updates) => super.copyWith((message) => updates(message as RegenerationRequest)) as RegenerationRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static RegenerationRequest create() => RegenerationRequest._();
  RegenerationRequest createEmptyInstance() => create();
  static $pb.PbList<RegenerationRequest> createRepeated() => $pb.PbList<RegenerationRequest>();
  @$core.pragma('dart2js:noInline')
  static RegenerationRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<RegenerationRequest>(create);
  static RegenerationRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get originalContentId => $_getSZ(1);
  @$pb.TagNumber(2)
  set originalContentId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasOriginalContentId() => $_has(1);
  @$pb.TagNumber(2)
  void clearOriginalContentId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get reviewId => $_getSZ(2);
  @$pb.TagNumber(3)
  set reviewId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasReviewId() => $_has(2);
  @$pb.TagNumber(3)
  void clearReviewId() => clearField(3);

  /// Regeneration type: improve_quality, fix_issues, change_style, add_details, simplify, custom
  @$pb.TagNumber(4)
  $core.String get regenerationType => $_getSZ(3);
  @$pb.TagNumber(4)
  set regenerationType($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasRegenerationType() => $_has(3);
  @$pb.TagNumber(4)
  void clearRegenerationType() => clearField(4);

  /// Improvement hints
  @$pb.TagNumber(5)
  $core.List<$core.String> get improvementHints => $_getList(4);

  /// Focus areas
  @$pb.TagNumber(6)
  $core.List<$core.String> get focusAreas => $_getList(5);

  /// Custom instructions
  @$pb.TagNumber(7)
  $core.String get customInstructions => $_getSZ(6);
  @$pb.TagNumber(7)
  set customInstructions($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasCustomInstructions() => $_has(6);
  @$pb.TagNumber(7)
  void clearCustomInstructions() => clearField(7);
}

/// RegenerationResponse - response to regeneration request
class RegenerationResponse extends $pb.GeneratedMessage {
  factory RegenerationResponse({
    $core.bool? success,
    $core.String? requestId,
    $core.String? newContent,
    $core.String? newContentId,
    $core.String? improvementSummary,
    $core.Iterable<$core.String>? changesMade,
    $core.double? scoreImprovement,
    $core.int? generationTimeMs,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (newContent != null) {
      $result.newContent = newContent;
    }
    if (newContentId != null) {
      $result.newContentId = newContentId;
    }
    if (improvementSummary != null) {
      $result.improvementSummary = improvementSummary;
    }
    if (changesMade != null) {
      $result.changesMade.addAll(changesMade);
    }
    if (scoreImprovement != null) {
      $result.scoreImprovement = scoreImprovement;
    }
    if (generationTimeMs != null) {
      $result.generationTimeMs = generationTimeMs;
    }
    return $result;
  }
  RegenerationResponse._() : super();
  factory RegenerationResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory RegenerationResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'RegenerationResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'requestId')
    ..aOS(3, _omitFieldNames ? '' : 'newContent')
    ..aOS(4, _omitFieldNames ? '' : 'newContentId')
    ..aOS(5, _omitFieldNames ? '' : 'improvementSummary')
    ..pPS(6, _omitFieldNames ? '' : 'changesMade')
    ..a<$core.double>(7, _omitFieldNames ? '' : 'scoreImprovement', $pb.PbFieldType.OD)
    ..a<$core.int>(8, _omitFieldNames ? '' : 'generationTimeMs', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  RegenerationResponse clone() => RegenerationResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  RegenerationResponse copyWith(void Function(RegenerationResponse) updates) => super.copyWith((message) => updates(message as RegenerationResponse)) as RegenerationResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static RegenerationResponse create() => RegenerationResponse._();
  RegenerationResponse createEmptyInstance() => create();
  static $pb.PbList<RegenerationResponse> createRepeated() => $pb.PbList<RegenerationResponse>();
  @$core.pragma('dart2js:noInline')
  static RegenerationResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<RegenerationResponse>(create);
  static RegenerationResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get requestId => $_getSZ(1);
  @$pb.TagNumber(2)
  set requestId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasRequestId() => $_has(1);
  @$pb.TagNumber(2)
  void clearRequestId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get newContent => $_getSZ(2);
  @$pb.TagNumber(3)
  set newContent($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasNewContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearNewContent() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get newContentId => $_getSZ(3);
  @$pb.TagNumber(4)
  set newContentId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasNewContentId() => $_has(3);
  @$pb.TagNumber(4)
  void clearNewContentId() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get improvementSummary => $_getSZ(4);
  @$pb.TagNumber(5)
  set improvementSummary($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasImprovementSummary() => $_has(4);
  @$pb.TagNumber(5)
  void clearImprovementSummary() => clearField(5);

  @$pb.TagNumber(6)
  $core.List<$core.String> get changesMade => $_getList(5);

  @$pb.TagNumber(7)
  $core.double get scoreImprovement => $_getN(6);
  @$pb.TagNumber(7)
  set scoreImprovement($core.double v) { $_setDouble(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasScoreImprovement() => $_has(6);
  @$pb.TagNumber(7)
  void clearScoreImprovement() => clearField(7);

  @$pb.TagNumber(8)
  $core.int get generationTimeMs => $_getIZ(7);
  @$pb.TagNumber(8)
  set generationTimeMs($core.int v) { $_setSignedInt32(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasGenerationTimeMs() => $_has(7);
  @$pb.TagNumber(8)
  void clearGenerationTimeMs() => clearField(8);
}

/// FeedbackStatisticsRequest - request feedback statistics
class FeedbackStatisticsRequest extends $pb.GeneratedMessage {
  factory FeedbackStatisticsRequest({
    $core.String? userId,
    $core.int? periodDays,
  }) {
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (periodDays != null) {
      $result.periodDays = periodDays;
    }
    return $result;
  }
  FeedbackStatisticsRequest._() : super();
  factory FeedbackStatisticsRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory FeedbackStatisticsRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'FeedbackStatisticsRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..a<$core.int>(2, _omitFieldNames ? '' : 'periodDays', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  FeedbackStatisticsRequest clone() => FeedbackStatisticsRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  FeedbackStatisticsRequest copyWith(void Function(FeedbackStatisticsRequest) updates) => super.copyWith((message) => updates(message as FeedbackStatisticsRequest)) as FeedbackStatisticsRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FeedbackStatisticsRequest create() => FeedbackStatisticsRequest._();
  FeedbackStatisticsRequest createEmptyInstance() => create();
  static $pb.PbList<FeedbackStatisticsRequest> createRepeated() => $pb.PbList<FeedbackStatisticsRequest>();
  @$core.pragma('dart2js:noInline')
  static FeedbackStatisticsRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<FeedbackStatisticsRequest>(create);
  static FeedbackStatisticsRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get periodDays => $_getIZ(1);
  @$pb.TagNumber(2)
  set periodDays($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasPeriodDays() => $_has(1);
  @$pb.TagNumber(2)
  void clearPeriodDays() => clearField(2);
}

/// FeedbackStatisticsResponse - feedback statistics
class FeedbackStatisticsResponse extends $pb.GeneratedMessage {
  factory FeedbackStatisticsResponse({
    $core.int? totalFeedbacks,
    $core.double? avgRating,
    $core.double? helpfulRate,
    $core.double? accuracyRate,
    $core.int? regenerationRequests,
    $core.int? successfulRegenerations,
    $core.int? periodDays,
  }) {
    final $result = create();
    if (totalFeedbacks != null) {
      $result.totalFeedbacks = totalFeedbacks;
    }
    if (avgRating != null) {
      $result.avgRating = avgRating;
    }
    if (helpfulRate != null) {
      $result.helpfulRate = helpfulRate;
    }
    if (accuracyRate != null) {
      $result.accuracyRate = accuracyRate;
    }
    if (regenerationRequests != null) {
      $result.regenerationRequests = regenerationRequests;
    }
    if (successfulRegenerations != null) {
      $result.successfulRegenerations = successfulRegenerations;
    }
    if (periodDays != null) {
      $result.periodDays = periodDays;
    }
    return $result;
  }
  FeedbackStatisticsResponse._() : super();
  factory FeedbackStatisticsResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory FeedbackStatisticsResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'FeedbackStatisticsResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'totalFeedbacks', $pb.PbFieldType.O3)
    ..a<$core.double>(2, _omitFieldNames ? '' : 'avgRating', $pb.PbFieldType.OD)
    ..a<$core.double>(3, _omitFieldNames ? '' : 'helpfulRate', $pb.PbFieldType.OD)
    ..a<$core.double>(4, _omitFieldNames ? '' : 'accuracyRate', $pb.PbFieldType.OD)
    ..a<$core.int>(5, _omitFieldNames ? '' : 'regenerationRequests', $pb.PbFieldType.O3)
    ..a<$core.int>(6, _omitFieldNames ? '' : 'successfulRegenerations', $pb.PbFieldType.O3)
    ..a<$core.int>(7, _omitFieldNames ? '' : 'periodDays', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  FeedbackStatisticsResponse clone() => FeedbackStatisticsResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  FeedbackStatisticsResponse copyWith(void Function(FeedbackStatisticsResponse) updates) => super.copyWith((message) => updates(message as FeedbackStatisticsResponse)) as FeedbackStatisticsResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static FeedbackStatisticsResponse create() => FeedbackStatisticsResponse._();
  FeedbackStatisticsResponse createEmptyInstance() => create();
  static $pb.PbList<FeedbackStatisticsResponse> createRepeated() => $pb.PbList<FeedbackStatisticsResponse>();
  @$core.pragma('dart2js:noInline')
  static FeedbackStatisticsResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<FeedbackStatisticsResponse>(create);
  static FeedbackStatisticsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get totalFeedbacks => $_getIZ(0);
  @$pb.TagNumber(1)
  set totalFeedbacks($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasTotalFeedbacks() => $_has(0);
  @$pb.TagNumber(1)
  void clearTotalFeedbacks() => clearField(1);

  @$pb.TagNumber(2)
  $core.double get avgRating => $_getN(1);
  @$pb.TagNumber(2)
  set avgRating($core.double v) { $_setDouble(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasAvgRating() => $_has(1);
  @$pb.TagNumber(2)
  void clearAvgRating() => clearField(2);

  @$pb.TagNumber(3)
  $core.double get helpfulRate => $_getN(2);
  @$pb.TagNumber(3)
  set helpfulRate($core.double v) { $_setDouble(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasHelpfulRate() => $_has(2);
  @$pb.TagNumber(3)
  void clearHelpfulRate() => clearField(3);

  @$pb.TagNumber(4)
  $core.double get accuracyRate => $_getN(3);
  @$pb.TagNumber(4)
  set accuracyRate($core.double v) { $_setDouble(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasAccuracyRate() => $_has(3);
  @$pb.TagNumber(4)
  void clearAccuracyRate() => clearField(4);

  @$pb.TagNumber(5)
  $core.int get regenerationRequests => $_getIZ(4);
  @$pb.TagNumber(5)
  set regenerationRequests($core.int v) { $_setSignedInt32(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasRegenerationRequests() => $_has(4);
  @$pb.TagNumber(5)
  void clearRegenerationRequests() => clearField(5);

  @$pb.TagNumber(6)
  $core.int get successfulRegenerations => $_getIZ(5);
  @$pb.TagNumber(6)
  set successfulRegenerations($core.int v) { $_setSignedInt32(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasSuccessfulRegenerations() => $_has(5);
  @$pb.TagNumber(6)
  void clearSuccessfulRegenerations() => clearField(6);

  @$pb.TagNumber(7)
  $core.int get periodDays => $_getIZ(6);
  @$pb.TagNumber(7)
  set periodDays($core.int v) { $_setSignedInt32(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasPeriodDays() => $_has(6);
  @$pb.TagNumber(7)
  void clearPeriodDays() => clearField(7);
}

/// GetArbitrationQueueRequest - request arbitration queue
class GetArbitrationQueueRequest extends $pb.GeneratedMessage {
  factory GetArbitrationQueueRequest({
    $core.int? limit,
    $core.String? priorityFilter,
    $core.String? statusFilter,
  }) {
    final $result = create();
    if (limit != null) {
      $result.limit = limit;
    }
    if (priorityFilter != null) {
      $result.priorityFilter = priorityFilter;
    }
    if (statusFilter != null) {
      $result.statusFilter = statusFilter;
    }
    return $result;
  }
  GetArbitrationQueueRequest._() : super();
  factory GetArbitrationQueueRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory GetArbitrationQueueRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'GetArbitrationQueueRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'limit', $pb.PbFieldType.O3)
    ..aOS(2, _omitFieldNames ? '' : 'priorityFilter')
    ..aOS(3, _omitFieldNames ? '' : 'statusFilter')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueRequest clone() => GetArbitrationQueueRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueRequest copyWith(void Function(GetArbitrationQueueRequest) updates) => super.copyWith((message) => updates(message as GetArbitrationQueueRequest)) as GetArbitrationQueueRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueRequest create() => GetArbitrationQueueRequest._();
  GetArbitrationQueueRequest createEmptyInstance() => create();
  static $pb.PbList<GetArbitrationQueueRequest> createRepeated() => $pb.PbList<GetArbitrationQueueRequest>();
  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GetArbitrationQueueRequest>(create);
  static GetArbitrationQueueRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get limit => $_getIZ(0);
  @$pb.TagNumber(1)
  set limit($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasLimit() => $_has(0);
  @$pb.TagNumber(1)
  void clearLimit() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get priorityFilter => $_getSZ(1);
  @$pb.TagNumber(2)
  set priorityFilter($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasPriorityFilter() => $_has(1);
  @$pb.TagNumber(2)
  void clearPriorityFilter() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get statusFilter => $_getSZ(2);
  @$pb.TagNumber(3)
  set statusFilter($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasStatusFilter() => $_has(2);
  @$pb.TagNumber(3)
  void clearStatusFilter() => clearField(3);
}

/// ArbitrationCaseInfo - information about an arbitration case
class ArbitrationCaseInfo extends $pb.GeneratedMessage {
  factory ArbitrationCaseInfo({
    $core.String? caseId,
    $core.String? appealId,
    $core.String? reviewId,
    $core.String? userId,
    $core.String? escalationReason,
    $core.String? priority,
    $core.String? createdAt,
    $core.String? status,
    $core.String? assignedTo,
    $core.String? assignedAt,
    $core.double? originalReviewScore,
    $core.double? secondaryReviewScore,
    $core.double? scoreDiscrepancy,
    $core.String? resolution,
    $core.String? finalDecision,
    $core.String? resolvedAt,
    $core.String? resolvedBy,
    $core.Iterable<$core.String>? notes,
  }) {
    final $result = create();
    if (caseId != null) {
      $result.caseId = caseId;
    }
    if (appealId != null) {
      $result.appealId = appealId;
    }
    if (reviewId != null) {
      $result.reviewId = reviewId;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    if (escalationReason != null) {
      $result.escalationReason = escalationReason;
    }
    if (priority != null) {
      $result.priority = priority;
    }
    if (createdAt != null) {
      $result.createdAt = createdAt;
    }
    if (status != null) {
      $result.status = status;
    }
    if (assignedTo != null) {
      $result.assignedTo = assignedTo;
    }
    if (assignedAt != null) {
      $result.assignedAt = assignedAt;
    }
    if (originalReviewScore != null) {
      $result.originalReviewScore = originalReviewScore;
    }
    if (secondaryReviewScore != null) {
      $result.secondaryReviewScore = secondaryReviewScore;
    }
    if (scoreDiscrepancy != null) {
      $result.scoreDiscrepancy = scoreDiscrepancy;
    }
    if (resolution != null) {
      $result.resolution = resolution;
    }
    if (finalDecision != null) {
      $result.finalDecision = finalDecision;
    }
    if (resolvedAt != null) {
      $result.resolvedAt = resolvedAt;
    }
    if (resolvedBy != null) {
      $result.resolvedBy = resolvedBy;
    }
    if (notes != null) {
      $result.notes.addAll(notes);
    }
    return $result;
  }
  ArbitrationCaseInfo._() : super();
  factory ArbitrationCaseInfo.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ArbitrationCaseInfo.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ArbitrationCaseInfo', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'caseId')
    ..aOS(2, _omitFieldNames ? '' : 'appealId')
    ..aOS(3, _omitFieldNames ? '' : 'reviewId')
    ..aOS(4, _omitFieldNames ? '' : 'userId')
    ..aOS(5, _omitFieldNames ? '' : 'escalationReason')
    ..aOS(6, _omitFieldNames ? '' : 'priority')
    ..aOS(7, _omitFieldNames ? '' : 'createdAt')
    ..aOS(8, _omitFieldNames ? '' : 'status')
    ..aOS(9, _omitFieldNames ? '' : 'assignedTo')
    ..aOS(10, _omitFieldNames ? '' : 'assignedAt')
    ..a<$core.double>(11, _omitFieldNames ? '' : 'originalReviewScore', $pb.PbFieldType.OD)
    ..a<$core.double>(12, _omitFieldNames ? '' : 'secondaryReviewScore', $pb.PbFieldType.OD)
    ..a<$core.double>(13, _omitFieldNames ? '' : 'scoreDiscrepancy', $pb.PbFieldType.OD)
    ..aOS(14, _omitFieldNames ? '' : 'resolution')
    ..aOS(15, _omitFieldNames ? '' : 'finalDecision')
    ..aOS(16, _omitFieldNames ? '' : 'resolvedAt')
    ..aOS(17, _omitFieldNames ? '' : 'resolvedBy')
    ..pPS(18, _omitFieldNames ? '' : 'notes')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ArbitrationCaseInfo clone() => ArbitrationCaseInfo()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ArbitrationCaseInfo copyWith(void Function(ArbitrationCaseInfo) updates) => super.copyWith((message) => updates(message as ArbitrationCaseInfo)) as ArbitrationCaseInfo;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ArbitrationCaseInfo create() => ArbitrationCaseInfo._();
  ArbitrationCaseInfo createEmptyInstance() => create();
  static $pb.PbList<ArbitrationCaseInfo> createRepeated() => $pb.PbList<ArbitrationCaseInfo>();
  @$core.pragma('dart2js:noInline')
  static ArbitrationCaseInfo getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ArbitrationCaseInfo>(create);
  static ArbitrationCaseInfo? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get caseId => $_getSZ(0);
  @$pb.TagNumber(1)
  set caseId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasCaseId() => $_has(0);
  @$pb.TagNumber(1)
  void clearCaseId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get appealId => $_getSZ(1);
  @$pb.TagNumber(2)
  set appealId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasAppealId() => $_has(1);
  @$pb.TagNumber(2)
  void clearAppealId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get reviewId => $_getSZ(2);
  @$pb.TagNumber(3)
  set reviewId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasReviewId() => $_has(2);
  @$pb.TagNumber(3)
  void clearReviewId() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get userId => $_getSZ(3);
  @$pb.TagNumber(4)
  set userId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasUserId() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserId() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get escalationReason => $_getSZ(4);
  @$pb.TagNumber(5)
  set escalationReason($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasEscalationReason() => $_has(4);
  @$pb.TagNumber(5)
  void clearEscalationReason() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get priority => $_getSZ(5);
  @$pb.TagNumber(6)
  set priority($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasPriority() => $_has(5);
  @$pb.TagNumber(6)
  void clearPriority() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get createdAt => $_getSZ(6);
  @$pb.TagNumber(7)
  set createdAt($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasCreatedAt() => $_has(6);
  @$pb.TagNumber(7)
  void clearCreatedAt() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get status => $_getSZ(7);
  @$pb.TagNumber(8)
  set status($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasStatus() => $_has(7);
  @$pb.TagNumber(8)
  void clearStatus() => clearField(8);

  @$pb.TagNumber(9)
  $core.String get assignedTo => $_getSZ(8);
  @$pb.TagNumber(9)
  set assignedTo($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasAssignedTo() => $_has(8);
  @$pb.TagNumber(9)
  void clearAssignedTo() => clearField(9);

  @$pb.TagNumber(10)
  $core.String get assignedAt => $_getSZ(9);
  @$pb.TagNumber(10)
  set assignedAt($core.String v) { $_setString(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasAssignedAt() => $_has(9);
  @$pb.TagNumber(10)
  void clearAssignedAt() => clearField(10);

  @$pb.TagNumber(11)
  $core.double get originalReviewScore => $_getN(10);
  @$pb.TagNumber(11)
  set originalReviewScore($core.double v) { $_setDouble(10, v); }
  @$pb.TagNumber(11)
  $core.bool hasOriginalReviewScore() => $_has(10);
  @$pb.TagNumber(11)
  void clearOriginalReviewScore() => clearField(11);

  @$pb.TagNumber(12)
  $core.double get secondaryReviewScore => $_getN(11);
  @$pb.TagNumber(12)
  set secondaryReviewScore($core.double v) { $_setDouble(11, v); }
  @$pb.TagNumber(12)
  $core.bool hasSecondaryReviewScore() => $_has(11);
  @$pb.TagNumber(12)
  void clearSecondaryReviewScore() => clearField(12);

  @$pb.TagNumber(13)
  $core.double get scoreDiscrepancy => $_getN(12);
  @$pb.TagNumber(13)
  set scoreDiscrepancy($core.double v) { $_setDouble(12, v); }
  @$pb.TagNumber(13)
  $core.bool hasScoreDiscrepancy() => $_has(12);
  @$pb.TagNumber(13)
  void clearScoreDiscrepancy() => clearField(13);

  @$pb.TagNumber(14)
  $core.String get resolution => $_getSZ(13);
  @$pb.TagNumber(14)
  set resolution($core.String v) { $_setString(13, v); }
  @$pb.TagNumber(14)
  $core.bool hasResolution() => $_has(13);
  @$pb.TagNumber(14)
  void clearResolution() => clearField(14);

  @$pb.TagNumber(15)
  $core.String get finalDecision => $_getSZ(14);
  @$pb.TagNumber(15)
  set finalDecision($core.String v) { $_setString(14, v); }
  @$pb.TagNumber(15)
  $core.bool hasFinalDecision() => $_has(14);
  @$pb.TagNumber(15)
  void clearFinalDecision() => clearField(15);

  @$pb.TagNumber(16)
  $core.String get resolvedAt => $_getSZ(15);
  @$pb.TagNumber(16)
  set resolvedAt($core.String v) { $_setString(15, v); }
  @$pb.TagNumber(16)
  $core.bool hasResolvedAt() => $_has(15);
  @$pb.TagNumber(16)
  void clearResolvedAt() => clearField(16);

  @$pb.TagNumber(17)
  $core.String get resolvedBy => $_getSZ(16);
  @$pb.TagNumber(17)
  set resolvedBy($core.String v) { $_setString(16, v); }
  @$pb.TagNumber(17)
  $core.bool hasResolvedBy() => $_has(16);
  @$pb.TagNumber(17)
  void clearResolvedBy() => clearField(17);

  @$pb.TagNumber(18)
  $core.List<$core.String> get notes => $_getList(17);
}

/// GetArbitrationQueueResponse - response with arbitration cases
class GetArbitrationQueueResponse extends $pb.GeneratedMessage {
  factory GetArbitrationQueueResponse({
    $core.Iterable<ArbitrationCaseInfo>? cases,
    $core.int? totalCount,
  }) {
    final $result = create();
    if (cases != null) {
      $result.cases.addAll(cases);
    }
    if (totalCount != null) {
      $result.totalCount = totalCount;
    }
    return $result;
  }
  GetArbitrationQueueResponse._() : super();
  factory GetArbitrationQueueResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory GetArbitrationQueueResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'GetArbitrationQueueResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..pc<ArbitrationCaseInfo>(1, _omitFieldNames ? '' : 'cases', $pb.PbFieldType.PM, subBuilder: ArbitrationCaseInfo.create)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'totalCount', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueResponse clone() => GetArbitrationQueueResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueResponse copyWith(void Function(GetArbitrationQueueResponse) updates) => super.copyWith((message) => updates(message as GetArbitrationQueueResponse)) as GetArbitrationQueueResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueResponse create() => GetArbitrationQueueResponse._();
  GetArbitrationQueueResponse createEmptyInstance() => create();
  static $pb.PbList<GetArbitrationQueueResponse> createRepeated() => $pb.PbList<GetArbitrationQueueResponse>();
  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GetArbitrationQueueResponse>(create);
  static GetArbitrationQueueResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<ArbitrationCaseInfo> get cases => $_getList(0);

  @$pb.TagNumber(2)
  $core.int get totalCount => $_getIZ(1);
  @$pb.TagNumber(2)
  set totalCount($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTotalCount() => $_has(1);
  @$pb.TagNumber(2)
  void clearTotalCount() => clearField(2);
}

/// AssignArbitrationCaseRequest - assign a case to an arbitrator
class AssignArbitrationCaseRequest extends $pb.GeneratedMessage {
  factory AssignArbitrationCaseRequest({
    $core.String? caseId,
    $core.String? arbitratorId,
    $core.String? arbitratorRole,
  }) {
    final $result = create();
    if (caseId != null) {
      $result.caseId = caseId;
    }
    if (arbitratorId != null) {
      $result.arbitratorId = arbitratorId;
    }
    if (arbitratorRole != null) {
      $result.arbitratorRole = arbitratorRole;
    }
    return $result;
  }
  AssignArbitrationCaseRequest._() : super();
  factory AssignArbitrationCaseRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AssignArbitrationCaseRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AssignArbitrationCaseRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'caseId')
    ..aOS(2, _omitFieldNames ? '' : 'arbitratorId')
    ..aOS(3, _omitFieldNames ? '' : 'arbitratorRole')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AssignArbitrationCaseRequest clone() => AssignArbitrationCaseRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AssignArbitrationCaseRequest copyWith(void Function(AssignArbitrationCaseRequest) updates) => super.copyWith((message) => updates(message as AssignArbitrationCaseRequest)) as AssignArbitrationCaseRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AssignArbitrationCaseRequest create() => AssignArbitrationCaseRequest._();
  AssignArbitrationCaseRequest createEmptyInstance() => create();
  static $pb.PbList<AssignArbitrationCaseRequest> createRepeated() => $pb.PbList<AssignArbitrationCaseRequest>();
  @$core.pragma('dart2js:noInline')
  static AssignArbitrationCaseRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AssignArbitrationCaseRequest>(create);
  static AssignArbitrationCaseRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get caseId => $_getSZ(0);
  @$pb.TagNumber(1)
  set caseId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasCaseId() => $_has(0);
  @$pb.TagNumber(1)
  void clearCaseId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get arbitratorId => $_getSZ(1);
  @$pb.TagNumber(2)
  set arbitratorId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasArbitratorId() => $_has(1);
  @$pb.TagNumber(2)
  void clearArbitratorId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get arbitratorRole => $_getSZ(2);
  @$pb.TagNumber(3)
  set arbitratorRole($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasArbitratorRole() => $_has(2);
  @$pb.TagNumber(3)
  void clearArbitratorRole() => clearField(3);
}

/// AssignArbitrationCaseResponse - response to case assignment
class AssignArbitrationCaseResponse extends $pb.GeneratedMessage {
  factory AssignArbitrationCaseResponse({
    $core.bool? success,
    $core.String? message,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (message != null) {
      $result.message = message;
    }
    return $result;
  }
  AssignArbitrationCaseResponse._() : super();
  factory AssignArbitrationCaseResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AssignArbitrationCaseResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AssignArbitrationCaseResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AssignArbitrationCaseResponse clone() => AssignArbitrationCaseResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AssignArbitrationCaseResponse copyWith(void Function(AssignArbitrationCaseResponse) updates) => super.copyWith((message) => updates(message as AssignArbitrationCaseResponse)) as AssignArbitrationCaseResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AssignArbitrationCaseResponse create() => AssignArbitrationCaseResponse._();
  AssignArbitrationCaseResponse createEmptyInstance() => create();
  static $pb.PbList<AssignArbitrationCaseResponse> createRepeated() => $pb.PbList<AssignArbitrationCaseResponse>();
  @$core.pragma('dart2js:noInline')
  static AssignArbitrationCaseResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AssignArbitrationCaseResponse>(create);
  static AssignArbitrationCaseResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);
}

/// SubmitArbitrationDecisionRequest - submit an arbitration decision
class SubmitArbitrationDecisionRequest extends $pb.GeneratedMessage {
  factory SubmitArbitrationDecisionRequest({
    $core.String? caseId,
    $core.String? decision,
    $core.String? explanation,
    $core.String? arbitratorId,
    $core.String? arbitratorRole,
    $core.String? feedbackForModel,
  }) {
    final $result = create();
    if (caseId != null) {
      $result.caseId = caseId;
    }
    if (decision != null) {
      $result.decision = decision;
    }
    if (explanation != null) {
      $result.explanation = explanation;
    }
    if (arbitratorId != null) {
      $result.arbitratorId = arbitratorId;
    }
    if (arbitratorRole != null) {
      $result.arbitratorRole = arbitratorRole;
    }
    if (feedbackForModel != null) {
      $result.feedbackForModel = feedbackForModel;
    }
    return $result;
  }
  SubmitArbitrationDecisionRequest._() : super();
  factory SubmitArbitrationDecisionRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory SubmitArbitrationDecisionRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'SubmitArbitrationDecisionRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'caseId')
    ..aOS(2, _omitFieldNames ? '' : 'decision')
    ..aOS(3, _omitFieldNames ? '' : 'explanation')
    ..aOS(4, _omitFieldNames ? '' : 'arbitratorId')
    ..aOS(5, _omitFieldNames ? '' : 'arbitratorRole')
    ..aOS(6, _omitFieldNames ? '' : 'feedbackForModel')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  SubmitArbitrationDecisionRequest clone() => SubmitArbitrationDecisionRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  SubmitArbitrationDecisionRequest copyWith(void Function(SubmitArbitrationDecisionRequest) updates) => super.copyWith((message) => updates(message as SubmitArbitrationDecisionRequest)) as SubmitArbitrationDecisionRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SubmitArbitrationDecisionRequest create() => SubmitArbitrationDecisionRequest._();
  SubmitArbitrationDecisionRequest createEmptyInstance() => create();
  static $pb.PbList<SubmitArbitrationDecisionRequest> createRepeated() => $pb.PbList<SubmitArbitrationDecisionRequest>();
  @$core.pragma('dart2js:noInline')
  static SubmitArbitrationDecisionRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<SubmitArbitrationDecisionRequest>(create);
  static SubmitArbitrationDecisionRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get caseId => $_getSZ(0);
  @$pb.TagNumber(1)
  set caseId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasCaseId() => $_has(0);
  @$pb.TagNumber(1)
  void clearCaseId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get decision => $_getSZ(1);
  @$pb.TagNumber(2)
  set decision($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDecision() => $_has(1);
  @$pb.TagNumber(2)
  void clearDecision() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get explanation => $_getSZ(2);
  @$pb.TagNumber(3)
  set explanation($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasExplanation() => $_has(2);
  @$pb.TagNumber(3)
  void clearExplanation() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get arbitratorId => $_getSZ(3);
  @$pb.TagNumber(4)
  set arbitratorId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasArbitratorId() => $_has(3);
  @$pb.TagNumber(4)
  void clearArbitratorId() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get arbitratorRole => $_getSZ(4);
  @$pb.TagNumber(5)
  set arbitratorRole($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasArbitratorRole() => $_has(4);
  @$pb.TagNumber(5)
  void clearArbitratorRole() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get feedbackForModel => $_getSZ(5);
  @$pb.TagNumber(6)
  set feedbackForModel($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasFeedbackForModel() => $_has(5);
  @$pb.TagNumber(6)
  void clearFeedbackForModel() => clearField(6);
}

/// SubmitArbitrationDecisionResponse - response to decision submission
class SubmitArbitrationDecisionResponse extends $pb.GeneratedMessage {
  factory SubmitArbitrationDecisionResponse({
    $core.bool? success,
    $core.String? decisionId,
    $core.String? message,
  }) {
    final $result = create();
    if (success != null) {
      $result.success = success;
    }
    if (decisionId != null) {
      $result.decisionId = decisionId;
    }
    if (message != null) {
      $result.message = message;
    }
    return $result;
  }
  SubmitArbitrationDecisionResponse._() : super();
  factory SubmitArbitrationDecisionResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory SubmitArbitrationDecisionResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'SubmitArbitrationDecisionResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'success')
    ..aOS(2, _omitFieldNames ? '' : 'decisionId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  SubmitArbitrationDecisionResponse clone() => SubmitArbitrationDecisionResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  SubmitArbitrationDecisionResponse copyWith(void Function(SubmitArbitrationDecisionResponse) updates) => super.copyWith((message) => updates(message as SubmitArbitrationDecisionResponse)) as SubmitArbitrationDecisionResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static SubmitArbitrationDecisionResponse create() => SubmitArbitrationDecisionResponse._();
  SubmitArbitrationDecisionResponse createEmptyInstance() => create();
  static $pb.PbList<SubmitArbitrationDecisionResponse> createRepeated() => $pb.PbList<SubmitArbitrationDecisionResponse>();
  @$core.pragma('dart2js:noInline')
  static SubmitArbitrationDecisionResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<SubmitArbitrationDecisionResponse>(create);
  static SubmitArbitrationDecisionResponse? _defaultInstance;

  @$pb.TagNumber(1)
  $core.bool get success => $_getBF(0);
  @$pb.TagNumber(1)
  set success($core.bool v) { $_setBool(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSuccess() => $_has(0);
  @$pb.TagNumber(1)
  void clearSuccess() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get decisionId => $_getSZ(1);
  @$pb.TagNumber(2)
  set decisionId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDecisionId() => $_has(1);
  @$pb.TagNumber(2)
  void clearDecisionId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => clearField(3);
}

/// GetArbitrationQueueStatsRequest - request queue statistics
class GetArbitrationQueueStatsRequest extends $pb.GeneratedMessage {
  factory GetArbitrationQueueStatsRequest() => create();
  GetArbitrationQueueStatsRequest._() : super();
  factory GetArbitrationQueueStatsRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory GetArbitrationQueueStatsRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'GetArbitrationQueueStatsRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueStatsRequest clone() => GetArbitrationQueueStatsRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueStatsRequest copyWith(void Function(GetArbitrationQueueStatsRequest) updates) => super.copyWith((message) => updates(message as GetArbitrationQueueStatsRequest)) as GetArbitrationQueueStatsRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueStatsRequest create() => GetArbitrationQueueStatsRequest._();
  GetArbitrationQueueStatsRequest createEmptyInstance() => create();
  static $pb.PbList<GetArbitrationQueueStatsRequest> createRepeated() => $pb.PbList<GetArbitrationQueueStatsRequest>();
  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueStatsRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GetArbitrationQueueStatsRequest>(create);
  static GetArbitrationQueueStatsRequest? _defaultInstance;
}

/// ArbitrationQueueStatsInfo - queue statistics
class ArbitrationQueueStatsInfo extends $pb.GeneratedMessage {
  factory ArbitrationQueueStatsInfo({
    $core.int? totalPending,
    $core.int? totalAssigned,
    $core.int? totalInReview,
    $core.int? totalResolvedToday,
    $core.double? avgResolutionTimeHours,
    $core.Map<$core.String, $core.int>? byPriority,
    $core.Map<$core.String, $core.int>? byReason,
  }) {
    final $result = create();
    if (totalPending != null) {
      $result.totalPending = totalPending;
    }
    if (totalAssigned != null) {
      $result.totalAssigned = totalAssigned;
    }
    if (totalInReview != null) {
      $result.totalInReview = totalInReview;
    }
    if (totalResolvedToday != null) {
      $result.totalResolvedToday = totalResolvedToday;
    }
    if (avgResolutionTimeHours != null) {
      $result.avgResolutionTimeHours = avgResolutionTimeHours;
    }
    if (byPriority != null) {
      $result.byPriority.addAll(byPriority);
    }
    if (byReason != null) {
      $result.byReason.addAll(byReason);
    }
    return $result;
  }
  ArbitrationQueueStatsInfo._() : super();
  factory ArbitrationQueueStatsInfo.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ArbitrationQueueStatsInfo.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ArbitrationQueueStatsInfo', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'totalPending', $pb.PbFieldType.O3)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'totalAssigned', $pb.PbFieldType.O3)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'totalInReview', $pb.PbFieldType.O3)
    ..a<$core.int>(4, _omitFieldNames ? '' : 'totalResolvedToday', $pb.PbFieldType.O3)
    ..a<$core.double>(5, _omitFieldNames ? '' : 'avgResolutionTimeHours', $pb.PbFieldType.OD)
    ..m<$core.String, $core.int>(6, _omitFieldNames ? '' : 'byPriority', entryClassName: 'ArbitrationQueueStatsInfo.ByPriorityEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.O3, packageName: const $pb.PackageName('agent.v1'))
    ..m<$core.String, $core.int>(7, _omitFieldNames ? '' : 'byReason', entryClassName: 'ArbitrationQueueStatsInfo.ByReasonEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.O3, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ArbitrationQueueStatsInfo clone() => ArbitrationQueueStatsInfo()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ArbitrationQueueStatsInfo copyWith(void Function(ArbitrationQueueStatsInfo) updates) => super.copyWith((message) => updates(message as ArbitrationQueueStatsInfo)) as ArbitrationQueueStatsInfo;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ArbitrationQueueStatsInfo create() => ArbitrationQueueStatsInfo._();
  ArbitrationQueueStatsInfo createEmptyInstance() => create();
  static $pb.PbList<ArbitrationQueueStatsInfo> createRepeated() => $pb.PbList<ArbitrationQueueStatsInfo>();
  @$core.pragma('dart2js:noInline')
  static ArbitrationQueueStatsInfo getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ArbitrationQueueStatsInfo>(create);
  static ArbitrationQueueStatsInfo? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get totalPending => $_getIZ(0);
  @$pb.TagNumber(1)
  set totalPending($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasTotalPending() => $_has(0);
  @$pb.TagNumber(1)
  void clearTotalPending() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get totalAssigned => $_getIZ(1);
  @$pb.TagNumber(2)
  set totalAssigned($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTotalAssigned() => $_has(1);
  @$pb.TagNumber(2)
  void clearTotalAssigned() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get totalInReview => $_getIZ(2);
  @$pb.TagNumber(3)
  set totalInReview($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTotalInReview() => $_has(2);
  @$pb.TagNumber(3)
  void clearTotalInReview() => clearField(3);

  @$pb.TagNumber(4)
  $core.int get totalResolvedToday => $_getIZ(3);
  @$pb.TagNumber(4)
  set totalResolvedToday($core.int v) { $_setSignedInt32(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasTotalResolvedToday() => $_has(3);
  @$pb.TagNumber(4)
  void clearTotalResolvedToday() => clearField(4);

  @$pb.TagNumber(5)
  $core.double get avgResolutionTimeHours => $_getN(4);
  @$pb.TagNumber(5)
  set avgResolutionTimeHours($core.double v) { $_setDouble(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasAvgResolutionTimeHours() => $_has(4);
  @$pb.TagNumber(5)
  void clearAvgResolutionTimeHours() => clearField(5);

  @$pb.TagNumber(6)
  $core.Map<$core.String, $core.int> get byPriority => $_getMap(5);

  @$pb.TagNumber(7)
  $core.Map<$core.String, $core.int> get byReason => $_getMap(6);
}

/// GetArbitrationQueueStatsResponse - response with queue statistics
class GetArbitrationQueueStatsResponse extends $pb.GeneratedMessage {
  factory GetArbitrationQueueStatsResponse({
    ArbitrationQueueStatsInfo? stats,
  }) {
    final $result = create();
    if (stats != null) {
      $result.stats = stats;
    }
    return $result;
  }
  GetArbitrationQueueStatsResponse._() : super();
  factory GetArbitrationQueueStatsResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory GetArbitrationQueueStatsResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'GetArbitrationQueueStatsResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOM<ArbitrationQueueStatsInfo>(1, _omitFieldNames ? '' : 'stats', subBuilder: ArbitrationQueueStatsInfo.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueStatsResponse clone() => GetArbitrationQueueStatsResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  GetArbitrationQueueStatsResponse copyWith(void Function(GetArbitrationQueueStatsResponse) updates) => super.copyWith((message) => updates(message as GetArbitrationQueueStatsResponse)) as GetArbitrationQueueStatsResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueStatsResponse create() => GetArbitrationQueueStatsResponse._();
  GetArbitrationQueueStatsResponse createEmptyInstance() => create();
  static $pb.PbList<GetArbitrationQueueStatsResponse> createRepeated() => $pb.PbList<GetArbitrationQueueStatsResponse>();
  @$core.pragma('dart2js:noInline')
  static GetArbitrationQueueStatsResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<GetArbitrationQueueStatsResponse>(create);
  static GetArbitrationQueueStatsResponse? _defaultInstance;

  @$pb.TagNumber(1)
  ArbitrationQueueStatsInfo get stats => $_getN(0);
  @$pb.TagNumber(1)
  set stats(ArbitrationQueueStatsInfo v) { setField(1, v); }
  @$pb.TagNumber(1)
  $core.bool hasStats() => $_has(0);
  @$pb.TagNumber(1)
  void clearStats() => clearField(1);
  @$pb.TagNumber(1)
  ArbitrationQueueStatsInfo ensureStats() => $_ensure(0);
}

class CitationBlock extends $pb.GeneratedMessage {
  factory CitationBlock({
    $core.Iterable<Citation>? citations,
  }) {
    final $result = create();
    if (citations != null) {
      $result.citations.addAll(citations);
    }
    return $result;
  }
  CitationBlock._() : super();
  factory CitationBlock.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory CitationBlock.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'CitationBlock', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..pc<Citation>(1, _omitFieldNames ? '' : 'citations', $pb.PbFieldType.PM, subBuilder: Citation.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  CitationBlock clone() => CitationBlock()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  CitationBlock copyWith(void Function(CitationBlock) updates) => super.copyWith((message) => updates(message as CitationBlock)) as CitationBlock;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CitationBlock create() => CitationBlock._();
  CitationBlock createEmptyInstance() => create();
  static $pb.PbList<CitationBlock> createRepeated() => $pb.PbList<CitationBlock>();
  @$core.pragma('dart2js:noInline')
  static CitationBlock getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CitationBlock>(create);
  static CitationBlock? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<Citation> get citations => $_getList(0);
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
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (title != null) {
      $result.title = title;
    }
    if (content != null) {
      $result.content = content;
    }
    if (sourceType != null) {
      $result.sourceType = sourceType;
    }
    if (url != null) {
      $result.url = url;
    }
    if (score != null) {
      $result.score = score;
    }
    if (fileId != null) {
      $result.fileId = fileId;
    }
    if (pageNumber != null) {
      $result.pageNumber = pageNumber;
    }
    if (chunkIndex != null) {
      $result.chunkIndex = chunkIndex;
    }
    if (sectionTitle != null) {
      $result.sectionTitle = sectionTitle;
    }
    return $result;
  }
  Citation._() : super();
  factory Citation.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Citation.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Citation', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'title')
    ..aOS(3, _omitFieldNames ? '' : 'content')
    ..aOS(4, _omitFieldNames ? '' : 'sourceType')
    ..aOS(5, _omitFieldNames ? '' : 'url')
    ..a<$core.double>(6, _omitFieldNames ? '' : 'score', $pb.PbFieldType.OF)
    ..aOS(7, _omitFieldNames ? '' : 'fileId')
    ..a<$core.int>(8, _omitFieldNames ? '' : 'pageNumber', $pb.PbFieldType.O3)
    ..a<$core.int>(9, _omitFieldNames ? '' : 'chunkIndex', $pb.PbFieldType.O3)
    ..aOS(10, _omitFieldNames ? '' : 'sectionTitle')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Citation clone() => Citation()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Citation copyWith(void Function(Citation) updates) => super.copyWith((message) => updates(message as Citation)) as Citation;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Citation create() => Citation._();
  Citation createEmptyInstance() => create();
  static $pb.PbList<Citation> createRepeated() => $pb.PbList<Citation>();
  @$core.pragma('dart2js:noInline')
  static Citation getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Citation>(create);
  static Citation? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get title => $_getSZ(1);
  @$pb.TagNumber(2)
  set title($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTitle() => $_has(1);
  @$pb.TagNumber(2)
  void clearTitle() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get content => $_getSZ(2);
  @$pb.TagNumber(3)
  set content($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearContent() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get sourceType => $_getSZ(3);
  @$pb.TagNumber(4)
  set sourceType($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasSourceType() => $_has(3);
  @$pb.TagNumber(4)
  void clearSourceType() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get url => $_getSZ(4);
  @$pb.TagNumber(5)
  set url($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasUrl() => $_has(4);
  @$pb.TagNumber(5)
  void clearUrl() => clearField(5);

  @$pb.TagNumber(6)
  $core.double get score => $_getN(5);
  @$pb.TagNumber(6)
  set score($core.double v) { $_setFloat(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasScore() => $_has(5);
  @$pb.TagNumber(6)
  void clearScore() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get fileId => $_getSZ(6);
  @$pb.TagNumber(7)
  set fileId($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasFileId() => $_has(6);
  @$pb.TagNumber(7)
  void clearFileId() => clearField(7);

  @$pb.TagNumber(8)
  $core.int get pageNumber => $_getIZ(7);
  @$pb.TagNumber(8)
  set pageNumber($core.int v) { $_setSignedInt32(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasPageNumber() => $_has(7);
  @$pb.TagNumber(8)
  void clearPageNumber() => clearField(8);

  @$pb.TagNumber(9)
  $core.int get chunkIndex => $_getIZ(8);
  @$pb.TagNumber(9)
  set chunkIndex($core.int v) { $_setSignedInt32(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasChunkIndex() => $_has(8);
  @$pb.TagNumber(9)
  void clearChunkIndex() => clearField(9);

  @$pb.TagNumber(10)
  $core.String get sectionTitle => $_getSZ(9);
  @$pb.TagNumber(10)
  set sectionTitle($core.String v) { $_setString(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasSectionTitle() => $_has(9);
  @$pb.TagNumber(10)
  void clearSectionTitle() => clearField(10);
}

class ToolCall extends $pb.GeneratedMessage {
  factory ToolCall({
    $core.String? id,
    $core.String? name,
    $core.String? arguments,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (name != null) {
      $result.name = name;
    }
    if (arguments != null) {
      $result.arguments = arguments;
    }
    return $result;
  }
  ToolCall._() : super();
  factory ToolCall.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ToolCall.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ToolCall', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'name')
    ..aOS(3, _omitFieldNames ? '' : 'arguments')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ToolCall clone() => ToolCall()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ToolCall copyWith(void Function(ToolCall) updates) => super.copyWith((message) => updates(message as ToolCall)) as ToolCall;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolCall create() => ToolCall._();
  ToolCall createEmptyInstance() => create();
  static $pb.PbList<ToolCall> createRepeated() => $pb.PbList<ToolCall>();
  @$core.pragma('dart2js:noInline')
  static ToolCall getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ToolCall>(create);
  static ToolCall? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get name => $_getSZ(1);
  @$pb.TagNumber(2)
  set name($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasName() => $_has(1);
  @$pb.TagNumber(2)
  void clearName() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get arguments => $_getSZ(2);
  @$pb.TagNumber(3)
  set arguments($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasArguments() => $_has(2);
  @$pb.TagNumber(3)
  void clearArguments() => clearField(3);
}

class ToolResultPayload extends $pb.GeneratedMessage {
  factory ToolResultPayload({
    $core.String? toolName,
    $core.bool? success,
    $4.Struct? data,
    $core.String? errorMessage,
    $core.String? suggestion,
    $core.String? widgetType,
    $4.Struct? widgetData,
    $core.String? toolCallId,
  }) {
    final $result = create();
    if (toolName != null) {
      $result.toolName = toolName;
    }
    if (success != null) {
      $result.success = success;
    }
    if (data != null) {
      $result.data = data;
    }
    if (errorMessage != null) {
      $result.errorMessage = errorMessage;
    }
    if (suggestion != null) {
      $result.suggestion = suggestion;
    }
    if (widgetType != null) {
      $result.widgetType = widgetType;
    }
    if (widgetData != null) {
      $result.widgetData = widgetData;
    }
    if (toolCallId != null) {
      $result.toolCallId = toolCallId;
    }
    return $result;
  }
  ToolResultPayload._() : super();
  factory ToolResultPayload.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ToolResultPayload.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ToolResultPayload', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'toolName')
    ..aOB(2, _omitFieldNames ? '' : 'success')
    ..aOM<$4.Struct>(3, _omitFieldNames ? '' : 'data', subBuilder: $4.Struct.create)
    ..aOS(4, _omitFieldNames ? '' : 'errorMessage')
    ..aOS(5, _omitFieldNames ? '' : 'suggestion')
    ..aOS(6, _omitFieldNames ? '' : 'widgetType')
    ..aOM<$4.Struct>(7, _omitFieldNames ? '' : 'widgetData', subBuilder: $4.Struct.create)
    ..aOS(8, _omitFieldNames ? '' : 'toolCallId')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ToolResultPayload clone() => ToolResultPayload()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ToolResultPayload copyWith(void Function(ToolResultPayload) updates) => super.copyWith((message) => updates(message as ToolResultPayload)) as ToolResultPayload;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolResultPayload create() => ToolResultPayload._();
  ToolResultPayload createEmptyInstance() => create();
  static $pb.PbList<ToolResultPayload> createRepeated() => $pb.PbList<ToolResultPayload>();
  @$core.pragma('dart2js:noInline')
  static ToolResultPayload getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ToolResultPayload>(create);
  static ToolResultPayload? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get toolName => $_getSZ(0);
  @$pb.TagNumber(1)
  set toolName($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasToolName() => $_has(0);
  @$pb.TagNumber(1)
  void clearToolName() => clearField(1);

  @$pb.TagNumber(2)
  $core.bool get success => $_getBF(1);
  @$pb.TagNumber(2)
  set success($core.bool v) { $_setBool(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasSuccess() => $_has(1);
  @$pb.TagNumber(2)
  void clearSuccess() => clearField(2);

  @$pb.TagNumber(3)
  $4.Struct get data => $_getN(2);
  @$pb.TagNumber(3)
  set data($4.Struct v) { setField(3, v); }
  @$pb.TagNumber(3)
  $core.bool hasData() => $_has(2);
  @$pb.TagNumber(3)
  void clearData() => clearField(3);
  @$pb.TagNumber(3)
  $4.Struct ensureData() => $_ensure(2);

  @$pb.TagNumber(4)
  $core.String get errorMessage => $_getSZ(3);
  @$pb.TagNumber(4)
  set errorMessage($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasErrorMessage() => $_has(3);
  @$pb.TagNumber(4)
  void clearErrorMessage() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get suggestion => $_getSZ(4);
  @$pb.TagNumber(5)
  set suggestion($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasSuggestion() => $_has(4);
  @$pb.TagNumber(5)
  void clearSuggestion() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get widgetType => $_getSZ(5);
  @$pb.TagNumber(6)
  set widgetType($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasWidgetType() => $_has(5);
  @$pb.TagNumber(6)
  void clearWidgetType() => clearField(6);

  @$pb.TagNumber(7)
  $4.Struct get widgetData => $_getN(6);
  @$pb.TagNumber(7)
  set widgetData($4.Struct v) { setField(7, v); }
  @$pb.TagNumber(7)
  $core.bool hasWidgetData() => $_has(6);
  @$pb.TagNumber(7)
  void clearWidgetData() => clearField(7);
  @$pb.TagNumber(7)
  $4.Struct ensureWidgetData() => $_ensure(6);

  @$pb.TagNumber(8)
  $core.String get toolCallId => $_getSZ(7);
  @$pb.TagNumber(8)
  set toolCallId($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasToolCallId() => $_has(7);
  @$pb.TagNumber(8)
  void clearToolCallId() => clearField(8);
}

class EvidenceRef extends $pb.GeneratedMessage {
  factory EvidenceRef({
    $core.String? type,
    $core.String? id,
    $core.String? schemaVersion,
    $core.bool? userDeleted,
  }) {
    final $result = create();
    if (type != null) {
      $result.type = type;
    }
    if (id != null) {
      $result.id = id;
    }
    if (schemaVersion != null) {
      $result.schemaVersion = schemaVersion;
    }
    if (userDeleted != null) {
      $result.userDeleted = userDeleted;
    }
    return $result;
  }
  EvidenceRef._() : super();
  factory EvidenceRef.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory EvidenceRef.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'EvidenceRef', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'type')
    ..aOS(2, _omitFieldNames ? '' : 'id')
    ..aOS(3, _omitFieldNames ? '' : 'schemaVersion')
    ..aOB(4, _omitFieldNames ? '' : 'userDeleted')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  EvidenceRef clone() => EvidenceRef()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  EvidenceRef copyWith(void Function(EvidenceRef) updates) => super.copyWith((message) => updates(message as EvidenceRef)) as EvidenceRef;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EvidenceRef create() => EvidenceRef._();
  EvidenceRef createEmptyInstance() => create();
  static $pb.PbList<EvidenceRef> createRepeated() => $pb.PbList<EvidenceRef>();
  @$core.pragma('dart2js:noInline')
  static EvidenceRef getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<EvidenceRef>(create);
  static EvidenceRef? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get type => $_getSZ(0);
  @$pb.TagNumber(1)
  set type($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasType() => $_has(0);
  @$pb.TagNumber(1)
  void clearType() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get id => $_getSZ(1);
  @$pb.TagNumber(2)
  set id($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasId() => $_has(1);
  @$pb.TagNumber(2)
  void clearId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get schemaVersion => $_getSZ(2);
  @$pb.TagNumber(3)
  set schemaVersion($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasSchemaVersion() => $_has(2);
  @$pb.TagNumber(3)
  void clearSchemaVersion() => clearField(3);

  @$pb.TagNumber(4)
  $core.bool get userDeleted => $_getBF(3);
  @$pb.TagNumber(4)
  set userDeleted($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasUserDeleted() => $_has(3);
  @$pb.TagNumber(4)
  void clearUserDeleted() => clearField(4);
}

class CoolDownPolicy extends $pb.GeneratedMessage {
  factory CoolDownPolicy({
    $core.String? policy,
    $fixnum.Int64? untilMs,
  }) {
    final $result = create();
    if (policy != null) {
      $result.policy = policy;
    }
    if (untilMs != null) {
      $result.untilMs = untilMs;
    }
    return $result;
  }
  CoolDownPolicy._() : super();
  factory CoolDownPolicy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory CoolDownPolicy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'CoolDownPolicy', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'policy')
    ..aInt64(2, _omitFieldNames ? '' : 'untilMs')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  CoolDownPolicy clone() => CoolDownPolicy()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  CoolDownPolicy copyWith(void Function(CoolDownPolicy) updates) => super.copyWith((message) => updates(message as CoolDownPolicy)) as CoolDownPolicy;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static CoolDownPolicy create() => CoolDownPolicy._();
  CoolDownPolicy createEmptyInstance() => create();
  static $pb.PbList<CoolDownPolicy> createRepeated() => $pb.PbList<CoolDownPolicy>();
  @$core.pragma('dart2js:noInline')
  static CoolDownPolicy getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<CoolDownPolicy>(create);
  static CoolDownPolicy? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get policy => $_getSZ(0);
  @$pb.TagNumber(1)
  set policy($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasPolicy() => $_has(0);
  @$pb.TagNumber(1)
  void clearPolicy() => clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get untilMs => $_getI64(1);
  @$pb.TagNumber(2)
  set untilMs($fixnum.Int64 v) { $_setInt64(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasUntilMs() => $_has(1);
  @$pb.TagNumber(2)
  void clearUntilMs() => clearField(2);
}

class InterventionReason extends $pb.GeneratedMessage {
  factory InterventionReason({
    $core.String? triggerEventId,
    $core.String? explanationText,
    $core.double? confidence,
    $core.Iterable<EvidenceRef>? evidenceRefs,
    $core.Iterable<$core.String>? decisionTrace,
  }) {
    final $result = create();
    if (triggerEventId != null) {
      $result.triggerEventId = triggerEventId;
    }
    if (explanationText != null) {
      $result.explanationText = explanationText;
    }
    if (confidence != null) {
      $result.confidence = confidence;
    }
    if (evidenceRefs != null) {
      $result.evidenceRefs.addAll(evidenceRefs);
    }
    if (decisionTrace != null) {
      $result.decisionTrace.addAll(decisionTrace);
    }
    return $result;
  }
  InterventionReason._() : super();
  factory InterventionReason.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionReason.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionReason', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'triggerEventId')
    ..aOS(2, _omitFieldNames ? '' : 'explanationText')
    ..a<$core.double>(3, _omitFieldNames ? '' : 'confidence', $pb.PbFieldType.OF)
    ..pc<EvidenceRef>(4, _omitFieldNames ? '' : 'evidenceRefs', $pb.PbFieldType.PM, subBuilder: EvidenceRef.create)
    ..pPS(5, _omitFieldNames ? '' : 'decisionTrace')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionReason clone() => InterventionReason()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionReason copyWith(void Function(InterventionReason) updates) => super.copyWith((message) => updates(message as InterventionReason)) as InterventionReason;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionReason create() => InterventionReason._();
  InterventionReason createEmptyInstance() => create();
  static $pb.PbList<InterventionReason> createRepeated() => $pb.PbList<InterventionReason>();
  @$core.pragma('dart2js:noInline')
  static InterventionReason getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionReason>(create);
  static InterventionReason? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get triggerEventId => $_getSZ(0);
  @$pb.TagNumber(1)
  set triggerEventId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasTriggerEventId() => $_has(0);
  @$pb.TagNumber(1)
  void clearTriggerEventId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get explanationText => $_getSZ(1);
  @$pb.TagNumber(2)
  set explanationText($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasExplanationText() => $_has(1);
  @$pb.TagNumber(2)
  void clearExplanationText() => clearField(2);

  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double v) { $_setFloat(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => clearField(3);

  @$pb.TagNumber(4)
  $core.List<EvidenceRef> get evidenceRefs => $_getList(3);

  @$pb.TagNumber(5)
  $core.List<$core.String> get decisionTrace => $_getList(4);
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
    $4.Struct? content,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (dedupeKey != null) {
      $result.dedupeKey = dedupeKey;
    }
    if (topic != null) {
      $result.topic = topic;
    }
    if (createdAtMs != null) {
      $result.createdAtMs = createdAtMs;
    }
    if (expiresAtMs != null) {
      $result.expiresAtMs = expiresAtMs;
    }
    if (isRetractable != null) {
      $result.isRetractable = isRetractable;
    }
    if (supersedesId != null) {
      $result.supersedesId = supersedesId;
    }
    if (schemaVersion != null) {
      $result.schemaVersion = schemaVersion;
    }
    if (policyVersion != null) {
      $result.policyVersion = policyVersion;
    }
    if (modelVersion != null) {
      $result.modelVersion = modelVersion;
    }
    if (reason != null) {
      $result.reason = reason;
    }
    if (level != null) {
      $result.level = level;
    }
    if (onReject != null) {
      $result.onReject = onReject;
    }
    if (content != null) {
      $result.content = content;
    }
    return $result;
  }
  InterventionRequest._() : super();
  factory InterventionRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
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
    ..aOM<InterventionReason>(11, _omitFieldNames ? '' : 'reason', subBuilder: InterventionReason.create)
    ..e<InterventionLevel>(12, _omitFieldNames ? '' : 'level', $pb.PbFieldType.OE, defaultOrMaker: InterventionLevel.SILENT_MARKER, valueOf: InterventionLevel.valueOf, enumValues: InterventionLevel.values)
    ..aOM<CoolDownPolicy>(13, _omitFieldNames ? '' : 'onReject', subBuilder: CoolDownPolicy.create)
    ..aOM<$4.Struct>(14, _omitFieldNames ? '' : 'content', subBuilder: $4.Struct.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionRequest clone() => InterventionRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionRequest copyWith(void Function(InterventionRequest) updates) => super.copyWith((message) => updates(message as InterventionRequest)) as InterventionRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionRequest create() => InterventionRequest._();
  InterventionRequest createEmptyInstance() => create();
  static $pb.PbList<InterventionRequest> createRepeated() => $pb.PbList<InterventionRequest>();
  @$core.pragma('dart2js:noInline')
  static InterventionRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionRequest>(create);
  static InterventionRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get dedupeKey => $_getSZ(1);
  @$pb.TagNumber(2)
  set dedupeKey($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDedupeKey() => $_has(1);
  @$pb.TagNumber(2)
  void clearDedupeKey() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get topic => $_getSZ(2);
  @$pb.TagNumber(3)
  set topic($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTopic() => $_has(2);
  @$pb.TagNumber(3)
  void clearTopic() => clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get createdAtMs => $_getI64(3);
  @$pb.TagNumber(4)
  set createdAtMs($fixnum.Int64 v) { $_setInt64(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasCreatedAtMs() => $_has(3);
  @$pb.TagNumber(4)
  void clearCreatedAtMs() => clearField(4);

  @$pb.TagNumber(5)
  $fixnum.Int64 get expiresAtMs => $_getI64(4);
  @$pb.TagNumber(5)
  set expiresAtMs($fixnum.Int64 v) { $_setInt64(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasExpiresAtMs() => $_has(4);
  @$pb.TagNumber(5)
  void clearExpiresAtMs() => clearField(5);

  @$pb.TagNumber(6)
  $core.bool get isRetractable => $_getBF(5);
  @$pb.TagNumber(6)
  set isRetractable($core.bool v) { $_setBool(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasIsRetractable() => $_has(5);
  @$pb.TagNumber(6)
  void clearIsRetractable() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get supersedesId => $_getSZ(6);
  @$pb.TagNumber(7)
  set supersedesId($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasSupersedesId() => $_has(6);
  @$pb.TagNumber(7)
  void clearSupersedesId() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get schemaVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set schemaVersion($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasSchemaVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearSchemaVersion() => clearField(8);

  @$pb.TagNumber(9)
  $core.String get policyVersion => $_getSZ(8);
  @$pb.TagNumber(9)
  set policyVersion($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasPolicyVersion() => $_has(8);
  @$pb.TagNumber(9)
  void clearPolicyVersion() => clearField(9);

  @$pb.TagNumber(10)
  $core.String get modelVersion => $_getSZ(9);
  @$pb.TagNumber(10)
  set modelVersion($core.String v) { $_setString(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasModelVersion() => $_has(9);
  @$pb.TagNumber(10)
  void clearModelVersion() => clearField(10);

  @$pb.TagNumber(11)
  InterventionReason get reason => $_getN(10);
  @$pb.TagNumber(11)
  set reason(InterventionReason v) { setField(11, v); }
  @$pb.TagNumber(11)
  $core.bool hasReason() => $_has(10);
  @$pb.TagNumber(11)
  void clearReason() => clearField(11);
  @$pb.TagNumber(11)
  InterventionReason ensureReason() => $_ensure(10);

  @$pb.TagNumber(12)
  InterventionLevel get level => $_getN(11);
  @$pb.TagNumber(12)
  set level(InterventionLevel v) { setField(12, v); }
  @$pb.TagNumber(12)
  $core.bool hasLevel() => $_has(11);
  @$pb.TagNumber(12)
  void clearLevel() => clearField(12);

  @$pb.TagNumber(13)
  CoolDownPolicy get onReject => $_getN(12);
  @$pb.TagNumber(13)
  set onReject(CoolDownPolicy v) { setField(13, v); }
  @$pb.TagNumber(13)
  $core.bool hasOnReject() => $_has(12);
  @$pb.TagNumber(13)
  void clearOnReject() => clearField(13);
  @$pb.TagNumber(13)
  CoolDownPolicy ensureOnReject() => $_ensure(12);

  @$pb.TagNumber(14)
  $4.Struct get content => $_getN(13);
  @$pb.TagNumber(14)
  set content($4.Struct v) { setField(14, v); }
  @$pb.TagNumber(14)
  $core.bool hasContent() => $_has(13);
  @$pb.TagNumber(14)
  void clearContent() => clearField(14);
  @$pb.TagNumber(14)
  $4.Struct ensureContent() => $_ensure(13);
}

class InterventionPayload extends $pb.GeneratedMessage {
  factory InterventionPayload({
    InterventionRequest? request,
  }) {
    final $result = create();
    if (request != null) {
      $result.request = request;
    }
    return $result;
  }
  InterventionPayload._() : super();
  factory InterventionPayload.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionPayload.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionPayload', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOM<InterventionRequest>(1, _omitFieldNames ? '' : 'request', subBuilder: InterventionRequest.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionPayload clone() => InterventionPayload()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionPayload copyWith(void Function(InterventionPayload) updates) => super.copyWith((message) => updates(message as InterventionPayload)) as InterventionPayload;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionPayload create() => InterventionPayload._();
  InterventionPayload createEmptyInstance() => create();
  static $pb.PbList<InterventionPayload> createRepeated() => $pb.PbList<InterventionPayload>();
  @$core.pragma('dart2js:noInline')
  static InterventionPayload getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionPayload>(create);
  static InterventionPayload? _defaultInstance;

  @$pb.TagNumber(1)
  InterventionRequest get request => $_getN(0);
  @$pb.TagNumber(1)
  set request(InterventionRequest v) { setField(1, v); }
  @$pb.TagNumber(1)
  $core.bool hasRequest() => $_has(0);
  @$pb.TagNumber(1)
  void clearRequest() => clearField(1);
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
    final $result = create();
    if (state != null) {
      $result.state = state;
    }
    if (details != null) {
      $result.details = details;
    }
    if (currentAgentName != null) {
      $result.currentAgentName = currentAgentName;
    }
    if (activeAgent != null) {
      $result.activeAgent = activeAgent;
    }
    return $result;
  }
  AgentStatus._() : super();
  factory AgentStatus.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AgentStatus.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AgentStatus', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..e<AgentStatus_State>(1, _omitFieldNames ? '' : 'state', $pb.PbFieldType.OE, defaultOrMaker: AgentStatus_State.UNKNOWN, valueOf: AgentStatus_State.valueOf, enumValues: AgentStatus_State.values)
    ..aOS(2, _omitFieldNames ? '' : 'details')
    ..aOS(3, _omitFieldNames ? '' : 'currentAgentName')
    ..e<AgentType>(4, _omitFieldNames ? '' : 'activeAgent', $pb.PbFieldType.OE, defaultOrMaker: AgentType.AGENT_UNKNOWN, valueOf: AgentType.valueOf, enumValues: AgentType.values)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AgentStatus clone() => AgentStatus()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AgentStatus copyWith(void Function(AgentStatus) updates) => super.copyWith((message) => updates(message as AgentStatus)) as AgentStatus;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AgentStatus create() => AgentStatus._();
  AgentStatus createEmptyInstance() => create();
  static $pb.PbList<AgentStatus> createRepeated() => $pb.PbList<AgentStatus>();
  @$core.pragma('dart2js:noInline')
  static AgentStatus getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AgentStatus>(create);
  static AgentStatus? _defaultInstance;

  @$pb.TagNumber(1)
  AgentStatus_State get state => $_getN(0);
  @$pb.TagNumber(1)
  set state(AgentStatus_State v) { setField(1, v); }
  @$pb.TagNumber(1)
  $core.bool hasState() => $_has(0);
  @$pb.TagNumber(1)
  void clearState() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get details => $_getSZ(1);
  @$pb.TagNumber(2)
  set details($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDetails() => $_has(1);
  @$pb.TagNumber(2)
  void clearDetails() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get currentAgentName => $_getSZ(2);
  @$pb.TagNumber(3)
  set currentAgentName($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasCurrentAgentName() => $_has(2);
  @$pb.TagNumber(3)
  void clearCurrentAgentName() => clearField(3);

  @$pb.TagNumber(4)
  AgentType get activeAgent => $_getN(3);
  @$pb.TagNumber(4)
  set activeAgent(AgentType v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasActiveAgent() => $_has(3);
  @$pb.TagNumber(4)
  void clearActiveAgent() => clearField(4);
}

class Error extends $pb.GeneratedMessage {
  factory Error({
    $core.String? code,
    $core.String? message,
    $core.bool? retryable,
    $core.Map<$core.String, $core.String>? details,
  }) {
    final $result = create();
    if (code != null) {
      $result.code = code;
    }
    if (message != null) {
      $result.message = message;
    }
    if (retryable != null) {
      $result.retryable = retryable;
    }
    if (details != null) {
      $result.details.addAll(details);
    }
    return $result;
  }
  Error._() : super();
  factory Error.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Error.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Error', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'code')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOB(3, _omitFieldNames ? '' : 'retryable')
    ..m<$core.String, $core.String>(4, _omitFieldNames ? '' : 'details', entryClassName: 'Error.DetailsEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Error clone() => Error()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Error copyWith(void Function(Error) updates) => super.copyWith((message) => updates(message as Error)) as Error;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Error create() => Error._();
  Error createEmptyInstance() => create();
  static $pb.PbList<Error> createRepeated() => $pb.PbList<Error>();
  @$core.pragma('dart2js:noInline')
  static Error getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Error>(create);
  static Error? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get code => $_getSZ(0);
  @$pb.TagNumber(1)
  set code($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasCode() => $_has(0);
  @$pb.TagNumber(1)
  void clearCode() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => clearField(2);

  @$pb.TagNumber(3)
  $core.bool get retryable => $_getBF(2);
  @$pb.TagNumber(3)
  set retryable($core.bool v) { $_setBool(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasRetryable() => $_has(2);
  @$pb.TagNumber(3)
  void clearRetryable() => clearField(3);

  @$pb.TagNumber(4)
  $core.Map<$core.String, $core.String> get details => $_getMap(3);
}

class Usage extends $pb.GeneratedMessage {
  factory Usage({
    $core.int? promptTokens,
    $core.int? completionTokens,
    $core.int? totalTokens,
    $fixnum.Int64? costMicroUsd,
  }) {
    final $result = create();
    if (promptTokens != null) {
      $result.promptTokens = promptTokens;
    }
    if (completionTokens != null) {
      $result.completionTokens = completionTokens;
    }
    if (totalTokens != null) {
      $result.totalTokens = totalTokens;
    }
    if (costMicroUsd != null) {
      $result.costMicroUsd = costMicroUsd;
    }
    return $result;
  }
  Usage._() : super();
  factory Usage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Usage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Usage', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'promptTokens', $pb.PbFieldType.O3)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'completionTokens', $pb.PbFieldType.O3)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'totalTokens', $pb.PbFieldType.O3)
    ..aInt64(4, _omitFieldNames ? '' : 'costMicroUsd')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Usage clone() => Usage()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Usage copyWith(void Function(Usage) updates) => super.copyWith((message) => updates(message as Usage)) as Usage;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Usage create() => Usage._();
  Usage createEmptyInstance() => create();
  static $pb.PbList<Usage> createRepeated() => $pb.PbList<Usage>();
  @$core.pragma('dart2js:noInline')
  static Usage getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Usage>(create);
  static Usage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get promptTokens => $_getIZ(0);
  @$pb.TagNumber(1)
  set promptTokens($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasPromptTokens() => $_has(0);
  @$pb.TagNumber(1)
  void clearPromptTokens() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get completionTokens => $_getIZ(1);
  @$pb.TagNumber(2)
  set completionTokens($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasCompletionTokens() => $_has(1);
  @$pb.TagNumber(2)
  void clearCompletionTokens() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get totalTokens => $_getIZ(2);
  @$pb.TagNumber(3)
  set totalTokens($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTotalTokens() => $_has(2);
  @$pb.TagNumber(3)
  void clearTotalTokens() => clearField(3);

  @$pb.TagNumber(4)
  $fixnum.Int64 get costMicroUsd => $_getI64(3);
  @$pb.TagNumber(4)
  set costMicroUsd($fixnum.Int64 v) { $_setInt64(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasCostMicroUsd() => $_has(3);
  @$pb.TagNumber(4)
  void clearCostMicroUsd() => clearField(4);
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
    final $result = create();
    if (userId != null) {
      $result.userId = userId;
    }
    if (queryText != null) {
      $result.queryText = queryText;
    }
    if (limit != null) {
      $result.limit = limit;
    }
    if (minScore != null) {
      $result.minScore = minScore;
    }
    if (filter != null) {
      $result.filter = filter;
    }
    if (hybridAlpha != null) {
      $result.hybridAlpha = hybridAlpha;
    }
    return $result;
  }
  MemoryQuery._() : super();
  factory MemoryQuery.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory MemoryQuery.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'MemoryQuery', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'userId')
    ..aOS(2, _omitFieldNames ? '' : 'queryText')
    ..a<$core.int>(3, _omitFieldNames ? '' : 'limit', $pb.PbFieldType.O3)
    ..a<$core.double>(4, _omitFieldNames ? '' : 'minScore', $pb.PbFieldType.OF)
    ..aOM<MemoryFilter>(5, _omitFieldNames ? '' : 'filter', subBuilder: MemoryFilter.create)
    ..a<$core.double>(6, _omitFieldNames ? '' : 'hybridAlpha', $pb.PbFieldType.OF)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  MemoryQuery clone() => MemoryQuery()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  MemoryQuery copyWith(void Function(MemoryQuery) updates) => super.copyWith((message) => updates(message as MemoryQuery)) as MemoryQuery;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryQuery create() => MemoryQuery._();
  MemoryQuery createEmptyInstance() => create();
  static $pb.PbList<MemoryQuery> createRepeated() => $pb.PbList<MemoryQuery>();
  @$core.pragma('dart2js:noInline')
  static MemoryQuery getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<MemoryQuery>(create);
  static MemoryQuery? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get userId => $_getSZ(0);
  @$pb.TagNumber(1)
  set userId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasUserId() => $_has(0);
  @$pb.TagNumber(1)
  void clearUserId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get queryText => $_getSZ(1);
  @$pb.TagNumber(2)
  set queryText($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasQueryText() => $_has(1);
  @$pb.TagNumber(2)
  void clearQueryText() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get limit => $_getIZ(2);
  @$pb.TagNumber(3)
  set limit($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasLimit() => $_has(2);
  @$pb.TagNumber(3)
  void clearLimit() => clearField(3);

  @$pb.TagNumber(4)
  $core.double get minScore => $_getN(3);
  @$pb.TagNumber(4)
  set minScore($core.double v) { $_setFloat(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasMinScore() => $_has(3);
  @$pb.TagNumber(4)
  void clearMinScore() => clearField(4);

  @$pb.TagNumber(5)
  MemoryFilter get filter => $_getN(4);
  @$pb.TagNumber(5)
  set filter(MemoryFilter v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasFilter() => $_has(4);
  @$pb.TagNumber(5)
  void clearFilter() => clearField(5);
  @$pb.TagNumber(5)
  MemoryFilter ensureFilter() => $_ensure(4);

  /// Hybrid search parameter.
  /// 0.0 = Keyword Search (BM25)
  /// 1.0 = Vector Search (Dense)
  /// 0.5 = Hybrid
  @$pb.TagNumber(6)
  $core.double get hybridAlpha => $_getN(5);
  @$pb.TagNumber(6)
  set hybridAlpha($core.double v) { $_setFloat(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasHybridAlpha() => $_has(5);
  @$pb.TagNumber(6)
  void clearHybridAlpha() => clearField(6);
}

class MemoryFilter extends $pb.GeneratedMessage {
  factory MemoryFilter({
    $core.Iterable<$core.String>? tags,
    $5.Timestamp? startTime,
    $5.Timestamp? endTime,
    $core.Iterable<$core.String>? sourceTypes,
  }) {
    final $result = create();
    if (tags != null) {
      $result.tags.addAll(tags);
    }
    if (startTime != null) {
      $result.startTime = startTime;
    }
    if (endTime != null) {
      $result.endTime = endTime;
    }
    if (sourceTypes != null) {
      $result.sourceTypes.addAll(sourceTypes);
    }
    return $result;
  }
  MemoryFilter._() : super();
  factory MemoryFilter.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory MemoryFilter.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'MemoryFilter', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..pPS(1, _omitFieldNames ? '' : 'tags')
    ..aOM<$5.Timestamp>(2, _omitFieldNames ? '' : 'startTime', subBuilder: $5.Timestamp.create)
    ..aOM<$5.Timestamp>(3, _omitFieldNames ? '' : 'endTime', subBuilder: $5.Timestamp.create)
    ..pPS(4, _omitFieldNames ? '' : 'sourceTypes')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  MemoryFilter clone() => MemoryFilter()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  MemoryFilter copyWith(void Function(MemoryFilter) updates) => super.copyWith((message) => updates(message as MemoryFilter)) as MemoryFilter;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryFilter create() => MemoryFilter._();
  MemoryFilter createEmptyInstance() => create();
  static $pb.PbList<MemoryFilter> createRepeated() => $pb.PbList<MemoryFilter>();
  @$core.pragma('dart2js:noInline')
  static MemoryFilter getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<MemoryFilter>(create);
  static MemoryFilter? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<$core.String> get tags => $_getList(0);

  @$pb.TagNumber(2)
  $5.Timestamp get startTime => $_getN(1);
  @$pb.TagNumber(2)
  set startTime($5.Timestamp v) { setField(2, v); }
  @$pb.TagNumber(2)
  $core.bool hasStartTime() => $_has(1);
  @$pb.TagNumber(2)
  void clearStartTime() => clearField(2);
  @$pb.TagNumber(2)
  $5.Timestamp ensureStartTime() => $_ensure(1);

  @$pb.TagNumber(3)
  $5.Timestamp get endTime => $_getN(2);
  @$pb.TagNumber(3)
  set endTime($5.Timestamp v) { setField(3, v); }
  @$pb.TagNumber(3)
  $core.bool hasEndTime() => $_has(2);
  @$pb.TagNumber(3)
  void clearEndTime() => clearField(3);
  @$pb.TagNumber(3)
  $5.Timestamp ensureEndTime() => $_ensure(2);

  @$pb.TagNumber(4)
  $core.List<$core.String> get sourceTypes => $_getList(3);
}

class MemoryResult extends $pb.GeneratedMessage {
  factory MemoryResult({
    $core.Iterable<MemoryItem>? items,
    $core.int? totalFound,
  }) {
    final $result = create();
    if (items != null) {
      $result.items.addAll(items);
    }
    if (totalFound != null) {
      $result.totalFound = totalFound;
    }
    return $result;
  }
  MemoryResult._() : super();
  factory MemoryResult.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory MemoryResult.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'MemoryResult', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..pc<MemoryItem>(1, _omitFieldNames ? '' : 'items', $pb.PbFieldType.PM, subBuilder: MemoryItem.create)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'totalFound', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  MemoryResult clone() => MemoryResult()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  MemoryResult copyWith(void Function(MemoryResult) updates) => super.copyWith((message) => updates(message as MemoryResult)) as MemoryResult;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryResult create() => MemoryResult._();
  MemoryResult createEmptyInstance() => create();
  static $pb.PbList<MemoryResult> createRepeated() => $pb.PbList<MemoryResult>();
  @$core.pragma('dart2js:noInline')
  static MemoryResult getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<MemoryResult>(create);
  static MemoryResult? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<MemoryItem> get items => $_getList(0);

  @$pb.TagNumber(2)
  $core.int get totalFound => $_getIZ(1);
  @$pb.TagNumber(2)
  set totalFound($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTotalFound() => $_has(1);
  @$pb.TagNumber(2)
  void clearTotalFound() => clearField(2);
}

class MemoryItem extends $pb.GeneratedMessage {
  factory MemoryItem({
    $core.String? id,
    $core.String? content,
    $core.double? score,
    $5.Timestamp? createdAt,
    $core.Map<$core.String, $core.String>? metadata,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (content != null) {
      $result.content = content;
    }
    if (score != null) {
      $result.score = score;
    }
    if (createdAt != null) {
      $result.createdAt = createdAt;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    return $result;
  }
  MemoryItem._() : super();
  factory MemoryItem.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory MemoryItem.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'MemoryItem', package: const $pb.PackageName(_omitMessageNames ? '' : 'agent.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..a<$core.double>(3, _omitFieldNames ? '' : 'score', $pb.PbFieldType.OF)
    ..aOM<$5.Timestamp>(4, _omitFieldNames ? '' : 'createdAt', subBuilder: $5.Timestamp.create)
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'metadata', entryClassName: 'MemoryItem.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('agent.v1'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  MemoryItem clone() => MemoryItem()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  MemoryItem copyWith(void Function(MemoryItem) updates) => super.copyWith((message) => updates(message as MemoryItem)) as MemoryItem;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MemoryItem create() => MemoryItem._();
  MemoryItem createEmptyInstance() => create();
  static $pb.PbList<MemoryItem> createRepeated() => $pb.PbList<MemoryItem>();
  @$core.pragma('dart2js:noInline')
  static MemoryItem getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<MemoryItem>(create);
  static MemoryItem? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get content => $_getSZ(1);
  @$pb.TagNumber(2)
  set content($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasContent() => $_has(1);
  @$pb.TagNumber(2)
  void clearContent() => clearField(2);

  @$pb.TagNumber(3)
  $core.double get score => $_getN(2);
  @$pb.TagNumber(3)
  set score($core.double v) { $_setFloat(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasScore() => $_has(2);
  @$pb.TagNumber(3)
  void clearScore() => clearField(3);

  @$pb.TagNumber(4)
  $5.Timestamp get createdAt => $_getN(3);
  @$pb.TagNumber(4)
  set createdAt($5.Timestamp v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasCreatedAt() => $_has(3);
  @$pb.TagNumber(4)
  void clearCreatedAt() => clearField(4);
  @$pb.TagNumber(4)
  $5.Timestamp ensureCreatedAt() => $_ensure(3);

  @$pb.TagNumber(5)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(4);
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
