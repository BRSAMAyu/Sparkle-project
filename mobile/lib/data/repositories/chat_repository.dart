import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/chat_response_model.dart';

class ChatRepository {
  final Dio _dio;

  ChatRepository(this._dio);

  /// 发送任务相关消息 (非流式)
  Future<ChatResponseModel> sendMessageToTask(String taskId, String message, String? conversationId) async {
    final response = await _dio.post(
      '/api/v1/chat/task/$taskId',
      data: {
        'message': message,
        'conversation_id': conversationId,
      },
    );
    return ChatResponseModel.fromJson(response.data);
  }

  /// 流式聊天（SSE）
  Stream<ChatStreamEvent> chatStream(String message, String? conversationId) {
    final controller = StreamController<ChatStreamEvent>();
    
    _startSSEConnection(
      message: message,
      conversationId: conversationId,
      controller: controller,
    );
    
    return controller.stream;
  }

  Future<void> _startSSEConnection({
    required String message,
    required StreamController<ChatStreamEvent> controller, String? conversationId,
  }) async {
    try {
      final response = await _dio.post<ResponseBody>(
        '/api/v1/chat/stream',
        data: {
          'message': message,
          'conversation_id': conversationId,
        },
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );

      final stream = response.data!.stream;
      String buffer = '';

      await for (final chunk in stream.cast<List<int>>().transform(utf8.decoder)) {
        buffer += chunk;
        
        // 解析 SSE 事件
        while (buffer.contains('\n\n')) {
          final eventEnd = buffer.indexOf('\n\n');
          final eventStr = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);
          
          if (eventStr.startsWith('data: ')) {
            final dataStr = eventStr.substring(6);
            try {
              final data = json.decode(dataStr);
              if (!controller.isClosed) {
                controller.add(_parseEvent(data));
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
      
      if (!controller.isClosed) {
        controller.close();
      }
    } catch (e) {
      if (!controller.isClosed) {
        controller.addError(e);
        controller.close();
      }
    }
  }

  ChatStreamEvent _parseEvent(Map<String, dynamic> data) {
    final type = data['type'] as String;
    
    switch (type) {
      case 'text':
        return TextEvent(content: data['content'] as String);
      
      case 'tool_start':
        return ToolStartEvent(toolName: data['tool'] as String);
      
      case 'tool_result':
        return ToolResultEvent(
          result: ToolResultModel.fromJson(data['result']),
        );
      
      case 'widget':
        return WidgetEvent(
          widgetType: data['widget_type'] as String,
          widgetData: data['widget_data'] as Map<String, dynamic>,
        );
      
      case 'done':
        return DoneEvent();
      
      default:
        return UnknownEvent(data: data);
    }
  }
}

// 事件类型定义
abstract class ChatStreamEvent {}

class TextEvent extends ChatStreamEvent {
  final String content;
  TextEvent({required this.content});
}

class ToolStartEvent extends ChatStreamEvent {
  final String toolName;
  ToolStartEvent({required this.toolName});
}

class ToolResultEvent extends ChatStreamEvent {
  final ToolResultModel result;
  ToolResultEvent({required this.result});
}

class WidgetEvent extends ChatStreamEvent {
  final String widgetType;
  final Map<String, dynamic> widgetData;
  WidgetEvent({required this.widgetType, required this.widgetData});
}

class DoneEvent extends ChatStreamEvent {}

class UnknownEvent extends ChatStreamEvent {
  final Map<String, dynamic> data;
  UnknownEvent({required this.data});
}