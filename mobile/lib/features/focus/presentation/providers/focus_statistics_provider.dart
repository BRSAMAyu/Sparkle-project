import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/features/focus/data/models/focus_session_model.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart';
import 'package:sparkle/features/focus/data/repositories/focus_statistics_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';

part 'focus_statistics_provider.g.dart';

/// Statistics view period
enum StatsViewPeriod {
  today,
  week,
  month;

  String label(AppLocalizations l10n) {
    switch (this) {
      case StatsViewPeriod.today:
        return l10n.focusStatsToday;
      case StatsViewPeriod.week:
        return l10n.focusStatsWeek;
      case StatsViewPeriod.month:
        return l10n.focusStatsMonth;
    }
  }
}

/// Focus statistics state
class FocusStatisticsState {
  const FocusStatisticsState({
    this.period = StatsViewPeriod.today,
    this.isLoading = false,
    this.isRefreshing = false,
    this.errorMessage,
    this.todayMinutes = 0,
    this.todaySessionCount = 0,
    this.weeklyData,
    this.monthlyData,
    this.sessionHistory = const [],
    this.heatmapData = const {},
    this.streakDays = 0,
    this.longestStreak = 0,
  });

  final StatsViewPeriod period;
  final bool isLoading;
  final bool isRefreshing;
  final String? errorMessage;
  final int todayMinutes;
  final int todaySessionCount;
  final Map<String, dynamic>? weeklyData;
  final Map<String, dynamic>? monthlyData;
  final List<FocusSessionDetail> sessionHistory;
  final Map<DateTime, double> heatmapData;
  final int streakDays;
  final int longestStreak;

  /// Get formatted today duration (e.g., "2h 35m")
  String get todayFormatted {
    final hours = todayMinutes ~/ 60;
    final minutes = todayMinutes % 60;
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    }
    return '${minutes}m';
  }

  /// Get formatted week total duration
  String get weekTotalFormatted {
    final minutes = weeklyData?['total_minutes'] as int? ?? 0;
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    if (hours > 0) {
      return '${hours}h ${mins}m';
    }
    return '${mins}m';
  }

  /// Get formatted month total duration
  String get monthTotalFormatted {
    final minutes = monthlyData?['total_minutes'] as int? ?? 0;
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    if (hours > 0) {
      return '${hours}h ${mins}m';
    }
    return '${mins}m';
  }

  /// Get daily breakdown for the selected period
  Map<String, int> get dailyBreakdown {
    switch (period) {
      case StatsViewPeriod.today:
        return {};
      case StatsViewPeriod.week:
        return (weeklyData?['daily_breakdown'] as Map<String, dynamic>?)
                ?.cast<String, int>() ??
            {};
      case StatsViewPeriod.month:
        return (monthlyData?['daily_breakdown'] as Map<String, dynamic>?)
                ?.cast<String, int>() ??
            {};
    }
  }

  /// Get focus type distribution for the selected period
  Map<String, int> get focusTypeDistribution {
    switch (period) {
      case StatsViewPeriod.today:
        return {};
      case StatsViewPeriod.week:
        return (weeklyData?['focus_type_distribution'] as Map<String, dynamic>?)
                ?.cast<String, int>() ??
            {};
      case StatsViewPeriod.month:
        return (monthlyData?['focus_type_distribution']
                    as Map<String, dynamic>?)
                ?.cast<String, int>() ??
            {};
    }
  }

  FocusStatisticsState copyWith({
    StatsViewPeriod? period,
    bool? isLoading,
    bool? isRefreshing,
    String? errorMessage,
    int? todayMinutes,
    int? todaySessionCount,
    Map<String, dynamic>? weeklyData,
    Map<String, dynamic>? monthlyData,
    List<FocusSessionDetail>? sessionHistory,
    Map<DateTime, double>? heatmapData,
    int? streakDays,
    int? longestStreak,
  }) =>
      FocusStatisticsState(
        period: period ?? this.period,
        isLoading: isLoading ?? this.isLoading,
        isRefreshing: isRefreshing ?? this.isRefreshing,
        errorMessage: errorMessage ?? this.errorMessage,
        todayMinutes: todayMinutes ?? this.todayMinutes,
        todaySessionCount: todaySessionCount ?? this.todaySessionCount,
        weeklyData: weeklyData ?? this.weeklyData,
        monthlyData: monthlyData ?? this.monthlyData,
        sessionHistory: sessionHistory ?? this.sessionHistory,
        heatmapData: heatmapData ?? this.heatmapData,
        streakDays: streakDays ?? this.streakDays,
        longestStreak: longestStreak ?? this.longestStreak,
      );
}

/// Focus statistics provider
@riverpod
class FocusStatistics extends _$FocusStatistics {
  FocusStatisticsRepository? _localRepo;
  FocusRepository? _apiRepo;

