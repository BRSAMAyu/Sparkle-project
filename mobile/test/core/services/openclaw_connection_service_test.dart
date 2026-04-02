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
                jsonEncode(<String, dynamic>{'ok': true, 'status': 'live'}));
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

      final ok = await service.testConnection(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
          transport: 'responses_http',
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
                jsonEncode(<String, dynamic>{'ok': true, 'status': 'live'}));
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
      final ok = await service.testConnection(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
          transport: 'responses_http',
        ),
      );

      expect(ok, isFalse);
      expect(service.info.status, OpenClawConnectionStatus.error);
      expect(service.info.errorMessage, isNotEmpty);
    });

    test('initialization prefers backend profile over local cache', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{
        'openclaw_connection_config': jsonEncode(<String, dynamic>{
          'gateway_url': 'http://127.0.0.1:1111',
          'transport': 'responses_http',
        }),
      });

      final service = OpenClawConnectionService(
        backendProfileLoader: () async => <String, dynamic>{
          'configured': true,
          'gateway_url': 'https://remote.openclaw.example',
          'auth_token': 'profile-token',
          'transport': 'gateway_ws',
          'ws_url': 'wss://remote.openclaw.example',
        },
      );

      await service.initialize();

      expect(service.config.gatewayUrl, 'https://remote.openclaw.example');
      expect(service.config.authToken, 'profile-token');
      expect(service.config.transport, 'gateway_ws');
      expect(service.config.wsUrl, 'wss://remote.openclaw.example');
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

      final ok = await service.configure(
        OpenClawConnectionConfig(
          gatewayUrl: 'http://127.0.0.1:${server.port}',
          authToken: 'sync-token',
          transport: 'responses_http',
        ),
      );

      expect(ok, isTrue);
      expect(savedPayload?['gateway_url'], 'http://127.0.0.1:${server.port}');
      expect(savedPayload?['auth_token'], 'sync-token');
      expect(service.config.authToken, 'sync-token');
    });
  });
}
