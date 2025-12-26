import 'package:json_annotation/json_annotation.dart';

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
  prerequisite,   // 前置知识
  @JsonValue('derived')
  derived,        // 衍生知识
  @JsonValue('related')
  related,        // 相关知识
  @JsonValue('similar')
  similar,        // 相似概念
  @JsonValue('contrast')
  contrast,       // 对比概念
  @JsonValue('application')
  application,    // 应用场景
  @JsonValue('example')
  example,        // 具体示例
  @JsonValue('parent_child')
  parentChild,    // 父子层级关系
}

/// 节点边/连接模型
@JsonSerializable()
class GalaxyEdgeModel {
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

  const GalaxyEdgeModel({
    required this.id,
    required this.sourceId,
    required this.targetId,
    this.relationType = EdgeRelationType.related,
    this.strength = 0.5,
    this.bidirectional = false,
  });

  factory GalaxyEdgeModel.fromJson(Map<String, dynamic> json) =>
      _$GalaxyEdgeModelFromJson(json);
  Map<String, dynamic> toJson() => _$GalaxyEdgeModelToJson(this);
}

/// LLM 提供的位置提示
@JsonSerializable()
class NodePositionHint {
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

  const NodePositionHint({
    this.angleOffset,
    this.radiusRatio,
    this.nearNodeId,
    this.distanceFromReference,
  });

  factory NodePositionHint.fromJson(Map<String, dynamic> json) =>
      _$NodePositionHintFromJson(json);
  Map<String, dynamic> toJson() => _$NodePositionHintToJson(this);

  bool get hasValidHint =>
      angleOffset != null ||
      radiusRatio != null ||
      nearNodeId != null;
}

@JsonSerializable()
class GalaxyNodeModel {
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
  });

  factory GalaxyNodeModel.fromJson(Map<String, dynamic> json) =>
      _$GalaxyNodeModelFromJson(json);
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
  }) {
    return GalaxyNodeModel(
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
    );
  }
}

@JsonSerializable()
class GalaxyGraphResponse {
  final List<GalaxyNodeModel> nodes;

  /// 节点间的连接关系
  final List<GalaxyEdgeModel> edges;

  @JsonKey(name: 'user_flame_intensity')
  final double userFlameIntensity;

  GalaxyGraphResponse({
    required this.nodes,
    this.edges = const [],
    required this.userFlameIntensity,
  });

  factory GalaxyGraphResponse.fromJson(Map<String, dynamic> json) =>
      _$GalaxyGraphResponseFromJson(json);
  Map<String, dynamic> toJson() => _$GalaxyGraphResponseToJson(this);

  /// 获取特定节点的所有出边
  List<GalaxyEdgeModel> getOutgoingEdges(String nodeId) {
    return edges.where((e) => e.sourceId == nodeId).toList();
  }

  /// 获取特定节点的所有入边
  List<GalaxyEdgeModel> getIncomingEdges(String nodeId) {
    return edges.where((e) => e.targetId == nodeId).toList();
  }

  /// 获取特定节点的所有相连边
  List<GalaxyEdgeModel> getAllEdgesFor(String nodeId) {
    return edges.where((e) =>
      e.sourceId == nodeId ||
      e.targetId == nodeId ||
      (e.bidirectional && e.targetId == nodeId)
    ).toList();
  }
}

@JsonSerializable(createFactory: false)
class GalaxySearchResult {
  final GalaxyNodeModel node;
  final double similarity;

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
}

@JsonSerializable()
class GalaxySearchResponse {
  final String query;
  final List<GalaxySearchResult> results;
  @JsonKey(name: 'total_count')
  final int totalCount;

  GalaxySearchResponse({
    required this.query,
    required this.results,
    required this.totalCount,
  });

  factory GalaxySearchResponse.fromJson(Map<String, dynamic> json) =>
      _$GalaxySearchResponseFromJson(json);
  Map<String, dynamic> toJson() => _$GalaxySearchResponseToJson(this);
}
