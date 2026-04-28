import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';

@immutable
class ExamSprintDashboardData {
  const ExamSprintDashboardData({
    required this.planId,
    required this.planName,
    required this.subject,
    required this.daysLeft,
    required this.targetMode,
    required this.todayProgress,
    required this.highFreqCoverage,
    required this.highFreqCoveredCount,
    required this.highFreqTotalCount,
    required this.mistakeFixRate,
    required this.fixedMistakeCount,
    required this.totalMistakeCount,
    required this.streakDays,
    required this.taskGroups,
    this.estimatedScoreNow,
    this.baselineEstimatedScore,
    this.passProbability,
    this.baselinePassProbability,
    this.highYieldLowMasteryTopics = const [],
    this.sleepGuardHint,
  });

  factory ExamSprintDashboardData.fromJson(Map<String, dynamic> json) =>
      ExamSprintDashboardData(
        planId: _asString(json['plan_id']),
        planName: _asString(json['plan_name'], fallback: '考试冲刺'),
        subject: _asString(json['subject']),
        daysLeft: _asInt(json['days_left']),
        targetMode: _asNullableString(json['target_mode']),
        estimatedScoreNow: _asNullableDouble(json['estimated_score_now']),
        baselineEstimatedScore:
            _asNullableDouble(json['baseline_estimated_score']),
        passProbability: _asNullableDouble(json['pass_probability']),
        baselinePassProbability:
            _asNullableDouble(json['baseline_pass_probability']),
        todayProgress: ExamSprintTodayProgress.fromJson(
          _asStringKeyedMap(json['today_progress']) ??
              const <String, dynamic>{},
        ),
        highFreqCoverage: _asDouble(json['high_freq_coverage']),
        highFreqCoveredCount: _asInt(json['high_freq_covered_count']),
        highFreqTotalCount: _asInt(json['high_freq_total_count']),
        mistakeFixRate: _asDouble(json['mistake_fix_rate']),
        fixedMistakeCount: _asInt(json['fixed_mistake_count']),
        totalMistakeCount: _asInt(json['total_mistake_count']),
        streakDays: _asInt(json['streak_days']),
        highYieldLowMasteryTopics:
            _asStringList(json['high_yield_low_mastery_topics']),
        taskGroups: _asDynamicList(json['task_groups'])
            .map(_asStringKeyedMap)
            .whereType<Map<String, dynamic>>()
            .map(ExamSprintTaskGroup.fromJson)
            .toList(growable: false),
        sleepGuardHint: _asNullableString(json['sleep_guard_hint']),
      );

  final String planId;
  final String planName;
  final String subject;
  final int daysLeft;
  final String? targetMode;
  final double? estimatedScoreNow;
  final double? baselineEstimatedScore;
  final double? passProbability;
  final double? baselinePassProbability;
  final ExamSprintTodayProgress todayProgress;
  final double highFreqCoverage;
  final int highFreqCoveredCount;
  final int highFreqTotalCount;
  final double mistakeFixRate;
  final int fixedMistakeCount;
  final int totalMistakeCount;
  final int streakDays;
  final List<String> highYieldLowMasteryTopics;
  final List<ExamSprintTaskGroup> taskGroups;
  final String? sleepGuardHint;

  ExamSprintTaskGroup? get todayGroup {
    for (final group in taskGroups) {
      if (group.isToday) {
        return group;
      }
    }
    return taskGroups.isEmpty ? null : taskGroups.first;
  }

  List<ExamSprintTaskGroup> get futureGroups =>
      taskGroups.where((group) => !group.isToday).toList(growable: false);

  double get currentPassProbability => passProbability ?? 0.0;
  double get baselinePassProbabilitySafe =>
      baselinePassProbability ?? currentPassProbability;
  double get passProbabilityDelta =>
      currentPassProbability - baselinePassProbabilitySafe;
  bool get hasPassProbabilityDelta =>
      passProbability != null &&
      baselinePassProbability != null &&
      passProbabilityDelta.abs() >= 0.001;
}

@immutable
class ExamSprintTodayProgress {
  const ExamSprintTodayProgress({
    required this.completed,
    required this.total,
    required this.completionRate,
  });

