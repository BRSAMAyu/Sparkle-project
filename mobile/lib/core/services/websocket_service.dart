import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

class WebSocketService {
  WebSocketChannel? _channel;
  bool _isConnected = false;

  bool get isConnected => _isConnected;
  Stream<dynamic>? get stream => _channel?.stream;

  void connect(String url, {Map<String, dynamic>? headers}) {
    if (_isConnected) {
      disconnect();
    }

    try {
      // Create URI
      final uri = Uri.parse(url);
      
      debugPrint('Connecting to WebSocket: $uri');
      
      _channel = WebSocketChannel.connect(uri);
      _isConnected = true;
      
    } catch (e) {
      debugPrint('WebSocket connection error: $e');
      _isConnected = false;
      rethrow;
    }
  }

  void disconnect() {
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
