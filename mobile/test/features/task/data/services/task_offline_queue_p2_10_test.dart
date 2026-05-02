import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/features/task/data/services/task_offline_queue.dart';

import '../../../../core/p2_10_core_service_test_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late P2TestIsar harness;
  late RecordingSyncEngine syncEngine;
  late TaskOfflineQueue queue;

  setUpAll(initializeP2TestIsar);

  setUp(() async {
    harness = await openP2TestIsar('task_offline_queue_p2_10');
    syncEngine = RecordingSyncEngine(harness.localDb);
    queue = TaskOfflineQueue(syncEngine, harness.localDb);
  });

  tearDown(() => harness.dispose());

  test('enqueueStart records an idempotent task start operation', () async {
    await queue.enqueueStart('task-1', traceId: 'trace-start');

    expect(syncEngine.enqueued.single.topic, 'task');
    expect(syncEngine.enqueued.single.opType, 'start');
    expect(syncEngine.enqueued.single.payload, {'task_id': 'task-1'});
    expect(syncEngine.enqueued.single.entityType, 'task');
    expect(syncEngine.enqueued.single.entityId, 'task-1');
    expect(syncEngine.enqueued.single.dedupeKey, 'task:task-1:start');
    expect(syncEngine.enqueued.single.priority, 1);
    expect(syncEngine.enqueued.single.traceId, 'trace-start');
  });

  test('enqueuePause includes non-empty reasons only', () async {
    await queue.enqueuePause('task-2', reason: 'manual');
    await queue.enqueuePause('task-3', reason: '');

    expect(syncEngine.enqueued.first.payload, {
      'task_id': 'task-2',
      'reason': 'manual',
    });
    expect(syncEngine.enqueued.last.payload, {'task_id': 'task-3'});
    expect(syncEngine.enqueued.last.dedupeKey, 'task:task-3:pause');
  });

  test('enqueueComplete carries completion payload at higher priority',
      () async {
    await queue.enqueueComplete(
      'task-4',
      completion: const <String, dynamic>{'score': 96},
      traceId: 'trace-complete',
    );

    expect(syncEngine.enqueued.single.opType, 'complete');
    expect(syncEngine.enqueued.single.payload, {
      'task_id': 'task-4',
      'completion': {'score': 96},
    });
    expect(syncEngine.enqueued.single.priority, 2);
    expect(syncEngine.enqueued.single.traceId, 'trace-complete');
  });

  test('pendingTaskOpsCount includes pending waitingAck and failed task ops',
      () async {
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.pending,
    );
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.waitingAck,
    );
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.failed,
    );
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.synced,
    );
    await _putOutbox(
      harness.localDb,
      topic: 'cognitive',
      status: SyncStatus.pending,
    );

    expect(await queue.pendingTaskOpsCount(), 3);
  });

  test('providers build the queue and emit the pending task op count',
      () async {
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.pending,
    );
    await _putOutbox(
      harness.localDb,
      topic: 'task',
      status: SyncStatus.failed,
    );
    final container = ProviderContainer(
      overrides: [
        localDatabaseProvider.overrideWithValue(harness.localDb),
        syncEngineProvider.overrideWithValue(syncEngine),
      ],
    );
    addTearDown(container.dispose);

    await container.read(taskOfflineQueueProvider).enqueueResume('task-5');
    final count = await container.read(pendingTaskOpsCountProvider.future);

    expect(syncEngine.enqueued.single.opType, 'resume');
    expect(count, 2);
  });
}

Future<int> _putOutbox(
  LocalDatabase localDb, {
  required String topic,
  required SyncStatus status,
}) {
  final item = OutboxItem()
    ..uuid = '$topic-${status.name}-${DateTime.now().microsecondsSinceEpoch}'
    ..topic = topic
    ..opType = 'test'
    ..payloadJson = jsonEncode(<String, dynamic>{'topic': topic})
    ..createdAt = DateTime.now()
    ..status = status;
  return localDb.isar.writeTxn(() => localDb.isar.outboxItems.put(item));
}
