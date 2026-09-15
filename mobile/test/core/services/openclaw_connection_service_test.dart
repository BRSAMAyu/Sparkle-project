import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('OpenClawConnectionService', () {
    setUp(() {
      SharedPreferences.setMockInitialValues(<String, Object>{});
    });

    test(
        'falls back to backend execution availability when local token lacks write scope',
        () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(server.close);
      server.listen((request) async {
        if (request.uri.path == '/health') {
          request.response
            ..statusCode = HttpStatus.ok
            ..headers.contentType = ContentType.json
            ..write(
              jsonEncode(<String, dynamic>{'ok': true, 'status': 'live'}),
            );
        } else if (request.uri.path == '/v1/responses') {
          request.response
            ..statusCode = HttpStatus.forbidden
            ..headers.contentType = ContentType.json
            ..write(
              jsonEncode(<String, dynamic>{
                'ok': false,
                'error': <String, dynamic>{
                  'type': 'forbidden',
                  'message': 'missing scope: operator.write',
                },
              }),
            );
        } else {
          request.response.statusCode = HttpStatus.notFound;
        }
        await request.response.close();
      });

      final service = OpenClawConnectionService(
        backendStatusLoader: () async => <String, dynamic>{
          'reachable': true,
          'latency_ms': 18,
          'connected_nodes': 2,
          'capabilities': <String>['实时生命周期'],
          'supports_templates': true,
          'supports_quality_loop': true,
        },
      );
      addTearDown(service.dispose);

      final ok = await service.testConnection(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
        ),
      );

      expect(ok, isTrue);
      expect(service.info.status, OpenClawConnectionStatus.connected);
      expect(service.hasExecutionPermissionIssue, isFalse);
      expect(service.info.nodeCount, 2);
      expect(service.info.capabilities, contains('Sparkle 后端代连'));
    });

    test(
        'preserves local permission failure when backend fallback is unavailable',
        () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(server.close);
      server.listen((request) async {
        if (request.uri.path == '/health') {
          request.response
            ..statusCode = HttpStatus.ok
            ..headers.contentType = ContentType.json
            ..write(
              jsonEncode(<String, dynamic>{'ok': true, 'status': 'live'}),
            );
        } else if (request.uri.path == '/v1/responses') {
          request.response
            ..statusCode = HttpStatus.forbidden
            ..headers.contentType = ContentType.json
            ..write(
              jsonEncode(<String, dynamic>{
                'ok': false,
                'error': <String, dynamic>{
                  'type': 'forbidden',
                  'message': 'missing scope: operator.write',
                },
              }),
            );
        } else {
          request.response.statusCode = HttpStatus.notFound;
        }
        await request.response.close();
      });

      final service = OpenClawConnectionService();
      addTearDown(service.dispose);
      final ok = await service.testConnection(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
        ),
      );

      expect(ok, isFalse);
      expect(service.info.status, OpenClawConnectionStatus.error);
      expect(service.info.errorMessage, isNotEmpty);
    });

    test('initialization prefers backend profile over local cache', () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(server.close);
      server.listen((request) async {
        request.response
          ..statusCode = HttpStatus.ok
          ..headers.contentType = ContentType.json
          ..write(jsonEncode(<String, dynamic>{'ok': true}));
        await request.response.close();
      });

      SharedPreferences.setMockInitialValues(<String, Object>{
        'openclaw_connection_config': jsonEncode(<String, dynamic>{
          'gateway_url': 'http://127.0.0.1:1111',
          'transport': 'responses_http',
        }),
      });

      final service = OpenClawConnectionService(
        backendProfileLoader: () async => <String, dynamic>{
          'configured': true,
          'gateway_url': 'http://127.0.0.1:${server.port}',
          'auth_token': 'profile-token',
          'transport': 'gateway_ws',
          'ws_url': 'ws://127.0.0.1:${server.port}',
        },
      );

      await service.initialize();

      expect(service.config.gatewayUrl, 'http://127.0.0.1:${server.port}');
      expect(service.config.authToken, 'profile-token');
      expect(service.config.transport, 'gateway_ws');
      expect(service.config.wsUrl, 'ws://127.0.0.1:${server.port}');

      await Future<void>.delayed(const Duration(milliseconds: 20));
      await service.disconnect();
    });

    test('configure syncs remote profile through backend before health check',
        () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(server.close);
      server.listen((request) async {
        if (request.uri.path == '/health') {
          request.response
            ..statusCode = HttpStatus.ok
            ..headers.contentType = ContentType.json
            ..write(jsonEncode(<String, dynamic>{'ok': true}));
        } else if (request.uri.path == '/v1/responses') {
          request.response
            ..statusCode = HttpStatus.badRequest
            ..headers.contentType = ContentType.json
            ..write(jsonEncode(<String, dynamic>{'error': 'invalid request'}));
        } else {
          request.response.statusCode = HttpStatus.notFound;
        }
        await request.response.close();
      });

      Map<String, dynamic>? savedPayload;
      final service = OpenClawConnectionService(
        backendStatusLoader: () async => <String, dynamic>{
          'reachable': true,
          'connected_nodes': 1,
          'capabilities': <String>['Sparkle 后端代连'],
        },
        backendProfileSaver: (payload) async {
          savedPayload = payload;
          return <String, dynamic>{
            'configured': true,
            ...payload,
          };
        },
      );
      addTearDown(service.dispose);

      final ok = await service.configure(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
          authToken: 'sync-token',
        ),
      );

      expect(ok, isTrue);
      expect(savedPayload?['gateway_url'], 'http://127.0.0.1:${server.port}');
      expect(savedPayload?['auth_token'], 'sync-token');
      expect(service.config.authToken, 'sync-token');
    });

    test('parses JSON pairing payload into gateway ws config', () {
      final payload = OpenClawConnectionService.parsePairingPayload(
        jsonEncode(<String, dynamic>{
          'gateway_url': 'ws://demo.openclaw.local:18789',
          'pair_token': 'pair-secret',
          'device_name': 'Demo MacBook',
        }),
      );

      expect(payload, isNotNull);
      final config = payload!.toConfig();
      expect(config.gatewayUrl, 'http://demo.openclaw.local:18789');
      expect(config.wsUrl, 'ws://demo.openclaw.local:18789');
      expect(config.authToken, 'pair-secret');
      expect(config.transport, 'gateway_ws');
    });

    test('parses openclaw deep link pairing payload', () {
      final payload = OpenClawConnectionService.parsePairingPayload(
        'openclaw://pair?gateway_url=https%3A%2F%2Fopenclaw.example.com&auth_token=token-123&transport=gateway_ws',
      );

      expect(payload, isNotNull);
      final config = payload!.toConfig();
      expect(config.gatewayUrl, 'https://openclaw.example.com');
      expect(config.wsUrl, 'wss://openclaw.example.com');
      expect(config.authToken, 'token-123');
      expect(config.transport, 'gateway_ws');
    });

    test('loads structured connection diagnostics from backend', () async {
      final service = OpenClawConnectionService(
        backendDiagnosticsLoader: () async => <String, dynamic>{
          'reachable': false,
          'overall_status': 'failed',
          'summary': '认证检查未通过：pairing required',
          'generated_at': '2026-04-02T12:00:00Z',
          'transport': 'gateway_ws',
          'connection_source': 'user_profile',
          'gateway_url': 'https://remote.openclaw.example',
          'ws_url': 'wss://remote.openclaw.example',
          'checks': <Map<String, dynamic>>[
            <String, dynamic>{
              'key': 'dns',
              'label': 'DNS 解析',
              'status': 'passed',
              'message': '已解析到 1 个地址',
              'details': <String, dynamic>{
                'addresses': <String>['100.64.0.8'],
              },
            },
            <String, dynamic>{
              'key': 'auth',
              'label': '认证检查',
              'status': 'failed',
              'message': 'pairing required',
              'suggestion': '重新配对当前设备',
            },
          ],
        },
      );
      addTearDown(service.dispose);

      final report = await service.diagnoseConnection();

      expect(report.reachable, isFalse);
      expect(report.overallStatus, OpenClawDiagnosticCheckStatus.failed);
      expect(report.transport, 'gateway_ws');
      expect(report.connectionSource, 'user_profile');
      expect(report.checks, hasLength(2));
      expect(report.checks.last.key, 'auth');
      expect(report.checks.last.suggestion, '重新配对当前设备');
    });
  });
}
