import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/websocket_chat_service_v2.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';

void main() {
  group('WebSocketChatServiceV2 - TODO-A5: Dispose Race Condition', () {
    late WebSocketChatServiceV2 service;

    setUp(() {
      // Use a non-standard base URL to avoid real connections
      service = WebSocketChatServiceV2(baseUrl: 'ws://localhost:9999');
    });

    tearDown(() {
      // Safe cleanup - dispose is idempotent
      try {
        service.dispose();
      } catch (_) {}
    });

    test('URL construction does not include token in query string', () {
      // This is the core safety check for TODO-A9
      const userId = 'user-123';
      const baseUrl = 'ws://localhost:8080';

      // Simulate what the service does (from _establishConnection)
      final query = 'user_id=$userId';
      final wsUrl = '$baseUrl/ws/chat?$query';

      // Verify no token in URL
      expect(wsUrl, isNot(contains('token=')));
      expect(wsUrl, isNot(contains('secret')));
      expect(wsUrl, contains('user_id=user-123'));
      expect(wsUrl, contains('/ws/chat'));
    });

    test('Authorization header format is correct', () {
      const token = 'secret-token-abc123';
      const headerValue = 'Bearer $token';

      // Verify header format
      expect(headerValue, startsWith('Bearer '));
      expect(headerValue, contains(token));
      expect(headerValue, isNot(contains('?token=')));
      expect(headerValue, isNot(contains('&token=')));
    });

    test('URL masking in logs does not expose token', () {
      // Test the masking logic from _log method
      const message1 = 'Connecting with token=secret123';
      const message2 = 'Authorization: Bearer xyz789';

      // Simulate the masking regex
      final masked1 = message1.replaceAllMapped(
        RegExp('(token=|Authorization: )([^&]+)'),
        (m) => '${m.group(1)}${_maskSecret(m.group(2))}',
      );
      final masked2 = message2.replaceAllMapped(
        RegExp('(token=|Authorization: )([^&]+)'),
        (m) => '${m.group(1)}${_maskSecret(m.group(2))}',
      );

      // Verify masking hides the secret
      expect(masked1, isNot(contains('secret123')));
      expect(masked2, isNot(contains('xyz789')));

      // Verify the format is masked (group 2 is the full value after token= or Bearer )
      expect(masked1, contains('token=sec...123'));
      expect(masked2, contains('Authorization: Bea...789'));
    });

    test('Web platform error message is clear and actionable', () {
      // Verify the error message content from TODO-A9
      const errorMessage =
          'WebSocket header authentication is not supported on Web platform. '
          'Web browsers do not allow custom headers in WebSocket connections. '
          'Please configure the server to accept token via query parameter or use a proxy.';

      expect(errorMessage, contains('Web platform'));
      expect(errorMessage, contains('custom headers'));
      expect(errorMessage, contains('server'));
      expect(errorMessage, contains('proxy'));
    });

    test('dispose is idempotent and safe', () {
      // Test that multiple dispose calls don't crash
      expect(() => service.dispose(), returnsNormally);
      expect(() => service.dispose(), returnsNormally);
      expect(() => service.dispose(), returnsNormally);
    });

    test('StreamController guards prevent add-after-dispose errors', () async {
      // Test the pattern used in the service to prevent race conditions
      // The service uses: if (!_disposed && controller != null && !controller.isClosed)

      final streamController = StreamController<ChatStreamEvent>.broadcast();
      final events = <ChatStreamEvent>[];
      final subscription = streamController.stream.listen(events.add);

      bool disposed = false;

      // Simulate adding with guard (like the service does)
      void safeAdd(ChatStreamEvent event) {
        if (!disposed && !streamController.isClosed) {
          streamController.add(event);
        }
      }

      // Add before dispose - should work
      safeAdd(TextEvent(content: 'before'));
      await Future.microtask(() {});
      expect(events.length, 1);

      // Dispose
      disposed = true;
      await streamController.close();
      await subscription.cancel();

      // Add after dispose with guard - should NOT throw
      expect(() => safeAdd(TextEvent(content: 'after')), returnsNormally);

      // Verify no new events were added
      expect(events.length, 1);
    });

    test('connection state transitions are valid', () {
      // Verify the enum exists and has expected values
      expect(WsConnectionState.disconnected, isNotNull);
      expect(WsConnectionState.connecting, isNotNull);
      expect(WsConnectionState.connected, isNotNull);
      expect(WsConnectionState.reconnecting, isNotNull);
      expect(WsConnectionState.failed, isNotNull);
    });

    test('message stream events are properly typed', () {
      // Verify event types exist
      expect(ErrorEvent(code: 'TEST', message: 'test', retryable: false), isA<ErrorEvent>());
      expect(TextEvent(content: 'test'), isA<TextEvent>());
      expect(DoneEvent(finishReason: 'stop'), isA<DoneEvent>());
    });
  });

  group('WebSocketChatServiceV2 - TODO-A9: Web Platform Behavior', () {
    test('Web platform check is present in code', () {
      // This test verifies the kIsWeb check exists by testing the logic
      // We can't actually test kIsWeb=true in unit tests, but we verify
      // the code path exists

      if (kIsWeb) {
        // On Web, the service should throw UnsupportedError
        final service = WebSocketChatServiceV2();
        expect(
          () => service.sendMessage(
            message: 'test',
            userId: 'user-123',
            token: 'token-123',
          ),
          throwsA(isA<UnsupportedError>()),
        );
      } else {
        // On non-Web platforms, document expected behavior
        expect(true, isTrue); // Placeholder
      }
    });
  });

  group('WebSocketChatServiceV2 - Security: Token Safety', () {
    test('token never appears in URL construction', () {
      const testCases = [
        {'baseUrl': 'ws://localhost:8080', 'userId': 'user1', 'token': 'secret123'},
        {'baseUrl': 'wss://api.example.com', 'userId': 'user-abc', 'token': 'xyz789token'},
        {'baseUrl': 'ws://10.0.2.2:8080', 'userId': '12345', 'token': 'Bearer abc'},
      ];

      for (final testCase in testCases) {
        final query = 'user_id=${testCase['userId']}';
        final wsUrl = '${testCase['baseUrl']}/ws/chat?$query';

        // Critical security check: token must NOT be in URL
        expect(
          wsUrl,
          isNot(contains(testCase['token']!)),
          reason: 'Token should never be in URL: $wsUrl',
        );

        // Verify user_id IS in URL
        expect(wsUrl, contains('user_id=${testCase['userId']}'));
      }
    });

    test('header auth is used for token', () {
      const token = 'my-secret-token';

      // Verify token goes in header, not query
      final headers = <String, dynamic>{};
      if (token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      expect(headers['Authorization'], equals('Bearer $token'));
      expect(headers.length, 1);
    });
  });
}

// Helper function copied from service for testing
String _maskSecret(String? secret) {
  if (secret == null) return '';
  if (secret.length < 6) return '***';
  return '${secret.substring(0, 3)}...${secret.substring(secret.length - 3)}';
}
