import 'package:flutter/material.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_layout_engine.dart';
import 'package:sparkle/features/galaxy/domain/entities/galaxy_llm_protocol.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// 知识星图 LLM 服务
///
/// 处理 LLM 发出的星图操作指令，包括：
/// - 添加知识节点
/// - 建立节点连接
/// - 移动节点位置
/// - 更新节点属性
class GalaxyLLMService {
  /// 当前节点列表
  final List<GalaxyNodeModel> _nodes = [];

  /// 当前边列表
  final List<GalaxyEdgeModel> _edges = [];

  /// 节点位置缓存
  final Map<String, Offset> _positions = {};

  /// 获取当前节点列表（只读）
  List<GalaxyNodeModel> get nodes => List.unmodifiable(_nodes);

  /// 获取当前边列表（只读）
  List<GalaxyEdgeModel> get edges => List.unmodifiable(_edges);

  /// 获取当前位置映射（只读）
  Map<String, Offset> get positions => Map.unmodifiable(_positions);

  /// 初始化服务（从后端加载数据）
  void initialize(List<GalaxyNodeModel> nodes, List<GalaxyEdgeModel> edges) {
    _nodes.clear();
    _edges.clear();
    _positions.clear();

    _nodes.addAll(nodes);
    _edges.addAll(edges);

    // 计算初始布局
    final initialPositions = GalaxyLayoutEngine.calculateInitialLayout(
      nodes: _nodes,
      edges: _edges,
    );
    _positions.addAll(initialPositions);
  }

  /// 执行 LLM 操作
  ///
  /// 返回操作结果，包括成功/失败状态和计算出的新位置
  LLMActionResult executeAction(LLMGalaxyAction action) {
    try {
      switch (action.action) {
        case LLMActionType.addNodes:
          return _handleAddNodes(action.nodes ?? []);
        case LLMActionType.updateNodes:
          return _handleUpdateNodes(action.nodes ?? []);
        case LLMActionType.deleteNodes:
          return _handleDeleteNodes(action.nodeIds ?? []);
        case LLMActionType.addConnections:
          return _handleAddConnections(action.connections ?? []);
        case LLMActionType.updateConnections:
          return _handleUpdateConnections(action.connections ?? []);
        case LLMActionType.removeConnections:
          return _handleRemoveConnections(action.connections ?? []);
        case LLMActionType.moveNodes:
          return _handleMoveNodes(action.moveSpecs ?? []);
        case LLMActionType.batchOperation:
          return _handleBatchOperation(action.batchActions ?? []);
      }
    } catch (e) {
      return LLMActionResult.failure('操作失败: $e');
    }
  }

