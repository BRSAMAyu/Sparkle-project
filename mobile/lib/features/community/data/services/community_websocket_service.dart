import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/network/ws_ticket_client.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:web_socket_channel/io.dart';
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

/// M-3 客户端终态停重试（配合网关 b62b530b 的终态透传）：
/// 判断一次 WS 连接失败是否为"终态"——上游明确拒绝（401/403/404）、
/// 网关标记 `retryable:false`，或 WS 4401/4403/4404 close code。
/// 终态失败换凭据/路径也不会成功，客户端必须立即停止重试，
/// 否则会复现 round1 的 ×15 重连风暴。
bool isTerminalCommunityWsFailure(Object? error) {
  if (error == null) return false;
  final text = error.toString();
  // 网关终态拒帧标记（writeBackendDialFailure 透传体）
  if (text.contains('websocket_upstream_rejected')) return true;
  if (text.contains('"retryable":false') || text.contains('retryable: false')) {
    return true;
  }
  // dart:io 握手失败：'WebSocketException: ... HTTP status code: 403'；
  // 网关 JSON 拒帧：'"upstream_status":403'。
  final terminalStatus = RegExp(
    r'status[\s"_-]*code[\s":_=]*(\d{3})\b'
    r'|(?:upstream_)?status"?\s*[:=]\s*"?\s*(\d{3})\b',
    caseSensitive: false,
  ).firstMatch(text);
  if (terminalStatus != null) {
    final status =
        int.parse(terminalStatus.group(1) ?? terminalStatus.group(2)!);
    if (status == 401 || status == 403 || status == 404) return true;
  }
  // WS close code 约定：4401/4403/4404 表示上游鉴权/路由终态
  final closeMatch =
      RegExp(r'close code[:\s]*(\d{4})', caseSensitive: false).firstMatch(text);
  if (closeMatch != null) {
    final code = int.parse(closeMatch.group(1)!);
    if (code == 4401 || code == 4403 || code == 4404) return true;
  }
  if (text.contains('401 unauthorized') || text.contains('403 forbidden')) {
    return true;
  }
  return false;
}

/// 判断一条带内（already-upgraded socket）错误帧是否为终态拒绝。
bool isTerminalCommunityWsFrame(Map<String, dynamic> frame) {
  if (frame['retryable'] == false) return true;
  final upstream = frame['upstream_status'];
  final upstreamStatus = upstream is num
      ? upstream.toInt()
      : upstream is String
          ? int.tryParse(upstream)
          : null;
  if (upstreamStatus == 401 || upstreamStatus == 403 || upstreamStatus == 404) {
    return true;
  }
  final type = frame['type'];
  if (type == 'error' || type == 'connection_failed' || type == 'auth_failed') {
    final errorText = frame['error']?.toString() ?? '';
    if (errorText.isNotEmpty && isTerminalCommunityWsFailure(errorText)) {
      return true;
    }
    if (frame['status'] is num) {
      final status = (frame['status'] as num).toInt();
      if (status == 401 || status == 403 || status == 404) return true;
    }
  }
  return false;
}

/// Community WebSocket Service
/// Handles real-time communication for group chats and personal notifications
class CommunityWebSocketService {
  CommunityWebSocketService({
    required AuthRepository authRepository,
    WsReconnectConfig reconnectConfig = const WsReconnectConfig(),

    /// 测试注入：覆盖 WS 基地址（默认 [ApiConstants.wsBaseUrl]）。
    String? wsBaseUrlOverride,

    /// WS ticket 签发客户端（WSQ-5，WS-TICKET-DESIGN §四 Step 4）；测试可注入桩。
    WsTicketClient? ticketClient,
  })  : _authRepository = authRepository,
        _reconnectConfig = reconnectConfig,
        _wsBaseUrlOverride = wsBaseUrlOverride,
        _ticketClient = ticketClient ?? WsTicketClient();
  final AuthRepository _authRepository;
  final WsReconnectConfig _reconnectConfig;
  final String? _wsBaseUrlOverride;
  final WsTicketClient _ticketClient;

  String get _wsBaseUrl => _wsBaseUrlOverride ?? ApiConstants.wsBaseUrl;

  WebSocketChannel? _groupChannel;
  WebSocketChannel? _personalChannel;
  StreamSubscription<dynamic>? _groupSubscription;
  StreamSubscription<dynamic>? _personalSubscription;

  // Message deduplication cache
  final Set<String> _receivedMessageIds = {};
  static const int _maxMessageCacheSize = 1000;

  // Connection state controllers
  final _groupStateController = StreamController<WsConnectionState>.broadcast();
  final _personalStateController =
      StreamController<WsConnectionState>.broadcast();
  final _eventController = StreamController<CommunityEvent>.broadcast();

  // Reconnection mechanism
  Timer? _groupReconnectTimer;
  Timer? _personalReconnectTimer;
  int _groupReconnectAttempts = 0;
  int _personalReconnectAttempts = 0;

