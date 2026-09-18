// ignore_for_file: discarded_futures

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/gen/websocket.pb.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketService {
  static const List<Duration> _reconnectSchedule = <Duration>[
    Duration(milliseconds: 800),
    Duration(milliseconds: 1200),
    Duration(milliseconds: 2200),
    Duration(milliseconds: 4200),
    Duration(milliseconds: 8200),
    Duration(milliseconds: 12200),
  ];
  static const int _maxReconnectAttempts = 6;

  WebSocketChannel? _channel;
  bool _isConnected = false;
  String? _url;
  Map<String, dynamic>? _customHeaders;

  // Reconnection logic
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _isManualDisconnect = false;

  final StreamController<dynamic> _controller =
      StreamController<dynamic>.broadcast();
  Stream<dynamic> get stream => _controller.stream;
  bool get isConnected => _isConnected;

  void connect(String url, {Map<String, dynamic>? headers}) {
    _url = url;
    _customHeaders = headers; // 存储headers供内部使用
    _isManualDisconnect = false;
    _reconnectAttempts = 0;
    _cancelReconnectTimer();

    _connectInternal();
  }

  void _connectInternal() {
    if (_url == null) return;

    // Close any existing channel before overwriting to avoid resource leaks.
    if (_channel != null) {
      try {
        _channel!.sink.close(status.goingAway);
      } catch (_) {
        // Channel may already be dead; this is best-effort cleanup.
      }
      _channel = null;
    }
    _isConnected = false;

    try {
      final uri = Uri.parse(_url!);
      debugPrint(
          'Connecting to WebSocket: $uri (Attempt: $_reconnectAttempts)',);

      // 使用headers参数（如果提供）- 使用IOWebSocketChannel支持headers
      final channel = IOWebSocketChannel.connect(
        uri,
        headers: _customHeaders,
      );
      _channel = channel;

      // 连接建立成功（握手完成）即标记已连接并复位重连预算。
      // 此前预算只在收到第一条消息时复位——对静默连接（如离线同步引擎
      // 等待 outbox、无服务端推送）预算保持耗尽，两次真实断线后即永久
      // 放弃重连。catchError 同时消费 ready 上的失败，避免未处理的
      // 异步异常泄漏到调用方 zone。
      unawaited(
        channel.ready.then((_) {
          if (_isManualDisconnect || !identical(_channel, channel)) {
            return;
          }
          _isConnected = true;
          _reconnectAttempts = 0;
        }).catchError((Object error) {
          if (_isManualDisconnect || !identical(_channel, channel)) {
            return;
          }
          debugPrint('WebSocket handshake failed: $error');
          _isConnected = false;
          _scheduleReconnect();
        }),
      );

      _channel!.stream.listen(
        (data) {
          if (data is List<int>) {
            try {
              final msg = WebSocketMessage.fromBuffer(data);
              _controller.add(msg);
            } catch (e) {
              // 解析失败的二进制帧无法被消费方识别（sync_engine 等只认
              // WebSocketMessage / JSON Map），广播原始字节只会让下游
              // 崩溃——记日志后丢弃。
              debugPrint('Failed to parse Protobuf message: $e');
            }
          } else {
            // Text/JSON message
            try {
              // Try to decode JSON to Map if possible, for easier consumption
              final decoded = jsonDecode(data as String);
              _controller.add(decoded);
            } catch (_) {
              // Not JSON, just emit string
              _controller.add(data);
            }
          }
        },
        onError: (Object error) {
          debugPrint('WebSocket stream error: $error');
          _isConnected = false;
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('WebSocket stream closed');
          _isConnected = false;
          _scheduleReconnect();
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('WebSocket connection error: $e');
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_isManualDisconnect) return;

    if (_reconnectAttempts >= _maxReconnectAttempts) {
      debugPrint('WebSocket max reconnect attempts reached');
      return;
    }

    final index = _reconnectAttempts.clamp(0, _maxReconnectAttempts - 1);
    final delay = _reconnectSchedule[index];
    debugPrint('Scheduling reconnect in ${delay}ms');

    // 单一调度路径：onError 与 onDone（以及握手失败）会对同一次断线先后
    // 进入这里，先取消旧 Timer 再排程，避免叠加 Timer 令重连预算倍速消耗。
    _cancelReconnectTimer();
    _reconnectTimer = Timer(delay, () {
      _reconnectAttempts++;
      _connectInternal();
    });
  }

  void _cancelReconnectTimer() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void disconnect() {
    _isManualDisconnect = true;
    _cancelReconnectTimer();

    if (_channel != null) {
      debugPrint('Disconnecting WebSocket');
      _channel!.sink.close(status.normalClosure);
      _channel = null;
      _isConnected = false;
    }
  }

  void send(dynamic data) {
    if (_channel != null && _isConnected) {
      final span = TracingService.instance.startSpan('ws.send');
      if (data is WebSocketMessage) {
        span.setAttribute('ws.type', data.type);
        _channel!.sink.add(data.writeToBuffer());
      } else if (data is List<int>) {
        _channel!.sink.add(data);
      } else if (data is Map || data is List) {
        if (data is Map && !data.containsKey('trace_id')) {
          data['trace_id'] = TracingService.instance.createTraceId();
        }
        if (data is Map && data['type'] is String) {
          span.setAttribute('ws.type', data['type'] as String);
        }
        _channel!.sink.add(jsonEncode(data));
      } else {
        _channel!.sink.add(data);
      }
      span.end();
    } else {
      debugPrint('Cannot send message: WebSocket not connected');
    }
  }
}
