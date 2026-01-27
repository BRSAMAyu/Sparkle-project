import 'package:sparkle/features/task/data/models/next_action.dart';

class TaskCompletionResult {
  TaskCompletionResult({
    required this.task,
    this.feedback,
    this.flameUpdate,
    this.statsUpdate,
    this.galaxyUpdate,
    this.nextActions = const [],
    this.unlockedAchievements = const [],
  });

  factory TaskCompletionResult.fromJson(Map<String, dynamic> json) =>
      TaskCompletionResult(
        task: json['task'] as Map<String, dynamic>,
        feedback: json['feedback'] as String?,
        flameUpdate: json['flame_update'] as Map<String, dynamic>?,
        statsUpdate: json['stats_update'] as Map<String, dynamic>?,
        galaxyUpdate: json['galaxy_update'] as String?,
        nextActions: _parseNextActions(json['next_actions'] as List<dynamic>?),
        unlockedAchievements: json['unlocked_achievements'] as List<dynamic>? ??
            const [],
      );

  static List<NextAction> _parseNextActions(List<dynamic>? actionsJson) {
    if (actionsJson == null) return const [];
    return actionsJson
        .map((json) =>
            NextAction.fromJson(json as Map<String, dynamic>),)
        .toList();
  }

  final Map<String, dynamic> task; // Keep as map or parse to TaskModel
  final String? feedback;
  final Map<String, dynamic>? flameUpdate;
  final Map<String, dynamic>? statsUpdate;
  final String? galaxyUpdate;
  final List<NextAction> nextActions;
  final List<dynamic> unlockedAchievements;
}
