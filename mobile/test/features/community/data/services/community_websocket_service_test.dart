import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/ws_ticket_client.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/community/data/services/community_websocket_service.dart';

/// 认证仓库桩：只提供 access token，其余成员 noSuchMethod 拒绝。
class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => 'test-token';

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not stubbed');
}

/// WS ticket 签发客户端桩：记录签发次数，按脚本返回票或抛错。
class _FakeTicketClient implements WsTicketClient {
  _FakeTicketClient({this.ticket = 'ticket-stub', List<String>? ticketSequence})
      : _ticketSequence = ticketSequence;

  /// 固定票值（无序列脚本时每次签发都返回它）。
  String ticket;

  /// 序列脚本：第 n 次签发返回第 n 个票值（耗尽后回退 [ticket]）——
  /// 用于断言「重连必须携带新票，而非重放已烧掉的那张」。
  final List<String>? _ticketSequence;

  /// 非空时签发抛出该对象（模拟签发通道故障）。
  Exception? throwOnIssue;

  int issueCount = 0;

  @override
  Future<WsTicketGrant?> issue({required String authToken}) async {
    issueCount++;
    final failure = throwOnIssue;
    if (failure != null) {
      throw failure;
    }
    final sequence = _ticketSequence;
    final value = (sequence != null && sequence.isNotEmpty)
        ? sequence[issueCount - 1 < sequence.length
            ? issueCount - 1
            : sequence.length - 1]
        : ticket;
    return WsTicketGrant(ticket: value, expiresIn: 120);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not stubbed');
}

/// 本地 WS 服务器：升级握手并记录请求，可选升级后立即关闭（触发重连）。
class _RecordingWsServer {
  final List<HttpRequest> requests = [];

  /// 升级成功后立即以 1001 关闭 socket（模拟服务端排空/断开）。
  bool closeAfterUpgrade = false;
  HttpServer? _server;
  StreamSubscription<HttpRequest>? _subscription;

  Future<Uri> start() async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _server = server;
    _subscription = server.listen((request) async {
      requests.add(request);
      try {
        final ws = await WebSocketTransformer.upgrade(request);
        if (closeAfterUpgrade) {
          await ws.close(1001, 'server closing');
        }
      } catch (_) {
        // 非 WS 请求或客户端提前断开——请求已记录，忽略升级失败。
      }
    });
    return Uri.parse('ws://${server.address.host}:${server.port}');
  }

  Future<void> stop() async {
    await _subscription?.cancel();
    await _server?.close(force: true);
  }
}

/// 轮询等待第 [count] 个请求到达（避免固定 sleep 的不确定性）。
Future<List<HttpRequest>> _waitForRequests(
  _RecordingWsServer server,
  int count,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 3));
  while (server.requests.length < count) {
    if (DateTime.now().isAfter(deadline)) {
      fail('expected $count upgrade request(s), saw ${server.requests.length}');
    }
    await Future<void>.delayed(const Duration(milliseconds: 10));
  }
  return server.requests;
}

/// 本地 HTTP 服务器：对每个 WS 升级请求返回给定的终态拒绝
/// （与网关 b62b530b 的 writeBackendDialFailure 透传帧同构）。
class _RejectingHandshakeServer {
  _RejectingHandshakeServer(this.statusCode, this.body);

  final int statusCode;
  final String body;
  int requestCount = 0;
  HttpServer? _server;
  StreamSubscription<HttpRequest>? _subscription;

  Future<Uri> start() async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _server = server;
    _subscription = server.listen((request) {
      requestCount++;
      request.response.statusCode = statusCode;
      request.response.headers.contentType = ContentType.json;
      request.response.write(body);
      unawaited(request.response.close());
    });
    return Uri.parse(
      'ws://${server.address.host}:${server.port}',
    );
  }

  Future<void> stop() async {
    await _subscription?.cancel();
    await _server?.close(force: true);
  }
}

