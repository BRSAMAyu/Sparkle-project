import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';

// Data models for dashboard state
class DashboardState {
  DashboardState({
    required this.weather,
    required this.flame,
    required this.sprint,
    required this.nextActions,
    required this.cognitive,
    this.nextIntentForecast,
    this.growth,
    this.growthStatus,
    this.mostImportantTask,
    this.growthSignal,
    this.activePlanProgress,
    this.isLoading = false,
    this.error,
  });

  DashboardState.loading()
      : weather = WeatherData(type: 'sunny', condition: ''),
        flame = FlameData(level: 1, brightness: 0.0, todayFocusMinutes: 0),
        sprint = null,
        growth = null,
        nextActions = const [],
        cognitive = CognitiveData(status: 'empty'),
        nextIntentForecast = null,
        growthStatus = null,
        mostImportantTask = null,
        growthSignal = null,
        activePlanProgress = null,
        isLoading = true,
        error = null;

  DashboardState.error(String errorMessage)
      : weather = WeatherData(type: 'sunny', condition: ''),
        flame = FlameData(level: 1, brightness: 0.0, todayFocusMinutes: 0),
        sprint = null,
        growth = null,
        nextActions = const [],
        cognitive = CognitiveData(status: 'empty'),
        nextIntentForecast = null,
        growthStatus = null,
        mostImportantTask = null,
        growthSignal = null,
        activePlanProgress = null,
        isLoading = false,
        error = errorMessage;
  final WeatherData weather;
  final FlameData flame;
  final SprintData? sprint;
  final GrowthData? growth; // Added Growth Plan
  final List<TaskData> nextActions;
  final CognitiveData cognitive;
  final PredictionInsightData? nextIntentForecast;
  final GrowthStatusData? growthStatus;
  final PriorityTaskData? mostImportantTask;
  final GrowthSignalData? growthSignal;
  final ActivePlanProgressData? activePlanProgress;
  final bool isLoading;
  final String? error;

  DashboardState copyWith({
    WeatherData? weather,
    FlameData? flame,
    SprintData? sprint,
    GrowthData? growth,
    List<TaskData>? nextActions,
    CognitiveData? cognitive,
    PredictionInsightData? nextIntentForecast,
    GrowthStatusData? growthStatus,
    PriorityTaskData? mostImportantTask,
    GrowthSignalData? growthSignal,
    ActivePlanProgressData? activePlanProgress,
    bool? isLoading,
    String? error,
  }) =>
      DashboardState(
        weather: weather ?? this.weather,
        flame: flame ?? this.flame,
        sprint: sprint ?? this.sprint,
        growth: growth ?? this.growth,
        nextActions: nextActions ?? this.nextActions,
        cognitive: cognitive ?? this.cognitive,
        nextIntentForecast: nextIntentForecast ?? this.nextIntentForecast,
        growthStatus: growthStatus ?? this.growthStatus,
        mostImportantTask: mostImportantTask ?? this.mostImportantTask,
        growthSignal: growthSignal ?? this.growthSignal,
        activePlanProgress: activePlanProgress ?? this.activePlanProgress,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
      );
}

class WeatherData {
  WeatherData({required this.type, required this.condition});
  final String type; // sunny, cloudy, rainy, meteor
  final String condition;
}

class FlameData {
  FlameData({
    required this.level,
    required this.brightness,
    required this.todayFocusMinutes,
    this.tasksCompleted = 0,
    this.nudgeMessage = '保持专注，继续前行',
  });
  final int level;
  final double brightness; // 🔧 修复：改为double以匹配后端返回的0.0-1.0范围值
  final int todayFocusMinutes;
  final int tasksCompleted;
  final String nudgeMessage;
}

class SprintData {
  SprintData({
    required this.id,
    required this.name,
    required this.progress,
    required this.daysLeft,
    required this.totalEstimatedHours,
  });
  final String id;
  final String name;
  final double progress;
  final int daysLeft;
  final double totalEstimatedHours;
}

class GrowthData {
  GrowthData({
    required this.id,
    required this.name,
    required this.progress,
    required this.masteryLevel,
  });
  final String id;
  final String name;
  final double progress;
  final double masteryLevel;
}

class TaskData {
  TaskData({
    required this.id,
    required this.title,
    required this.estimatedMinutes,
    required this.priority,
    required this.type,
  });
  final String id;
  final String title;
  final int estimatedMinutes;
  final int priority;
  final String type;
}

class CognitiveData {
  CognitiveData({
    required this.status,
    this.weeklyPattern,
    this.patternType,
    this.description,
    this.solutionText,
    this.hasNewInsight = false,
  });
  final String? weeklyPattern;
  final String? patternType;
  final String? description;
  final String? solutionText;
  final String status;
  final bool hasNewInsight;
}