  // M-3：终态失败标记。置位后禁止任何自动重连（含 onDone 触发的那类），
  // 原因向外暴露供 UI surfaced。
  bool _groupTerminalFailure = false;
  bool _personalTerminalFailure = false;
  String? _groupFailureReason;
  String? _personalFailureReason;

  /// 最近一次群聊通道终态失败的原因（null = 无终态失败）。
  String? get groupFailureReason => _groupFailureReason;

  /// 最近一次个人通道终态失败的原因（null = 无终态失败）。
  String? get personalFailureReason => _personalFailureReason;

  // Pending ACK messages (nonce -> callback)
  final Map<String, AckCallback> _pendingAcks = {};

  // Current connections
  String? _currentGroupId;

  Stream<WsConnectionState> get groupState => _groupStateController.stream;
  Stream<WsConnectionState> get personalState =>
      _personalStateController.stream;
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

    final wsUrl = '$_wsBaseUrl/api/v1/community/groups/$groupId/ws';

    debugPrint('[WS] Connecting to group: $groupId');

    // WSQ-5（WS-TICKET-DESIGN §四 Step 4）：ticket-first 握手——JWT 换单次票
    // 后以 ?ticket= 携带。票单次核销，重连路径经 [connectToGroup] 重新入内，
    // 天然逐次换新票。签发失败回退 Authorization 头（过渡期双带无害）。
    final ticket = await _issueTicketSafely(token);
    final wsUri = Uri.parse(wsUrl).replace(
      queryParameters: ticket == null ? null : {'ticket': ticket},
    );

    try {
      _groupReconnectAttempts = 0;
      _groupTerminalFailure = false;
      _groupFailureReason = null;
      _currentGroupId = groupId;

      _groupChannel = IOWebSocketChannel.connect(
        wsUri,
        protocols: ['json'],
        headers: {'Authorization': 'Bearer $token'},
      );

      _setGroupState(WsConnectionState.connecting);

      // 握手失败会同时打到 stream 的 onError 与 ready；在这里消费 ready 的
      // 错误，避免未处理的异步异常泄漏（错误本身由 _handleGroupError 分类）。
      unawaited(
        _groupChannel!.ready.catchError((Object e) {
          debugPrint('[WS] Group handshake ready error (handled): $e');
        }),
      );

      _groupSubscription = _groupChannel!.stream.listen(
        _handleGroupMessage,
        onError: _handleGroupError,
        onDone: _handleGroupDone,
        cancelOnError: false,
      );

      // Give connection a moment to establish
      await Future<void>.delayed(const Duration(milliseconds: 100));

      if (_groupChannel != null && !_groupTerminalFailure) {
        _setGroupState(WsConnectionState.connected);
        _groupReconnectAttempts = 0;
        debugPrint('[WS] Group connection established: $groupId');
      }
    } catch (e) {
      if (isTerminalCommunityWsFailure(e)) {
        debugPrint('[WS] Group terminal failure (no retry): $e');
        _failGroupPermanently(e.toString());
        return;
      }
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

    final wsUrl = '$_wsBaseUrl/api/v1/community/ws/connect';

    debugPrint('[WS] Connecting to personal channel');

    // WSQ-5：ticket-first 握手（语义同 [connectToGroup]）。
    final ticket = await _issueTicketSafely(token);
    final wsUri = Uri.parse(wsUrl).replace(
      queryParameters: ticket == null ? null : {'ticket': ticket},
    );

    try {
      _personalReconnectAttempts = 0;
      _personalTerminalFailure = false;
      _personalFailureReason = null;

      _personalChannel = IOWebSocketChannel.connect(
        wsUri,
        protocols: ['json'],
        headers: {'Authorization': 'Bearer $token'},
      );

      _setPersonalState(WsConnectionState.connecting);

      // 握手失败会同时打到 stream 的 onError 与 ready；在这里消费 ready 的
      // 错误，避免未处理的异步异常泄漏（错误本身由 _handlePersonalError 分类）。
      unawaited(
        _personalChannel!.ready.catchError((Object e) {
          debugPrint('[WS] Personal handshake ready error (handled): $e');
        }),
      );

      _personalSubscription = _personalChannel!.stream.listen(
        _handlePersonalMessage,
        onError: _handlePersonalError,
        onDone: _handlePersonalDone,
        cancelOnError: false,
      );

      // Give connection a moment to establish
      await Future<void>.delayed(const Duration(milliseconds: 100));

      if (_personalChannel != null && !_personalTerminalFailure) {
        _setPersonalState(WsConnectionState.connected);
        _personalReconnectAttempts = 0;
        debugPrint('[WS] Personal connection established');
      }
    } catch (e) {
      if (isTerminalCommunityWsFailure(e)) {
        debugPrint('[WS] Personal terminal failure (no retry): $e');
        _failPersonalPermanently(e.toString());
        return;
      }
      debugPrint('[WS] Personal connection error: $e');
      _setPersonalState(WsConnectionState.error);
      _schedulePersonalReconnect();
    }
  }

