import 'package:json_annotation/json_annotation.dart';

part 'learning_path_progress_model.g.dart';

@JsonSerializable()
class LearningPathProgressModel {
  LearningPathProgressModel({
    required this.nodes, required this.overallProgress, this.targetNode,
  });

  factory LearningPathProgressModel.fromJson(Map<String, dynamic> json) =>
      _$LearningPathProgressModelFromJson(json);

  @JsonKey(name: 'target_node')
  final LearningPathNodeProgress? targetNode;
  final List<LearningPathNodeProgress> nodes;
  @JsonKey(name: 'overall_progress')
  final double overallProgress;

  Map<String, dynamic> toJson() => _$LearningPathProgressModelToJson(this);
}

@JsonSerializable()
class LearningPathNodeProgress {
  LearningPathNodeProgress({
    required this.id,
    required this.name,
    required this.status,
    required this.mastery,
    this.isTarget = false,
  });

  factory LearningPathNodeProgress.fromJson(Map<String, dynamic> json) =>
      _$LearningPathNodeProgressFromJson(json);

  final String id;
  final String name;
  final String status;
  final int mastery;
  @JsonKey(name: 'is_target')
  final bool isTarget;

  Map<String, dynamic> toJson() => _$LearningPathNodeProgressToJson(this);
}
