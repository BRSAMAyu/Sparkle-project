/// Nudge suggestion for task creation
class TaskNudge {
  TaskNudge({
    required this.type,
    required this.title,
    required this.message,
    this.suggestedValue,
    this.patternId,
    this.confidence,
  });

  factory TaskNudge.fromJson(Map<String, dynamic> json) => TaskNudge(
        type: json['type'] as String,
        title: json['title'] as String,
        message: json['message'] as String,
        suggestedValue: json['suggested_value'] as int?,
        patternId: json['pattern_id'] as String?,
        confidence: (json['confidence'] as num?)?.toDouble(),
      );

  final String type;
  final String title;
  final String message;
  final int? suggestedValue;
  final String? patternId;
  final double? confidence;
}

/// Result from task creation API including nudges
class TaskCreateResult {
  TaskCreateResult({
    required this.task,
    this.nudges = const [],
  });

  final dynamic task; // TaskModel
  final List<TaskNudge> nudges;
}
