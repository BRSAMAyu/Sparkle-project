import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/shared/models/compact_knowledge_node.dart';

part 'galaxy_model.g.dart';

enum SectorEnum {
  @JsonValue('COSMOS')
  cosmos,
  @JsonValue('TECH')
  tech,
  @JsonValue('ART')
  art,
  @JsonValue('CIVILIZATION')
  civilization,
  @JsonValue('LIFE')
  life,
  @JsonValue('WISDOM')
  wisdom,
  @JsonValue('VOID')
  voidSector
}

/// 关系类型枚举
enum EdgeRelationType {
  @JsonValue('prerequisite')
  prerequisite, // 前置知识
  @JsonValue('derived')
  derived, // 衍生知识
  @JsonValue('related')
  related, // 相关知识
  @JsonValue('similar')
  similar, // 相似概念
  @JsonValue('contrast')
  contrast, // 对比概念
  @JsonValue('application')
  application, // 应用场景
  @JsonValue('example')
  example, // 具体示例
  @JsonValue('parent_child')
  parentChild, // 父子层级关系
}

/// 节点边/连接模型
@JsonSerializable()
class GalaxyEdgeModel {
  const GalaxyEdgeModel({
    required this.id,
    required this.sourceId,
    required this.targetId,
    this.relationType = EdgeRelationType.related,
    this.strength = 0.5,
    this.bidirectional = false,
  });

  factory GalaxyEdgeModel.fromJson(Map<String, dynamic> json) {
    final sourceId =
        (json['source_id'] ?? json['source_node_id'] ?? '').toString();
    final targetId =
        (json['target_id'] ?? json['target_node_id'] ?? '').toString();
    final relationRaw = json['relation_type']?.toString();

    return GalaxyEdgeModel(
      id: (json['id'] ?? '${sourceId}_${targetId}_${relationRaw ?? 'related'}')
          .toString(),
      sourceId: sourceId,
      targetId: targetId,
      relationType: _parseRelationType(relationRaw),
      strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      bidirectional: json['bidirectional'] as bool? ?? false,
    );
  }
  final String id;

  @JsonKey(name: 'source_id')
  final String sourceId;

  @JsonKey(name: 'target_id')
  final String targetId;

  @JsonKey(name: 'relation_type')
  final EdgeRelationType relationType;

  /// 连接强度 0.0-1.0
  final double strength;

  /// 是否双向
  final bool bidirectional;
  Map<String, dynamic> toJson() => _$GalaxyEdgeModelToJson(this);

  static EdgeRelationType _parseRelationType(String? raw) {
    return EdgeRelationType.values.firstWhere(
      (type) => type.name == raw || _relationWireValue(type) == raw,
      orElse: () => EdgeRelationType.related,
    );
  }

  static String _relationWireValue(EdgeRelationType type) {
    switch (type) {
      case EdgeRelationType.parentChild:
        return 'parent_child';
      default:
        return type.name;
    }
  }
}

/// LLM 提供的位置提示
@JsonSerializable()
class NodePositionHint {
  const NodePositionHint({
    this.angleOffset,
    this.radiusRatio,
    this.nearNodeId,
    this.distanceFromReference,
  });

  factory NodePositionHint.fromJson(Map<String, dynamic> json) =>
      _$NodePositionHintFromJson(json);

  /// 在星域内的角度偏移 (0.0-1.0)
  @JsonKey(name: 'angle_offset')
  final double? angleOffset;

  /// 到中心的半径比例 (0.0-1.0)
  @JsonKey(name: 'radius_ratio')
  final double? radiusRatio;

  /// 靠近的参考节点 ID
  @JsonKey(name: 'near_node_id')
  final String? nearNodeId;

  /// 与参考节点的距离 (像素)
  @JsonKey(name: 'distance_from_reference')
  final double? distanceFromReference;
  Map<String, dynamic> toJson() => _$NodePositionHintToJson(this);

  bool get hasValidHint =>
      angleOffset != null || radiusRatio != null || nearNodeId != null;
}

@JsonSerializable()
class GalaxyNodeModel {
  GalaxyNodeModel({
    required this.id,
    required this.name,
    required this.importance,
    required this.sector,
    required this.isUnlocked,
    required this.masteryScore,
    this.studyCount = 0,
    this.parentId,
    this.baseColor,
    this.tags,
    this.description,
    this.positionHint,
    this.outgoingEdgeIds,
    this.incomingEdgeIds,
    this.positionX,
    this.positionY,
  });

