import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/reasoning_step_model.dart';

/// 聊天流事件基类
abstract class ChatStreamEvent {}

/// 文本事件
class TextEvent extends ChatStreamEvent {
  TextEvent({required this.content});
  final String content;
}

/// 工具开始事件
class ToolStartEvent extends ChatStreamEvent {
  ToolStartEvent({required this.toolName});
  final String toolName;
}

/// 工具结果事件
class ToolResultEvent extends ChatStreamEvent {
  ToolResultEvent({required this.result});
  final ToolResultModel result;
}

/// Widget 事件
class WidgetEvent extends ChatStreamEvent {
  WidgetEvent({required this.widgetType, required this.widgetData});
  final String widgetType;
  final Map<String, dynamic> widgetData;
}

/// 完成事件
class DoneEvent extends ChatStreamEvent {
  DoneEvent({this.finishReason});
  final String? finishReason;
}

/// 未知事件
class UnknownEvent extends ChatStreamEvent {
  UnknownEvent({required this.data});
  final Map<String, dynamic> data;
}

/// 状态更新事件（THINKING, GENERATING 等）
class StatusUpdateEvent extends ChatStreamEvent {
  StatusUpdateEvent({
    required this.state,
    required this.details,
  });
  final String state;
  final String details;
}

/// 完整文本事件
class FullTextEvent extends ChatStreamEvent {
  FullTextEvent({required this.content});
  final String content;
}

/// 错误事件
class ErrorEvent extends ChatStreamEvent {
  ErrorEvent({
    required this.code,
    required this.message,
    required this.retryable,
  });
  final String code;
  final String message;
  final bool retryable;
}

/// Token 使用统计事件
class UsageEvent extends ChatStreamEvent {
  UsageEvent({
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
  });
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;
}

/// 推理步骤事件（Chain of Thought Visualization）
class ReasoningStepEvent extends ChatStreamEvent {
  ReasoningStepEvent({required this.step});
  final ReasoningStep step;
}

/// 引用事件
class CitationEvent extends ChatStreamEvent {
  CitationEvent({required this.citations});
  final List<Map<String, dynamic>> citations;
}

/// ActionCard 状态事件
class ActionStatusEvent extends ChatStreamEvent {
  ActionStatusEvent({
    required this.actionId,
    required this.status,
    this.message,
    this.widgetType,
    this.timestamp,
  });
  final String actionId;
  final String status; // 'confirmed', 'dismissed'
  final String? message;
  final String? widgetType;
  final int? timestamp;
}
