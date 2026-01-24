import 'package:isar/isar.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

part 'cached_statistics_model.g.dart';

/// Isar collection model for caching statistics data
///
/// This stores serialized statistics data locally for offline access
/// and faster loading. Supports TTL-based expiration.
@collection
class CachedStatisticsModel {
  /// Unnamed constructor required by Isar
  CachedStatisticsModel();

  /// Auto-incrementing ID
  Id id = Isar.autoIncrement;

  /// Unique cache key (combination of type + period + dates)
  @Index(unique: true)
  late String cacheKey;

  /// Statistics type (focus, agent, capsule, learning)
  @Enumerated(EnumType.name)
  late StatisticsType type;

  /// Time period for this cached data
  @Enumerated(EnumType.name)
  late StatisticsPeriod period;

  /// Start time of the period
  late DateTime periodStart;

  /// End time of the period
  late DateTime periodEnd;

  /// Serialized JSON data of the statistics entity
  late List<int> jsonData;

  /// When this cache was created
  @Index()
  late DateTime createdAt;

  /// When this cache was last accessed (for LRU eviction)
  @Index()
  late DateTime lastAccessedAt;

  /// Time-to-live in seconds (null = never expires)
  int? ttlSeconds;

  /// Priority hint for cache eviction (higher = less likely to evict)
  int priority = 0;

  /// Whether this data was fully synced with server
  late bool isFullySynced;

  /// Metadata (e.g., API version, data hash)
  String? metadata;

  /// Check if this cache entry is expired
  bool isExpired() {
    if (ttlSeconds == null) return false;
    final age = DateTime.now().difference(createdAt).inSeconds;
    return age > ttlSeconds!;
  }

  /// Get cache age in seconds
  int get ageSeconds => DateTime.now().difference(createdAt).inSeconds;

  /// Update last accessed time
  void touch() {
    lastAccessedAt = DateTime.now();
  }

  /// Get the data size in bytes
  int get dataSize => jsonData.length;

  /// Generate a cache key for a statistics query
  static String generateKey({
    required StatisticsType type,
    required StatisticsPeriod period,
    DateTime? customStart,
    DateTime? customEnd,
    String? suffix,
  }) {
    final buffer = StringBuffer();
    buffer.write(type.name);
    buffer.write('_');
    buffer.write(period.name);

    if (customStart != null) {
      buffer.write('_${customStart.millisecondsSinceEpoch}');
    }
    if (customEnd != null) {
      buffer.write('_${customEnd.millisecondsSinceEpoch}');
    }
    if (suffix != null) {
      buffer.write('_$suffix');
    }

    return buffer.toString();
  }

  /// Create from statistics entity
  factory CachedStatisticsModel.fromEntity(
    StatisticsEntity entity, {
    required List<int> jsonData,
    int? ttlSeconds,
    int priority = 0,
    String? metadata,
  }) {
    final now = DateTime.now();

    return CachedStatisticsModel()
      ..cacheKey = generateKey(
        type: entity.type,
        period: entity.period,
      )
      ..type = entity.type
      ..period = entity.period
      ..periodStart = entity.period.getStartTime()
      ..periodEnd = entity.period.getEndTime()
      ..jsonData = jsonData
      ..createdAt = now
      ..lastAccessedAt = now
      ..ttlSeconds = ttlSeconds
      ..priority = priority
      ..isFullySynced = !entity.isFromCache
      ..metadata = metadata;
  }

  /// Copy with
  CachedStatisticsModel copyWith({
    String? cacheKey,
    StatisticsType? type,
    StatisticsPeriod? period,
    DateTime? periodStart,
    DateTime? periodEnd,
    List<int>? jsonData,
    DateTime? createdAt,
    DateTime? lastAccessedAt,
    int? ttlSeconds,
    int? priority,
    bool? isFullySynced,
    String? metadata,
  }) {
    final model = CachedStatisticsModel()
      ..cacheKey = cacheKey ?? this.cacheKey
      ..type = type ?? this.type
      ..period = period ?? this.period
      ..periodStart = periodStart ?? this.periodStart
      ..periodEnd = periodEnd ?? this.periodEnd
      ..jsonData = jsonData ?? this.jsonData
      ..createdAt = createdAt ?? this.createdAt
      ..lastAccessedAt = lastAccessedAt ?? this.lastAccessedAt
      ..ttlSeconds = ttlSeconds ?? this.ttlSeconds
      ..priority = priority ?? this.priority
      ..isFullySynced = isFullySynced ?? this.isFullySynced
      ..metadata = metadata ?? this.metadata;

    model.id = id;
    return model;
  }
}

/// Cache statistics for monitoring
class CacheStatistics {
  /// Total number of entries
  final int totalEntries;

  /// Total size in bytes
  final int totalSizeBytes;

  /// Number of expired entries
  final int expiredEntries;

  /// Number of entries by type
  final Map<StatisticsType, int> entriesByType;

  const CacheStatistics({
    required this.totalEntries,
    required this.totalSizeBytes,
    required this.expiredEntries,
    required this.entriesByType,
  });

  /// Get total size in human readable format
  String get totalSizeHuman {
    if (totalSizeBytes < 1024) return '${totalSizeBytes}B';
    if (totalSizeBytes < 1024 * 1024) {
      return '${(totalSizeBytes / 1024).toStringAsFixed(1)}KB';
    }
    return '${(totalSizeBytes / (1024 * 1024)).toStringAsFixed(1)}MB';
  }

  /// Calculate hit rate (hits / total requests)
  double calculateHitRate({required int totalRequests}) {
    if (totalRequests == 0) return 0.0;
    final hits = totalEntries - expiredEntries;
    return hits / totalRequests;
  }
}

/// Cache priority levels
class CachePriority {
  /// High priority - rarely evict
  static const int high = 100;

  /// Normal priority - default
  static const int normal = 50;

  /// Low priority - evict first
  static const int low = 10;
}
