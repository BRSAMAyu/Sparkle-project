//
//  Generated code. Do not modify.
//  source: sparkle/inference/v1/inference.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

import 'inference.pbenum.dart';

export 'inference.pbenum.dart';

class Message extends $pb.GeneratedMessage {
  factory Message({
    $core.String? role,
    $core.String? content,
  }) {
    final $result = create();
    if (role != null) {
      $result.role = role;
    }
    if (content != null) {
      $result.content = content;
    }
    return $result;
  }
  Message._() : super();
  factory Message.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Message.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Message', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'role')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Message clone() => Message()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Message copyWith(void Function(Message) updates) => super.copyWith((message) => updates(message as Message)) as Message;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Message create() => Message._();
  Message createEmptyInstance() => create();
  static $pb.PbList<Message> createRepeated() => $pb.PbList<Message>();
  @$core.pragma('dart2js:noInline')
  static Message getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Message>(create);
  static Message? _defaultInstance;

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
}

class ToolDefinition extends $pb.GeneratedMessage {
  factory ToolDefinition({
    $core.String? name,
    $core.String? description,
    $core.String? schemaJson,
  }) {
    final $result = create();
    if (name != null) {
      $result.name = name;
    }
    if (description != null) {
      $result.description = description;
    }
    if (schemaJson != null) {
      $result.schemaJson = schemaJson;
    }
    return $result;
  }
  ToolDefinition._() : super();
  factory ToolDefinition.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory ToolDefinition.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'ToolDefinition', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'name')
    ..aOS(2, _omitFieldNames ? '' : 'description')
    ..aOS(3, _omitFieldNames ? '' : 'schemaJson')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  ToolDefinition clone() => ToolDefinition()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  ToolDefinition copyWith(void Function(ToolDefinition) updates) => super.copyWith((message) => updates(message as ToolDefinition)) as ToolDefinition;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolDefinition create() => ToolDefinition._();
  ToolDefinition createEmptyInstance() => create();
  static $pb.PbList<ToolDefinition> createRepeated() => $pb.PbList<ToolDefinition>();
  @$core.pragma('dart2js:noInline')
  static ToolDefinition getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<ToolDefinition>(create);
  static ToolDefinition? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get name => $_getSZ(0);
  @$pb.TagNumber(1)
  set name($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasName() => $_has(0);
  @$pb.TagNumber(1)
  void clearName() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get description => $_getSZ(1);
  @$pb.TagNumber(2)
  set description($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasDescription() => $_has(1);
  @$pb.TagNumber(2)
  void clearDescription() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get schemaJson => $_getSZ(2);
  @$pb.TagNumber(3)
  set schemaJson($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasSchemaJson() => $_has(2);
  @$pb.TagNumber(3)
  void clearSchemaJson() => clearField(3);
}

class Budgets extends $pb.GeneratedMessage {
  factory Budgets({
    $core.int? maxOutputTokens,
    $core.int? maxInputTokens,
    $core.String? maxCostLevel,
  }) {
    final $result = create();
    if (maxOutputTokens != null) {
      $result.maxOutputTokens = maxOutputTokens;
    }
    if (maxInputTokens != null) {
      $result.maxInputTokens = maxInputTokens;
    }
    if (maxCostLevel != null) {
      $result.maxCostLevel = maxCostLevel;
    }
    return $result;
  }
  Budgets._() : super();
  factory Budgets.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory Budgets.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'Budgets', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'maxOutputTokens', $pb.PbFieldType.OU3)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'maxInputTokens', $pb.PbFieldType.OU3)
    ..aOS(3, _omitFieldNames ? '' : 'maxCostLevel')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  Budgets clone() => Budgets()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  Budgets copyWith(void Function(Budgets) updates) => super.copyWith((message) => updates(message as Budgets)) as Budgets;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Budgets create() => Budgets._();
  Budgets createEmptyInstance() => create();
  static $pb.PbList<Budgets> createRepeated() => $pb.PbList<Budgets>();
  @$core.pragma('dart2js:noInline')
  static Budgets getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Budgets>(create);
  static Budgets? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get maxOutputTokens => $_getIZ(0);
  @$pb.TagNumber(1)
  set maxOutputTokens($core.int v) { $_setUnsignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasMaxOutputTokens() => $_has(0);
  @$pb.TagNumber(1)
  void clearMaxOutputTokens() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get maxInputTokens => $_getIZ(1);
  @$pb.TagNumber(2)
  set maxInputTokens($core.int v) { $_setUnsignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasMaxInputTokens() => $_has(1);
  @$pb.TagNumber(2)
  void clearMaxInputTokens() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get maxCostLevel => $_getSZ(2);
  @$pb.TagNumber(3)
  set maxCostLevel($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasMaxCostLevel() => $_has(2);
  @$pb.TagNumber(3)
  void clearMaxCostLevel() => clearField(3);
}

class InferenceRequest extends $pb.GeneratedMessage {
  factory InferenceRequest({
    $core.String? requestId,
    $core.String? traceId,
    $core.String? userId,
    TaskType? taskType,
    Priority? priority,
    $core.String? schemaVersion,
    $core.String? outputSchema,
    $core.String? promptVersion,
    $core.String? idempotencyKey,
    Budgets? budgets,
    $core.Iterable<Message>? messages,
    $core.Iterable<ToolDefinition>? tools,
    ResponseFormat? responseFormat,
    $core.Map<$core.String, $core.String>? metadata,
    $core.Iterable<$core.String>? fileIds,
    ArtifactScope? artifactScope,
  }) {
    final $result = create();
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (userId != null) {
      $result.userId = userId;
    }
    if (taskType != null) {
      $result.taskType = taskType;
    }
    if (priority != null) {
      $result.priority = priority;
    }
    if (schemaVersion != null) {
      $result.schemaVersion = schemaVersion;
    }
    if (outputSchema != null) {
      $result.outputSchema = outputSchema;
    }
    if (promptVersion != null) {
      $result.promptVersion = promptVersion;
    }
    if (idempotencyKey != null) {
      $result.idempotencyKey = idempotencyKey;
    }
    if (budgets != null) {
      $result.budgets = budgets;
    }
    if (messages != null) {
      $result.messages.addAll(messages);
    }
    if (tools != null) {
      $result.tools.addAll(tools);
    }
    if (responseFormat != null) {
      $result.responseFormat = responseFormat;
    }
    if (metadata != null) {
      $result.metadata.addAll(metadata);
    }
    if (fileIds != null) {
      $result.fileIds.addAll(fileIds);
    }
    if (artifactScope != null) {
      $result.artifactScope = artifactScope;
    }
    return $result;
  }
  InferenceRequest._() : super();
  factory InferenceRequest.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InferenceRequest.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InferenceRequest', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..e<TaskType>(4, _omitFieldNames ? '' : 'taskType', $pb.PbFieldType.OE, defaultOrMaker: TaskType.TASK_TYPE_UNSPECIFIED, valueOf: TaskType.valueOf, enumValues: TaskType.values)
    ..e<Priority>(5, _omitFieldNames ? '' : 'priority', $pb.PbFieldType.OE, defaultOrMaker: Priority.PRIORITY_UNSPECIFIED, valueOf: Priority.valueOf, enumValues: Priority.values)
    ..aOS(6, _omitFieldNames ? '' : 'schemaVersion')
    ..aOS(7, _omitFieldNames ? '' : 'outputSchema')
    ..aOS(8, _omitFieldNames ? '' : 'promptVersion')
    ..aOS(9, _omitFieldNames ? '' : 'idempotencyKey')
    ..aOM<Budgets>(10, _omitFieldNames ? '' : 'budgets', subBuilder: Budgets.create)
    ..pc<Message>(11, _omitFieldNames ? '' : 'messages', $pb.PbFieldType.PM, subBuilder: Message.create)
    ..pc<ToolDefinition>(12, _omitFieldNames ? '' : 'tools', $pb.PbFieldType.PM, subBuilder: ToolDefinition.create)
    ..e<ResponseFormat>(13, _omitFieldNames ? '' : 'responseFormat', $pb.PbFieldType.OE, defaultOrMaker: ResponseFormat.RESPONSE_FORMAT_UNSPECIFIED, valueOf: ResponseFormat.valueOf, enumValues: ResponseFormat.values)
    ..m<$core.String, $core.String>(14, _omitFieldNames ? '' : 'metadata', entryClassName: 'InferenceRequest.MetadataEntry', keyFieldType: $pb.PbFieldType.OS, valueFieldType: $pb.PbFieldType.OS, packageName: const $pb.PackageName('sparkle.inference.v1'))
    ..pPS(15, _omitFieldNames ? '' : 'fileIds')
    ..e<ArtifactScope>(16, _omitFieldNames ? '' : 'artifactScope', $pb.PbFieldType.OE, defaultOrMaker: ArtifactScope.ARTIFACT_SCOPE_UNSPECIFIED, valueOf: ArtifactScope.valueOf, enumValues: ArtifactScope.values)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InferenceRequest clone() => InferenceRequest()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InferenceRequest copyWith(void Function(InferenceRequest) updates) => super.copyWith((message) => updates(message as InferenceRequest)) as InferenceRequest;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InferenceRequest create() => InferenceRequest._();
  InferenceRequest createEmptyInstance() => create();
  static $pb.PbList<InferenceRequest> createRepeated() => $pb.PbList<InferenceRequest>();
  @$core.pragma('dart2js:noInline')
  static InferenceRequest getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InferenceRequest>(create);
  static InferenceRequest? _defaultInstance;

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
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => clearField(3);

  @$pb.TagNumber(4)
  TaskType get taskType => $_getN(3);
  @$pb.TagNumber(4)
  set taskType(TaskType v) { setField(4, v); }
  @$pb.TagNumber(4)
  $core.bool hasTaskType() => $_has(3);
  @$pb.TagNumber(4)
  void clearTaskType() => clearField(4);

  @$pb.TagNumber(5)
  Priority get priority => $_getN(4);
  @$pb.TagNumber(5)
  set priority(Priority v) { setField(5, v); }
  @$pb.TagNumber(5)
  $core.bool hasPriority() => $_has(4);
  @$pb.TagNumber(5)
  void clearPriority() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get schemaVersion => $_getSZ(5);
  @$pb.TagNumber(6)
  set schemaVersion($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasSchemaVersion() => $_has(5);
  @$pb.TagNumber(6)
  void clearSchemaVersion() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get outputSchema => $_getSZ(6);
  @$pb.TagNumber(7)
  set outputSchema($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasOutputSchema() => $_has(6);
  @$pb.TagNumber(7)
  void clearOutputSchema() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get promptVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set promptVersion($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasPromptVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearPromptVersion() => clearField(8);

  @$pb.TagNumber(9)
  $core.String get idempotencyKey => $_getSZ(8);
  @$pb.TagNumber(9)
  set idempotencyKey($core.String v) { $_setString(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasIdempotencyKey() => $_has(8);
  @$pb.TagNumber(9)
  void clearIdempotencyKey() => clearField(9);

  @$pb.TagNumber(10)
  Budgets get budgets => $_getN(9);
  @$pb.TagNumber(10)
  set budgets(Budgets v) { setField(10, v); }
  @$pb.TagNumber(10)
  $core.bool hasBudgets() => $_has(9);
  @$pb.TagNumber(10)
  void clearBudgets() => clearField(10);
  @$pb.TagNumber(10)
  Budgets ensureBudgets() => $_ensure(9);

  @$pb.TagNumber(11)
  $core.List<Message> get messages => $_getList(10);

  @$pb.TagNumber(12)
  $core.List<ToolDefinition> get tools => $_getList(11);

  @$pb.TagNumber(13)
  ResponseFormat get responseFormat => $_getN(12);
  @$pb.TagNumber(13)
  set responseFormat(ResponseFormat v) { setField(13, v); }
  @$pb.TagNumber(13)
  $core.bool hasResponseFormat() => $_has(12);
  @$pb.TagNumber(13)
  void clearResponseFormat() => clearField(13);

  @$pb.TagNumber(14)
  $core.Map<$core.String, $core.String> get metadata => $_getMap(13);

  @$pb.TagNumber(15)
  $core.List<$core.String> get fileIds => $_getList(14);

  @$pb.TagNumber(16)
  ArtifactScope get artifactScope => $_getN(15);
  @$pb.TagNumber(16)
  set artifactScope(ArtifactScope v) { setField(16, v); }
  @$pb.TagNumber(16)
  $core.bool hasArtifactScope() => $_has(15);
  @$pb.TagNumber(16)
  void clearArtifactScope() => clearField(16);
}

class InferenceResponse extends $pb.GeneratedMessage {
  factory InferenceResponse({
    $core.String? requestId,
    $core.String? traceId,
    $core.bool? ok,
    $core.String? provider,
    $core.String? modelId,
    $core.String? content,
    ErrorReason? errorReason,
    $core.String? errorMessage,
    $core.int? promptTokens,
    $core.int? completionTokens,
  }) {
    final $result = create();
    if (requestId != null) {
      $result.requestId = requestId;
    }
    if (traceId != null) {
      $result.traceId = traceId;
    }
    if (ok != null) {
      $result.ok = ok;
    }
    if (provider != null) {
      $result.provider = provider;
    }
    if (modelId != null) {
      $result.modelId = modelId;
    }
    if (content != null) {
      $result.content = content;
    }
    if (errorReason != null) {
      $result.errorReason = errorReason;
    }
    if (errorMessage != null) {
      $result.errorMessage = errorMessage;
    }
    if (promptTokens != null) {
      $result.promptTokens = promptTokens;
    }
    if (completionTokens != null) {
      $result.completionTokens = completionTokens;
    }
    return $result;
  }
  InferenceResponse._() : super();
  factory InferenceResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory InferenceResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'InferenceResponse', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOB(3, _omitFieldNames ? '' : 'ok')
    ..aOS(4, _omitFieldNames ? '' : 'provider')
    ..aOS(5, _omitFieldNames ? '' : 'modelId')
    ..aOS(6, _omitFieldNames ? '' : 'content')
    ..e<ErrorReason>(7, _omitFieldNames ? '' : 'errorReason', $pb.PbFieldType.OE, defaultOrMaker: ErrorReason.ERROR_REASON_UNSPECIFIED, valueOf: ErrorReason.valueOf, enumValues: ErrorReason.values)
    ..aOS(8, _omitFieldNames ? '' : 'errorMessage')
    ..a<$core.int>(9, _omitFieldNames ? '' : 'promptTokens', $pb.PbFieldType.OU3)
    ..a<$core.int>(10, _omitFieldNames ? '' : 'completionTokens', $pb.PbFieldType.OU3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  InferenceResponse clone() => InferenceResponse()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  InferenceResponse copyWith(void Function(InferenceResponse) updates) => super.copyWith((message) => updates(message as InferenceResponse)) as InferenceResponse;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InferenceResponse create() => InferenceResponse._();
  InferenceResponse createEmptyInstance() => create();
  static $pb.PbList<InferenceResponse> createRepeated() => $pb.PbList<InferenceResponse>();
  @$core.pragma('dart2js:noInline')
  static InferenceResponse getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<InferenceResponse>(create);
  static InferenceResponse? _defaultInstance;

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
  $core.bool get ok => $_getBF(2);
  @$pb.TagNumber(3)
  set ok($core.bool v) { $_setBool(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasOk() => $_has(2);
  @$pb.TagNumber(3)
  void clearOk() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get provider => $_getSZ(3);
  @$pb.TagNumber(4)
  set provider($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasProvider() => $_has(3);
  @$pb.TagNumber(4)
  void clearProvider() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get modelId => $_getSZ(4);
  @$pb.TagNumber(5)
  set modelId($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasModelId() => $_has(4);
  @$pb.TagNumber(5)
  void clearModelId() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get content => $_getSZ(5);
  @$pb.TagNumber(6)
  set content($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasContent() => $_has(5);
  @$pb.TagNumber(6)
  void clearContent() => clearField(6);

  @$pb.TagNumber(7)
  ErrorReason get errorReason => $_getN(6);
  @$pb.TagNumber(7)
  set errorReason(ErrorReason v) { setField(7, v); }
  @$pb.TagNumber(7)
  $core.bool hasErrorReason() => $_has(6);
  @$pb.TagNumber(7)
  void clearErrorReason() => clearField(7);

  @$pb.TagNumber(8)
  $core.String get errorMessage => $_getSZ(7);
  @$pb.TagNumber(8)
  set errorMessage($core.String v) { $_setString(7, v); }
  @$pb.TagNumber(8)
  $core.bool hasErrorMessage() => $_has(7);
  @$pb.TagNumber(8)
  void clearErrorMessage() => clearField(8);

  @$pb.TagNumber(9)
  $core.int get promptTokens => $_getIZ(8);
  @$pb.TagNumber(9)
  set promptTokens($core.int v) { $_setUnsignedInt32(8, v); }
  @$pb.TagNumber(9)
  $core.bool hasPromptTokens() => $_has(8);
  @$pb.TagNumber(9)
  void clearPromptTokens() => clearField(9);

  @$pb.TagNumber(10)
  $core.int get completionTokens => $_getIZ(9);
  @$pb.TagNumber(10)
  set completionTokens($core.int v) { $_setUnsignedInt32(9, v); }
  @$pb.TagNumber(10)
  $core.bool hasCompletionTokens() => $_has(9);
  @$pb.TagNumber(10)
  void clearCompletionTokens() => clearField(10);
}

class TranslationSegment extends $pb.GeneratedMessage {
  factory TranslationSegment({
    $core.String? id,
    $core.String? text,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (text != null) {
      $result.text = text;
    }
    return $result;
  }
  TranslationSegment._() : super();
  factory TranslationSegment.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TranslationSegment.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TranslationSegment', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'text')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TranslationSegment clone() => TranslationSegment()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TranslationSegment copyWith(void Function(TranslationSegment) updates) => super.copyWith((message) => updates(message as TranslationSegment)) as TranslationSegment;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationSegment create() => TranslationSegment._();
  TranslationSegment createEmptyInstance() => create();
  static $pb.PbList<TranslationSegment> createRepeated() => $pb.PbList<TranslationSegment>();
  @$core.pragma('dart2js:noInline')
  static TranslationSegment getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TranslationSegment>(create);
  static TranslationSegment? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get text => $_getSZ(1);
  @$pb.TagNumber(2)
  set text($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasText() => $_has(1);
  @$pb.TagNumber(2)
  void clearText() => clearField(2);
}

class TranslationInput extends $pb.GeneratedMessage {
  factory TranslationInput({
    $core.Iterable<TranslationSegment>? segments,
    $core.String? sourceLang,
    $core.String? targetLang,
    $core.String? domain,
    $core.String? style,
    $core.String? glossaryId,
    $core.String? segmenterVersion,
  }) {
    final $result = create();
    if (segments != null) {
      $result.segments.addAll(segments);
    }
    if (sourceLang != null) {
      $result.sourceLang = sourceLang;
    }
    if (targetLang != null) {
      $result.targetLang = targetLang;
    }
    if (domain != null) {
      $result.domain = domain;
    }
    if (style != null) {
      $result.style = style;
    }
    if (glossaryId != null) {
      $result.glossaryId = glossaryId;
    }
    if (segmenterVersion != null) {
      $result.segmenterVersion = segmenterVersion;
    }
    return $result;
  }
  TranslationInput._() : super();
  factory TranslationInput.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TranslationInput.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TranslationInput', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..pc<TranslationSegment>(1, _omitFieldNames ? '' : 'segments', $pb.PbFieldType.PM, subBuilder: TranslationSegment.create)
    ..aOS(2, _omitFieldNames ? '' : 'sourceLang')
    ..aOS(3, _omitFieldNames ? '' : 'targetLang')
    ..aOS(4, _omitFieldNames ? '' : 'domain')
    ..aOS(5, _omitFieldNames ? '' : 'style')
    ..aOS(6, _omitFieldNames ? '' : 'glossaryId')
    ..aOS(7, _omitFieldNames ? '' : 'segmenterVersion')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TranslationInput clone() => TranslationInput()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TranslationInput copyWith(void Function(TranslationInput) updates) => super.copyWith((message) => updates(message as TranslationInput)) as TranslationInput;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationInput create() => TranslationInput._();
  TranslationInput createEmptyInstance() => create();
  static $pb.PbList<TranslationInput> createRepeated() => $pb.PbList<TranslationInput>();
  @$core.pragma('dart2js:noInline')
  static TranslationInput getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TranslationInput>(create);
  static TranslationInput? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<TranslationSegment> get segments => $_getList(0);

  @$pb.TagNumber(2)
  $core.String get sourceLang => $_getSZ(1);
  @$pb.TagNumber(2)
  set sourceLang($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasSourceLang() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceLang() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get targetLang => $_getSZ(2);
  @$pb.TagNumber(3)
  set targetLang($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTargetLang() => $_has(2);
  @$pb.TagNumber(3)
  void clearTargetLang() => clearField(3);

  @$pb.TagNumber(4)
  $core.String get domain => $_getSZ(3);
  @$pb.TagNumber(4)
  set domain($core.String v) { $_setString(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasDomain() => $_has(3);
  @$pb.TagNumber(4)
  void clearDomain() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get style => $_getSZ(4);
  @$pb.TagNumber(5)
  set style($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasStyle() => $_has(4);
  @$pb.TagNumber(5)
  void clearStyle() => clearField(5);

  @$pb.TagNumber(6)
  $core.String get glossaryId => $_getSZ(5);
  @$pb.TagNumber(6)
  set glossaryId($core.String v) { $_setString(5, v); }
  @$pb.TagNumber(6)
  $core.bool hasGlossaryId() => $_has(5);
  @$pb.TagNumber(6)
  void clearGlossaryId() => clearField(6);

  @$pb.TagNumber(7)
  $core.String get segmenterVersion => $_getSZ(6);
  @$pb.TagNumber(7)
  set segmenterVersion($core.String v) { $_setString(6, v); }
  @$pb.TagNumber(7)
  $core.bool hasSegmenterVersion() => $_has(6);
  @$pb.TagNumber(7)
  void clearSegmenterVersion() => clearField(7);
}

class AlignmentSpan extends $pb.GeneratedMessage {
  factory AlignmentSpan({
    $core.int? sourceStart,
    $core.int? sourceEnd,
    $core.int? targetStart,
    $core.int? targetEnd,
    $core.String? type,
  }) {
    final $result = create();
    if (sourceStart != null) {
      $result.sourceStart = sourceStart;
    }
    if (sourceEnd != null) {
      $result.sourceEnd = sourceEnd;
    }
    if (targetStart != null) {
      $result.targetStart = targetStart;
    }
    if (targetEnd != null) {
      $result.targetEnd = targetEnd;
    }
    if (type != null) {
      $result.type = type;
    }
    return $result;
  }
  AlignmentSpan._() : super();
  factory AlignmentSpan.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory AlignmentSpan.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'AlignmentSpan', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..a<$core.int>(1, _omitFieldNames ? '' : 'sourceStart', $pb.PbFieldType.O3)
    ..a<$core.int>(2, _omitFieldNames ? '' : 'sourceEnd', $pb.PbFieldType.O3)
    ..a<$core.int>(3, _omitFieldNames ? '' : 'targetStart', $pb.PbFieldType.O3)
    ..a<$core.int>(4, _omitFieldNames ? '' : 'targetEnd', $pb.PbFieldType.O3)
    ..aOS(5, _omitFieldNames ? '' : 'type')
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  AlignmentSpan clone() => AlignmentSpan()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  AlignmentSpan copyWith(void Function(AlignmentSpan) updates) => super.copyWith((message) => updates(message as AlignmentSpan)) as AlignmentSpan;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AlignmentSpan create() => AlignmentSpan._();
  AlignmentSpan createEmptyInstance() => create();
  static $pb.PbList<AlignmentSpan> createRepeated() => $pb.PbList<AlignmentSpan>();
  @$core.pragma('dart2js:noInline')
  static AlignmentSpan getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<AlignmentSpan>(create);
  static AlignmentSpan? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get sourceStart => $_getIZ(0);
  @$pb.TagNumber(1)
  set sourceStart($core.int v) { $_setSignedInt32(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasSourceStart() => $_has(0);
  @$pb.TagNumber(1)
  void clearSourceStart() => clearField(1);

  @$pb.TagNumber(2)
  $core.int get sourceEnd => $_getIZ(1);
  @$pb.TagNumber(2)
  set sourceEnd($core.int v) { $_setSignedInt32(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasSourceEnd() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceEnd() => clearField(2);

  @$pb.TagNumber(3)
  $core.int get targetStart => $_getIZ(2);
  @$pb.TagNumber(3)
  set targetStart($core.int v) { $_setSignedInt32(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasTargetStart() => $_has(2);
  @$pb.TagNumber(3)
  void clearTargetStart() => clearField(3);

  @$pb.TagNumber(4)
  $core.int get targetEnd => $_getIZ(3);
  @$pb.TagNumber(4)
  set targetEnd($core.int v) { $_setSignedInt32(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasTargetEnd() => $_has(3);
  @$pb.TagNumber(4)
  void clearTargetEnd() => clearField(4);

  @$pb.TagNumber(5)
  $core.String get type => $_getSZ(4);
  @$pb.TagNumber(5)
  set type($core.String v) { $_setString(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasType() => $_has(4);
  @$pb.TagNumber(5)
  void clearType() => clearField(5);
}

class TranslatedSegment extends $pb.GeneratedMessage {
  factory TranslatedSegment({
    $core.String? id,
    $core.String? translation,
    $core.Iterable<$core.String>? notes,
    $core.Iterable<AlignmentSpan>? spans,
  }) {
    final $result = create();
    if (id != null) {
      $result.id = id;
    }
    if (translation != null) {
      $result.translation = translation;
    }
    if (notes != null) {
      $result.notes.addAll(notes);
    }
    if (spans != null) {
      $result.spans.addAll(spans);
    }
    return $result;
  }
  TranslatedSegment._() : super();
  factory TranslatedSegment.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TranslatedSegment.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TranslatedSegment', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'translation')
    ..pPS(3, _omitFieldNames ? '' : 'notes')
    ..pc<AlignmentSpan>(4, _omitFieldNames ? '' : 'spans', $pb.PbFieldType.PM, subBuilder: AlignmentSpan.create)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TranslatedSegment clone() => TranslatedSegment()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TranslatedSegment copyWith(void Function(TranslatedSegment) updates) => super.copyWith((message) => updates(message as TranslatedSegment)) as TranslatedSegment;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslatedSegment create() => TranslatedSegment._();
  TranslatedSegment createEmptyInstance() => create();
  static $pb.PbList<TranslatedSegment> createRepeated() => $pb.PbList<TranslatedSegment>();
  @$core.pragma('dart2js:noInline')
  static TranslatedSegment getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TranslatedSegment>(create);
  static TranslatedSegment? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String v) { $_setString(0, v); }
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => clearField(1);

  @$pb.TagNumber(2)
  $core.String get translation => $_getSZ(1);
  @$pb.TagNumber(2)
  set translation($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasTranslation() => $_has(1);
  @$pb.TagNumber(2)
  void clearTranslation() => clearField(2);

  @$pb.TagNumber(3)
  $core.List<$core.String> get notes => $_getList(2);

  @$pb.TagNumber(4)
  $core.List<AlignmentSpan> get spans => $_getList(3);
}

class TranslationOutput extends $pb.GeneratedMessage {
  factory TranslationOutput({
    $core.Iterable<TranslatedSegment>? segments,
    $core.String? provider,
    $core.String? modelId,
    $core.bool? cacheHit,
    $core.int? latencyMs,
  }) {
    final $result = create();
    if (segments != null) {
      $result.segments.addAll(segments);
    }
    if (provider != null) {
      $result.provider = provider;
    }
    if (modelId != null) {
      $result.modelId = modelId;
    }
    if (cacheHit != null) {
      $result.cacheHit = cacheHit;
    }
    if (latencyMs != null) {
      $result.latencyMs = latencyMs;
    }
    return $result;
  }
  TranslationOutput._() : super();
  factory TranslationOutput.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromBuffer(i, r);
  factory TranslationOutput.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) => create()..mergeFromJson(i, r);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(_omitMessageNames ? '' : 'TranslationOutput', package: const $pb.PackageName(_omitMessageNames ? '' : 'sparkle.inference.v1'), createEmptyInstance: create)
    ..pc<TranslatedSegment>(1, _omitFieldNames ? '' : 'segments', $pb.PbFieldType.PM, subBuilder: TranslatedSegment.create)
    ..aOS(2, _omitFieldNames ? '' : 'provider')
    ..aOS(3, _omitFieldNames ? '' : 'modelId')
    ..aOB(4, _omitFieldNames ? '' : 'cacheHit')
    ..a<$core.int>(5, _omitFieldNames ? '' : 'latencyMs', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.deepCopy] instead. '
  'Will be removed in next major version')
  TranslationOutput clone() => TranslationOutput()..mergeFromMessage(this);
  @$core.Deprecated(
  'Using this can add significant overhead to your binary. '
  'Use [GeneratedMessageGenericExtensions.rebuild] instead. '
  'Will be removed in next major version')
  TranslationOutput copyWith(void Function(TranslationOutput) updates) => super.copyWith((message) => updates(message as TranslationOutput)) as TranslationOutput;

  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationOutput create() => TranslationOutput._();
  TranslationOutput createEmptyInstance() => create();
  static $pb.PbList<TranslationOutput> createRepeated() => $pb.PbList<TranslationOutput>();
  @$core.pragma('dart2js:noInline')
  static TranslationOutput getDefault() => _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<TranslationOutput>(create);
  static TranslationOutput? _defaultInstance;

  @$pb.TagNumber(1)
  $core.List<TranslatedSegment> get segments => $_getList(0);

  @$pb.TagNumber(2)
  $core.String get provider => $_getSZ(1);
  @$pb.TagNumber(2)
  set provider($core.String v) { $_setString(1, v); }
  @$pb.TagNumber(2)
  $core.bool hasProvider() => $_has(1);
  @$pb.TagNumber(2)
  void clearProvider() => clearField(2);

  @$pb.TagNumber(3)
  $core.String get modelId => $_getSZ(2);
  @$pb.TagNumber(3)
  set modelId($core.String v) { $_setString(2, v); }
  @$pb.TagNumber(3)
  $core.bool hasModelId() => $_has(2);
  @$pb.TagNumber(3)
  void clearModelId() => clearField(3);

  @$pb.TagNumber(4)
  $core.bool get cacheHit => $_getBF(3);
  @$pb.TagNumber(4)
  set cacheHit($core.bool v) { $_setBool(3, v); }
  @$pb.TagNumber(4)
  $core.bool hasCacheHit() => $_has(3);
  @$pb.TagNumber(4)
  void clearCacheHit() => clearField(4);

  @$pb.TagNumber(5)
  $core.int get latencyMs => $_getIZ(4);
  @$pb.TagNumber(5)
  set latencyMs($core.int v) { $_setSignedInt32(4, v); }
  @$pb.TagNumber(5)
  $core.bool hasLatencyMs() => $_has(4);
  @$pb.TagNumber(5)
  void clearLatencyMs() => clearField(5);
}


const _omitFieldNames = $core.bool.fromEnvironment('protobuf.omit_field_names');
const _omitMessageNames = $core.bool.fromEnvironment('protobuf.omit_message_names');
