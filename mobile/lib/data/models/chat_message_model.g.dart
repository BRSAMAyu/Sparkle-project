// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_message_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ChatMessageModel _$ChatMessageModelFromJson(Map<String, dynamic> json) =>
    ChatMessageModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      sessionId: json['session_id'] as String,
      role: $enumDecode(_$MessageRoleEnumMap, json['role']),
      content: json['content'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      taskId: json['task_id'] as String?,
      actions: (json['actions'] as List<dynamic>?)
          ?.map((e) => ChatAction.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$ChatMessageModelToJson(ChatMessageModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'session_id': instance.sessionId,
      'task_id': instance.taskId,
      'role': _$MessageRoleEnumMap[instance.role]!,
      'content': instance.content,
      'actions': instance.actions,
      'created_at': instance.createdAt.toIso8601String(),
    };

const _$MessageRoleEnumMap = {
  MessageRole.user: 'user',
  MessageRole.assistant: 'assistant',
  MessageRole.system: 'system',
};

ChatAction _$ChatActionFromJson(Map<String, dynamic> json) => ChatAction(
      type: json['type'] as String,
      params: json['params'] as Map<String, dynamic>,
    );

Map<String, dynamic> _$ChatActionToJson(ChatAction instance) =>
    <String, dynamic>{
      'type': instance.type,
      'params': instance.params,
    };

ChatRequest _$ChatRequestFromJson(Map<String, dynamic> json) => ChatRequest(
      content: json['content'] as String,
      sessionId: json['session_id'] as String?,
      taskId: json['task_id'] as String?,
    );

Map<String, dynamic> _$ChatRequestToJson(ChatRequest instance) =>
    <String, dynamic>{
      'content': instance.content,
      'session_id': instance.sessionId,
      'task_id': instance.taskId,
    };

ChatResponse _$ChatResponseFromJson(Map<String, dynamic> json) => ChatResponse(
      message:
          ChatMessageModel.fromJson(json['message'] as Map<String, dynamic>),
      actions: (json['actions'] as List<dynamic>?)
          ?.map((e) => ChatAction.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$ChatResponseToJson(ChatResponse instance) =>
    <String, dynamic>{
      'message': instance.message,
      'actions': instance.actions,
    };

ChatSession _$ChatSessionFromJson(Map<String, dynamic> json) => ChatSession(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      firstMessageSummary: json['first_message_summary'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ChatSessionToJson(ChatSession instance) =>
    <String, dynamic>{
      'id': instance.id,
      'user_id': instance.userId,
      'first_message_summary': instance.firstMessageSummary,
      'created_at': instance.createdAt.toIso8601String(),
    };
