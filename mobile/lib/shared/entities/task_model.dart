import 'package:json_annotation/json_annotation.dart';

part 'task_model.g.dart';

enum TaskType {
  @JsonValue('LEARNING')
  learning,
  @JsonValue('TRAINING')
  training,
  @JsonValue('ERROR_FIX')
  errorFix,
  @JsonValue('REFLECTION')
  reflection,
  @JsonValue('SOCIAL')
  social,
  @JsonValue('PLANNING')
  planning,
  @JsonValue('OCR')
  ocr,
}

enum TaskStatus {
  @JsonValue('PENDING')
  pending,
  @JsonValue('IN_PROGRESS')
  inProgress,
  @JsonValue('PAUSED')
  paused,
  @JsonValue('RESTORE')
  restore,
  @JsonValue('STUCK')
  stuck,
  @JsonValue('COMPLETED')
  completed,
  @JsonValue('ABANDONED')
  abandoned,
}

enum TaskSyncStatus {
  synced,
  pending,
  failed,
}

enum SourceLifecycleStatus {
  active,
  archived,
  revoked,
  orphaned,
}

class SourceAssetBinding {
  const SourceAssetBinding({
    required this.id,
    required this.title,
    required this.lifecycleStatus,
    this.sourceType = 'file',
    this.linkedBy,
    this.reason,
    this.status,
    this.lifecycleReason,
    this.updatedAt,
  });

  factory SourceAssetBinding.fromJson(Map<String, dynamic> json) {
    final rawStatus =
        (json['lifecycle_status'] ?? json['lifecycleStatus'] ?? 'active')
            .toString()
            .toLowerCase();
    final lifecycleStatus = SourceLifecycleStatus.values.firstWhere(
      (status) => status.name == rawStatus,
      orElse: () => SourceLifecycleStatus.active,
    );
    return SourceAssetBinding(
      id: (json['id'] ?? json['source_id'] ?? json['sourceId'] ?? '')
          .toString(),
      title: (json['title'] ?? json['file_name'] ?? json['fileName'] ?? '')
          .toString(),
      lifecycleStatus: lifecycleStatus,
      sourceType:
          (json['source_type'] ?? json['sourceType'] ?? 'file').toString(),
      linkedBy: json['linked_by']?.toString() ?? json['linkedBy']?.toString(),
      reason: json['reason']?.toString(),
      status: json['status']?.toString(),
      lifecycleReason: json['lifecycle_reason']?.toString() ??
          json['lifecycleReason']?.toString(),
      updatedAt: DateTime.tryParse(
        (json['updated_at'] ?? json['updatedAt'] ?? '').toString(),
      ),
    );
  }

  final String id;
  final String title;
  final SourceLifecycleStatus lifecycleStatus;
  final String sourceType;
  final String? linkedBy;
  final String? reason;
  final String? status;
  final String? lifecycleReason;
  final DateTime? updatedAt;

  bool get needsAttention => lifecycleStatus != SourceLifecycleStatus.active;

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'lifecycle_status': lifecycleStatus.name,
        'source_type': sourceType,
        if (linkedBy != null) 'linked_by': linkedBy,
        if (reason != null) 'reason': reason,
        if (status != null) 'status': status,
        if (lifecycleReason != null) 'lifecycle_reason': lifecycleReason,
        if (updatedAt != null) 'updated_at': updatedAt!.toIso8601String(),
      };
}

