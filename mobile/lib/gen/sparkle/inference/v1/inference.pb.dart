// This is a generated file - do not edit.
//
// Generated from sparkle/inference/v1/inference.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

import 'inference.pbenum.dart';

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'inference.pbenum.dart';

class Message extends $pb.GeneratedMessage {
  factory Message({
    $core.String? role,
    $core.String? content,
  }) {
    final result = create();
    if (role != null) result.role = role;
    if (content != null) result.content = content;
    return result;
  }

  Message._();

  factory Message.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Message.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Message',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'role')
    ..aOS(2, _omitFieldNames ? '' : 'content')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Message clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Message copyWith(void Function(Message) updates) =>
      super.copyWith((message) => updates(message as Message)) as Message;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Message create() => Message._();
  @$core.override
  Message createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Message getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Message>(create);
  static Message? _defaultInstance;

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
}

class ToolDefinition extends $pb.GeneratedMessage {
  factory ToolDefinition({
    $core.String? name,
    $core.String? description,
    $core.String? schemaJson,
  }) {
    final result = create();
    if (name != null) result.name = name;
    if (description != null) result.description = description;
    if (schemaJson != null) result.schemaJson = schemaJson;
    return result;
  }

  ToolDefinition._();

  factory ToolDefinition.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory ToolDefinition.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'ToolDefinition',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'name')
    ..aOS(2, _omitFieldNames ? '' : 'description')
    ..aOS(3, _omitFieldNames ? '' : 'schemaJson')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolDefinition clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  ToolDefinition copyWith(void Function(ToolDefinition) updates) =>
      super.copyWith((message) => updates(message as ToolDefinition))
          as ToolDefinition;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static ToolDefinition create() => ToolDefinition._();
  @$core.override
  ToolDefinition createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static ToolDefinition getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<ToolDefinition>(create);
  static ToolDefinition? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get name => $_getSZ(0);
  @$pb.TagNumber(1)
  set name($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasName() => $_has(0);
  @$pb.TagNumber(1)
  void clearName() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get description => $_getSZ(1);
  @$pb.TagNumber(2)
  set description($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDescription() => $_has(1);
  @$pb.TagNumber(2)
  void clearDescription() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get schemaJson => $_getSZ(2);
  @$pb.TagNumber(3)
  set schemaJson($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasSchemaJson() => $_has(2);
  @$pb.TagNumber(3)
  void clearSchemaJson() => $_clearField(3);
}

class Budgets extends $pb.GeneratedMessage {
  factory Budgets({
    $core.int? maxOutputTokens,
    $core.int? maxInputTokens,
    $core.String? maxCostLevel,
  }) {
    final result = create();
    if (maxOutputTokens != null) result.maxOutputTokens = maxOutputTokens;
    if (maxInputTokens != null) result.maxInputTokens = maxInputTokens;
    if (maxCostLevel != null) result.maxCostLevel = maxCostLevel;
    return result;
  }

  Budgets._();

  factory Budgets.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory Budgets.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'Budgets',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'maxOutputTokens',
        fieldType: $pb.PbFieldType.OU3)
    ..aI(2, _omitFieldNames ? '' : 'maxInputTokens',
        fieldType: $pb.PbFieldType.OU3)
    ..aOS(3, _omitFieldNames ? '' : 'maxCostLevel')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Budgets clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  Budgets copyWith(void Function(Budgets) updates) =>
      super.copyWith((message) => updates(message as Budgets)) as Budgets;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static Budgets create() => Budgets._();
  @$core.override
  Budgets createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static Budgets getDefault() =>
      _defaultInstance ??= $pb.GeneratedMessage.$_defaultFor<Budgets>(create);
  static Budgets? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get maxOutputTokens => $_getIZ(0);
  @$pb.TagNumber(1)
  set maxOutputTokens($core.int value) => $_setUnsignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasMaxOutputTokens() => $_has(0);
  @$pb.TagNumber(1)
  void clearMaxOutputTokens() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get maxInputTokens => $_getIZ(1);
  @$pb.TagNumber(2)
  set maxInputTokens($core.int value) => $_setUnsignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMaxInputTokens() => $_has(1);
  @$pb.TagNumber(2)
  void clearMaxInputTokens() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get maxCostLevel => $_getSZ(2);
  @$pb.TagNumber(3)
  set maxCostLevel($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasMaxCostLevel() => $_has(2);
  @$pb.TagNumber(3)
  void clearMaxCostLevel() => $_clearField(3);
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
    $core.Iterable<$core.MapEntry<$core.String, $core.String>>? metadata,
    $core.Iterable<$core.String>? fileIds,
    ArtifactScope? artifactScope,
  }) {
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (traceId != null) result.traceId = traceId;
    if (userId != null) result.userId = userId;
    if (taskType != null) result.taskType = taskType;
    if (priority != null) result.priority = priority;
    if (schemaVersion != null) result.schemaVersion = schemaVersion;
    if (outputSchema != null) result.outputSchema = outputSchema;
    if (promptVersion != null) result.promptVersion = promptVersion;
    if (idempotencyKey != null) result.idempotencyKey = idempotencyKey;
    if (budgets != null) result.budgets = budgets;
    if (messages != null) result.messages.addAll(messages);
    if (tools != null) result.tools.addAll(tools);
    if (responseFormat != null) result.responseFormat = responseFormat;
    if (metadata != null) result.metadata.addEntries(metadata);
    if (fileIds != null) result.fileIds.addAll(fileIds);
    if (artifactScope != null) result.artifactScope = artifactScope;
    return result;
  }

  InferenceRequest._();

  factory InferenceRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InferenceRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InferenceRequest',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOS(3, _omitFieldNames ? '' : 'userId')
    ..aE<TaskType>(4, _omitFieldNames ? '' : 'taskType',
        enumValues: TaskType.values)
    ..aE<Priority>(5, _omitFieldNames ? '' : 'priority',
        enumValues: Priority.values)
    ..aOS(6, _omitFieldNames ? '' : 'schemaVersion')
    ..aOS(7, _omitFieldNames ? '' : 'outputSchema')
    ..aOS(8, _omitFieldNames ? '' : 'promptVersion')
    ..aOS(9, _omitFieldNames ? '' : 'idempotencyKey')
    ..aOM<Budgets>(10, _omitFieldNames ? '' : 'budgets',
        subBuilder: Budgets.create)
    ..pPM<Message>(11, _omitFieldNames ? '' : 'messages',
        subBuilder: Message.create)
    ..pPM<ToolDefinition>(12, _omitFieldNames ? '' : 'tools',
        subBuilder: ToolDefinition.create)
    ..aE<ResponseFormat>(13, _omitFieldNames ? '' : 'responseFormat',
        enumValues: ResponseFormat.values)
    ..m<$core.String, $core.String>(14, _omitFieldNames ? '' : 'metadata',
        entryClassName: 'InferenceRequest.MetadataEntry',
        keyFieldType: $pb.PbFieldType.OS,
        valueFieldType: $pb.PbFieldType.OS,
        packageName: const $pb.PackageName('sparkle.inference.v1'))
    ..pPS(15, _omitFieldNames ? '' : 'fileIds')
    ..aE<ArtifactScope>(16, _omitFieldNames ? '' : 'artifactScope',
        enumValues: ArtifactScope.values)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InferenceRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InferenceRequest copyWith(void Function(InferenceRequest) updates) =>
      super.copyWith((message) => updates(message as InferenceRequest))
          as InferenceRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InferenceRequest create() => InferenceRequest._();
  @$core.override
  InferenceRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InferenceRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InferenceRequest>(create);
  static InferenceRequest? _defaultInstance;

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
  $core.String get userId => $_getSZ(2);
  @$pb.TagNumber(3)
  set userId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasUserId() => $_has(2);
  @$pb.TagNumber(3)
  void clearUserId() => $_clearField(3);

  @$pb.TagNumber(4)
  TaskType get taskType => $_getN(3);
  @$pb.TagNumber(4)
  set taskType(TaskType value) => $_setField(4, value);
  @$pb.TagNumber(4)
  $core.bool hasTaskType() => $_has(3);
  @$pb.TagNumber(4)
  void clearTaskType() => $_clearField(4);

  @$pb.TagNumber(5)
  Priority get priority => $_getN(4);
  @$pb.TagNumber(5)
  set priority(Priority value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasPriority() => $_has(4);
  @$pb.TagNumber(5)
  void clearPriority() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get schemaVersion => $_getSZ(5);
  @$pb.TagNumber(6)
  set schemaVersion($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSchemaVersion() => $_has(5);
  @$pb.TagNumber(6)
  void clearSchemaVersion() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get outputSchema => $_getSZ(6);
  @$pb.TagNumber(7)
  set outputSchema($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasOutputSchema() => $_has(6);
  @$pb.TagNumber(7)
  void clearOutputSchema() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get promptVersion => $_getSZ(7);
  @$pb.TagNumber(8)
  set promptVersion($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasPromptVersion() => $_has(7);
  @$pb.TagNumber(8)
  void clearPromptVersion() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.String get idempotencyKey => $_getSZ(8);
  @$pb.TagNumber(9)
  set idempotencyKey($core.String value) => $_setString(8, value);
  @$pb.TagNumber(9)
  $core.bool hasIdempotencyKey() => $_has(8);
  @$pb.TagNumber(9)
  void clearIdempotencyKey() => $_clearField(9);

  @$pb.TagNumber(10)
  Budgets get budgets => $_getN(9);
  @$pb.TagNumber(10)
  set budgets(Budgets value) => $_setField(10, value);
  @$pb.TagNumber(10)
  $core.bool hasBudgets() => $_has(9);
  @$pb.TagNumber(10)
  void clearBudgets() => $_clearField(10);
  @$pb.TagNumber(10)
  Budgets ensureBudgets() => $_ensure(9);

  @$pb.TagNumber(11)
  $pb.PbList<Message> get messages => $_getList(10);

  @$pb.TagNumber(12)
  $pb.PbList<ToolDefinition> get tools => $_getList(11);

  @$pb.TagNumber(13)
  ResponseFormat get responseFormat => $_getN(12);
  @$pb.TagNumber(13)
  set responseFormat(ResponseFormat value) => $_setField(13, value);
  @$pb.TagNumber(13)
  $core.bool hasResponseFormat() => $_has(12);
  @$pb.TagNumber(13)
  void clearResponseFormat() => $_clearField(13);

  @$pb.TagNumber(14)
  $pb.PbMap<$core.String, $core.String> get metadata => $_getMap(13);

  @$pb.TagNumber(15)
  $pb.PbList<$core.String> get fileIds => $_getList(14);

  @$pb.TagNumber(16)
  ArtifactScope get artifactScope => $_getN(15);
  @$pb.TagNumber(16)
  set artifactScope(ArtifactScope value) => $_setField(16, value);
  @$pb.TagNumber(16)
  $core.bool hasArtifactScope() => $_has(15);
  @$pb.TagNumber(16)
  void clearArtifactScope() => $_clearField(16);
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
    final result = create();
    if (requestId != null) result.requestId = requestId;
    if (traceId != null) result.traceId = traceId;
    if (ok != null) result.ok = ok;
    if (provider != null) result.provider = provider;
    if (modelId != null) result.modelId = modelId;
    if (content != null) result.content = content;
    if (errorReason != null) result.errorReason = errorReason;
    if (errorMessage != null) result.errorMessage = errorMessage;
    if (promptTokens != null) result.promptTokens = promptTokens;
    if (completionTokens != null) result.completionTokens = completionTokens;
    return result;
  }

  InferenceResponse._();

  factory InferenceResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory InferenceResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'InferenceResponse',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'requestId')
    ..aOS(2, _omitFieldNames ? '' : 'traceId')
    ..aOB(3, _omitFieldNames ? '' : 'ok')
    ..aOS(4, _omitFieldNames ? '' : 'provider')
    ..aOS(5, _omitFieldNames ? '' : 'modelId')
    ..aOS(6, _omitFieldNames ? '' : 'content')
    ..aE<ErrorReason>(7, _omitFieldNames ? '' : 'errorReason',
        enumValues: ErrorReason.values)
    ..aOS(8, _omitFieldNames ? '' : 'errorMessage')
    ..aI(9, _omitFieldNames ? '' : 'promptTokens',
        fieldType: $pb.PbFieldType.OU3)
    ..aI(10, _omitFieldNames ? '' : 'completionTokens',
        fieldType: $pb.PbFieldType.OU3)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InferenceResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  InferenceResponse copyWith(void Function(InferenceResponse) updates) =>
      super.copyWith((message) => updates(message as InferenceResponse))
          as InferenceResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static InferenceResponse create() => InferenceResponse._();
  @$core.override
  InferenceResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static InferenceResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<InferenceResponse>(create);
  static InferenceResponse? _defaultInstance;

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
  $core.bool get ok => $_getBF(2);
  @$pb.TagNumber(3)
  set ok($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasOk() => $_has(2);
  @$pb.TagNumber(3)
  void clearOk() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get provider => $_getSZ(3);
  @$pb.TagNumber(4)
  set provider($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasProvider() => $_has(3);
  @$pb.TagNumber(4)
  void clearProvider() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get modelId => $_getSZ(4);
  @$pb.TagNumber(5)
  set modelId($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasModelId() => $_has(4);
  @$pb.TagNumber(5)
  void clearModelId() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get content => $_getSZ(5);
  @$pb.TagNumber(6)
  set content($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasContent() => $_has(5);
  @$pb.TagNumber(6)
  void clearContent() => $_clearField(6);

  @$pb.TagNumber(7)
  ErrorReason get errorReason => $_getN(6);
  @$pb.TagNumber(7)
  set errorReason(ErrorReason value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasErrorReason() => $_has(6);
  @$pb.TagNumber(7)
  void clearErrorReason() => $_clearField(7);

  @$pb.TagNumber(8)
  $core.String get errorMessage => $_getSZ(7);
  @$pb.TagNumber(8)
  set errorMessage($core.String value) => $_setString(7, value);
  @$pb.TagNumber(8)
  $core.bool hasErrorMessage() => $_has(7);
  @$pb.TagNumber(8)
  void clearErrorMessage() => $_clearField(8);

  @$pb.TagNumber(9)
  $core.int get promptTokens => $_getIZ(8);
  @$pb.TagNumber(9)
  set promptTokens($core.int value) => $_setUnsignedInt32(8, value);
  @$pb.TagNumber(9)
  $core.bool hasPromptTokens() => $_has(8);
  @$pb.TagNumber(9)
  void clearPromptTokens() => $_clearField(9);

  @$pb.TagNumber(10)
  $core.int get completionTokens => $_getIZ(9);
  @$pb.TagNumber(10)
  set completionTokens($core.int value) => $_setUnsignedInt32(9, value);
  @$pb.TagNumber(10)
  $core.bool hasCompletionTokens() => $_has(9);
  @$pb.TagNumber(10)
  void clearCompletionTokens() => $_clearField(10);
}

class TranslationSegment extends $pb.GeneratedMessage {
  factory TranslationSegment({
    $core.String? id,
    $core.String? text,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (text != null) result.text = text;
    return result;
  }

  TranslationSegment._();

  factory TranslationSegment.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranslationSegment.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranslationSegment',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'text')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationSegment clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationSegment copyWith(void Function(TranslationSegment) updates) =>
      super.copyWith((message) => updates(message as TranslationSegment))
          as TranslationSegment;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationSegment create() => TranslationSegment._();
  @$core.override
  TranslationSegment createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranslationSegment getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranslationSegment>(create);
  static TranslationSegment? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get text => $_getSZ(1);
  @$pb.TagNumber(2)
  set text($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasText() => $_has(1);
  @$pb.TagNumber(2)
  void clearText() => $_clearField(2);
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
    final result = create();
    if (segments != null) result.segments.addAll(segments);
    if (sourceLang != null) result.sourceLang = sourceLang;
    if (targetLang != null) result.targetLang = targetLang;
    if (domain != null) result.domain = domain;
    if (style != null) result.style = style;
    if (glossaryId != null) result.glossaryId = glossaryId;
    if (segmenterVersion != null) result.segmenterVersion = segmenterVersion;
    return result;
  }

  TranslationInput._();

  factory TranslationInput.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranslationInput.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranslationInput',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..pPM<TranslationSegment>(1, _omitFieldNames ? '' : 'segments',
        subBuilder: TranslationSegment.create)
    ..aOS(2, _omitFieldNames ? '' : 'sourceLang')
    ..aOS(3, _omitFieldNames ? '' : 'targetLang')
    ..aOS(4, _omitFieldNames ? '' : 'domain')
    ..aOS(5, _omitFieldNames ? '' : 'style')
    ..aOS(6, _omitFieldNames ? '' : 'glossaryId')
    ..aOS(7, _omitFieldNames ? '' : 'segmenterVersion')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationInput clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationInput copyWith(void Function(TranslationInput) updates) =>
      super.copyWith((message) => updates(message as TranslationInput))
          as TranslationInput;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationInput create() => TranslationInput._();
  @$core.override
  TranslationInput createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranslationInput getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranslationInput>(create);
  static TranslationInput? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<TranslationSegment> get segments => $_getList(0);

  @$pb.TagNumber(2)
  $core.String get sourceLang => $_getSZ(1);
  @$pb.TagNumber(2)
  set sourceLang($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSourceLang() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceLang() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get targetLang => $_getSZ(2);
  @$pb.TagNumber(3)
  set targetLang($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTargetLang() => $_has(2);
  @$pb.TagNumber(3)
  void clearTargetLang() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.String get domain => $_getSZ(3);
  @$pb.TagNumber(4)
  set domain($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasDomain() => $_has(3);
  @$pb.TagNumber(4)
  void clearDomain() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get style => $_getSZ(4);
  @$pb.TagNumber(5)
  set style($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasStyle() => $_has(4);
  @$pb.TagNumber(5)
  void clearStyle() => $_clearField(5);

  @$pb.TagNumber(6)
  $core.String get glossaryId => $_getSZ(5);
  @$pb.TagNumber(6)
  set glossaryId($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasGlossaryId() => $_has(5);
  @$pb.TagNumber(6)
  void clearGlossaryId() => $_clearField(6);

  @$pb.TagNumber(7)
  $core.String get segmenterVersion => $_getSZ(6);
  @$pb.TagNumber(7)
  set segmenterVersion($core.String value) => $_setString(6, value);
  @$pb.TagNumber(7)
  $core.bool hasSegmenterVersion() => $_has(6);
  @$pb.TagNumber(7)
  void clearSegmenterVersion() => $_clearField(7);
}

class AlignmentSpan extends $pb.GeneratedMessage {
  factory AlignmentSpan({
    $core.int? sourceStart,
    $core.int? sourceEnd,
    $core.int? targetStart,
    $core.int? targetEnd,
    $core.String? type,
  }) {
    final result = create();
    if (sourceStart != null) result.sourceStart = sourceStart;
    if (sourceEnd != null) result.sourceEnd = sourceEnd;
    if (targetStart != null) result.targetStart = targetStart;
    if (targetEnd != null) result.targetEnd = targetEnd;
    if (type != null) result.type = type;
    return result;
  }

  AlignmentSpan._();

  factory AlignmentSpan.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory AlignmentSpan.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'AlignmentSpan',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aI(1, _omitFieldNames ? '' : 'sourceStart')
    ..aI(2, _omitFieldNames ? '' : 'sourceEnd')
    ..aI(3, _omitFieldNames ? '' : 'targetStart')
    ..aI(4, _omitFieldNames ? '' : 'targetEnd')
    ..aOS(5, _omitFieldNames ? '' : 'type')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AlignmentSpan clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AlignmentSpan copyWith(void Function(AlignmentSpan) updates) =>
      super.copyWith((message) => updates(message as AlignmentSpan))
          as AlignmentSpan;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AlignmentSpan create() => AlignmentSpan._();
  @$core.override
  AlignmentSpan createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static AlignmentSpan getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<AlignmentSpan>(create);
  static AlignmentSpan? _defaultInstance;

  @$pb.TagNumber(1)
  $core.int get sourceStart => $_getIZ(0);
  @$pb.TagNumber(1)
  set sourceStart($core.int value) => $_setSignedInt32(0, value);
  @$pb.TagNumber(1)
  $core.bool hasSourceStart() => $_has(0);
  @$pb.TagNumber(1)
  void clearSourceStart() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.int get sourceEnd => $_getIZ(1);
  @$pb.TagNumber(2)
  set sourceEnd($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSourceEnd() => $_has(1);
  @$pb.TagNumber(2)
  void clearSourceEnd() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.int get targetStart => $_getIZ(2);
  @$pb.TagNumber(3)
  set targetStart($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasTargetStart() => $_has(2);
  @$pb.TagNumber(3)
  void clearTargetStart() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.int get targetEnd => $_getIZ(3);
  @$pb.TagNumber(4)
  set targetEnd($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasTargetEnd() => $_has(3);
  @$pb.TagNumber(4)
  void clearTargetEnd() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.String get type => $_getSZ(4);
  @$pb.TagNumber(5)
  set type($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasType() => $_has(4);
  @$pb.TagNumber(5)
  void clearType() => $_clearField(5);
}

class TranslatedSegment extends $pb.GeneratedMessage {
  factory TranslatedSegment({
    $core.String? id,
    $core.String? translation,
    $core.Iterable<$core.String>? notes,
    $core.Iterable<AlignmentSpan>? spans,
  }) {
    final result = create();
    if (id != null) result.id = id;
    if (translation != null) result.translation = translation;
    if (notes != null) result.notes.addAll(notes);
    if (spans != null) result.spans.addAll(spans);
    return result;
  }

  TranslatedSegment._();

  factory TranslatedSegment.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranslatedSegment.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranslatedSegment',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'id')
    ..aOS(2, _omitFieldNames ? '' : 'translation')
    ..pPS(3, _omitFieldNames ? '' : 'notes')
    ..pPM<AlignmentSpan>(4, _omitFieldNames ? '' : 'spans',
        subBuilder: AlignmentSpan.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslatedSegment clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslatedSegment copyWith(void Function(TranslatedSegment) updates) =>
      super.copyWith((message) => updates(message as TranslatedSegment))
          as TranslatedSegment;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslatedSegment create() => TranslatedSegment._();
  @$core.override
  TranslatedSegment createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranslatedSegment getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranslatedSegment>(create);
  static TranslatedSegment? _defaultInstance;

  @$pb.TagNumber(1)
  $core.String get id => $_getSZ(0);
  @$pb.TagNumber(1)
  set id($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasId() => $_has(0);
  @$pb.TagNumber(1)
  void clearId() => $_clearField(1);

  @$pb.TagNumber(2)
  $core.String get translation => $_getSZ(1);
  @$pb.TagNumber(2)
  set translation($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasTranslation() => $_has(1);
  @$pb.TagNumber(2)
  void clearTranslation() => $_clearField(2);

  @$pb.TagNumber(3)
  $pb.PbList<$core.String> get notes => $_getList(2);

  @$pb.TagNumber(4)
  $pb.PbList<AlignmentSpan> get spans => $_getList(3);
}

class TranslationOutput extends $pb.GeneratedMessage {
  factory TranslationOutput({
    $core.Iterable<TranslatedSegment>? segments,
    $core.String? provider,
    $core.String? modelId,
    $core.bool? cacheHit,
    $core.int? latencyMs,
  }) {
    final result = create();
    if (segments != null) result.segments.addAll(segments);
    if (provider != null) result.provider = provider;
    if (modelId != null) result.modelId = modelId;
    if (cacheHit != null) result.cacheHit = cacheHit;
    if (latencyMs != null) result.latencyMs = latencyMs;
    return result;
  }

  TranslationOutput._();

  factory TranslationOutput.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranslationOutput.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranslationOutput',
      package: const $pb.PackageName(
          _omitMessageNames ? '' : 'sparkle.inference.v1'),
      createEmptyInstance: create)
    ..pPM<TranslatedSegment>(1, _omitFieldNames ? '' : 'segments',
        subBuilder: TranslatedSegment.create)
    ..aOS(2, _omitFieldNames ? '' : 'provider')
    ..aOS(3, _omitFieldNames ? '' : 'modelId')
    ..aOB(4, _omitFieldNames ? '' : 'cacheHit')
    ..aI(5, _omitFieldNames ? '' : 'latencyMs')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationOutput clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranslationOutput copyWith(void Function(TranslationOutput) updates) =>
      super.copyWith((message) => updates(message as TranslationOutput))
          as TranslationOutput;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranslationOutput create() => TranslationOutput._();
  @$core.override
  TranslationOutput createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranslationOutput getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranslationOutput>(create);
  static TranslationOutput? _defaultInstance;

  @$pb.TagNumber(1)
  $pb.PbList<TranslatedSegment> get segments => $_getList(0);

  @$pb.TagNumber(2)
  $core.String get provider => $_getSZ(1);
  @$pb.TagNumber(2)
  set provider($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasProvider() => $_has(1);
  @$pb.TagNumber(2)
  void clearProvider() => $_clearField(2);

  @$pb.TagNumber(3)
  $core.String get modelId => $_getSZ(2);
  @$pb.TagNumber(3)
  set modelId($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasModelId() => $_has(2);
  @$pb.TagNumber(3)
  void clearModelId() => $_clearField(3);

  @$pb.TagNumber(4)
  $core.bool get cacheHit => $_getBF(3);
  @$pb.TagNumber(4)
  set cacheHit($core.bool value) => $_setBool(3, value);
  @$pb.TagNumber(4)
  $core.bool hasCacheHit() => $_has(3);
  @$pb.TagNumber(4)
  void clearCacheHit() => $_clearField(4);

  @$pb.TagNumber(5)
  $core.int get latencyMs => $_getIZ(4);
  @$pb.TagNumber(5)
  set latencyMs($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasLatencyMs() => $_has(4);
  @$pb.TagNumber(5)
  void clearLatencyMs() => $_clearField(5);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
