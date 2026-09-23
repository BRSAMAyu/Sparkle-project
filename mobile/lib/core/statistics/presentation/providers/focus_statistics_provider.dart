import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_timeouts.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/statistics/data/statistics_data.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';
import 'package:sparkle/core/statistics/presentation/providers/statistics_provider.dart';

part 'focus_statistics_provider.g.dart';

/// Focus statistics entity
///
/// Field semantics follow the backend `/focus/stats*` aggregations over
/// completed `focus_sessions` rows (B-02 lineage INV-02). Fields with no
/// real data source are `null` — never a fabricated constant.
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
  /// (server: `total_minutes`, or the sum of heatmap minutes for year/custom)
  final int totalMinutes;

  /// Number of completed focus sessions in the period.
  /// Null when the serving endpoint provides minutes only (heatmap path).
  final int? totalSessions;

  /// Average session duration in minutes.
  /// Null when not derivable from the serving endpoint.
  final double? averageSessionDuration;

  /// Longest single session in minutes. Null: no endpoint exposes it.
  final int? longestSession;

  /// Consecutive focused days ending today
  /// (server: `streak_days`, or derived from heatmap minutes)
  final int? currentStreak;

  /// Daily breakdown data. [DailyFocusData.sessions] is null when the
  /// serving endpoint provides minutes only.
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
    this.sessions,
  });
  final DateTime date;
  final int minutes;

  /// Sessions completed on this day. Null when the serving endpoint
  /// provides minutes only (heatmap-derived days).
  final int? sessions;
}

