import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/calendar/data/models/calendar_day_aggregate.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// State for the unified calendar provider
/// 统一日历 Provider 状态
class UnifiedCalendarState {
  const UnifiedCalendarState({
    this.monthAggregates = const {},
    this.isLoading = false,
    this.error,
  });

  /// Month-level aggregates indexed by 'YYYY-MM' format
  /// 月度聚合数据，按 'YYYY-MM' 格式索引
  final Map<String, CalendarMonthAggregate> monthAggregates;

  /// Loading state
  final bool isLoading;

  /// Error message if any
  final String? error;

  /// Get aggregate for a specific date
  /// 获取特定日期的聚合数据
  CalendarDayAggregate? getDayAggregate(DateTime date) {
    final monthKey = '${date.year}-${date.month.toString().padLeft(2, '0')}';
    final monthAggregate = monthAggregates[monthKey];
    return monthAggregate?.getDay(date.day);
  }

  /// Check if a month is loaded
  /// 检查某月是否已加载
  bool isMonthLoaded(int year, int month) {
    final monthKey = '$year-${month.toString().padLeft(2, '0')}';
    return monthAggregates.containsKey(monthKey);
  }

  UnifiedCalendarState copyWith({
    Map<String, CalendarMonthAggregate>? monthAggregates,
    bool? isLoading,
    String? error,
  }) =>
      UnifiedCalendarState(
        monthAggregates: monthAggregates ?? this.monthAggregates,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

/// Unified Calendar Provider
/// 统一日历数据聚合 Provider
///
/// Aggregates data from multiple sources:
/// - Tasks from cloud API (via TaskRepository)
/// - Calendar events from local storage (via CalendarRepository)
/// - Active plans (via PlanProvider)
/// - Cognitive data (via CognitiveProvider/DashboardProvider)
class UnifiedCalendarNotifier extends StateNotifier<UnifiedCalendarState> {
  UnifiedCalendarNotifier(
    this._ref,
    this._taskRepository,
    this._calendarRepository,
  ) : super(const UnifiedCalendarState());

  final Ref _ref;
  final TaskRepository _taskRepository;
  final CalendarRepository _calendarRepository;

  /// Track if initial load has been triggered
  bool _initialLoadTriggered = false;

  /// Initialize the provider with deferred loading
  /// This method should be called after the widget tree is built
  void initializeIfNeeded() {
    if (_initialLoadTriggered) return;
    _initialLoadTriggered = true;

    // Defer loading to avoid Riverpod initialization issues
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted) {
        loadMonth(DateTime.now());
      }
    });
  }

  /// Load aggregated data for a specific month
  /// 加载特定月份的聚合数据
  Future<void> loadMonth(DateTime month, {bool force = false}) async {
    final monthKey = '${month.year}-${month.month.toString().padLeft(2, '0')}';

    // Skip if already loaded and not forcing refresh
    if (!force && state.isMonthLoaded(month.year, month.month)) {
      return;
    }

    state = state.copyWith(isLoading: true);

    try {
      // Calculate date range for the month
      final start = DateTime(month.year, month.month);
      final end = DateTime(month.year, month.month + 1, 0);

      // Load data from multiple sources in parallel
      final results = await Future.wait([
        _loadTasksForMonth(start, end),
        _loadEventsForMonth(start, end),
        _loadActivePlans(),
      ]);

      final tasks = results[0] as List<TaskModel>;
      final events = results[1] as List<CalendarEventModel>;
      final activePlans = results[2] as List<PlanModel>;

      // Build day aggregates
      final dayAggregates = <int, CalendarDayAggregate>{};

      // Group tasks by day
      final tasksByDay = _groupTasksByDay(tasks);
      final eventsByDay = _groupEventsByDay(events);

      // Get cognitive data for today (for now, use dashboard data)
      final dashboardState = _ref.read(dashboardProvider);
      final cognitiveSnapshot = _buildCognitiveSnapshot(
        DateTime.now(),
        dashboardState,
      );

      // Build aggregates for each day in the month
      for (var day = 1; day <= end.day; day++) {
        final dayDate = DateTime(month.year, month.month, day);
        final dayTasks = tasksByDay[day] ?? [];
        final dayEvents = eventsByDay[day] ?? [];

        // Find active plan for this day
        final activePlan = _findActivePlanForDate(dayDate, activePlans);

        // Calculate focus minutes and completed count from tasks
        var focusMinutes = 0;
        var completedCount = 0;
        for (final task in dayTasks) {
          if (task.status == TaskStatus.completed) {
            completedCount++;
            focusMinutes += task.actualMinutes ?? task.estimatedMinutes;
          }
        }

        // Only create aggregate if there's activity or it's today
        final isToday = _isSameDay(dayDate, DateTime.now());
        if (dayTasks.isNotEmpty || dayEvents.isNotEmpty || isToday) {
          dayAggregates[day] = CalendarDayAggregate(
            date: dayDate,
            tasks: dayTasks,
            events: dayEvents,
            activePlan: activePlan,
            focusMinutes: focusMinutes,
            completedCount: completedCount,
            cognitive: isToday ? cognitiveSnapshot : null,
          );
        }
      }

      // Calculate month-level stats
      final totalFocusMinutes = dayAggregates.values
          .fold(0, (sum, day) => sum + day.focusMinutes);
      final totalCompletedTasks = dayAggregates.values
          .fold(0, (sum, day) => sum + day.completedCount);
      final activeDays = dayAggregates.values
          .where((day) => day.hasActivity)
          .length;

      // Find primary active plan for the month
      final primaryActivePlan = activePlans.isNotEmpty ? activePlans.first : null;

      final monthAggregate = CalendarMonthAggregate(
        year: month.year,
        month: month.month,
        dayAggregates: dayAggregates,
        totalFocusMinutes: totalFocusMinutes,
        totalCompletedTasks: totalCompletedTasks,
        activeDays: activeDays,
        activePlan: primaryActivePlan,
      );

      // Update state with new month data
      final newMonthAggregates = Map<String, CalendarMonthAggregate>.from(
        state.monthAggregates,
      );
      newMonthAggregates[monthKey] = monthAggregate;

      state = state.copyWith(
        monthAggregates: newMonthAggregates,
        isLoading: false,
      );
    } catch (e) {
      debugPrint('Error loading calendar month data: $e');
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Get aggregate for a specific day (loads month if needed)
  /// 获取特定日期的聚合数据（如需要则加载月份）
  Future<CalendarDayAggregate> getDayAggregate(DateTime date) async {
    // Ensure month is loaded
    if (!state.isMonthLoaded(date.year, date.month)) {
      await loadMonth(date);
    }

    // Return aggregate or empty
    return state.getDayAggregate(date) ?? CalendarDayAggregate.empty(date);
  }

  /// Refresh a specific month
  /// 刷新特定月份
  Future<void> refreshMonth(DateTime month) async {
    await loadMonth(month, force: true);
  }

  /// Clear all cached data
  /// 清除所有缓存数据
  void clearCache() {
    state = const UnifiedCalendarState();
  }

  // ========== Private Helper Methods ==========

  Future<List<TaskModel>> _loadTasksForMonth(DateTime start, DateTime end) async {
    try {
      return await _taskRepository.getTasksByDateRange(start, end);
    } catch (e) {
      debugPrint('Error loading tasks for month: $e');
      return [];
    }
  }

  Future<List<CalendarEventModel>> _loadEventsForMonth(
    DateTime start,
    DateTime end,
  ) async {
    try {
      final events = await _calendarRepository.getEvents();
      // Filter events for the month
      return events.where((event) =>
          event.startTime.isAfter(start.subtract(const Duration(days: 1))) &&
          event.startTime.isBefore(end.add(const Duration(days: 1))),).toList();
    } catch (e) {
      debugPrint('Error loading events for month: $e');
      return [];
    }
  }

  Future<List<PlanModel>> _loadActivePlans() async {
    try {
      final planListState = _ref.read(planListProvider);
      return planListState.activePlans;
    } catch (e) {
      debugPrint('Error loading active plans: $e');
      return [];
    }
  }

  Map<int, List<TaskModel>> _groupTasksByDay(List<TaskModel> tasks) {
    final tasksByDay = <int, List<TaskModel>>{};
    for (final task in tasks) {
      if (task.dueDate != null) {
        final day = task.dueDate!.day;
        tasksByDay.putIfAbsent(day, () => []).add(task);
      }
    }
    return tasksByDay;
  }

  Map<int, List<CalendarEventModel>> _groupEventsByDay(
    List<CalendarEventModel> events,
  ) {
    final eventsByDay = <int, List<CalendarEventModel>>{};
    for (final event in events) {
      final day = event.startTime.day;
      eventsByDay.putIfAbsent(day, () => []).add(event);
    }
    return eventsByDay;
  }

  PlanModel? _findActivePlanForDate(DateTime date, List<PlanModel> plans) {
    for (final plan in plans) {
      // Check if plan spans this date
      if (plan.targetDate != null) {
        // Plan is active from createdAt to targetDate
        if (date.isAfter(plan.createdAt.subtract(const Duration(days: 1))) &&
            date.isBefore(plan.targetDate!.add(const Duration(days: 1)))) {
          return plan;
        }
      } else if (plan.isActive) {
        // Active plan without target date
        return plan;
      }
    }
    return null;
  }

  CognitiveSnapshot? _buildCognitiveSnapshot(
    DateTime date,
    DashboardState dashboardState,
  ) {
    final cognitive = dashboardState.cognitive;
    if (cognitive.status == 'empty') return null;

    return CognitiveSnapshot(
      date: date,
      weeklyPattern: cognitive.weeklyPattern,
      description: cognitive.description,
      dominantPattern: cognitive.patternType,
    );
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

/// Provider for unified calendar data
/// 统一日历数据 Provider
final unifiedCalendarProvider =
    StateNotifierProvider<UnifiedCalendarNotifier, UnifiedCalendarState>(
  (ref) => UnifiedCalendarNotifier(
    ref,
    ref.watch(taskRepositoryProvider),
    ref.watch(calendarRepositoryProvider),
  ),
);

/// Provider for a specific day's aggregate (async)
/// 特定日期聚合数据的异步 Provider
final dayAggregateProvider =
    FutureProvider.family<CalendarDayAggregate, DateTime>((ref, date) async {
  final notifier = ref.watch(unifiedCalendarProvider.notifier);
  return notifier.getDayAggregate(date);
});

/// Provider for today's aggregate (sync, with auto-refresh)
/// 今日聚合数据的同步 Provider（带自动刷新）
///
/// Note: Uses initializeIfNeeded to defer loading to avoid
/// modifying other providers during initialization.
final todayAggregateProvider = Provider<CalendarDayAggregate>((ref) {
  final now = DateTime.now();
  final state = ref.watch(unifiedCalendarProvider);

  // Trigger deferred initialization if not loaded
  if (!state.isMonthLoaded(now.year, now.month) && !state.isLoading) {
    // Use Future.microtask to defer the initialization call
    Future.microtask(() {
      ref.read(unifiedCalendarProvider.notifier).initializeIfNeeded();
    });
  }

  return state.getDayAggregate(now) ?? CalendarDayAggregate.empty(now);
});

/// Provider for current month's aggregate
/// 当前月份聚合数据的 Provider
///
/// Note: Uses initializeIfNeeded to defer loading to avoid
/// modifying other providers during initialization.
final currentMonthAggregateProvider = Provider<CalendarMonthAggregate?>((ref) {
  final now = DateTime.now();
  final state = ref.watch(unifiedCalendarProvider);

  // Trigger deferred initialization if not loaded
  if (!state.isMonthLoaded(now.year, now.month) && !state.isLoading) {
    // Use Future.microtask to defer the initialization call
    Future.microtask(() {
      ref.read(unifiedCalendarProvider.notifier).initializeIfNeeded();
    });
  }

  final monthKey = '${now.year}-${now.month.toString().padLeft(2, '0')}';
  return state.monthAggregates[monthKey];
});

/// Provider for today's summary text
/// 今日概要文本的 Provider
final todaySummaryProvider = Provider<String>((ref) {
  final todayAggregate = ref.watch(todayAggregateProvider);
  return todayAggregate.summaryText;
});
