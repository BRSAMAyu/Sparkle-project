// M6-R2-02 regression tests: core WebSocketService reconnect budget must
// survive the "handshake succeeds, server immediately closes" loop
// (gateway crash-loop / LB drain / hot reload all behave this way).
//
// Locks:
//   1. In an accept-then-close loop the backoff escalates step by step,
//      exactly [_maxReconnectAttempts] reconnects happen (initial + 6
//      total connects), and then the service gives up — the max-attempts
//      guard is reachable. The pre-fix implementation reset the budget on
//      every successful handshake, so every reconnect stayed at the first
//      step (800ms) forever.
//   2. A STABLE connection (uptime >= threshold) that drops refreshes the
//      budget: the next reconnect starts again from the first step.
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/websocket_service.dart';

List<String> _wsLogs = <String>[];

List<String> _scheduleLogs() => _wsLogs
    .where((log) => log.startsWith('Scheduling reconnect in'))
    .toList();

List<String> _connectingLogsFor(String url) => _wsLogs
    .where((log) => log.startsWith('Connecting to WebSocket') && (
          log.contains(url)
        ))
    .toList();

Duration _parseScheduleDelay(String log) {
  // The service logs `'Scheduling reconnect in ${delay}ms'` where [delay]
  // is a Duration: the value is Duration.toString() plus a literal "ms"
  // suffix (e.g. "0:00:00.050000ms" = 50ms).
  var value = log.replaceFirst('Scheduling reconnect in ', '').trim();
  if (value.endsWith('ms')) {
    value = value.substring(0, value.length - 2);
  }
  final duration =
      RegExp(r'^(\d+):(\d{2}):(\d{2})\.(\d{3})(\d{3})$').firstMatch(value);
  if (duration != null) {
    return Duration(
      hours: int.parse(duration.group(1)!),
      minutes: int.parse(duration.group(2)!),
      seconds: int.parse(duration.group(3)!),
      milliseconds: int.parse(duration.group(4)!),
      microseconds: int.parse(duration.group(5)!),
    );
  }
  if (value.endsWith('s')) {
    // Plain seconds like "1.6s".
    return Duration(
      milliseconds: (double.parse(value.replaceAll('s', '')) * 1000).round(),
    );
  }
  // Plain milliseconds like "800".
  return Duration(milliseconds: int.parse(value));
}

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

/// Server that accepts each WebSocket client and closes the socket
/// immediately after: the handshake succeeds, the connection does not
/// survive.
Future<HttpServer> _startAcceptAndCloseServer({
  Duration holdAfterUpgrade = const Duration(milliseconds: 20),
}) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    final client = await WebSocketTransformer.upgrade(request);
    unawaited(
      Future<void>.delayed(holdAfterUpgrade).then((_) {
        try {
          unawaited(client.close());
        } catch (_) {}
      }),
    );
  });
  return server;
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

  test(
      'accept-then-close loop escalates backoff and gives up after max '
      'attempts (short-lived sessions must not refresh the budget)',
      () async {
    final server = await _startAcceptAndCloseServer();
    addTearDown(server.close);
    final url = 'ws://127.0.0.1:${server.port}';

    // Tiny schedule so the whole budget (6 backoff steps) fits in ~4s.
    const schedule = <Duration>[
      Duration(milliseconds: 50),
      Duration(milliseconds: 100),
      Duration(milliseconds: 200),
      Duration(milliseconds: 400),
      Duration(milliseconds: 800),
      Duration(milliseconds: 1600),
    ];
    final service = WebSocketService(reconnectSchedule: schedule);
    addTearDown(service.disconnect);

    service.connect(url);

    // Wait until the final (6th) reconnect attempt happens.
    await _waitFor(
      const Duration(seconds: 10),
      () => _connectingLogsFor(url).length >= 7,
    );

    // Give the buggy implementation room to keep dialing: it never stops,
    // the fixed implementation must stay at exactly initial + 6.
    await Future<void>.delayed(const Duration(milliseconds: 2500));

    final connects = _connectingLogsFor(url);
    expect(
      connects.length,
      7,
      reason:
          'Expected initial connect + exactly 6 reconnects, then give up. '
          'Got ${connects.length} connects: $connects',
    );

    final delays = _scheduleLogs().map(_parseScheduleDelay).toList();
    expect(
      delays,
      schedule,
      reason:
          'Every reconnect must advance one step up the backoff schedule. '
          'Observed: $delays',
    );
    for (var i = 1; i < delays.length; i++) {
      expect(
        delays[i] > delays[i - 1],
        isTrue,
        reason: 'Backoff must be strictly increasing: $delays',
      );
    }

    // Attempt counter must walk 1..6 — never reset by the short-lived
    // successful handshakes.
    final attemptNumbers = connects
        .map((log) => int.parse(
              RegExp(r'\(Attempt: (\d+)\)').firstMatch(log)!.group(1)!,
            ))
        .toList();
    expect(
      attemptNumbers,
      <int>[0, 1, 2, 3, 4, 5, 6],
      reason: 'Attempts must escalate 0→6 without resets: $attemptNumbers',
    );
  });

  test(
      'a stable connection (uptime >= threshold) that drops refreshes the '
      'reconnect budget', () async {
    // Each "connection" is held open for 500ms — well past the 200ms
    // threshold — then closed: a genuinely established session that
    // drops. Every drop must hand out a fresh budget, so every reconnect
    // restarts from the first backoff step (Attempt: 1).
    final server = await _startAcceptAndCloseServer(
      holdAfterUpgrade: const Duration(milliseconds: 500),
    );
    addTearDown(server.close);
    final url = 'ws://127.0.0.1:${server.port}';

    final service = WebSocketService(
      reconnectSchedule: const [
        Duration(milliseconds: 50),
        Duration(milliseconds: 100),
        Duration(milliseconds: 200),
        Duration(milliseconds: 400),
        Duration(milliseconds: 800),
        Duration(milliseconds: 1600),
      ],
      stableConnectionThreshold: const Duration(milliseconds: 200),
    );
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
          'Every reconnect after an established (stable) connection must '
          'restart from the first backoff step, i.e. attempt counter == 1. '
          'Got: $reconnects',
    );
  });
}
