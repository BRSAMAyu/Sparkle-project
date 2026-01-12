import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:uuid/uuid.dart';

part 'chat_message_model.g.dart';

enum MessageRole {
  user,
  assistant,
  system,
}

@JsonSerializable()
class ChatMessageModel {
  // Metadata for FinOps and Chaos

  ChatMessageModel({
    required this.conversationId,
    required this.role,
    required this.content,
    String? id,
    this.userId,
    this.taskId,
    DateTime? createdAt,
    this.widgets,
    this.toolResults,
    this.hasErrors,
    this.errors,
    this.requiresConfirmation,
    this.confirmationData,
    this.aiStatus,
    this.reasoningSteps,
    this.reasoningSummary,
    this.isReasoningComplete,
    this.meta,
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now();

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) =>
      _$ChatMessageModelFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String? userId; // Optional for client-generated messages
  @JsonKey(name: 'conversation_id')
  final String conversationId;
  @JsonKey(name: 'task_id')
  final String? taskId;
  final MessageRole role;
  final String content;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  // New: Agent Workflow support
  final List<WidgetPayload>? widgets; // Widgets to render
  @JsonKey(name: 'tool_results')
  final List<ToolResultModel>? toolResults; // Tool execution results
  @JsonKey(name: 'has_errors')
  final bool? hasErrors;
  final List<ErrorInfo>? errors;
  @JsonKey(name: 'requires_confirmation')
  final bool? requiresConfirmation;
  @JsonKey(name: 'confirmation_data')
  final ConfirmationData? confirmationData;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final String?
      aiStatus; // Optional status for assistant messages (THINKING, etc.)

  // New: Chain of Thought Visualization support
  @JsonKey(
      name: 'reasoning_steps',
      fromJson: _reasoningStepsFromJson,
      toJson: _reasoningStepsToJson,)
  final List<ReasoningStep>? reasoningSteps; // Step-by-step thinking process

  @JsonKey(name: 'reasoning_summary')
  final String? reasoningSummary; // "Completed in 2.1s with 3 agents"

  @JsonKey(name: 'is_reasoning_complete')
  final bool? isReasoningComplete; // For real-time updates

  final MessageMeta? meta;
  Map<String, dynamic> toJson() => _$ChatMessageModelToJson(this);

  ChatMessageModel copyWith({
    String? id,
    String? userId,
    String? conversationId,
    String? taskId,
    MessageRole? role,
    String? content,
    DateTime? createdAt,
    List<WidgetPayload>? widgets,
    List<ToolResultModel>? toolResults,
    bool? hasErrors,
    List<ErrorInfo>? errors,
    bool? requiresConfirmation,
    ConfirmationData? confirmationData,
    String? aiStatus,
    List<ReasoningStep>? reasoningSteps,
    String? reasoningSummary,
    bool? isReasoningComplete,
    MessageMeta? meta,
  }) =>
      ChatMessageModel(
        id: id ?? this.id,
        userId: userId ?? this.userId,
        conversationId: conversationId ?? this.conversationId,
        taskId: taskId ?? this.taskId,
        role: role ?? this.role,
        content: content ?? this.content,
        createdAt: createdAt ?? this.createdAt,
        widgets: widgets ?? this.widgets,
        toolResults: toolResults ?? this.toolResults,
        hasErrors: hasErrors ?? this.hasErrors,
        errors: errors ?? this.errors,
        requiresConfirmation: requiresConfirmation ?? this.requiresConfirmation,
        confirmationData: confirmationData ?? this.confirmationData,
        aiStatus: aiStatus ?? this.aiStatus,
        reasoningSteps: reasoningSteps ?? this.reasoningSteps,
        reasoningSummary: reasoningSummary ?? this.reasoningSummary,
        isReasoningComplete: isReasoningComplete ?? this.isReasoningComplete,
        meta: meta ?? this.meta,
      );
}

@JsonSerializable()
class MessageMeta {
  // 'open' | 'closed'

  MessageMeta({
    this.latencyMs,
    this.isCacheHit,
    this.costSaved,
    this.breakerStatus,
  });

