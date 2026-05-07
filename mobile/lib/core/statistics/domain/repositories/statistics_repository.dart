import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_data_point.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_entity.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_period.dart';

/// Error types for statistics operations
enum StatisticsError {
  /// Network request failed
  networkFailed,

  /// Data parsing failed
  parseFailed,

  /// Cache not found
  cacheMiss,

  /// Cache was stale/expired
  cacheStale,

  /// Permission denied
  forbidden,

  /// Rate limited
  rateLimited,

  /// Unknown error
  unknown,
}

/// Generic statistics repository interface
///
/// All concrete statistics repositories (Focus, Agent, Capsule)
/// should implement this interface for consistent behavior.
abstract class StatisticsRepository<T extends StatisticsEntity> {
  /// The type of statistics this repository handles
  StatisticsType get type;

  /// Get statistics for a specific time period
  ///
  /// [forceRefresh] - If true, bypass cache and fetch from API
  /// [ttlSeconds] - Cache time-to-live for cached results
  Future<T> getStatistics(
    StatisticsPeriod period, {
    bool forceRefresh = false,
    int ttlSeconds = 300, // 5 minutes default
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Get time series data for charting
  ///
  /// [aggregation] - How to aggregate data points
  /// [limit] - Maximum number of data points to return
  Future<List<StatisticsDataPoint>> getTimeSeriesData(
    StatisticsPeriod period, {
    StatisticsAggregation aggregation = StatisticsAggregation.daily,
    int? limit,
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Get overview metrics for quick display
  ///
  /// Returns a map of metric names to values
  Future<Map<String, double>> getOverviewMetrics(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Clear all cached data for this statistics type
  Future<void> clearCache();

  /// Preload statistics data for a period
  ///
  /// Useful for background loading before user navigates to a screen
  Future<void> preload(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Check if cached data is available and fresh
  ///
  /// Returns true if cache exists and is within TTL
  Future<bool> isCacheAvailable(
    StatisticsPeriod period, {
    int ttlSeconds = 300,
    DateTime? customStart,
    DateTime? customEnd,
  });

  /// Stream of statistics updates for real-time UI updates
  ///
  /// Emits new values whenever statistics change
  Stream<T> watchStatistics(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  });
}

/// Summary statistics for quick overview
class StatisticsSummary {

  const StatisticsSummary({
    required this.total,
    required this.average,
    required this.maximum,
    required this.minimum,
    required this.trend, this.changePercentage,
  });

  /// Create summary from a list of values
  factory StatisticsSummary.fromValues(
    List<double> values, {
    double? previousTotal,
  }) {
    if (values.isEmpty) {
      return const StatisticsSummary(
        total: 0,
        average: 0,
        maximum: 0,
        minimum: 0,
        trend: StatisticsTrend.stable,
      );
    }

    final total = values.reduce((a, b) => a + b);
    final average = total / values.length;
    final maximum = values.reduce((a, b) => a > b ? a : b);
    final minimum = values.reduce((a, b) => a < b ? a : b);

    double? changePercentage;
    var trend = StatisticsTrend.stable;

    if (previousTotal != null && previousTotal > 0) {
      changePercentage = ((total - previousTotal) / previousTotal) * 100;
      if (changePercentage > 5) {
        trend = StatisticsTrend.up;
      } else if (changePercentage < -5) {
        trend = StatisticsTrend.down;
      }
    }

    return StatisticsSummary(
      total: total,
      average: average,
      maximum: maximum,
      minimum: minimum,
      changePercentage: changePercentage,
      trend: trend,
    );
  }
  /// Total count/sum of the primary metric
  final double total;

  /// Average value
  final double average;

  /// Maximum value
  final double maximum;

  /// Minimum value
  final double minimum;

  /// Change from previous period (percentage)
  final double? changePercentage;

  /// Trend direction (up, down, stable)
  final StatisticsTrend trend;

  /// Summary formatted for display
  String formatTotal({int decimalPlaces = 1}) => total.toStringAsFixed(decimalPlaces);

  String formatChange({bool showSign = true}) {
    if (changePercentage == null) return '--';
    final sign = changePercentage! >= 0 ? '+' : '';
    return '$sign${changePercentage!.toStringAsFixed(1)}%';
  }
}

/// Trend direction for summary statistics
enum StatisticsTrend {
  /// Value increased (positive trend)
  up,

  /// Value decreased (negative trend)
  down,

  /// Value remained stable
  stable,
}

/// Extension for StatisticsTrend
extension StatisticsTrendExt on StatisticsTrend {
  String get label {
    final zh = I18nService.instance.isChinese;
    switch (this) {
      case StatisticsTrend.up:
        return zh ? '上升' : 'Up';
      case StatisticsTrend.down:
        return zh ? '下降' : 'Down';
      case StatisticsTrend.stable:
        return zh ? '持平' : 'Stable';
    }
  }

  /// Get an arrow icon representation
  String get arrow {
    switch (this) {
      case StatisticsTrend.up:
        return '↑';
      case StatisticsTrend.down:
        return '↓';
      case StatisticsTrend.stable:
        return '→';
    }
  }

  /// Whether this is a positive trend (context-dependent)
  bool get isPositive => this == StatisticsTrend.up;

  /// Whether this is a negative trend (context-dependent)
  bool get isNegative => this == StatisticsTrend.down;
}