class GrowthStatusData {
  GrowthStatusData({
    required this.headline,
    required this.subtitle,
    required this.userName,
    required this.streakDays,
    required this.focusHoursWeek,
    required this.tasksCompletedWeek,
  });

  final String headline;
  final String subtitle;
  final String userName;
  final int streakDays;
  final double focusHoursWeek;
  final int tasksCompletedWeek;
}

class PriorityTaskData {
  PriorityTaskData({
    required this.id,
    required this.title,
    required this.estimatedMinutes,
    required this.priority,
    required this.type,
    required this.reason,
    this.planName,
    this.daysToDeadline,
    this.riskScore = 0,
  });

  final String id;
  final String title;
  final int estimatedMinutes;
  final int priority;
  final String type;
  final String reason;
  final String? planName;
  final int? daysToDeadline;
  final double riskScore;
}

class GrowthSignalData {
  GrowthSignalData({
    required this.headline,
    required this.summary,
    required this.source,
    this.topic,
    this.deltaPoints = 0,
    this.evidenceCount = 0,
  });

  final String headline;
  final String summary;
  final String source;
  final String? topic;
  final double deltaPoints;
  final int evidenceCount;
}

class ActivePlanProgressData {
  ActivePlanProgressData({
    required this.id,
    required this.name,
    required this.type,
    required this.phase,
    required this.progress,
    required this.masteryLevel,
    this.targetDate,
    this.daysToDeadline,
  });

  final String id;
  final String name;
  final String type;
  final String phase;
  final double progress;
  final double masteryLevel;
  final String? targetDate;
  final int? daysToDeadline;
}

// Provider
final dashboardProvider =
    StateNotifierProvider<DashboardNotifier, DashboardState>(
  (ref) => DashboardNotifier(ref.watch(dashboardRepositoryProvider)),
);

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

double _asDouble(dynamic value, {double fallback = 0}) {
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
      default:
        return fallback;
    }
  }
  return fallback;
}

class DashboardNotifier extends StateNotifier<DashboardState> {
  DashboardNotifier(this._repository) : super(DashboardState.loading()) {
    unawaited(Future<void>.microtask(fetchData));
  }
  final DashboardRepository _repository;

