import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

part 'galaxy_llm_protocol.g.dart';

/// LLM 知识星图交互协议
///
/// 该协议定义了 LLM 如何向星图系统发送指令来：
/// 1. 添加新的知识节点
/// 2. 建立节点之间的连接
/// 3. 指定节点的位置提示
/// 4. 更新节点属性
///
/// 示例 LLM 响应:
/// ```json
/// {
///   "action": "add_nodes",
///   "nodes": [
///     {
///       "id": "node_123",
///       "name": "微积分基础",
///       "sector": "COSMOS",
///       "importance": 4,
///       "position_hint": {
///         "strategy": "near_node",
///         "reference_node_id": "node_100",
///         "distance": "close"
///       },
///       "connections": [
///         {"target_id": "node_100", "relation_type": "prerequisite", "strength": 0.9},
///         {"target_id": "node_101", "relation_type": "related", "strength": 0.6}
///       ]
///     }
///   ]
/// }
/// ```

/// LLM 操作类型
enum LLMActionType {
  @JsonValue('add_nodes')
  addNodes,
  @JsonValue('update_nodes')
  updateNodes,
  @JsonValue('delete_nodes')
  deleteNodes,
  @JsonValue('add_connections')
  addConnections,
  @JsonValue('update_connections')
  updateConnections,
  @JsonValue('remove_connections')
  removeConnections,
  @JsonValue('move_nodes')
  moveNodes,
  @JsonValue('batch_operation')
  batchOperation,
}

/// 位置策略枚举
enum PositionStrategy {
  /// 相对于画布中心的极坐标
  @JsonValue('polar')
  polar,

  /// 靠近某个参考节点
  @JsonValue('near_node')
  nearNode,

  /// 在星域的特定区域
  @JsonValue('sector_region')
  sectorRegion,

  /// 自动布局（让算法决定）
  @JsonValue('auto')
  auto,

  /// 绝对坐标（调试用）
  @JsonValue('absolute')
  absolute,
}

/// 距离枚举
enum RelativeDistance {
  @JsonValue('very_close')
  veryClose,  // 20-40px
  @JsonValue('close')
  close,      // 40-80px
  @JsonValue('medium')
  medium,     // 80-150px
  @JsonValue('far')
  far,        // 150-250px
  @JsonValue('very_far')
  veryFar,    // 250-400px
}

/// 星域区域
enum SectorRegion {
  @JsonValue('inner')
  inner,      // 靠近中心
  @JsonValue('middle')
  middle,     // 中间区域
  @JsonValue('outer')
  outer,      // 边缘区域
  @JsonValue('center_angle')
  centerAngle, // 星域中心角度
}

/// 关系类型
enum RelationType {
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
}

/// 位置提示
@JsonSerializable()
class PositionHint {
  final PositionStrategy strategy;

  /// 极坐标：相对于星域中心的角度偏移 (0.0-1.0, 映射到星域角度范围)
  @JsonKey(name: 'angle_offset')
  final double? angleOffset;

  /// 极坐标：到中心的距离 (0.0-1.0, 0是中心，1是边缘)
  @JsonKey(name: 'radius_ratio')
  final double? radiusRatio;

  /// nearNode 策略：参考节点 ID
  @JsonKey(name: 'reference_node_id')
  final String? referenceNodeId;

  /// nearNode 策略：相对距离
  final RelativeDistance? distance;

  /// sectorRegion 策略：区域
  final SectorRegion? region;

  /// absolute 策略：绝对 X 坐标
  final double? x;

  /// absolute 策略：绝对 Y 坐标
  final double? y;

  const PositionHint({
    required this.strategy,
    this.angleOffset,
    this.radiusRatio,
    this.referenceNodeId,
    this.distance,
    this.region,
    this.x,
    this.y,
  });

  factory PositionHint.fromJson(Map<String, dynamic> json) =>
      _$PositionHintFromJson(json);
  Map<String, dynamic> toJson() => _$PositionHintToJson(this);

  /// 自动布局的默认提示
  static const PositionHint auto = PositionHint(strategy: PositionStrategy.auto);

  /// 星域中间区域
  static PositionHint sectorMiddle() => const PositionHint(
    strategy: PositionStrategy.sectorRegion,
    region: SectorRegion.middle,
  );

  /// 靠近某节点
  static PositionHint nearTo(String nodeId, {RelativeDistance dist = RelativeDistance.close}) =>
    PositionHint(
      strategy: PositionStrategy.nearNode,
      referenceNodeId: nodeId,
      distance: dist,
    );
}

/// 节点连接定义
@JsonSerializable()
class NodeConnection {
  /// 目标节点 ID
  @JsonKey(name: 'target_id')
  final String targetId;

  /// 关系类型
  @JsonKey(name: 'relation_type')
  final RelationType relationType;

  /// 连接强度 (0.0-1.0)，影响线条粗细和颜色
  final double strength;

  /// 是否双向连接
  @JsonKey(name: 'bidirectional')
  final bool bidirectional;

  const NodeConnection({
    required this.targetId,
    required this.relationType,
    this.strength = 0.5,
    this.bidirectional = false,
  });

  factory NodeConnection.fromJson(Map<String, dynamic> json) =>
      _$NodeConnectionFromJson(json);
  Map<String, dynamic> toJson() => _$NodeConnectionToJson(this);
}

/// LLM 节点创建请求
@JsonSerializable()
class LLMNodeSpec {
  final String id;
  final String name;

  /// 所属星域
  final SectorEnum sector;