  /// 用 JWT 换单次 WS 票；失败不阻断建连（返回 null 时走 Authorization 头
  /// 回退，见 [WsTicketClient.issue] 的过渡期语义）。
  Future<String?> _issueTicketSafely(String token) async {
    try {
      final grant = await _ticketClient.issue(authToken: token);
      return grant?.ticket;
    } catch (e) {
      debugPrint(
          '[WS] Ticket issuance failed, falling back to header auth: $e');
      return null;
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
      channel.sink.add(
        jsonEncode({
          'type': 'ack',
          'msg_id': msgId,
          'timestamp': DateTime.now().millisecondsSinceEpoch,
        }),
      );
    } catch (e) {
      debugPrint('[WS] Error sending ACK: $e');
    }
  }

  void _handleGroupMessage(dynamic data) {
    if (data is! String) return;

    try {
      final json = jsonDecode(data) as Map<String, dynamic>;

      // M-3：带内终态拒帧（网关透传 / 引擎下发的 retryable:false）。
      if (isTerminalCommunityWsFrame(json)) {
        debugPrint('[WS] Group terminal reject frame (no retry): $data');
        _failGroupPermanently(data);
        return;
      }

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

      // M-3：带内终态拒帧（网关透传 / 引擎下发的 retryable:false）。
      if (isTerminalCommunityWsFrame(json)) {
        debugPrint('[WS] Personal terminal reject frame (no retry): $data');
        _failPersonalPermanently(data);
        return;
      }

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

  /// M-3：群聊通道终态失败——立即清场并停在 failed，绝不自动重连。
  /// 重新连接的唯一入口是用户显式调用 [connectToGroup]（会复位终态标记）。
  void _failGroupPermanently(String reason) {
    if (_groupTerminalFailure) return;
    _groupTerminalFailure = true;
    _groupFailureReason = reason;
    _groupReconnectTimer?.cancel();
    _groupReconnectTimer = null;
    _currentGroupId = null;
    unawaited(_groupSubscription?.cancel());
    _groupSubscription = null;
    _groupChannel = null;
    _setGroupState(WsConnectionState.failed);
  }

  /// M-3：个人通道终态失败（语义同 [_failGroupPermanently]）。
  void _failPersonalPermanently(String reason) {
    if (_personalTerminalFailure) return;
    _personalTerminalFailure = true;
    _personalFailureReason = reason;
    _personalReconnectTimer?.cancel();
    _personalReconnectTimer = null;
    unawaited(_personalSubscription?.cancel());
    _personalSubscription = null;
    _personalChannel = null;
    _setPersonalState(WsConnectionState.failed);
  }

  void _scheduleGroupReconnect(String groupId) {
    if (_groupTerminalFailure) return;
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
    debugPrint(
        '[WS] Scheduling group reconnect in ${delay}ms (attempt ${_groupReconnectAttempts + 1})');

    _groupReconnectTimer = Timer(Duration(milliseconds: delay), () {
      _groupReconnectAttempts++;
      unawaited(connectToGroup(groupId));
    });
  }

  void _schedulePersonalReconnect() {
    if (_personalTerminalFailure) return;
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
    debugPrint(
        '[WS] Scheduling personal reconnect in ${delay}ms (attempt ${_personalReconnectAttempts + 1})');

    _personalReconnectTimer = Timer(Duration(milliseconds: delay), () {
      _personalReconnectAttempts++;
      unawaited(connectToPersonal());
    });
  }

  void _handleGroupError(Object error) {
    // M-3：终态失败（上游 401/403/404、retryable:false）→ 立即停重试。
    if (isTerminalCommunityWsFailure(error)) {
      debugPrint('[WS] Group terminal failure (no retry): $error');
      _failGroupPermanently(error.toString());
      return;
    }
    debugPrint('[WS] Group stream error: $error');
    _setGroupState(WsConnectionState.error);
  }

  void _handleGroupDone() {
    debugPrint('[WS] Group stream closed');
    if (_groupTerminalFailure) {
      _setGroupState(WsConnectionState.failed);
      return;
    }
    _setGroupState(WsConnectionState.disconnected);

    // Attempt reconnection
    if (_currentGroupId != null) {
      _scheduleGroupReconnect(_currentGroupId!);
    }
  }

  void _handlePersonalError(Object error) {
    // M-3：终态失败（上游 401/403/404、retryable:false）→ 立即停重试。
    if (isTerminalCommunityWsFailure(error)) {
      debugPrint('[WS] Personal terminal failure (no retry): $error');
      _failPersonalPermanently(error.toString());
      return;
    }
    debugPrint('[WS] Personal stream error: $error');
    _setPersonalState(WsConnectionState.error);
  }

  void _handlePersonalDone() {
    debugPrint('[WS] Personal stream closed');
    if (_personalTerminalFailure) {
      _setPersonalState(WsConnectionState.failed);
      return;
    }
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
    _groupTerminalFailure = false;
    _groupFailureReason = null;

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
    _personalTerminalFailure = false;
    _personalFailureReason = null;

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
