import 'package:flutter/widgets.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

part 'statistics_data_point.freezed.dart';
part 'statistics_data_point.g.dart';

/// A single data point in a time series
///
/// Used for chart rendering where each point represents
/// a value at a specific point in time.
@freezed
class StatisticsDataPoint with _$StatisticsDataPoint {
  const factory StatisticsDataPoint({
    /// The timestamp for this data point
    required DateTime timestamp,

    /// The primary value (e.g., minutes, count, score)
    required double value,

    /// Optional secondary value for dual-axis charts
    double? secondaryValue,

    /// Optional label for this data point (e.g., "Mon", "Jan 1")
    String? label,

    /// Optional metadata (for tooltips, etc.)
    @Default({}) Map<String, dynamic> metadata,
  }) = _StatisticsDataPoint;

  factory StatisticsDataPoint.fromJson(Map<String, dynamic> json) =>
      _$StatisticsDataPointFromJson(json);
}

/// A collection of data points with aggregation metadata
@freezed
class StatisticsDataSeries with _$StatisticsDataSeries {
  const factory StatisticsDataSeries({
    /// Unique identifier for this series
    required String id,

    /// Display name for this series
    required String name,

    /// The data points in chronological order
    required List<StatisticsDataPoint> points, /// Color code for this series (hex or named)
    String? color,

    /// Unit label for values (e.g., "分钟", "次", "分")
    String? unit,

    /// Maximum value in the series
    double? maxValue,

    /// Minimum value in the series
    double? minValue,

    /// Average value across all points
    double? averageValue,

    /// Total/sum of all values
    double? totalValue,
  }) = _StatisticsDataSeries;

  factory StatisticsDataSeries.fromJson(Map<String, dynamic> json) =>
      _$StatisticsDataSeriesFromJson(json);

  const StatisticsDataSeries._();

  /// Get a series with calculated statistics (max, min, avg, total)
  StatisticsDataSeries withCalculatedStats() {
    if (points.isEmpty) return this;

    final values = points.map((p) => p.value).toList();
    final max = values.reduce((a, b) => a > b ? a : b);
    final min = values.reduce((a, b) => a < b ? a : b);
    final total = values.reduce((a, b) => a + b);
    final avg = total / values.length;

    return copyWith(
      maxValue: max,
      minValue: min,
      averageValue: avg,
      totalValue: total,
    );
  }
}

/// Aggregation level for time series data
enum StatisticsAggregation {
  /// No aggregation (raw data points)
  none,

  /// Aggregate by hour
  hourly,

  /// Aggregate by day
  daily,

  /// Aggregate by week
  weekly,

  /// Aggregate by month
  monthly,
}

/// Extension for aggregation helper methods
extension StatisticsAggregationExt on StatisticsAggregation {
  /// Get the label for this aggregation level
  String getLabel(BuildContext context) {
    switch (this) {
      case StatisticsAggregation.none:
        return context.l10n.statisticsAggregationNone;
      case StatisticsAggregation.hourly:
        return context.l10n.statisticsAggregationHourly;
      case StatisticsAggregation.daily:
        return context.l10n.statisticsAggregationDaily;
      case StatisticsAggregation.weekly:
        return context.l10n.statisticsAggregationWeekly;
      case StatisticsAggregation.monthly:
        return context.l10n.statisticsAggregationMonthly;
    }
  }

  /// Truncate a datetime to the start of this aggregation period
  DateTime truncate(DateTime dateTime) {
    switch (this) {
      case StatisticsAggregation.none:
      case StatisticsAggregation.hourly:
        return DateTime(dateTime.year, dateTime.month, dateTime.day, dateTime.hour);
      case StatisticsAggregation.daily:
        return DateTime(dateTime.year, dateTime.month, dateTime.day);
      case StatisticsAggregation.weekly:
        // Get Monday of the week
        final dayOfWeek = dateTime.weekday;
        return DateTime(dateTime.year, dateTime.month, dateTime.day).subtract(
          Duration(days: dayOfWeek - 1),
        );
      case StatisticsAggregation.monthly:
        return DateTime(dateTime.year, dateTime.month);
    }
  }
}
