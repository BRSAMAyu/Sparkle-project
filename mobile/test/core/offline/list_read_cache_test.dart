import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/cached_list_snapshot.dart';

import '../../shared/isar_test_helper.dart';

/// N34（A-SPEC6）验收：备考资产本地读缓存服务的机制钉。
///
/// - 只存真实 API 响应（put 即入、get 即回，payload 形状不改动）；
/// - 版本不符的旧条目永不服务（照统计域 legacy purge 先例）；
/// - 连接类失败才可回退快照；服务端语义错误不回退（诚实口径）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;
  late ListReadCache cache;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('list_read_cache_test');
    isar = await Isar.open(
      [CachedListSnapshotSchema],
      directory: tempDir.path,
    );
    localDb = LocalDatabase();
    localDb.isar = isar;
    cache = ListReadCache(localDb);
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  group('ListReadCache put/get', () {
    test('roundtrip preserves payload shape and stamps fetchedAt', () async {
      final payload = <String, dynamic>{
        'items': [
          {'id': 'e1', 'question_text': 'Q1'},
          {'id': 'e2', 'question_text': 'Q2'},
        ],
        'total': 2,
        'page': 1,
      };
      final before = DateTime.now().subtract(const Duration(seconds: 1));

      await cache.put('eb:list:key1', payload);
      final snapshot = await cache.get('eb:list:key1');

      expect(snapshot, isNotNull);
      expect(snapshot!.fetchedAt.isAfter(before), isTrue);
      final decoded = snapshot.payload as Map<String, dynamic>;
      expect((decoded['items'] as List).length, 2);
      expect(decoded['total'], 2);
    });

    test('second put overwrites same key (unique cacheKey)', () async {
      await cache.put('task:today:v1', <Map<String, dynamic>>[
        {'id': 't1'},
      ]);
      await cache.put('task:today:v1', <Map<String, dynamic>>[
        {'id': 't1'},
        {'id': 't2'},
      ]);

      final snapshot = await cache.get('task:today:v1');
      expect((snapshot!.payload as List).length, 2);
    });

    test('get returns null for missing key', () async {
      expect(await cache.get('community:feed:missing'), isNull);
    });

    test('get rejects and purges version-mismatched entries', () async {
      // 手工写入一个旧版本条目（模拟格式演进后的存量数据）。
      await isar.writeTxn(() async {
        await isar.cachedListSnapshots.put(
          CachedListSnapshot()
            ..cacheKey = 'eb:list:legacy'
            ..jsonData = const [123]
            ..fetchedAt = DateTime.now()
            ..version = 'v0',
        );
      });

      expect(await cache.get('eb:list:legacy'), isNull);
      // 旧条目已被清理，不留死数据。
      final remaining = await isar.cachedListSnapshots
          .filter()
          .cacheKeyEqualTo('eb:list:legacy')
          .count();
      expect(remaining, 0);
    });
  });

  group('ListReadCache invalidatePrefix', () {
    test('deletes same-domain snapshots only', () async {
      await cache.put('eb:list:a', <String, dynamic>{'x': 1});
      await cache.put('eb:stats', <String, dynamic>{'y': 2});
      await cache.put('task:today:v1', <String, dynamic>{'z': 3});

      await cache.invalidatePrefix('eb:');

      expect(await cache.get('eb:list:a'), isNull);
      expect(await cache.get('eb:stats'), isNull);
      expect(await cache.get('task:today:v1'), isNotNull);
    });
  });

  group('ListReadCache.isNetworkFailure', () {
    DioException dioError(DioExceptionType type) => DioException(
          requestOptions: RequestOptions(path: '/'),
          type: type,
        );

    test('connection-class failures are network failures', () {
      expect(
        ListReadCache.isNetworkFailure(
          dioError(DioExceptionType.connectionError),
        ),
        isTrue,
      );
      expect(
        ListReadCache.isNetworkFailure(
          dioError(DioExceptionType.connectionTimeout),
        ),
        isTrue,
      );
      expect(
        ListReadCache.isNetworkFailure(
          dioError(DioExceptionType.receiveTimeout),
        ),
        isTrue,
      );
      expect(
        ListReadCache.isNetworkFailure(
          dioError(DioExceptionType.sendTimeout),
        ),
        isTrue,
      );
    });

    test('server-side semantic failures are never network failures', () {
      final badResponse = DioException(
        requestOptions: RequestOptions(path: '/'),
        type: DioExceptionType.badResponse,
      );
      expect(ListReadCache.isNetworkFailure(badResponse), isFalse);
      expect(ListReadCache.isNetworkFailure(Exception('500 server')), isFalse);
    });
  });
}
