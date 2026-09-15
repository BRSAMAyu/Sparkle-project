// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_response_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ChatResponseModel _$ChatResponseModelFromJson(Map<String, dynamic> json) =>
    ChatResponseModel(
      message: json['message'] as String,
      conversationId: json['conversation_id'] as String,
      widgets: (json['widgets'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList(),
      toolResults: (json['tool_results'] as List<dynamic>?)
          ?.map((e) => e as Map<String, dynamic>)
          .toList(),
      hasErrors: json['has_errors'] as bool? ?? false,
    );

Map<String, dynamic> _$ChatResponseModelToJson(ChatResponseModel instance) =>
    <String, dynamic>{
      'message': instance.message,
      'conversation_id': instance.conversationId,
      'widgets': instance.widgets,
      'tool_results': instance.toolResults,
      'has_errors': instance.hasErrors,
    };
