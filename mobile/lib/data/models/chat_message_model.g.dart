// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_message_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ChatMessageModel _$ChatMessageModelFromJson(Map<String, dynamic> json) =>
    ChatMessageModel(
      conversationId: json['conversation_id'] as String,
      role: $enumDecode(_$MessageRoleEnumMap, json['role']),
      content: json['content'] as String,
      id: json['id'] as String?,
      userId: json['user_id'] as String?,
      taskId: json['task_id'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      widgets: (json['widgets'] as List<dynamic>?)
          ?.map((e) => WidgetPayload.fromJson(e as Map<String, dynamic>))
          .toList(),
      toolResults: (json['tool_results'] as List<dynamic>?)
          ?.map((e) => ToolResultModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasErrors: json['has_errors'] as bool?,
      errors: (json['errors'] as List<dynamic>?)
          ?.map((e) => ErrorInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      requiresConfirmation: json['requires_confirmation'] as bool?,
      confirmationData: json['confirmation_data'] == null
          ? null
          : ConfirmationData.fromJson(
              json['confirmation_data'] as Map<String, dynamic>),
      reasoningSteps: _reasoningStepsFromJson(json['reasoning_steps'] as List?),
      reasoningSummary: json['reasoning_summary'] as String?,
      isReasoningComplete: json['is_reasoning_complete'] as bool?,
      meta: json['meta'] == null
          ? null
          : MessageMeta.fromJson(json['meta'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$ChatMessageModelToJson(ChatMessageModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'conversation_id': instance.conversationId,
      'task_id': instance.taskId,
      'role': _$MessageRoleEnumMap[instance.role]!,
      'content': instance.content,
      'created_at': instance.createdAt.toIso8601String(),
      'widgets': instance.widgets,
      'tool_results': instance.toolResults,
      'has_errors': instance.hasErrors,
      'errors': instance.errors,
      'requires_confirmation': instance.requiresConfirmation,
      'confirmation_data': instance.confirmationData,
      'reasoning_steps': _reasoningStepsToJson(instance.reasoningSteps),
      'reasoning_summary': instance.reasoningSummary,
      'is_reasoning_complete': instance.isReasoningComplete,
      'meta': instance.meta,
    };

const _$MessageRoleEnumMap = {
  MessageRole.user: 'user',
  MessageRole.assistant: 'assistant',
  MessageRole.system: 'system',
};

MessageMeta _$MessageMetaFromJson(Map<String, dynamic> json) => MessageMeta(
      latencyMs: (json['latency_ms'] as num?)?.toInt(),
      isCacheHit: json['is_cache_hit'] as bool?,
      costSaved: (json['cost_saved'] as num?)?.toDouble(),
      breakerStatus: json['breaker_status'] as String?,
    );

Map<String, dynamic> _$MessageMetaToJson(MessageMeta instance) =>
    <String, dynamic>{
      'latency_ms': instance.latencyMs,
      'is_cache_hit': instance.isCacheHit,
      'cost_saved': instance.costSaved,
      'breaker_status': instance.breakerStatus,
    };

WidgetPayload _$WidgetPayloadFromJson(Map<String, dynamic> json) =>
    WidgetPayload(
      type: json['type'] as String,
      data: json['data'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$WidgetPayloadToJson(WidgetPayload instance) =>
    <String, dynamic>{
      'type': instance.type,
      'data': instance.data,
    };

ToolResultModel _$ToolResultModelFromJson(Map<String, dynamic> json) =>
    ToolResultModel(
      success: json['success'] as bool,
      toolName: json['tool_name'] as String,
      data: json['data'] as Map<String, dynamic>?,
      errorMessage: json['error_message'] as String?,
      widgetType: json['widget_type'] as String?,
      widgetData: json['widget_data'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$ToolResultModelToJson(ToolResultModel instance) =>
    <String, dynamic>{
      'success': instance.success,
      'tool_name': instance.toolName,
      'data': instance.data,
      'error_message': instance.errorMessage,
      'widget_type': instance.widgetType,
      'widget_data': instance.widgetData,
    };

ErrorInfo _$ErrorInfoFromJson(Map<String, dynamic> json) => ErrorInfo(
      tool: json['tool'] as String,
      message: json['message'] as String,
      suggestion: json['suggestion'] as String?,
    );

Map<String, dynamic> _$ErrorInfoToJson(ErrorInfo instance) => <String, dynamic>{
      'tool': instance.tool,
      'message': instance.message,
      'suggestion': instance.suggestion,
    };

ConfirmationData _$ConfirmationDataFromJson(Map<String, dynamic> json) =>
    ConfirmationData(
      actionId: json['action_id'] as String,
      toolName: json['tool_name'] as String,
      description: json['description'] as String,
      preview: json['preview'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$ConfirmationDataToJson(ConfirmationData instance) =>
    <String, dynamic>{
      'action_id': instance.actionId,
      'tool_name': instance.toolName,
      'description': instance.description,
      'preview': instance.preview,
    };

ChatApiResponse _$ChatApiResponseFromJson(Map<String, dynamic> json) =>
    ChatApiResponse(
      message: json['message'] as String,
      conversationId: json['conversation_id'] as String,
      widgets: (json['widgets'] as List<dynamic>?)
          ?.map((e) => WidgetPayload.fromJson(e as Map<String, dynamic>))
          .toList(),
      toolResults: (json['tool_results'] as List<dynamic>?)
          ?.map((e) => ToolResultModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasErrors: json['has_errors'] as bool?,
      errors: (json['errors'] as List<dynamic>?)
          ?.map((e) => ErrorInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      requiresConfirmation: json['requires_confirmation'] as bool?,
      confirmationData: json['confirmation_data'] == null
          ? null
          : ConfirmationData.fromJson(
              json['confirmation_data'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$ChatApiResponseToJson(ChatApiResponse instance) =>
    <String, dynamic>{
      'message': instance.message,
      'conversation_id': instance.conversationId,
      'widgets': instance.widgets,
      'tool_results': instance.toolResults,
      'has_errors': instance.hasErrors,
      'errors': instance.errors,
      'requires_confirmation': instance.requiresConfirmation,
      'confirmation_data': instance.confirmationData,
    };
