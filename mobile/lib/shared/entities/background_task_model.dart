import 'package:sparkle/shared/models/base_model.dart';

/// Background task type enumeration
enum BackgroundTaskType {
  aiGeneration('AI_GENERATION'),
  dataSync('DATA_SYNC'),
  planGeneration('PLAN_GENERATION'),
  galaxyExpansion('GALAXY_EXPANSION'),
  taskBatch('TASK_BATCH');

  final String value;
  const BackgroundTaskType(this.value);

  static BackgroundTaskType fromString(String value) {
    return BackgroundTaskType.values.firstWhere(
      (e) => e.value == value,
      orElse: () => BackgroundTaskType.dataSync,
    );
  }
}

/// Background task status enumeration
enum BackgroundTaskStatus {
  pending('PENDING'),
  running('RUNNING'),
  completed('COMPLETED'),
  failed('FAILED'),
  cancelled('CANCELLED');

  final String value;
  const BackgroundTaskStatus(this.value);

  static BackgroundTaskStatus fromString(String value) {
    return BackgroundTaskStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => BackgroundTaskStatus.pending,
    );
  }
}

/// Background task model
class BackgroundTaskModel extends BaseModel {
  const BackgroundTaskModel({
    required this.id,
    required this.userId,
    required this.taskType,
    required this.name,
    required this.status,
    required this.progress,
    this.progressMessage,
    this.resultData,
    this.errorMessage,
    this.relatedEntityId,
    this.relatedEntityType,
    this.externalTaskId,
    required this.createdAt,
    this.updatedAt,
    this.completedAt,
  });

  final String id;
  final String userId;
  final BackgroundTaskType taskType;
  final String name;
  final BackgroundTaskStatus status;
  final double progress; // 0.0 to 1.0
  final String? progressMessage;
  final Map<String, dynamic>? resultData;
  final String? errorMessage;
  final String? relatedEntityId;
  final String? relatedEntityType;
  final String? externalTaskId;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final DateTime? completedAt;

  bool get isPending => status == BackgroundTaskStatus.pending;
  bool get isRunning => status == BackgroundTaskStatus.running;
  bool get isCompleted => status == BackgroundTaskStatus.completed;
  bool get isFailed => status == BackgroundTaskStatus.failed;
  bool get isCancelled => status == BackgroundTaskStatus.cancelled;
  bool get isActive => isPending || isRunning;
  bool get isTerminal => isCompleted || isFailed || isCancelled;

  int get progressPercent => (progress * 100).round();

  @override
  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'task_type': taskType.value,
        'name': name,
        'status': status.value,
        'progress': progress,
        'progress_message': progressMessage,
        'result_data': resultData,
        'error_message': errorMessage,
        'related_entity_id': relatedEntityId,
        'related_entity_type': relatedEntityType,
        'external_task_id': externalTaskId,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt?.toIso8601String(),
        'completed_at': completedAt?.toIso8601String(),
      };

  factory BackgroundTaskModel.fromJson(Map<String, dynamic> json) =>
      BackgroundTaskModel(
        id: json['id'] as String,
        userId: json['user_id'] as String,
        taskType: BackgroundTaskType.fromString(json['task_type'] as String),
        name: json['name'] as String,
        status: BackgroundTaskStatus.fromString(json['status'] as String),
        progress: (json['progress'] as num).toDouble(),
        progressMessage: json['progress_message'] as String?,
        resultData: json['result_data'] as Map<String, dynamic>?,
        errorMessage: json['error_message'] as String?,
        relatedEntityId: json['related_entity_id'] as String?,
        relatedEntityType: json['related_entity_type'] as String?,
        externalTaskId: json['external_task_id'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: json['updated_at'] == null
            ? null
            : DateTime.parse(json['updated_at'] as String),
        completedAt: json['completed_at'] == null
            ? null
            : DateTime.parse(json['completed_at'] as String),
      );

  BackgroundTaskModel copyWith({
    String? id,
    String? userId,
    BackgroundTaskType? taskType,
    String? name,
    BackgroundTaskStatus? status,
    double? progress,
    String? progressMessage,
    Map<String, dynamic>? resultData,
    String? errorMessage,
    String? relatedEntityId,
    String? relatedEntityType,
    String? externalTaskId,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? completedAt,
  }) =>
      BackgroundTaskModel(
        id: id ?? this.id,
        userId: userId ?? this.userId,
        taskType: taskType ?? this.taskType,
        name: name ?? this.name,
        status: status ?? this.status,
        progress: progress ?? this.progress,
        progressMessage: progressMessage ?? this.progressMessage,
        resultData: resultData ?? this.resultData,
        errorMessage: errorMessage ?? this.errorMessage,
        relatedEntityId: relatedEntityId ?? this.relatedEntityId,
        relatedEntityType: relatedEntityType ?? this.relatedEntityType,
        externalTaskId: externalTaskId ?? this.externalTaskId,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
        completedAt: completedAt ?? this.completedAt,
      );

  @override
  String toString() =>
      'BackgroundTaskModel(id: $id, name: $name, status: ${status.value})';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is BackgroundTaskModel &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;
}