  factory ExamSprintTodayProgress.fromJson(Map<String, dynamic> json) =>
      ExamSprintTodayProgress(
        completed: _asInt(json['completed']),
        total: _asInt(json['total']),
        completionRate: _asDouble(json['completion_rate']),
      );

  final int completed;
  final int total;
  final double completionRate;
}

@immutable
class ExamSprintTaskGroup {
  const ExamSprintTaskGroup({
    required this.dayIndex,
    required this.isToday,
    required this.completedCount,
    required this.totalCount,
    required this.tasks,
    this.date,
  });

  factory ExamSprintTaskGroup.fromJson(Map<String, dynamic> json) =>
      ExamSprintTaskGroup(
        dayIndex: _asInt(json['day_index'], fallback: 1),
        date: _asDateTime(json['date']),
        isToday: _asBool(json['is_today']),
        completedCount: _asInt(json['completed_count']),
        totalCount: _asInt(json['total_count']),
        tasks: _asDynamicList(json['tasks'])
            .map(_asStringKeyedMap)
            .whereType<Map<String, dynamic>>()
            .map(ExamSprintTaskItem.fromJson)
            .toList(growable: false),
      );

  final int dayIndex;
  final DateTime? date;
  final bool isToday;
  final int completedCount;
  final int totalCount;
  final List<ExamSprintTaskItem> tasks;
}

@immutable
class ExamSprintTaskItem {
  const ExamSprintTaskItem({
    required this.id,
    required this.title,
    required this.status,
    required this.estimatedMinutes,
    required this.isCompleted,
  });

  factory ExamSprintTaskItem.fromJson(Map<String, dynamic> json) =>
      ExamSprintTaskItem(
        id: _asString(json['id']),
        title: _asString(json['title'], fallback: S.unnamedTask),
        status: _asString(json['status'], fallback: 'PENDING').toUpperCase(),
        estimatedMinutes: _asInt(json['estimated_minutes']),
        isCompleted: _asBool(
          json['is_completed'],
          fallback: _asString(json['status']).toUpperCase() == 'COMPLETED',
        ),
      );

  final String id;
  final String title;
  final String status;
  final int estimatedMinutes;
  final bool isCompleted;

  bool get isInProgress => status == 'IN_PROGRESS';
}

final examSprintDashboardProvider =
    FutureProvider<ExamSprintDashboardData?>((ref) async {
  final repository = ref.watch(dashboardRepositoryProvider);
  final payload = await repository.getExamSprintDashboard();
  if (!_asBool(payload['active'])) {
    return null;
  }
  return ExamSprintDashboardData.fromJson(payload);
});

Map<String, dynamic>? _asStringKeyedMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    try {
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }
  return null;
}

List<dynamic> _asDynamicList(dynamic value) {
  if (value is List<dynamic>) {
    return value;
  }
  if (value is List) {
    return List<dynamic>.from(value);
  }
  return const <dynamic>[];
}

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString();
  if (text == null || text.isEmpty) {
    return fallback;
  }
  return text;
}

String? _asNullableString(dynamic value) {
  final text = _asString(value);
  return text.isEmpty ? null : text;
}

int _asInt(dynamic value, {int fallback = 0}) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? fallback;
  }
  return fallback;
}

double _asDouble(dynamic value, {double fallback = 0.0}) {
  if (value is double) {
    return value;
  }
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value) ?? fallback;
  }
  return fallback;
}

double? _asNullableDouble(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is String && value.trim().isEmpty) {
    return null;
  }
  return _asDouble(value);
}

bool _asBool(dynamic value, {bool fallback = false}) {
  if (value is bool) {
    return value;
  }
  if (value is num) {
    return value != 0;
  }
  if (value is String) {
    switch (value.trim().toLowerCase()) {
      case 'true':
      case '1':
      case 'yes':
      case 'y':
        return true;
      case 'false':
      case '0':
      case 'no':
      case 'n':
        return false;
    }
  }
  return fallback;
}

DateTime? _asDateTime(dynamic value) {
  if (value is DateTime) {
    return value;
  }
  if (value is String) {
    return DateTime.tryParse(value);
  }
  return null;
}

List<String> _asStringList(dynamic value) => _asDynamicList(value)
    .map((item) => '$item')
    .where((item) => item.trim().isNotEmpty)
    .toList(growable: false);