  @override
  FocusStatisticsState build() {
    // Initialize repositories
    final db = ref.read(localDatabaseProvider);
    _localRepo = FocusStatisticsRepository(db.isar);
    _apiRepo = ref.read(focusRepositoryProvider);

    // Get the persisted period
    final persistedPeriod = ref.watch(statsViewPeriodProvider);

    // Load initial data based on persisted period
    switch (persistedPeriod) {
      case StatsViewPeriod.today:
        loadTodayStats();
      case StatsViewPeriod.week:
        loadWeeklyStats();
      case StatsViewPeriod.month:
        loadMonthlyStats();
    }

    return FocusStatisticsState(period: persistedPeriod);
  }

  /// Set the view period
  void setPeriod(StatsViewPeriod newPeriod) {
    // Update the persisted period
    ref.read(statsViewPeriodProvider.notifier).setValue(newPeriod);

    state = state.copyWith(period: newPeriod);

    switch (newPeriod) {
      case StatsViewPeriod.today:
        loadTodayStats();
      case StatsViewPeriod.week:
        loadWeeklyStats();
      case StatsViewPeriod.month:
        loadMonthlyStats();
    }
  }

  /// Load today's statistics
  Future<void> loadTodayStats() async {
    state = state.copyWith(isLoading: true);

    try {
      // Try API first
      try {
        final response = await _apiRepo!.getFocusStats();
        state = state.copyWith(
          isLoading: false,
          todayMinutes: response.totalMinutes,
          todaySessionCount: response.pomodoroCount,
        );
        return;
      } catch (e) {
        debugPrint('API failed, using local data: $e');
      }

      // Fallback to local data
      if (_localRepo != null) {
        final localMinutes = await _localRepo!.getTodayTotalMinutes();
        state = state.copyWith(
          isLoading: false,
          todayMinutes: localMinutes,
          todaySessionCount: 0, // Not tracked locally
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Load weekly statistics
  Future<void> loadWeeklyStats() async {
    state = state.copyWith(isLoading: true);

    try {
      // Try API first
      try {
        final response = await _apiRepo!.getWeeklyStats();
        state = state.copyWith(
          isLoading: false,
          weeklyData: {
            'total_minutes': response.totalMinutes,
            'session_count': response.sessionCount,
            'avg_duration': response.avgDuration,
            'best_day': response.bestDay,
            'daily_breakdown': response.dailyBreakdown,
            'focus_type_distribution': response.focusTypeDistribution,
            'streak_days': response.streakDays,
            'longest_streak': response.longestStreak,
          },
          streakDays: response.streakDays,
          longestStreak: response.longestStreak,
        );
        return;
      } catch (e) {
        debugPrint('API failed, using local data: $e');
      }

      // Fallback to local data
      if (_localRepo != null) {
        final localStats = await _localRepo!.getWeeklyStats();

        state = state.copyWith(
          isLoading: false,
          weeklyData: localStats,
          streakDays: localStats['streak_days'] as int? ?? 0,
          longestStreak: localStats['longest_streak'] as int? ?? 0,
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Load monthly statistics
  Future<void> loadMonthlyStats() async {
    state = state.copyWith(isLoading: true);

    try {
      // Try API first
      try {
        final response = await _apiRepo!.getMonthlyStats();
        state = state.copyWith(
          isLoading: false,
          monthlyData: {
            'total_minutes': response.totalMinutes,
            'session_count': response.sessionCount,
            'avg_duration': response.avgDuration,
            'best_day': response.bestDay,
            'daily_breakdown': response.dailyBreakdown,
            'weekly_breakdown': response.weeklyBreakdown,
            'focus_type_distribution': response.focusTypeDistribution,
            'streak_days': response.streakDays,
            'longest_streak': response.longestStreak,
          },
          streakDays: response.streakDays,
          longestStreak: response.longestStreak,
        );
        return;
      } catch (e) {
        debugPrint('API failed, using local data: $e');
      }

      // Fallback to local data
      if (_localRepo != null) {
        final localStats = await _localRepo!.getMonthlyStats();

        state = state.copyWith(
          isLoading: false,
          monthlyData: localStats,
          streakDays: localStats['streak_days'] as int? ?? 0,
          longestStreak: localStats['longest_streak'] as int? ?? 0,
        );
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  /// Load heatmap data
  Future<void> loadHeatmapData({int days = 90}) async {
    try {
      // Try API first
      try {
        final apiData = await _apiRepo!.getHeatmapData(days: days);
        final heatmapData = <DateTime, double>{};
        for (final entry in apiData.entries) {
          final date = DateTime.parse(entry.key);
          heatmapData[date] = entry.value;
        }
        state = state.copyWith(heatmapData: heatmapData);
        return;
      } catch (e) {
        debugPrint('API heatmap failed, using local data: $e');
      }

      // Fallback to local data
      if (_localRepo != null) {
        final localHeatmap = await _localRepo!.getHeatmapData(days: days);
        state = state.copyWith(heatmapData: localHeatmap);
      }
    } catch (e) {
      debugPrint('Failed to load heatmap data: $e');
    }
  }

  /// Load session history
  Future<void> loadSessionHistory({int limit = 20}) async {
    try {
      // Try API first
      try {
        final response = await _apiRepo!.getSessionHistory(limit: limit);
        state = state.copyWith(sessionHistory: response.sessions);
        return;
      } catch (e) {
        debugPrint('API history failed, using local data: $e');
      }

      // Fallback to local data
      if (_localRepo != null) {
        final localSessions = await _localRepo!.getSessionHistory(limit: limit);
        final details = localSessions
            .map(
              (s) => FocusSessionDetail(
                id: s.id.toString(),
                startTime: s.startTime,
                endTime: s.endTime,
                durationMinutes: s.durationMinutes,
                focusType: s.focusType,
                status: s.status,
                taskId: s.taskId,
                taskTitle: s.taskTitle,
                whiteNoiseType: int.tryParse(s.whiteNoiseType ?? ''),
              ),
            )
            .toList();
        state = state.copyWith(sessionHistory: details);
      }
    } catch (e) {
      debugPrint('Failed to load session history: $e');
    }
  }

  /// Refresh all data
  Future<void> refresh() async {
    state = state.copyWith(isRefreshing: true);

    await Future.wait([
      loadTodayStats(),
      loadWeeklyStats(),
      loadMonthlyStats(),
      loadHeatmapData(),
      loadSessionHistory(),
    ]);

    state = state.copyWith(isRefreshing: false);
  }

  /// Sync unsynced sessions to server
  Future<void> sync() async {
    if (_localRepo == null || _apiRepo == null) return;

    final unsynced = await _localRepo!.getUnsyncedSessions();
    if (unsynced.isEmpty) return;

    for (final session in unsynced) {
      try {
        final response = await _apiRepo!.logFocusSession(
          startTime: session.startTime,
          endTime: session.endTime,
          durationMinutes: session.durationMinutes,
          taskId: session.taskId,
          focusType: session.focusType,
          status: session.status,
          whiteNoiseType: session.whiteNoiseType,
        );
        await _localRepo!.markAsSynced(session.id, response.id);
      } catch (e) {
        await _localRepo!.markSyncFailed(session.id, e.toString());
      }
    }

    // Reload data after sync
    await refresh();
  }

  /// Save a completed focus session locally
  Future<void> saveSession({
    required DateTime startTime,
    required DateTime endTime,
    required int durationMinutes,
    String focusType = 'pomodoro',
    String? taskId,
    String? taskTitle,
    String? whiteNoiseType,
    int interruptionCount = 0,
    int? qualityScore,
  }) async {
    if (_localRepo == null) return;

    final record = FocusSessionRecordExtension.createCompleted(
      startTime: startTime,
      endTime: endTime,
      durationMinutes: durationMinutes,
      focusType: focusType,
      taskId: taskId,
      taskTitle: taskTitle,
      whiteNoiseType: whiteNoiseType,
      interruptionCount: interruptionCount,
      qualityScore: qualityScore,
    );

    await _localRepo!.saveSession(record);

    // Reload today's stats
    if (state.period == StatsViewPeriod.today) {
      await loadTodayStats();
    }

    // Try to sync immediately if online
    try {
      final response = await _apiRepo!.logFocusSession(
        startTime: startTime,
        endTime: endTime,
        durationMinutes: durationMinutes,
        taskId: taskId,
        focusType: focusType,
        whiteNoiseType: whiteNoiseType,
      );
      await _localRepo!.markAsSynced(record.id, response.id);
    } catch (e) {
      debugPrint('Sync failed, will retry later: $e');
    }
  }
}

/// Local repository provider
@riverpod
FocusStatisticsRepository localStatisticsRepo(Ref ref) {
  final db = ref.watch(localDatabaseProvider);
  return FocusStatisticsRepository(db.isar);
}

/// Stats view period provider with persistence
///
/// Persists the user's selected statistics view period (today/week/month).
final statsViewPeriodProvider =
    StateNotifierProvider<StatsViewPeriodNotifier, StatsViewPeriod>(
        (ref) => StatsViewPeriodNotifier());

/// Notifier for the stats view period
class StatsViewPeriodNotifier extends EnumPersistentNotifier<StatsViewPeriod> {
  StatsViewPeriodNotifier()
      : super(
          namespace: 'focus_statistics',
          key: 'view_period',
          defaultValue: StatsViewPeriod.today,
          values: StatsViewPeriod.values,
        );
}
