import 'package:intl/intl.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';

/// Repository for local focus session statistics using Isar
/// Provides offline support and sync capabilities
class FocusStatisticsRepository {
  FocusStatisticsRepository(this._isar);

  final Isar _isar;
  late final IsarCollection<FocusSessionRecord> _collection =
      _isar.focusSessionRecords;

  // ==================== Save Operations ====================

  /// Save a focus session to local storage
  Future<int> saveSession(FocusSessionRecord session) async {
    return await _isar.writeTxn(() async {
      return await _collection.put(session);
    });
  }

  /// Save multiple sessions at once
  Future<void> saveSessions(List<FocusSessionRecord> sessions) async {
    await _isar.writeTxn(() async {
      await _collection.putAll(sessions);
    });
  }

  // ==================== Query Operations ====================

  /// Get sessions within a date range
  Future<List<FocusSessionRecord>> getSessionsByDateRange(
    DateTime start,
    DateTime end,
  ) async {
    return await _collection
        .where()
        .startTimeBetween(start, end)
        .sortByStartTimeDesc()
        .findAll();
  }

  /// Get today's total focus minutes (completed sessions only)
  Future<int> getTodayTotalMinutes() async {
    final now = DateTime.now();
    final todayStart = DateTime(now.year, now.month, now.day);
    final todayEnd = todayStart.add(const Duration(days: 1));

    final sessions = await _collection
        .where()
        .startTimeBetween(todayStart, todayEnd)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    return sessions.fold<int>(
      0,
      (sum, session) => sum + session.durationMinutes,
    );
  }

