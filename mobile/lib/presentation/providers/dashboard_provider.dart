import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/repositories/dashboard_repository.dart';

// Data models for dashboard state
class DashboardState {
  DashboardState({
    required this.weather,
    required this.flame,
    required this.sprint,
    required this.nextActions,
    required this.cognitive,
    this.growth,
    this.isLoading = false,
    this.error,
  });

  DashboardState.loading()
      : weather = WeatherData(type: 'sunny', condition: ''),
        flame = FlameData(level: 1, brightness: 0, todayFocusMinutes: 0),
        sprint = null,
        growth = null,
        nextActions = const [],
        cognitive = CognitiveData(status: 'empty'),
        isLoading = true,
        error = null;

  DashboardState.error(String errorMessage)
      : weather = WeatherData(type: 'sunny', condition: ''),
        flame = FlameData(level: 1, brightness: 0, todayFocusMinutes: 0),
        sprint = null,
        growth = null,
        nextActions = const [],
        cognitive = CognitiveData(status: 'empty'),
        isLoading = false,
        error = errorMessage;
  final WeatherData weather;
  final FlameData flame;
  final SprintData? sprint;
  final GrowthData? growth; // Added Growth Plan
  final List<TaskData> nextActions;
  final CognitiveData cognitive;
  final bool isLoading;
  final String? error;

  DashboardState copyWith({
    WeatherData? weather,
    FlameData? flame,
    SprintData? sprint,
    GrowthData? growth,
    List<TaskData>? nextActions,
    CognitiveData? cognitive,
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
  final int brightness;
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

class DashboardNotifier extends StateNotifier<DashboardState> {
  DashboardNotifier(this._repository) : super(DashboardState.loading()) {
    fetchData();
  }
  final DashboardRepository _repository;

  Future<void> fetchData() async {
    try {
      state = DashboardState.loading();

      final dashboardData = await _repository.getDashboardStatus();

      // Parse weather data
      final weatherMap = dashboardData['weather'] as Map<String, dynamic>;
      final weather = WeatherData(
        type: weatherMap['type'] as String,
        condition: weatherMap['condition'] as String,
      );

      // Parse flame data
      final flameMap = dashboardData['flame'] as Map<String, dynamic>;
      final flame = FlameData(
        level: flameMap['level'] as int,
        brightness: flameMap['brightness'] as int,
        todayFocusMinutes: flameMap['today_focus_minutes'] as int,
        tasksCompleted: flameMap['tasks_completed'] as int? ?? 0,
        nudgeMessage: flameMap['nudge_message'] as String? ?? '保持专注，继续前行',
      );

      // Parse sprint data (nullable)
      final sprintMap = dashboardData['sprint'] as Map<String, dynamic>?;
      final sprint = sprintMap != null
          ? SprintData(
              id: sprintMap['id'] as String,
              name: sprintMap['name'] as String,
              progress: (sprintMap['progress'] as num).toDouble(),
              daysLeft: sprintMap['days_left'] as int,
              totalEstimatedHours:
                  (sprintMap['total_estimated_hours'] as num).toDouble(),
            )
          : null;

      // Parse growth data (nullable)
      final growthMap = dashboardData['growth'] as Map<String, dynamic>?;
      final growth = growthMap != null
          ? GrowthData(
              id: growthMap['id'] as String,
              name: growthMap['name'] as String,
              progress: (growthMap['progress'] as num).toDouble(),
              masteryLevel: (growthMap['mastery_level'] as num).toDouble(),
            )
          : null;

      // Parse next actions
      final nextActionsList = dashboardData['next_actions'] as List<dynamic>;
      final nextActions = nextActionsList.map((item) {
        final map = item as Map<String, dynamic>;
        return TaskData(
          id: map['id'] as String,
          title: map['title'] as String,
          estimatedMinutes: map['estimated_minutes'] as int,
          priority: map['priority'] as int,
          type: map['type'] as String,
        );
      }).toList();

      // Parse cognitive data
      final cognitiveMap = dashboardData['cognitive'] as Map<String, dynamic>;
      final cognitive = CognitiveData(
        weeklyPattern: cognitiveMap['weekly_pattern'] as String?,
        patternType: cognitiveMap['pattern_type'] as String?,
        description: cognitiveMap['description'] as String?,
        solutionText: cognitiveMap['solution_text'] as String?,
        status: cognitiveMap['status'] as String,
        hasNewInsight: cognitiveMap['has_new_insight'] as bool? ?? false,
      );

      state = DashboardState(
        weather: weather,
        flame: flame,
        sprint: sprint,
        growth: growth,
        nextActions: nextActions,
        cognitive: cognitive,
      );
    } catch (e) {
      debugPrint('Error loading dashboard: $e');
    }
  }

  Future<void> refresh() async {
    await fetchData();
  }
}
