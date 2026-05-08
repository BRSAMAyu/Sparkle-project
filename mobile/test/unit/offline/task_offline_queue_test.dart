// ignore_for_file: discarded_futures

import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import '../../shared/isar_test_helper.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/features/task/data/services/task_offline_queue.dart';

import 'task_offline_queue_test.mocks.dart';

@GenerateMocks([WebSocketService, ApiClient, SyncEngine])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late MockSyncEngine mockEngine;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('task_queue_test');
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
    mockEngine = MockSyncEngine();
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  test('enqueueStart enqueues task:start with correct payload', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    await queue.enqueueStart('task-1', traceId: 'trace-1');

    verify(mockEngine.enqueue(
      topic: 'task',
      opType: 'start',
      payload: argThat(
        allOf([
          containsPair('task_id', 'task-1'),
        ]),
        named: 'payload',
      ),
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:start',
      priority: 1,
      traceId: 'trace-1',
    )).called(1);
  });

  test('enqueuePause includes reason when provided', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    await queue.enqueuePause('task-1', reason: 'manual', traceId: 'trace-2');

    verify(mockEngine.enqueue(
      topic: 'task',
      opType: 'pause',
      payload: argThat(
        allOf([
          containsPair('task_id', 'task-1'),
          containsPair('reason', 'manual'),
        ]),
        named: 'payload',
      ),
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:pause',
      priority: 1,
      traceId: 'trace-2',
    )).called(1);
  });

  test('enqueueResume enqueues task:resume', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    await queue.enqueueResume('task-1');

    verify(mockEngine.enqueue(
      topic: 'task',
      opType: 'resume',
      payload: argThat(
        containsPair('task_id', 'task-1'),
        named: 'payload',
      ),
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:resume',
      priority: 1,
      traceId: anyNamed('traceId'),
    )).called(1);
  });

  test('enqueueComplete includes completion data at priority 2', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    final completion = {'score': 95, 'note': 'Great work'};
    await queue.enqueueComplete('task-1', completion: completion);

    verify(mockEngine.enqueue(
      topic: 'task',
      opType: 'complete',
      payload: argThat(
        allOf([
          containsPair('task_id', 'task-1'),
          containsPair('completion', completion),
        ]),
        named: 'payload',
      ),
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:complete',
      priority: 2,
      traceId: anyNamed('traceId'),
    )).called(1);
  });

  test('enqueueAbandon includes reason when provided', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    await queue.enqueueAbandon('task-1', reason: 'too hard');

    verify(mockEngine.enqueue(
      topic: 'task',
      opType: 'abandon',
      payload: argThat(
        allOf([
          containsPair('task_id', 'task-1'),
          containsPair('reason', 'too hard'),
        ]),
        named: 'payload',
      ),
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:abandon',
      priority: 1,
      traceId: anyNamed('traceId'),
    )).called(1);
  });

  test('pendingTaskOpsCount returns 0 when no task ops exist', () async {
    final queue = TaskOfflineQueue(mockEngine, localDb);
    final count = await queue.pendingTaskOpsCount();
    expect(count, 0);
  });

  test('pendingTaskOpsCount counts pending task outbox items', () async {
    // Use a real SyncEngine to write items
    final mockWs = MockWebSocketService();
    final mockApi = MockApiClient();
    final realEngine = SyncEngine(localDb, mockWs, mockApi);

    final queue = TaskOfflineQueue(realEngine, localDb);
    await queue.enqueueStart('task-1');
    await queue.enqueuePause('task-2');

    final count = await queue.pendingTaskOpsCount();
    expect(count, 2);
  });
}