  /// 处理添加节点
  LLMActionResult _handleAddNodes(List<LLMNodeSpec> specs) {
    final addedIds = <String>[];

    for (final spec in specs) {
      // 检查节点是否已存在
      if (_nodes.any((n) => n.id == spec.id)) {
        continue; // 跳过已存在的节点
      }

      // 创建节点
      final node = GalaxyNodeModel(
        id: spec.id,
        name: spec.name,
        importance: spec.importance,
        sector: spec.sector,
        isUnlocked: spec.isUnlocked,
        masteryScore: spec.masteryScore,
        parentId: spec.parentId,
        baseColor: spec.baseColor ?? _getDefaultColorForSector(spec.sector),
        tags: spec.tags,
        description: spec.description,
        positionHint: _convertPositionHint(spec.positionHint),
      );

      _nodes.add(node);
      addedIds.add(node.id);

      // 添加连接
      for (final conn in spec.connections) {
        final edgeId = 'edge_${spec.id}_${conn.targetId}';
        final edge = GalaxyEdgeModel(
          id: edgeId,
          sourceId: spec.id,
          targetId: conn.targetId,
          relationType: _convertRelationType(conn.relationType),
          strength: conn.strength,
          bidirectional: conn.bidirectional,
        );
        _edges.add(edge);
      }
    }

    // 重新计算布局
    _recalculateLayout();

    return LLMActionResult.successResult(
      addedNodeIds: addedIds,
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理更新节点
  LLMActionResult _handleUpdateNodes(List<LLMNodeSpec> specs) {
    final updatedIds = <String>[];

    for (final spec in specs) {
      final index = _nodes.indexWhere((n) => n.id == spec.id);
      if (index < 0) continue;

      final oldNode = _nodes[index];
      final newNode = oldNode.copyWith(
        name: spec.name,
        importance: spec.importance,
        sector: spec.sector,
        isUnlocked: spec.isUnlocked,
        masteryScore: spec.masteryScore,
        baseColor: spec.baseColor,
        tags: spec.tags,
        description: spec.description,
        positionHint: _convertPositionHint(spec.positionHint),
      );

      _nodes[index] = newNode;
      updatedIds.add(spec.id);
    }

    // 如果星域变化，重新计算布局
    if (updatedIds.isNotEmpty) {
      _recalculateLayout();
    }

    return LLMActionResult.successResult(
      updatedNodeIds: updatedIds,
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理删除节点
  LLMActionResult _handleDeleteNodes(List<String> nodeIds) {
    final deletedIds = <String>[];

    for (final nodeId in nodeIds) {
      // 删除节点
      _nodes.removeWhere((n) => n.id == nodeId);
      _positions.remove(nodeId);
      deletedIds.add(nodeId);

      // 删除相关的边
      _edges.removeWhere((e) => e.sourceId == nodeId || e.targetId == nodeId);
    }

    return LLMActionResult.successResult(
      deletedNodeIds: deletedIds,
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理添加连接
  LLMActionResult _handleAddConnections(List<LLMConnectionSpec> specs) {
    for (final spec in specs) {
      final edgeId = 'edge_${spec.sourceId}_${spec.targetId}';

      // 检查是否已存在
      if (_edges.any((e) => e.id == edgeId)) continue;

      final edge = GalaxyEdgeModel(
        id: edgeId,
        sourceId: spec.sourceId,
        targetId: spec.targetId,
        relationType: _convertRelationType(spec.relationType),
        strength: spec.strength,
        bidirectional: spec.bidirectional,
      );
      _edges.add(edge);
    }

    return LLMActionResult.successResult(
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理更新连接
  LLMActionResult _handleUpdateConnections(List<LLMConnectionSpec> specs) {
    for (final spec in specs) {
      final edgeId = 'edge_${spec.sourceId}_${spec.targetId}';
      final index = _edges.indexWhere((e) => e.id == edgeId);

      if (index >= 0) {
        _edges[index] = GalaxyEdgeModel(
          id: edgeId,
          sourceId: spec.sourceId,
          targetId: spec.targetId,
          relationType: _convertRelationType(spec.relationType),
          strength: spec.strength,
          bidirectional: spec.bidirectional,
        );
      }
    }

    return LLMActionResult.successResult(
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理移除连接
  LLMActionResult _handleRemoveConnections(List<LLMConnectionSpec> specs) {
    for (final spec in specs) {
      _edges.removeWhere(
        (e) => e.sourceId == spec.sourceId && e.targetId == spec.targetId,
      );
    }

    return LLMActionResult.successResult(
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理移动节点
  LLMActionResult _handleMoveNodes(List<LLMNodeMoveSpec> specs) {
    final movedIds = <String>[];

    for (final spec in specs) {
      final index = _nodes.indexWhere((n) => n.id == spec.nodeId);
      if (index < 0) continue;

      final oldNode = _nodes[index];
      final newNode = oldNode.copyWith(
        sector: spec.newSector ?? oldNode.sector,
        positionHint: _convertPositionHint(spec.positionHint),
      );

      _nodes[index] = newNode;
      movedIds.add(spec.nodeId);
    }

    // 重新计算布局
    _recalculateLayout();

    return LLMActionResult.successResult(
      updatedNodeIds: movedIds,
      computedPositions: _positionsToJson(),
    );
  }

  /// 处理批量操作
  LLMActionResult _handleBatchOperation(List<LLMGalaxyAction> actions) {
    final allAddedIds = <String>[];
    final allUpdatedIds = <String>[];
    final allDeletedIds = <String>[];

    for (final action in actions) {
      final result = executeAction(action);
      if (!result.success) {
        return result; // 如果有操作失败，立即返回
      }

      allAddedIds.addAll(result.addedNodeIds ?? []);
      allUpdatedIds.addAll(result.updatedNodeIds ?? []);
      allDeletedIds.addAll(result.deletedNodeIds ?? []);
    }

    return LLMActionResult.successResult(
      addedNodeIds: allAddedIds,
      updatedNodeIds: allUpdatedIds,
      deletedNodeIds: allDeletedIds,
      computedPositions: _positionsToJson(),
    );
  }

  /// 重新计算布局
  void _recalculateLayout() {
    final newPositions = GalaxyLayoutEngine.calculateInitialLayout(
      nodes: _nodes,
      edges: _edges,
      existingPositions: _positions,
    );
    _positions
      ..clear()
      ..addAll(newPositions);
  }

  /// 将位置转换为 JSON 格式
  Map<String, List<double>> _positionsToJson() =>
      _positions.map((key, value) => MapEntry(key, [value.dx, value.dy]));

  /// 获取星域默认颜色
  String _getDefaultColorForSector(SectorEnum sector) {
    final style = SectorConfig.getStyle(sector);
    final color = style.primaryColor;
    // 使用 color.toARGB32() 获取颜色值
    final argb = color.toARGB32();
    return '#${argb.toRadixString(16).padLeft(8, '0').substring(2)}';
  }

  /// 转换位置提示
  NodePositionHint? _convertPositionHint(PositionHint? hint) {
    if (hint == null) return null;

    return NodePositionHint(
      angleOffset: hint.angleOffset,
      radiusRatio: hint.radiusRatio,
      nearNodeId: hint.referenceNodeId,
      distanceFromReference: _distanceToPixels(hint.distance),
    );
  }

  /// 将相对距离转换为像素
  double? _distanceToPixels(RelativeDistance? distance) {
    if (distance == null) return null;
    switch (distance) {
      case RelativeDistance.veryClose:
        return 30.0;
      case RelativeDistance.close:
        return 60.0;
      case RelativeDistance.medium:
        return 120.0;
      case RelativeDistance.far:
        return 200.0;
      case RelativeDistance.veryFar:
        return 320.0;
    }
  }

  /// 转换关系类型
  EdgeRelationType _convertRelationType(RelationType type) {
    switch (type) {
      case RelationType.prerequisite:
        return EdgeRelationType.prerequisite;
      case RelationType.derived:
        return EdgeRelationType.derived;
      case RelationType.related:
        return EdgeRelationType.related;
      case RelationType.similar:
        return EdgeRelationType.similar;
      case RelationType.contrast:
        return EdgeRelationType.contrast;
      case RelationType.application:
        return EdgeRelationType.application;
      case RelationType.example:
        return EdgeRelationType.example;
    }
  }

  /// 从 JSON 解析 LLM 动作
  static LLMGalaxyAction? parseAction(Map<String, dynamic>? json) {
    if (json == null) return null;
    try {
      return LLMGalaxyAction.fromJson(json);
    } catch (e) {
      debugPrint('Error parsing LLM action: $e');
      return null;
    }
  }

  /// 创建添加节点的快捷方法
  static LLMGalaxyAction createAddNodeAction({
    required String id,
    required String name,
    required SectorEnum sector,
    int importance = 3,
    String? parentId,
    List<NodeConnection> connections = const [],
    PositionHint? positionHint,
  }) =>
      LLMGalaxyAction(
        action: LLMActionType.addNodes,
        nodes: [
          LLMNodeSpec(
            id: id,
            name: name,
            sector: sector,
            importance: importance,
            parentId: parentId,
            connections: connections,
            positionHint: positionHint,
          ),
        ],
      );

  /// 创建添加连接的快捷方法
  static LLMGalaxyAction createAddConnectionAction({
    required String sourceId,
    required String targetId,
    RelationType relationType = RelationType.related,
    double strength = 0.5,
    bool bidirectional = false,
  }) =>
      LLMGalaxyAction(
        action: LLMActionType.addConnections,
        connections: [
          LLMConnectionSpec(
            sourceId: sourceId,
            targetId: targetId,
            relationType: relationType,
            strength: strength,
            bidirectional: bidirectional,
          ),
        ],
      );
}
