// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'knowledge_detail_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

KnowledgeDetailResponse _$KnowledgeDetailResponseFromJson(
        Map<String, dynamic> json) =>
    KnowledgeDetailResponse(
      node: KnowledgeNodeDetail.fromJson(json['node'] as Map<String, dynamic>),
      userStats: KnowledgeUserStats.fromJson(
          json['userStats'] as Map<String, dynamic>),
      relations: (json['relations'] as List<dynamic>?)
              ?.map((e) => NodeRelation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      relatedTasks: (json['relatedTasks'] as List<dynamic>?)
              ?.map((e) => TaskModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      relatedPlans: (json['relatedPlans'] as List<dynamic>?)
              ?.map((e) => RelatedPlan.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$KnowledgeDetailResponseToJson(
        KnowledgeDetailResponse instance) =>
    <String, dynamic>{
      'node': instance.node,
      'relations': instance.relations,
      'relatedTasks': instance.relatedTasks,
      'relatedPlans': instance.relatedPlans,
      'userStats': instance.userStats,
    };

KnowledgeNodeDetail _$KnowledgeNodeDetailFromJson(Map<String, dynamic> json) =>
    KnowledgeNodeDetail(
      id: json['id'] as String,
      name: json['name'] as String,
      nameEn: json['name_en'] as String?,
      description: json['description'] as String?,
      keywords: (json['keywords'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      importanceLevel: (json['importance_level'] as num?)?.toInt() ?? 1,
      sectorCode: json['sector_code'] as String? ?? 'VOID',
      isSeed: json['is_seed'] as bool? ?? false,
      sourceType: json['source_type'] as String? ?? 'seed',
      parentId: json['parent_id'] as String?,
      subjectId: (json['subject_id'] as num?)?.toInt(),
      subjectName: json['subject_name'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$KnowledgeNodeDetailToJson(
        KnowledgeNodeDetail instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'name_en': instance.nameEn,
      'description': instance.description,
      'keywords': instance.keywords,
      'importance_level': instance.importanceLevel,
      'sector_code': instance.sectorCode,
      'is_seed': instance.isSeed,
      'source_type': instance.sourceType,
      'parent_id': instance.parentId,
      'subject_id': instance.subjectId,
      'subject_name': instance.subjectName,
      'created_at': instance.createdAt?.toIso8601String(),
    };

NodeRelation _$NodeRelationFromJson(Map<String, dynamic> json) => NodeRelation(
      id: json['id'] as String,
      sourceNodeId: json['source_node_id'] as String,
      targetNodeId: json['target_node_id'] as String,
      relationType: json['relation_type'] as String,
      strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      sourceNodeName: json['source_node_name'] as String?,
      targetNodeName: json['target_node_name'] as String?,
    );

Map<String, dynamic> _$NodeRelationToJson(NodeRelation instance) =>
    <String, dynamic>{
      'id': instance.id,
      'source_node_id': instance.sourceNodeId,
      'target_node_id': instance.targetNodeId,
      'relation_type': instance.relationType,
      'strength': instance.strength,
      'source_node_name': instance.sourceNodeName,
      'target_node_name': instance.targetNodeName,
    };

RelatedPlan _$RelatedPlanFromJson(Map<String, dynamic> json) => RelatedPlan(
      id: json['id'] as String,
      title: json['title'] as String,
      planType: json['plan_type'] as String,
      status: json['status'] as String,
      targetDate: json['target_date'] == null
          ? null
          : DateTime.parse(json['target_date'] as String),
    );

Map<String, dynamic> _$RelatedPlanToJson(RelatedPlan instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'plan_type': instance.planType,
      'status': instance.status,
      'target_date': instance.targetDate?.toIso8601String(),
    };

KnowledgeUserStats _$KnowledgeUserStatsFromJson(Map<String, dynamic> json) =>
    KnowledgeUserStats(
      masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
      totalStudyMinutes: (json['total_study_minutes'] as num?)?.toInt() ?? 0,
      studyCount: (json['study_count'] as num?)?.toInt() ?? 0,
      isUnlocked: json['is_unlocked'] as bool? ?? false,
      isFavorite: json['is_favorite'] as bool? ?? false,
      lastStudyAt: json['last_study_at'] == null
          ? null
          : DateTime.parse(json['last_study_at'] as String),
      nextReviewAt: json['next_review_at'] == null
          ? null
          : DateTime.parse(json['next_review_at'] as String),
      decayPaused: json['decay_paused'] as bool? ?? false,
    );

Map<String, dynamic> _$KnowledgeUserStatsToJson(KnowledgeUserStats instance) =>
    <String, dynamic>{
      'mastery_score': instance.masteryScore,
      'total_study_minutes': instance.totalStudyMinutes,
      'study_count': instance.studyCount,
      'is_unlocked': instance.isUnlocked,
      'is_favorite': instance.isFavorite,
      'last_study_at': instance.lastStudyAt?.toIso8601String(),
      'next_review_at': instance.nextReviewAt?.toIso8601String(),
      'decay_paused': instance.decayPaused,
    };
