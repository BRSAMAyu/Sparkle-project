import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

part 'capsule_feedback_model.g.dart';

/// 反馈分类
enum FeedbackCategory {
  tooLong('too_long', 'Too long'),
  tooShort('too_short', 'Too short'),
  justRight('just_right', 'Just right'),
  tooComplex('too_complex', 'Too complex'),
  tooSimple('too_simple', 'Too simple'),
  irrelevant('irrelevant', 'Irrelevant'),
  other('other', 'Other');

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

  String? get categoryLabel {
    final value = categoryEnum;
    if (value == null) return null;
    final l10n = I18nService.instance.l10n;
    switch (value) {
      case FeedbackCategory.tooLong:
        return l10n.capsuleFeedbackTooLong;
      case FeedbackCategory.tooShort:
        return l10n.capsuleFeedbackTooShort;
      case FeedbackCategory.justRight:
        return l10n.capsuleFeedbackJustRight;
      case FeedbackCategory.tooComplex:
        return l10n.capsuleFeedbackTooComplex;
      case FeedbackCategory.tooSimple:
        return l10n.capsuleFeedbackTooSimple;
      case FeedbackCategory.irrelevant:
        return l10n.capsuleFeedbackIrrelevant;
      case FeedbackCategory.other:
        return l10n.capsuleFeedbackOther;
    }
  }
}
