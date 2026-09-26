import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/isar_test_helper.dart';
import 'task_offline_wiring_test.mocks.dart';

@GenerateMocks([ApiClient, SyncEngine])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late ListReadCache cache;
  late MockApiClient mockApi;
  late MockSyncEngine mockEngine;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('task_offline_wiring');
    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
        CachedListSnapshotSchema,
      ],
      directory: tempDir.path,
    );
    localDb = LocalDatabase()..isar = isar;
    cache = ListReadCache(localDb);
    mockApi = MockApiClient();
    mockEngine = MockSyncEngine();
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  RequestOptions options(String path) => RequestOptions(path: path);

  DioException offlineError() => DioException(
        requestOptions: options('/tasks'),
        type: DioExceptionType.connectionError,
      );

  Map<String, dynamic> taskJson(String id, {String status = 'PENDING'}) => {
        'id': id,
        'user_id': 'u1',
        'title': 'Task $id',
        'type': 'LEARNING',
        'tags': <String>[],
        'estimated_minutes': 30,
        'difficulty': 3,
        'energy_cost': 2,
        'status': status,
        'priority': 2,
        'created_at': '2026-09-20T08:00:00Z',
        'updated_at': '2026-09-20T08:00:00Z',
      };

  group('N35 · task 生命周期离线入队（死代码接线令验收）', () {
    test('pauseTask 离线 → 入队 pause 并抛 OfflineEnqueuedException', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.pauseTask('t1', reason: 'user_paused'),
        throwsA(isA<OfflineEnqueuedException>()),
      );

      final captured = verify(mockEngine.enqueue(
        topic: 'task',
        opType: 'pause',
        payload: captureAnyNamed('payload'),
        entityType: 'task',
        entityId: 't1',
        dedupeKey: 'task:t1:pause',
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),).captured.single as Map<String, dynamic>;
      expect(captured['task_id'], 't1');
      expect(captured['reason'], 'user_paused');
    });

    test('resumeTask 离线 → 入队 resume', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.resumeTask('t2'),
        throwsA(isA<OfflineEnqueuedException>()),
      );

      verify(mockEngine.enqueue(
        topic: 'task',
        opType: 'resume',
        payload: anyNamed('payload'),
        entityType: 'task',
        entityId: 't2',
        dedupeKey: 'task:t2:resume',
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),).called(1);
    });

    test('startTask 离线 → 入队 start（原死代码接线）', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.startTask('t3'),
        throwsA(isA<OfflineEnqueuedException>()),
      );

      verify(mockEngine.enqueue(
        topic: 'task',
        opType: 'start',
        payload: anyNamed('payload'),
        entityType: 'task',
        entityId: 't3',
        dedupeKey: 'task:t3:start',
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),).called(1);
    });

    test('completeTask 离线 → 入队 complete（实测分钟进 completion 体）', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.completeTask('t4', 42, 'done'),
        throwsA(isA<OfflineEnqueuedException>()),
      );

      final captured = verify(mockEngine.enqueue(
        topic: 'task',
        opType: 'complete',
        payload: captureAnyNamed('payload'),
        entityType: 'task',
        entityId: 't4',
        dedupeKey: 'task:t4:complete',
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),).captured.single as Map<String, dynamic>;
      expect(captured['completion']['actual_minutes'], 42);
      expect(captured['completion']['user_note'], 'done');
    });

    test('abandonTask 离线 → 入队 abandon（原死代码接线）', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.abandonTask('t5'),
        throwsA(isA<OfflineEnqueuedException>()),
      );

      verify(mockEngine.enqueue(
        topic: 'task',
        opType: 'abandon',
        payload: anyNamed('payload'),
        entityType: 'task',
        entityId: 't5',
        dedupeKey: 'task:t5:abandon',
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),).called(1);
    });

    test('SyncEngine 不可用时不入队、沿用旧错误通道', () async {
      final repo = TaskRepository(mockApi);
      when(mockApi.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(offlineError());

      await expectLater(
        repo.pauseTask('t6'),
        throwsA(isA<Exception>()),
      );
      verifyNever(mockEngine.enqueue(
        topic: anyNamed('topic'),
        opType: anyNamed('opType'),
        payload: anyNamed('payload'),
        entityType: anyNamed('entityType'),
        entityId: anyNamed('entityId'),
        dedupeKey: anyNamed('dedupeKey'),
        priority: anyNamed('priority'),
        traceId: anyNamed('traceId'),
      ),);
    });
  });

  group('N34 · 任务读路径本地快照', () {
    test('getTodayTasksCached 成功落快照；断网回读 fromCache+asOf', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine, readCache: cache);
      final body = <String, dynamic>{
        'data': [taskJson('t7', status: 'IN_PROGRESS')],
      };
      when(mockApi.get<Map<String, dynamic>>(any,
          queryParameters: anyNamed('queryParameters'),),)
          .thenAnswer((_) async => Response<Map<String, dynamic>>(
                requestOptions: options('/tasks/today'),
                data: body,
                statusCode: 200,
              ),);

      final fresh = await repo.getTodayTasksCached();
      expect(fresh.fromCache, isFalse);
      expect(fresh.data.single.id, 't7');

      // 断网重进（连接类失败）。
      when(mockApi.get<Map<String, dynamic>>(any,
          queryParameters: anyNamed('queryParameters'),),)
          .thenThrow(offlineError());

      final stale = await repo.getTodayTasksCached();
      expect(stale.fromCache, isTrue);
      expect(stale.asOf, isNotNull);
      expect(stale.data.single.status, TaskStatus.inProgress);
    });

    test('getTasksCached 断网回读分页快照', () async {
      final repo = TaskRepository(mockApi, offlineSync: mockEngine, readCache: cache);
      final body = <String, dynamic>{
        'items': [taskJson('t8')],
        'total': 1,
        'page': 1,
        'page_size': 50,
      };
      when(mockApi.get<Map<String, dynamic>>(any,
          queryParameters: anyNamed('queryParameters'),),)
          .thenAnswer((_) async => Response<Map<String, dynamic>>(
                requestOptions: options('/tasks'),
                data: body,
                statusCode: 200,
              ),);

      await repo.getTasksCached(filters: {});
      expect(
        await cache.get('task:list:-:p1:s50'),
        isNotNull,
      );

      when(mockApi.get<Map<String, dynamic>>(any,
          queryParameters: anyNamed('queryParameters'),),)
          .thenThrow(offlineError());

      final stale = await repo.getTasksCached(filters: {});
      expect(stale.fromCache, isTrue);
      expect(stale.data.items.single.id, 't8');
      expect(stale.data.total, 1);
    });
  });
}
