import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Cognitive snapshot for a specific date
/// 认知数据快照，记录特定日期的认知状态
class CognitiveSnapshot {
  const CognitiveSnapshot({
    required this.date,
    this.weeklyPattern,
    this.description,
    this.energyLevel,
    this.focusScore,
    this.dominantPattern,
  });

  factory CognitiveSnapshot.fromJson(Map<String, dynamic> json) =>
      CognitiveSnapshot(
        date: DateTime.parse(json['date'] as String),
        weeklyPattern: json['weekly_pattern'] as String?,
        description: json['description'] as String?,
        energyLevel: json['energy_level'] as int?,
        focusScore: json['focus_score'] as double?,
        dominantPattern: json['dominant_pattern'] as String?,
      );
  final DateTime date;
  final String? weeklyPattern;
  final String? description;
  final int? energyLevel;
  final double? focusScore;
  final String? dominantPattern;

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String(),
        'weekly_pattern': weeklyPattern,
        'description': description,
        'energy_level': energyLevel,
        'focus_score': focusScore,
        'dominant_pattern': dominantPattern,
      };

  CognitiveSnapshot copyWith({
    DateTime? date,
    String? weeklyPattern,
    String? description,
    int? energyLevel,
    double? focusScore,
    String? dominantPattern,
  }) =>
      CognitiveSnapshot(
        date: date ?? this.date,
        weeklyPattern: weeklyPattern ?? this.weeklyPattern,
        description: description ?? this.description,
        energyLevel: energyLevel ?? this.energyLevel,
        focusScore: focusScore ?? this.focusScore,
        dominantPattern: dominantPattern ?? this.dominantPattern,
      );
}

/// Aggregated data for a single calendar day
/// 单日日历聚合数据，整合任务、事件、计划、认知等多源数据
class CalendarDayAggregate {
  const CalendarDayAggregate({
    required this.date,
    this.tasks = const [],
    this.events = const [],
    this.activePlan,
    this.focusMinutes = 0,
    this.completedCount = 0,
    this.cognitive,
  });

  factory CalendarDayAggregate.empty(DateTime date) =>
      CalendarDayAggregate(date: date);

  final DateTime date;

  /// Tasks due on this date (from cloud API)
  /// 当日到期的任务（来自云端API）
  final List<TaskModel> tasks;

  /// Calendar events on this date (from local Hive storage)
  /// 当日的日历事件（本地Hive存储）
  final List<CalendarEventModel> events;

  /// Active plan associated with this date (if any)
  /// 关联的活跃计划（如有）
  final PlanModel? activePlan;

  /// Total focus minutes for this date
  /// 当日专注时长（分钟）
  final int focusMinutes;

  /// Number of completed tasks for this date
  /// 当日完成任务数
  final int completedCount;

  /// Cognitive data snapshot for this date
  /// 认知数据快照
  final CognitiveSnapshot? cognitive;

  // ========== Computed Properties ==========

  /// Total number of tasks (pending + in-progress + completed)
  /// 总任务数
  int get totalTasks => tasks.length;

  /// Number of pending tasks
  /// 待处理任务数
  int get pendingTasks =>
      tasks.where((t) => t.status == TaskStatus.pending).length;

  /// Number of in-progress tasks
  /// 进行中任务数
  int get inProgressTasks =>
      tasks.where((t) => t.status == TaskStatus.inProgress).length;

  /// Total number of events
  /// 事件总数
  int get totalEvents => events.length;

  /// Whether this day has any activity
  /// 当日是否有任何活动
  bool get hasActivity =>
      tasks.isNotEmpty || events.isNotEmpty || focusMinutes > 0;

  /// Whether this day has cognitive data
  /// 当日是否有认知数据
  bool get hasCognitiveData => cognitive != null;

  /// Activity intensity level (0-4) for heatmap display
  /// 活动强度等级（0-4），用于热力图显示
  int get intensityLevel {
    final total = totalTasks + totalEvents;
    if (total == 0 && focusMinutes == 0) return 0;
    if (total <= 1 && focusMinutes < 30) return 1;
    if (total <= 3 && focusMinutes < 60) return 2;
    if (total <= 5 && focusMinutes < 120) return 3;
    return 4;
  }

