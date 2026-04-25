import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

part 'error_record.freezed.dart';
part 'error_record.g.dart';

String _stringFromJson(Object? value) {
  if (value == null) {
    return '';
  }
  return value.toString();
}

String? _nullableStringFromJson(Object? value) {
  final text = value?.toString();
  if (text == null || text.isEmpty) {
    return null;
  }
  return text;
}

int _intFromJson(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}

double? _nullableDoubleFromJson(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  if (value is String) {
    return double.tryParse(value);
  }
  return null;
}

Map<String, int> _intMapFromJson(Object? value) {
  if (value is! Map) {
    return const <String, int>{};
  }
  return value.map(
    (key, dynamic item) => MapEntry(key.toString(), _intFromJson(item)),
  );
}

/// 错题记录模型
@freezed
class ErrorRecord with _$ErrorRecord {
  const factory ErrorRecord({
    required String id,
    @JsonKey(name: 'question_text', fromJson: _stringFromJson)
    required String questionText,
    @JsonKey(name: 'user_answer', fromJson: _stringFromJson)
    required String userAnswer,
    @JsonKey(name: 'correct_answer', fromJson: _stringFromJson)
    required String correctAnswer,
    @JsonKey(name: 'subject_code', fromJson: _stringFromJson)
    required String subject,
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
    @JsonKey(name: 'affected_node_id', fromJson: _nullableStringFromJson)
    String? affectedNodeId,
    @JsonKey(name: 'mastery_delta', fromJson: _nullableDoubleFromJson)
    double? masteryDelta,
    @JsonKey(name: 'cognitive_tags')
    @Default([])
    List<CognitiveDimension> cognitiveTags,
    @JsonKey(name: 'ai_analysis_summary') String? aiAnalysisSummary,
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
    @JsonKey(name: 'analyzed_at') DateTime? analyzedAt,
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
    @JsonKey(name: 'id') required String nodeId,
    @JsonKey(name: 'name') required String nodeName,
    @Default(1.0) double relevance,
    @JsonKey(name: 'is_primary') @Default(false) bool isPrimary,
  }) = _KnowledgeLink;

  factory KnowledgeLink.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeLinkFromJson(json);
}

/// 列表响应封装
@freezed
class ErrorListResponse with _$ErrorListResponse {
  const factory ErrorListResponse({
    required List<ErrorRecord> items,
    @JsonKey(fromJson: _intFromJson) required int total,
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
    @JsonKey(name: 'total_errors', fromJson: _intFromJson)
    required int totalErrors,
    @JsonKey(name: 'mastered_count', fromJson: _intFromJson)
    required int masteredCount,
    @JsonKey(name: 'need_review_count', fromJson: _intFromJson)
    required int needReviewCount,
    @JsonKey(name: 'review_streak_days') required int reviewStreakDays,
    @JsonKey(name: 'subject_distribution', fromJson: _intMapFromJson)
    required Map<String, int> subjectDistribution,
  }) = _ReviewStats;

  factory ReviewStats.fromJson(Map<String, dynamic> json) =>
      _$ReviewStatsFromJson(json);
}
