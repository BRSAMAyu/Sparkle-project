import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'focus_statistics_provider.g.dart';

/// Focus statistics entity
class FocusStatisticsData extends StatisticsEntity {

  FocusStatisticsData({
    required this.id,
    required this.period,
    required this.lastRefreshedAt,
    required this.isFromCache,
    required this.totalMinutes,
    required this.totalSessions,
    required this.averageSessionDuration,
    required this.longestSession,
    required this.currentStreak,
    required this.dailyData,
  });
  @override
  final String id;

  @override
  final StatisticsType type = StatisticsType.focus;

  @override
  final StatisticsPeriod period;

  @override
  final DateTime lastRefreshedAt;

  @override
  final bool isFromCache;

  /// Total focused minutes in the period
  final int totalMinutes;

  /// Total number of sessions
  final int totalSessions;

  /// Average session duration in minutes
  final double averageSessionDuration;

  /// Longest session in minutes
  final int longestSession;

  /// Current streak count
  final int currentStreak;

  /// Daily breakdown data
  final List<DailyFocusData> dailyData;

  @override
  double getPrimaryValue() => totalMinutes.toDouble();

  /// Calculate change from previous period
  @override
  double? calculateChange(StatisticsEntity? previous) {
    if (previous == null || previous is! FocusStatisticsData) {
      return null;
    }
    if (previous.totalMinutes == 0) {
      return totalMinutes > 0 ? 100.0 : 0.0;
    }
    return ((totalMinutes - previous.totalMinutes) / previous.totalMinutes) * 100;
  }

  /// Copy with
  FocusStatisticsData copyWith({
    String? id,
    StatisticsPeriod? period,
    DateTime? lastRefreshedAt,
    bool? isFromCache,
    int? totalMinutes,
    int? totalSessions,
    double? averageSessionDuration,
    int? longestSession,
    int? currentStreak,
    List<DailyFocusData>? dailyData,
  }) => FocusStatisticsData(
      id: id ?? this.id,
      period: period ?? this.period,
      lastRefreshedAt: lastRefreshedAt ?? this.lastRefreshedAt,
      isFromCache: isFromCache ?? this.isFromCache,
      totalMinutes: totalMinutes ?? this.totalMinutes,
      totalSessions: totalSessions ?? this.totalSessions,
      averageSessionDuration: averageSessionDuration ?? this.averageSessionDuration,
      longestSession: longestSession ?? this.longestSession,
      currentStreak: currentStreak ?? this.currentStreak,
      dailyData: dailyData ?? this.dailyData,
    );
}

/// Daily focus data for charts
class DailyFocusData {

  const DailyFocusData({
    required this.date,
    required this.minutes,
    required this.sessions,
  });
  final DateTime date;
  final int minutes;
  final int sessions;
}

/// Repository for focus statistics
class FocusStatsRepository extends HybridStatisticsRepository<FocusStatisticsData> {
  FocusStatsRepository({required super.database, super.cacheConfig});

  @override
  StatisticsType get type => StatisticsType.focus;

  @override
  Future<FocusStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    // This would call the actual API
    // For now, return mock data
    final now = DateTime.now();
    final mockData = FocusStatisticsData(
      id: 'focus_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalMinutes: _generateMockTotal(period),
      totalSessions: _generateMockSessions(period),
      averageSessionDuration: 25.5,
      longestSession: 90,
      currentStreak: 5,
      dailyData: _generateMockDailyData(period),
    );
    return mockData;
  }

  @override
  FocusStatisticsData deserializeEntity(Map<String, dynamic> json) => FocusStatisticsData(
      id: json['id'] as String,
      period: StatisticsPeriodExt.fromCode(json['period'] as String),
      lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
      isFromCache: json['isFromCache'] as bool,
      totalMinutes: json['totalMinutes'] as int,
      totalSessions: json['totalSessions'] as int,
      averageSessionDuration: json['averageSessionDuration'] as double,
      longestSession: json['longestSession'] as int,
      currentStreak: json['currentStreak'] as int,
      dailyData: (json['dailyData'] as List?)
              ?.map((e) => DailyFocusData(
                    date: DateTime.parse(e['date'] as String),
                    minutes: e['minutes'] as int,
                    sessions: e['sessions'] as int,
                  ),)
              .toList() ??
          [],
    );

  @override
  Map<String, dynamic> serializeEntity(FocusStatisticsData entity) => {
      'id': entity.id,
      'type': entity.type.code,
      'period': entity.period.name,
      'lastRefreshedAt': entity.lastRefreshedAt.toIso8601String(),
      'isFromCache': entity.isFromCache,
      'totalMinutes': entity.totalMinutes,
      'totalSessions': entity.totalSessions,
      'averageSessionDuration': entity.averageSessionDuration,
      'longestSession': entity.longestSession,
      'currentStreak': entity.currentStreak,
      'dailyData': entity.dailyData
          .map((d) => {
                'date': d.date.toIso8601String(),
                'minutes': d.minutes,
                'sessions': d.sessions,
              },)
          .toList(),
    };

  int _generateMockTotal(StatisticsPeriod period) {
    switch (period) {
      case StatisticsPeriod.today:
        return 120;
      case StatisticsPeriod.week:
        return 600;
      case StatisticsPeriod.month:
        return 2400;
      case StatisticsPeriod.year:
        return 28800;
      case StatisticsPeriod.custom:
        return 300;
    }
  }

  int _generateMockSessions(StatisticsPeriod period) {
    switch (period) {
      case StatisticsPeriod.today:
        return 4;
      case StatisticsPeriod.week:
        return 20;
      case StatisticsPeriod.month:
        return 80;
      case StatisticsPeriod.year:
        return 960;
      case StatisticsPeriod.custom:
        return 10;
    }
  }

  List<DailyFocusData> _generateMockDailyData(StatisticsPeriod period) {
    final start = period.getStartTime();
    final end = period.getEndTime();

    final days = end.difference(start).inDays + 1;
    final limitedDays = days > 90 ? 90 : days;

    return List.generate(limitedDays, (index) {
      final date = start.add(Duration(days: index));
      return DailyFocusData(
        date: date,
        minutes: 20 + (index % 5) * 15,
        sessions: 1 + (index % 3),
      );
    });
  }
}

/// Provider for focus statistics repository
@riverpod
FocusStatsRepository focusStatsRepository(FocusStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return FocusStatsRepository(database: database);
}

/// Provider for focus statistics state
@riverpod
class FocusStatistics extends _$FocusStatistics {
  @override
  StatisticsState<FocusStatisticsData> build() => const StatisticsState.initial();

  /// Load focus statistics for a period
  Future<void> load(
    StatisticsPeriod period, {
    bool forceRefresh = false,
  }) async {
    state = StatisticsState<FocusStatisticsData>.loading(period: period);

    final repository = ref.read(focusStatsRepositoryProvider);
    try {
      final data = await repository.getStatistics(
        period,
        forceRefresh: forceRefresh,
      );
      state = state.withData(data, newPeriod: period);
    } catch (e) {
      state = state.withError(I18nService.instance.isChinese ? '加载失败: $e' : 'Failed to load: $e');
    }
  }

  /// Refresh current statistics
  Future<void> refresh() async {
    final period = state.lastPeriod ?? StatisticsPeriod.today;
    await load(period, forceRefresh: true);
  }

  /// Clear cache
  Future<void> clearCache() async {
    final repository = ref.read(focusStatsRepositoryProvider);
    await repository.clearCache();
    state = const StatisticsState.initial();
  }
}
