import 'package:sparkle/shared/utils/entity_card_payloads.dart';

class LearningPathPlanResponse {
  LearningPathPlanResponse({
    required this.planId,
    required this.planSummary,
    required this.tasks,
    this.message,
    this.retry,
    this.entityCard,
    this.planEntityCard,
    this.taskListEntityCard,
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
      entityCard: json['entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': json['entity_card'] as Map<String, dynamic>},
              fallbackType: 'learning_path',
            )
          : null,
      planEntityCard: json['plan_entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': json['plan_entity_card'] as Map<String, dynamic>},
              fallbackType: 'plan',
            )
          : null,
      taskListEntityCard: json['task_list_entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {
                'entity_card':
                    json['task_list_entity_card'] as Map<String, dynamic>,
              },
              fallbackType: 'task_list',
            )
          : null,
    );
  }

  final String planId;
  final String planSummary;
  final List<LearningPathTaskSummary> tasks;
  final String? message;
  final bool? retry;
  final EntityCardPayload? entityCard;
  final EntityCardPayload? planEntityCard;
  final EntityCardPayload? taskListEntityCard;
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

  factory LearningPathTaskSummary.fromJson(Map<String, dynamic> json) =>
      LearningPathTaskSummary(
        id: json['id'] as String,
        title: json['title'] as String? ?? 'Untitled Task',
        type: json['type'] as String? ?? 'learning',
        estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 25,
        priority: (json['priority'] as num?)?.toInt(),
        status: json['status'] as String?,
      );

  final String id;
  final String title;
  final String type;
  final int estimatedMinutes;
  final int? priority;
  final String? status;
}

class LearningPathTaskPathResponse {
  LearningPathTaskPathResponse({
    required this.mode,
    required this.targetNodeId,
    required this.targetName,
    required this.planSummary,
    required this.tasks,
    this.message,
    this.retry,
    this.taskListEntityCard,
  });

  factory LearningPathTaskPathResponse.fromJson(Map<String, dynamic> json) {
    final tasksJson = json['tasks'];
    final taskList = tasksJson is List
        ? tasksJson
            .whereType<Map<String, dynamic>>()
            .map(LearningPathTaskSummary.fromJson)
            .toList()
        : <LearningPathTaskSummary>[];

    return LearningPathTaskPathResponse(
      mode: json['mode'] as String? ?? 'task_path',
      targetNodeId: json['target_node_id'] as String? ?? '',
      targetName: json['target_name'] as String? ?? '',
      planSummary: json['plan_summary'] as String? ?? '',
      tasks: taskList,
      message: json['message'] as String?,
      retry: json['retry'] as bool?,
      taskListEntityCard: json['task_list_entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {
                'entity_card':
                    json['task_list_entity_card'] as Map<String, dynamic>,
              },
              fallbackType: 'task_list',
            )
          : null,
    );
  }

  final String mode;
  final String targetNodeId;
  final String targetName;
  final String planSummary;
  final List<LearningPathTaskSummary> tasks;
  final String? message;
  final bool? retry;
  final EntityCardPayload? taskListEntityCard;
}

class FullPlanResponse {
  FullPlanResponse({
    required this.planId,
    required this.planSummary,
    required this.parentTaskId,
    required this.subtaskCount,
    this.entityCard,
    this.planEntityCard,
    this.taskListEntityCard,
  });

  factory FullPlanResponse.fromJson(Map<String, dynamic> json) =>
      FullPlanResponse(
        planId: json['plan_id'] as String,
        planSummary: json['plan_summary'] as String? ?? '',
        parentTaskId: json['parent_task_id'] as String,
        subtaskCount: (json['subtask_count'] as num?)?.toInt() ?? 0,
        entityCard: json['entity_card'] is Map<String, dynamic>
            ? EntityCardPayload.fromRaw(
                {'entity_card': json['entity_card'] as Map<String, dynamic>},
                fallbackType: 'learning_path',
              )
            : null,
        planEntityCard: json['plan_entity_card'] is Map<String, dynamic>
            ? EntityCardPayload.fromRaw(
                {
                  'entity_card':
                      json['plan_entity_card'] as Map<String, dynamic>,
                },
                fallbackType: 'plan',
              )
            : null,
        taskListEntityCard:
            json['task_list_entity_card'] is Map<String, dynamic>
                ? EntityCardPayload.fromRaw(
                    {
                      'entity_card':
                          json['task_list_entity_card'] as Map<String, dynamic>,
                    },
                    fallbackType: 'task_list',
                  )
                : null,
      );

  final String planId;
  final String planSummary;
  final String parentTaskId;
  final int subtaskCount;
  final EntityCardPayload? entityCard;
  final EntityCardPayload? planEntityCard;
  final EntityCardPayload? taskListEntityCard;
}
