// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'error_record.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ErrorRecordImpl _$$ErrorRecordImplFromJson(Map<String, dynamic> json) =>
    _$ErrorRecordImpl(
      id: json['id'] as String,
      questionText: json['question_text'] as String,
      questionImageUrl: json['question_image_url'] as String?,
      userAnswer: json['user_answer'] as String,
      correctAnswer: json['correct_answer'] as String,
      subject: json['subject'] as String,
      chapter: json['chapter'] as String?,
      difficulty: (json['difficulty'] as num?)?.toInt(),
      masteryLevel: (json['mastery_level'] as num).toDouble(),
      reviewCount: (json['review_count'] as num).toInt(),
      nextReviewAt: json['next_review_at'] == null
          ? null
          : DateTime.parse(json['next_review_at'] as String),
      lastReviewedAt: json['last_reviewed_at'] == null
          ? null
          : DateTime.parse(json['last_reviewed_at'] as String),
      latestAnalysis: json['latest_analysis'] == null
          ? null
          : ErrorAnalysis.fromJson(
              json['latest_analysis'] as Map<String, dynamic>),
      knowledgeLinks: (json['knowledge_links'] as List<dynamic>?)
              ?.map((e) => KnowledgeLink.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$$ErrorRecordImplToJson(_$ErrorRecordImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'question_text': instance.questionText,
      'question_image_url': instance.questionImageUrl,
      'user_answer': instance.userAnswer,
      'correct_answer': instance.correctAnswer,
      'subject': instance.subject,
      'chapter': instance.chapter,
      'difficulty': instance.difficulty,
      'mastery_level': instance.masteryLevel,
      'review_count': instance.reviewCount,
      'next_review_at': instance.nextReviewAt?.toIso8601String(),
      'last_reviewed_at': instance.lastReviewedAt?.toIso8601String(),
      'latest_analysis': instance.latestAnalysis,
      'knowledge_links': instance.knowledgeLinks,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

_$ErrorAnalysisImpl _$$ErrorAnalysisImplFromJson(Map<String, dynamic> json) =>
    _$ErrorAnalysisImpl(
      errorType: json['error_type'] as String,
      errorTypeLabel: json['error_type_label'] as String,
      rootCause: json['root_cause'] as String,
      correctApproach: json['correct_approach'] as String,
      similarTraps: (json['similar_traps'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      recommendedKnowledge: (json['recommended_knowledge'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      studySuggestion: json['study_suggestion'] as String,
      analyzedAt: DateTime.parse(json['analyzed_at'] as String),
    );

Map<String, dynamic> _$$ErrorAnalysisImplToJson(_$ErrorAnalysisImpl instance) =>
    <String, dynamic>{
      'error_type': instance.errorType,
      'error_type_label': instance.errorTypeLabel,
      'root_cause': instance.rootCause,
      'correct_approach': instance.correctApproach,
      'similar_traps': instance.similarTraps,
      'recommended_knowledge': instance.recommendedKnowledge,
      'study_suggestion': instance.studySuggestion,
      'analyzed_at': instance.analyzedAt.toIso8601String(),
    };

_$KnowledgeLinkImpl _$$KnowledgeLinkImplFromJson(Map<String, dynamic> json) =>
    _$KnowledgeLinkImpl(
      nodeId: json['knowledge_node_id'] as String,
      nodeName: json['node_name'] as String,
      relevance: (json['relevance'] as num).toDouble(),
      isPrimary: json['is_primary'] as bool,
    );

Map<String, dynamic> _$$KnowledgeLinkImplToJson(_$KnowledgeLinkImpl instance) =>
    <String, dynamic>{
      'knowledge_node_id': instance.nodeId,
      'node_name': instance.nodeName,
      'relevance': instance.relevance,
      'is_primary': instance.isPrimary,
    };

_$ErrorListResponseImpl _$$ErrorListResponseImplFromJson(
        Map<String, dynamic> json) =>
    _$ErrorListResponseImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => ErrorRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
      page: (json['page'] as num).toInt(),
      pageSize: (json['page_size'] as num).toInt(),
      hasNext: json['has_next'] as bool,
    );

Map<String, dynamic> _$$ErrorListResponseImplToJson(
        _$ErrorListResponseImpl instance) =>
    <String, dynamic>{
      'items': instance.items,
      'total': instance.total,
      'page': instance.page,
      'page_size': instance.pageSize,
      'has_next': instance.hasNext,
    };

_$ReviewStatsImpl _$$ReviewStatsImplFromJson(Map<String, dynamic> json) =>
    _$ReviewStatsImpl(
      totalErrors: (json['total_errors'] as num).toInt(),
      masteredCount: (json['mastered_count'] as num).toInt(),
      needReviewCount: (json['need_review_count'] as num).toInt(),
      reviewStreakDays: (json['review_streak_days'] as num).toInt(),
      subjectDistribution:
          Map<String, int>.from(json['subject_distribution'] as Map),
    );

Map<String, dynamic> _$$ReviewStatsImplToJson(_$ReviewStatsImpl instance) =>
    <String, dynamic>{
      'total_errors': instance.totalErrors,
      'mastered_count': instance.masteredCount,
      'need_review_count': instance.needReviewCount,
      'review_streak_days': instance.reviewStreakDays,
      'subject_distribution': instance.subjectDistribution,
    };
