import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/crdt_sync_manager.dart';
import 'package:sparkle/core/offline/offline_crdt_document.dart';

import '../p2_10_core_service_test_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late P2TestIsar harness;
  late RecordingSyncEngine syncEngine;
  late CRDTSyncManager manager;

  setUpAll(initializeP2TestIsar);

  setUp(() async {
    harness = await openP2TestIsar('crdt_sync_manager_p2_10');
    syncEngine = RecordingSyncEngine(harness.localDb);
    manager = CRDTSyncManager(
      harness.localDb,
      syncEngine,
      actorId: 'actor-a',
    );
  });

  tearDown(() => harness.dispose());

  test('initialize and dispose delegate lifecycle to SyncEngine', () {
    manager
      ..initialize()
      ..dispose();

    expect(syncEngine.started, isTrue);
    expect(syncEngine.stopped, isTrue);
  });

  test('local mastery delta persists a snapshot and enqueues CRDT payload',
      () async {
    await manager.applyKnowledgeMasteryDelta(
      nodeId: 'node-1',
      delta: 12,
      galaxyId: 'galaxy-a',
    );

    final snapshot = await manager.getSnapshot('galaxy-a');
    final document = OfflineCrdtDocument.fromBytes(snapshot!.updateData);

    expect(snapshot.synced, isFalse);
    expect(document.knowledgeMastery('node-1'), 12);
    expect(syncEngine.enqueued, hasLength(1));
    expect(syncEngine.enqueued.single.topic, 'crdt');
    expect(syncEngine.enqueued.single.opType, 'delta');
    expect(syncEngine.enqueued.single.entityId, 'galaxy-a');
    expect(syncEngine.enqueued.single.dedupeKey, isNotEmpty);
    expect(syncEngine.enqueued.single.payload['operations'], hasLength(1));
  });

  test('setKnowledgeMastery clamps to 100 and avoids no-op enqueue', () async {
    await manager.setKnowledgeMastery(
      nodeId: 'node-2',
      mastery: 140,
      galaxyId: 'galaxy-b',
    );
    await manager.setKnowledgeMastery(
      nodeId: 'node-2',
      mastery: 100,
      galaxyId: 'galaxy-b',
    );

    final document = await manager.getDocument('galaxy-b');

    expect(document.knowledgeMastery('node-2'), 100);
    expect(syncEngine.enqueued, hasLength(1));
  });

  test('remote conflict merge is idempotent and does not enqueue', () async {
    final operation = makeKnowledgeMasteryDelta(
      opId: 'remote-op-1',
      actorId: 'remote-a',
      nodeId: 'node-3',
      delta: 9,
      lamport: 3,
      createdAt: DateTime.utc(2026, 5, 2),
    );
    final update = utf8.encode(
      jsonEncode(<String, dynamic>{
        'protocol': offlineCrdtProtocol,
        'operations': <Map<String, dynamic>>[operation.toJson()],
      }),
    );

    await manager.resolveConflict(update, galaxyId: 'galaxy-c');
    await manager.resolveConflict(update, galaxyId: 'galaxy-c');

    final snapshot = await manager.getSnapshot('galaxy-c');
    final document = OfflineCrdtDocument.fromBytes(snapshot!.updateData);

    expect(snapshot.synced, isTrue);
    expect(document.operations, hasLength(1));
    expect(document.knowledgeMastery('node-3'), 9);
    expect(syncEngine.enqueued, isEmpty);
  });

  test('task state operations merge to the highest-ranked terminal status',
      () async {
    await manager.setTaskState(
      taskId: 'task-1',
      status: 'in_progress',
      galaxyId: 'galaxy-d',
    );
    await manager.setTaskState(
      taskId: 'task-1',
      status: 'completed',
      galaxyId: 'galaxy-d',
      metadata: const <String, dynamic>{'source': 'offline'},
    );

    final document = await manager.getDocument('galaxy-d');

    expect(document.taskState('task-1'), containsPair('status', 'completed'));
    expect(syncEngine.enqueued, hasLength(2));
    expect(syncEngine.enqueued.last.payload['operations'], hasLength(1));
  });

  test('chat append stores ordered message content and enqueues a delta',
      () async {
    await manager.appendChatMessage(
      sessionId: 'session-1',
      messageId: 'message-1',
      content: 'hello offline',
      role: 'user',
      galaxyId: 'galaxy-e',
      metadata: const <String, dynamic>{'surface': 'chat'},
    );

    final document = await manager.getDocument('galaxy-e');
    final messages = document.chatMessages('session-1');

    expect(messages, hasLength(1));
    expect(messages.single['messageId'], 'message-1');
    expect(messages.single['content'], 'hello offline');
    expect(messages.single['metadata'], containsPair('surface', 'chat'));
    expect(syncEngine.enqueued.single.payload['operations'], hasLength(1));
  });
}
