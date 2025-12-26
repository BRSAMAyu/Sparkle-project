import 'dart:convert';
import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

class WebSocketService {
  WebSocketChannel? _channel;
  bool _isConnected = false;
  String? _url;
  
  // Reconnection logic
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _isManualDisconnect = false;
  static const int _maxReconnectAttempts = 10;
  static const int _baseReconnectDelayMs = 1000;

  bool get isConnected => _isConnected;
  Stream<dynamic>? get stream => _channel?.stream;

  void connect(String url, {Map<String, dynamic>? headers}) {
    _url = url;
    _isManualDisconnect = false;
    _reconnectAttempts = 0;
    _cancelReconnectTimer();
    
    _connectInternal(url, headers: headers);
  }

  void _connectInternal(String url, {Map<String, dynamic>? headers}) {
    if (_isConnected) {
      // Already connected, or cleanup previous?
      // For simplicity, we don't disconnect if same URL, but let's be safe.
      // Actually, if we are reconnecting, we should ensure previous channel is closed.
      _channel?.sink.close(status.goingAway); 
    }

    try {
      final uri = Uri.parse(url);
      debugPrint('Connecting to WebSocket: $uri (Attempt: $_reconnectAttempts)');
      
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      
      // Listen to stream to detect closure/error for reconnection
      // Note: We are not consuming the stream here, just listening for done/error.
      // But WebSocketChannel stream is single-subscription usually.
      // If we listen here, the provider won't be able to listen.
      // SOLUTION: We can't listen here if we expose `stream` directly.
      // We should probably wrap the stream or check if `WebSocketChannel` allows determining status.
      // The `web_socket_channel` package doesn't expose connection state easily without listening.
      // If we want auto-reconnect, we must control the stream.
      // So we should expose a `StreamController` that we pipe events into.
      
    } catch (e) {
      debugPrint('WebSocket connection error: $e');
      _isConnected = false;
      _scheduleReconnect();
      rethrow;
    }
  }
  
  // Since we cannot listen to the stream twice, and refactoring to StreamController 
  // would require changing how `stream` is accessed (it's a getter), 
  // let's stick to a simpler approach or a broadcast stream if needed.
  // BUT, `stream` getter is used by providers.
  // If we change `stream` to return `_controller.stream`, existing code works.
  
  // Refactoring to use StreamController to handle reconnects transparently
  final StreamController<dynamic> _controller = StreamController<dynamic>.broadcast();
  Stream<dynamic> get stream => _controller.stream;
  
  // Re-implement connect to use the controller
  void connectWithRetry(String url) {
     _url = url;
     _isManualDisconnect = false;
     _reconnectAttempts = 0;
     _cancelReconnectTimer();
     _connectAndPipe();
  }
  
  // We keep `connect` signature for compatibility but redirect to internal logic
  void connect(String url, {Map<String, dynamic>? headers}) {
     connectWithRetry(url);
  }

  void _connectAndPipe() {
    if (_url == null) return;
    
    try {
      final uri = Uri.parse(_url!);
      debugPrint('Connecting to WebSocket: $uri (Attempt: $_reconnectAttempts)');
      
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      
      // Pipe events to controller
      _channel!.stream.listen(
        (data) {
          _controller.add(data);
          // Successful message resets attempts
          _reconnectAttempts = 0; 
        },
        onError: (error) {
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
      debugPrint('WebSocket init error: $e');
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
      _connectAndPipe();
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
      _channel!.sink.close(status.goingAway);
      _channel = null;
      _isConnected = false;
    }
  }

  void send(dynamic data) {
    if (_channel != null && _isConnected) {
      if (data is Map || data is List) {
        _channel!.sink.add(jsonEncode(data));
      } else {
        _channel!.sink.add(data);
      }
    } else {
      debugPrint('Cannot send message: WebSocket not connected');
    }
  }
}