@JsonSerializable()
class TaskModel {
  TaskModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.type,
    required this.tags,
    required this.estimatedMinutes,
    required this.difficulty,
    required this.energyCost,
    required this.status,
    required this.priority,
    required this.createdAt,
    required this.updatedAt,
    this.planId,
    this.guideContent,
    this.guideJson,
    this.aiPrompt,
    this.sourcePlanningSessionId,
    this.phaseIndex,
    this.successCriteria,
    this.pausedReason,
    this.pausedAt,
    this.startedAt,
    this.completedAt,
    this.actualMinutes,
    this.userNote,
    this.dueDate,
    this.knowledgeNodeId,
    this.orderIndex = 0,
    this.subtasksTotal = 0,
    this.subtasksCompleted = 0,
    this.boundSources = const <SourceAssetBinding>[],
    this.metadata = const <String, dynamic>{},
    this.syncStatus = TaskSyncStatus.synced,
    this.syncError,
    this.retryToken,
  });

  factory TaskModel.fromJson(Map<String, dynamic> json) =>
      _$TaskModelFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'plan_id')
  final String? planId;
  final String title;
  final TaskType type;
  final List<String> tags;
  @JsonKey(name: 'estimated_minutes')
  final int estimatedMinutes;
  final int difficulty;
  @JsonKey(name: 'energy_cost')
  final int energyCost;
  @JsonKey(name: 'guide_content')
  final String? guideContent;
  @JsonKey(name: 'guide_json')
  final Map<String, dynamic>? guideJson;
  @JsonKey(name: 'ai_prompt')
  final String? aiPrompt;
  @JsonKey(name: 'source_planning_session_id')
  final String? sourcePlanningSessionId;
  @JsonKey(name: 'phase_index')
  final int? phaseIndex;
  @JsonKey(name: 'success_criteria')
  final String? successCriteria;
  @JsonKey(name: 'paused_reason')
  final String? pausedReason;
  @JsonKey(name: 'paused_at')
  final DateTime? pausedAt;
  final TaskStatus status;
  @JsonKey(name: 'started_at')
  final DateTime? startedAt;
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  @JsonKey(name: 'actual_minutes')
  final int? actualMinutes;
  @JsonKey(name: 'user_note')
  final String? userNote;
  final int priority;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  @JsonKey(name: 'knowledge_node_id')
  final String? knowledgeNodeId;
  @JsonKey(name: 'order_index')
  final int orderIndex;
  @JsonKey(name: 'subtasks_total')
  final int subtasksTotal;
  @JsonKey(name: 'subtasks_completed')
  final int subtasksCompleted;
  @JsonKey(name: 'bound_sources')
  final List<SourceAssetBinding> boundSources;
  final Map<String, dynamic> metadata;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  // 🆕 v2.1 Local State
  @JsonKey(includeFromJson: false, includeToJson: false)
  final TaskSyncStatus syncStatus;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final String? syncError;
  @JsonKey(includeFromJson: false, includeToJson: false)
  final String? retryToken;
  Map<String, dynamic> toJson() => _$TaskModelToJson(this);

  TaskModel copyWith({
    String? id,
    String? userId,
    String? planId,
    String? title,
    TaskType? type,
    List<String>? tags,
    int? estimatedMinutes,
    int? difficulty,
    int? energyCost,
    String? guideContent,
    Map<String, dynamic>? guideJson,
    String? aiPrompt,
    String? sourcePlanningSessionId,
    int? phaseIndex,
    String? successCriteria,
    String? pausedReason,
    DateTime? pausedAt,
    TaskStatus? status,
    DateTime? startedAt,
    DateTime? completedAt,
    int? actualMinutes,
    String? userNote,
    int? priority,
    DateTime? dueDate,
    String? knowledgeNodeId,
    int? orderIndex,
    int? subtasksTotal,
    int? subtasksCompleted,
    List<SourceAssetBinding>? boundSources,
    Map<String, dynamic>? metadata,
    DateTime? createdAt,
    DateTime? updatedAt,
    TaskSyncStatus? syncStatus,
    String? syncError,
    String? retryToken,
  }) =>
      TaskModel(
        id: id ?? this.id,
        userId: userId ?? this.userId,
        planId: planId ?? this.planId,
        title: title ?? this.title,
        type: type ?? this.type,
        tags: tags ?? this.tags,
        estimatedMinutes: estimatedMinutes ?? this.estimatedMinutes,
        difficulty: difficulty ?? this.difficulty,
        energyCost: energyCost ?? this.energyCost,
        guideContent: guideContent ?? this.guideContent,
        guideJson: guideJson ?? this.guideJson,
        aiPrompt: aiPrompt ?? this.aiPrompt,
        sourcePlanningSessionId:
            sourcePlanningSessionId ?? this.sourcePlanningSessionId,
        phaseIndex: phaseIndex ?? this.phaseIndex,
        successCriteria: successCriteria ?? this.successCriteria,
        pausedReason: pausedReason ?? this.pausedReason,
        pausedAt: pausedAt ?? this.pausedAt,
        status: status ?? this.status,
        startedAt: startedAt ?? this.startedAt,
        completedAt: completedAt ?? this.completedAt,
        actualMinutes: actualMinutes ?? this.actualMinutes,
        userNote: userNote ?? this.userNote,
        priority: priority ?? this.priority,
        dueDate: dueDate ?? this.dueDate,
        knowledgeNodeId: knowledgeNodeId ?? this.knowledgeNodeId,
        orderIndex: orderIndex ?? this.orderIndex,
        subtasksTotal: subtasksTotal ?? this.subtasksTotal,
        subtasksCompleted: subtasksCompleted ?? this.subtasksCompleted,
        boundSources: boundSources ?? this.boundSources,
        metadata: metadata ?? this.metadata,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        syncStatus: syncStatus ?? this.syncStatus,
        syncError: syncError ?? this.syncError,
        retryToken: retryToken ?? this.retryToken,
      );
}

