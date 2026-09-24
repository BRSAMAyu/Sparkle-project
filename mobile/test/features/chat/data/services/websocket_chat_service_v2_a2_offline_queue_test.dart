// A-2 regression tests: the guest offline chat queue must replay frames the
// gateway can parse, and a server `message_nack` must move a queued/sending
// message to the failed state (with retry) instead of leaving it stuck.
//
// Field evidence (android-round1.md A-2, gateway.log 19:53:57):
//   chat_orchestrator.go:521 Failed to parse chat message: json: cannot
//   unmarshal string into Go struct field chatInput.extra_context of type
//   map[string]interface {}
// The client used `Map.toString()` when persisting extra_context, so every
// replayed frame was invalid and was permanently NACKed while the UI stayed
// on "Sending" forever.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/offline_message_queue_service.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../../shared/isar_test_helper.dart';

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

class _ReplayChannel
    with StreamChannelMixin<dynamic>
    implements WebSocketChannel {
  final Completer<void> readyCompleter = Completer<void>();
  final StreamController<dynamic> incoming = StreamController<dynamic>();
  final _MockWebSocketSink _sink = _MockWebSocketSink();

  @override
  WebSocketSink get sink => _sink;

  @override
  Stream<dynamic> get stream => incoming.stream;

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
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late OfflineMessageQueueService queue;
  late ProviderContainer container;
  late List<_ReplayChannel> channels;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('a2_offline_queue_test');
    isar = await Isar.open(
      [OfflineChatMessageSchema],
      directory: tempDir.path,
      name: 'a2_${DateTime.now().microsecondsSinceEpoch}',
    );
    localDb = LocalDatabase()..isar = isar;
    queue = OfflineMessageQueueService(localDb);
    channels = <_ReplayChannel>[];
    container = ProviderContainer(
      overrides: [localDatabaseProvider.overrideWithValue(localDb)],
    );
  });

  tearDown(() async {
    container.dispose();
    try {
      await isar.close(deleteFromDisk: true);
    } catch (_) {}
    try {
      await tempDir.delete(recursive: true);
    } catch (_) {}
  });

  WebSocketChatServiceV2 buildService() => WebSocketChatServiceV2(
        container: container,
        channelFactory: (uri, {headers}) {
          final channel = _ReplayChannel();
          channels.add(channel);
          return channel;
        },
        enableReconnect: false,
        autoConnect: false,
      );

  Future<void> waitFor(Duration max, FutureOr<bool> Function() condition) async {
    final deadline = DateTime.now().add(max);
    while (!await condition()) {
      if (DateTime.now().isAfter(deadline)) {
        fail('Condition not met within ${max.inMilliseconds}ms');
      }
      await Future<void>.delayed(const Duration(milliseconds: 20));
    }
  }

  Map<String, dynamic>? lastChatFrame(_ReplayChannel channel) {
    final sink = channel.sink as _MockWebSocketSink;
    for (final raw in sink.sentData.reversed) {
      if (raw is String && raw.contains('"request_id"')) {
        return json.decode(raw) as Map<String, dynamic>;
      }
    }
    return null;
  }

  Future<OfflineChatMessage?> findRow(String message) =>
      isar.offlineChatMessages.filter().messageEqualTo(message).findFirst();

  test(
      'replayed queued message carries extra_context as a Map, not a '
      'stringified Dart literal (gateway unmarshal contract)', () async {
    final sender = buildService();
    // Establish identity first (as the app does), but leave the handshake
    // pending so sendMessage takes the offline-queue path.
    await sender.ensureConnected(userId: 'u1');
    sender.sendMessage(
      message: 'hello from guest',
      userId: 'u1',
      extraContext: const {'source': 'galaxy', 'node_id': 'n1'},
    );
    sender.dispose();

    OfflineChatMessage? row;
    await waitFor(const Duration(seconds: 2), () async {
      row = await findRow('hello from guest');
      return row != null;
    });
    // The persisted extra_context must be valid JSON — exactly what the
    // gateway unmarshals back into map[string]interface{}.
    expect(
      () => json.decode(row!.extraContext!),
      returnsNormally,
      reason:
          'offline row extra_context must be real JSON; got: '
          '${row!.extraContext}',
    );

    // Simulate the process-restart replay path: a brand-new service instance
    // restores the row from Isar and flushes it once the socket is ready.
    final replayer = buildService();
    await replayer.ensureConnected(userId: 'u1');
    channels.last.completeHandshake();

    await waitFor(
      const Duration(seconds: 3),
      () async => lastChatFrame(channels.last) != null,
    );
    final frame = lastChatFrame(channels.last)!;
    expect(frame['message'], 'hello from guest');
    expect(
      frame['extra_context'],
      const {'source': 'galaxy', 'node_id': 'n1'},
      reason:
          'Replayed extra_context must be a Map (gateway contract is '
          'map[string]interface{}); a string here is permanently NACKed. '
          'Got: ${frame['extra_context']} '
          '(${frame['extra_context'].runtimeType})',
    );
    replayer.dispose();
  });

  test(
      'legacy Dart-literal extra_context rows are healed on replay: the '
      'frame goes out without extra_context instead of being NACKed',
      () async {
    // Seed a row exactly the way the pre-fix client did (Map.toString()).
    await queue.enqueue(
      requestId: 'req_legacy_poison',
      sessionId: 'session_legacy',
      message: 'legacy poisoned message',
      userId: 'u1',
      extraContext: '{source: legacy, depth: 2}', // Not valid JSON.
    );

    final replayer = buildService();
    await replayer.ensureConnected(userId: 'u1');
    channels.last.completeHandshake();

    await waitFor(
      const Duration(seconds: 3),
      () async => lastChatFrame(channels.last) != null,
    );
    final frame = lastChatFrame(channels.last)!;
    expect(frame['message'], 'legacy poisoned message');
    expect(
      frame.containsKey('extra_context'),
      isFalse,
      reason:
          'An undecodable legacy extra_context must be dropped rather than '
          're-sent as a string (the gateway NACKs such frames permanently '
          '— android-round1.md A-2). Frame: $frame',
    );
    replayer.dispose();
  });

  test('message_nack marks the offline row failed so the bubble can retry',
      () async {
    final service = buildService();
    await service.ensureConnected(userId: 'u1');
    channels.last.completeHandshake();
    await waitFor(
      const Duration(seconds: 2),
      () async => service.connectionState == WsConnectionState.connected,
    );

    final events = <ChatStreamEvent>[];
    final requestStream = service.sendMessage(
      message: 'doomed message',
      userId: 'u1',
      extraContext: const {'k': 'v'},
    );
    final subscription = requestStream.listen(events.add);

    Map<String, dynamic>? sentFrame;
    await waitFor(const Duration(seconds: 3), () async {
      sentFrame = lastChatFrame(channels.last);
      return sentFrame != null;
    });
    final requestId = sentFrame!['request_id'] as String;
    await waitFor(const Duration(seconds: 2), () async {
      final row = await findRow('doomed message');
      return row != null && row.requestId == requestId;
    });

    // Gateway rejects the frame permanently.
    channels.last.incoming.add(json.encode(<String, dynamic>{
      'type': 'message_nack',
      'message_id': requestId,
      'error_code': 'permanent_failure',
      'error_message': 'bad frame',
      'permanent': true,
    }),);

    await waitFor(
      const Duration(seconds: 3),
      () async => events.any((e) => e is NackEvent),
    );
    expect(
      events.whereType<NackEvent>().first.errorCode,
      'permanent_failure',
      reason: 'The request stream must observe the NACK (live-stream path)',
    );

    // The offline row must leave the sent/queued state (new behavior).
    OfflineChatMessage? failedRow;
    await waitFor(const Duration(seconds: 3), () async {
      final row = await findRow('doomed message');
      if (row == null || row.requestId != requestId) {
        return false;
      }
      failedRow = row;
      return row.status == OfflineMessageStatus.failed;
    });
    expect(
      failedRow!.status,
      OfflineMessageStatus.failed,
      reason:
          'message_nack must markFailed the offline row; status stayed '
          '${failedRow!.status} so the bubble would stay Sending forever',
    );
    expect(failedRow!.lastError, 'bad frame');
    expect(failedRow!.canRetry, isTrue);

    await subscription.cancel();
    service.dispose();
  });
}
