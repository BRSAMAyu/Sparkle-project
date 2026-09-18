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
  static const Duration _defaultStableConnectionThreshold =
      Duration(seconds: 30);

  WebSocketService({
    /// 测试注入：覆盖退避表（长度需 ≥ [_maxReconnectAttempts]），
    /// 便于在秒级时间内验证退避升级与 max-attempts 行为。
    List<Duration>? reconnectSchedule,
    /// M6-R2-02：连接存活达到该阈值才视为"稳定连接"，断开时才刷新
    /// 重连预算。生产默认 30s；测试注入小值以避免真实等待。
    Duration stableConnectionThreshold = _defaultStableConnectionThreshold,
  })  : _reconnectScheduleOverride = reconnectSchedule,
        _stableConnectionThreshold = stableConnectionThreshold;

  final List<Duration>? _reconnectScheduleOverride;
  final Duration _stableConnectionThreshold;

  WebSocketChannel? _channel;
  bool _isConnected = false;
  // M6-R2-02：本次握手成功（ready 完成）的时刻。断开时据此判断是
  // "稳定连接断开"（存活 ≥ 阈值 → 刷新预算）还是"接受即断"
  // （存活 < 阈值 → 预算照常递增直至放弃）。
  DateTime? _connectedAt;
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
    _connectedAt = null;
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

      // 握手完成才标记已连接。此处不再复位重连预算——"接受即断"
      // （网关 crash-loop、LB 排水、热重载）场景下每次握手都成功，
      // ready 即复位会让退避停在第一档、max-attempts 守卫失效
      // （M6-R2-02）。预算改为断开时按连接存活时长门控刷新
      // （见 _settleReconnectBudgetOnDisconnect），静默长连接
      // （M6-02 的原始诉求）与快速失败两个场景同时正确。
      // catchError 同时消费 ready 上的失败，避免未处理的异步异常
      // 泄漏到调用方 zone。
      unawaited(
        channel.ready.then((_) {
          if (_isManualDisconnect || !identical(_channel, channel)) {
            return;
          }
          _isConnected = true;
          _connectedAt = DateTime.now();
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
          _settleReconnectBudgetOnDisconnect();
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('WebSocket stream closed');
          _isConnected = false;
          _settleReconnectBudgetOnDisconnect();
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

  /// M6-R2-02：断开时结算重连预算。仅当本次连接存活达到稳定阈值才
  /// 复位 attempts（稳定连接断开 = 给一份新预算）；存活低于阈值的
  /// 短命会话不复位，退避照常升级直至 [_maxReconnectAttempts] 触发
  /// 永久放弃。握手从未成功（[_connectedAt] 为空）时不做任何事。
  void _settleReconnectBudgetOnDisconnect() {
    final connectedAt = _connectedAt;
    _connectedAt = null;
    if (connectedAt == null) {
      return;
    }
    final uptime = DateTime.now().difference(connectedAt);
    if (uptime >= _stableConnectionThreshold) {
      debugPrint(
          'Stable connection (up ${uptime.inSeconds}s) dropped — '
          'refreshing reconnect budget',);
      _reconnectAttempts = 0;
    }
  }

  void _scheduleReconnect() {
    if (_isManualDisconnect) return;

    if (_reconnectAttempts >= _maxReconnectAttempts) {
      debugPrint('WebSocket max reconnect attempts reached');
      return;
    }

    final schedule = _reconnectScheduleOverride ?? _reconnectSchedule;
    final index = _reconnectAttempts.clamp(0, _maxReconnectAttempts - 1);
    final delay = schedule[index];
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
    _connectedAt = null;

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