  factory MessageMeta.fromJson(Map<String, dynamic> json) =>
      _$MessageMetaFromJson(json);
  @JsonKey(name: 'latency_ms')
  final int? latencyMs;
  @JsonKey(name: 'is_cache_hit')
  final bool? isCacheHit;
  @JsonKey(name: 'cost_saved')
  final double? costSaved;
  @JsonKey(name: 'breaker_status')
  final String? breakerStatus;
  Map<String, dynamic> toJson() => _$MessageMetaToJson(this);
}

// Helper functions for ReasoningStep serialization
List<ReasoningStep>? _reasoningStepsFromJson(List<dynamic>? json) {
  if (json == null) return null;
  return json
      .map((e) => ReasoningStep.fromJson(e as Map<String, dynamic>))
      .toList();
}

List<Map<String, dynamic>>? _reasoningStepsToJson(List<ReasoningStep>? steps) {
  if (steps == null) return null;
  return steps.map((e) => e.toJson()).toList();
}

@JsonSerializable()
class WidgetPayload {
  WidgetPayload({required this.type, required this.data});

  factory WidgetPayload.fromJson(Map<String, dynamic> json) =>
      _$WidgetPayloadFromJson(json);
  final String
      type; // 'task_card' | 'knowledge_card' | 'task_list' | 'plan_card'
  final Map<String, dynamic> data;
  Map<String, dynamic> toJson() => _$WidgetPayloadToJson(this);
}

@JsonSerializable()
class ToolResultModel {
  ToolResultModel({
    required this.success,
    required this.toolName,
    this.data,
    this.errorMessage,
    this.widgetType,
    this.widgetData,
  });

  factory ToolResultModel.fromJson(Map<String, dynamic> json) =>
      _$ToolResultModelFromJson(json);
  final bool success;
  @JsonKey(name: 'tool_name')
  final String toolName;
  final Map<String, dynamic>? data;
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @JsonKey(name: 'widget_type')
  final String? widgetType;
  @JsonKey(name: 'widget_data')
  final Map<String, dynamic>? widgetData;
  Map<String, dynamic> toJson() => _$ToolResultModelToJson(this);
}

@JsonSerializable()
class ErrorInfo {
  ErrorInfo({required this.tool, required this.message, this.suggestion});

  factory ErrorInfo.fromJson(Map<String, dynamic> json) =>
      _$ErrorInfoFromJson(json);
  final String tool;
  final String message;
  final String? suggestion;
  Map<String, dynamic> toJson() => _$ErrorInfoToJson(this);
}

@JsonSerializable()
class ConfirmationData {
  ConfirmationData({
    required this.actionId,
    required this.toolName,
    required this.description,
    required this.preview,
  });

  factory ConfirmationData.fromJson(Map<String, dynamic> json) =>
      _$ConfirmationDataFromJson(json);
  @JsonKey(name: 'action_id')
  final String actionId;
  @JsonKey(name: 'tool_name')
  final String toolName;
  final String description;
  final Map<String, dynamic> preview;
  Map<String, dynamic> toJson() => _$ConfirmationDataToJson(this);
}

// Backend API response for chat endpoint
@JsonSerializable()
class ChatApiResponse {
  ChatApiResponse({
    required this.message,
    required this.conversationId,
    this.widgets,
    this.toolResults,
    this.hasErrors,
    this.errors,
    this.requiresConfirmation,
    this.confirmationData,
  });

  factory ChatApiResponse.fromJson(Map<String, dynamic> json) =>
      _$ChatApiResponseFromJson(json);
  final String message;
  @JsonKey(name: 'conversation_id')
  final String conversationId;
  final List<WidgetPayload>? widgets;
  @JsonKey(name: 'tool_results')
  final List<ToolResultModel>? toolResults;
  @JsonKey(name: 'has_errors')
  final bool? hasErrors;
  final List<ErrorInfo>? errors;
  @JsonKey(name: 'requires_confirmation')
  final bool? requiresConfirmation;
  @JsonKey(name: 'confirmation_data')
  final ConfirmationData? confirmationData;
  Map<String, dynamic> toJson() => _$ChatApiResponseToJson(this);
}
