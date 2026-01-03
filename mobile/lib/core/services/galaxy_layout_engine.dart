import 'dart:math';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/quad_tree.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

/// 高性能星域布局引擎
///
/// 功能：
/// 1. 基于 6+1 星域系统进行节点布局
/// 2. 支持 LLM 位置提示
/// 3. 防止节点重叠
/// 4. 在 Isolate 中进行力导向优化
class GalaxyLayoutEngine {
  /// 布局常量
  static const double minNodeSpacing = 120.0; // 显著增加节点间距
  static const double sectorRootRadius = 350.0; // 星域根节点半径外移
  static const double universeCenterRadius = 0.0;
  static const double innerRadius = 150.0; // 核心区域半径扩大
  static const double outerRadius = 2500.0; // 宇宙边界扩大
  static const double sectorPadding = 5.0;

  /// 计算初始布局（快速，在主线程）
  static Map<String, Offset> calculateInitialLayout({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    Map<String, Offset>? existingPositions,
  }) {
    final positions = <String, Offset>{};
    final random = Random(42);

    // 1. 建立父子索引和星域分组
    final childrenMap = <String, List<String>>{};
    final sectorRoots = <SectorEnum, List<GalaxyNodeModel>>{};
    
    // 初始化 map
    for (final sector in SectorEnum.values) {
      sectorRoots[sector] = [];
    }

    for (final node in nodes) {
      if (node.parentId != null) {
        childrenMap.putIfAbsent(node.parentId!, () => []);
        childrenMap[node.parentId]!.add(node.id);
      } else {
        // 没有父节点的作为该星域的根节点
        sectorRoots[node.sector]?.add(node);
      }
    }

    // 2. 布局星域根节点 (Sector Roots)
    for (final entry in sectorRoots.entries) {
      final sector = entry.key;
      final roots = entry.value;
      if (roots.isEmpty) continue;

      final style = SectorConfig.getStyle(sector);
      // 星域中心角度
      final centerAngleRad = (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
      
      // 将多个根节点分布在扇形中心附近
      for (var i = 0; i < roots.length; i++) {
        final node = roots[i];
        
        // 优先复用现有位置
        if (existingPositions != null && existingPositions.containsKey(node.id)) {
          positions[node.id] = existingPositions[node.id]!;
          _layoutChildrenRecursive(
            node.id, 
            positions[node.id]!, 
            childrenMap, 
            positions, 
            nodes, 
            style, 
            random,
            existingPositions,
          );
          continue;
        }

        // 计算根节点位置 - 增加随机散布范围
        var angle = centerAngleRad;
        if (roots.length > 1) {
          final spread = (style.sweepAngle * 0.6) * pi / 180; // 更宽的分布
          final step = spread / (roots.length + 1);
          angle = centerAngleRad - spread / 2 + step * (i + 1);
        }

        // 增加径向随机性
        final radius = sectorRootRadius + (random.nextDouble() - 0.5) * 150;
        final pos = Offset(radius * cos(angle), radius * sin(angle));
        
        positions[node.id] = pos;
        
        // 递归布局子节点
        _layoutChildrenRecursive(
          node.id, 
          pos, 
          childrenMap, 
          positions, 
          nodes, 
          style, 
          random,
          existingPositions,
        );
      }
    }

    // 3. 处理孤立节点（如果有）或未处理的节点（可能是循环依赖导致的）
    for (final node in nodes) {
      if (!positions.containsKey(node.id)) {
         final style = SectorConfig.getStyle(node.sector);
         final centerAngleRad = (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
         final radius = sectorRootRadius * 2.0 + random.nextDouble() * 200;
         positions[node.id] = Offset(radius * cos(centerAngleRad), radius * sin(centerAngleRad));
      }
    }

    // 4. 碰撞检测和松弛
    _resolveOverlaps(positions, nodes);

    return positions;
  }

  /// 递归布局子节点
  static void _layoutChildrenRecursive(
    String parentId,
    Offset parentPos,
    Map<String, List<String>> childrenMap,
    Map<String, Offset> positions,
    List<GalaxyNodeModel> allNodes,
    SectorStyle style,
    Random random,
    Map<String, Offset>? existingPositions,
  ) {
    final childrenIds = childrenMap[parentId];
    if (childrenIds == null || childrenIds.isEmpty) return;

    // 获取子节点对象
    final children = allNodes.where((n) => childrenIds.contains(n.id)).toList();
    // 按重要性排序
    children.sort((a, b) => b.importance.compareTo(a.importance));

    // 父节点到中心的角度
    final parentAngle = atan2(parentPos.dy, parentPos.dx);
    final parentDist = parentPos.distance;

    // 扇形分布范围 - 随距离增加而减小
    var spreadAngle = pi / 2.5; // 72度 - 初始更宽
    if (parentDist > 800) spreadAngle = pi / 4;

    for (var i = 0; i < children.length; i++) {
      final child = children[i];
      
      if (existingPositions != null && existingPositions.containsKey(child.id)) {
        positions[child.id] = existingPositions[child.id]!;
        _layoutChildrenRecursive(child.id, positions[child.id]!, childrenMap, positions, allNodes, style, random, existingPositions);
        continue;
      }

      // 计算位置 - 增加基础间距
      // 基础距离：根据重要性递减，但整体增大
      final distStep = 120.0 + (5 - child.importance) * 30.0; 
      final childDist = parentDist + distStep;

      // 角度偏移
      // 将子节点分布在父节点向外的扇形区域内
      double angleOffset = 0;
      if (children.length > 1) {
        angleOffset = (i - (children.length - 1) / 2) * (spreadAngle / children.length);
      }
      // 添加更多随机扰动以打破人工感
      angleOffset += (random.nextDouble() - 0.5) * 0.2;

      final childAngle = parentAngle + angleOffset;

      final pos = Offset(childDist * cos(childAngle), childDist * sin(childAngle));
      
      positions[child.id] = pos;

      // 递归
      _layoutChildrenRecursive(child.id, pos, childrenMap, positions, allNodes, style, random, existingPositions);
    }
  }

  /// 解决节点重叠 - 使用四叉树优化碰撞检测
  static void _resolveOverlaps(
    Map<String, Offset> positions,
    List<GalaxyNodeModel> nodes,
  ) {
    const maxIterations = 50;
    const pushForce = 0.8;

    // 使用四叉树加速碰撞检测
    for (var iter = 0; iter < maxIterations; iter++) {
      var hasOverlap = false;

      // 构建四叉树
      final tree = QuadTree<_LayoutNode>(
        bounds: const Rect.fromLTWH(
          -outerRadius * 1.5,
          -outerRadius * 1.5,
          outerRadius * 3,
          outerRadius * 3,
        ),
        capacity: 8,
      );

      // 插入所有节点
      for (final node in nodes) {
        final pos = positions[node.id];
        if (pos != null) {
          tree.insert(_LayoutNode(
            id: node.id,
            position: pos,
            radius: node.radius,
          ),);
        }
      }

      // 使用四叉树查询邻近节点进行碰撞检测
      for (final node in nodes) {
        final posA = positions[node.id];
        if (posA == null) continue;

        // 查询可能碰撞的邻近节点
        final searchRadius = minNodeSpacing + node.radius * 2;
        final neighbors = tree.queryCircle(posA, searchRadius);

        for (final neighbor in neighbors) {
          if (neighbor.id == node.id) continue;

          final posB = positions[neighbor.id];
          if (posB == null) continue;

          final nodeB = nodes.firstWhere(
            (n) => n.id == neighbor.id,
            orElse: () => node,
          );

          final minDist = minNodeSpacing + node.radius + nodeB.radius;
          final delta = posA - posB;
          final dist = delta.distance;

          if (dist < minDist && dist > 0.1) {
            hasOverlap = true;
            final overlap = minDist - dist;
            final direction = Offset(delta.dx / dist, delta.dy / dist);
            final push = direction * overlap * pushForce * 0.5;

            positions[node.id] = posA + push;
            positions[neighbor.id] = posB - push;
          }
        }
      }

      if (!hasOverlap) break;
    }
  }
}

/// 布局节点包装器（用于四叉树）
class _LayoutNode implements QuadTreeItem {
  _LayoutNode({
    required this.id,
    required this.position,
    required this.radius,
  });

  @override
  final String id;

  @override
  final Offset position;

  final double radius;
}

/// GalaxyLayoutEngine的扩展方法
extension GalaxyLayoutEngineAsync on GalaxyLayoutEngine {
  /// 在 Isolate 中进行力导向优化
  static Future<Map<String, Offset>> optimizeLayoutAsync({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required Map<String, Offset> initialPositions,
  }) async {
    final data = _LayoutOptimizationData(
      nodes: nodes.map((n) => _SimpleNode(
        id: n.id,
        parentId: n.parentId,
        sector: n.sector,
        importance: n.importance,
      ),).toList(),
      edges: edges.map((e) => _SimpleEdge(
        sourceId: e.sourceId,
        targetId: e.targetId,
        strength: e.strength,
      ),).toList(),
      initialPositions: initialPositions,
    );

    return compute(_forceDirectedOptimization, data);
  }
}

/// 简化的节点数据（用于 Isolate）
class _SimpleNode {

  _SimpleNode({
    required this.id,
    required this.sector, required this.importance, this.parentId,
  });
  final String id;
  final String? parentId;
  final SectorEnum sector;
  final int importance;
}

/// 简化的边数据（用于 Isolate）
class _SimpleEdge {

  _SimpleEdge({
    required this.sourceId,
    required this.targetId,
    required this.strength,
  });
  final String sourceId;
  final String targetId;
  final double strength;
}

/// 布局优化数据
class _LayoutOptimizationData {

  _LayoutOptimizationData({
    required this.nodes,
    required this.edges,
    required this.initialPositions,
  });
  final List<_SimpleNode> nodes;
  final List<_SimpleEdge> edges;
  final Map<String, Offset> initialPositions;
}

/// 力导向布局优化（在 Isolate 中运行）
Map<String, Offset> _forceDirectedOptimization(_LayoutOptimizationData data) {
  final nodes = data.nodes;
  final edges = data.edges;
  final positions = Map<String, Offset>.from(data.initialPositions);

  if (nodes.isEmpty) return positions;

  // 优化参数 - 针对分散布局调整
  const iterations = 150; // 更多迭代次数以达到平衡
  const repulsionStrength = 8000.0; // 极强的斥力，推开节点
  const edgeAttractionStrength = 0.02; // 很弱的引力，允许边拉长
  const parentAttractionStrength = 0.03;
  const minDistance = 300.0; // 斥力作用范围显著增大
  const maxDisplacement = 50.0; // 允许更大的单步位移
  const damping = 0.88;
  const coolingFactor = 0.96; // 冷却稍慢

  // 构建连接图
  final nodeEdges = <String, List<_SimpleEdge>>{};
  for (final edge in edges) {
    nodeEdges.putIfAbsent(edge.sourceId, () => []);
    nodeEdges.putIfAbsent(edge.targetId, () => []);
    nodeEdges[edge.sourceId]!.add(edge);
    nodeEdges[edge.targetId]!.add(edge);
  }

  // 构建父子关系
  final children = <String, List<String>>{};
  for (final node in nodes) {
    if (node.parentId != null) {
      children.putIfAbsent(node.parentId!, () => []);
      children[node.parentId]!.add(node.id);
    }
  }

  // 获取星域配置
  final sectorStyles = <String, (double, double)>{};
  for (final node in nodes) {
    final style = SectorConfig.getStyle(node.sector);
    sectorStyles[node.id] = (
      (style.baseAngle - 90) * pi / 180,
      style.sweepAngle * pi / 180,
    );
  }

  // 速度
  final velocity = <String, Offset>{};
  for (final node in nodes) {
    velocity[node.id] = Offset.zero;
  }

  var temperature = 1.0;

  for (var iter = 0; iter < iterations; iter++) {
    for (final nodeA in nodes) {
      var force = Offset.zero;
      final posA = positions[nodeA.id]!;

      // 1. 斥力：节点之间互斥
      for (final nodeB in nodes) {
        if (nodeA.id == nodeB.id) continue;
        final posB = positions[nodeB.id]!;
        final delta = posA - posB;
        var distance = delta.distance;
        if (distance < 1) distance = 1;

        if (distance < minDistance * 4) {
          final repulsion = repulsionStrength * temperature / (distance * distance);
          force += Offset(
            delta.dx / distance * repulsion,
            delta.dy / distance * repulsion,
          );
        }
      }

      // 2. 边吸引力
      final nodeEdgeList = nodeEdges[nodeA.id];
      if (nodeEdgeList != null) {
        for (final edge in nodeEdgeList) {
          final otherId = edge.sourceId == nodeA.id ? edge.targetId : edge.sourceId;
          final otherPos = positions[otherId];
          if (otherPos != null) {
            final delta = otherPos - posA;
            final distance = delta.distance;
            if (distance > 50) {
              final attraction = edgeAttractionStrength * edge.strength * temperature;
              force += Offset(
                delta.dx * attraction,
                delta.dy * attraction,
              );
            }
          }
        }
      }

      // 3. 父节点吸引力
      if (nodeA.parentId != null) {
        final parentPos = positions[nodeA.parentId];
        if (parentPos != null) {
          final delta = parentPos - posA;
          final distance = delta.distance;
          if (distance > 40) {
            force += Offset(
              delta.dx * parentAttractionStrength * temperature,
              delta.dy * parentAttractionStrength * temperature,
            );
          }
        }
      }

      // 4. 子节点轻微吸引
      final nodeChildren = children[nodeA.id];
      if (nodeChildren != null) {
        for (final childId in nodeChildren) {
          final childPos = positions[childId];
          if (childPos != null) {
            final delta = childPos - posA;
            if (delta.distance > 100) {
              force += Offset(
                delta.dx * parentAttractionStrength * 0.5 * temperature,
                delta.dy * parentAttractionStrength * 0.5 * temperature,
              );
            }
          }
        }
      }

      // 5. 中心引力（防止飘远）
      if (posA.distance > GalaxyLayoutEngine.outerRadius * 0.9) {
        force -= Offset(
          posA.dx * 0.002 * temperature,
          posA.dy * 0.002 * temperature,
        );
      }

      // 应用力并更新速度
      velocity[nodeA.id] = (velocity[nodeA.id]! + force) * damping;

      // 限制最大位移
      var displacement = velocity[nodeA.id]!;
      if (displacement.distance > maxDisplacement * temperature) {
        displacement = displacement / displacement.distance * maxDisplacement * temperature;
      }

      var newPos = posA + displacement;

      // 6. 约束在星域内
      final (baseAngle, sweepAngle) = sectorStyles[nodeA.id]!;
      final nodeAngle = atan2(newPos.dy, newPos.dx);
      final endAngle = baseAngle + sweepAngle;

      var normalizedAngle = nodeAngle;
      while (normalizedAngle < baseAngle) {
        normalizedAngle += 2 * pi;
      }
      while (normalizedAngle >= baseAngle + 2 * pi) {
        normalizedAngle -= 2 * pi;
      }

      if (normalizedAngle < baseAngle || normalizedAngle > endAngle) {
        final centerAngle = baseAngle + sweepAngle / 2;
        final targetAngle = centerAngle + (normalizedAngle - centerAngle) * 0.85;
        newPos = Offset(
          newPos.distance * cos(targetAngle),
          newPos.distance * sin(targetAngle),
        );
      }

      // 约束半径
      final radius = newPos.distance.clamp(
        GalaxyLayoutEngine.innerRadius,
        GalaxyLayoutEngine.outerRadius,
      );
      if (newPos.distance > 0.1) {
        newPos = Offset(
          radius * newPos.dx / newPos.distance,
          radius * newPos.dy / newPos.distance,
        );
      }

      positions[nodeA.id] = newPos;
    }

    // 冷却
    temperature *= coolingFactor;
  }

  return positions;
}

/// 视口裁剪工具
class ViewportCuller {

  ViewportCuller({
    required this.viewport,
    this.margin = 50.0,
  });
  final Rect viewport;
  final double margin;

  /// 检查位置是否在视口内
  bool isVisible(Offset position) => position.dx >= viewport.left - margin &&
           position.dx <= viewport.right + margin &&
           position.dy >= viewport.top - margin &&
           position.dy <= viewport.bottom + margin;

  /// 过滤可见节点
  List<GalaxyNodeModel> filterVisibleNodes(
    List<GalaxyNodeModel> nodes,
    Map<String, Offset> positions,
  ) => nodes.where((node) {
      final pos = positions[node.id];
      return pos != null && isVisible(pos);
    }).toList();

  /// 过滤可见边
  List<GalaxyEdgeModel> filterVisibleEdges(
    List<GalaxyEdgeModel> edges,
    Map<String, Offset> positions,
  ) => edges.where((edge) {
      final startPos = positions[edge.sourceId];
      final endPos = positions[edge.targetId];
      if (startPos == null || endPos == null) return false;

      // 如果任一端点可见，或者线段穿过视口，则保留
      return isVisible(startPos) ||
             isVisible(endPos) ||
             _lineIntersectsRect(startPos, endPos, viewport);
    }).toList();

  /// 检查线段是否与矩形相交
  bool _lineIntersectsRect(Offset p1, Offset p2, Rect rect) {
    // 简化检查：如果线段的包围盒与矩形相交
    final lineRect = Rect.fromPoints(p1, p2);
    return lineRect.overlaps(rect.inflate(margin));
  }
}
