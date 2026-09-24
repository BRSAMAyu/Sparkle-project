// M6-05 / M6-R2-01 regression tests: WebSocketChatServiceV2 must gate the
// `connected` state (and the reconnect-budget reset) on the actual
// WebSocket handshake, and must consume `channel.ready` failures instead
// of leaking them as unhandled async errors.
//
// Locks:
//   1. Until the channel's `ready` future completes, the connection state
//      must not be `connected` (UI must not flash "online" and messages
//      must not take the direct-send path).
//   2. A failed handshake is routed through `_handleConnectionError`:
//      the reconnect budget increments and a reconnect is scheduled; the
//      ready error is consumed (no unhandled async exception).
//   3. Under a persistent accept-then-close server, the backoff escalates
//      step by step, the attempt budget reaches the max, and the
//      `failed` / MESSAGES_LOST terminal state becomes reachable (the
//      pre-fix implementation reset the budget right after `connect()`,
//      so every cycle restarted at step one and the terminal state was
//      unreachable).
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class _MockWebSocketSink implements WebSocketSink {
  final List<dynamic> sentData = <dynamic>[];

  @override
  void add(dynamic data) {
    sentData.add(data);
  }

  @override
  void addError(Object error, [StackTrace? stackTrace]) {}

  @override
  Future<void> addStream(Stream<dynamic> stream) async {
    await stream.forEach(add);
  }

  @override
  Future<void> close([int? closeCode, String? closeReason]) async {}

  @override
  Future<void> get done => Future<void>.value();
}

/// Channel whose `ready` future is controlled by the test.
class _GateChannel with StreamChannelMixin<dynamic> implements WebSocketChannel {
  final Completer<void> readyCompleter = Completer<void>();
  final StreamController<dynamic> incoming = StreamController<dynamic>();
  final _MockWebSocketSink _sink = _MockWebSocketSink();

  @override
  Stream<dynamic> get stream => incoming.stream;

  @override
  WebSocketSink get sink => _sink;

  @override
  String? get protocol => null;

  @override
  int? get closeCode => null;

  @override
  String? get closeReason => null;

  @override
  Future<void> get ready => readyCompleter.future;

  void completeHandshake() {
    if (!readyCompleter.isCompleted) {
      readyCompleter.complete();
    }
  }

  void failHandshake(Object error) {
    // Attach an in-test consumer so the error is never unhandled even if
    // the service (pre-fix) never listens on `ready`.
    unawaited(readyCompleter.future.catchError((Object _) {}));
    readyCompleter.completeError(error);
  }