  factory GalaxyNodeModel.fromJson(Map<String, dynamic> json) {
    final userStatus = json['user_status'] as Map<String, dynamic>?;

    return GalaxyNodeModel(
      id: json['id'] as String,
      parentId: json['parent_id']?.toString(),
      name: json['name'] as String,
      importance:
          ((json['importance'] ?? json['importance_level']) as num?)?.toInt() ??
              1,
      sector: _parseSector(json['sector_code']),
      baseColor: json['base_color'] as String?,
      isUnlocked: (json['is_unlocked'] as bool?) ??
          (userStatus?['is_unlocked'] as bool?) ??
          false,
      masteryScore:
          ((json['mastery_score'] ?? userStatus?['mastery_score']) as num?)
                  ?.toInt() ??
              0,
      studyCount: (GalaxyNodeModel._readStudyCount(json, 'study_count') as num?)
              ?.toInt() ??
          0,
      tags: ((json['auto_tags'] ?? json['tags'] ?? json['keywords'])
              as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
      description: json['description'] as String?,
      positionHint: json['position_hint'] == null
          ? null
          : NodePositionHint.fromJson(
              json['position_hint'] as Map<String, dynamic>,
            ),
      outgoingEdgeIds: (json['outgoing_edge_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      incomingEdgeIds: (json['incoming_edge_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      positionX: (json['position_x'] as num?)?.toDouble(),
      positionY: (json['position_y'] as num?)?.toDouble(),
    );
  }
  final String id;

  @JsonKey(name: 'parent_id')
  final String? parentId;

  final String name;

  /// 重要程度 1-5
  final int importance;

  @JsonKey(name: 'sector_code')
  final SectorEnum sector;

  @JsonKey(name: 'base_color')
  final String? baseColor;

  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;

  @JsonKey(name: 'mastery_score')
  final int masteryScore;

  @JsonKey(name: 'study_count', readValue: _readStudyCount, defaultValue: 0)
  final int studyCount;

  /// 节点标签
  final List<String>? tags;

  /// 简短描述
  final String? description;

  /// LLM 提供的位置提示
  @JsonKey(name: 'position_hint')
  final NodePositionHint? positionHint;

  /// 出边 ID 列表（该节点作为 source）
  @JsonKey(name: 'outgoing_edge_ids')
  final List<String>? outgoingEdgeIds;

  /// 入边 ID 列表（该节点作为 target）
  @JsonKey(name: 'incoming_edge_ids')
  final List<String>? incomingEdgeIds;

  @JsonKey(name: 'position_x')
  final double? positionX;

  @JsonKey(name: 'position_y')
  final double? positionY;
  Map<String, dynamic> toJson() => _$GalaxyNodeModelToJson(this);

  /// Helper to read study_count from nested user_status if present
  static Object? _readStudyCount(Map<dynamic, dynamic> json, String key) {
    if (json.containsKey('study_count')) return json['study_count'];
    if (json['user_status'] != null && json['user_status'] is Map) {
      return (json['user_status'] as Map)['study_count'];
    }
    return 0;
  }

  /// 节点半径（基于重要程度）
  double get radius => 3.0 + importance * 2.0;

  bool get hasStablePosition => positionX != null && positionY != null;

  List<String> get autoTags => tags ?? const [];

  /// Convert to CompactKnowledgeNode for rendering
  CompactKnowledgeNode toCompact(double x, double y) =>
      CompactKnowledgeNode.create(
        id: id,
        parentId: parentId,
        name: name,
        x: x,
        y: y,
        mastery: masteryScore,
        isUnlocked: isUnlocked,
        isMastered: masteryScore >= 100,
        sectorIndex: sector.index,
        importance: importance,
        studyCount: studyCount,
        primaryTag: autoTags.isEmpty ? null : autoTags.first,
      );

  /// 复制并修改
  GalaxyNodeModel copyWith({
    String? id,
    String? parentId,
    String? name,
    int? importance,
    SectorEnum? sector,
    String? baseColor,
    bool? isUnlocked,
    int? masteryScore,
    int? studyCount,
    List<String>? tags,
    String? description,
    NodePositionHint? positionHint,
    List<String>? outgoingEdgeIds,
    List<String>? incomingEdgeIds,
    double? positionX,
    double? positionY,
  }) =>
      GalaxyNodeModel(
        id: id ?? this.id,
        parentId: parentId ?? this.parentId,
        name: name ?? this.name,
        importance: importance ?? this.importance,
        sector: sector ?? this.sector,
        baseColor: baseColor ?? this.baseColor,
        isUnlocked: isUnlocked ?? this.isUnlocked,
        masteryScore: masteryScore ?? this.masteryScore,
        studyCount: studyCount ?? this.studyCount,
        tags: tags ?? this.tags,
        description: description ?? this.description,
        positionHint: positionHint ?? this.positionHint,
        outgoingEdgeIds: outgoingEdgeIds ?? this.outgoingEdgeIds,
        incomingEdgeIds: incomingEdgeIds ?? this.incomingEdgeIds,
        positionX: positionX ?? this.positionX,
        positionY: positionY ?? this.positionY,
      );

  static SectorEnum _parseSector(Object? raw) {
    final value = raw?.toString();
    return SectorEnum.values.firstWhere(
      (sector) => sector.name == value || _sectorWireValue(sector) == value,
      orElse: () => SectorEnum.voidSector,
    );
  }

  static String _sectorWireValue(SectorEnum sector) {
    switch (sector) {
      case SectorEnum.voidSector:
        return 'VOID';
      default:
        return sector.name.toUpperCase();
    }
  }
}

@JsonSerializable()
class GalaxyGraphResponse {
  GalaxyGraphResponse({
    required this.nodes,
    required this.userFlameIntensity,
    this.edges = const [],
  });

  factory GalaxyGraphResponse.fromJson(Map<String, dynamic> json) {
    final rawEdges = (json['edges'] ?? json['relations'] ?? const <dynamic>[])
        as List<dynamic>;

    return GalaxyGraphResponse(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) => GalaxyNodeModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      userFlameIntensity:
          (json['user_flame_intensity'] as num?)?.toDouble() ?? 0.0,
      edges: rawEdges
          .map((e) => GalaxyEdgeModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
  final List<GalaxyNodeModel> nodes;

  /// 节点间的连接关系
  final List<GalaxyEdgeModel> edges;

  @JsonKey(name: 'user_flame_intensity')
  final double userFlameIntensity;
  Map<String, dynamic> toJson() => _$GalaxyGraphResponseToJson(this);

  /// 获取特定节点的所有出边
  List<GalaxyEdgeModel> getOutgoingEdges(String nodeId) =>
      edges.where((e) => e.sourceId == nodeId).toList();

  /// 获取特定节点的所有入边
  List<GalaxyEdgeModel> getIncomingEdges(String nodeId) =>
      edges.where((e) => e.targetId == nodeId).toList();

  /// 获取特定节点的所有相连边
  List<GalaxyEdgeModel> getAllEdgesFor(String nodeId) => edges
      .where(
        (e) =>
            e.sourceId == nodeId ||
            e.targetId == nodeId ||
            (e.bidirectional && e.targetId == nodeId),
      )
      .toList();
}

@JsonSerializable(createFactory: false)
class GalaxySearchResult {
  GalaxySearchResult({required this.node, required this.similarity});

  factory GalaxySearchResult.fromJson(Map<String, dynamic> json) {
    final nodeJson = json['node'] as Map<String, dynamic>;
    final statusJson = json['user_status'] as Map<String, dynamic>?;

    // Flatten for GalaxyNodeModel
    final flatJson = Map<String, dynamic>.from(nodeJson);
    if (statusJson != null) {
      flatJson.addAll(statusJson);
    } else {
      // Defaults
      flatJson['mastery_score'] = 0;
      flatJson['is_unlocked'] = false;
    }

    // Handle sector_code if nested or root
    // Usually handled by GalaxyNodeModel's JsonKey, but here we prep the map.
    // If backend sends 'sector_code' inside 'node', it is already in flatJson.

    return GalaxySearchResult(
      node: GalaxyNodeModel.fromJson(flatJson),
      similarity: (json['similarity'] as num).toDouble(),
    );
  }
  final GalaxyNodeModel node;
  final double similarity;
}

@JsonSerializable()
class GalaxySearchResponse {
  GalaxySearchResponse({
    required this.query,
    required this.results,
    required this.totalCount,
  });

  factory GalaxySearchResponse.fromJson(Map<String, dynamic> json) =>
      _$GalaxySearchResponseFromJson(json);
  final String query;
  final List<GalaxySearchResult> results;
  @JsonKey(name: 'total_count')
  final int totalCount;
  Map<String, dynamic> toJson() => _$GalaxySearchResponseToJson(this);
}
