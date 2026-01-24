import 'package:sparkle/shared/models/base_model.dart';

/// Subtask status enumeration
enum SubTaskStatus {
  pending('PENDING'),
  inProgress('IN_PROGRESS'),
  completed('COMPLETED');

  final String value;
  const SubTaskStatus(this.value);

  static SubTaskStatus fromString(String value) => SubTaskStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => SubTaskStatus.pending,
    );
}

/// Subtask model
class SubTaskModel extends BaseModel {

  factory SubTaskModel.fromJson(Map<String, dynamic> json) => SubTaskModel(
        id: json['id'] as String,
        parentTaskId: json['parent_task_id'] as String,
        title: json['title'] as String,
        description: json['description'] as String?,
        order: json['order'] as int,
        status: SubTaskStatus.fromString(json['status'] as String),
        completedAt: json['completed_at'] == null
            ? null
            : DateTime.parse(json['completed_at'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );
  SubTaskModel({
    required this.id,
    required this.parentTaskId,
    required this.title,
    required this.order, required this.status, required this.createdAt, required this.updatedAt, this.description,
    this.completedAt,
  });

  final String id;
  final String parentTaskId;
  final String title;
  final String? description;
  final int order;
  final SubTaskStatus status;
  final DateTime? completedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isCompleted => status == SubTaskStatus.completed;

  @override
  Map<String, dynamic> toJson() => {
        'id': id,
        'parent_task_id': parentTaskId,
        'title': title,
        'description': description,
        'order': order,
        'status': status.value,
        'completed_at': completedAt?.toIso8601String(),
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
      };

  SubTaskModel copyWith({
    String? id,
    String? parentTaskId,
    String? title,
    String? description,
    int? order,
    SubTaskStatus? status,
    DateTime? completedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) =>
      SubTaskModel(
        id: id ?? this.id,
        parentTaskId: parentTaskId ?? this.parentTaskId,
        title: title ?? this.title,
        description: description ?? this.description,
        order: order ?? this.order,
        status: status ?? this.status,
        completedAt: completedAt ?? this.completedAt,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );

  @override
  String toString() =>
      'SubTaskModel(id: $id, title: $title, status: ${status.value})';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SubTaskModel &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;
}

/// Subtask create model
class SubTaskCreate {
  const SubTaskCreate({
    required this.title,
    this.description,
    this.order = 0,
  });

  final String title;
  final String? description;
  final int order;

  Map<String, dynamic> toJson() => {
        'title': title,
        if (description != null) 'description': description,
        'order': order,
      };
}

/// Subtask update model
class SubTaskUpdate {
  const SubTaskUpdate({
    this.title,
    this.description,
    this.status,
    this.order,
  });

  final String? title;
  final String? description;
  final SubTaskStatus? status;
  final int? order;

  Map<String, dynamic> toJson() => {
        if (title != null) 'title': title,
        if (description != null) 'description': description,
        if (status != null) 'status': status!.value,
        if (order != null) 'order': order,
      };

  bool get hasChanges =>
      title != null || description != null || status != null || order != null;
}

/// Subtask reorder item
class SubTaskReorderItem {
  const SubTaskReorderItem({
    required this.subtaskId,
    required this.order,
  });

  final String subtaskId;
  final int order;

  Map<String, dynamic> toJson() => {
        'subtask_id': subtaskId,
        'order': order,
      };
}
