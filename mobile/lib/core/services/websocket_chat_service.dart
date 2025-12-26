import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';
import 'package:sparkle/core/constants/api_constants.dart';

/// WebSocket 聊天服务
/// 连接到 Go Gateway 的 WebSocket 端点进行流式对话
class WebSocketChatService {
  WebSocketChannel? _channel;
  StreamController<ChatStreamEvent>? _streamController;
  final String baseUrl;
  String? _currentSessionId;
  
  // 重连相关
  int _retryCount = 0;
  final int _maxRetries = 5;
  bool _isManuallyClosed = false;
  Timer? _reconnectTimer;

  WebSocketChatService({
    this.baseUrl = ApiConstants.wsBaseUrl,
  });

  /// 发送消息并返回流式响应
  Stream<ChatStreamEvent> sendMessage({
    required String message,
    required String userId,
    String? sessionId,
    String? nickname,
  }) {
    // 重置状态
    _isManuallyClosed = false;
    _retryCount = 0;
    _reconnectTimer?.cancel();
    
    // 生成或使用现有的 session ID
    _currentSessionId = sessionId ?? _currentSessionId ?? _generateSessionId();

    // 创建新的流控制器 (如果之前的已关闭)
    if (_streamController == null || _streamController!.isClosed) {
      _streamController = StreamController<ChatStreamEvent>.broadcast();
    }

    // 建立 WebSocket 连接
    _connect(
      userId: userId,
      message: message,
      sessionId: _currentSessionId!,
      nickname: nickname,
    );

    return _streamController!.stream;
  }

  /// 建立 WebSocket 连接
  void _connect({
    required String userId,
    required String message,
    required String sessionId,
    String? nickname,
  }) {
    try {
      // 构建 WebSocket URL
      final wsUrl = '$baseUrl/ws/chat?user_id=$userId';

      // 创建 WebSocket 连接
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      // 监听消息
      _channel!.stream.listen(
        (data) {
          _retryCount = 0; // 收到消息，重置重试计数
          _handleMessage(data);
        },
        onError: (error) {
          print('WebSocket Error: $error');
          _handleReconnect(userId, message, sessionId, nickname);
        },
        onDone: () {
          if (!_isManuallyClosed) {
            print('WebSocket closed unexpectedly');
            _handleReconnect(userId, message, sessionId, nickname);
          } else {
            if (!(_streamController?.isClosed ?? true)) {
              _streamController?.add(DoneEvent());
              _streamController?.close();
            }
          }
        },
        cancelOnError: true,
      );

      // 发送初始消息
      _sendWebSocketMessage(
        message: message,
        sessionId: sessionId,
        nickname: nickname,
      );
    } catch (e) {
      print('WebSocket connection error: $e');
      _handleReconnect(userId, message, sessionId, nickname);
    }
  }

  /// 处理重连逻辑
  void _handleReconnect(String userId, String message, String sessionId, String? nickname) {
    if (_isManuallyClosed || _retryCount >= _maxRetries) {
      if (!(_streamController?.isClosed ?? true)) {
        _streamController?.add(ErrorEvent(
          code: 'CONNECTION_FAILED',
          message: '无法建立连接，请检查网络设置',
          retryable: true,
        ));
        _streamController?.close();
      }
      return;
    }

    _retryCount++;
    final delaySeconds = pow(2, _retryCount).toInt(); // 指数退避: 2, 4, 8, 16, 32 秒
    print('Attempting reconnect in $delaySeconds seconds (Attempt $_retryCount/$_maxRetries)...');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      _connect(
        userId: userId,
        message: message,
        sessionId: sessionId,
        nickname: nickname,
      );
    });
  }

  /// 发送 WebSocket 消息
  void _sendWebSocketMessage({
    required String message,
    required String sessionId,
    String? nickname,
  }) {
    final payload = {
      'message': message,
      'session_id': sessionId,
      if (nickname != null) 'nickname': nickname,
    };

    _channel?.sink.add(json.encode(payload));
  }

  /// 处理接收到的消息
  void _handleMessage(dynamic data) {
    try {
      final jsonData = json.decode(data as String) as Map<String, dynamic>;
      final event = _parseEvent(jsonData);

      if (!(_streamController?.isClosed ?? true)) {
        _streamController?.add(event);
      }
    } catch (e) {
      // 忽略解析错误
      print('WebSocket message parse error: $e');
    }
  }

  /// 解析事件
  ChatStreamEvent _parseEvent(Map<String, dynamic> data) {
    final type = data['type'] as String?;

    switch (type) {
      case 'delta':
        // 流式文本片段
        return TextEvent(content: data['delta'] as String? ?? '');

      case 'status_update':
        // 状态更新（THINKING, GENERATING 等）
        final status = data['status'] as Map<String, dynamic>?;
        if (status != null) {
          final state = status['state'] as String?;
          final details = status['details'] as String?;
          return StatusUpdateEvent(
            state: state ?? 'UNKNOWN',
            details: details ?? '',
          );
        }
        return UnknownEvent(data: data);

      case 'tool_call':
        // 工具调用
        final toolCall = data['tool_call'] as Map<String, dynamic>?;
        if (toolCall != null) {
          return ToolStartEvent(
            toolName: toolCall['name'] as String? ?? 'unknown',
          );
        }
        return UnknownEvent(data: data);

      case 'full_text':
        // 完整文本（通常在流结束时发送）
        return FullTextEvent(content: data['full_text'] as String? ?? '');

      case 'error':
        // 错误
        final error = data['error'] as Map<String, dynamic>?;
        if (error != null) {
          return ErrorEvent(
            code: error['code'] as String? ?? 'UNKNOWN',
            message: error['message'] as String? ?? 'Unknown error',
            retryable: error['retryable'] as bool? ?? false,
          );
        }
        return ErrorEvent(
          code: 'UNKNOWN',
          message: 'Unknown error',
          retryable: false,
        );

      case 'usage':
        // Token 使用统计
        final usage = data['usage'] as Map<String, dynamic>?;
        if (usage != null) {
          return UsageEvent(
            promptTokens: usage['prompt_tokens'] as int? ?? 0,
            completionTokens: usage['completion_tokens'] as int? ?? 0,
            totalTokens: usage['total_tokens'] as int? ?? 0,
          );
        }
        return UnknownEvent(data: data);

      default:
        // 检查 finish_reason
        final finishReason = data['finish_reason'] as String?;
        if (finishReason != null && finishReason != 'NULL') {
          return DoneEvent(finishReason: finishReason);
        }

        return UnknownEvent(data: data);
    }
  }

  /// 生成 session ID
  String _generateSessionId() {
    return 'session_${DateTime.now().millisecondsSinceEpoch}';
  }

  /// 关闭连接
  void dispose() {
    _isManuallyClosed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _streamController?.close();
    _channel = null;
    _streamController = null;
  }
}

