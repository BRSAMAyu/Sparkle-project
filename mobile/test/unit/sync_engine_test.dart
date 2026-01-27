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
}

class _TestSyncEngine extends SyncEngine {
  _TestSyncEngine(super.localDb, super.wsService, super.apiClient);

  @override
  Future<void> processNow({bool force = false, bool skipConnectivity = false}) => super.processNow(force: force, skipConnectivity: true);
}