void main() {
  group('CommunityEvent', () {
    test('parses from JSON correctly', () {
      final event = CommunityEvent.fromJson({
        'type': 'message',
        'data': 'hello',
        'msg_id': 'msg-123',
      });

      expect(event.type, 'message');
      expect(event.data['type'], 'message');
      expect(event.messageId, 'msg-123');
    });

    test('isAck detects ACK messages', () {
      final ackEvent = CommunityEvent.fromJson({
        'type': 'ack',
        'msg_id': 'msg-456',
      });
      expect(ackEvent.isAck, isTrue);

      final msgEvent = CommunityEvent.fromJson({
        'type': 'message',
        'msg_id': 'msg-789',
      });
      expect(msgEvent.isAck, isFalse);
    });

    test('nonce extraction works', () {
      final event = CommunityEvent.fromJson({
        'type': 'message',
        'nonce': 'abc-123',
      });
      expect(event.nonce, 'abc-123');
    });

    test('handles missing fields gracefully', () {
      final event = CommunityEvent.fromJson({});

      expect(event.type, 'unknown');
      expect(event.messageId, isNull);
      expect(event.nonce, isNull);
      expect(event.isAck, isFalse);
    });

    test('toString provides readable output', () {
      final event = CommunityEvent.fromJson({
        'type': 'message',
        'content': 'test',
      });

      final str = event.toString();
      expect(str, contains('CommunityEvent'));
      expect(str, contains('message'));
    });
  });

  group('WsConnectionState', () {
    test('all states are distinct', () {
      const states = WsConnectionState.values;
      final stateSet = states.toSet();
      expect(states.length, stateSet.length);
    });

    test('has expected states', () {
      expect(
        WsConnectionState.values,
        containsAll([
          WsConnectionState.disconnected,
          WsConnectionState.connecting,
          WsConnectionState.connected,
          WsConnectionState.reconnecting,
          WsConnectionState.error,
          WsConnectionState.failed,
        ]),
      );
    });

    test('state names are readable', () {
      for (final state in WsConnectionState.values) {
        expect(state.name, isNotEmpty);
      }
    });
  });

  group('WsReconnectConfig', () {
    test('default config has sane values', () {
      const config = WsReconnectConfig();

      expect(config.maxAttempts, greaterThan(0));
      expect(config.maxAttempts, 10);
      expect(config.baseDelayMs, greaterThan(0));
      expect(config.baseDelayMs, 1000);
      expect(config.maxDelayMs, greaterThanOrEqualTo(config.baseDelayMs));
      expect(config.maxDelayMs, 30000);
    });

    test('custom config is respected', () {
      const config = WsReconnectConfig(
        maxAttempts: 5,
        baseDelayMs: 500,
        maxDelayMs: 10000,
      );

      expect(config.maxAttempts, 5);
      expect(config.baseDelayMs, 500);
      expect(config.maxDelayMs, 10000);
    });

    test('maxDelayMs should be >= baseDelayMs for sane backoff', () {
      const config = WsReconnectConfig(
        maxAttempts: 3,
        baseDelayMs: 2000,
        maxDelayMs: 1000, // Lower than base — bad config but shouldn't crash
      );

      // Verify it can be created (validation is caller's responsibility)
      expect(config.maxDelayMs, 1000);
    });
  });

  group('AckCallback', () {
    test('typedef allows function assignment', () {
      void callback(msgId) {
        // Acknowledged message
      }

      expect(callback, isNotNull);
    });

    test('callback receives message ID string', () {
      String? receivedId;
      void callback(String msgId) {
        receivedId = msgId;
      }

      callback('msg-abc-123');
      expect(receivedId, 'msg-abc-123');
    });
  });

  group('terminal connection failures (M-3 client-side retry stop)', () {
    test('isTerminalCommunityWsFailure classifies gateway passthrough errors',
        () {
      // 网关 b62b530b 透传：HTTP 握手被上游 401/403/404 拒绝时，
      // dart:io WebSocketException 把状态码带进错误串。
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketChannelException: WebSocketException: Connection to '
          '"ws://x" was not upgraded to websocket, HTTP status code: 403',
        ),
        isTrue,
      );
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketException: handshake failed, HTTP status code: 401',
        ),
        isTrue,
      );
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketException: handshake failed, HTTP status code: 404',
        ),
        isTrue,
      );
      // 网关 JSON 拒帧（retryable:false）
      expect(
        isTerminalCommunityWsFailure(
          '{"error":"websocket_upstream_rejected","upstream_status":403,'
          '"retryable":false}',
        ),
        isTrue,
      );
      expect(
        isTerminalCommunityWsFailure('upstream rejected, retryable: false'),
        isTrue,
      );
      // 瞬态错误必须继续重试
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketChannelException: Connection refused',
        ),
        isFalse,
      );
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketException: handshake failed, HTTP status code: 502',
        ),
        isFalse,
      );
      expect(
        isTerminalCommunityWsFailure(
          'WebSocketException: handshake failed, HTTP status code: 504',
        ),
        isFalse,
      );
      expect(isTerminalCommunityWsFailure(null), isFalse);
      expect(isTerminalCommunityWsFailure(Exception('timeout')), isFalse);
    });

    test('isTerminalCommunityWsFrame classifies in-band reject frames', () {
      expect(
        isTerminalCommunityWsFrame({
          'type': 'error',
          'error': 'websocket_upstream_rejected',
          'upstream_status': 403,
          'retryable': false,
        }),
        isTrue,
      );
      expect(
        isTerminalCommunityWsFrame({'type': 'error', 'retryable': false}),
        isTrue,
      );
      expect(
        isTerminalCommunityWsFrame({'upstream_status': 401}),
        isTrue,
      );
      // 瞬态/无关帧
      expect(
        isTerminalCommunityWsFrame({'type': 'error', 'retryable': true}),
        isFalse,
      );
      expect(
        isTerminalCommunityWsFrame({'type': 'message', 'msg_id': 'm1'}),
        isFalse,
      );
    });

    test('group channel stops retrying after a 403 handshake rejection',
        () async {
      final server = _RejectingHandshakeServer(
        403,
        '{"error":"websocket_upstream_rejected","upstream_status":403,'
        '"retryable":false}',
      );
      final baseUri = await server.start();
      final ticketClient = _FakeTicketClient();
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        reconnectConfig: const WsReconnectConfig(
          maxAttempts: 6,
          baseDelayMs: 40,
          maxDelayMs: 40,
        ),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: ticketClient,
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      await service.connectToGroup('group-1');

      // 给旧实现的重连风暴留足时间（6 次指数退避 × 40ms 若继续重试）。
      await Future<void>.delayed(const Duration(milliseconds: 700));

      // 终态：立即停止，不再 ×N 风暴。
      expect(
        server.requestCount,
        1,
        reason: 'terminal 403 rejection must not trigger any retry',
      );
      // 终态失败同样不得反复烧票（签发口 per-user 限流是主钉）。
      expect(
        ticketClient.issueCount,
        1,
        reason: 'terminal rejection must not re-issue tickets',
      );
      expect(service.groupConnectionState, WsConnectionState.failed);
      expect(service.groupFailureReason, isNotNull);
      expect(service.groupFailureReason, contains('403'));
    });

    test('personal channel stops retrying after a 401 handshake rejection',
        () async {
      final server = _RejectingHandshakeServer(
        401,
        '{"error":"websocket_upstream_rejected","upstream_status":401,'
        '"retryable":false}',
      );
      final baseUri = await server.start();
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        reconnectConfig: const WsReconnectConfig(
          maxAttempts: 6,
          baseDelayMs: 40,
          maxDelayMs: 40,
        ),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: _FakeTicketClient(),
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      await service.connectToPersonal();
      await Future<void>.delayed(const Duration(milliseconds: 700));

      expect(
        server.requestCount,
        1,
        reason: 'terminal 401 rejection must not trigger any retry',
      );
      expect(service.personalConnectionState, WsConnectionState.failed);
      expect(service.personalFailureReason, isNotNull);
      expect(service.personalFailureReason, contains('401'));
    });
  });

  group('WSQ-5 ticket-first handshake (WS-TICKET-DESIGN §四 Step 4)', () {
    test('group connect carries ?ticket= and keeps Authorization header',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: _FakeTicketClient(ticket: 'ticket-group-1'),
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      await service.connectToGroup('group-9');
      final requests = await _waitForRequests(server, 1);

      final request = requests.single;
      expect(request.uri.path, '/api/v1/community/groups/group-9/ws');
      expect(request.uri.queryParameters['ticket'], 'ticket-group-1');
      // 票签发成功后 Authorization 头保留一个版本周期（设计 §3.2 双带语义）。
      expect(request.headers.value('Authorization'), 'Bearer test-token');
      // R7：ticket 走 query，与 json 子协议共存，互不挤占。
      expect(request.headers.value('Sec-WebSocket-Protocol'), 'json');
      expect(service.groupConnectionState, WsConnectionState.connected);
    });

    test('personal connect carries ?ticket= and keeps Authorization header',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: _FakeTicketClient(ticket: 'ticket-personal-1'),
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      await service.connectToPersonal();
      final requests = await _waitForRequests(server, 1);

      final request = requests.single;
      expect(request.uri.path, '/api/v1/community/ws/connect');
      expect(request.uri.queryParameters['ticket'], 'ticket-personal-1');
      expect(request.headers.value('Authorization'), 'Bearer test-token');
      expect(service.personalConnectionState, WsConnectionState.connected);
    });

    test('issuance failure falls back to header-only (no ticket, no token)',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      final ticketClient = _FakeTicketClient()..throwOnIssue = Exception('429');
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: ticketClient,
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      await service.connectToGroup('group-fallback');
      final requests = await _waitForRequests(server, 1);

      final request = requests.single;
      expect(
        request.uri.queryParameters.containsKey('ticket'),
        isFalse,
        reason: 'failed issuance must not put a stale ticket on the wire',
      );
      expect(
        request.uri.queryParameters.containsKey('token'),
        isFalse,
        reason: 'JWT must never travel in the URL (security invariant)',
      );
      expect(request.headers.value('Authorization'), 'Bearer test-token');
      expect(
        service.groupConnectionState,
        WsConnectionState.connected,
        reason: 'header fallback keeps the connect flow alive',
      );
    });

    test('reconnect re-issues a fresh ticket (single-use discipline)',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      final ticketClient = _FakeTicketClient(
        ticketSequence: ['ticket-round-1', 'ticket-round-2'],
      );
      final service = CommunityWebSocketService(
        authRepository: _FakeAuthRepository(),
        reconnectConfig: const WsReconnectConfig(
          maxAttempts: 3,
          baseDelayMs: 40,
          maxDelayMs: 40,
        ),
        wsBaseUrlOverride: baseUri.toString(),
        ticketClient: ticketClient,
      );
      addTearDown(service.dispose);
      addTearDown(server.stop);

      // 第一次建连：签发并携带 ticket-round-1（服务端核销后即作废）。
      await service.connectToGroup('group-reconnect');
      final requests = await _waitForRequests(server, 1);
      expect(requests.single.uri.queryParameters['ticket'], 'ticket-round-1');
      expect(ticketClient.issueCount, 1);

      // 断开重连——服务内部重连路径（_scheduleGroupReconnect）最终也是重新
      // 调用 connectToGroup，此处直接走同一入口：必须重新签发并携带新票，
      // 而非重放已烧掉的那张。
      await service.disconnectGroup();
      await service.connectToGroup('group-reconnect');
      final requests2 = await _waitForRequests(server, 2);

      expect(
        ticketClient.issueCount,
        2,
        reason: 'each (re)connect must mint a new ticket — the old one '
            'was single-use burned by the first handshake',
      );
      expect(
        requests2[1].uri.queryParameters['ticket'],
        'ticket-round-2',
        reason:
            'reconnect must carry the NEW ticket, not replay the burned one',
      );
    });
  });
}
