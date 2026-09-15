import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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
    this.sourceDocuments = const [],
    this.knowledgeStats = const NodeKnowledgeStats(),
    this.learningPathSnapshot,
  });

  factory KnowledgeDetailResponse.fromJson(Map<String, dynamic> json) =>
      _$KnowledgeDetailResponseFromJson(json);
  final KnowledgeNodeDetail node;
  final List<NodeRelation> relations;
  final List<TaskModel> relatedTasks;
  final List<RelatedPlan> relatedPlans;
  @JsonKey(name: 'source_documents')
  final List<NodeSourceDocumentRef> sourceDocuments;
  @JsonKey(name: 'knowledge_stats')
  final NodeKnowledgeStats knowledgeStats;
  final KnowledgeUserStats userStats;
  @JsonKey(name: 'learningPathSnapshot')
  final LearningPathSnapshot? learningPathSnapshot;

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
    this.communitySignal,
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
  @JsonKey(name: 'community_signal')
  final Map<String, dynamic>? communitySignal;

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
    final l10n = I18nService.instance.l10n;
    switch (relationType) {
      case 'prerequisite':
        return l10n.knowledgeRelationPrerequisite;
      case 'related':
        return l10n.knowledgeRelationRelated;
      case 'application':
        return l10n.knowledgeRelationApplication;
      case 'composition':
        return l10n.knowledgeRelationComposition;
      case 'evolution':
        return l10n.knowledgeRelationEvolution;
      default:
        return l10n.knowledgeRelationDefault;
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
    final l10n = I18nService.instance.l10n;
    if (!isUnlocked) return l10n.knowledgeMasteryLevelLocked;
    if (masteryScore >= 95) return l10n.knowledgeMasteryLevelMastered;
    if (masteryScore >= 80) return l10n.knowledgeMasteryLevelBrilliant;
    if (masteryScore >= 30) return l10n.knowledgeMasteryLevelShining;
    if (masteryScore > 0) return l10n.knowledgeMasteryLevelGlimmer;
    return l10n.knowledgeMasteryLevelUnlit;
  }

  /// Get mastery progress (0.0 - 1.0)
  double get masteryProgress => (masteryScore / 100).clamp(0.0, 1.0);

  Map<String, dynamic> toJson() => _$KnowledgeUserStatsToJson(this);
}

@JsonSerializable()
class NodeSourceDocumentRef {
  NodeSourceDocumentRef({
    required this.fileId,
    required this.filename,
    this.fileType,
    this.uploadDate,
    this.chunkCount = 0,
    this.previewChunks = const [],
  });

  factory NodeSourceDocumentRef.fromJson(Map<String, dynamic> json) =>
      _$NodeSourceDocumentRefFromJson(json);

  @JsonKey(name: 'file_id')
  final String fileId;
  final String filename;
  @JsonKey(name: 'file_type')
  final String? fileType;
  @JsonKey(name: 'upload_date')
  final DateTime? uploadDate;
  @JsonKey(name: 'chunk_count')
  final int chunkCount;
  @JsonKey(name: 'preview_chunks')
  final List<String> previewChunks;

  String get normalizedFileType {
    final lowerName = filename.toLowerCase();
    final lowerType = (fileType ?? '').toLowerCase();
    if (lowerName.endsWith('.pdf') || lowerType.contains('pdf')) return 'pdf';
    if (lowerName.endsWith('.docx') ||
        lowerName.endsWith('.doc') ||
        lowerType.contains('word') ||
        lowerType.contains('msword')) {
      return 'docx';
    }
    if (lowerName.endsWith('.pptx') ||
        lowerName.endsWith('.ppt') ||
        lowerType.contains('presentationml') ||
        lowerType.contains('powerpoint')) {
      return 'pptx';
    }
    if (lowerName.endsWith('.md') ||
        lowerName.endsWith('.markdown') ||
        lowerType.contains('markdown')) {
      return 'md';
    }
    if (lowerType.startsWith('image/')) return 'image';
    return 'file';
  }

  Map<String, dynamic> toJson() => _$NodeSourceDocumentRefToJson(this);
}

@JsonSerializable()
class NodeKnowledgeStats {
  const NodeKnowledgeStats({
    this.totalDocuments = 0,
    this.totalChunks = 0,
    this.hasPersonalUploads = false,
    this.lastMaterialAdded,
  });

  factory NodeKnowledgeStats.fromJson(Map<String, dynamic> json) =>
      _$NodeKnowledgeStatsFromJson(json);

