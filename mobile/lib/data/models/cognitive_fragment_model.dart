import 'package:json_annotation/json_annotation.dart';

part 'cognitive_fragment_model.g.dart';

@JsonSerializable()
class CognitiveFragmentModel {
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'task_id')
  final String? taskId;
  @JsonKey(name: 'source_type')
  final String sourceType;
  final String content;
  final String? sentiment;
  final List<String>? tags;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  CognitiveFragmentModel({
    required this.id,
    required this.userId,
    required this.sourceType, required this.content, required this.createdAt, this.taskId,
    this.sentiment,
    this.tags,
  });

  factory CognitiveFragmentModel.fromJson(Map<String, dynamic> json) =>
      _$CognitiveFragmentModelFromJson(json);

  Map<String, dynamic> toJson() => _$CognitiveFragmentModelToJson(this);
}

@JsonSerializable()
class CognitiveFragmentCreate {
  final String content;
  @JsonKey(name: 'source_type')
  final String sourceType;
  @JsonKey(name: 'task_id')
  final String? taskId;

  CognitiveFragmentCreate({
    required this.content,
    required this.sourceType,
    this.taskId,
  });

  Map<String, dynamic> toJson() => _$CognitiveFragmentCreateToJson(this);
}
