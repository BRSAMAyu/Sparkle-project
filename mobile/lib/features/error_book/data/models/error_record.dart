import 'package:freezed_annotation/freezed_annotation.dart';

part 'error_record.freezed.dart';
part 'error_record.g.dart';

/// 错题记录模型
@freezed
class ErrorRecord with _$ErrorRecord {
  const factory ErrorRecord({
    required String id,
    @JsonKey(name: 'question_text') required String questionText,
    @JsonKey(name: 'user_answer') required String userAnswer,
    @JsonKey(name: 'correct_answer') required String correctAnswer,
    @JsonKey(name: 'subject_code') required String subject,
    @JsonKey(name: 'mastery_level') required double masteryLevel,
    @JsonKey(name: 'review_count') required int reviewCount,
    @JsonKey(name: 'created_at') required DateTime createdAt,
    @JsonKey(name: 'updated_at') required DateTime updatedAt,
    @JsonKey(name: 'question_image_url') String? questionImageUrl,
    String? chapter,
    int? difficulty,
    @JsonKey(name: 'next_review_at') DateTime? nextReviewAt,
    @JsonKey(name: 'last_reviewed_at') DateTime? lastReviewedAt,
    @JsonKey(name: 'latest_analysis') ErrorAnalysis? latestAnalysis,
    @JsonKey(name: 'knowledge_links')
    @Default([])
    List<KnowledgeLink> knowledgeLinks,
  }) = _ErrorRecord;

  factory ErrorRecord.fromJson(Map<String, dynamic> json) =>
      _$ErrorRecordFromJson(json);
}

/// AI 分析结果
@freezed
class ErrorAnalysis with _$ErrorAnalysis {
  const factory ErrorAnalysis({
    @JsonKey(name: 'error_type') required String errorType,
    @JsonKey(name: 'error_type_label') required String errorTypeLabel,
    @JsonKey(name: 'root_cause') required String rootCause,
    @JsonKey(name: 'correct_approach') required String correctApproach,
    @JsonKey(name: 'study_suggestion') required String studySuggestion,
    @JsonKey(name: 'analyzed_at') required DateTime analyzedAt,
    @JsonKey(name: 'similar_traps') @Default([]) List<String> similarTraps,
    @JsonKey(name: 'recommended_knowledge')
    @Default([])
    List<String> recommendedKnowledge,
  }) = _ErrorAnalysis;

  factory ErrorAnalysis.fromJson(Map<String, dynamic> json) =>
      _$ErrorAnalysisFromJson(json);
}

/// 关联知识点
@freezed
class KnowledgeLink with _$KnowledgeLink {
  const factory KnowledgeLink({
    @JsonKey(name: 'knowledge_node_id') required String nodeId,
    @JsonKey(name: 'node_name') required String nodeName,
    required double relevance,
    @JsonKey(name: 'is_primary') required bool isPrimary,
  }) = _KnowledgeLink;

  factory KnowledgeLink.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeLinkFromJson(json);
}

/// 列表响应封装
@freezed
class ErrorListResponse with _$ErrorListResponse {
  const factory ErrorListResponse({
    required List<ErrorRecord> items,
    required int total,
    required int page,
    @JsonKey(name: 'page_size') required int pageSize,
    @JsonKey(name: 'has_next') required bool hasNext,
  }) = _ErrorListResponse;

  factory ErrorListResponse.fromJson(Map<String, dynamic> json) =>
      _$ErrorListResponseFromJson(json);
}

/// 统计数据
@freezed
class ReviewStats with _$ReviewStats {
  const factory ReviewStats({
    @JsonKey(name: 'total_errors') required int totalErrors,
    @JsonKey(name: 'mastered_count') required int masteredCount,
    @JsonKey(name: 'need_review_count') required int needReviewCount,
    @JsonKey(name: 'review_streak_days') required int reviewStreakDays,
    @JsonKey(name: 'subject_distribution')
    required Map<String, int> subjectDistribution,
  }) = _ReviewStats;

  factory ReviewStats.fromJson(Map<String, dynamic> json) =>
      _$ReviewStatsFromJson(json);
}
