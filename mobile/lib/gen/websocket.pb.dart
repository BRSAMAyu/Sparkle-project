// This is a generated file - do not edit.
//
// Generated from websocket.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;
import 'package:protobuf/well_known_types/google/protobuf/timestamp.pb.dart'
    as $0;

import 'agent_service.pb.dart' as $1;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

/// WebSocketMessage represents the envelope for all WebSocket communications
class WebSocketMessage extends $pb.GeneratedMessage {
  factory WebSocketMessage({
    $core.String? version,
    $core.String? type,
    $core.List<$core.int>? payload,
    $core.String? traceId,
    $core.String? requestId,
    $0.Timestamp? eventTime,
  }) {
    final result = create();
    if (version != null) result.version = version;
    if (type != null) result.type = type;
    if (payload != null) result.payload = payload;
    if (traceId != null) result.traceId = traceId;
    if (requestId != null) result.requestId = requestId;
    if (eventTime != null) result.eventTime = eventTime;
    return result;
  }

  WebSocketMessage._();

  factory WebSocketMessage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory WebSocketMessage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WebSocketMessage',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..a<$core.List<$core.int>>(
        3, _omitFieldNames ? '' : 'payload', $pb.PbFieldType.OY)
    ..aOS(4, _omitFieldNames ? '' : 'traceId')
    ..aOS(5, _omitFieldNames ? '' : 'requestId')
    ..aOM<$0.Timestamp>(7, _omitFieldNames ? '' : 'eventTime',
        subBuilder: $0.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WebSocketMessage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WebSocketMessage copyWith(void Function(WebSocketMessage) updates) =>
      super.copyWith((message) => updates(message as WebSocketMessage))
          as WebSocketMessage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WebSocketMessage create() => WebSocketMessage._();
  @$core.override
  WebSocketMessage createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static WebSocketMessage getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WebSocketMessage>(create);
  static WebSocketMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.List<$core.int> get payload => $_getN(2);
  @$pb.TagNumber(3)
  set payload($core.List<$core.int> value) => $_setBytes(2, value);
  @$pb.TagNumber(3)
  $core.bool hasPayload() => $_has(2);
  @$pb.TagNumber(3)
  void clearPayload() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get traceId => $_getSZ(3);
  @$pb.TagNumber(4)
  set traceId($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTraceId() => $_has(3);
  @$pb.TagNumber(4)
  void clearTraceId() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get requestId => $_getSZ(4);
  @$pb.TagNumber(5)
  set requestId($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasRequestId() => $_has(4);
  @$pb.TagNumber(5)
  void clearRequestId() => $_clearField(5);

  @$pb.TagNumber(7)
  $0.Timestamp get eventTime => $_getN(5);
  @$pb.TagNumber(7)
  set eventTime($0.Timestamp value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasEventTime() => $_has(5);
  @$pb.TagNumber(7)
  void clearEventTime() => $_clearField(7);
  @$pb.TagNumber(7)
  $0.Timestamp ensureEventTime() => $_ensure(5);
}

/// ChatMessage represents a user chat message payload
class ChatMessage extends $pb.GeneratedMessage {
  factory ChatMessage({
    $core.String? sessionId,
    $core.String? userId,
    $core.String? message,
    $core.Iterable<$1.ToolCall>? toolCalls,
  }) {
    final result = create();
    if (sessionId != null) result.sessionId = sessionId;
    if (userId != null) result.userId = userId;
    if (message != null) result.message = message;
    if (toolCalls != null) result.toolCalls.addAll(toolCalls);
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
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'sessionId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..pPM<$1.ToolCall>(4, _omitFieldNames ? '' : 'toolCalls',
        subBuilder: $1.ToolCall.create)
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
  $core.String get sessionId => $_getSZ(0);
  @$pb.TagNumber(1)
  set sessionId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSessionId() => $_has(0);
  @$pb.TagNumber(1)
  void clearSessionId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => $_clearField(3);

  @$pb.TagNumber(4)
  $pb.PbList<$1.ToolCall> get toolCalls => $_getList(3);
}

class UpdateNodeMasteryRequest extends $pb.GeneratedMessage {
  factory UpdateNodeMasteryRequest({
    $core.String? nodeId,
    $core.int? mastery,
    $core.String? requestId,
    $core.int? revision,
    $0.Timestamp? eventTime,
  }) {
    final result = create();
    if (nodeId != null) result.nodeId = nodeId;
    if (mastery != null) result.mastery = mastery;
    if (requestId != null) result.requestId = requestId;
    if (revision != null) result.revision = revision;
    if (eventTime != null) result.eventTime = eventTime;
    return result;
  }

  UpdateNodeMasteryRequest._();

  factory UpdateNodeMasteryRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory UpdateNodeMasteryRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'UpdateNodeMasteryRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nodeId')
    ..aI(2, _omitFieldNames ? '' : 'mastery')
    ..aOS(4, _omitFieldNames ? '' : 'requestId')
    ..aI(5, _omitFieldNames ? '' : 'revision')
    ..aOM<$0.Timestamp>(6, _omitFieldNames ? '' : 'eventTime',
        subBuilder: $0.Timestamp.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UpdateNodeMasteryRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  UpdateNodeMasteryRequest copyWith(
          void Function(UpdateNodeMasteryRequest) updates) =>
      super.copyWith((message) => updates(message as UpdateNodeMasteryRequest))
          as UpdateNodeMasteryRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryRequest create() => UpdateNodeMasteryRequest._();
  @$core.override
  UpdateNodeMasteryRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static UpdateNodeMasteryRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<UpdateNodeMasteryRequest>(create);
  static UpdateNodeMasteryRequest? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get nodeId => $_getSZ(0);
  @$pb.TagNumber(1)
  set nodeId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasNodeId() => $_has(0);
  @$pb.TagNumber(1)
  void clearNodeId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get mastery => $_getIZ(1);
  @$pb.TagNumber(2)
  set mastery($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMastery() => $_has(1);
  @$pb.TagNumber(2)
  void clearMastery() => $_clearField(2);

  @$pb.TagNumber(4)
  $core.String get requestId => $_getSZ(2);
  @$pb.TagNumber(4)
  set requestId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(4)
  $core.bool hasRequestId() => $_has(2);
  @$pb.TagNumber(4)
  void clearRequestId() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get revision => $_getIZ(3);
  @$pb.TagNumber(5)
  set revision($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(5)
  $core.bool hasRevision() => $_has(3);
  @$pb.TagNumber(5)
  void clearRevision() => $_clearField(5);

  @$pb.TagNumber(6)
  $0.Timestamp get eventTime => $_getN(4);
  @$pb.TagNumber(6)
  set eventTime($0.Timestamp value) => $_setField(6, value);
  @$pb.TagNumber(6)
  $core.bool hasEventTime() => $_has(4);
  @$pb.TagNumber(6)
  void clearEventTime() => $_clearField(6);
  @$pb.TagNumber(6)
  $0.Timestamp ensureEventTime() => $_ensure(4);
}

/// Intervention push messages for real-time adaptive interventions
class InterventionPushMessage extends $pb.GeneratedMessage {
  factory InterventionPushMessage({
    $core.String? interventionId,
    $core.String? level,
    InterventionContent? content,
    $core.Iterable<InterventionAction>? actions,
    $fixnum.Int64? expiresAt,
  }) {
    final result = create();
    if (interventionId != null) result.interventionId = interventionId;
    if (level != null) result.level = level;
    if (content != null) result.content = content;
    if (actions != null) result.actions.addAll(actions);
    if (expiresAt != null) result.expiresAt = expiresAt;
    return result;
  }

  InterventionPushMessage._();

  factory InterventionPushMessage.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionPushMessage.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionPushMessage',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'interventionId')
    ..aOS(2, _omitFieldNames ? '' : 'level')
    ..aOM<InterventionContent>(3, _omitFieldNames ? '' : 'content',
        subBuilder: InterventionContent.create)
    ..pPM<InterventionAction>(4, _omitFieldNames ? '' : 'actions',
        subBuilder: InterventionAction.create)
    ..aInt64(5, _omitFieldNames ? '' : 'expiresAt')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionPushMessage clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionPushMessage copyWith(
          void Function(InterventionPushMessage) updates) =>
      super.copyWith((message) => updates(message as InterventionPushMessage))
          as InterventionPushMessage;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionPushMessage create() => InterventionPushMessage._();
  @$core.override
  InterventionPushMessage createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionPushMessage getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionPushMessage>(create);
  static InterventionPushMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get interventionId => $_getSZ(0);
  @$pb.TagNumber(1)
  set interventionId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasInterventionId() => $_has(0);
  @$pb.TagNumber(1)
  void clearInterventionId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get level => $_getSZ(1);
  @$pb.TagNumber(2)
  set level($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasLevel() => $_has(1);
  @$pb.TagNumber(2)
  void clearLevel() => $_clearField(2);

  @$pb.TagNumber(3)
  InterventionContent get content => $_getN(2);
  @$pb.TagNumber(3)
  set content(InterventionContent value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearContent() => $_clearField(3);
  @$pb.TagNumber(3)
  InterventionContent ensureContent() => $_ensure(2);

  @$pb.TagNumber(4)
  $pb.PbList<InterventionAction> get actions => $_getList(3);

  @$pb.TagNumber(5)
  $fixnum.Int64 get expiresAt => $_getI64(4);
  @$pb.TagNumber(5)
  set expiresAt($fixnum.Int64 value) => $_setInt64(4, value);
  @$pb.TagNumber(5)
  $core.bool hasExpiresAt() => $_has(4);
  @$pb.TagNumber(5)
  void clearExpiresAt() => $_clearField(5);
}

class InterventionContent extends $pb.GeneratedMessage {
  factory InterventionContent({
    $core.String? renderedMessage,
    $core.String? intentType,
    $core.String? templateId,
    $core.int? scaffoldingLevel,
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>?
        contextVariables,
  }) {
    final result = create();
    if (renderedMessage != null) result.renderedMessage = renderedMessage;
    if (intentType != null) result.intentType = intentType;
    if (templateId != null) result.templateId = templateId;
    if (scaffoldingLevel != null) result.scaffoldingLevel = scaffoldingLevel;
    if (contextVariables != null)
      result.contextVariables.addEntries(contextVariables);
    return result;
  }

  InterventionContent._();

  factory InterventionContent.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionContent.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionContent',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'renderedMessage')
    ..aOS(2, _omitFieldNames ? '' : 'intentType')
    ..aOS(3, _omitFieldNames ? '' : 'templateId')
    ..aI(4, _omitFieldNames ? '' : 'scaffoldingLevel')
    ..m<$core.String, $core.String>(
        5, _omitFieldNames ? '' : 'contextVariables',
        entryClassName: 'InterventionContent.ContextVariablesEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.ws'))
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionContent clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionContent copyWith(void Function(InterventionContent) updates) =>
      super.copyWith((message) => updates(message as InterventionContent))
          as InterventionContent;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionContent create() => InterventionContent._();
  @$core.override
  InterventionContent createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionContent getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionContent>(create);
  static InterventionContent? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get renderedMessage => $_getSZ(0);
  @$pb.TagNumber(1)
  set renderedMessage($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasRenderedMessage() => $_has(0);
  @$pb.TagNumber(1)
  void clearRenderedMessage() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get intentType => $_getSZ(1);
  @$pb.TagNumber(2)
  set intentType($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasIntentType() => $_has(1);
  @$pb.TagNumber(2)
  void clearIntentType() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get templateId => $_getSZ(2);
  @$pb.TagNumber(3)
  set templateId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTemplateId() => $_has(2);
  @$pb.TagNumber(3)
  void clearTemplateId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get scaffoldingLevel => $_getIZ(3);
  @$pb.TagNumber(4)
  set scaffoldingLevel($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasScaffoldingLevel() => $_has(3);
  @$pb.TagNumber(4)
  void clearScaffoldingLevel() => $_clearField(4);

  @$pb.TagNumber(5)
  $pb.PbMap<$core.String, $core.String> get contextVariables => $_getMap(4);
}

class InterventionAction extends $pb.GeneratedMessage {
  factory InterventionAction({
    $core.String? id,
    $core.String? label,
    $core.String? type,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (label != null) result.label = label;
    if (type != null) result.type = type;
    return result;
  }

  InterventionAction._();

  factory InterventionAction.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InterventionAction.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InterventionAction',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'label')
    ..aOS(3, _omitFieldNames ? '' : 'type')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionAction clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InterventionAction copyWith(void Function(InterventionAction) updates) =>
      super.copyWith((message) => updates(message as InterventionAction))
          as InterventionAction;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionAction create() => InterventionAction._();
  @$core.override
  InterventionAction createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InterventionAction getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InterventionAction>(create);
  static InterventionAction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get label => $_getSZ(1);
  @$pb.TagNumber(2)
  set label($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasLabel() => $_has(1);
  @$pb.TagNumber(2)
  void clearLabel() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get type => $_getSZ(2);
  @$pb.TagNumber(3)
  set type($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasType() => $_has(2);
  @$pb.TagNumber(3)
  void clearType() => $_clearField(3);
}

/// MessageAck - Server acknowledgment of client message
class MessageAck extends $pb.GeneratedMessage {
  factory MessageAck({
    $core.String? messageId,
    $core.String? status,
    $fixnum.Int64? timestamp,
    $core.String? errorCode,
    $core.String? errorMessage,
  }) {
    final result = create();
    if (messageId != null) result.messageId = messageId;
    if (status != null) result.status = status;
    if (timestamp != null) result.timestamp = timestamp;
    if (errorCode != null) result.errorCode = errorCode;
    if (errorMessage != null) result.errorMessage = errorMessage;
    return result;
  }

  MessageAck._();

  factory MessageAck.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MessageAck.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MessageAck',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'messageId')
    ..aOS(2, _omitFieldNames ? '' : 'status')
    ..aInt64(3, _omitFieldNames ? '' : 'timestamp')
    ..aOS(4, _omitFieldNames ? '' : 'errorCode')
    ..aOS(5, _omitFieldNames ? '' : 'errorMessage')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageAck clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageAck copyWith(void Function(MessageAck) updates) =>
      super.copyWith((message) => updates(message as MessageAck)) as MessageAck;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MessageAck create() => MessageAck._();
  @$core.override
  MessageAck createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MessageAck getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MessageAck>(create);
  static MessageAck? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get messageId => $_getSZ(0);
  @$pb.TagNumber(1)
  set messageId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasMessageId() => $_has(0);
  @$pb.TagNumber(1)
  void clearMessageId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get status => $_getSZ(1);
  @$pb.TagNumber(2)
  set status($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasStatus() => $_has(1);
  @$pb.TagNumber(2)
  void clearStatus() => $_clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get timestamp => $_getI64(2);
  @$pb.TagNumber(3)
  set timestamp($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTimestamp() => $_has(2);
  @$pb.TagNumber(3)
  void clearTimestamp() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get errorCode => $_getSZ(3);
  @$pb.TagNumber(4)
  set errorCode($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasErrorCode() => $_has(3);
  @$pb.TagNumber(4)
  void clearErrorCode() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get errorMessage => $_getSZ(4);
  @$pb.TagNumber(5)
  set errorMessage($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasErrorMessage() => $_has(4);
  @$pb.TagNumber(5)
  void clearErrorMessage() => $_clearField(5);
}

/// MessageNack - Server rejection of client message
class MessageNack extends $pb.GeneratedMessage {
  factory MessageNack({
    $core.String? messageId,
    $core.String? errorCode,
    $core.String? errorMessage,
    $core.int? retryAfterMs,
    $core.bool? permanent,
  }) {
    final result = create();
    if (messageId != null) result.messageId = messageId;
    if (errorCode != null) result.errorCode = errorCode;
    if (errorMessage != null) result.errorMessage = errorMessage;
    if (retryAfterMs != null) result.retryAfterMs = retryAfterMs;
    if (permanent != null) result.permanent = permanent;
    return result;
  }

  MessageNack._();

  factory MessageNack.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory MessageNack.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'MessageNack',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'messageId')
    ..aOS(2, _omitFieldNames ? '' : 'errorCode')
    ..aOS(3, _omitFieldNames ? '' : 'errorMessage')
    ..aI(4, _omitFieldNames ? '' : 'retryAfterMs')
    ..aOB(5, _omitFieldNames ? '' : 'permanent')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageNack clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  MessageNack copyWith(void Function(MessageNack) updates) =>
      super.copyWith((message) => updates(message as MessageNack))
          as MessageNack;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static MessageNack create() => MessageNack._();
  @$core.override
  MessageNack createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static MessageNack getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<MessageNack>(create);
  static MessageNack? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get messageId => $_getSZ(0);
  @$pb.TagNumber(1)
  set messageId($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasMessageId() => $_has(0);
  @$pb.TagNumber(1)
  void clearMessageId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get errorCode => $_getSZ(1);
  @$pb.TagNumber(2)
  set errorCode($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasErrorCode() => $_has(1);
  @$pb.TagNumber(2)
  void clearErrorCode() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get errorMessage => $_getSZ(2);
  @$pb.TagNumber(3)
  set errorMessage($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasErrorMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearErrorMessage() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get retryAfterMs => $_getIZ(3);
  @$pb.TagNumber(4)
  set retryAfterMs($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasRetryAfterMs() => $_has(3);
  @$pb.TagNumber(4)
  void clearRetryAfterMs() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.bool get permanent => $_getBF(4);
  @$pb.TagNumber(5)
  set permanent($core.bool value) => $_setBool(4, value);
  @$pb.TagNumber(5)
  $core.bool hasPermanent() => $_has(4);
  @$pb.TagNumber(5)
  void clearPermanent() => $_clearField(5);
}

/// Heartbeat ping/pong for connection health monitoring
class HeartbeatPing extends $pb.GeneratedMessage {
  factory HeartbeatPing({
    $fixnum.Int64? timestamp,
    $core.String? clientId,
  }) {
    final result = create();
    if (timestamp != null) result.timestamp = timestamp;
    if (clientId != null) result.clientId = clientId;
    return result;
  }

  HeartbeatPing._();

  factory HeartbeatPing.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory HeartbeatPing.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'HeartbeatPing',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aInt64(1, _omitFieldNames ? '' : 'timestamp')
    ..aOS(2, _omitFieldNames ? '' : 'clientId')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HeartbeatPing clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HeartbeatPing copyWith(void Function(HeartbeatPing) updates) =>
      super.copyWith((message) => updates(message as HeartbeatPing))
          as HeartbeatPing;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static HeartbeatPing create() => HeartbeatPing._();
  @$core.override
  HeartbeatPing createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static HeartbeatPing getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<HeartbeatPing>(create);
  static HeartbeatPing? _defaultInstance;

  @$pb.TagNumber(1)
  $fixnum.Int64 get timestamp => $_getI64(0);
  @$pb.TagNumber(1)
  set timestamp($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasTimestamp() => $_has(0);
  @$pb.TagNumber(1)
  void clearTimestamp() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get clientId => $_getSZ(1);
  @$pb.TagNumber(2)
  set clientId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasClientId() => $_has(1);
  @$pb.TagNumber(2)
  void clearClientId() => $_clearField(2);
}

class HeartbeatPong extends $pb.GeneratedMessage {
  factory HeartbeatPong({
    $fixnum.Int64? clientTimestamp,
    $fixnum.Int64? serverTimestamp,
  }) {
    final result = create();
    if (clientTimestamp != null) result.clientTimestamp = clientTimestamp;
    if (serverTimestamp != null) result.serverTimestamp = serverTimestamp;
    return result;
  }

  HeartbeatPong._();

  factory HeartbeatPong.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory HeartbeatPong.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'HeartbeatPong',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'),
      createEmptyInstance: create)
    ..aInt64(1, _omitFieldNames ? '' : 'clientTimestamp')
    ..aInt64(2, _omitFieldNames ? '' : 'serverTimestamp')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HeartbeatPong clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  HeartbeatPong copyWith(void Function(HeartbeatPong) updates) =>
      super.copyWith((message) => updates(message as HeartbeatPong))
          as HeartbeatPong;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static HeartbeatPong create() => HeartbeatPong._();
  @$core.override
  HeartbeatPong createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static HeartbeatPong getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<HeartbeatPong>(create);
  static HeartbeatPong? _defaultInstance;

  @$pb.TagNumber(1)
  $fixnum.Int64 get clientTimestamp => $_getI64(0);
  @$pb.TagNumber(1)
  set clientTimestamp($fixnum.Int64 value) => $_setInt64(0, value);
  @$pb.TagNumber(1)
  $core.bool hasClientTimestamp() => $_has(0);
  @$pb.TagNumber(1)
  void clearClientTimestamp() => $_clearField(1);

  @$pb.TagNumber(2)
  $fixnum.Int64 get serverTimestamp => $_getI64(1);
  @$pb.TagNumber(2)
  set serverTimestamp($fixnum.Int64 value) => $_setInt64(1, value);
  @$pb.TagNumber(2)
  $core.bool hasServerTimestamp() => $_has(1);
  @$pb.TagNumber(2)
  void clearServerTimestamp() => $_clearField(2);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
