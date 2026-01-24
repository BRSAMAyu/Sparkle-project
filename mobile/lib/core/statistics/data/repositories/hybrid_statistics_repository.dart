import 'dart:convert';
import 'package:isar/isar.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/models/cached_statistics_model.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

part 'hybrid_statistics_repository.g.dart';

/// Cache tier for the hybrid repository
enum CacheTier {
  /// Hot data - in-memory cache (fastest, ~5min TTL)
  hot,

  /// Warm data - Isar local storage (fast, ~24hr TTL)
  warm,

  /// Cold data - API only (slowest, no caching)
  cold,
}

/// Cache configuration for the hybrid repository
class HybridCacheConfig {
  /// Hot cache TTL in seconds (default: 5 minutes)
  final int hotTtlSeconds;

  /// Warm cache TTL in seconds (default: 24 hours)
  final int warmTtlSeconds;

  /// Maximum number of entries in hot cache
  final int hotCacheMaxEntries;

  /// Maximum size of warm cache in bytes (default: 50MB)
  final int warmCacheMaxSizeBytes;

  /// Whether to enable hot cache
  final bool enableHotCache;

  /// Whether to enable warm cache
  final bool enableWarmCache;

  const HybridCacheConfig({
    this.hotTtlSeconds = 300, // 5 minutes
    this.warmTtlSeconds = 86400, // 24 hours
    this.hotCacheMaxEntries = 20,
    this.warmCacheMaxSizeBytes = 50 * 1024 * 1024, // 50MB
    this.enableHotCache = true,
    this.enableWarmCache = true,
  });
}

