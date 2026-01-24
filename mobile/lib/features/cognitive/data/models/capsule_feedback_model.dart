import 'package:json_annotation/json_annotation.dart';

part 'capsule_feedback_model.g.dart';

/// 反馈分类
enum FeedbackCategory {
  tooLong('too_long', '太长了'),
  tooShort('too_short', '太短了'),
  justRight('just_right', '刚刚好'),
  tooComplex('too_complex', '太复杂'),
  tooSimple('too_simple', '太简单'),
  irrelevant('irrelevant', '不相关'),
  other('other', '其他');

  const FeedbackCategory(this.value, this.label);

  final String value;
  final String label;

  static FeedbackCategory fromValue(String? value) => FeedbackCategory.values.firstWhere(
      (e) => e.value == value,
      orElse: () => FeedbackCategory.other,
    );
}

@JsonSerializable()
class CapsuleFeedbackModel {
  CapsuleFeedbackModel({
    required this.id,
    required this.capsuleId,
    required this.createdAt,
    this.rating,
    this.helpful,
    this.category,
    this.comment,
  });

  factory CapsuleFeedbackModel.fromJson(Map<String, dynamic> json) =>
      _$CapsuleFeedbackModelFromJson(json);

  final String id;

  @JsonKey(name: 'capsule_id')
  final String capsuleId;

  final int? rating; // 1-5
  final bool? helpful;
  final String? category;
  final String? comment;

  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  Map<String, dynamic> toJson() => _$CapsuleFeedbackModelToJson(this);

  /// 获取反馈分类枚举
  FeedbackCategory? get categoryEnum =>
      category != null ? FeedbackCategory.fromValue(category) : null;
}