  Future<void> fetchData() async {
    try {
      if (!mounted) return;
      state = DashboardState.loading();

      final dashboardData = await _repository.getDashboardStatus();
      var predictiveData = <String, dynamic>{};
      try {
        predictiveData = await _repository.getPredictiveDashboard();
      } catch (e) {
        debugPrint('Predictive dashboard unavailable: $e');
      }
      if (!mounted) return;

      // Parse weather data
      final weatherRaw = dashboardData['weather'];
      final weatherMap = _asStringKeyedMap(weatherRaw) ?? <String, dynamic>{};
      final weather = WeatherData(
        type: _asString(weatherMap['type'], fallback: 'sunny'),
        condition: _asString(weatherMap['condition'], fallback: 'clear'),
      );

      // Parse flame data
      final flameRaw = dashboardData['flame'];
      final flameMap = _asStringKeyedMap(flameRaw) ?? <String, dynamic>{};
      final flame = FlameData(
        level: _asInt(flameMap['level'], fallback: 1),
        brightness: _asDouble(flameMap['brightness'], fallback: 0.5),
        todayFocusMinutes: _asInt(flameMap['today_focus_minutes']),
        tasksCompleted: _asInt(flameMap['tasks_completed']),
        nudgeMessage: _asString(
          flameMap['nudge_message'],
          fallback: '保持专注，继续前行',
        ),
      );

      // Parse sprint data (nullable)
      final sprintRaw = dashboardData['sprint'];
      final sprintMap = _asStringKeyedMap(sprintRaw);
      final sprint = sprintMap != null
          ? SprintData(
              id: _asString(sprintMap['id']),
              name: _asString(sprintMap['name']),
              progress: _asDouble(sprintMap['progress']),
              daysLeft: _asInt(sprintMap['days_left']),
              totalEstimatedHours: _asDouble(
                sprintMap['total_estimated_hours'],
              ),
            )
          : null;

      // Parse growth data (nullable)
      final growthRaw = dashboardData['growth'];
      final growthMap = _asStringKeyedMap(growthRaw);
      final growth = growthMap != null
          ? GrowthData(
              id: _asString(growthMap['id']),
              name: _asString(growthMap['name']),
              progress: _asDouble(growthMap['progress']),
              masteryLevel: _asDouble(growthMap['mastery_level']),
            )
          : null;

      // Parse next actions
      final nextActionsRaw = dashboardData['next_actions'];
      final nextActionsList = _asDynamicList(nextActionsRaw);
      final nextActions = nextActionsList.map((item) {
        final map = _asStringKeyedMap(item) ?? <String, dynamic>{};

        // 🔧 修复：type字段可能是List，需要安全转换
        String typeValue;
        final typeRaw = map['type'];
        if (typeRaw is List) {
          typeValue = (typeRaw.isNotEmpty && typeRaw.first is String)
              ? typeRaw.first as String
              : 'learning';
        } else if (typeRaw is String) {
          typeValue = typeRaw;
        } else {
          typeValue = 'learning';
        }

        return TaskData(
          id: _asString(map['id']),
          title: _asString(map['title']),
          estimatedMinutes: _asInt(map['estimated_minutes']),
          priority: _asInt(map['priority']),
          type: typeValue,
        );
      }).toList();

      // Parse cognitive data
      final cognitiveRaw = dashboardData['cognitive'];
      final cognitiveMap = _asStringKeyedMap(cognitiveRaw) ??
          <String, dynamic>{'status': 'stable'};
      final cognitive = CognitiveData(
        weeklyPattern: _asNullableString(cognitiveMap['weekly_pattern']),
        patternType: _asNullableString(cognitiveMap['pattern_type']),
        description: _asNullableString(cognitiveMap['description']),
        solutionText: _asNullableString(cognitiveMap['solution_text']),
        status: _asString(cognitiveMap['status'], fallback: 'stable'),
        hasNewInsight: _asBool(cognitiveMap['has_new_insight']),
      );

      final nextIntentMap =
          _asStringKeyedMap(predictiveData['next_intent_forecast']);
      PredictionInsightData? nextIntent;
      if (nextIntentMap != null) {
        try {
          nextIntent = PredictionInsightData.fromJson(nextIntentMap);
        } catch (e) {
          debugPrint('Invalid next_intent_forecast payload: $e');
        }
      }

      final growthStatusMap = _asStringKeyedMap(dashboardData['growth_status']);
      final growthStatus = growthStatusMap == null
          ? null
          : GrowthStatusData(
              headline: _asString(growthStatusMap['headline']),
              subtitle: _asString(growthStatusMap['subtitle']),
              userName: _asString(growthStatusMap['user_name']),
              streakDays: _asInt(growthStatusMap['streak_days']),
              focusHoursWeek: _asDouble(growthStatusMap['focus_hours_week']),
              tasksCompletedWeek:
                  _asInt(growthStatusMap['tasks_completed_week']),
            );

      final priorityTaskMap =
          _asStringKeyedMap(dashboardData['most_important_task']);
      final mostImportantTask = priorityTaskMap == null
          ? null
          : PriorityTaskData(
              id: _asString(priorityTaskMap['id']),
              title: _asString(priorityTaskMap['title']),
              estimatedMinutes: _asInt(priorityTaskMap['estimated_minutes']),
              priority: _asInt(priorityTaskMap['priority']),
              type: _asString(priorityTaskMap['type'], fallback: 'learning'),
              reason: _asString(priorityTaskMap['reason']),
              planName: _asNullableString(priorityTaskMap['plan_name']),
              daysToDeadline: priorityTaskMap['days_to_deadline'] == null
                  ? null
                  : _asInt(priorityTaskMap['days_to_deadline']),
              riskScore: _asDouble(priorityTaskMap['risk_score']),
            );

      final growthSignalMap = _asStringKeyedMap(dashboardData['growth_signal']);
      final growthSignal = growthSignalMap == null
          ? null
          : GrowthSignalData(
              headline: _asString(growthSignalMap['headline']),
              summary: _asString(growthSignalMap['summary']),
              source: _asString(growthSignalMap['source']),
              topic: _asNullableString(growthSignalMap['topic']),
              deltaPoints: _asDouble(growthSignalMap['delta_points']),
              evidenceCount: _asInt(growthSignalMap['evidence_count']),
            );

      final activePlanMap =
          _asStringKeyedMap(dashboardData['active_plan_progress']);
      final activePlanProgress = activePlanMap == null
          ? null
          : ActivePlanProgressData(
              id: _asString(activePlanMap['id']),
              name: _asString(activePlanMap['name']),
              type: _asString(activePlanMap['type']),
              phase: _asString(activePlanMap['phase']),
              progress: _asDouble(activePlanMap['progress']),
              masteryLevel: _asDouble(activePlanMap['mastery_level']),
              targetDate: _asNullableString(activePlanMap['target_date']),
              daysToDeadline: activePlanMap['days_to_deadline'] == null
                  ? null
                  : _asInt(activePlanMap['days_to_deadline']),
            );

      state = DashboardState(
        weather: weather,
        flame: flame,
        sprint: sprint,
        growth: growth,
        nextActions: nextActions,
        cognitive: cognitive,
        nextIntentForecast: nextIntent,
        growthStatus: growthStatus,
        mostImportantTask: mostImportantTask,
        growthSignal: growthSignal,
        activePlanProgress: activePlanProgress,
      );
    } catch (e) {
      debugPrint('Error loading dashboard: $e');
      if (!mounted) return;
      state = DashboardState.error(e.toString());
    }
  }

  Future<void> refresh() async {
    await fetchData();
  }
}
