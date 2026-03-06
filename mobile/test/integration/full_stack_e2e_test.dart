import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

const _liveApiBase = String.fromEnvironment(
  'LIVE_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000/api/v1',
);
const _liveGatewayBase = String.fromEnvironment(
  'LIVE_GATEWAY_BASE_URL',
  defaultValue: 'http://127.0.0.1:8080/api/v1',
);
const _liveWsBase = String.fromEnvironment(
  'LIVE_WS_BASE_URL',
  defaultValue: 'ws://127.0.0.1:8080',
);
const _username = String.fromEnvironment(
  'LOCAL_SMOKE_USERNAME',
  defaultValue: 'chat_test',
);
const _password = String.fromEnvironment(
  'LOCAL_SMOKE_PASSWORD',
  defaultValue: 'Chat123456',
);

void main() {
  group('Live local full-stack smoke', () {
    test('api and gateway health endpoints are reachable', () async {
      final apiHealth = await http
          .get(Uri.parse(_stripApiSuffix(_liveApiBase) + '/health'))
          .timeout(const Duration(seconds: 10));
      expect(apiHealth.statusCode, 200, reason: apiHealth.body);

      final gatewayHealth = await http
          .get(Uri.parse('$_liveGatewayBase/health'))
          .timeout(const Duration(seconds: 10));
      expect(gatewayHealth.statusCode, 200, reason: gatewayHealth.body);

      final cqrsHealth = await http
          .get(Uri.parse('$_liveGatewayBase/health/cqrs'))
          .timeout(const Duration(seconds: 10));
      expect(cqrsHealth.statusCode, 200, reason: cqrsHealth.body);
    });

    test('demo account can login and read current profile', () async {
      final session = await _login();

      final me = await http.get(
        Uri.parse('$_liveApiBase/users/me'),
        headers: _bearerHeaders(session.token),
      ).timeout(const Duration(seconds: 10));

      expect(me.statusCode, 200, reason: me.body);
      final profile = jsonDecode(me.body) as Map<String, dynamic>;
      expect(profile['username'], isNotEmpty);
      expect(profile['id'], isNotEmpty);
    });

    test('mobile websocket path can obtain ticket and receive chat frames',
        () async {
      final session = await _login();

      final ticketResp = await http.post(
        Uri.parse('$_liveGatewayBase/ws/ticket'),
        headers: _bearerHeaders(session.token),
      ).timeout(const Duration(seconds: 10));
      expect(ticketResp.statusCode, 200, reason: ticketResp.body);

      final ticketJson = jsonDecode(ticketResp.body) as Map<String, dynamic>;
      final ticket = ticketJson['ticket'] as String?;
      expect(ticket, isNotNull);
      expect(ticket, isNotEmpty);

      final sessionId =
          'mobile-live-${DateTime.now().millisecondsSinceEpoch.toString()}';
      final channel = WebSocketChannel.connect(
        Uri.parse('$_liveWsBase/ws/chat?ticket=$ticket'),
      );
      addTearDown(() async {
        await channel.sink.close();
      });

      channel.sink.add(jsonEncode({
        'message': '本地最终联调验收，请返回任意响应',
        'session_id': sessionId,
        'chat_mode': 'chat',
      }));

      final firstFrame = await channel.stream
          .firstWhere((event) => event != null)
          .timeout(const Duration(seconds: 25));

      expect(firstFrame, isA<Object>());
      final frameText = firstFrame.toString();
      expect(frameText, isNotEmpty);
      expect(frameText, isNot(contains('Unauthorized')));
    });
  });
}

Future<_LiveSession> _login() async {
  final login = await http
      .post(
        Uri.parse('$_liveApiBase/auth/login'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': _username,
          'password': _password,
        }),
      )
      .timeout(const Duration(seconds: 15));

  if (login.statusCode != 200) {
    throw TestFailure('login failed: ${login.statusCode} ${login.body}');
  }

  final data = jsonDecode(login.body) as Map<String, dynamic>;
  final token = data['access_token'] as String?;
  if (token == null || token.isEmpty) {
    throw TestFailure('login response missing access_token: ${login.body}');
  }
  return _LiveSession(token);
}

Map<String, String> _bearerHeaders(String token) => {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };

String _stripApiSuffix(String apiBase) {
  const suffix = '/api/v1';
  if (apiBase.endsWith(suffix)) {
    return apiBase.substring(0, apiBase.length - suffix.length);
  }
  return apiBase;
}

class _LiveSession {
  const _LiveSession(this.token);

  final String token;
}
