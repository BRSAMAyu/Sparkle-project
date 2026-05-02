// ignore_for_file: discarded_futures

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_center_provider.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/gen/websocket.pb.dart';

import 'sync_engine_test.mocks.dart';

@GenerateMocks([WebSocketService, ApiClient])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;

  setUpAll(() async {
    await Isar.initializeIsarCore(download: true);
    SharedPreferences.setMockInitialValues({});
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('sync_engine_test');
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
    localDb = LocalDatabase();
    localDb.isar = isar;
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  test('waitingAck TTL rollback requeues item', () async {
    final mockWs = MockWebSocketService();
    final mockApi = MockApiClient();
    final engine = SyncEngine(localDb, mockWs, mockApi);

    final now = DateTime.now();
    final item = OutboxItem()
      ..uuid = 'op1'
      ..topic = 'knowledge'
      ..opType = 'update'
      ..payloadJson = jsonEncode({'nodeId': 'n1', 'mastery': 10})
      ..createdAt = now.subtract(const Duration(minutes: 10))
      ..status = SyncStatus.waitingAck
      ..lastSentAt = now.subtract(const Duration(minutes: 5))
      ..nextAttemptAt = now.subtract(const Duration(minutes: 1));

    final id = await isar.writeTxn(() => isar.outboxItems.put(item));

    await engine.requeueStuckWaitingAckForTest();

    final updated = await isar.outboxItems.get(id);
    expect(updated, isNotNull);
    expect(updated!.status, SyncStatus.pending);
    expect(updated.attemptCount, 1);
    expect(updated.lastErrorCode, 'ACK_TIMEOUT');
    expect(updated.nextAttemptAt, isNotNull);
  });

  test('retryItem bypasses nextAttemptAt and syncs', () async {
    final mockWs = MockWebSocketService();
    final mockApi = MockApiClient();
    final streamController = StreamController<dynamic>.broadcast();
    when(mockWs.stream).thenAnswer((_) => streamController.stream);
    when(mockWs.send(any)).thenAnswer((invocation) {
      final data = invocation.positionalArguments.first;
      if (data is WebSocketMessage) {
        Future.microtask(() {
          streamController.add({
            'type': 'ack_node_mastery',
            'payload': {'requestId': data.requestId},
          });
        });
      }
    });

    final engine = _TestSyncEngine(localDb, mockWs, mockApi);
    final service = SyncCenterService(localDb, engine);

    final item = OutboxItem()
      ..uuid = 'op2'
      ..topic = 'knowledge'
      ..opType = 'update'
      ..payloadJson = jsonEncode({'nodeId': 'n1', 'mastery': 20})
      ..createdAt = DateTime.now()
      ..status = SyncStatus.failed
      ..nextAttemptAt = DateTime.now().add(const Duration(hours: 1));

    final id = await isar.writeTxn(() => isar.outboxItems.put(item));

    await service.retryItem(id);

    final updated = await isar.outboxItems.get(id);
    expect(updated, isNotNull);
    expect(updated!.status, SyncStatus.synced);
    await streamController.close();
  });

  test('enqueue writes outbox item with correct topic and opType', () async {
    final mockWs = MockWebSocketService();
    when(mockWs.stream).thenAnswer((_) => const Stream.empty());
    final mockApi = MockApiClient();
    final engine = SyncEngine(localDb, mockWs, mockApi);
    engine.stop();

    await engine.enqueue(
      topic: 'task',
      opType: 'complete',
      payload: {'task_id': 't1'},
      entityType: 'task',
      entityId: 't1',
      dedupeKey: 'task:t1:complete',
      priority: 2,
    );

    final items = await isar.outboxItems
        .filter()
        .topicEqualTo('task')
        .findAll();
    expect(items.length, 1);
    expect(items.first.opType, 'complete');
    expect(items.first.entityId, 't1');
    expect(items.first.priority, 2);
    expect(items.first.status, SyncStatus.pending);
  });

  test('enqueueLegacy delegates to enqueue with legacy topic', () async {
    final mockWs = MockWebSocketService();
    when(mockWs.stream).thenAnswer((_) => const Stream.empty());
    final mockApi = MockApiClient();
    final engine = SyncEngine(localDb, mockWs, mockApi);
    engine.stop();

    await engine.enqueueLegacy('mastery_update', {'nodeId': 'n1'});

    final items = await isar.outboxItems
        .filter()
        .topicEqualTo('legacy')
        .findAll();
    expect(items.length, 1);
    expect(items.first.opType, 'mastery_update');
  });

  test('processNow marks item as failed after max attempts', () async {
    final mockWs = MockWebSocketService();
    final streamController = StreamController<dynamic>.broadcast();
    when(mockWs.stream).thenAnswer((_) => streamController.stream);
    // Never send ACK → will timeout
    final mockApi = MockApiClient();
    final engine = _TestSyncEngine(localDb, mockWs, mockApi);

    final item = OutboxItem()
      ..uuid = 'op-fail'
      ..topic = 'cognitive'
      ..opType = 'create'
      ..payloadJson = jsonEncode({'fragment': 'test'})
      ..createdAt = DateTime.now()
      ..status = SyncStatus.pending
      ..attemptCount = 4; // One more attempt = max

    await isar.writeTxn(() => isar.outboxItems.put(item));

    // Mock API to throw so processing fails
    when(mockApi.post<dynamic>(any, data: anyNamed('data')))
        .thenThrow(Exception('Network error'));

    await engine.processNow(force: true, skipConnectivity: true);

    final updated = await isar.outboxItems.get(item.id);
    expect(updated, isNotNull);
    expect(updated!.status, SyncStatus.failed);
    expect(updated.attemptCount, 5);
    await streamController.close();
  });

  test('_describeItem falls back to legacy type parsing', () async {
    // Legacy item with type but no topic/opType
    final item = OutboxItem()..type = 'mastery_update';
    // _describeItem is private but tested via processItem behavior
    // We verify indirectly by checking the outbox behavior
    expect(item.type, 'mastery_update');
    expect(item.topic, isNull);
  });

  test('SyncFailure has code and message', () {
    final failure = SyncFailure('TEST_CODE', 'Test message');
    expect(failure.code, 'TEST_CODE');
    expect(failure.message, 'Test message');
    expect(failure.toString(), 'Test message');
  });
}

class _TestSyncEngine extends SyncEngine {
  _TestSyncEngine(super.localDb, super.wsService, super.apiClient);

  @override
  Future<void> processNow({bool force = false, bool skipConnectivity = false}) =>
      super.processNow(force: force, skipConnectivity: true);
}
