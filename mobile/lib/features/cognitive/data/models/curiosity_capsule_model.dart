import 'package:json_annotation/json_annotation.dart';

part 'curiosity_capsule_model.g.dart';

/// 胶囊深度级别
enum CapsuleDepthLevel {
  shallow('shallow', '浅度', '⚡'),
  medium('medium', '中度', '💡'),
  deep('deep', '深度', '🔬');

  const CapsuleDepthLevel(this.value, this.label, this.emoji);

  final String value;
  final String label;
  final String emoji;

  static CapsuleDepthLevel fromValue(String? value) {
    return CapsuleDepthLevel.values.firstWhere(
      (e) => e.value == value,
      orElse: () => CapsuleDepthLevel.medium,
    );
  }
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

  /// 质量评级
  String get qualityRating {
    if (qualityScore == null) return '未评级';
    if (qualityScore! >= 0.8) return '优秀';
    if (qualityScore! >= 0.6) return '良好';
    if (qualityScore! >= 0.4) return '一般';
    return '待改进';
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
  }) {
    return CuriosityCapsuleModel(
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
}
