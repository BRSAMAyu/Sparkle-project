import 'package:json_annotation/json_annotation.dart';

part 'curiosity_capsule_model.g.dart';

@JsonSerializable()
class CuriosityCapsuleModel {
  final String id;
  final String title;
  final String content;
  @JsonKey(name: 'is_read')
  final bool isRead;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'related_subject')
  final String? relatedSubject;

  CuriosityCapsuleModel({
    required this.id,
    required this.title,
    required this.content,
    required this.isRead,
    required this.createdAt,
    this.relatedSubject,
  });

  factory CuriosityCapsuleModel.fromJson(Map<String, dynamic> json) => _$CuriosityCapsuleModelFromJson(json);
  Map<String, dynamic> toJson() => _$CuriosityCapsuleModelToJson(this);
}