import 'package:json_annotation/json_annotation.dart';

part 'task_model.g.dart';

enum TaskType {
  learning,
  training,
  errorFix,
  reflection,
  social,
  planning,
}

enum TaskStatus {
  pending,
  inProgress,
  completed,
  abandoned,
}

enum TaskSyncStatus {
  synced,
  pending,
  failed,
}

@JsonSerializable()
class TaskModel {

  TaskModel({
    required this.id,
    required this.userId,
    required this.title, required this.type, required this.tags, required this.estimatedMinutes, required this.difficulty, required this.energyCost, required this.status, required this.priority, required this.createdAt, required this.updatedAt, this.planId,
    this.guideContent,
    this.startedAt,
    this.completedAt,
    this.actualMinutes,
    this.userNote,
    this.dueDate,
    this.knowledgeNodeId,
    this.syncStatus = TaskSyncStatus.synced,
    this.syncError,
    this.retryToken,
  });

  factory TaskModel.fromJson(Map<String, dynamic> json) => _$TaskModelFromJson(json);
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
    TaskStatus? status,
    DateTime? startedAt,
    DateTime? completedAt,
    int? actualMinutes,
    String? userNote,
    int? priority,
    DateTime? dueDate,
    String? knowledgeNodeId,
    DateTime? createdAt,
    DateTime? updatedAt,
    TaskSyncStatus? syncStatus,
    String? syncError,
    String? retryToken,
  }) => TaskModel(
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
      status: status ?? this.status,
      startedAt: startedAt ?? this.startedAt,
      completedAt: completedAt ?? this.completedAt,
      actualMinutes: actualMinutes ?? this.actualMinutes,
      userNote: userNote ?? this.userNote,
      priority: priority ?? this.priority,
      dueDate: dueDate ?? this.dueDate,
      knowledgeNodeId: knowledgeNodeId ?? this.knowledgeNodeId,
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
  });

  factory TaskCreate.fromJson(Map<String, dynamic> json) => _$TaskCreateFromJson(json);
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
  Map<String, dynamic> toJson() => _$TaskCreateToJson(this);
}

@JsonSerializable()
class TaskUpdate {

  TaskUpdate({
    this.title,
    this.type,
    this.estimatedMinutes,
    this.difficulty,
    this.tags,
    this.status,
    this.dueDate,
  });

  factory TaskUpdate.fromJson(Map<String, dynamic> json) => _$TaskUpdateFromJson(json);
  final String? title;
  final TaskType? type;
  final int? estimatedMinutes;
  final int? difficulty;
  final List<String>? tags;
  final TaskStatus? status;
  @JsonKey(name: 'due_date')
  final DateTime? dueDate;
  Map<String, dynamic> toJson() => _$TaskUpdateToJson(this);
}

@JsonSerializable()
class TaskComplete {

  TaskComplete({
    required this.actualMinutes,
    this.userNote,
  });

    factory TaskComplete.fromJson(Map<String, dynamic> json) => _$TaskCompleteFromJson(json);
  @JsonKey(name: 'actual_minutes')
  final int actualMinutes;
  @JsonKey(name: 'user_note')
  final String? userNote;

    Map<String, dynamic> toJson() => _$TaskCompleteToJson(this);

  }

  

  @JsonSerializable()

  class SuggestedNode {

  

    SuggestedNode({

      required this.name, required this.reason, required this.isNew, this.id,

    });

  

    factory SuggestedNode.fromJson(Map<String, dynamic> json) => _$SuggestedNodeFromJson(json);

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

  

    factory TaskSuggestionResponse.fromJson(Map<String, dynamic> json) => _$TaskSuggestionResponseFromJson(json);

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

  