  /// Simulate the server dropping the connection right after the
  /// handshake: stream completes → onDone fires.
  Future<void> closeImmediately() async {
    await incoming.close();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late List<_GateChannel> channels;
  late WebSocketChatServiceV2 service;
  late ProviderContainer container;
  final logs = <String>[];

  setUp(() {
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null) {
        logs.add(message);
      }
    };
    // Logs must not leak across tests: the reconnect-log assertions below
    // count and parse them per test.
    logs.clear();
    channels = <_GateChannel>[];
    container = ProviderContainer();
    service = WebSocketChatServiceV2(
      container: container,
      channelFactory: (uri, {headers}) {
        final channel = _GateChannel();
        channels.add(channel);
        return channel;
      },
      autoConnect: false,
    );
  });

  tearDown(() {
    service.dispose();
    container.dispose();
    debugPrint = debugPrintThrottled;
  });

  Future<void> waitFor(Duration max, bool Function() condition) async {
    final deadline = DateTime.now().add(max);
    while (!condition()) {
      if (DateTime.now().isAfter(deadline)) {
        fail('Condition not met within ${max.inMilliseconds}ms');
      }
      await Future<void>.delayed(const Duration(milliseconds: 25));
    }
  }

  test(
      'state stays connecting until the channel ready future completes '
      '(no premature connected flash)', () async {
    await service.ensureConnected(userId: 'u1');

    expect(
      channels,
      hasLength(1),
      reason: 'Exactly one channel should have been created',
    );
    expect(
      service.connectionState,
      WsConnectionState.connecting,
      reason:
          'The handshake has not completed (ready pending): reporting '
          '`connected` before the channel is ready flashes online status '
          'and lets sendMessage take the direct-send path (M6-05).',
    );
    expect(service.isConnected, isFalse);

    channels.first.completeHandshake();
    await Future<void>.delayed(Duration.zero);

    expect(service.connectionState, WsConnectionState.connected);
    expect(service.isConnected, isTrue);
  });

  test(
      'failed handshake (ready error) is consumed and triggers a reconnect '
      'with an incremented attempt budget', () async {
    await service.ensureConnected(userId: 'u1');
    expect(channels, hasLength(1));

    // Handshake rejected (connection refused / 502 …).
    channels.first.failHandshake(const SocketException('handshake refused'));

    // Reconnect is scheduled at the first backoff step (800ms + jitter).
    // Assert while the timer is still pending: once it fires the service
    // legitimately flips back to `connecting` for the new dial.
    await waitFor(
      const Duration(seconds: 4),
      () => logs.any((log) => log.contains('Reconnecting in')),
    );

    expect(
      service.reconnectAttempts,
      greaterThanOrEqualTo(1),
      reason:
          'The reconnect budget must increment on handshake failure '
          '(observed: ${service.reconnectAttempts})',
    );
    expect(
      service.connectionState,
      WsConnectionState.reconnecting,
      reason: 'State must reflect the reconnect-in-progress reality while '
          'the reconnect timer is pending',
    );

    // The scheduled reconnect must actually dial again.
    await waitFor(
      const Duration(seconds: 4),
      () => channels.length >= 2,
    );
    expect(
      channels.length,
      greaterThanOrEqualTo(2),
      reason:
          'A failed handshake must schedule a reconnect and open a new '
          'channel. Channels created: ${channels.length}; '
          'state: ${service.connectionState}',
    );
  });

  test(
      'persistent accept-then-close escalates backoff and reaches the '
      'failed terminal state with the pending MESSAGES_LOST path', () async {
    final events = <dynamic>[];

    // Accept-then-close loop: every handshake succeeds (ready completes),
    // every connection dies immediately. Rebuild the service with a tiny
    // backoff table so the whole budget fits in ~2s — the setUp-built
    // service uses the production schedule (800ms→12.2s), under which the
    // terminal state would take ~30s to reach. The rebuild happens BEFORE
    // the tracked sendMessage so the terminal broadcast reaches a request
    // controller registered on THIS service.
    const schedule = <int>[10, 40, 100, 200, 400, 800];
    service.dispose();
    service = WebSocketChatServiceV2(
      container: container,
      channelFactory: (uri, {headers}) {
        final channel = _GateChannel();
        channels.add(channel);
        return channel;
      },
      autoConnect: false,
      reconnectSchedule: const [
        Duration(milliseconds: 10),
        Duration(milliseconds: 40),
        Duration(milliseconds: 100),
        Duration(milliseconds: 200),
        Duration(milliseconds: 400),
        Duration(milliseconds: 800),
      ],
    );
    final requestStream = service.sendMessage(
      message: 'tracked request',
      userId: 'u1',
    );
    final requestSub =
        requestStream.listen(events.add, onError: (Object _) {});

    await service.ensureConnected(userId: 'u1');

    // Drive every channel the service opens: complete its handshake, then
    // drop the connection — an accept-then-close server.
    final driver = Timer.periodic(const Duration(milliseconds: 20), (timer) {
      if (service.connectionState == WsConnectionState.failed) {
        timer.cancel();
        return;
      }
      for (final channel in channels) {
        if (!channel.readyCompleter.isCompleted) {
          channel.completeHandshake();
          unawaited(channel.closeImmediately());
        }
      }
    });

    await waitFor(
      const Duration(seconds: 15),
      () => service.connectionState == WsConnectionState.failed,
    );
    driver.cancel();

    expect(
      service.connectionState,
      WsConnectionState.failed,
      reason:
          'The failed terminal state must be reachable under a persistent '
          'accept-then-close server',
    );
    expect(
      service.reconnectAttempts,
      6,
      reason:
          'The attempt budget must climb to the max instead of being reset '
          'after every handshake (observed: ${service.reconnectAttempts})',
    );
    expect(
      channels.length,
      7,
      reason:
          'Initial connect + exactly 6 reconnects — no budget refresh means '
          'no extra dials (observed: ${channels.length})',
    );
    // The terminal branch must have run: `failed` is only set inside the
    // max-attempts guard, and the pending message must have been failed
    // with the MESSAGES_LOST path (Discarding log) at that point.
    expect(
      logs.any((log) => log.contains('Max reconnect attempts reached')),
      isTrue,
      reason: 'The max-attempts guard (failed terminal branch) must execute',
    );
    expect(
      logs.any((log) => log.contains('Discarding 1 pending messages')),
      isTrue,
      reason:
          'The pending message must go through the MESSAGES_LOST path when '
          'the reconnect budget is exhausted',
    );
    // The active request stream receives a terminal broadcast on the first
    // drop (CONNECTION_CLOSED); `_broadcastErrorToActiveRequests` closes the
    // controller after broadcasting, so later broadcasts (MESSAGES_LOST /
    // MAX_RETRIES_EXCEEDED) target an empty controller map by design — the
    // pending message learns its fate via the offline queue instead.
    expect(
      events.map((e) => e.code as String),
      contains('CONNECTION_CLOSED'),
      reason:
          'The request stream must be terminated with a broadcast; got: '
          '${events.map((e) => e.code as String).toList()}',
    );

    // Every reconnect log line must match its own schedule step window
    // (base + <250ms jitter): proves the schedule truly advanced per
    // attempt instead of staying at step one.
    final reconnectLogs =
        logs.where((log) => log.contains('Reconnecting in')).toList();
    expect(reconnectLogs, hasLength(6));
    for (final log in reconnectLogs) {
      final match =
          RegExp(r'Reconnecting in (\d+)ms \(attempt (\d)/').firstMatch(log)!;
      final delayMs = int.parse(match.group(1)!);
      final attempt = int.parse(match.group(2)!);
      final base = schedule[attempt - 1];
      expect(
        delayMs,
        allBetween(base, base + 250),
        reason:
            'Attempt $attempt must be scheduled inside its own (escalated) '
            'backoff window [$base, ${base + 250}) — log: $log',
      );
    }

    await requestSub.cancel();
  });
}

Matcher allBetween(int lo, int hi) => predicate<int>(
      (v) => v >= lo && v < hi,
      'in [$lo, $hi)',
    );