  /// 重要程度 1-5
  final int importance;

  /// 节点颜色（可选，默认使用星域颜色）
  @JsonKey(name: 'base_color')
  final String? baseColor;

  /// 掌握度 0-100
  @JsonKey(name: 'mastery_score')
  final int masteryScore;

  /// 是否已解锁
  @JsonKey(name: 'is_unlocked')
  final bool isUnlocked;

  /// 位置提示
  @JsonKey(name: 'position_hint')
  final PositionHint? positionHint;

  /// 连接定义
  final List<NodeConnection> connections;

  /// 标签
  final List<String> tags;

  /// 简短描述
  final String? description;

  /// 父节点 ID（层级关系）
  @JsonKey(name: 'parent_id')
  final String? parentId;

  const LLMNodeSpec({
    required this.id,
    required this.name,
    required this.sector,
    this.importance = 3,
    this.baseColor,
    this.masteryScore = 0,
    this.isUnlocked = true,
    this.positionHint,
    this.connections = const [],
    this.tags = const [],
    this.description,
    this.parentId,
  });

  factory LLMNodeSpec.fromJson(Map<String, dynamic> json) =>
      _$LLMNodeSpecFromJson(json);
  Map<String, dynamic> toJson() => _$LLMNodeSpecToJson(this);
}

/// 节点移动请求
@JsonSerializable()
class LLMNodeMoveSpec {
  @JsonKey(name: 'node_id')
  final String nodeId;

  /// 新的星域（可选）
  @JsonKey(name: 'new_sector')
  final SectorEnum? newSector;

  /// 新的位置提示
  @JsonKey(name: 'position_hint')
  final PositionHint positionHint;

  const LLMNodeMoveSpec({
    required this.nodeId,
    this.newSector,
    required this.positionHint,
  });

  factory LLMNodeMoveSpec.fromJson(Map<String, dynamic> json) =>
      _$LLMNodeMoveSpecFromJson(json);
  Map<String, dynamic> toJson() => _$LLMNodeMoveSpecToJson(this);
}

/// LLM 操作请求
@JsonSerializable()
class LLMGalaxyAction {
  final LLMActionType action;

  /// 添加/更新节点列表
  final List<LLMNodeSpec>? nodes;

  /// 删除节点 ID 列表
  @JsonKey(name: 'node_ids')
  final List<String>? nodeIds;

  /// 添加连接列表
  final List<LLMConnectionSpec>? connections;

  /// 移动节点列表
  @JsonKey(name: 'move_specs')
  final List<LLMNodeMoveSpec>? moveSpecs;

  /// 批量操作列表
  @JsonKey(name: 'batch_actions')
  final List<LLMGalaxyAction>? batchActions;

  /// 操作元数据
  final Map<String, dynamic>? metadata;

  const LLMGalaxyAction({
    required this.action,
    this.nodes,
    this.nodeIds,
    this.connections,
    this.moveSpecs,
    this.batchActions,
    this.metadata,
  });

  factory LLMGalaxyAction.fromJson(Map<String, dynamic> json) =>
      _$LLMGalaxyActionFromJson(json);
  Map<String, dynamic> toJson() => _$LLMGalaxyActionToJson(this);
}

/// 连接规格
@JsonSerializable()
class LLMConnectionSpec {
  @JsonKey(name: 'source_id')
  final String sourceId;

  @JsonKey(name: 'target_id')
  final String targetId;

  @JsonKey(name: 'relation_type')
  final RelationType relationType;

  final double strength;

  final bool bidirectional;

  const LLMConnectionSpec({
    required this.sourceId,
    required this.targetId,
    required this.relationType,
    this.strength = 0.5,
    this.bidirectional = false,
  });

  factory LLMConnectionSpec.fromJson(Map<String, dynamic> json) =>
      _$LLMConnectionSpecFromJson(json);
  Map<String, dynamic> toJson() => _$LLMConnectionSpecToJson(this);
}

/// LLM 操作结果
@JsonSerializable()
class LLMActionResult {
  final bool success;
  final String? error;

  /// 新添加节点的 ID 列表
  @JsonKey(name: 'added_node_ids')
  final List<String>? addedNodeIds;

  /// 更新节点的 ID 列表
  @JsonKey(name: 'updated_node_ids')
  final List<String>? updatedNodeIds;

  /// 删除节点的 ID 列表
  @JsonKey(name: 'deleted_node_ids')
  final List<String>? deletedNodeIds;

  /// 计算出的节点位置
  @JsonKey(name: 'computed_positions')
  final Map<String, List<double>>? computedPositions;

  const LLMActionResult({
    required this.success,
    this.error,
    this.addedNodeIds,
    this.updatedNodeIds,
    this.deletedNodeIds,
    this.computedPositions,
  });

  factory LLMActionResult.fromJson(Map<String, dynamic> json) =>
      _$LLMActionResultFromJson(json);
  Map<String, dynamic> toJson() => _$LLMActionResultToJson(this);

  static LLMActionResult successResult({
    List<String>? addedNodeIds,
    List<String>? updatedNodeIds,
    List<String>? deletedNodeIds,
    Map<String, List<double>>? computedPositions,
  }) => LLMActionResult(
    success: true,
    addedNodeIds: addedNodeIds,
    updatedNodeIds: updatedNodeIds,
    deletedNodeIds: deletedNodeIds,
    computedPositions: computedPositions,
  );

  static LLMActionResult failure(String error) => LLMActionResult(
    success: false,
    error: error,
  );
}
