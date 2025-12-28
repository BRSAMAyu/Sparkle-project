import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket 连接状态
enum WsConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  failed,
}

/// WebSocket 聊天服务 V2（完整的连接复用和状态管理）
class WebSocketChatServiceV2 {

  WebSocketChatServiceV2({
    this.baseUrl = ApiConstants.wsBaseUrl,
  });
  // WebSocket 连接
  WebSocketChannel? _channel;

  // 消息流（广播模式，支持多个监听者）
  StreamController<ChatStreamEvent>? _messageStreamController;

  // 连接状态流
  final StreamController<WsConnectionState> _connectionStateController =
      StreamController<WsConnectionState>.broadcast();

  final String baseUrl;

  // 当前用户和会话
  String? _currentUserId;
  String? _currentSessionId;

  // 连接状态
  WsConnectionState _connectionState = WsConnectionState.disconnected;

  // 重连机制
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  Timer? _reconnectTimer;

  // 心跳保活
  Timer? _heartbeatTimer;
  static const Duration _heartbeatInterval = Duration(seconds: 30);

  // 消息队列（连接断开时暂存）
  final List<Map<String, dynamic>> _pendingMessages = [];

  /// 获取连接状态流
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionStateController.stream;

  /// 当前连接状态
  WsConnectionState get connectionState => _connectionState;

  /// 是否已连接
  bool get isConnected => _connectionState == WsConnectionState.connected;

  /// 发送消息（复用连接）
  Stream<ChatStreamEvent> sendMessage({
    required String message,
    required String userId,
    String? sessionId,
    String? nickname,
  }) {
    // 更新 session ID
    _currentSessionId = sessionId ?? _currentSessionId ?? _generateSessionId();

    // 创建消息流（如果不存在）
    _messageStreamController ??=
        StreamController<ChatStreamEvent>.broadcast();

    // 检查是否需要建立连接
    if (_shouldConnect(userId)) {
      _establishConnection(userId);
    }

    // 构建消息
    final messagePayload = {
      'message': message,
      'session_id': _currentSessionId,
      if (nickname != null) 'nickname': nickname,
    };

    // 发送或排队
    if (isConnected) {
      _sendMessage(messagePayload);
    } else {
      debugPrint('⏳ Message queued (not connected yet)');
      _pendingMessages.add(messagePayload);
    }

    return _messageStreamController!.stream;
  }

  /// 判断是否需要建立连接
  bool _shouldConnect(String userId) {
    // 用户切换
    if (_currentUserId != null && _currentUserId != userId) {
      debugPrint('👤 User changed, reconnecting...');
      _closeConnection();
      return true;
    }

    // 未连接
    if (_connectionState == WsConnectionState.disconnected ||
        _connectionState == WsConnectionState.failed) {
      return true;
    }

    return false;
  }

  /// 建立 WebSocket 连接
  void _establishConnection(String userId) {
    if (_connectionState == WsConnectionState.connecting ||
        _connectionState == WsConnectionState.connected) {
      debugPrint('⚠️  Already connecting/connected');
      return;
    }

    _currentUserId = userId;
    _updateConnectionState(WsConnectionState.connecting);

    try {
      final wsUrl = '$baseUrl/ws/chat?user_id=$userId';
      debugPrint('🔌 Connecting to: $wsUrl');

      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      // 监听 WebSocket 流
      _channel!.stream.listen(
        _handleIncomingMessage,
        onError: _handleConnectionError,
        onDone: _handleConnectionClosed,
        cancelOnError: false,
      );

      // 连接成功
      _updateConnectionState(WsConnectionState.connected);
      _reconnectAttempts = 0;

      // 启动心跳
      _startHeartbeat();

      // 发送待发送的消息
      _flushPendingMessages();

      debugPrint('✅ WebSocket connected');
    } catch (e) {
      debugPrint('❌ Connection failed: $e');
      _handleConnectionError(e);
    }
  }

  /// 更新连接状态
  void _updateConnectionState(WsConnectionState newState) {
    if (_connectionState != newState) {
      _connectionState = newState;
      if (!_connectionStateController.isClosed) {
        _connectionStateController.add(newState);
      }
      debugPrint('📡 Connection state: ${newState.name}');
    }
  }

  /// 处理接收到的消息
  void _handleIncomingMessage(dynamic data) {
    try {
      final jsonData = json.decode(data as String) as Map<String, dynamic>;
      final event = _parseEvent(jsonData);

      if (_messageStreamController != null &&
          !_messageStreamController!.isClosed) {
        _messageStreamController!.add(event);
      }
    } catch (e) {
      debugPrint('❌ Parse error: $e');
    }
  }

  /// 处理连接错误
  void _handleConnectionError(dynamic error) {
    debugPrint('❌ Connection error: $error');

    // 发送错误事件给消息流
    if (_messageStreamController != null &&
        !_messageStreamController!.isClosed) {
      _messageStreamController!.add(
        ErrorEvent(
          code: 'CONNECTION_ERROR',
          message: 'Network connection failed',
          retryable: true,
        ),
      );
    }

    _triggerReconnect();
  }

  /// 处理连接关闭
  void _handleConnectionClosed() {
    debugPrint('🔌 Connection closed');
    _stopHeartbeat();

    // 非主动关闭时尝试重连
    if (_connectionState != WsConnectionState.disconnected) {
      _triggerReconnect();
    }
  }

