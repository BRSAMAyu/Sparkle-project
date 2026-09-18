// M6-02 regression tests: core WebSocketService reconnection scheduler.
//
// Locks two invariants:
//   1. A single failed connect must schedule exactly ONE reconnect timer
//      (onError + onDone must not stack timers on top of each other), and
//      the failed handshake must not leak an unhandled `ready` error.
//   2. A successfully established connection resets the reconnect budget,
//      so silent connections never keep the budget exhausted. Consequence:
//      3 consecutive drops of silent connections still trigger a 4th
//      reconnect from the FIRST backoff step.
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/websocket_service.dart';

List<String> _wsLogs = <String>[];

List<String> _connectingLogsFor(String url) => _wsLogs
    .where((log) => log.startsWith('Connecting to WebSocket') && (
          log.contains(url)
        ))
    .toList();

Future<void> _waitFor(
  Duration max,
  bool Function() condition, {
  Duration step = const Duration(milliseconds: 25),
}) async {
  final deadline = DateTime.now().add(max);
  while (!condition()) {
    if (DateTime.now().isAfter(deadline)) {
      fail('Condition not met within ${max.inMilliseconds}ms');
    }
    await Future<void>.delayed(step);
  }
}

void _captureDebugPrints() {
  debugPrint = (String? message, {int? wrapWidth}) {
    if (message != null) {
      _wsLogs.add(message);
    }
  };
}

class _WsServer {
  _WsServer(this._httpServer, this.accepted);

  final HttpServer _httpServer;
  final List<WebSocket> accepted;

  int get port => _httpServer.port;

  Future<void> close() => _httpServer.close(force: true);
}

Future<_WsServer> _startServer(void Function(WebSocket client)? onClient) async {
  final accepted = <WebSocket>[];
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    final client = await WebSocketTransformer.upgrade(request);
    accepted.add(client);
    onClient?.call(client);
  });
  return _WsServer(server, accepted);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    _wsLogs = <String>[];
    _captureDebugPrints();
  });

  tearDown(() {
    debugPrint = debugPrintThrottled;
  });

  group('WebSocketService reconnection', () {
    test(
        'a single failed connect schedules exactly one reconnect timer and '
        'does not leak an unhandled handshake error', () async {
      // Reserve an ephemeral port, then release it: nothing is listening and
      // every connect attempt fails immediately.
      final temp = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
      final deadPort = temp.port;
      await temp.close();
      final url = 'ws://127.0.0.1:$deadPort';

      final strayErrors = <Object>[];
      final service = WebSocketService();
      addTearDown(service.disconnect);

      await runZonedGuarded(() async {
        service.connect(url);

        // First backoff step is 800ms. Sample right after the reconnect
        // wave but before the *next* scheduled attempt (+1200ms on the
        // fixed service) can fire. A double-scheduled service burns the
        // budget twice per drop, so two reconnects appear in the window.
        await Future<void>.delayed(const Duration(milliseconds: 1500));
      }, (error, stackTrace) {
        strayErrors.add(error);
      });
      service.disconnect();
      await Future<void>.delayed(Duration.zero);

      final connects = _connectingLogsFor(url);
      expect(
        connects.length,
        2,
        reason:
            'Expected exactly one initial connect plus exactly one reconnect, '
            'got: $connects',
      );
      expect(connects.last, contains('(Attempt: 1)'));
      expect(
        strayErrors,
        isEmpty,
        reason: 'Failed handshakes must be consumed, not leaked into the '
            'zone: $strayErrors',
      );
    });

    test(
        'three consecutive drops of silent connections still trigger a 4th '
        'reconnect from the first backoff step (budget resets on connect)',
        () async {
      // Server accepts each client, stays completely silent (no messages:
      // the sync engine's steady state), then closes cleanly.
      final accepted = <WebSocket>[];
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      addTearDown(server.close);
      server.listen((request) async {
        final client = await WebSocketTransformer.upgrade(request);
        accepted.add(client);
        unawaited(
          Future<void>.delayed(const Duration(milliseconds: 120)).then((_) {
            try {
              unawaited(client.close());
            } catch (_) {}
          }),
        );
      });
      final url = 'ws://127.0.0.1:${server.port}';

      final service = WebSocketService();
      addTearDown(service.disconnect);

      service.connect(url);

      // Wait for the 4th connection attempt (initial + 3 reconnects).
      await _waitFor(
        const Duration(seconds: 10),
        () => _connectingLogsFor(url).length >= 4,
      );
      service.disconnect();
      await Future<void>.delayed(Duration.zero);

      final reconnects = _connectingLogsFor(url).sublist(1);
      expect(
        reconnects,
        everyElement(contains('(Attempt: 1)')),
        reason:
            'Every reconnect after an established (silent) connection must '
            'restart from the first backoff step, i.e. attempt counter == 1. '
            'Got: $reconnects',
      );
    });

    test('drops unparseable binary frames instead of broadcasting raw bytes',
        () async {
      final events = <dynamic>[];
      final server = await _startServer((client) {
        // Bytes that are not a valid WebSocketMessage protobuf frame
        // (leading 0x00 is an invalid protobuf tag).
        client.add(<int>[0x00, 0xFF, 0x13, 0x37, 0xDE, 0xAD]);
        // A valid JSON text frame must still be delivered.
        client.add('{"type":"pong"}');
      });
      final service = WebSocketService();
      addTearDown(service.disconnect);
      final subscription = service.stream.listen(events.add);
      addTearDown(subscription.cancel);

      service.connect('ws://127.0.0.1:${server.port}');
      await _waitFor(
        const Duration(seconds: 3),
        () => events.any((event) => event is Map),
      );
      await Future<void>.delayed(const Duration(milliseconds: 300));
      service.disconnect();
      await Future<void>.delayed(Duration.zero);

      final rawBinary = events.whereType<List<int>>().toList();
      expect(
        rawBinary,
        isEmpty,
        reason: 'Unparseable binary must be dropped, not broadcast raw to '
            'consumers that cannot handle arbitrary bytes: $rawBinary',
      );
      expect(
        events.whereType<Map<String, dynamic>>().map((m) => m['type']),
        contains('pong'),
        reason: 'The JSON text path must keep working',
      );
    });
  });
}
