import 'package:sparkle/data/models/chat_message_model.dart';

/// 聊天流事件基类
abstract class ChatStreamEvent {}

/// 文本事件
class TextEvent extends ChatStreamEvent {
  final String content;
  TextEvent({required this.content});
}

/// 工具开始事件
class ToolStartEvent extends ChatStreamEvent {
  final String toolName;
  ToolStartEvent({required this.toolName});
}

/// 工具结果事件
class ToolResultEvent extends ChatStreamEvent {
  final ToolResultModel result;
  ToolResultEvent({required this.result});
}

/// Widget 事件
class WidgetEvent extends ChatStreamEvent {
  final String widgetType;
  final Map<String, dynamic> widgetData;
  WidgetEvent({required this.widgetType, required this.widgetData});
}

/// 完成事件
class DoneEvent extends ChatStreamEvent {
  final String? finishReason;

  DoneEvent({this.finishReason});
}

/// 未知事件
class UnknownEvent extends ChatStreamEvent {
  final Map<String, dynamic> data;
  UnknownEvent({required this.data});
}

/// 状态更新事件（THINKING, GENERATING 等）
class StatusUpdateEvent extends ChatStreamEvent {
  final String state;
  final String details;

  StatusUpdateEvent({
    required this.state,
    required this.details,
  });
}

/// 完整文本事件
class FullTextEvent extends ChatStreamEvent {
  final String content;

  FullTextEvent({required this.content});
}

/// 错误事件
class ErrorEvent extends ChatStreamEvent {
  final String code;
  final String message;
  final bool retryable;

  ErrorEvent({
    required this.code,
    required this.message,
    required this.retryable,
  });
}

/// Token 使用统计事件
class UsageEvent extends ChatStreamEvent {
  final int promptTokens;
  final int completionTokens;
  final int totalTokens;

  UsageEvent({
    required this.promptTokens,
    required this.completionTokens,
    required this.totalTokens,
  });
}