  /// Get this week's total focus minutes
  Future<int> getWeekTotalMinutes() async {
    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday));
    final todayStart = DateTime(weekStart.year, weekStart.month, weekStart.day);
    final weekEnd = todayStart.add(const Duration(days: 7));

    final sessions = await _collection
        .where()
        .startTimeBetween(todayStart, weekEnd)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    return sessions.fold<int>(
      0,
      (sum, session) => sum + session.durationMinutes,
    );
  }

  /// Get this month's total focus minutes
  Future<int> getMonthTotalMinutes() async {
    final now = DateTime.now();
    final monthStart = DateTime(now.year, now.month, 1);

    final sessions = await _collection
        .where()
        .startTimeGreaterThanOrEqualTo(monthStart)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    return sessions.fold<int>(
      0,
      (sum, session) => sum + session.durationMinutes,
    );
  }

  /// Get weekly statistics breakdown
  Future<Map<String, dynamic>> getWeeklyStats() async {
    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday));
    final todayStart = DateTime(weekStart.year, weekStart.month, weekStart.day);
    final weekEnd = todayStart.add(const Duration(days: 7));

    final sessions = await _collection
        .where()
        .startTimeBetween(todayStart, weekEnd)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    // Daily breakdown
    final dailyBreakdown = <String, int>{};
    final focusTypeDistribution = <String, int>{
      'pomodoro': 0,
      'stopwatch': 0,
    };

    for (final session in sessions) {
      final dateKey = session.dateKey;
      dailyBreakdown[dateKey] =
          (dailyBreakdown[dateKey] ?? 0) + session.durationMinutes;
      focusTypeDistribution[session.focusType] =
          (focusTypeDistribution[session.focusType] ?? 0) +
              session.durationMinutes;
    }

    // Ensure all 7 days are present
    for (int i = 0; i < 7; i++) {
      final day = todayStart.add(Duration(days: i));
      final dateKey =
          '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';
      dailyBreakdown.putIfAbsent(dateKey, () => 0);
    }

    final totalMinutes = sessions.fold<int>(
      0,
      (sum, session) => sum + session.durationMinutes,
    );

    final currentStreak = await _calculateCurrentStreak();
    final longestStreak = await _calculateLongestStreak();

    return {
      'period_start': todayStart.toIso8601String(),
      'period_end': weekEnd.toIso8601String(),
      'total_minutes': totalMinutes,
      'session_count': sessions.length,
      'daily_breakdown': dailyBreakdown,
      'focus_type_distribution': focusTypeDistribution,
      'streak_days': currentStreak,
      'longest_streak': longestStreak,
    };
  }

  /// Get monthly statistics breakdown
  Future<Map<String, dynamic>> getMonthlyStats() async {
    final now = DateTime.now();
    final monthStart = DateTime(now.year, now.month, 1);

    final sessions = await _collection
        .where()
        .startTimeGreaterThanOrEqualTo(monthStart)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    // Daily breakdown
    final dailyBreakdown = <String, int>{};
    final weeklyBreakdown = <String, int>{};
    final focusTypeDistribution = <String, int>{
      'pomodoro': 0,
      'stopwatch': 0,
    };

    for (final session in sessions) {
      final dateKey = session.dateKey;
      dailyBreakdown[dateKey] =
          (dailyBreakdown[dateKey] ?? 0) + session.durationMinutes;
      focusTypeDistribution[session.focusType] =
          (focusTypeDistribution[session.focusType] ?? 0) +
              session.durationMinutes;

      // Weekly breakdown
      final weekKey =
          '${session.startTime.year}-W${_getWeekNumber(session.startTime).toString().padLeft(2, '0')}';
      weeklyBreakdown[weekKey] =
          (weeklyBreakdown[weekKey] ?? 0) + session.durationMinutes;
    }

    final totalMinutes = sessions.fold<int>(
      0,
      (sum, session) => sum + session.durationMinutes,
    );

    final currentStreak = await _calculateCurrentStreak();
    final longestStreak = await _calculateLongestStreak();

    return {
      'period_start': monthStart.toIso8601String(),
      'total_minutes': totalMinutes,
      'session_count': sessions.length,
      'daily_breakdown': dailyBreakdown,
      'weekly_breakdown': weeklyBreakdown,
      'focus_type_distribution': focusTypeDistribution,
      'streak_days': currentStreak,
      'longest_streak': longestStreak,
    };
  }

  /// Get session history with pagination
  Future<List<FocusSessionRecord>> getSessionHistory({
    int limit = 20,
    int offset = 0,
  }) async {
    return await _collection
        .where()
        .sortByStartTimeDesc()
        .offset(offset)
        .limit(limit)
        .findAll();
  }

  /// Get total session count
  Future<int> getTotalSessionCount() async {
    return await _collection.count();
  }

  /// Get heatmap data for the last N days
  Future<Map<DateTime, double>> getHeatmapData({int days = 90}) async {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: days));

    final sessions = await _collection
        .where()
        .startTimeBetween(startDate, now)
        .filter()
        .statusEqualTo('completed')
        .findAll();

    final heatmapData = <DateTime, double>{};

    for (final session in sessions) {
      final date = DateTime(
        session.startTime.year,
        session.startTime.month,
        session.startTime.day,
      );
      heatmapData[date] =
          (heatmapData[date] ?? 0.0) + session.durationMinutes.toDouble();
    }

    return heatmapData;
  }

  // ==================== Streak Calculations ====================

  /// Calculate current consecutive days streak
  Future<int> _calculateCurrentStreak() async {
    final today = DateTime.now();
    final todayStart = DateTime(today.year, today.month, today.day);
    var checkDate = todayStart;
    int streak = 0;

    // Check up to 365 days back
    for (int i = 0; i < 365; i++) {
      final nextDay = checkDate.add(const Duration(days: 1));
      final dayStart = checkDate;
      final dayEnd = nextDay;

      final count = await _collection
          .where()
          .startTimeBetween(dayStart, dayEnd)
          .filter()
          .statusEqualTo('completed')
          .count();

      if (count > 0) {
        streak++;
        checkDate = dayStart.subtract(const Duration(days: 1));
      } else {
        // If checking today and no sessions, check yesterday
        if (checkDate == todayStart) {
          checkDate = dayStart.subtract(const Duration(days: 1));
          continue;
        }
        break;
      }
    }

    return streak;
  }

  /// Calculate the longest consecutive days streak ever
  Future<int> _calculateLongestStreak() async {
    final sessions = await _collection
        .where()
        .filter()
        .statusEqualTo('completed')
        .sortByStartTime()
        .findAll();

    if (sessions.isEmpty) return 0;

    // Extract unique dates
    final dates = <DateTime>[];
    DateTime? lastDate;

    for (final session in sessions) {
      final date = DateTime(
        session.startTime.year,
        session.startTime.month,
        session.startTime.day,
      );

      if (lastDate == null ||
          date.year != lastDate.year ||
          date.month != lastDate.month ||
          date.day != lastDate.day) {
        dates.add(date);
        lastDate = date;
      }
    }

    if (dates.isEmpty) return 0;

    int longestStreak = 1;
    int currentStreak = 1;
    var prevDate = dates[0];

    for (int i = 1; i < dates.length; i++) {
      final diff = dates[i].difference(prevDate).inDays;
      if (diff == 1) {
        currentStreak++;
      } else if (diff > 1) {
        longestStreak = longestStreak > currentStreak
            ? longestStreak
            : currentStreak;
        currentStreak = 1;
      }
      prevDate = dates[i];
    }

    longestStreak =
        longestStreak > currentStreak ? longestStreak : currentStreak;
    return longestStreak;
  }

  // ==================== Sync Operations ====================

  /// Get all unsynced sessions
  Future<List<FocusSessionRecord>> getUnsyncedSessions() async {
    return await _collection
        .where()
        .isSyncedEqualTo(false)
        .sortByCreatedAt()
        .findAll();
  }

  /// Mark a session as synced with server ID
  Future<void> markAsSynced(int localId, String serverId) async {
    await _isar.writeTxn(() async {
      final session = await _collection.get(localId);
      if (session != null) {
        session.serverId = serverId;
        session.isSynced = true;
        session.lastSyncAttempt = DateTime.now();
        session.syncError = null;
        await _collection.put(session);
      }
    });
  }

  /// Mark sync as failed
  Future<void> markSyncFailed(int localId, String error) async {
    await _isar.writeTxn(() async {
      final session = await _collection.get(localId);
      if (session != null) {
        session.isSynced = false;
        session.lastSyncAttempt = DateTime.now();
        session.syncError = error;
        await _collection.put(session);
      }
    });
  }

  /// Merge server sessions into local storage
  /// Returns the number of new sessions added
  Future<int> mergeServerSessions(List<Map<String, dynamic>> serverSessions) async {
    int newCount = 0;

    await _isar.writeTxn(() async {
      for (final sessionData in serverSessions) {
        final serverId = sessionData['id'] as String;
        final startTime = DateTime.parse(sessionData['start_time'] as String);

        // Check if session already exists by serverId
        final existing = await _collection
            .filter()
            .serverIdEqualTo(serverId)
            .findFirst();

        if (existing == null) {
          // Create new local record
          final record = FocusSessionRecord()
            ..serverId = serverId
            ..startTime = startTime
            ..endTime = DateTime.parse(sessionData['end_time'] as String)
            ..durationMinutes = sessionData['duration_minutes'] as int
            ..focusType = sessionData['focus_type'] as String
            ..status = sessionData['status'] as String
            ..taskId = sessionData['task_id'] as String?
            ..taskTitle = sessionData['task_title'] as String?
            ..whiteNoiseType = sessionData['white_noise_type']?.toString()
            ..interruptionCount = 0
            ..isSynced = true
            ..createdAt = DateTime.now();

          await _collection.put(record);
          newCount++;
        }
      }
    });

    return newCount;
  }

  /// Delete a session by local ID
  Future<bool> deleteSession(int id) async {
    return await _isar.writeTxn(() async {
      return await _collection.delete(id);
    });
  }

  /// Clear all local data (use with caution)
  Future<void> clearAll() async {
    await _isar.writeTxn(() async {
      await _collection.clear();
    });
  }

  // ==================== Helpers ====================

  /// Get ISO week number for a date
  int _getWeekNumber(DateTime date) {
    final dayOfYear = int.parse(DateFormat('D').format(date));
    final weekNumber = ((dayOfYear - date.weekday + 10) / 7).floor();
    return weekNumber;
  }
}
