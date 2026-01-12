// ignore_for_file: discarded_futures

import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:fixnum/fixnum.dart';
import 'package:flutter/foundation.dart';
import 'package:sparkle/core/network/proto/websocket.pb.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/status.dart' as status;
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  String? _url;
  Map<String, dynamic>? _customHeaders;

  // Reconnection logic
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _isManualDisconnect = false;
  static const int _maxReconnectAttempts = 10;
  static const int _baseReconnectDelayMs = 1000;

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

    try {
      final uri = Uri.parse(_url!);
      debugPrint(
          'Connecting to WebSocket: $uri (Attempt: $_reconnectAttempts)',);

      // 使用headers参数（如果提供）- 使用IOWebSocketChannel支持headers
      _channel = IOWebSocketChannel.connect(
        uri,
        headers: _customHeaders,
      );
      _isConnected = true;

      _channel!.stream.listen(
        (data) {
          if (data is List<int>) {
            try {
              final msg = WebSocketMessage.fromBuffer(data);
              _controller.add(msg);
            } catch (e) {
              debugPrint('Failed to parse Protobuf message: $e');
              // Fallback: emit raw binary if it wasn't a valid WebSocketMessage (unlikely)
              _controller.add(data);
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
          _reconnectAttempts = 0; // Reset on success
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

    final delay = _baseReconnectDelayMs * pow(2, _reconnectAttempts);
    debugPrint('Scheduling reconnect in ${delay}ms');

    _reconnectTimer = Timer(Duration(milliseconds: delay.toInt()), () {
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
