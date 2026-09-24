import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/ws_ticket_client.dart';
import 'package:sparkle/features/chat/data/services/audio_recording_service.dart';

/// WS ticket 签发客户端桩：记录签发次数，按脚本返回票或抛错。
class _FakeTicketClient implements WsTicketClient {
  _FakeTicketClient({this.ticket = 'ticket-stub'});

  String ticket;

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
    return WsTicketGrant(ticket: ticket, expiresIn: 120);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName} not stubbed');
}

/// 本地 WS 服务器：升级 /ws/stt 握手并记录请求（服务端视角的验收面）。
class _RecordingWsServer {
  final List<HttpRequest> requests = [];
  HttpServer? _server;
  StreamSubscription<HttpRequest>? _subscription;

  Future<Uri> start() async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _server = server;
    _subscription = server.listen((request) async {
      requests.add(request);
      try {
        final ws = await WebSocketTransformer.upgrade(request);
        // 请求已记录，随即收尾断开；用例断言完后随 server.stop(force) 回收。
        await ws.close(1001, 'recorded');
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // record 插件无平台实现：startStream 抛 MissingPluginException，
  // 被 service 的 try/catch 吸收并走 onError 清理——不影响握手验收。
  Future<List<String>> startRecording({
    required AudioRecordingService service,
    required String wsUrl,
    required String authToken,
  }) async {
    final errors = <String>[];
    await service.startRecording(
      wsUrl: wsUrl,
      authToken: authToken,
      onTranscription: (_) {},
      onError: errors.add,
      onCompleted: () {},
    );
    return errors;
  }

  group('WSQ-4 STT ticket-first handshake (WS-TICKET-DESIGN §四 Step 3)', () {
    test('exchanges JWT for ticket: ?ticket= carries, ?token= is gone',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      addTearDown(server.stop);
      final service = AudioRecordingService(
        ticketClient: _FakeTicketClient(ticket: 'ticket-stt-1'),
      );
      addTearDown(service.dispose);

      final errors = await startRecording(
        service: service,
        wsUrl: '$baseUri/ws/stt',
        authToken: 'jwt-stt-abc',
      );
      final requests = await _waitForRequests(server, 1);

      final request = requests.single;
      expect(request.uri.path, '/ws/stt');
      // 修复点：旧实现 `?token=$jwt` 在生产被网关拒绝（ALLOW_WS_QUERY_TOKEN
      // =false → STT 401 潜伏故障）；迁移后 JWT 永不出现在 URL。
      expect(request.uri.queryParameters.containsKey('token'), isFalse);
      expect(request.uri.queryParameters['ticket'], 'ticket-stt-1');
      // 双带语义：票签发成功后 Authorization 头保留一个版本周期。
      expect(request.headers.value('Authorization'), 'Bearer jwt-stt-abc');
      // record 插件在测试环境无平台实现 → 预期恰好一条「启动失败」错误
      // （发生在 WS 连接建立之后），证明流程完整走过换票与握手。
      expect(errors, hasLength(1));
    });

    test('issuance failure falls back to header-only (no ticket, no token)',
        () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      addTearDown(server.stop);
      final ticketClient = _FakeTicketClient()..throwOnIssue = Exception('429');
      final service = AudioRecordingService(ticketClient: ticketClient);
      addTearDown(service.dispose);

      final errors = await startRecording(
        service: service,
        wsUrl: '$baseUri/ws/stt',
        authToken: 'jwt-stt-abc',
      );
      final requests = await _waitForRequests(server, 1);

      final request = requests.single;
      expect(request.uri.queryParameters.containsKey('ticket'), isFalse);
      expect(
        request.uri.queryParameters.containsKey('token'),
        isFalse,
        reason: 'fallback must not resurrect the legacy ?token= leak',
      );
      expect(request.headers.value('Authorization'), 'Bearer jwt-stt-abc');
      // 换票失败不阻断录音流程：连接照常发起（错误仅为测试环境的
      // record 插件缺平台实现，发生在连接建立之后）。
      expect(errors, hasLength(1));
      expect(ticketClient.issueCount, 1);
    });

    test('reissued ticket is minted per recording session', () async {
      final server = _RecordingWsServer();
      final baseUri = await server.start();
      addTearDown(server.stop);
      final ticketClient = _FakeTicketClient(ticket: 'ticket-stt-1');
      final service = AudioRecordingService(ticketClient: ticketClient);
      addTearDown(service.dispose);

      await startRecording(
        service: service,
        wsUrl: '$baseUri/ws/stt',
        authToken: 'jwt-stt-abc',
      );
      await _waitForRequests(server, 1);
      await service.stopRecording();

      // 第一次会话已烧掉单次票；下一次 startRecording 必须重新签发。
      expect(ticketClient.issueCount, 1);
      await startRecording(
        service: service,
        wsUrl: '$baseUri/ws/stt',
        authToken: 'jwt-stt-abc',
      );
      final requests = await _waitForRequests(server, 2);
      expect(ticketClient.issueCount, 2);
      expect(requests[1].uri.queryParameters['ticket'], 'ticket-stt-1');
    });
  });
}
