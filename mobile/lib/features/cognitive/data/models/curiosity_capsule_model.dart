import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

part 'curiosity_capsule_model.g.dart';

/// 胶囊深度级别
enum CapsuleDepthLevel {
  shallow('shallow', 'Light', '⚡'),
  medium('medium', 'Balanced', '💡'),
  deep('deep', 'Deep', '🔬');

  const CapsuleDepthLevel(this.value, this.label, this.emoji);

  final String value;
  final String label;
  final String emoji;

  static CapsuleDepthLevel fromValue(String? value) => CapsuleDepthLevel.values.firstWhere(
      (e) => e.value == value,
      orElse: () => CapsuleDepthLevel.medium,
    );
}

@JsonSerializable()
class CuriosityCapsuleModel {
  CuriosityCapsuleModel({
    required this.id,
    required this.title,
    required this.content,
    required this.isRead,
    required this.createdAt,
    this.relatedSubject,
    // 增强字段
    this.depthLevel,
    this.generationMethod,
    this.sourceContext,
    this.qualityScore,
    this.feedbackCount = 0,
    this.shareCount = 0,
    this.isFavorite = false,
  });

  factory CuriosityCapsuleModel.fromJson(Map<String, dynamic> json) =>
      _$CuriosityCapsuleModelFromJson(json);

  final String id;
  final String title;
  final String content;

  @JsonKey(name: 'is_read')
  final bool isRead;

  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  @JsonKey(name: 'related_subject')
  final String? relatedSubject;

  // 增强字段
  @JsonKey(name: 'depth_level')
  final String? depthLevel;

  @JsonKey(name: 'generation_method')
  final String? generationMethod;

  @JsonKey(name: 'source_context')
  final Map<String, dynamic>? sourceContext;

  @JsonKey(name: 'quality_score')
  final double? qualityScore;

  @JsonKey(name: 'feedback_count')
  final int feedbackCount;

  @JsonKey(name: 'share_count')
  final int shareCount;

  @JsonKey(name: 'is_favorite')
  final bool isFavorite;

  Map<String, dynamic> toJson() => _$CuriosityCapsuleModelToJson(this);

  /// 获取深度级别枚举
  CapsuleDepthLevel get depthLevelEnum =>
      CapsuleDepthLevel.fromValue(depthLevel);

  /// 获取深度级别emoji
  String get depthEmoji => depthLevelEnum.emoji;

  /// 获取本地化深度级别
  String get depthLabel {
    final l10n = I18nService.instance.l10n;
    switch (depthLevelEnum) {
      case CapsuleDepthLevel.shallow:
        return l10n.capsuleDepthShallow;
      case CapsuleDepthLevel.medium:
        return l10n.capsuleDepthMedium;
      case CapsuleDepthLevel.deep:
        return l10n.capsuleDepthDeep;
    }
  }

  /// 质量评级
  String get qualityRating {
    final l10n = I18nService.instance.l10n;
    if (qualityScore == null) return l10n.capsuleQualityUnrated;
    if (qualityScore! >= 0.8) return l10n.capsuleQualityExcellent;
    if (qualityScore! >= 0.6) return l10n.capsuleQualityGood;
    if (qualityScore! >= 0.4) return l10n.capsuleQualityFair;
    return l10n.capsuleQualityNeedsWork;
  }

  /// 复制对象并修改部分字段
  CuriosityCapsuleModel copyWith({
    String? id,
    String? title,
    String? content,
    bool? isRead,
    DateTime? createdAt,
    String? relatedSubject,
    String? depthLevel,
    String? generationMethod,
    Map<String, dynamic>? sourceContext,
    double? qualityScore,
    int? feedbackCount,
    int? shareCount,
    bool? isFavorite,
  }) => CuriosityCapsuleModel(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt ?? this.createdAt,
      relatedSubject: relatedSubject ?? this.relatedSubject,
      depthLevel: depthLevel ?? this.depthLevel,
      generationMethod: generationMethod ?? this.generationMethod,
      sourceContext: sourceContext ?? this.sourceContext,
      qualityScore: qualityScore ?? this.qualityScore,
      feedbackCount: feedbackCount ?? this.feedbackCount,
      shareCount: shareCount ?? this.shareCount,
      isFavorite: isFavorite ?? this.isFavorite,
    );
}