/// Base class for hybrid statistics repositories
///
/// Implements a three-tier caching strategy:
/// - Hot: In-memory cache (Riverpod asyncValue)
/// - Warm: Isar local storage
/// - Cold: API fetch on demand
///
/// Subclasses must implement [fetchFromApi] to provide data source.
abstract class HybridStatisticsRepository<T extends StatisticsEntity>
    implements StatisticsRepository<T> {
  /// Reference to the local database
  final LocalDatabase database;

  /// Cache configuration
  final HybridCacheConfig cacheConfig;

  /// Hot cache (in-memory)
  final Map<String, _CacheEntry<T>> _hotCache = {};

  /// Hot cache access timestamps (for LRU eviction)
  final Map<String, DateTime> _hotCacheAccess = {};

  HybridStatisticsRepository({
    required this.database,
    HybridCacheConfig? cacheConfig,
  }) : cacheConfig = cacheConfig ?? const HybridCacheConfig();

  // ============================================
  // ABSTRACT METHODS (must implement)
  // ============================================

  /// Fetch statistics from the API
  ///
  /// Subclasses must implement this to provide the actual data source.
  Future<T> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Deserialize JSON data into the entity type
  ///
  /// Subclasses must implement this to parse cached data.
  T deserializeEntity(Map<String, dynamic> json);

  /// Serialize entity to JSON
  ///
  /// Subclasses must implement this for caching.
  Map<String, dynamic> serializeEntity(T entity);

  // ============================================
  // INTERFACE IMPLEMENTATION
  // ============================================

  @override
  StatisticsType get type;

  @override
  Future<T> getStatistics(
    StatisticsPeriod period, {
    bool forceRefresh = false,
    int ttlSeconds = 300,
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final cacheKey = CachedStatisticsModel.generateKey(
      type: type,
      period: period,
      customStart: customStart,
      customEnd: customEnd,
    );

    // Try hot cache first (if not forcing refresh)
    if (!forceRefresh && cacheConfig.enableHotCache) {
      final hotResult = _getFromHotCache(cacheKey);
      if (hotResult != null && !hotResult.isExpired(cacheConfig.hotTtlSeconds)) {
        // Update last accessed time
        _hotCacheAccess[cacheKey] = DateTime.now();
        return hotResult.entity;
      }
    }

    // Try warm cache (Isar)
    if (!forceRefresh && cacheConfig.enableWarmCache) {
      final warmResult = await _getFromWarmCache(cacheKey);
      if (warmResult != null) {
        final age = DateTime.now().difference(warmResult.createdAt).inSeconds;
        final isExpired = warmResult.ttlSeconds != null && age > warmResult.ttlSeconds!;
        if (!isExpired) {
          final entity = _deserializeAndTrack(warmResult, cacheKey);
          return entity;
        }
      }
    }

    // Fetch from API (cold)
    try {
      final entity = await fetchFromApi(
        period,
        customStart: customStart,
        customEnd: customEnd,
      );

      // Store in hot cache
      _putInHotCache(cacheKey, entity);

      // Store in warm cache
      await _putInWarmCache(cacheKey, entity);

      return entity;
    } catch (e) {
      // If API fails, try to return stale cache as fallback
      final staleResult = await _getStaleCache(cacheKey);
      if (staleResult != null) {
        return staleResult;
      }
      rethrow;
    }
  }

  @override
  Future<List<StatisticsDataPoint>> getTimeSeriesData(
    StatisticsPeriod period, {
    StatisticsAggregation aggregation = StatisticsAggregation.daily,
    int? limit,
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    // Default implementation: return empty list
    // Subclasses should override this with actual data
    return [];
  }

  @override
  Future<Map<String, double>> getOverviewMetrics(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    // Default implementation: return empty map
    // Subclasses should override this with actual metrics
    return {};
  }

  @override
  Future<void> clearCache() async {
    // Clear hot cache
    _hotCache.clear();
    _hotCacheAccess.clear();

    // Clear warm cache for this type
    final cachedStats = await database.cachedStatistics
        .filter()
        .typeEqualTo(type)
        .findAll();

    await database.isar.writeTxn(() async {
      for (final stat in cachedStats) {
        await database.cachedStatistics.delete(stat.id);
      }
    });
  }

  @override
  Future<void> preload(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    // Silent preload - don't notify listeners
    await getStatistics(
      period,
      customStart: customStart,
      customEnd: customEnd,
    );
  }

  @override
  Future<bool> isCacheAvailable(
    StatisticsPeriod period, {
    int ttlSeconds = 300,
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final cacheKey = CachedStatisticsModel.generateKey(
      type: type,
      period: period,
      customStart: customStart,
      customEnd: customEnd,
    );

    // Check hot cache
    if (cacheConfig.enableHotCache) {
      final hotEntry = _hotCache[cacheKey];
      if (hotEntry != null && !hotEntry.isExpired(ttlSeconds)) {
        return true;
      }
    }

    // Check warm cache
    if (cacheConfig.enableWarmCache) {
      final cached = await database.cachedStatistics
          .filter()
          .cacheKeyEqualTo(cacheKey)
          .findFirst();
      if (cached != null && !cached.isExpired()) {
        return true;
      }
    }

    return false;
  }

  @override
  Stream<T> watchStatistics(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async* {
    // This is a placeholder implementation
    // In a real app, this would watch a database query or stream
    final result = await getStatistics(
      period,
      customStart: customStart,
      customEnd: customEnd,
    );
    yield result;
  }

  // ============================================
  // PRIVATE HELPER METHODS
  // ============================================

  /// Get data from hot cache
  _CacheEntry<T>? _getFromHotCache(String key) {
    _hotCacheAccess[key] = DateTime.now();
    return _hotCache[key];
  }

  /// Put data in hot cache
  void _putInHotCache(String key, T entity) {
    _hotCache[key] = _CacheEntry(entity: entity, cachedAt: DateTime.now());
    _hotCacheAccess[key] = DateTime.now();

    // Evict oldest if over limit
    if (_hotCache.length > cacheConfig.hotCacheMaxEntries) {
      _evictOldestHotCacheEntry();
    }
  }

  /// Evict the oldest entry from hot cache (LRU)
  void _evictOldestHotCacheEntry() {
    if (_hotCacheAccess.isEmpty) return;

    final oldestKey = _hotCacheAccess.entries
        .reduce((a, b) => a.value.isBefore(b.value) ? a : b)
        .key;

    _hotCache.remove(oldestKey);
    _hotCacheAccess.remove(oldestKey);
  }

  /// Get data from warm cache (Isar)
  Future<CachedStatisticsModel?> _getFromWarmCache(String key) async {
    final cached = await database.cachedStatistics
        .filter()
        .cacheKeyEqualTo(key)
        .findFirst();
    if (cached != null) {
      cached.touch();
      await database.isar.writeTxn(() async {
        await database.cachedStatistics.put(cached);
      });
    }
    return cached;
  }

  /// Put data in warm cache
  Future<void> _putInWarmCache(String key, T entity) async {
    final jsonData = serializeEntity(entity);
    final jsonString = jsonEncode(jsonData);
    final bytes = utf8.encode(jsonString);

    final model = CachedStatisticsModel()
      ..cacheKey = key
      ..type = type
      ..period = entity.period
      ..periodStart = entity.period.getStartTime()
      ..periodEnd = entity.period.getEndTime()
      ..jsonData = bytes
      ..createdAt = DateTime.now()
      ..lastAccessedAt = DateTime.now()
      ..ttlSeconds = cacheConfig.warmTtlSeconds
      ..priority = CachePriority.normal
      ..isFullySynced = !entity.isFromCache;

    await database.isar.writeTxn(() async {
      await database.cachedStatistics.put(model);
    });

    // Check if we need to evict old entries
    await _evictOldWarmCacheEntriesIfNeeded();
  }

  /// Evict old entries from warm cache if size limit exceeded
  Future<void> _evictOldWarmCacheEntriesIfNeeded() async {
    final allEntries = await database.cachedStatistics
        .filter()
        .typeEqualTo(type)
        .findAll();

    final totalSize = allEntries.fold<int>(
      0,
      (int sum, CachedStatisticsModel entry) => sum + entry.dataSize,
    );

    if (totalSize > cacheConfig.warmCacheMaxSizeBytes) {
      // Sort by last accessed time and remove oldest
      allEntries.sort((CachedStatisticsModel a, CachedStatisticsModel b) =>
          a.lastAccessedAt.compareTo(b.lastAccessedAt));

      var currentSize = totalSize;
      int index = 0;

      while (currentSize > cacheConfig.warmCacheMaxSizeBytes * 0.8 &&
          index < allEntries.length) {
        final toRemove = allEntries[index];
        await database.cachedStatistics.delete(toRemove.id);
        currentSize -= toRemove.dataSize;
        index++;
      }
    }
  }

  /// Get stale cache as fallback when API fails
  Future<T?> _getStaleCache(String key) async {
    // Try warm cache even if expired
    final warm = await _getFromWarmCache(key);
    if (warm != null) {
      return _deserializeAndTrack(warm, key);
    }

    // Try hot cache even if expired
    final hot = _hotCache[key];
    if (hot != null) {
      return hot.entity;
    }

    return null;
  }

  /// Deserialize cached data and track in hot cache
  T _deserializeAndTrack(CachedStatisticsModel cached, String key) {
    final jsonString = utf8.decode(cached.jsonData);
    final json = jsonDecode(jsonString) as Map<String, dynamic>;
    final entity = deserializeEntity(json);

    // Also store in hot cache for faster next access
    _putInHotCache(key, entity);

    return entity;
  }
}

/// Internal cache entry wrapper
class _CacheEntry<T extends StatisticsEntity> {
  final T entity;
  final DateTime cachedAt;

  _CacheEntry({required this.entity, required this.cachedAt});

  bool isExpired(int ttlSeconds) {
    final age = DateTime.now().difference(cachedAt).inSeconds;
    return age > ttlSeconds;
  }
}

/// Extension for DateTime comparison
extension DateTimeComparison on DateTime {
  bool isBeforeOrSame(DateTime other) =>
      isAtSameMomentAs(other) || isBefore(other);
}

/// Provider for hybrid cache config
@riverpod
HybridCacheConfig hybridCacheConfig(HybridCacheConfigRef ref) {
  return const HybridCacheConfig();
}
