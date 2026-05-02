// ignore_for_file: depend_on_referenced_packages

import 'dart:convert';

import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';

import '../p2_10_core_service_test_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late P2TestIsar harness;
  late FakeConnectivityPlatform connectivity;
  late ConnectivityPlatform previousConnectivity;
  late RecordingApiClient apiClient;
  late StubWebSocketService webSocket;
  late SyncEngine engine;

  setUpAll(initializeP2TestIsar);

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    previousConnectivity = ConnectivityPlatform.instance;
    connectivity = FakeConnectivityPlatform();
    ConnectivityPlatform.instance = connectivity;
    harness = await openP2TestIsar('sync_engine_p2_10');
    apiClient = RecordingApiClient();
    webSocket = StubWebSocketService();
    engine = SyncEngine(harness.localDb, webSocket, apiClient);
  });

  tearDown(() async {
    ConnectivityPlatform.instance = previousConnectivity;
    await webSocket.close();
    await connectivity.close();
    await harness.dispose();
  });

  test('enqueue persists a pending outbox item with dedupe metadata', () async {
    await engine.enqueue(
      topic: 'task',
      opType: 'pause',
      payload: const <String, dynamic>{'task_id': 'task-1', 'reason': 'manual'},
      entityType: 'task',
      entityId: 'task-1',
      dedupeKey: 'task:task-1:pause',
      priority: 2,
      traceId: 'trace-1',
    );

    final items = (await harness.isar.outboxItems.where().findAll())
        .where((item) => item.topic == 'task')
        .toList();

    expect(items, hasLength(1));
    expect(items.single.topic, 'task');
    expect(items.single.opType, 'pause');
    expect(items.single.entityType, 'task');
    expect(items.single.entityId, 'task-1');
    expect(items.single.dedupeKey, 'task:task-1:pause');
    expect(items.single.priority, 2);
    expect(items.single.traceId, 'trace-1');
    expect(items.single.status, SyncStatus.pending);
    expect(
      jsonDecode(items.single.payloadJson!),
      containsPair('reason', 'manual'),
    );
  });

  test('processNow routes task start operations to the task endpoint',
      () async {
    final id = await _putOutbox(
      harness.localDb,
      topic: 'task',
      opType: 'start',
      payload: const <String, dynamic>{'task_id': 'task-2'},
    );

    await engine.processNow(skipConnectivity: true);

    final updated = await harness.isar.outboxItems.get(id);
    expect(apiClient.requests.single.path, ApiEndpoints.startTask('task-2'));
    expect(apiClient.requests.single.data, isNull);
    expect(updated!.status, SyncStatus.synced);
  });

  test('task resume treats 409 idempotency conflict as success', () async {
    apiClient.onPost = (request) async {
      throw DioException(
        requestOptions: RequestOptions(path: request.path),
        response: Response<dynamic>(
          requestOptions: RequestOptions(path: request.path),
          statusCode: 409,
        ),
        type: DioExceptionType.badResponse,
      );
    };
    final id = await _putOutbox(
      harness.localDb,
      topic: 'task',
      opType: 'resume',
      payload: const <String, dynamic>{'task_id': 'task-3'},
    );

    await engine.processNow(skipConnectivity: true);

    final updated = await harness.isar.outboxItems.get(id);
    expect(apiClient.requests.single.path, ApiEndpoints.resumeTask('task-3'));
    expect(updated!.status, SyncStatus.synced);
  });

  test('cognitive and intervention topics are replayed through REST routes',
      () async {
    await _putOutbox(
      harness.localDb,
      topic: 'cognitive',
      opType: 'create',
      payload: const <String, dynamic>{'content': 'fragment'},
      createdAt: DateTime.now().subtract(const Duration(seconds: 1)),
    );
    await _putOutbox(
      harness.localDb,
      topic: 'intervention_feedback',
      opType: 'create',
      payload: const <String, dynamic>{
        'intervention_id': 'iv-1',
        'feedback_type': 'helpful',
      },
    );

    await engine.processNow(force: true, skipConnectivity: true);

    expect(
      apiClient.requests.map((request) => request.path),
      containsAllInOrder(<String>[
        ApiEndpoints.cognitiveFragments,
        ApiEndpoints.interventionFeedback('iv-1'),
      ]),
    );
    expect(
      (await harness.isar.outboxItems.where().findAll())
          .where((item) => item.status == SyncStatus.synced)
          .length,
      2,
    );
  });

  test('unknown task op records retry metadata instead of dropping the item',
      () async {
    final id = await _putOutbox(
      harness.localDb,
      topic: 'task',
      opType: 'teleport',
      payload: const <String, dynamic>{'task_id': 'task-4'},
    );

    await engine.processNow(skipConnectivity: true);

    final updated = await harness.isar.outboxItems.get(id);
    expect(updated!.status, SyncStatus.pending);
    expect(updated.attemptCount, 1);
    expect(updated.retryCount, 1);
    expect(updated.lastErrorCode, 'UNKNOWN_TASK_OP');
    expect(updated.nextAttemptAt, isNotNull);
    expect(apiClient.requests, isEmpty);
  });
}

Future<int> _putOutbox(
  LocalDatabase localDb, {
  required String topic,
  required String opType,
  required Map<String, dynamic> payload,
  DateTime? createdAt,
}) {
  final item = OutboxItem()
    ..uuid = '$topic-$opType-${DateTime.now().microsecondsSinceEpoch}'
    ..topic = topic
    ..opType = opType
    ..payloadJson = jsonEncode(payload)
    ..createdAt = createdAt ?? DateTime.now()
    ..status = SyncStatus.pending;
  return localDb.isar.writeTxn(() => localDb.isar.outboxItems.put(item));
}
