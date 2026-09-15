/// TASK-001: TaskCardProtocol model.
///
/// Mirrors the backend `TaskCardProtocol` dataclass (signals/types.py). Allows
/// the task guide UI to display "why this task", "what materials you need",
/// "what to do if stuck", and "what happens if you fail" sections — the full
/// protocol-level task card the vision describes.
class WhyThisTask {
  const WhyThisTask({
    this.primarySignal,
    this.userVisibleReason,
    this.priorityRationale,
    this.evidence = const [],
  });

  factory WhyThisTask.fromJson(Map<String, dynamic> json) => WhyThisTask(
        primarySignal: json['primary_signal'] as String?,
        userVisibleReason: json['user_visible_reason'] as String?,
        priorityRationale: json['priority_rationale'] as String?,
        evidence: (json['evidence'] as List?)?.map((e) => e.toString()).toList() ??
            const [],
      );

  final String? primarySignal;
  final String? userVisibleReason;
  final String? priorityRationale;
  final List<String> evidence;

  bool get hasContent =>
      (userVisibleReason ?? primarySignal ?? priorityRationale ?? '').isNotEmpty;
}

class MaterialsProtocol {
  const MaterialsProtocol({
    this.retrievalMode,
    this.mustLoadNodeIds = const [],
    this.optionalNodeIds = const [],
    this.attachedDocumentIds = const [],
  });

  factory MaterialsProtocol.fromJson(Map<String, dynamic> json) =>
      MaterialsProtocol(
        retrievalMode: json['retrieval_mode'] as String?,
        mustLoadNodeIds:
            (json['must_load_node_ids'] as List?)?.map((e) => e.toString()).toList() ??
                const [],
        optionalNodeIds:
            (json['optional_node_ids'] as List?)?.map((e) => e.toString()).toList() ??
                const [],
        attachedDocumentIds: (json['attached_document_ids'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
      );

  final String? retrievalMode;
  final List<String> mustLoadNodeIds;
  final List<String> optionalNodeIds;
  final List<String> attachedDocumentIds;

  bool get hasContent =>
      mustLoadNodeIds.isNotEmpty ||
      optionalNodeIds.isNotEmpty ||
      attachedDocumentIds.isNotEmpty ||
      (retrievalMode ?? '').isNotEmpty;
}

class StuckProtocol {
  const StuckProtocol({
    this.escalationAfterMin,
    this.hintStrategy,
    this.fallbackAction,
  });

  factory StuckProtocol.fromJson(Map<String, dynamic> json) => StuckProtocol(
        escalationAfterMin: (json['escalation_after_min'] as num?)?.toInt(),
        hintStrategy: json['hint_strategy'] as String?,
        fallbackAction: json['fallback_action'] as String?,
      );

  final int? escalationAfterMin;
  final String? hintStrategy;
  final String? fallbackAction;
}

class TaskCardProtocol {
  const TaskCardProtocol({
    required this.taskId,
    required this.goalId,
    required this.taskType,
    required this.boundNodes,
    required this.whyThisTask,
    required this.materialsProtocol,
    required this.stuckProtocol,
    this.successCriteria = const [],
    this.minimumOutput,
    this.updatesAfterCompletion = const [],
    this.fallbackIfFailed = const [],
  });

  factory TaskCardProtocol.fromJson(Map<String, dynamic> json) =>
      TaskCardProtocol(
        taskId: (json['task_id'] ?? '').toString(),
        goalId: (json['goal_id'] ?? '').toString(),
        taskType: (json['task_type'] ?? 'study').toString(),
        boundNodes: (json['bound_nodes'] as List?)?.map((e) => e.toString()).toList() ??
            const [],
        whyThisTask: WhyThisTask.fromJson(
          Map<String, dynamic>.from((json['why_this_task'] as Map?) ?? {}),
        ),
        materialsProtocol: MaterialsProtocol.fromJson(
          Map<String, dynamic>.from((json['materials_protocol'] as Map?) ?? {}),
        ),
        stuckProtocol: StuckProtocol.fromJson(
          Map<String, dynamic>.from((json['stuck_protocol'] as Map?) ?? {}),
        ),
        successCriteria: (json['success_criteria'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        minimumOutput: json['minimum_output'] as String?,
        updatesAfterCompletion: (json['updates_after_completion'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
        fallbackIfFailed: (json['fallback_if_failed'] as List?)
                ?.map((e) => e.toString())
                .toList() ??
            const [],
      );

  final String taskId;
  final String goalId;
  final String taskType;
  final List<String> boundNodes;
  final WhyThisTask whyThisTask;
  final MaterialsProtocol materialsProtocol;
  final StuckProtocol stuckProtocol;
  final List<String> successCriteria;
  final String? minimumOutput;
  final List<String> updatesAfterCompletion;
  final List<String> fallbackIfFailed;
}
