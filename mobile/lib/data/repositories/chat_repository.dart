import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/websocket_chat_service_v2.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/data/models/chat_response_model.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';

class ChatRepository {

  ChatRepository(
    this._dio, {
    WebSocketChatServiceV2? wsService,
  }) : _wsService = wsService ?? WebSocketChatServiceV2();
  final Dio _dio;
  final WebSocketChatServiceV2 _wsService;

  /// 获取 WebSocket 连接状态流
  Stream<WsConnectionState> get connectionStateStream =>
      _wsService.connectionStateStream;

  /// 当前 WebSocket 连接状态
  WsConnectionState get connectionState => _wsService.connectionState;

  /// 手动触发重连
  Future<void> reconnect() => _wsService.manualReconnect();

  /// 释放资源
  void dispose() {
    _wsService.dispose();
  }

  /// 发送任务相关消息 (非流式)
  Future<ChatResponseModel> sendMessageToTask(String taskId, String message, String? conversationId) async {
    if (DemoDataService.isDemoMode) {
      return ChatResponseModel(message: 'Demo response to task: $message', conversationId: 'demo_id');
    }
    final response = await _dio.post(
      '/api/v1/chat/task/$taskId',
      data: {
        'message': message,
        'conversation_id': conversationId,
      },
    );
    return ChatResponseModel.fromJson(response.data);
  }

  /// 获取对话历史
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoChatHistory;
    }

    final queryParams = <String, dynamic>{};
    if (limit != null) queryParams['limit'] = limit;
    if (offset != null) queryParams['offset'] = offset;

    final response = await _dio.get(
      '/api/v1/chat/history/$conversationId',
      queryParameters: queryParams.isEmpty ? null : queryParams,
    );

    final List list = response.data;
    return list.map((item) => ChatMessageModel.fromJson(item)).toList();
  }

  /// 获取最近对话列表
  Future<List<Map<String, dynamic>>> getRecentConversations() async {
    if (DemoDataService.isDemoMode) {
      return [
        {'id': 'demo_conv_1', 'title': '关于数学复习的建议', 'updated_at': DateTime.now().toIso8601String()},
      ];
    }
    final response = await _dio.get('/api/v1/chat/sessions');
    return List<Map<String, dynamic>>.from(response.data);
  }

  /// 流式聊天（WebSocket）
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? nickname,
  }) {
    if (DemoDataService.isDemoMode) {
      // Mock stream generator
      return _mockChatStream(message);
    }

    // 使用 WebSocket 服务
    return _wsService.sendMessage(
      message: message,
      userId: userId ?? 'anonymous',
      sessionId: conversationId,
      nickname: nickname,
    );
  }

  /// 流式聊天（SSE - 保留用于向后兼容）
  @Deprecated('Use chatStream with WebSocket instead')
  Stream<ChatStreamEvent> chatStreamSSE(String message, String? conversationId) {
    late StreamController<ChatStreamEvent> controller;
    controller = StreamController<ChatStreamEvent>(
      onCancel: () {
        if (!controller.isClosed) {
          controller.close();
        }
      },
    );

    _startSSEConnection(
      message: message,
      conversationId: conversationId,
      controller: controller,
    );

    return controller.stream;
  }
  
  Stream<ChatStreamEvent> _mockChatStream(String message) async* {
    yield TextEvent(content: 'Received: $message\n');
    await Future.delayed(const Duration(milliseconds: 300));
    yield TextEvent(content: 'Thinking...\n');
    yield ToolStartEvent(toolName: 'demo_tool');
    await Future.delayed(const Duration(milliseconds: 500));
    yield ToolResultEvent(result: ToolResultModel(success: true, toolName: 'demo_tool', data: {}));
    yield TextEvent(content: 'This is a simulated response in Demo Mode.\n');
    await Future.delayed(const Duration(milliseconds: 300));
    yield TextEvent(content: 'I can show you Markdown too:\n\n* Item 1\n* Item 2');
    yield DoneEvent();
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
      var buffer = '';

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

