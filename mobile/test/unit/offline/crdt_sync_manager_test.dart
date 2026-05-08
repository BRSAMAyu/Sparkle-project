// ignore_for_file: discarded_futures

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import '../../shared/isar_test_helper.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/crdt_sync_manager.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_crdt_document.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';

import 'crdt_sync_manager_test.mocks.dart';

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
    tempDir = await Directory.systemTemp.createTemp('crdt_test');
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
    try {
      await isar.close(deleteFromDisk: true);
    } catch (_) {}
    try {
      await tempDir.delete(recursive: true);
    } catch (_) {}
  });

  test('applyUpdate with valid operations persists document', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');
    final operations = [
      makeKnowledgeMasteryDelta(
        opId: 'op-1',
        actorId: 'actor-1',
        nodeId: 'node-1',
        delta: 10,
        lamport: 1,
        createdAt: DateTime.now(),
      ),
    ];
    final payload = {
      'protocol': offlineCrdtProtocol,
      'operations': operations.map((o) => o.toJson()).toList(),
      'vectorClock': {'actor-1': 1},
    };

    await manager.applyUpdate(
      utf8.encode(jsonEncode(payload)),
      origin: 'remote',
      galaxyId: 'test-galaxy',
    );

    final doc = await manager.getDocument('test-galaxy');
    expect(doc.operations.length, 1);
    expect(doc.knowledgeMastery('node-1'), 10);
  });

  test('applyKnowledgeMasteryDelta accumulates delta on existing document', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');

    await manager.applyKnowledgeMasteryDelta(
      nodeId: 'node-1',
      delta: 20,
      galaxyId: 'g1',
    );

    await manager.applyKnowledgeMasteryDelta(
      nodeId: 'node-1',
      delta: 15,
      galaxyId: 'g1',
    );

    final doc = await manager.getDocument('g1');
    expect(doc.knowledgeMastery('node-1'), 35);
    verify(mockEngine.enqueue(topic: 'crdt', opType: 'delta', payload: anyNamed('payload'), entityType: anyNamed('entityType'), entityId: anyNamed('entityId'), dedupeKey: anyNamed('dedupeKey'))).called(2);
  });

  test('applyKnowledgeMasteryDelta skips zero delta', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');

    await manager.applyKnowledgeMasteryDelta(
      nodeId: 'node-1',
      delta: 0,
      galaxyId: 'g1',
    );

    final doc = await manager.getDocument('g1');
    expect(doc.operations.isEmpty, isTrue);
    verifyNever(mockEngine.enqueue(
      topic: anyNamed('topic'),
      opType: anyNamed('opType'),
      payload: anyNamed('payload'),
    ));
  });

  test('setTaskState creates task_status operation', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');

    await manager.setTaskState(
      taskId: 'task-1',
      status: 'IN_PROGRESS',
      galaxyId: 'g1',
      metadata: {'source': 'test'},
    );

    final doc = await manager.getDocument('g1');
    final state = doc.taskState('task-1');
    expect(state['status'], 'IN_PROGRESS');
  });

  test('resolveConflict applies remote update and merges', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');

    // First, apply a local operation
    await manager.applyKnowledgeMasteryDelta(
      nodeId: 'node-1',
      delta: 10,
      galaxyId: 'g1',
    );

    // Then resolve a conflict with a remote update
    final remoteOps = [
      makeKnowledgeMasteryDelta(
        opId: 'remote-op-1',
        actorId: 'actor-2',
        nodeId: 'node-1',
        delta: 5,
        lamport: 1,
        createdAt: DateTime.now(),
      ),
    ];
    final remotePayload = {
      'protocol': offlineCrdtProtocol,
      'operations': remoteOps.map((o) => o.toJson()).toList(),
      'vectorClock': {'actor-2': 1},
    };

    await manager.resolveConflict(
      utf8.encode(jsonEncode(remotePayload)),
      galaxyId: 'g1',
    );

    final doc = await manager.getDocument('g1');
    // Both local and remote operations should be present
    expect(doc.knowledgeMastery('node-1'), 15);
  });

  test('appendChatMessage stores message in document', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');

    await manager.appendChatMessage(
      sessionId: 'session-1',
      messageId: 'msg-1',
      content: 'Hello',
      role: 'user',
      galaxyId: 'g1',
    );

    final doc = await manager.getDocument('g1');
    final messages = doc.chatMessages('session-1');
    expect(messages.length, 1);
    expect(messages.first['content'], 'Hello');
    expect(messages.first['role'], 'user');
  });

  test('getSnapshot returns null for non-existent galaxy', () async {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');
    final snapshot = await manager.getSnapshot('nonexistent');
    expect(snapshot, isNull);
  });

  test('initialize and dispose delegate to SyncEngine', () {
    final manager = CRDTSyncManager(localDb, mockEngine, actorId: 'actor-1');
    manager.initialize();
    verify(mockEngine.start()).called(1);

    manager.dispose();
    verify(mockEngine.stop()).called(1);
  });
}
