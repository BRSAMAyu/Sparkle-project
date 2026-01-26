//
//  Generated code. Do not modify.
//  source: websocket.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;

import 'agent_service.pb.dart' as $0;

/// WebSocketMessage represents the envelope for all WebSocket communications
class WebSocketMessage extends $pb.GeneratedMessage {
  factory WebSocketMessage({
    $core.String? version,
    $core.String? type,
    $core.List<$core.int>? payload,
    $core.String? traceId,
    $core.String? requestId,
    $fixnum.Int64? timestamp,
  }) {
    final $result = create();
    if (version != null) {
      $result.version = version;
    }
    if (type != null) {
      $result.type = type;
    }
    if (payload != null) {
      $result.payload = payload;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (timestamp != null) {
      $result.timestamp = timestamp;
    }
    return $result;
  }
  WebSocketMessage._() : super();
  factory WebSocketMessage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory WebSocketMessage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'WebSocketMessage', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'version')
    ..aOS(2, _omitFieldNames ? '' : 'type')
    ..a<$core.List<$core.int>>(3, _omitFieldNames ? '' : 'payload', $pb.PbFieldType.OY)
    ..aOS(4, _omitFieldNames ? '' : 'traceId')
    ..aOS(5, _omitFieldNames ? '' : 'requestId')
    ..aInt64(6, _omitFieldNames ? '' : 'timestamp')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  WebSocketMessage clone() => WebSocketMessage()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  WebSocketMessage copyWith(void Function(WebSocketMessage) updates) => super.copyWith((message) => updates(message as WebSocketMessage)) as WebSocketMessage;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WebSocketMessage create() => WebSocketMessage._();
  WebSocketMessage createEmptyInstance() => create();
  static $pb.PbList<WebSocketMessage> createRepeated() => $pb.PbList<WebSocketMessage>();
  @$core.pragma('dart2js:noInline')
  static WebSocketMessage getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<WebSocketMessage>(create);
  static WebSocketMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get version => $_getSZ(0);
  @$pb.TagNumber(1)
  set version($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasVersion() => $_has(0);
  @$pb.TagNumber(1)
  void clearVersion() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get type => $_getSZ(1);
  @$pb.TagNumber(2)
  set type($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasType() => $_has(1);
  @$pb.TagNumber(2)
  void clearType() => clearField(2);

  @$pb.TagNumber(3)
  $core.List<$core.int> get payload => $_getN(2);
  @$pb.TagNumber(3)
  set payload($core.List<$core.int> v) { $_setBytes(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasPayload() => $_has(2);
  @$pb.TagNumber(3)
  void clearPayload() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get traceId => $_getSZ(3);
  @$pb.TagNumber(4)
  set traceId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasTraceId() => $_has(3);
  @$pb.TagNumber(4)
  void clearTraceId() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get requestId => $_getSZ(4);
  @$pb.TagNumber(5)
  set requestId($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasRequestId() => $_has(4);
  @$pb.TagNumber(5)
  void clearRequestId() => clearField(5);

  @$pb.TagNumber(6)
  $fixnum.Int64 get timestamp => $_getI64(5);
  @$pb.TagNumber(6)
  set timestamp($fixnum.Int64 v) { $_setInt64(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasTimestamp() => $_has(5);
  @$pb.TagNumber(6)
  void clearTimestamp() => clearField(6);
}

/// ChatMessage represents a user chat message payload
class ChatMessage extends $pb.GeneratedMessage {
  factory ChatMessage({
    $core.String? sessionId,
    $core.String? userId,
    $core.String? message,
    $core.Iterable<$0.ToolCall>? toolCalls,
  }) {
    final $result = create();
    if (sessionId != null) {
      $result.sessionId = sessionId;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    if (message != null) {
      $result.message = message;
    }
    if (toolCalls != null) {
      $result.toolCalls.addAll(toolCalls);
    }
    return $result;
  }
  ChatMessage._() : super();
  factory ChatMessage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ChatMessage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ChatMessage', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'sessionId')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOS(3, _omitFieldNames ? '' : 'message')
    ..pc<$0.ToolCall>(4, _omitFieldNames ? '' : 'toolCalls', $pb.PbFieldType.PM, subBuilder: $0.ToolCall.create)
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
  $core.String get sessionId => $_getSZ(0);
  @$pb.TagNumber(1)
  set sessionId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSessionId() => $_has(0);
  @$pb.TagNumber(1)
  void clearSessionId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get message => $_getSZ(2);
  @$pb.TagNumber(3)
  set message($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMessage() => $_has(2);
  @$pb.TagNumber(3)
  void clearMessage() => clearField(3);

  @$pb.TagNumber(4)
  $core.List<$0.ToolCall> get toolCalls => $_getList(3);
}

class UpdateNodeMasteryRequest extends $pb.GeneratedMessage {
  factory UpdateNodeMasteryRequest({
    $core.String? nodeId,
    $core.int? mastery,
    $fixnum.Int64? timestamp,
    $core.String? requestId,
    $core.int? revision,
  }) {
    final $result = create();
    if (nodeId != null) {
      $result.nodeId = nodeId;
    }
    if (mastery != null) {
      $result.mastery = mastery;
    }
    if (timestamp != null) {
      $result.timestamp = timestamp;
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

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'UpdateNodeMasteryRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'nodeId')
    ..a<$core.int>(2, _omitFieldNames ? '' : 'mastery', $pb.PbFieldType.O3)
    ..aInt64(3, _omitFieldNames ? '' : 'timestamp')
    ..aOS(4, _omitFieldNames ? '' : 'requestId')
    ..a<$core.int>(5, _omitFieldNames ? '' : 'revision', $pb.PbFieldType.O3)
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
  $core.String get nodeId => $_getSZ(0);
  @$pb.TagNumber(1)
  set nodeId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasNodeId() => $_has(0);
  @$pb.TagNumber(1)
  void clearNodeId() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get mastery => $_getIZ(1);
  @$pb.TagNumber(2)
  set mastery($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMastery() => $_has(1);
  @$pb.TagNumber(2)
  void clearMastery() => clearField(2);

  @$pb.TagNumber(3)
  $fixnum.Int64 get timestamp => $_getI64(2);
  @$pb.TagNumber(3)
  set timestamp($fixnum.Int64 v) { $_setInt64(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTimestamp() => $_has(2);
  @$pb.TagNumber(3)
  void clearTimestamp() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get requestId => $_getSZ(3);
  @$pb.TagNumber(4)
  set requestId($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasRequestId() => $_has(3);
  @$pb.TagNumber(4)
  void clearRequestId() => clearField(4);

  @$pb.TagNumber(5)
  $core.int get revision => $_getIZ(4);
  @$pb.TagNumber(5)
  set revision($core.int v) { $_setSignedInt32(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasRevision() => $_has(4);
  @$pb.TagNumber(5)
  void clearRevision() => clearField(5);
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
    final $result = create();
    if (interventionId != null) {
      $result.interventionId = interventionId;
    }
    if (level != null) {
      $result.level = level;
    }
    if (content != null) {
      $result.content = content;
    }
    if (actions != null) {
      $result.actions.addAll(actions);
    }
    if (expiresAt != null) {
      $result.expiresAt = expiresAt;
    }
    return $result;
  }
  InterventionPushMessage._() : super();
  factory InterventionPushMessage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionPushMessage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionPushMessage', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'interventionId')
    ..aOS(2, _omitFieldNames ? '' : 'level')
    ..aOM<InterventionContent>(3, _omitFieldNames ? '' : 'content', subBuilder: InterventionContent.create)
    ..pc<InterventionAction>(4, _omitFieldNames ? '' : 'actions', $pb.PbFieldType.PM, subBuilder: InterventionAction.create)
    ..aInt64(5, _omitFieldNames ? '' : 'expiresAt')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionPushMessage clone() => InterventionPushMessage()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionPushMessage copyWith(void Function(InterventionPushMessage) updates) => super.copyWith((message) => updates(message as InterventionPushMessage)) as InterventionPushMessage;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionPushMessage create() => InterventionPushMessage._();
  InterventionPushMessage createEmptyInstance() => create();
  static $pb.PbList<InterventionPushMessage> createRepeated() => $pb.PbList<InterventionPushMessage>();
  @$core.pragma('dart2js:noInline')
  static InterventionPushMessage getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionPushMessage>(create);
  static InterventionPushMessage? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get interventionId => $_getSZ(0);
  @$pb.TagNumber(1)
  set interventionId($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasInterventionId() => $_has(0);
  @$pb.TagNumber(1)
  void clearInterventionId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get level => $_getSZ(1);
  @$pb.TagNumber(2)
  set level($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasLevel() => $_has(1);
  @$pb.TagNumber(2)
  void clearLevel() => clearField(2);

  @$pb.TagNumber(3)
  InterventionContent get content => $_getN(2);
  @$pb.TagNumber(3)
  set content(InterventionContent v) { setField(3, v); }
  @$pb.TagNumber(3)
  $core.bool hasContent() => $_has(2);
  @$pb.TagNumber(3)
  void clearContent() => clearField(3);
  @$pb.TagNumber(3)
  InterventionContent ensureContent() => $_ensure(2);

  @$pb.TagNumber(4)
  $core.List<InterventionAction> get actions => $_getList(3);

  @$pb.TagNumber(5)
  $fixnum.Int64 get expiresAt => $_getI64(4);
  @$pb.TagNumber(5)
  set expiresAt($fixnum.Int64 v) { $_setInt64(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasExpiresAt() => $_has(4);
  @$pb.TagNumber(5)
  void clearExpiresAt() => clearField(5);
}

class InterventionContent extends $pb.GeneratedMessage {
  factory InterventionContent({
    $core.String? renderedMessage,
    $core.String? intentType,
    $core.String? templateId,
    $core.int? scaffoldingLevel,
    $core.Map<$core.String, $core.String>? contextVariables,
  }) {
    final $result = create();
    if (renderedMessage != null) {
      $result.renderedMessage = renderedMessage;
    }
    if (intentType != null) {
      $result.intentType = intentType;
    }
    if (templateId != null) {
      $result.templateId = templateId;
    }
    if (scaffoldingLevel != null) {
      $result.scaffoldingLevel = scaffoldingLevel;
    }
    if (contextVariables != null) {
      $result.contextVariables.addAll(contextVariables);
    }
    return $result;
  }
  InterventionContent._() : super();
  factory InterventionContent.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionContent.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionContent', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'renderedMessage')
    ..aOS(2, _omitFieldNames ? '' : 'intentType')
    ..aOS(3, _omitFieldNames ? '' : 'templateId')
    ..a<$core.int>(4, _omitFieldNames ? '' : 'scaffoldingLevel', $pb.PbFieldType.O3)
    ..m<$core.String, $core.String>(5, _omitFieldNames ? '' : 'contextVariables', entryClassName: 'InterventionContent.ContextVariablesEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.ws'))
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionContent clone() => InterventionContent()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionContent copyWith(void Function(InterventionContent) updates) => super.copyWith((message) => updates(message as InterventionContent)) as InterventionContent;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionContent create() => InterventionContent._();
  InterventionContent createEmptyInstance() => create();
  static $pb.PbList<InterventionContent> createRepeated() => $pb.PbList<InterventionContent>();
  @$core.pragma('dart2js:noInline')
  static InterventionContent getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionContent>(create);
  static InterventionContent? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get renderedMessage => $_getSZ(0);
  @$pb.TagNumber(1)
  set renderedMessage($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasRenderedMessage() => $_has(0);
  @$pb.TagNumber(1)
  void clearRenderedMessage() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get intentType => $_getSZ(1);
  @$pb.TagNumber(2)
  set intentType($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasIntentType() => $_has(1);
  @$pb.TagNumber(2)
  void clearIntentType() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get templateId => $_getSZ(2);
  @$pb.TagNumber(3)
  set templateId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTemplateId() => $_has(2);
  @$pb.TagNumber(3)
  void clearTemplateId() => clearField(3);

  @$pb.TagNumber(4)
  $core.int get scaffoldingLevel => $_getIZ(3);
  @$pb.TagNumber(4)
  set scaffoldingLevel($core.int v) { $_setSignedInt32(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasScaffoldingLevel() => $_has(3);
  @$pb.TagNumber(4)
  void clearScaffoldingLevel() => clearField(4);

  @$pb.TagNumber(5)
  $core.Map<$core.String, $core.String> get contextVariables => $_getMap(4);
}

class InterventionAction extends $pb.GeneratedMessage {
  factory InterventionAction({
    $core.String? id,
    $core.String? label,
    $core.String? type,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (label != null) {
      $result.label = label;
    }
    if (type != null) {
      $result.type = type;
    }
    return $result;
  }
  InterventionAction._() : super();
  factory InterventionAction.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InterventionAction.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InterventionAction', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.ws'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'label')
    ..aOS(3, _omitFieldNames ? '' : 'type')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InterventionAction clone() => InterventionAction()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InterventionAction copyWith(void Function(InterventionAction) updates) => super.copyWith((message) => updates(message as InterventionAction)) as InterventionAction;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InterventionAction create() => InterventionAction._();
  InterventionAction createEmptyInstance() => create();
  static $pb.PbList<InterventionAction> createRepeated() => $pb.PbList<InterventionAction>();
  @$core.pragma('dart2js:noInline')
  static InterventionAction getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InterventionAction>(create);
  static InterventionAction? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get label => $_getSZ(1);
  @$pb.TagNumber(2)
  set label($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasLabel() => $_has(1);
  @$pb.TagNumber(2)
  void clearLabel() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get type => $_getSZ(2);
  @$pb.TagNumber(3)
  set type($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasType() => $_has(2);
  @$pb.TagNumber(3)
  void clearType() => clearField(3);
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
