import 'package:sparkle/core/statistics/domain/entities/statistics_period.dart';

/// Statistics type enumeration
enum StatisticsType {
  /// Focus/Pomodoro session statistics
  focus,

  /// Multi-Agent usage statistics
  agent,

  /// Curiosity capsule statistics
  capsule,

  /// General learning statistics
  learning,
}

/// Base entity interface for all statistics types
///
/// All concrete statistics implementations (Focus, Agent, Capsule, Learning)
/// must extend this interface to ensure consistent behavior across the module.
abstract class StatisticsEntity {
  /// Unique identifier for this statistics snapshot
  String get id;

  /// Type of statistics
  StatisticsType get type;

  /// Time period for this statistics data
  StatisticsPeriod get period;

  /// When this data was last refreshed
  DateTime get lastRefreshedAt;

  /// Whether this data is from cache or fresh from API
  bool get isFromCache;

  /// Cache age in seconds (null if not from cache)
  int? get cacheAge {
    if (!isFromCache) return null;
    return DateTime.now().difference(lastRefreshedAt).inSeconds;
  }

  /// Whether the cache is expired based on the given TTL
  bool isCacheExpired(int ttlSeconds) {
    if (!isFromCache) return false;
    return (cacheAge ?? 0) > ttlSeconds;
  }

  /// Calculate the percentage change from a previous statistics snapshot
  ///
  /// Returns null if:
  /// - [previous] is null
  /// - The types don't match
  /// - The periods don't match
  double? calculateChange(StatisticsEntity? previous) {
    if (previous == null) return null;
    if (previous.type != type) return null;
    if (previous.period != period) return null;

    final currentValue = getPrimaryValue();
    final previousValue = previous.getPrimaryValue();

    if (previousValue == 0) {
      return currentValue > 0 ? 100.0 : 0.0;
    }

    return ((currentValue - previousValue) / previousValue) * 100;
  }

  /// Get the primary numeric value for change calculation
  ///
  /// Each concrete implementation should define what its "primary value" is
  /// (e.g., total minutes for focus, total calls for agents)
  double getPrimaryValue();
}

/// Extension for StatisticsType to provide display names and icons
extension StatisticsTypeExt on StatisticsType {
  /// Display name in Chinese
  String get displayName {
    switch (this) {
      case StatisticsType.focus:
        return '专注';
      case StatisticsType.agent:
        return '智能体';
      case StatisticsType.capsule:
        return '胶囊';
      case StatisticsType.learning:
        return '学习';
    }
  }

  /// English code name for API/serialization
  String get code {
    switch (this) {
      case StatisticsType.focus:
        return 'focus';
      case StatisticsType.agent:
        return 'agent';
      case StatisticsType.capsule:
        return 'capsule';
      case StatisticsType.learning:
        return 'learning';
    }
  }

  /// Parse from string code
  static StatisticsType fromCode(String code) => StatisticsType.values.firstWhere(
      (type) => type.code == code,
      orElse: () => StatisticsType.learning,
    );
}