@JsonSerializable()
class TaskCreate {
  TaskCreate({
    required this.title,
    required this.type,
    required this.estimatedMinutes,
    required this.difficulty,
    this.energyCost = 1,
    this.planId,
    this.tags,
    this.dueDate,
    this.knowledgeNodeId,
    this.guideContent,
    this.guideJson,
    this.aiPrompt,
    this.sourcePlanningSessionId,
    this.phaseIndex,
    this.successCriteria,
  });

  factory TaskCreate.fromJson(Map<String, dynamic> json) =>
      _$TaskCreateFromJson(json);
  final String title;
  final TaskType type;
  final int estimatedMinutes;
  final int difficulty;
  @JsonKey(name: 'energy_cost')
  final int energyCost;
  @JsonKey(name: 'plan_id')
  final String? planId;
  final List<String>? tags;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  @JsonKey(name: 'knowledge_node_id')
  final String? knowledgeNodeId;
  @JsonKey(name: 'guide_content')
  final String? guideContent;
  @JsonKey(name: 'guide_json')
  final Map<String, dynamic>? guideJson;
  @JsonKey(name: 'ai_prompt')
  final String? aiPrompt;
  @JsonKey(name: 'source_planning_session_id')
  final String? sourcePlanningSessionId;
  @JsonKey(name: 'phase_index')
  final int? phaseIndex;
  @JsonKey(name: 'success_criteria')
  final String? successCriteria;
  Map<String, dynamic> toJson() => _$TaskCreateToJson(this);
}

@JsonSerializable()
class TaskUpdate {
  TaskUpdate({
    this.title,
    this.type,
    this.estimatedMinutes,
    this.difficulty,
    this.energyCost,
    this.tags,
    this.status,
    this.dueDate,
    this.guideContent,
    this.userNote,
  });

  factory TaskUpdate.fromJson(Map<String, dynamic> json) =>
      _$TaskUpdateFromJson(json);
  final String? title;
  final TaskType? type;
  @JsonKey(name: 'estimated_minutes')
  final int? estimatedMinutes;
  final int? difficulty;
  @JsonKey(name: 'energy_cost')
  final int? energyCost;
  final List<String>? tags;
  final TaskStatus? status;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  @JsonKey(name: 'guide_content')
  final String? guideContent;
  @JsonKey(name: 'user_note')
  final String? userNote;
  Map<String, dynamic> toJson() => _$TaskUpdateToJson(this);
}

@JsonSerializable()
class TaskComplete {
  TaskComplete({
    required this.actualMinutes,
    this.userNote,
  });

  factory TaskComplete.fromJson(Map<String, dynamic> json) =>
      _$TaskCompleteFromJson(json);
  @JsonKey(name: 'actual_minutes')
  final int actualMinutes;
  @JsonKey(name: 'user_note')
  final String? userNote;

  Map<String, dynamic> toJson() => _$TaskCompleteToJson(this);
}

@JsonSerializable()
class SuggestedNode {
  SuggestedNode({
    required this.name,
    required this.reason,
    required this.isNew,
    this.id,
  });

  factory SuggestedNode.fromJson(Map<String, dynamic> json) =>
      _$SuggestedNodeFromJson(json);

  final String? id;

  final String name;

  final String reason;

  @JsonKey(name: 'is_new')
  final bool isNew;

  Map<String, dynamic> toJson() => _$SuggestedNodeToJson(this);
}

@JsonSerializable()
class TaskSuggestionResponse {
  TaskSuggestionResponse({
    required this.intent,
    required this.suggestedNodes,
    required this.suggestedTags,
    this.estimatedMinutes,
    this.difficulty,
  });

  factory TaskSuggestionResponse.fromJson(Map<String, dynamic> json) =>
      _$TaskSuggestionResponseFromJson(json);

  final String intent;

  @JsonKey(name: 'suggested_nodes')
  final List<SuggestedNode> suggestedNodes;

  @JsonKey(name: 'suggested_tags')
  final List<String> suggestedTags;

  @JsonKey(name: 'estimated_minutes')
  final int? estimatedMinutes;

  final int? difficulty;

  Map<String, dynamic> toJson() => _$TaskSuggestionResponseToJson(this);
}
