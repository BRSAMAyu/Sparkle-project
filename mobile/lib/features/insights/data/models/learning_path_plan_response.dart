class LearningPathPlanResponse {
  LearningPathPlanResponse({
    required this.planId,
    required this.planSummary,
    required this.tasks,
    this.message,
    this.retry,
  });

  factory LearningPathPlanResponse.fromJson(Map<String, dynamic> json) {
    final tasksJson = json['tasks'];
    final taskList = tasksJson is List
        ? tasksJson
            .whereType<Map<String, dynamic>>()
            .map(LearningPathTaskSummary.fromJson)
            .toList()
        : <LearningPathTaskSummary>[];

    return LearningPathPlanResponse(
      planId: json['plan_id'] as String,
      planSummary: json['plan_summary'] as String? ?? '',
      tasks: taskList,
      message: json['message'] as String?,
      retry: json['retry'] as bool?,
    );
  }

  final String planId;
  final String planSummary;
  final List<LearningPathTaskSummary> tasks;
  final String? message;
  final bool? retry;
}

class LearningPathTaskSummary {
  LearningPathTaskSummary({
    required this.id,
    required this.title,
    required this.type,
    required this.estimatedMinutes,
    this.priority,
    this.status,
  });

  factory LearningPathTaskSummary.fromJson(Map<String, dynamic> json) {
    return LearningPathTaskSummary(
      id: json['id'] as String,
      title: json['title'] as String? ?? 'Untitled Task',
      type: json['type'] as String? ?? 'learning',
      estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 25,
      priority: (json['priority'] as num?)?.toInt(),
      status: json['status'] as String?,
    );
  }

  final String id;
  final String title;
  final String type;
  final int estimatedMinutes;
  final int? priority;
  final String? status;
}
