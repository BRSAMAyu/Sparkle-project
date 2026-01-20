import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:opentelemetry/api.dart' show Attribute;
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Parse JSON event in isolate to avoid blocking main thread
ChatStreamEvent _parseChatEvent(String jsonString) {
  try {
    final data = json.decode(jsonString) as Map<String, dynamic>;

    // Basic validation
    if (!data.containsKey('type')) {
      return ErrorEvent(
        code: 'INVALID_FORMAT',
        message: 'Missing "type" field',
        retryable: false,
      );
    }

    final type = data['type'] as String?;
    final responseId = data['response_id'] as String?;
    final traceId = data['trace_id'] as String?;
    final workflowId = data['workflow_id'] as String?;
    final promptVersion = data['prompt_version'] as String?;

    switch (type) {
      case 'delta':
        return TextEvent(
          content: data['delta'] as String? ?? '',
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'status_update':
        final status = data['status'] as Map<String, dynamic>?;
        if (status != null) {
          return StatusUpdateEvent(
            state: status['state'] as String? ?? 'UNKNOWN',
            details: status['details'] as String? ?? '',
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'tool_call':
        final toolCall = data['tool_call'] as Map<String, dynamic>?;
        if (toolCall != null) {
          return ToolStartEvent(
            toolName: toolCall['name'] as String? ?? 'unknown',
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'tool_result':
        final toolResult = data['tool_result'] as Map<String, dynamic>?;
        if (toolResult != null) {
          return ToolResultEvent(
            result: ToolResultModel.fromJson(toolResult),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'intervention':
        final intervention = data['intervention'] as Map<String, dynamic>?;
        if (intervention == null) {
          return UnknownEvent(
            data: data,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        final content = intervention['content'] as Map<String, dynamic>? ?? {};
        final widgetType =
            content['widget_type'] as String? ?? 'intervention_card';
        final widgetData =
            (content['widget_data'] as Map<String, dynamic>?) ??
                Map<String, dynamic>.from(content);

        widgetData['intervention_id'] ??= intervention['id'];
        widgetData['intervention_topic'] ??= intervention['topic'];
        widgetData['intervention_level'] ??= intervention['level'];

        return WidgetEvent(
          widgetType: widgetType,
          widgetData: widgetData,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'widget':
        final widgetType = data['widget_type'] as String?;
        final widgetData = data['widget_data'] as Map<String, dynamic>?;
        if (widgetType != null && widgetData != null) {
          return WidgetEvent(
            widgetType: widgetType,
            widgetData: widgetData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'full_text':
        return FullTextEvent(
          content: data['full_text'] as String? ?? '',
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'error':
        final error = data['error'] as Map<String, dynamic>?;
        if (error != null) {
          return ErrorEvent(
            code: error['code'] as String? ?? 'UNKNOWN',
            message: error['message'] as String? ?? 'Unknown error',
            retryable: error['retryable'] as bool? ?? false,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return ErrorEvent(
          code: 'UNKNOWN',
          message: 'Unknown error',
          retryable: false,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'usage':
        final usage = data['usage'] as Map<String, dynamic>?;
        if (usage != null) {
          return UsageEvent(
            promptTokens: usage['prompt_tokens'] as int? ?? 0,
            completionTokens: usage['completion_tokens'] as int? ?? 0,
            totalTokens: usage['total_tokens'] as int? ?? 0,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'citations':
        final list = data['citations'] as List<dynamic>?;
        if (list != null) {
          return CitationEvent(
            citations: list.map((e) => e as Map<String, dynamic>).toList(),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'pong':
        // 心跳响应，静默处理
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'reasoning_step':
        final step = data['step'] as Map<String, dynamic>?;
        if (step != null) {
          return ReasoningStepEvent(
            step: ReasoningStep.fromJson(step),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'action_status':
        final actionId = data['action_id'] as String?;
        final status = data['status'] as String?;
        if (actionId != null && status != null) {
          return ActionStatusEvent(
            actionId: actionId,
            status: status,
            message: data['message'] as String?,
            widgetType: data['widget_type'] as String?,
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'intervention_feedback_ack':
        final requestId = data['request_id'] as String?;
        final status = data['status'] as String?;
        if (requestId != null && status != null) {
          return ActionStatusEvent(
            actionId: requestId,
            status: status,
            message: data['message'] as String?,
            widgetType: 'intervention',
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      default:
        final finishReason = data['finish_reason'] as String?;
        if (finishReason != null && finishReason != 'NULL') {
          return DoneEvent(
            finishReason: finishReason,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );
    }
  } catch (e) {
    return ErrorEvent(
      code: 'PARSE_ERROR',
      message: e.toString(),
      retryable: false,
    );
  }
}

/// WebSocket 连接状态
enum WsConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  failed,
}

/// Factory for creating WebSocket channels (facilitates testing)
typedef WebSocketChannelFactory = WebSocketChannel Function(Uri uri,
    {Map<String, dynamic>? headers,});

/// WebSocket 聊天服务 V2（完整的连接复用和状态管理）
class WebSocketChatServiceV2 {
  WebSocketChatServiceV2({
    String? baseUrl,
    WebSocketChannelFactory? channelFactory,
    bool enableReconnect = true,
    bool autoConnect = true,
  })  : baseUrl = baseUrl ?? ApiConstants.wsBaseUrl,
        _channelFactory = channelFactory,
        _enableReconnect = enableReconnect,
        _autoConnect = autoConnect;

  // Factory for creating channels
  final WebSocketChannelFactory? _channelFactory;
  final bool _enableReconnect;
  final bool _autoConnect;

  // WebSocket 连接
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _socketSubscription;
  bool _disposed = false;
  int _connGen = 0;

  // 消息流（广播模式，支持多个监听者）
  StreamController<ChatStreamEvent>? _messageStreamController;

  // 连接状态流
  final StreamController<WsConnectionState> _connectionStateController =
      StreamController<WsConnectionState>.broadcast();

  final String baseUrl;

  // 当前用户和会话
  String? _currentUserId;
  String? _currentSessionId;
  String? _currentToken;

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

  /// Exposed for testing
  @visibleForTesting
  List<Map<String, dynamic>> get pendingMessages => _pendingMessages;

  /// Exposed for testing
  @visibleForTesting
  int get reconnectAttempts => _reconnectAttempts;

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
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
  }) {
    // 更新 session ID
    _currentSessionId = sessionId ?? _currentSessionId ?? _generateSessionId();

    // 创建消息流（如果不存在）
    _messageStreamController ??= StreamController<ChatStreamEvent>.broadcast();

    // 检查是否需要建立连接
    if (_autoConnect && _shouldConnect(userId, token)) {
      _establishConnection(userId, token);
    }

    // 构建消息
    final messagePayload = {
      'message': message,
      'session_id': _currentSessionId,
      if (nickname != null) 'nickname': nickname,
      if (extraContext != null) 'extra_context': extraContext,
      if (fileIds != null && fileIds.isNotEmpty) 'file_ids': fileIds,
      if (includeReferences) 'include_references': true,
    };

    // 发送或排队
    if (isConnected) {
      _sendMessage(messagePayload);
    } else {
      _log('⏳ Message queued (not connected yet)');
      // TODO-A7: Pending Limit
      if (_pendingMessages.length >= 50) {
        _pendingMessages.removeAt(0); // Drop oldest
      }
      _pendingMessages.add(messagePayload);
    }

    return _messageStreamController!.stream;
  }

  /// 发送行动反馈（确认/拒绝）
  void sendActionFeedback({
    required String action,
    required String toolResultId,
    required String widgetType,
  }) {
    final feedback = {
      'type': 'action_feedback',
      'action': action, // 'confirm' or 'dismiss'
      'tool_result_id': toolResultId,
      'widget_type': widgetType,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Action feedback sent: $action for $widgetType');
  }

  /// 发送干预反馈（Intervention）
  void sendInterventionFeedback({
    required String requestId,
    required String feedbackType,
    Map<String, dynamic>? extraData,
  }) {
    final feedback = {
      'type': 'intervention_feedback',
      'request_id': requestId,
      'feedback_type': feedbackType,
      if (extraData != null) 'extra_data': extraData,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Intervention feedback sent: $feedbackType for $requestId');
  }

  /// 发送回复反馈（Thumbs up/down）
  void sendResponseFeedback({
    required String responseId,
    required String feedbackType,
    List<String>? reasons,
    String? freeText,
    String? workflowId,
    String? promptVersion,
    String? traceId,
    Map<String, dynamic>? meta,
  }) {
    final feedback = {
      'type': 'response_feedback',
      'response_id': responseId,
      'feedback_type': feedbackType,
      if (reasons != null && reasons.isNotEmpty) 'reasons': reasons,
      if (freeText != null && freeText.isNotEmpty) 'free_text': freeText,
      if (workflowId != null) 'workflow_id': workflowId,
      if (promptVersion != null) 'prompt_version': promptVersion,
      if (traceId != null) 'trace_id': traceId,
      if (meta != null) 'meta': meta,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Response feedback sent: $feedbackType for $responseId');
  }

  /// 发送专注完成事件
  void sendFocusCompleted({
    required String sessionId,
    required int actualDuration,
    List<String> completedTaskIds = const [],
  }) {
    final event = {
      'type': 'focus_completed',
      'session_id': sessionId,
      'actual_duration': actualDuration,
      'tasks_completed': completedTaskIds,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(event);
    _log('📤 Focus completed event sent');
  }

  /// 判断是否需要建立连接
  bool _shouldConnect(String userId, String? token) {
    // 用户切换
    if (_currentUserId != null && _currentUserId != userId) {
      _log('👤 User changed, reconnecting...');
      _closeConnection();
      return true;
    }
    if (token != null && _currentToken != null && _currentToken != token) {
      _log('🔐 Token changed, reconnecting...');
      _closeConnection();
      return true;
    }

    // 未连接
    if (_connectionState == WsConnectionState.failed && !_enableReconnect) {
      return false;
    }

    if (_connectionState == WsConnectionState.disconnected ||
        _connectionState == WsConnectionState.failed) {
      return true;
    }

    return false;
  }

  /// 建立 WebSocket 连接
  void _establishConnection(String userId, String? token) {
    if (_connectionState == WsConnectionState.connecting ||
        _connectionState == WsConnectionState.connected) {
      _log('⚠️  Already connecting/connected');
      return;
    }

    final effectiveToken = token ?? _currentToken;
    _currentUserId = userId;
    _currentToken = effectiveToken;
    _updateConnectionState(WsConnectionState.connecting);

    try {
      // Web platform: headers not supported - throw explicit error
      if (kIsWeb) {
        throw UnsupportedError(
          'WebSocket header authentication is not supported on Web platform. '
          'Web browsers do not allow custom headers in WebSocket connections. '
          'Please configure the server to accept token via query parameter or use a proxy.',
        );
      }

      // Force secure WebSocket in production
      const isProduction = kReleaseMode;
      final effectiveBaseUrl = _applyWebSocketSchemeForEnvironment(
        baseUrl,
        isProduction: isProduction,
      );

      // Token in headers only - never in URL query
      final query = 'user_id=$userId';

      final wsUrl = '$effectiveBaseUrl/ws/chat?$query';
      _log('🔌 Connecting to: $wsUrl');

      final headers = <String, dynamic>{};
      if (effectiveToken != null && effectiveToken.isNotEmpty) {
        headers['Authorization'] = 'Bearer $effectiveToken';
      }

      if (_channelFactory != null) {
        _channel = _channelFactory!(
          Uri.parse(wsUrl),
          headers: headers.isEmpty ? null : headers,
        );
      } else {
        _channel = IOWebSocketChannel.connect(
          Uri.parse(wsUrl),
          headers: headers.isEmpty ? null : headers,
        );
      }

      // 监听 WebSocket 流
      _socketSubscription = _channel!.stream.listen(
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

      _log('✅ WebSocket connected');
    } catch (e) {
      _log('❌ Connection failed: $e');
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
      _log('📡 Connection state: ${newState.name}');
    }
  }

  void _safeAdd<T>(StreamController<T> controller, T event) {
    if (_disposed || controller.isClosed) return;
    controller.add(event);
  }

  /// 处理接收到的消息
  Future<void> _handleIncomingMessage(dynamic data) async {
    if (_disposed) return;

    try {
      if (data is! String) {
        _log('❌ Invalid data type: ${data.runtimeType}');
        return;
      }

      // Parse event in isolate to avoid blocking main thread
      final event = await compute(_parseChatEvent, data);

      if (_messageStreamController != null) {
        _safeAdd(_messageStreamController!, event);
      }
    } catch (e) {
      _log('❌ Parse error: $e');
    }
  }

  /// 处理连接错误
  void _handleConnectionError(dynamic error) {
    if (_disposed) return;

    _log('❌ Connection error: $error');

    // 发送错误事件给消息流
    if (_messageStreamController != null) {
      _safeAdd(
        _messageStreamController!,
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
    _log('🔌 Connection closed');
    _stopHeartbeat();

    // 非主动关闭时尝试重连
    if (_connectionState != WsConnectionState.disconnected) {
      _triggerReconnect();
    }
  }

  /// 触发重连（指数退避）(TODO-A7)
  void _triggerReconnect() {
    if (_disposed) return; // TODO-A7: Check disposed
    if (!_enableReconnect) {
      _log('⛔ Reconnect disabled');
      _updateConnectionState(WsConnectionState.failed);
      return;
    }

    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _log('❌ Max reconnect attempts reached');
      _updateConnectionState(WsConnectionState.failed);

      // TODO-A7: Clear pending
      _pendingMessages.clear();

      if (_messageStreamController != null) {
        _safeAdd(
          _messageStreamController!,
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

    // TODO-A7: Jitter
    final backoff = math.min(
      math.pow(2, _reconnectAttempts).toInt(),
      32,
    );
    final jitter = math.Random().nextInt(1000);
    final delayMs = (backoff * 1000) + jitter;

    _log(
      '🔄 Reconnecting in ${delayMs}ms '
      '(attempt $_reconnectAttempts/$_maxReconnectAttempts)',
    );

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(milliseconds: delayMs), () {
      if (_disposed) return; // TODO-A7: Check disposed inside timer
      if (_currentUserId != null) {
        _establishConnection(_currentUserId!, _currentToken);
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
          _log('💓 Heartbeat sent');
        } catch (e) {
          _log('❌ Heartbeat failed: $e');
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

  /// 发送消息 (TODO-A7)
  void _sendMessage(Map<String, dynamic> payload) {
    if (!isConnected) {
      _log('⚠️  Cannot send: not connected');
      // TODO-A7: Pending Limit
      if (_pendingMessages.length >= 50) {
        _pendingMessages.removeAt(0); // Drop oldest
      }
      _pendingMessages.add(payload);
      return;
    }

    try {
      final span = TracingService.instance.startSpan('ws.chat_send');
      payload.putIfAbsent('trace_id', TracingService.instance.createTraceId);
      if (payload['type'] is String) {
        span.setAttribute(Attribute.fromString('ws.type', payload['type'] as String));
      }
      _channel?.sink.add(json.encode(payload));
      _log('📤 Sent: ${payload['message']}');
      span.end();
    } catch (e) {
      _log('❌ Send failed: $e');
      if (_pendingMessages.length >= 50) {
        _pendingMessages.removeAt(0);
      }
      _pendingMessages.add(payload);
      _handleConnectionError(e);
    }
  }

  /// 发送待发送的消息
  void _flushPendingMessages() {
    if (_pendingMessages.isEmpty) return;

    _log('📨 Flushing ${_pendingMessages.length} pending messages');
    final messages = List<Map<String, dynamic>>.from(_pendingMessages);
    _pendingMessages.clear();

    messages.forEach(_sendMessage);
  }

  String _applyWebSocketSchemeForEnvironment(
    String rawBaseUrl, {
    required bool isProduction,
  }) {
    final uri = Uri.parse(rawBaseUrl);
    if (isProduction) {
      if (uri.scheme != 'wss') {
        debugPrint(
            '⚠️ WARNING: Forcing WSS for release WebSocket connections.',);
      }
      return uri.replace(scheme: 'wss').toString();
    }
    return rawBaseUrl;
  }

  /// 生成 session ID
  String _generateSessionId() =>
      'session_${DateTime.now().millisecondsSinceEpoch}';

  /// 手动重连
  Future<void> manualReconnect() async {
    if (_disposed) return;
    if (_currentUserId == null) {
      _log('⚠️  Cannot reconnect: no user ID');
      return;
    }

    _log('🔄 Manual reconnect triggered');
    _reconnectAttempts = 0;

    _connGen++;
    await _teardownSocket(_connGen);
    _updateConnectionState(WsConnectionState.disconnected);

    await Future<void>.delayed(const Duration(milliseconds: 500));
    if (!_disposed) {
      _establishConnection(_currentUserId!, _currentToken);
    }
  }

  /// 销毁 Socket 连接（幂等、异步、安全）
  Future<void> _teardownSocket(int gen) async {
    if (gen != _connGen) {
      _log('⚠️ Ignored teardown for gen $gen (current: $_connGen)');
      return;
    }

    _log('🔌 Teardown socket (Gen: $gen)');

    _stopHeartbeat();

    if (!_disposed) {
      _connectionState = WsConnectionState.disconnected;
      _safeAdd(_connectionStateController, WsConnectionState.disconnected);
    }

    final sub = _socketSubscription;
    _socketSubscription = null;
    try {
      await sub?.cancel();
    } catch (_) {}

    final ch = _channel;
    _channel = null;
    try {
      await ch?.sink.close();
    } catch (_) {}
  }

  /// 关闭连接
  void _closeConnection() {
    _log('🔌 Closing connection');
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    final sink = _channel?.sink;
    if (sink != null) {
      unawaited(sink.close());
    }
    _channel = null;
    _updateConnectionState(WsConnectionState.disconnected);
  }

  /// 释放资源
  void dispose() {
    if (_disposed) return;
    _log('🗑️  Disposing WebSocketChatServiceV2');
    _disposed = true;
    _connGen++; // Invalidate any pending connection attempts

    unawaited(_socketSubscription?.cancel());
    _socketSubscription = null;

    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    _stopHeartbeat();

    _closeConnection();

    if (_messageStreamController != null &&
        !_messageStreamController!.isClosed) {
      unawaited(_messageStreamController!.close());
    }
    if (!_connectionStateController.isClosed) {
      unawaited(_connectionStateController.close());
    }
    _pendingMessages.clear();
  }

  // Helper for TODO-A10
  void _log(String message) {
    if (kDebugMode) {
      var masked = message;
      if (message.contains('token=') || message.contains('Authorization')) {
        masked = message.replaceAllMapped(
          RegExp('(token=|Authorization: )([^&]+)'),
          (m) => '${m.group(1)}${_maskSecret(m.group(2))}',
        );
      }
      debugPrint(masked);
    }
  }

  String _maskSecret(String? secret) {
    if (secret == null) return '';
    if (secret.length < 6) return '***';
    return '${secret.substring(0, 3)}...${secret.substring(secret.length - 3)}';
  }
}
