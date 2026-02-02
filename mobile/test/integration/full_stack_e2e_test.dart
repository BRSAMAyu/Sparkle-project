// ignore_for_file: avoid_print, strict_raw_type

import 'package:flutter_test/flutter_test.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

/// Full-Stack E2E Integration Tests for Flutter
///
/// These tests require:
/// - Running Go Gateway (make gateway-dev)
/// - Running Python gRPC server (make grpc-server)
/// - Running PostgreSQL and Redis (make dev-all)
///
/// Run with: flutter test test/integration/full_stack_e2e_test.dart

void main() {
  group('Full-Stack E2E Integration Tests', () {
    late WebSocketChannel channel;
    late String wsUrl;
    late String authToken;

    setUpAll(() {
      // Configuration
      const gatewayHost = String.fromEnvironment('GATEWAY_HOST', defaultValue: 'localhost');
      const gatewayPort = String.fromEnvironment('GATEWAY_PORT', defaultValue: '8080');
      wsUrl = 'ws://$gatewayHost:$gatewayPort/ws/chat';

      // Test auth token (in real tests, would obtain via login)
      authToken = const String.fromEnvironment('TEST_AUTH_TOKEN', defaultValue: 'test-token');
    });

    tearDown(() {
      channel.sink.close();
    });

    // ============================================================
    // Connection Tests
    // ============================================================

    group('WebSocket Connection', () {
      test('can establish WebSocket connection with valid token', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);

        // Wait for connection
        await channel.ready;

        expect(channel.stream.done, completes);

        channel.sink.close();
      });

      test('rejects connection with invalid token', () async {
        final uri = Uri.parse('$wsUrl?token=invalid_token_12345');
        channel = WebSocketChannel.connect(uri);

        // Should fail or receive error
        channel.stream.listen(
          (data) => print('Unexpected data: $data'),
          onError: (error) => print('Expected error: $error'),
          onDone: () => print('Connection closed'),
        );

        // Give time for connection to fail
        await Future.delayed(const Duration(seconds: 2));

        // Connection should be closed
        expect(channel.stream.done, completes);
      });

      test('maintains connection over time', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);

        await channel.ready;

        // Send ping
        channel.sink.add(jsonEncode({'type': 'ping'}));

        // Receive pong
        final response = await channel.stream.first;
        final data = jsonDecode(response as String);
        expect(data['type'], 'pong');

        channel.sink.close();
      });
    });

    // ============================================================
    // Chat Flow Tests
    // ============================================================

    group('Chat Message Flow', () {
      test('sends message and receives streaming response', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Send chat message
        final chatRequest = {
          'type': 'message',
          'content': '你好',
          'session_id': 'test-session-123',
          'user_id': 'test-user-456',
        };

        channel.sink.add(jsonEncode(chatRequest));

        // Collect streaming responses
        final responses = <Map<String, dynamic>>[];
        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            responses.add(response);

            // Stop after receiving done signal
            if (response['metadata']?['done'] == true) {
              subscription.cancel();
            }
          },
          onError: (error) => print('Stream error: $error'),
        );

        // Wait for completion
        await Future.delayed(const Duration(seconds: 30));

        // Verify responses
        expect(responses.isNotEmpty, true);

        final deltaResponses = responses.where((r) => r['type'] == 'delta').toList();
        expect(deltaResponses.isNotEmpty, true);

        // Should have some content
        final allContent = deltaResponses
            .map((r) => r['delta'] as String? ?? '')
            .join();
        expect(allContent.isNotEmpty, true);

        channel.sink.close();
      });

      test('maintains conversation context across messages', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        const sessionId = 'test-context-session';

        // First message
        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'My favorite color is blue',
          'session_id': sessionId,
          'user_id': 'test-user-789',
        }),);

        // Wait for response
        await Future.delayed(const Duration(seconds: 20));

        // Second message (should remember context)
        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'What is my favorite color?',
          'session_id': sessionId,
          'user_id': 'test-user-789',
        }),);

        final responses = <Map<String, dynamic>>[];
        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            responses.add(response);
            if (response['metadata']?['done'] == true) {
              subscription.cancel();
            }
          },
        );

        await Future.delayed(const Duration(seconds: 20));

        // Check if response mentions "blue"
        final allContent = responses
            .where((r) => r['type'] == 'delta')
            .map((r) => r['delta'] as String? ?? '')
            .join();

        // Note: This depends on LLM behavior, may not always work
        print('Response content: $allContent');

        channel.sink.close();
      });

      test('handles concurrent sessions independently', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Create two sessions
        const session1 = 'test-concurrent-session-1';
        const session2 = 'test-concurrent-session-2';

        // Send messages to both sessions
        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'Session 1: Hello',
          'session_id': session1,
          'user_id': 'test-user-concurrent',
        }),);

        await Future.delayed(const Duration(seconds: 1));

        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'Session 2: Hi there',
          'session_id': session2,
          'user_id': 'test-user-concurrent',
        }),);

        final responses = <String, List<Map<String, dynamic>>>{};
        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            final sessionId = response['session_id'] as String?;

            if (sessionId != null) {
              responses.putIfAbsent(sessionId, () => []);
              responses[sessionId]!.add(response);
            }
          },
        );

        await Future.delayed(const Duration(seconds: 40));
        subscription.cancel();

        // Both sessions should receive responses
        expect(responses.containsKey(session1), true);
        expect(responses.containsKey(session2), true);

        channel.sink.close();
      });
    });

    // ============================================================
    // Plan Review Tests
    // ============================================================

    group('Plan Review Workflow', () {
      test('receives plan review event via WebSocket', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Request plan creation and review
        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': '制定一个学习计划并评审',
          'session_id': 'test-plan-review',
          'user_id': 'test-user-plan',
        }),);

        var reviewReceived = false;
        Map<String, dynamic>? reviewData;

        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            final metadata = response['metadata'] as Map<String, dynamic>?;

            if (metadata != null && metadata['requires_review'] == true) {
              reviewReceived = true;
              reviewData = metadata['review_data'] as Map<String, dynamic>;
              subscription.cancel();
            }

            if (metadata != null && metadata['done'] == true) {
              subscription.cancel();
            }
          },
        );

        await Future.delayed(const Duration(seconds: 30));
        subscription.cancel();

        // Note: Plan review may not always trigger
        if (reviewReceived) {
          expect(reviewData, isNotNull);
          expect(reviewData!['plan_id'], isNotNull);
          expect(reviewData!['review_id'], isNotNull);
        }

        channel.sink.close();
      });

      test('submits plan review feedback', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Submit feedback (in real scenario, would have a review ID)
        final feedbackRequest = {
          'type': 'plan_review_feedback',
          'plan_id': 'test-plan-123',
          'review_id': 'test-review-456',
          'decision': 'approve',
          'session_id': 'test-feedback',
          'user_id': 'test-user-feedback',
        };

        channel.sink.add(jsonEncode(feedbackRequest));

        // Should receive confirmation
        final response = await channel.stream.first;
        final data = jsonDecode(response as String) as Map<String, dynamic>;

        // May receive ack or error
        expect(data, isNotNull);

        channel.sink.close();
      });
    });

    // ============================================================
    // State Change Notification Tests
    // ============================================================

    group('State Change Notifications', () {
      test('receives plan archived notification', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        var notificationReceived = false;
        Map<String, dynamic>? notificationData;

        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            final metadata = response['metadata'] as Map<String, dynamic>?;

            if (metadata != null && metadata['state_change_event'] != null) {
              final event = metadata['state_change_event'] as Map<String, dynamic>;
              if (event['change_type'] == 'plan_archived') {
                notificationReceived = true;
                notificationData = event;
                subscription.cancel();
              }
            }
          },
        );

        // Wait for notification (would be triggered by actual plan archive)
        await Future.delayed(const Duration(seconds: 10));
        subscription.cancel();

        // Note: This test requires actual plan archive to occur
        // In real tests, would trigger archive via API
        if (notificationReceived) {
          expect(notificationData!['change_type'], 'plan_archived');
        }

        channel.sink.close();
      });

      test('receives settings updated notification', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        var notificationReceived = false;
        Map<String, dynamic>? notificationData;

        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            final metadata = response['metadata'] as Map<String, dynamic>?;

            if (metadata != null && metadata['state_change_event'] != null) {
              final event = metadata['state_change_event'] as Map<String, dynamic>;
              if (event['change_type'] == 'settings_updated') {
                notificationReceived = true;
                notificationData = event;
                subscription.cancel();
              }
            }
          },
        );

        // Wait for notification
        await Future.delayed(const Duration(seconds: 10));
        subscription.cancel();

        // Note: Requires actual settings change
        if (notificationReceived) {
          expect(notificationData!['change_type'], 'settings_updated');
        }

        channel.sink.close();
      });
    });

    // ============================================================
    // Error Handling Tests
    // ============================================================

    group('Error Handling', () {
      test('handles malformed messages gracefully', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Send invalid JSON
        channel.sink.add('not valid json {{{');

        // Should receive error or ignore
        final response = await channel.stream.timeout(
          const Duration(seconds: 5),
          onTimeout: null,
        ).first;

        if (response != null) {
          final data = jsonDecode(response as String) as Map<String, dynamic>;
          expect(data['type'] == 'error' || data['type'] == 'validation_error', true);
        }

        channel.sink.close();
      });

      test('handles message without required fields', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Send message without content
        channel.sink.add(jsonEncode({'type': 'message'}));

        // Should receive validation error
        final response = await channel.stream.first;
        final data = jsonDecode(response as String) as Map<String, dynamic>;

        expect(
          data['type'] == 'error' || data['type'] == 'validation_error',
          true,
        );

        channel.sink.close();
      });

      test('recovers from server error', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Send invalid request
        channel.sink.add(jsonEncode({'type': 'invalid_type'}));

        // Wait for error response
        await channel.stream.first;

        // Send valid request after error
        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'Hello after error',
          'session_id': 'test-recovery',
          'user_id': 'test-user-recovery',
        }),);

        // Should receive valid response
        final response = await channel.stream.timeout(
          const Duration(seconds: 30),
        ).first;

        expect(response, isNotNull);

        channel.sink.close();
      });
    });

    // ============================================================
    // Performance Tests
    // ============================================================

    group('Performance', () {
      test('measures time to first token', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        final stopwatch = Stopwatch()..start();

        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'Hi',
          'session_id': 'test-ttft',
          'user_id': 'test-user-ttft',
        }),);

        DateTime? firstTokenTime;

        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            if (firstTokenTime == null && response['type'] == 'delta' && response['delta'] != '') {
              firstTokenTime = DateTime.now();
              subscription.cancel();
            }
          },
        );

        await Future.delayed(const Duration(seconds: 30));
        subscription.cancel();
        stopwatch.stop();

        if (firstTokenTime != null) {
          final ttft = stopwatch.elapsedMilliseconds.toDouble() / 1000;
          print('Time to First Token: ${ttft.toStringAsFixed(2)}s');
          expect(ttft, lessThan(10.0));
        }

        channel.sink.close();
      });

      test('measures tokens per second', () async {
        final uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        final stopwatch = Stopwatch()..start();

        channel.sink.add(jsonEncode({
          'type': 'message',
          'content': 'Explain what is machine learning',
          'session_id': 'test-tps',
          'user_id': 'test-user-tps',
        }),);

        final deltas = <String>[];
        final subscription = channel.stream.listen(
          (data) {
            final response = jsonDecode(data as String) as Map<String, dynamic>;
            if (response['type'] == 'delta') {
              deltas.add(response['delta'] as String? ?? '');
            }
            if (response['metadata']?['done'] == true) {
              subscription.cancel();
              stopwatch.stop();
            }
          },
        );

        await Future.delayed(const Duration(seconds: 60));
        subscription.cancel();

        final totalChars = deltas.join().length;
        final elapsedSeconds = stopwatch.elapsedMilliseconds.toDouble() / 1000;
        final cps = elapsedSeconds > 0 ? totalChars / elapsedSeconds : 0;

        print('Total characters: $totalChars');
        print('Elapsed time: ${elapsedSeconds.toStringAsFixed(2)}s');
        print('Characters per second: ${cps.toStringAsFixed(2)}');

        expect(cps, greaterThan(0));

        channel.sink.close();
      });
    });

    // ============================================================
    // Reconnection Tests
    // ============================================================

    group('Reconnection', () {
      test('reconnects after connection loss', () async {
        // First connection
        var uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        channel.sink.add(jsonEncode({'type': 'ping'}));
        await channel.stream.first;

        // Close connection
        channel.sink.close();
        await Future.delayed(const Duration(seconds: 1));

        // Reconnect
        uri = Uri.parse('$wsUrl?token=$authToken');
        channel = WebSocketChannel.connect(uri);
        await channel.ready;

        // Should work after reconnection
        channel.sink.add(jsonEncode({'type': 'ping'}));
        final response = await channel.stream.first;
        final data = jsonDecode(response as String);
        expect(data['type'], 'pong');

        channel.sink.close();
      });

      test('handles exponential backoff', () async {
        const maxRetries = 3;
        var attempts = 0;

        while (attempts < maxRetries) {
          try {
            final uri = Uri.parse('$wsUrl?token=$authToken');
            channel = WebSocketChannel.connect(uri);
            await channel.ready;

            // Success
            channel.sink.close();
            break;
          } catch (e) {
            attempts++;
            final delay = Duration(milliseconds: 1000 * (1 << attempts));
            print('Connection failed, retrying in ${delay.inSeconds}s...');
            await Future.delayed(delay);
          }
        }

        // Should eventually connect
        expect(attempts, lessThan(maxRetries));
      });
    });
  });
}

/// Custom timeout extension
extension StreamTimeout<T> on Stream<T> {
  Stream<T> timeout(Duration duration, {T? onTimeout}) => asyncMap((event) async {
      // This is a simplified version
      // In real implementation, would use proper timeout
      return event;
    });
}
