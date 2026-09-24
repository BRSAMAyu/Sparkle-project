import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/ws_ticket_client.dart';

/// 桩网关回执：状态码 + JSON 体。
class _StubReply {
  const _StubReply(this.statusCode, this.body);
  final int statusCode;
  final String body;
}

_StubReply _ok(String ticket, {int expiresIn = 120}) => _StubReply(
      200,
      jsonEncode({
        'ticket': ticket,
        'expires_in': expiresIn,
        'token_type': 'ws_ticket',
      }),
    );

/// 本地 HTTP 桩网关：记录收到的请求并按脚本回执（模拟 /api/v1/ws/ticket）。
class _FakeTicketGateway {
  _FakeTicketGateway(this._replyFor);

  final _StubReply Function(HttpRequest request, String body) _replyFor;
  final List<HttpRequest> requests = [];
  HttpServer? _server;
  StreamSubscription<HttpRequest>? _subscription;

  Future<Uri> start() async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _server = server;
    _subscription = server.listen((request) async {
      requests.add(request);
      final body = await utf8.decoder.bind(request).join();
      final reply = _replyFor(request, body);
      request.response.statusCode = reply.statusCode;
      request.response.headers.contentType = ContentType.json;
      request.response.write(reply.body);
      await request.response.close();
    });
    return Uri.parse('http://${server.address.host}:${server.port}');
  }

  Future<void> stop() async {
    await _subscription?.cancel();
    await _server?.close(force: true);
  }
}

void main() {
  // 注意：本文件刻意不初始化 TestWidgetsFlutterBinding——该绑定会把
  // HttpClient 整体替换为返回 400 的桩，真实 loopback HTTP 桩网关将不可达。
  // WsTicketClient 是纯 Dart（dio + HttpServer），无需 Flutter 绑定。
  group('WsTicketClient.issue (mock gateway issuance paths)', () {
    test('exchanges JWT for a ticket: POST /ws/ticket + Bearer header',
        () async {
      final gateway = _FakeTicketGateway((_, __) => _ok('ticket-uuid-1'));
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      final grant = await client.issue(authToken: 'jwt-abc');

      expect(grant, isNotNull);
      expect(grant!.ticket, 'ticket-uuid-1');
      expect(grant.expiresIn, 120);

      expect(gateway.requests, hasLength(1));
      final request = gateway.requests.single;
      expect(request.method, 'POST');
      expect(request.uri.path, '/ws/ticket');
      expect(request.headers.value('Authorization'), 'Bearer jwt-abc');
    });

    test('returns null on 401 (unauthenticated)', () async {
      final gateway = _FakeTicketGateway(
        (_, __) => const _StubReply(401, '{"error":"unauthorized"}'),
      );
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null on 429 (per-user issuance rate limited)', () async {
      final gateway = _FakeTicketGateway(
        (_, __) => const _StubReply(429, '{"error":"rate_limit_exceeded"}'),
      );
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null on 5xx (ticket service unavailable)', () async {
      final gateway = _FakeTicketGateway(
        (_, __) => const _StubReply(503, '{"error":"unavailable"}'),
      );
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null when expires_in is within the 5s usability margin',
        () async {
      // 设计 §3.2 规约：expires_in - 5s 内视为不可用——等握完手票已过期，
      // 按签发失败处理，绝不用一张即将过期的票去握手。
      final gateway =
          _FakeTicketGateway((_, __) => _ok('ticket-dying', expiresIn: 5));
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null when ticket field is missing', () async {
      final gateway = _FakeTicketGateway(
        (_, __) => const _StubReply(
            200, '{"expires_in":120,"token_type":"ws_ticket"}'),
      );
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null on non-JSON body (parse failure)', () async {
      final gateway =
          _FakeTicketGateway((_, __) => const _StubReply(200, 'not-json'));
      final baseUri = await gateway.start();
      addTearDown(gateway.stop);

      final client = WsTicketClient(dio: Dio(BaseOptions(baseUrl: '$baseUri')));
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });

    test('returns null on connection failure (never throws)', () async {
      // 不可达端口：验证 issue 吞掉网络异常返回 null，而非向上抛。
      final client = WsTicketClient(
        dio: Dio(
          BaseOptions(
            baseUrl: 'http://127.0.0.1:1',
            connectTimeout: const Duration(milliseconds: 300),
            receiveTimeout: const Duration(milliseconds: 300),
          ),
        ),
      );
      expect(await client.issue(authToken: 'jwt-abc'), isNull);
    });
  });
}
