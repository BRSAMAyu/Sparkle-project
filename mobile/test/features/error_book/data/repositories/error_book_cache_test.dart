import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

import '../../../../shared/isar_test_helper.dart';
import 'error_book_cache_test.mocks.dart';

@GenerateMocks([Dio])
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late ListReadCache cache;
  late MockDio mockDio;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
  });

  setUp(() async {
    tempDir =
        await Directory.systemTemp.createTemp('error_book_cache_test');
    isar = await Isar.open(
      [CachedListSnapshotSchema],
      directory: tempDir.path,
    );
    localDb = LocalDatabase();
    localDb.isar = isar;
    cache = ListReadCache(localDb);
    mockDio = MockDio();
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  RequestOptions options(String path) => RequestOptions(path: path);

  /// 与 /errors 真实响应同形的样本体。
  Map<String, dynamic> sampleListResponse() => {
        'items': [
          {
            'id': 'e1',
            'question_text': '快速排序平均复杂度?',
            'user_answer': 'O(n)',
            'correct_answer': 'O(n log n)',
            'subject_code': 'cs',
            'mastery_level': 0.6,
            'review_count': 2,
            'created_at': '2026-09-20T08:00:00Z',
            'updated_at': '2026-09-21T08:00:00Z',
          },
          {
            'id': 'e2',
            'question_text': '三次握手的第二步?',
            'user_answer': 'ACK',
            'correct_answer': 'SYN+ACK',
            'subject_code': 'network',
            'mastery_level': 0.3,
            'review_count': 1,
            'created_at': '2026-09-20T08:00:00Z',
            'updated_at': '2026-09-21T08:00:00Z',
          },
        ],
        'total': 2,
        'page': 1,
        'page_size': 20,
        'has_next': false,
      };

  group('getErrorsCached（N34 断网冷启动有数据）', () {
    test('成功响应落快照且 fromCache=false', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      when(mockDio.get<Map<String, dynamic>>(
        any,
        queryParameters: anyNamed('queryParameters'),
      ),).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: options('/errors'),
          data: sampleListResponse(),
          statusCode: 200,
        ),
      );

      final result = await repo.getErrorsCached(subject: 'cs');

      expect(result.fromCache, isFalse);
      expect(result.asOf, isNull);
      expect(result.data.items.length, 2);

      final snapshot = await cache.get('eb:list:cs|-|-|0|-|-|-|-|p1|s20');
      expect(snapshot, isNotNull);
    });

    test('断网（连接类失败）回读快照：fromCache=true + asOf 时点', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      const key = 'eb:list:cs|-|-|0|-|-|-|-|p1|s20';
      // 预置一次「上次在线时」的快照。
      await cache.put(key, sampleListResponse());

      when(mockDio.get<Map<String, dynamic>>(
        any,
        queryParameters: anyNamed('queryParameters'),
      ),).thenThrow(DioException(
        requestOptions: options('/errors'),
        type: DioExceptionType.connectionError,
      ),);

      final result = await repo.getErrorsCached(subject: 'cs');

      expect(result.fromCache, isTrue);
      expect(result.asOf, isNotNull);
      expect(result.data.items.length, 2);
      expect(result.data.items.first.id, 'e1');
    });

    test('无快照的断网照常抛业务错误（白屏→错误态，不造假数据）', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      when(mockDio.get<Map<String, dynamic>>(
        any,
        queryParameters: anyNamed('queryParameters'),
      ),).thenThrow(DioException(
        requestOptions: options('/errors'),
        type: DioExceptionType.connectionError,
      ),);

      expect(
        repo.getErrorsCached,
        throwsA(isA<Exception>()),
      );
    });

    test('服务端语义错误（4xx/5xx）不用旧快照掩盖，照常上抛', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      await cache.put('eb:list:-|-|-|0|-|-|-|-|p1|s20', sampleListResponse());

      when(mockDio.get<Map<String, dynamic>>(
        any,
        queryParameters: anyNamed('queryParameters'),
      ),).thenThrow(DioException(
        requestOptions: options('/errors'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options('/errors'),
          statusCode: 500,
        ),
      ),);

      expect(
        repo.getErrorsCached,
        throwsA(isA<Exception>()),
      );
      // 快照未被消费掉（仍然保留）。
      expect(
        await cache.get('eb:list:-|-|-|0|-|-|-|-|p1|s20'),
        isNotNull,
      );
    });
  });

  group('getStatsCached（N34 统计徽标离线有数）', () {
    test('断网回读统计快照', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      await cache.put('eb:stats', {
        'total_errors': 12,
        'mastered_count': 4,
        'need_review_count': 5,
        'review_streak_days': 3,
        'subject_distribution': {'cs': 7},
      });

      when(mockDio.get<Map<String, dynamic>>(any,
          queryParameters: anyNamed('queryParameters'),),)
          .thenThrow(DioException(
        requestOptions: options('/errors/stats'),
        type: DioExceptionType.connectionTimeout,
      ),);

      final result = await repo.getStatsCached();
      expect(result.fromCache, isTrue);
      expect(result.data.totalErrors, 12);
      expect(result.data.subjectDistribution['cs'], 7);
    });
  });

  group('写路径快照失效（N34：写不入缓存，口径不双源）', () {
    test('删除成功后同域快照全部失效', () async {
      final repo = ErrorBookRepository(mockDio, readCache: cache);
      await cache.put('eb:list:a', sampleListResponse());
      await cache.put('eb:stats', <String, dynamic>{});

      when(mockDio.delete<void>(any)).thenAnswer(
        (_) async => Response<void>(
          requestOptions: options('/errors/e1'),
          statusCode: 204,
        ),
      );

      await repo.deleteError('e1');

      expect(await cache.get('eb:list:a'), isNull);
      expect(await cache.get('eb:stats'), isNull);
    });
  });

  test('未注入读缓存时断网照常抛错（向后兼容）', () async {
    final repo = ErrorBookRepository(mockDio);
    when(mockDio.get<Map<String, dynamic>>(any,
        queryParameters: anyNamed('queryParameters'),),)
        .thenThrow(DioException(
      requestOptions: options('/errors'),
      type: DioExceptionType.connectionError,
    ),);

    expect(
      repo.getErrorsCached,
      throwsA(isA<Exception>()),
    );
  });

  test('CognitiveDimension 参与缓存键指纹（不同筛选不串快照）', () async {
    final repo = ErrorBookRepository(mockDio, readCache: cache);
    var call = 0;
    when(mockDio.get<Map<String, dynamic>>(any,
        queryParameters: anyNamed('queryParameters'),),)
        .thenAnswer((_) async {
      call++;
      return Response<Map<String, dynamic>>(
        requestOptions: options('/errors'),
        data: sampleListResponse(),
        statusCode: 200,
      );
    });

    await repo.getErrorsCached(
      cognitiveDimension: CognitiveDimension.memory,
    );
    await repo.getErrorsCached(
      cognitiveDimension: CognitiveDimension.understanding,
    );

    // 两个筛选各落一份快照。
    final all = await isar.cachedListSnapshots
        .filter()
        .cacheKeyStartsWith('eb:list:')
        .findAll();
    expect(all.length, 2);
    expect(call, 2);
  });
}
