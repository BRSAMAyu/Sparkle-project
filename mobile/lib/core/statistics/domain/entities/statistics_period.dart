import 'package:sparkle/l10n/app_localizations.dart';

/// Time period enumeration for statistics queries
enum StatisticsPeriod {
  /// Today's data (00:00 to now)
  today,

  /// This week (Monday to Sunday, or current day to now if today)
  week,

  /// This month (1st to end of month, or current day to now if today)
  month,

  /// This year (Jan 1 to Dec 31, or current day to now if today)
  year,

  /// Custom date range
  custom,
}

/// Extension for StatisticsPeriod to provide time range calculations
extension StatisticsPeriodExt on StatisticsPeriod {
  /// Display label in Chinese
  String get label => localizedLabel(null);

  /// Localized label
  String localizedLabel(AppLocalizations? l10n) {
    switch (this) {
      case StatisticsPeriod.today:
        return l10n?.statisticsPeriodToday ?? 'Today';
      case StatisticsPeriod.week:
        return l10n?.statisticsPeriodWeek ?? 'This Week';
      case StatisticsPeriod.month:
        return l10n?.statisticsPeriodMonth ?? 'This Month';
      case StatisticsPeriod.year:
        return l10n?.statisticsPeriodYear ?? 'This Year';
      case StatisticsPeriod.custom:
        return l10n?.statisticsPeriodCustom ?? 'Custom';
    }
  }

  /// Short label for compact displays
  String get shortLabel => localizedShortLabel(null);

  /// Localized short label
  String localizedShortLabel(AppLocalizations? l10n) {
    return localizedLabel(l10n);
  }

  /// Get the start time for this period
  ///
  /// For [custom] period, [customStart] must be provided
  DateTime getStartTime({DateTime? customStart}) {
    final now = DateTime.now();

    switch (this) {
      case StatisticsPeriod.today:
        return DateTime(now.year, now.month, now.day);

      case StatisticsPeriod.week:
        // Get Monday of the current week
        final dayOfWeek = now.weekday;
        return DateTime(now.year, now.month, now.day).subtract(
          Duration(days: dayOfWeek - 1),
        );

      case StatisticsPeriod.month:
        return DateTime(now.year, now.month);

      case StatisticsPeriod.year:
        return DateTime(now.year);

      case StatisticsPeriod.custom:
        return customStart ??
            DateTime(now.year, now.month, now.day); // Fallback to today
    }
  }

  /// Get the end time for this period
  ///
  /// For [custom] period, [customEnd] must be provided
  DateTime getEndTime({DateTime? customEnd}) {
    final now = DateTime.now();

    switch (this) {
      case StatisticsPeriod.today:
        return DateTime(now.year, now.month, now.day, 23, 59, 59);

      case StatisticsPeriod.week:
        // Get Sunday of the current week
        final dayOfWeek = now.weekday;
        final sunday = DateTime(now.year, now.month, now.day).add(
          Duration(days: 7 - dayOfWeek),
        );
        return DateTime(sunday.year, sunday.month, sunday.day, 23, 59, 59);

      case StatisticsPeriod.month:
        final lastDay = DateTime(now.year, now.month + 1, 0).day;
        return DateTime(now.year, now.month, lastDay, 23, 59, 59);

      case StatisticsPeriod.year:
        return DateTime(now.year, 12, 31, 23, 59, 59);

      case StatisticsPeriod.custom:
        return customEnd ??
            DateTime(now.year, now.month, now.day, 23, 59, 59); // Fallback to today
    }
  }

  /// Get the duration of this period
  Duration getDuration({DateTime? customStart, DateTime? customEnd}) {
    final start = getStartTime(customStart: customStart);
    final end = getEndTime(customEnd: customEnd);
    return end.difference(start);
  }

  /// Check if a given date falls within this period
  bool contains(DateTime date, {DateTime? customStart, DateTime? customEnd}) {
    final start = getStartTime(customStart: customStart);
    final end = getEndTime(customEnd: customEnd);
    return date.isAfter(start.subtract(const Duration(microseconds: 1))) &&
        date.isBefore(end.add(const Duration(microseconds: 1)));
  }

  /// Get the next period (for cycling in UI)
  StatisticsPeriod get next {
    const values = StatisticsPeriod.values;
    final currentIndex = values.indexOf(this);
    final nextIndex = (currentIndex + 1) % (values.length - 1); // Skip custom
    return values[nextIndex];
  }

  /// Get the previous period (for cycling in UI)
  StatisticsPeriod get previous {
    const values = StatisticsPeriod.values;
    final currentIndex = values.indexOf(this);
    final prevIndex = (currentIndex - 1) % (values.length - 1);
    if (prevIndex < 0) return values[values.length - 2]; // Skip custom
    return values[prevIndex];
  }

  /// Parse from string code
  static StatisticsPeriod fromCode(String code) => StatisticsPeriod.values.firstWhere(
      (period) => period.name == code,
      orElse: () => StatisticsPeriod.today,
    );
}

/// Data class for custom date range
class StatisticsCustomPeriod {

  const StatisticsCustomPeriod({
    required this.start,
    required this.end,
  });
  final DateTime start;
  final DateTime end;

  /// Get the period type
  StatisticsPeriod get period => StatisticsPeriod.custom;

  /// Get the duration
  Duration get duration => end.difference(start);

  /// Validate that the range is valid (end > start)
  bool get isValid => end.isAfter(start);

  /// Copy with modified values
  StatisticsCustomPeriod copyWith({
    DateTime? start,
    DateTime? end,
  }) => StatisticsCustomPeriod(
      start: start ?? this.start,
      end: end ?? this.end,
    );
}
