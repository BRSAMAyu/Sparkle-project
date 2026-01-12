class TaskCompletionResult {
  TaskCompletionResult({
    required this.task,
    this.feedback,
    this.flameUpdate,
    this.statsUpdate,
    this.galaxyUpdate,
  });

  factory TaskCompletionResult.fromJson(Map<String, dynamic> json) =>
      TaskCompletionResult(
        task: json['task'] as Map<String, dynamic>,
        feedback: json['feedback'] as String?,
        flameUpdate: json['flame_update'] as Map<String, dynamic>?,
        statsUpdate: json['stats_update'] as Map<String, dynamic>?,
        galaxyUpdate: json['galaxy_update'] as String?,
      );
  final Map<String, dynamic> task; // Keep as map or parse to TaskModel
  final String? feedback;
  final Map<String, dynamic>? flameUpdate;
  final Map<String, dynamic>? statsUpdate;
  final String? galaxyUpdate;
}
