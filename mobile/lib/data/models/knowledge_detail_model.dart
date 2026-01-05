import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

part 'knowledge_detail_model.g.dart';

/// Knowledge node detail response from API
@JsonSerializable()
class KnowledgeDetailResponse {
  KnowledgeDetailResponse({
    required this.node,
    required this.userStats,
    this.relations = const [],
    this.relatedTasks = const [],
    this.relatedPlans = const [],
  });

  factory KnowledgeDetailResponse.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeDetailResponseFromJson(json);
  final KnowledgeNodeDetail node;
  final List<NodeRelation> relations;
  final List<TaskModel> relatedTasks;
  final List<RelatedPlan> relatedPlans;
  final KnowledgeUserStats userStats;

  Map<String, dynamic> toJson() => _$KnowledgeDetailResponseToJson(this);
}

/// Detailed knowledge node information
@JsonSerializable()
class KnowledgeNodeDetail {
  KnowledgeNodeDetail({
    required this.id,
    required this.name,
    this.nameEn,
    this.description,
    this.keywords = const [],
    this.importanceLevel = 1,
    this.sectorCode = 'VOID',
    this.isSeed = false,
    this.sourceType = 'seed',
    this.parentId,
    this.subjectId,
    this.subjectName,
    this.createdAt,
  });

  factory KnowledgeNodeDetail.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeNodeDetailFromJson(json);
  final String id;
  final String name;
  @JsonKey(name: 'name_en')
  final String? nameEn;
  final String? description;
  final List<String> keywords;
  @JsonKey(name: 'importance_level')
  final int importanceLevel;
  @JsonKey(name: 'sector_code')
  final String sectorCode;
  @JsonKey(name: 'is_seed')
  final bool isSeed;
  @JsonKey(name: 'source_type')
  final String sourceType;
  @JsonKey(name: 'parent_id')
  final String? parentId;
  @JsonKey(name: 'subject_id')
  final int? subjectId;
  @JsonKey(name: 'subject_name')
  final String? subjectName;
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  /// Convert sectorCode string to SectorEnum
  SectorEnum get sector {
    switch (sectorCode.toUpperCase()) {
      case 'COSMOS':
        return SectorEnum.cosmos;
      case 'TECH':
        return SectorEnum.tech;
      case 'ART':
        return SectorEnum.art;
      case 'CIVILIZATION':
        return SectorEnum.civilization;
      case 'LIFE':
        return SectorEnum.life;
      case 'WISDOM':
        return SectorEnum.wisdom;
      default:
        return SectorEnum.voidSector;
    }
  }

  Map<String, dynamic> toJson() => _$KnowledgeNodeDetailToJson(this);
}

/// Node relation (edge in the knowledge graph)
@JsonSerializable()
class NodeRelation {
  NodeRelation({
    required this.id,
    required this.sourceNodeId,
    required this.targetNodeId,
    required this.relationType,
    this.strength = 0.5,
    this.sourceNodeName,
    this.targetNodeName,
  });

  factory NodeRelation.fromJson(Map<String, dynamic> json) =>
      _$NodeRelationFromJson(json);
  final String id;
  @JsonKey(name: 'source_node_id')
  final String sourceNodeId;
  @JsonKey(name: 'target_node_id')
  final String targetNodeId;
  @JsonKey(name: 'relation_type')
  final String relationType;
  final double strength;
  @JsonKey(name: 'source_node_name')
  final String? sourceNodeName;
  @JsonKey(name: 'target_node_name')
  final String? targetNodeName;

  /// Get a human-readable label for the relation type
  String get relationLabel {
    switch (relationType) {
      case 'prerequisite':
        return '前置知识';
      case 'related':
        return '相关知识';
      case 'application':
        return '应用';
      case 'composition':
        return '组成部分';
      case 'evolution':
        return '演进';
      default:
        return '关联';
    }
  }

  Map<String, dynamic> toJson() => _$NodeRelationToJson(this);
}

/// Related plan brief info
@JsonSerializable()
class RelatedPlan {
  RelatedPlan({
    required this.id,
    required this.title,
    required this.planType,
    required this.status,
    this.targetDate,
  });

  factory RelatedPlan.fromJson(Map<String, dynamic> json) =>
      _$RelatedPlanFromJson(json);
  final String id;
  final String title;
  @JsonKey(name: 'plan_type')
  final String planType;
  final String status;
  @JsonKey(name: 'target_date')
  final DateTime? targetDate;

  Map<String, dynamic> toJson() => _$RelatedPlanToJson(this);
}

/// User's stats for this knowledge node
@JsonSerializable()
class KnowledgeUserStats {
  KnowledgeUserStats({
    this.masteryScore = 0,
    this.totalStudyMinutes = 0,
    this.studyCount = 0,
    this.isUnlocked = false,
    this.isFavorite = false,
    this.lastStudyAt,
    this.nextReviewAt,
    this.decayPaused = false,
  });

  factory KnowledgeUserStats.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeUserStatsFromJson(json);
  @JsonKey(name: 'mastery_score')
  final double masteryScore;
  @JsonKey(name: 'total_study_minutes')
  final int totalStudyMinutes;
  @JsonKey(name: 'study_count')
  final int studyCount;
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;
  @JsonKey(name: 'is_favorite')
  final bool isFavorite;
  @JsonKey(name: 'last_study_at')
  final DateTime? lastStudyAt;
  @JsonKey(name: 'next_review_at')
  final DateTime? nextReviewAt;
  @JsonKey(name: 'decay_paused')
  final bool decayPaused;

  /// Get the mastery level label
  String get masteryLabel {
    if (!isUnlocked) return '未解锁';
    if (masteryScore >= 95) return '精通';
    if (masteryScore >= 80) return '璀璨';
    if (masteryScore >= 30) return '闪耀';
    if (masteryScore > 0) return '微光';
    return '未点亮';
  }

  /// Get mastery progress (0.0 - 1.0)
  double get masteryProgress => (masteryScore / 100).clamp(0.0, 1.0);

  Map<String, dynamic> toJson() => _$KnowledgeUserStatsToJson(this);
}
