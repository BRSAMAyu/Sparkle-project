import 'package:json_annotation/json_annotation.dart';

part 'learning_path_node.g.dart';

@JsonSerializable()
class LearningPathNode {
  final String id;
  final String name;
  final String status; // 'locked', 'unlocked', 'mastered'
  
  @JsonKey(name: 'is_target')
  final bool isTarget;

  LearningPathNode({
    required this.id,
    required this.name,
    required this.status,
    this.isTarget = false,
  });

  factory LearningPathNode.fromJson(Map<String, dynamic> json) => _$LearningPathNodeFromJson(json);
  Map<String, dynamic> toJson() => _$LearningPathNodeToJson(this);
}
