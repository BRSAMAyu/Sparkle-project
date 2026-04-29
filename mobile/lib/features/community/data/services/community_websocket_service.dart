import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket connection state
enum WsConnectionState {
  /// Disconnected - not connected
  disconnected,

  /// Connecting - in the process of establishing connection
  connecting,

  /// Connected - successfully connected and ready
  connected,

  /// Reconnecting - attempting to reconnect after disconnect
  reconnecting,

  /// Error - connection error occurred
  error,

  /// Failed - permanently failed (max retries exceeded)
  failed,
}

/// Community event received from WebSocket
class CommunityEvent {

  CommunityEvent({required this.type, required this.data});

  factory CommunityEvent.fromJson(Map<String, dynamic> json) => CommunityEvent(
      type: json['type'] as String? ?? 'unknown',
      data: json,
    );
  final String type;
  final Map<String, dynamic> data;

  /// Check if this is an ACK message
  bool get isAck => type == 'ack';

  /// Get message ID for ACK
  String? get messageId => data['msg_id'] as String?;

  /// Get nonce for client-side deduplication
  String? get nonce => data['nonce'] as String?;

  @override
  String toString() => 'CommunityEvent(type: $type, data: $data)';
}

/// Configuration for WebSocket reconnection
class WsReconnectConfig {

  const WsReconnectConfig({
    this.maxAttempts = 10,
    this.baseDelayMs = 1000,
    this.maxDelayMs = 30000,
  });
  final int maxAttempts;
  final int baseDelayMs;
  final int maxDelayMs;
}

/// Signature for ACK callback
typedef AckCallback = void Function(String);

/// Community WebSocket Service
/// Handles real-time communication for group chats and personal notifications
class CommunityWebSocketService {

  CommunityWebSocketService({
    required AuthRepository authRepository,
    WsReconnectConfig reconnectConfig = const WsReconnectConfig(),
  })  : _authRepository = authRepository,
        _reconnectConfig = reconnectConfig;
  final AuthRepository _authRepository;
  final WsReconnectConfig _reconnectConfig;

  WebSocketChannel? _groupChannel;
  WebSocketChannel? _personalChannel;
  StreamSubscription<dynamic>? _groupSubscription;
  StreamSubscription<dynamic>? _personalSubscription;

  // Message deduplication cache
  final Set<String> _receivedMessageIds = {};
  static const int _maxMessageCacheSize = 1000;

  // Connection state controllers
  final _groupStateController = StreamController<WsConnectionState>.broadcast();
  final _personalStateController = StreamController<WsConnectionState>.broadcast();
  final _eventController = StreamController<CommunityEvent>.broadcast();

  // Reconnection mechanism
  Timer? _groupReconnectTimer;
  Timer? _personalReconnectTimer;
  int _groupReconnectAttempts = 0;
  int _personalReconnectAttempts = 0;

  // Pending ACK messages (nonce -> callback)
  final Map<String, AckCallback> _pendingAcks = {};

  // Current connections
  String? _currentGroupId;

  Stream<WsConnectionState> get groupState => _groupStateController.stream;
  Stream<WsConnectionState> get personalState => _personalStateController.stream;
  Stream<CommunityEvent> get events => _eventController.stream;

  WsConnectionState? _groupConnectionState;
  WsConnectionState? _personalConnectionState;

  /// Get current group connection state
  WsConnectionState? get groupConnectionState => _groupConnectionState;

  /// Get current personal connection state
  WsConnectionState? get personalConnectionState => _personalConnectionState;

  /// Check if group connection is active
  bool get isGroupConnected =>
      _groupConnectionState == WsConnectionState.connected;

  /// Check if personal connection is active
  bool get isPersonalConnected =>
      _personalConnectionState == WsConnectionState.connected;

  /// Connect to a group chat WebSocket
  Future<void> connectToGroup(String groupId) async {
    // Disconnect existing group connection if any
    if (_groupChannel != null) {
      await disconnectGroup();
    }

    final token = await _authRepository.getAccessToken();
    if (token == null) {
      debugPrint('[WS] No access token available');
      _setGroupState(WsConnectionState.error);
      return;
    }

    final wsUrl = '${ApiConstants.wsBaseUrl}/api/v1/community/groups/$groupId/ws?token=$token';

    debugPrint('[WS] Connecting to group: $groupId');

    try {
      _groupReconnectAttempts = 0;
      _currentGroupId = groupId;

      _groupChannel = WebSocketChannel.connect(
        Uri.parse(wsUrl),
        protocols: ['json'],
      );

      _setGroupState(WsConnectionState.connecting);

      _groupSubscription = _groupChannel!.stream.listen(
        _handleGroupMessage,
        onError: _handleGroupError,
        onDone: _handleGroupDone,
        cancelOnError: false,
      );

      // Give connection a moment to establish
      await Future<void>.delayed(const Duration(milliseconds: 100));

      if (_groupChannel != null) {
        _setGroupState(WsConnectionState.connected);
        _groupReconnectAttempts = 0;
        debugPrint('[WS] Group connection established: $groupId');
      }
    } catch (e) {
      debugPrint('[WS] Group connection error: $e');
      _setGroupState(WsConnectionState.error);
      _scheduleGroupReconnect(groupId);
    }
  }

