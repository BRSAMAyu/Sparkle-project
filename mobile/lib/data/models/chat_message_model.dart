import 'package:json_annotation/json_annotation.dart';

part 'chat_message_model.g.dart';

enum MessageRole {
  user,
  assistant,
  system,
}

@JsonSerializable()
class ChatMessageModel {
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'session_id')
  final String sessionId;
  @JsonKey(name: 'task_id')
  final String? taskId;
  final MessageRole role;
  final String content;
  final List<ChatAction>? actions;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  ChatMessageModel({
    required this.id,
    required this.userId,
    required this.sessionId,
    required this.role, required this.content, required this.createdAt, this.taskId,
    this.actions,
  });

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) => _$ChatMessageModelFromJson(json);
  Map<String, dynamic> toJson() => _$ChatMessageModelToJson(this);
}

@JsonSerializable()
class ChatAction {
  final String type;
  final Map<String, dynamic> params;

  ChatAction({
    required this.type,
    required this.params,
  });

  factory ChatAction.fromJson(Map<String, dynamic> json) => _$ChatActionFromJson(json);
  Map<String, dynamic> toJson() => _$ChatActionToJson(this);
}

@JsonSerializable()
class ChatRequest {
  final String content;
  @JsonKey(name: 'session_id')
  final String? sessionId;
  @JsonKey(name: 'task_id')
  final String? taskId;

  ChatRequest({
    required this.content,
    this.sessionId,
    this.taskId,
  });

  factory ChatRequest.fromJson(Map<String, dynamic> json) => _$ChatRequestFromJson(json);
  Map<String, dynamic> toJson() => _$ChatRequestToJson(this);
}

@JsonSerializable()
class ChatResponse {
  final ChatMessageModel message;
  final List<ChatAction>? actions;
  
  String get sessionId => message.sessionId;

  ChatResponse({
    required this.message,
    this.actions,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) => _$ChatResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ChatResponseToJson(this);
}

@JsonSerializable()
class ChatSession {
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'first_message_summary')
  final String firstMessageSummary;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  ChatSession({
    required this.id,
    required this.userId,
    required this.firstMessageSummary,
    required this.createdAt,
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) => _$ChatSessionFromJson(json);
  Map<String, dynamic> toJson() => _$ChatSessionToJson(this);
}