  @JsonKey(name: 'total_documents')
  final int totalDocuments;
  @JsonKey(name: 'total_chunks')
  final int totalChunks;
  @JsonKey(name: 'has_personal_uploads')
  final bool hasPersonalUploads;
  @JsonKey(name: 'last_material_added')
  final DateTime? lastMaterialAdded;

  Map<String, dynamic> toJson() => _$NodeKnowledgeStatsToJson(this);
}

@JsonSerializable()
class NodeSourceChunk {
  NodeSourceChunk({
    required this.chunkId,
    required this.fileId,
    required this.filename,
    required this.chunkIndex,
    required this.content,
    required this.preview,
    this.fileType,
    this.pageNumbers = const [],
    this.sectionTitle,
    this.qualityScore,
    this.createdAt,
  });

  factory NodeSourceChunk.fromJson(Map<String, dynamic> json) =>
      _$NodeSourceChunkFromJson(json);

  @JsonKey(name: 'chunk_id')
  final String chunkId;
  @JsonKey(name: 'file_id')
  final String fileId;
  final String filename;
  @JsonKey(name: 'file_type')
  final String? fileType;
  @JsonKey(name: 'chunk_index')
  final int chunkIndex;
  final String content;
  final String preview;
  @JsonKey(name: 'page_numbers')
  final List<int> pageNumbers;
  @JsonKey(name: 'section_title')
  final String? sectionTitle;
  @JsonKey(name: 'quality_score')
  final double? qualityScore;
  @JsonKey(name: 'created_at')
  final DateTime? createdAt;

  String get displayPreview {
    final trimmed = preview.trim();
    if (trimmed.isNotEmpty) {
      return trimmed;
    }
    return content.trim();
  }

  Map<String, dynamic> toJson() => _$NodeSourceChunkToJson(this);
}

@JsonSerializable()
class NodeChunksResponse {
  NodeChunksResponse({
    required this.nodeId,
    this.chunks = const [],
    this.total = 0,
    this.page = 1,
    this.pageSize = 20,
    this.totalPages = 0,
    this.hasNext = false,
    this.hasPrev = false,
  });

  factory NodeChunksResponse.fromJson(Map<String, dynamic> json) =>
      _$NodeChunksResponseFromJson(json);

  @JsonKey(name: 'node_id')
  final String nodeId;
  final List<NodeSourceChunk> chunks;
  final int total;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  @JsonKey(name: 'total_pages')
  final int totalPages;
  @JsonKey(name: 'has_next')
  final bool hasNext;
  @JsonKey(name: 'has_prev')
  final bool hasPrev;

  Map<String, dynamic> toJson() => _$NodeChunksResponseToJson(this);
}

@JsonSerializable()
class LearningPathSnapshot {
  LearningPathSnapshot({
    required this.mode,
    required this.summary,
    this.taskCount = 0,
    this.tasks = const [],
    this.selectedRelatedNodeIds = const [],
    this.generatedAt,
  });

  factory LearningPathSnapshot.fromJson(Map<String, dynamic> json) =>
      _$LearningPathSnapshotFromJson(json);

  final String mode;
  final String summary;
  @JsonKey(name: 'task_count')
  final int taskCount;
  final List<LearningPathSnapshotTask> tasks;
  @JsonKey(name: 'selected_related_node_ids')
  final List<String> selectedRelatedNodeIds;
  @JsonKey(name: 'generated_at')
  final DateTime? generatedAt;

  Map<String, dynamic> toJson() => _$LearningPathSnapshotToJson(this);
}

@JsonSerializable()
class LearningPathSnapshotTask {
  LearningPathSnapshotTask({
    required this.id,
    required this.title,
    required this.type,
    required this.estimatedMinutes,
    required this.status,
    this.knowledgeNodeId,
    this.guideContent,
  });

  factory LearningPathSnapshotTask.fromJson(Map<String, dynamic> json) =>
      _$LearningPathSnapshotTaskFromJson(json);

  final String id;
  final String title;
  final String type;
  @JsonKey(name: 'estimated_minutes')
  final int estimatedMinutes;
  final String status;
  @JsonKey(name: 'knowledge_node_id')
  final String? knowledgeNodeId;
  @JsonKey(name: 'guide_content')
  final String? guideContent;

  Map<String, dynamic> toJson() => _$LearningPathSnapshotTaskToJson(this);
}
