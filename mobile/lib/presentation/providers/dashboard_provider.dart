import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/repositories/dashboard_repository.dart';

// Data models for dashboard state
class DashboardState {
  final WeatherData weather;
  final FlameData flame;
  final SprintData? sprint;
  final List<TaskData> nextActions;
  final CognitiveData cognitive;
  final bool isLoading;
  final String? error;

  DashboardState({
    required this.weather,
    required this.flame,
    required this.sprint,
    required this.nextActions,
    required this.cognitive,
    this.isLoading = false,
    this.error,
  });

  DashboardState.loading() : 
    weather = WeatherData(type: 'sunny', condition: ''),
    flame = FlameData(level: 1, brightness: 0, todayFocusMinutes: 0),
    sprint = null,
    nextActions = const [],
    cognitive = CognitiveData(weeklyPattern: '', status: ''),
    isLoading = true,
    error = null;

  DashboardState.error(String errorMessage) : 
    weather = WeatherData(type: 'sunny', condition: ''),
    flame = FlameData(level: 1, brightness: 0, todayFocusMinutes: 0),
    sprint = null,
    nextActions = const [],
    cognitive = CognitiveData(weeklyPattern: '', status: ''),
    isLoading = false,
    error = errorMessage;

  DashboardState copyWith({
    WeatherData? weather,
    FlameData? flame,
    SprintData? sprint,
    List<TaskData>? nextActions,
    CognitiveData? cognitive,
    bool? isLoading,
    String? error,
  }) {
    return DashboardState(
      weather: weather ?? this.weather,
      flame: flame ?? this.flame,
      sprint: sprint ?? this.sprint,
      nextActions: nextActions ?? this.nextActions,
      cognitive: cognitive ?? this.cognitive,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class WeatherData {
  final String type; // sunny, cloudy, rainy, meteor
  final String condition;

  WeatherData({required this.type, required this.condition});
}

class FlameData {
  final int level;
  final int brightness;
  final int todayFocusMinutes;

  FlameData({required this.level, required this.brightness, required this.todayFocusMinutes});
}

class SprintData {
  final String id;
  final String name;
  final double progress;
  final int daysLeft;
  final double totalEstimatedHours;

  SprintData({
    required this.id,
    required this.name,
    required this.progress,
    required this.daysLeft,
    required this.totalEstimatedHours,
  });
}

class TaskData {
  final String id;
  final String title;
  final int estimatedMinutes;
  final int priority;
  final String type;

  TaskData({
    required this.id,
    required this.title,
    required this.estimatedMinutes,
    required this.priority,
    required this.type,
  });
}

class CognitiveData {
  final String weeklyPattern;
  final String status;

  CognitiveData({required this.weeklyPattern, required this.status});
}

// Provider
final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>(
  (ref) => DashboardNotifier(ref.watch(dashboardRepositoryProvider)),
);

class DashboardNotifier extends StateNotifier<DashboardState> {
  final DashboardRepository _repository;

  DashboardNotifier(this._repository) : super(DashboardState.loading()) {
    fetchData();
  }

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
      );
      
      // Parse sprint data (nullable)
      final sprintMap = dashboardData['sprint'] as Map<String, dynamic>?;
      final SprintData? sprint = sprintMap != null ? SprintData(
        id: sprintMap['id'] as String,
        name: sprintMap['name'] as String,
        progress: (sprintMap['progress'] as num).toDouble(),
        daysLeft: sprintMap['days_left'] as int,
        totalEstimatedHours: (sprintMap['total_estimated_hours'] as num).toDouble(),
      ) : null;
      
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
        weeklyPattern: cognitiveMap['weekly_pattern'] as String,
        status: cognitiveMap['status'] as String,
      );
      
      state = DashboardState(
        weather: weather,
        flame: flame,
        sprint: sprint,
        nextActions: nextActions,
        cognitive: cognitive,
      );
    } catch (e, stackTrace) {
      state = DashboardState.error('Failed to load dashboard data: $e');
      // In a real app, you might want to log this error
      print('Dashboard fetch error: $e\n$stackTrace');
    }
  }
  
  Future<void> refresh() async {
    await fetchData();
  }
}
