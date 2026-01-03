import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/smart_cache.dart';

void main() {
  group('SmartCache', () {
    late SmartCache<String, int> cache;

    setUp(() {
      cache = SmartCache<String, int>(
        maxSize: 5,
        maxAge: const Duration(seconds: 10),
      );
    });

    test('stores and retrieves values', () {
      cache.set('key1', 100);
      cache.set('key2', 200);

      expect(cache.get('key1'), equals(100));
      expect(cache.get('key2'), equals(200));
    });

    test('returns null for non-existent keys', () {
      expect(cache.get('nonexistent'), isNull);
    });

    test('containsKey works correctly', () {
      cache.set('key1', 100);

      expect(cache.containsKey('key1'), isTrue);
      expect(cache.containsKey('key2'), isFalse);
    });

    test('removes values', () {
      cache.set('key1', 100);
      expect(cache.get('key1'), equals(100));

      cache.remove('key1');
      expect(cache.get('key1'), isNull);
    });

    test('clears all values', () {
      cache.set('key1', 100);
      cache.set('key2', 200);

      cache.clear();

      expect(cache.get('key1'), isNull);
      expect(cache.get('key2'), isNull);
      expect(cache.size, equals(0));
    });

    test('respects maxSize limit', () {
      for (var i = 0; i < 10; i++) {
        cache.set('key$i', i);
      }

      // 缓存大小应该不超过 maxSize
      expect(cache.size, lessThanOrEqualTo(5));
    });

    test('uses LRU eviction', () {
      // 填满缓存
      cache.set('key0', 0);
      cache.set('key1', 1);
      cache.set('key2', 2);
      cache.set('key3', 3);
      cache.set('key4', 4);

      // 访问最早的key，使其成为最近使用
      cache.get('key0');

      // 添加新key，应该淘汰 key1（现在是最久未使用的）
      cache.set('key5', 5);

      expect(cache.get('key0'), isNotNull); // 应该还在
      expect(cache.get('key5'), equals(5)); // 新添加的
    });

    test('calls onEvicted callback when items are removed', () {
      final evictedItems = <String, int>{};

      final cacheWithCallback = SmartCache<String, int>(
        maxSize: 3,
        onEvicted: (key, value) {
          evictedItems[key] = value;
        },
      );

      cacheWithCallback.set('key1', 100);
      cacheWithCallback.set('key2', 200);
      cacheWithCallback.set('key3', 300);
      cacheWithCallback.set('key4', 400); // 这应该触发淘汰

      expect(evictedItems.isNotEmpty, isTrue);
    });

    test('returns correct stats', () {
      cache.set('key1', 100);
      cache.set('key2', 200);

      final stats = cache.stats;

      expect(stats.size, equals(2));
      expect(stats.maxSize, equals(5));
      expect(stats.utilizationRate, equals(0.4));
    });

    test('updates value for existing key', () {
      cache.set('key1', 100);
      cache.set('key1', 200);

      expect(cache.get('key1'), equals(200));
      expect(cache.size, equals(1));
    });

    group('with time expiration', () {
      test('expires old entries', () async {
        final shortLivedCache = SmartCache<String, int>(
          maxSize: 10,
          maxAge: const Duration(milliseconds: 100),
        );

        shortLivedCache.set('key1', 100);

        expect(shortLivedCache.get('key1'), equals(100));

        // 等待过期
        await Future<void>.delayed(const Duration(milliseconds: 150));

        expect(shortLivedCache.get('key1'), isNull);
      });

      test('updates access time on get', () async {
        final shortLivedCache = SmartCache<String, int>(
          maxSize: 10,
          maxAge: const Duration(milliseconds: 200),
        );

        shortLivedCache.set('key1', 100);

        // 在过期前访问
        await Future<void>.delayed(const Duration(milliseconds: 100));
        expect(shortLivedCache.get('key1'), equals(100));

        // 再等待100ms，如果没有更新访问时间，应该过期了
        await Future<void>.delayed(const Duration(milliseconds: 100));
        expect(shortLivedCache.get('key1'), equals(100)); // 应该还在，因为访问更新了时间
      });
    });
  });

  group('SizedSmartCache', () {
    test('respects memory limit', () {
      final cache = SizedSmartCache<String, List<int>>(
        maxSize: 100,
        maxMemoryBytes: 1000,
        sizeEstimator: (value) => value.length * 4, // 每个int约4字节
      );

      // 添加一个250字节的条目
      cache.set('key1', List.generate(62, (i) => i)); // ~248 bytes

      // 添加更多条目直到接近限制
      cache.set('key2', List.generate(62, (i) => i)); // ~248 bytes
      cache.set('key3', List.generate(62, (i) => i)); // ~248 bytes
      cache.set('key4', List.generate(62, (i) => i)); // ~248 bytes

      // 此时应该接近1000字节限制

      // 添加新条目应该触发淘汰
      cache.set('key5', List.generate(62, (i) => i));

      // 内存使用应该在限制内
      expect(cache.currentMemoryBytes, lessThanOrEqualTo(1000));
    });

    test('does not cache items larger than max memory', () {
      final cache = SizedSmartCache<String, List<int>>(
        maxSize: 100,
        maxMemoryBytes: 100,
        sizeEstimator: (value) => value.length * 4,
      );

      // 尝试添加一个超大条目
      cache.set('large', List.generate(100, (i) => i)); // ~400 bytes

      // 不应该被缓存
      expect(cache.get('large'), isNull);
    });

    test('reports memory utilization correctly', () {
      final cache = SizedSmartCache<String, List<int>>(
        maxSize: 100,
        maxMemoryBytes: 1000,
        sizeEstimator: (value) => value.length * 4,
      );

      cache.set('key1', List.generate(50, (i) => i)); // ~200 bytes

      expect(cache.memoryUtilization, closeTo(0.2, 0.05));
    });
  });
}