  /// Connect to personal WebSocket (private messages, notifications)
  Future<void> connectToPersonal() async {
    // Disconnect existing personal connection if any
    if (_personalChannel != null) {
      await disconnectPersonal();
    }

    final token = await _authRepository.getAccessToken();
    if (token == null) {
      debugPrint('[WS] No access token available');
      _setPersonalState(WsConnectionState.error);
      return;
    }

    final wsUrl = '${ApiConstants.wsBaseUrl}/api/v1/community/ws/connect?token=$token';

    debugPrint('[WS] Connecting to personal channel');

    try {
      _personalReconnectAttempts = 0;
      // Token already embedded in URL

      _personalChannel = WebSocketChannel.connect(
        Uri.parse(wsUrl),
        protocols: ['json'],
      );

      _setPersonalState(WsConnectionState.connecting);

      _personalSubscription = _personalChannel!.stream.listen(
        _handlePersonalMessage,
        onError: _handlePersonalError,
        onDone: _handlePersonalDone,
        cancelOnError: false,
      );

      // Give connection a moment to establish
      await Future<void>.delayed(const Duration(milliseconds: 100));

      if (_personalChannel != null) {
        _setPersonalState(WsConnectionState.connected);
        _personalReconnectAttempts = 0;
        debugPrint('[WS] Personal connection established');
      }
    } catch (e) {
      debugPrint('[WS] Personal connection error: $e');
      _setPersonalState(WsConnectionState.error);
      _schedulePersonalReconnect();
    }
  }

  /// Send a message through the group WebSocket
  void sendGroupMessage(Map<String, dynamic> message) {
    if (_groupChannel == null) {
      debugPrint('[WS] Cannot send message: group not connected');
      return;
    }

    try {
      final json = jsonEncode(message);
      _groupChannel!.sink.add(json);
      debugPrint('[WS] Sent group message: ${message['type']}');
    } catch (e) {
      debugPrint('[WS] Error sending group message: $e');
    }
  }

  /// Send typing indicator
  void sendTypingIndicator(String groupId) {
    sendGroupMessage({
      'type': 'typing',
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });
  }

  /// Send ACK for a received message
  void _sendAck(WebSocketChannel? channel, String msgId) {
    if (channel == null) return;

    try {
      channel.sink.add(jsonEncode({
        'type': 'ack',
        'msg_id': msgId,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      }),);
    } catch (e) {
      debugPrint('[WS] Error sending ACK: $e');
    }
  }

  void _handleGroupMessage(dynamic data) {
    if (data is! String) return;

    try {
      final json = jsonDecode(data) as Map<String, dynamic>;

      // Message deduplication
      final msgId = json['id'] as String?;
      if (msgId != null) {
        if (_receivedMessageIds.contains(msgId)) {
          debugPrint('[WS] Duplicate message ignored: $msgId');
          return;
        }
        _receivedMessageIds.add(msgId);
        if (_receivedMessageIds.length > _maxMessageCacheSize) {
          _receivedMessageIds.remove(_receivedMessageIds.first);
        }
      }

      // Handle ACK messages
      if (json['type'] == 'ack' && json['nonce'] != null) {
        final nonce = json['nonce'] as String;
        final messageId = json['message_id'] as String?;
        final callback = _pendingAcks.remove(nonce);
        if (callback != null && messageId != null) {
          callback(messageId);
        }
        return;
      }

      // Send ACK for messages with msg_id
      if (json['msg_id'] != null) {
        _sendAck(_groupChannel, json['msg_id'] as String);
      }

      // Dispatch event
      final event = CommunityEvent.fromJson(json);
      _eventController.add(event);
    } catch (e) {
      debugPrint('[WS] Parse error: $e');
    }
  }

  void _handlePersonalMessage(dynamic data) {
    // Similar handling as group messages
    if (data is! String) return;

    try {
      final json = jsonDecode(data) as Map<String, dynamic>;

      // Message deduplication
      final msgId = json['id'] as String?;
      if (msgId != null) {
        if (_receivedMessageIds.contains(msgId)) {
          debugPrint('[WS] Duplicate message ignored: $msgId');
          return;
        }
        _receivedMessageIds.add(msgId);
        if (_receivedMessageIds.length > _maxMessageCacheSize) {
          _receivedMessageIds.remove(_receivedMessageIds.first);
        }
      }

      // Handle ACK messages
      if (json['type'] == 'ack' && json['nonce'] != null) {
        final nonce = json['nonce'] as String;
        final messageId = json['message_id'] as String?;
        final callback = _pendingAcks.remove(nonce);
        if (callback != null && messageId != null) {
          callback(messageId);
        }
        return;
      }

      // Send ACK for messages with msg_id
      if (json['msg_id'] != null) {
        _sendAck(_personalChannel, json['msg_id'] as String);
      }

      // Dispatch event
      final event = CommunityEvent.fromJson(json);
      _eventController.add(event);
    } catch (e) {
      debugPrint('[WS] Parse error: $e');
    }
  }

