import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

import '../../../../shared/isar_test_helper.dart';

import 'community_feed_cache_test.mocks.dart';

@GenerateMocks([ApiClient])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late ListReadCache cache;
  late MockApiClient mockApi;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
  });

  setUp(() async {
    tempDir =
        await Directory.systemTemp.createTemp('community_feed_cache_test');
    isar = await Isar.open(
      [CachedListSnapshotSchema],
      directory: tempDir.path,
    );
    localDb = LocalDatabase();
    localDb.isar = isar;
    cache = ListReadCache(localDb);
    mockApi = MockApiClient();
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  RequestOptions options(String path) => RequestOptions(path: path);

  List<Map<String, dynamic>> sampleFeed() => [
        {
          'id': 'p1',
          'user_id': 'u1',
          'content': '高数第三章刷完了，冲！',
          'created_at': '2026-09-21T10:00:00Z',
          'user': {'id': 'u1', 'username': '同学A'},
          'like_count': 3,
        },
      ];

  group('N34 · getFeedCached 断网回读快照', () {
    test('在线成功落快照；断网回读 fromCache=true + asOf 时点', () async {
      final repo = CommunityRepository(mockApi, readCache: cache);
      when(mockApi.get<dynamic>(any,
              queryParameters: anyNamed('queryParameters')))
          .thenAnswer((_) async => Response<dynamic>(
                requestOptions: options('/community/feed'),
                data: {'data': sampleFeed()},
                statusCode: 200,
              ));

      final fresh = await repo.getFeedCached(page: 1, scope: null);
      expect(fresh.fromCache, isFalse);
      expect(fresh.data.single.id, 'p1');

      when(mockApi.get<dynamic>(any,
              queryParameters: anyNamed('queryParameters')))
          .thenThrow(DioException(
        requestOptions: options('/community/feed'),
        type: DioExceptionType.connectionError,
      ));

      final stale = await repo.getFeedCached(page: 1, scope: null);
      expect(stale.fromCache, isTrue);
      expect(stale.asOf, isNotNull);
      expect(stale.data.single.content, '高数第三章刷完了，冲！');
    });

    test('无快照断网照常抛错（不造数据）', () async {
      final repo = CommunityRepository(mockApi, readCache: cache);
      when(mockApi.get<dynamic>(any,
              queryParameters: anyNamed('queryParameters')))
          .thenThrow(DioException(
        requestOptions: options('/community/feed'),
        type: DioExceptionType.connectionError,
      ));

      await expectLater(
        repo.getFeedCached(),
        throwsA(isA<DioException>()),
      );
    });
  });
}