  /// 触发重连（指数退避）
  void _triggerReconnect() {
    if (_reconnectAttempts >= _maxReconnectAttempts) {
      debugPrint('❌ Max reconnect attempts reached');
      _updateConnectionState(WsConnectionState.failed);

      if (_messageStreamController != null &&
          !_messageStreamController!.isClosed) {
        _messageStreamController!.add(
          ErrorEvent(
            code: 'MAX_RETRIES_EXCEEDED',
            message: 'Unable to connect after $_maxReconnectAttempts attempts',
            retryable: false,
          ),
        );
      }
      return;
    }

    _reconnectAttempts++;
    _updateConnectionState(WsConnectionState.reconnecting);

    // 指数退避：2^n 秒，最多 32 秒
    final delaySeconds = math.min(
      math.pow(2, _reconnectAttempts).toInt(),
      32,
    );

    debugPrint(
      '🔄 Reconnecting in $delaySeconds seconds '
      '(attempt $_reconnectAttempts/$_maxReconnectAttempts)',
    );

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delaySeconds), () {
      if (_currentUserId != null) {
        _establishConnection(_currentUserId!);
      }
    });
  }

  /// 启动心跳
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (isConnected) {
        try {
          _channel?.sink.add(json.encode({'type': 'ping'}));
          debugPrint('💓 Heartbeat sent');
        } catch (e) {
          debugPrint('❌ Heartbeat failed: $e');
          timer.cancel();
          _handleConnectionClosed();
        }
      } else {
        timer.cancel();
      }
    });
  }

  /// 停止心跳
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// 发送消息
  void _sendMessage(Map<String, dynamic> payload) {
    if (!isConnected) {
      debugPrint('⚠️  Cannot send: not connected');
      _pendingMessages.add(payload);
      return;
    }

    try {
      _channel?.sink.add(json.encode(payload));
      debugPrint('📤 Sent: ${payload['message']}');
    } catch (e) {
      debugPrint('❌ Send failed: $e');
      _pendingMessages.add(payload);
      _handleConnectionError(e);
    }
  }

  /// 发送待发送的消息
  void _flushPendingMessages() {
    if (_pendingMessages.isEmpty) return;

    debugPrint('📨 Flushing ${_pendingMessages.length} pending messages');
    final messages = List<Map<String, dynamic>>.from(_pendingMessages);
    _pendingMessages.clear();

    for (final message in messages) {
      _sendMessage(message);
    }
  }

  /// 解析事件
  ChatStreamEvent _parseEvent(Map<String, dynamic> data) {
    final type = data['type'] as String?;

    switch (type) {
      case 'delta':
        return TextEvent(content: data['delta'] as String? ?? '');

      case 'status_update':
        final status = data['status'] as Map<String, dynamic>?;
        if (status != null) {
          return StatusUpdateEvent(
            state: status['state'] as String? ?? 'UNKNOWN',
            details: status['details'] as String? ?? '',
          );
        }
        return UnknownEvent(data: data);

      case 'tool_call':
        final toolCall = data['tool_call'] as Map<String, dynamic>?;
        if (toolCall != null) {
          return ToolStartEvent(
            toolName: toolCall['name'] as String? ?? 'unknown',
          );
        }
        return UnknownEvent(data: data);

      case 'full_text':
        return FullTextEvent(content: data['full_text'] as String? ?? '');

      case 'error':
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
        final usage = data['usage'] as Map<String, dynamic>?;
        if (usage != null) {
          return UsageEvent(
            promptTokens: usage['prompt_tokens'] as int? ?? 0,
            completionTokens: usage['completion_tokens'] as int? ?? 0,
            totalTokens: usage['total_tokens'] as int? ?? 0,
          );
        }
        return UnknownEvent(data: data);

      case 'citations':
        final list = data['citations'] as List<dynamic>?;
        if (list != null) {
          return CitationEvent(
            citations: list.map((e) => e as Map<String, dynamic>).toList(),
          );
        }
        return UnknownEvent(data: data);

      case 'pong':
        // 心跳响应，静默处理
        return UnknownEvent(data: data);

      default:
        final finishReason = data['finish_reason'] as String?;
        if (finishReason != null && finishReason != 'NULL') {
          return DoneEvent(finishReason: finishReason);
        }
        return UnknownEvent(data: data);
    }
  }

  /// 生成 session ID
  String _generateSessionId() => 'session_${DateTime.now().millisecondsSinceEpoch}';

  /// 手动重连
  Future<void> manualReconnect() async {
    if (_currentUserId == null) {
      debugPrint('⚠️  Cannot reconnect: no user ID');
      return;
    }

    debugPrint('🔄 Manual reconnect triggered');
    _reconnectAttempts = 0;
    _closeConnection();
    await Future.delayed(const Duration(milliseconds: 500));
    _establishConnection(_currentUserId!);
  }

  /// 关闭连接
  void _closeConnection() {
    debugPrint('🔌 Closing connection');
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
    _updateConnectionState(WsConnectionState.disconnected);
  }

  /// 释放资源
  void dispose() {
    debugPrint('🗑️  Disposing WebSocketChatServiceV2');
    _closeConnection();
    _messageStreamController?.close();
    _connectionStateController.close();
    _pendingMessages.clear();
  }
}