  /// Summary string for display (e.g., "3任务, 1h专注")
  /// 概要字符串（如 "3任务, 1h专注"）
  String get summaryText {
    final isChinese = I18nService.instance.isChinese;
    final parts = <String>[];
    if (totalTasks > 0) {
      parts.add(isChinese ? '$totalTasks任务' : '$totalTasks tasks');
    }
    if (totalEvents > 0) {
      parts.add(isChinese ? '$totalEvents事件' : '$totalEvents events');
    }
    if (focusMinutes >= 60) {
      final hours = focusMinutes ~/ 60;
      parts.add(isChinese ? '${hours}h专注' : '${hours}h focus');
    } else if (focusMinutes > 0) {
      parts.add(isChinese ? '${focusMinutes}m专注' : '${focusMinutes}m focus');
    }
    return parts.isEmpty
        ? (isChinese ? '无活动' : 'No activity')
        : parts.join(', ');
  }

  CalendarDayAggregate copyWith({
    DateTime? date,
    List<TaskModel>? tasks,
    List<CalendarEventModel>? events,
    PlanModel? activePlan,
    int? focusMinutes,
    int? completedCount,
    CognitiveSnapshot? cognitive,
    bool clearActivePlan = false,
    bool clearCognitive = false,
  }) =>
      CalendarDayAggregate(
        date: date ?? this.date,
        tasks: tasks ?? this.tasks,
        events: events ?? this.events,
        activePlan: clearActivePlan ? null : (activePlan ?? this.activePlan),
        focusMinutes: focusMinutes ?? this.focusMinutes,
        completedCount: completedCount ?? this.completedCount,
        cognitive: clearCognitive ? null : (cognitive ?? this.cognitive),
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CalendarDayAggregate &&
          runtimeType == other.runtimeType &&
          date.year == other.date.year &&
          date.month == other.date.month &&
          date.day == other.date.day;

  @override
  int get hashCode => Object.hash(date.year, date.month, date.day);
}

/// Aggregated data for a calendar month
/// 月度日历聚合数据
class CalendarMonthAggregate {
  const CalendarMonthAggregate({
    required this.year,
    required this.month,
    this.dayAggregates = const {},
    this.totalFocusMinutes = 0,
    this.totalCompletedTasks = 0,
    this.activeDays = 0,
    this.activePlan,
  });

  final int year;
  final int month;

  /// Day-level aggregates indexed by day of month (1-31)
  /// 按日期索引的日聚合数据（1-31）
  final Map<int, CalendarDayAggregate> dayAggregates;

  /// Total focus minutes for the month
  /// 月度总专注时长
  final int totalFocusMinutes;

  /// Total completed tasks for the month
  /// 月度完成任务总数
  final int totalCompletedTasks;

  /// Number of days with activity
  /// 活跃天数
  final int activeDays;

  /// Active plan spanning this month (if any)
  /// 跨越本月的活跃计划（如有）
  final PlanModel? activePlan;

  /// Get aggregate for a specific day
  /// 获取特定日期的聚合数据
  CalendarDayAggregate? getDay(int day) => dayAggregates[day];

  /// Whether this month has any activity
  /// 本月是否有任何活动
  bool get hasActivity => activeDays > 0;

  /// Peak task count in a single day
  /// 单日峰值任务数
  int get peakTasks {
    var peak = 0;
    for (final day in dayAggregates.values) {
      if (day.totalTasks > peak) peak = day.totalTasks;
    }
    return peak;
  }

  CalendarMonthAggregate copyWith({
    int? year,
    int? month,
    Map<int, CalendarDayAggregate>? dayAggregates,
    int? totalFocusMinutes,
    int? totalCompletedTasks,
    int? activeDays,
    PlanModel? activePlan,
    bool clearActivePlan = false,
  }) =>
      CalendarMonthAggregate(
        year: year ?? this.year,
        month: month ?? this.month,
        dayAggregates: dayAggregates ?? this.dayAggregates,
        totalFocusMinutes: totalFocusMinutes ?? this.totalFocusMinutes,
        totalCompletedTasks: totalCompletedTasks ?? this.totalCompletedTasks,
        activeDays: activeDays ?? this.activeDays,
        activePlan: clearActivePlan ? null : (activePlan ?? this.activePlan),
      );
}