  void _setGroupState(WsConnectionState state) {
    _groupConnectionState = state;
    _groupStateController.add(state);
  }

  void _setPersonalState(WsConnectionState state) {
    _personalConnectionState = state;
    _personalStateController.add(state);
  }

  void _scheduleGroupReconnect(String groupId) {
    if (_groupReconnectAttempts >= _reconnectConfig.maxAttempts) {
      _setGroupState(WsConnectionState.failed);
      debugPrint('[WS] Group reconnection failed: max attempts reached');
      return;
    }

    final delay = min(
      _reconnectConfig.baseDelayMs * pow(2, _groupReconnectAttempts).toInt(),
      _reconnectConfig.maxDelayMs,
    );

    _setGroupState(WsConnectionState.reconnecting);
    debugPrint('[WS] Scheduling group reconnect in ${delay}ms (attempt ${_groupReconnectAttempts + 1})');

    _groupReconnectTimer = Timer(Duration(milliseconds: delay), () {
      _groupReconnectAttempts++;
      connectToGroup(groupId);
    });
  }

  void _schedulePersonalReconnect() {
    if (_personalReconnectAttempts >= _reconnectConfig.maxAttempts) {
      _setPersonalState(WsConnectionState.failed);
      debugPrint('[WS] Personal reconnection failed: max attempts reached');
      return;
    }

    final delay = min(
      _reconnectConfig.baseDelayMs * pow(2, _personalReconnectAttempts).toInt(),
      _reconnectConfig.maxDelayMs,
    );

    _setPersonalState(WsConnectionState.reconnecting);
    debugPrint('[WS] Scheduling personal reconnect in ${delay}ms (attempt ${_personalReconnectAttempts + 1})');

    _personalReconnectTimer = Timer(Duration(milliseconds: delay), () {
      _personalReconnectAttempts++;
      connectToPersonal();
    });
  }

  void _handleGroupError(Object error) {
    debugPrint('[WS] Group stream error: $error');
    _setGroupState(WsConnectionState.error);
  }

  void _handleGroupDone() {
    debugPrint('[WS] Group stream closed');
    _setGroupState(WsConnectionState.disconnected);

    // Attempt reconnection
    if (_currentGroupId != null) {
      _scheduleGroupReconnect(_currentGroupId!);
    }
  }

  void _handlePersonalError(Object error) {
    debugPrint('[WS] Personal stream error: $error');
    _setPersonalState(WsConnectionState.error);
  }

  void _handlePersonalDone() {
    debugPrint('[WS] Personal stream closed');
    _setPersonalState(WsConnectionState.disconnected);

    // Attempt reconnection
    _schedulePersonalReconnect();
  }

  /// Disconnect from group WebSocket
  Future<void> disconnectGroup() async {
    _groupReconnectTimer?.cancel();
    _groupReconnectTimer = null;
    _groupReconnectAttempts = 0;
    _currentGroupId = null;

    await _groupSubscription?.cancel();
    _groupSubscription = null;

    if (_groupChannel != null) {
      await _groupChannel!.sink.close();
      _groupChannel = null;
    }

    _setGroupState(WsConnectionState.disconnected);
    debugPrint('[WS] Group connection closed');
  }

  /// Disconnect from personal WebSocket
  Future<void> disconnectPersonal() async {
    _personalReconnectTimer?.cancel();
    _personalReconnectTimer = null;
    _personalReconnectAttempts = 0;

    await _personalSubscription?.cancel();
    _personalSubscription = null;

    if (_personalChannel != null) {
      await _personalChannel!.sink.close();
      _personalChannel = null;
    }

    _setPersonalState(WsConnectionState.disconnected);
    debugPrint('[WS] Personal connection closed');
  }

  /// Disconnect all connections and clean up resources
  Future<void> dispose() async {
    await disconnectGroup();
    await disconnectPersonal();

    await _groupStateController.close();
    await _personalStateController.close();
    await _eventController.close();

    _receivedMessageIds.clear();
    _pendingAcks.clear();
  }

  /// Register a callback for message ACK (for client-side deduplication)
  void registerAckCallback(String nonce, void Function(String) callback) {
    _pendingAcks[nonce] = callback;
  }
}
