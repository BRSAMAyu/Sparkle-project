import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import '../../shared/isar_test_helper.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';

import '../../unit/sync_engine_test.mocks.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  setUp(() async {
    tempDir =
        await Directory.systemTemp.createTemp('sync_engine_crdt_ack_test');
    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
      ],
      directory: tempDir.path,
    );
    localDb = LocalDatabase()..isar = isar;
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  test('crdt delta waits for ACK and is deleted from outbox', () async {
    final mockWs = MockWebSocketService();
    final mockApi = MockApiClient();
    final streamController = StreamController<dynamic>.broadcast();
    when(mockWs.stream).thenAnswer((_) => streamController.stream);
    when(mockWs.send(any)).thenAnswer((invocation) {
      final data = invocation.positionalArguments.first;
      if (data is Map) {
        final requestId = data['request_id'] as String;
        unawaited(
          Future.microtask(
            () {
              streamController.add({
                'type': 'ack_crdt_update',
                'payload': {'requestId': requestId},
              });
            },
          ),
        );
      }
    });

    final engine = _TestSyncEngine(localDb, mockWs, mockApi);
    final item = OutboxItem()
      ..uuid = 'crdt-op-1'
      ..topic = 'crdt'
      ..opType = 'delta'
      ..payloadJson = jsonEncode({
        'protocol': 'sparkle-crdt-v1',
        'galaxyId': 'default',
        'operations': <Map<String, dynamic>>[],
      })
      ..createdAt = DateTime.now()
      ..status = SyncStatus.pending;

    final id = await isar.writeTxn(() => isar.outboxItems.put(item));

    await engine.processNow(force: true);

    expect(await isar.outboxItems.get(id), isNull);
    verify(
      mockWs.send(
        argThat(
          isA<Map<dynamic, dynamic>>()
              .having((data) => data['type'], 'type', 'crdt_update'),
        ),
      ),
    ).called(1);

    await streamController.close();
  });
}

class _TestSyncEngine extends SyncEngine {
  _TestSyncEngine(
    super.localDb,
    super.wsService,
    super.apiClient,
  );

  @override
  Future<void> processNow({
    bool force = false,
    bool skipConnectivity = false,
  }) =>
      super.processNow(force: force, skipConnectivity: true);
}
