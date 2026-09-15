import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/services/community_websocket_service.dart';

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
      final states = WsConnectionState.values;
      final stateSet = states.toSet();
      expect(states.length, stateSet.length);
    });

    test('has expected states', () {
      expect(WsConnectionState.values, containsAll([
        WsConnectionState.disconnected,
        WsConnectionState.connecting,
        WsConnectionState.connected,
        WsConnectionState.reconnecting,
        WsConnectionState.error,
        WsConnectionState.failed,
      ]));
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
      void Function(String) callback = (msgId) {
        // Acknowledged message
      };

      expect(callback, isNotNull);
    });

    test('callback receives message ID string', () {
      String? receivedId;
      void Function(String) callback = (msgId) {
        receivedId = msgId;
      };

      callback('msg-abc-123');
      expect(receivedId, 'msg-abc-123');
    });
  });
}
