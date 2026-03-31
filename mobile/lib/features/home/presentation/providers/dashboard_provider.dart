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
        isLoading = false,
        error = errorMessage;
  final WeatherData weather;
  final FlameData flame;
  final SprintData? sprint;
  final GrowthData? growth; // Added Growth Plan
  final List<TaskData> nextActions;
  final CognitiveData cognitive;
  final PredictionInsightData? nextIntentForecast;
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

      state = DashboardState(
        weather: weather,
        flame: flame,
        sprint: sprint,
        growth: growth,
        nextActions: nextActions,
        cognitive: cognitive,
        nextIntentForecast: nextIntent,
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