/// Repository for focus statistics.
///
/// Data sources (all real aggregations over completed `focus_sessions`):
/// - today  → `GET /focus/stats` (+ `GET /focus/stats/heatmap?days=60` for
///   the streak window)
/// - week   → `GET /focus/stats/weekly`
/// - month  → `GET /focus/stats/monthly`
/// - year/custom → `GET /focus/stats/heatmap?days=<window>` (minutes only;
///   session-dependent fields stay null)
///
/// No client-side fallback exists: transport failures propagate (D-04).
class FocusStatsRepository extends HybridStatisticsRepository<FocusStatisticsData> {
  FocusStatsRepository({required super.database, super.cacheConfig, Dio? dio})
      : dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: ApiEndpoints.baseUrl,
                // N37 单一事实源：core/network/api_timeouts.dart（数值守恒 10s/30s）。
                connectTimeout: ApiTimeouts.defaultConnectTimeout,
                receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
              ),
            );

  /// HTTP client used for statistics fetches. Production wiring passes the
  /// shared authenticated client (`ApiClient.dio`); tests inject a stub.
  final Dio dio;

  /// Lookback window (days) used to derive the current streak from the
  /// heatmap when the period endpoint does not report it.
  static const int _streakLookbackDays = 60;

  @override
  StatisticsType get type => StatisticsType.focus;

  @override
  Future<FocusStatisticsData> fetchFromApi(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    switch (period) {
      case StatisticsPeriod.today:
        return _fetchToday(period);
      case StatisticsPeriod.week:
        return _fetchPeriodSummary(period, ApiEndpoints.focusStatsWeekly);
      case StatisticsPeriod.month:
        return _fetchPeriodSummary(period, ApiEndpoints.focusStatsMonthly);
      case StatisticsPeriod.year:
      case StatisticsPeriod.custom:
        return _fetchFromHeatmap(
          period,
          customStart: customStart,
          customEnd: customEnd,
        );
    }
  }

  /// Today: totals from `/focus/stats`; streak from a 60-day heatmap.
  Future<FocusStatisticsData> _fetchToday(StatisticsPeriod period) async {
    final statsResponse = await dio.get<dynamic>(ApiEndpoints.focusStats);
    final stats = ApiResponseParser.unwrapMap(
      statsResponse.data,
      action: 'fetchFocusTodayStats',
    );
    final heatmapResponse = await dio.get<dynamic>(
      ApiEndpoints.focusStatsHeatmap,
      queryParameters: <String, dynamic>{'days': _streakLookbackDays},
    );
    final heatmap = ApiResponseParser.unwrapMap(
      heatmapResponse.data,
      action: 'fetchFocusTodayHeatmap',
    );

    final totalMinutes = (stats['total_minutes'] as num?)?.toInt() ?? 0;
    final totalSessions = (stats['pomodoro_count'] as num?)?.toInt() ?? 0;
    final today = DateTime.now();
    final todayKey = _dayKey(today);
    final todayMinutes = (heatmap[todayKey] as num?)?.toInt() ?? totalMinutes;

    final now = DateTime.now();
    return FocusStatisticsData(
      id: 'focus_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalMinutes: totalMinutes,
      totalSessions: totalSessions,
      averageSessionDuration: totalSessions > 0
          ? totalMinutes / totalSessions
          : null,
      longestSession: null, // no real source
      currentStreak: _deriveStreakFromHeatmap(heatmap),
      dailyData: [
        DailyFocusData(
          date: DateTime(today.year, today.month, today.day),
          minutes: todayMinutes,
          sessions: totalSessions,
        ),
      ],
    );
  }

  /// Week/month: full summary from the period endpoint.
  Future<FocusStatisticsData> _fetchPeriodSummary(
    StatisticsPeriod period,
    String path,
  ) async {
    final response = await dio.get<dynamic>(path);
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchFocusPeriodStats',
    );

    final totalMinutes = (payload['total_minutes'] as num?)?.toInt() ?? 0;
    final totalSessions = (payload['session_count'] as num?)?.toInt() ?? 0;
    final dailyBreakdown =
        (payload['daily_breakdown'] as Map?)?.cast<String, dynamic>() ?? {};

    final now = DateTime.now();
    return FocusStatisticsData(
      id: 'focus_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalMinutes: totalMinutes,
      totalSessions: totalSessions,
      averageSessionDuration:
          (payload['avg_duration'] as num?)?.toDouble() ?? 0.0,
      longestSession: null, // no real source
      currentStreak: (payload['streak_days'] as num?)?.toInt(),
      dailyData: [
        for (final entry in dailyBreakdown.entries)
          DailyFocusData(
            date: DateTime.parse(entry.key),
            // per-day session count not exposed by endpoint (defaults to
            // null = unknown)
            minutes: (entry.value as num?)?.toInt() ?? 0,
          ),
      ]..sort((a, b) => a.date.compareTo(b.date)),
    );
  }

  /// Year/custom: minutes-only heatmap aggregation; session-dependent
  /// fields stay null instead of being invented.
  Future<FocusStatisticsData> _fetchFromHeatmap(
    StatisticsPeriod period, {
    DateTime? customStart,
    DateTime? customEnd,
  }) async {
    final days =
        period.windowDays(customStart: customStart, customEnd: customEnd);
    final response = await dio.get<dynamic>(
      ApiEndpoints.focusStatsHeatmap,
      queryParameters: <String, dynamic>{'days': days},
    );
    final heatmap = ApiResponseParser.unwrapMap(
      response.data,
      action: 'fetchFocusHeatmap',
    );

    final totalMinutes = heatmap.values
        .map((value) => (value as num?)?.toInt() ?? 0)
        .fold<int>(0, (sum, minutes) => sum + minutes);

    final now = DateTime.now();
    return FocusStatisticsData(
      id: 'focus_${period.name}_${now.millisecondsSinceEpoch}',
      period: period,
      lastRefreshedAt: now,
      isFromCache: false,
      totalMinutes: totalMinutes,
      totalSessions: null, // heatmap carries minutes only
      averageSessionDuration: null,
      longestSession: null,
      currentStreak: _deriveStreakFromHeatmap(heatmap),
      dailyData: [
        for (final entry in heatmap.entries)
          DailyFocusData(
            date: DateTime.parse(entry.key),
            minutes: (entry.value as num?)?.toInt() ?? 0,
          ),
      ]..sort((a, b) => a.date.compareTo(b.date)),
    );
  }

  /// Count consecutive days with focused minutes, ending today.
  ///
  /// NOT semantically equivalent to the server-side streak: sessions are
  /// stored as local wall-clock naive and the backend aggregates naive-UTC,
  /// so UTC+8 morning sessions (00:00–08:00) can be excluded by the heatmap
  /// upper bound and under-report the streak. Must be resolved before this
  /// module gains UI consumers (D-04 follow-up).
  static int _deriveStreakFromHeatmap(Map<String, dynamic> heatmap) {
    var streak = 0;
    var day = DateTime.now();
    while (streak < 365) {
      final minutes = (heatmap[_dayKey(day)] as num?)?.toInt() ?? 0;
      if (minutes <= 0) break;
      streak++;
      day = day.subtract(const Duration(days: 1));
    }
    return streak;
  }

  static String _dayKey(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }

  @override
  FocusStatisticsData deserializeEntity(Map<String, dynamic> json) =>
      FocusStatisticsData(
        id: json['id'] as String,
        period: StatisticsPeriodExt.fromCode(json['period'] as String),
        lastRefreshedAt: DateTime.parse(json['lastRefreshedAt'] as String),
        isFromCache: json['isFromCache'] as bool,
        totalMinutes: json['totalMinutes'] as int,
        totalSessions: json['totalSessions'] as int?,
        averageSessionDuration: (json['averageSessionDuration'] as num?)?.toDouble(),
        longestSession: json['longestSession'] as int?,
        currentStreak: json['currentStreak'] as int?,
        dailyData: (json['dailyData'] as List?)
                ?.map((e) => DailyFocusData(
                      date: DateTime.parse(e['date'] as String),
                      minutes: e['minutes'] as int,
                      sessions: e['sessions'] as int?,
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

  @override
  FocusStatisticsData markFromCache(FocusStatisticsData entity) =>
      entity.isFromCache ? entity : entity.copyWith(isFromCache: true);
}

/// Provider for focus statistics repository
@riverpod
FocusStatsRepository focusStatsRepository(FocusStatsRepositoryRef ref) {
  final database = ref.watch(localDatabaseProvider);
  return FocusStatsRepository(
    database: database,
    // Shared authenticated transport (auth/retry/logging/pinning stack).
    dio: ref.watch(apiClientProvider).dio,
  );
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
    // Keep the last-known-real snapshot across the reload so an offline
    // reload can display "data as of <lastRefreshedAt>" (D-04).
    final previous = state;
    state = StatisticsState<FocusStatisticsData>.loading(period: period);

    final repository = ref.read(focusStatsRepositoryProvider);
    try {
      final data = await repository.getStatistics(
        period,
        forceRefresh: forceRefresh,
      );
      state = state.withData(data, newPeriod: period);
    } catch (e) {
      state = previous.withError('Failed to load: $e');
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
