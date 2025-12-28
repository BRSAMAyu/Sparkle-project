import 'package:json_annotation/json_annotation.dart';

part 'behavior_pattern_model.g.dart';

@JsonSerializable()
class BehaviorPatternModel {

  BehaviorPatternModel({
    required this.id,
    required this.userId,
    required this.patternName,
    required this.patternType,
    required this.isArchived, required this.createdAt, required this.updatedAt, this.description,
    this.solutionText,
    this.evidenceIds,
  });

  factory BehaviorPatternModel.fromJson(Map<String, dynamic> json) =>
      _$BehaviorPatternModelFromJson(json);
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  @JsonKey(name: 'pattern_name')
  final String patternName;
  @JsonKey(name: 'pattern_type')
  final String patternType;
  final String? description;
  @JsonKey(name: 'solution_text')
  final String? solutionText;
  @JsonKey(name: 'evidence_ids')
  final List<String>? evidenceIds; // List of CognitiveFragment IDs
  @JsonKey(name: 'is_archived')
  final bool isArchived;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  Map<String, dynamic> toJson() => _$BehaviorPatternModelToJson(this);
}
