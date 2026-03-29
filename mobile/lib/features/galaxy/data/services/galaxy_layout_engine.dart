import 'dart:collection';
import 'dart:math';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/quad_tree.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyLayoutSolverResult {
  const GalaxyLayoutSolverResult({
    required this.positions,
    required this.componentAnchors,
    required this.settled,
  });

  final Map<String, Offset> positions;
  final Map<String, Offset> componentAnchors;
  final bool settled;
}

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
  static const double canvasPadding = 400.0;
  static const double canvasSize = outerRadius * 2 + canvasPadding * 2;
  static const double canvasCenter = canvasSize / 2;
  static const double _goldenAngle = 2.39996322972865332;

  /// 计算初始布局（快速，在主线程）
  static Map<String, Offset> calculateInitialLayout({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    Map<String, Offset>? existingPositions,
    double sectorAffinity = 0.28,
    int refinementIterations = 42,
  }) {
    if (nodes.isEmpty) {
      return const <String, Offset>{};
    }

    final stablePositions = existingPositions ?? const <String, Offset>{};
    final adjacency = _buildAdjacency(nodes, edges);
    final sectorAnchors = _buildSectorAnchors();
    final positions = <String, Offset>{};
    final nodesBySector = <SectorEnum, List<GalaxyNodeModel>>{};
    final sectorPlacementIndex = <SectorEnum, int>{};

    for (final node in nodes) {
      nodesBySector
          .putIfAbsent(node.sector, () => <GalaxyNodeModel>[])
          .add(node);
    }

    for (final entry in nodesBySector.entries) {
      final sector = entry.key;
      final sectorNodes = entry.value
        ..sort((left, right) {
          final degreeCompare = (adjacency[right.id]?.length ?? 0)
              .compareTo(adjacency[left.id]?.length ?? 0);
          if (degreeCompare != 0) {
            return degreeCompare;
          }
          final importanceCompare = right.importance.compareTo(left.importance);
          if (importanceCompare != 0) {
            return importanceCompare;
          }
          final studyCompare = right.studyCount.compareTo(left.studyCount);
          if (studyCompare != 0) {
            return studyCompare;
          }
          return left.name.compareTo(right.name);
        });

      for (final node in sectorNodes) {
        final stable = stablePositions[node.id];
        if (stable != null) {
          positions[node.id] = stable;
          continue;
        }
        final index = sectorPlacementIndex.update(
          sector,
          (value) => value + 1,
          ifAbsent: () => 0,
        );
        positions[node.id] = _seedPhyllotaxisPosition(
          node: node,
          index: index,
          degree: adjacency[node.id]?.length ?? 0,
          sectorAnchor: sectorAnchors[sector] ?? Offset.zero,
        );
      }
    }

    _solveHybridLayout(
      positions: positions,
      nodes: nodes,
      edges: edges,
      adjacency: adjacency,
      sectorAnchors: sectorAnchors,
      sectorAffinity: sectorAffinity,
      iterations: refinementIterations,
      memoryAnchors: stablePositions,
    );
    _resolveOverlaps(
      positions,
      nodes,
      pinnedNodeIds: stablePositions.keys.toSet(),
    );
    _clampToUniverse(positions);
    return positions;
  }

  static Map<String, Set<String>> _buildAdjacency(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
  ) {
    final adjacency = {
      for (final node in nodes) node.id: <String>{},
    };
    for (final edge in edges) {
      adjacency.putIfAbsent(edge.sourceId, () => <String>{}).add(edge.targetId);
      adjacency.putIfAbsent(edge.targetId, () => <String>{}).add(edge.sourceId);
    }
    return adjacency;
  }

  static Map<SectorEnum, Offset> _buildSectorAnchors() => {
        for (final sector in SectorEnum.values)
          sector: () {
            final style = SectorConfig.getStyle(sector);
            final angle =
                (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
            return Offset(
              sectorRootRadius * cos(angle),
              sectorRootRadius * sin(angle),
            );
          }(),
      };

  static Offset _seedPhyllotaxisPosition({
    required GalaxyNodeModel node,
    required int index,
    required int degree,
    required Offset sectorAnchor,
  }) {
    final orbitAngle =
        _goldenAngle * (index + 1) + _stableJitter(node.id) * 0.6;
    final orbitRadius = 46 +
        sqrt(index + 1) * minNodeSpacing * 0.84 +
        (5 - node.importance) * 8;
    final hubLift = degree * 7.0;
    final radial = sectorAnchor.distance == 0
        ? const Offset(0, -1)
        : sectorAnchor / sectorAnchor.distance;
    final tangent = Offset(-radial.dy, radial.dx);
    final orbitOffset = radial * (hubLift * 0.3) +
        tangent * sin(orbitAngle) * orbitRadius * 0.34 +
        Offset(cos(orbitAngle), sin(orbitAngle)) * orbitRadius;
    return sectorAnchor + orbitOffset;
  }

  static void _solveHybridLayout({
    required Map<String, Offset> positions,
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required Map<String, Set<String>> adjacency,
    required Map<SectorEnum, Offset> sectorAnchors,
    required double sectorAffinity,
    required int iterations,
    required Map<String, Offset> memoryAnchors,
  }) {
    final velocities = <String, Offset>{
      for (final node in nodes) node.id: Offset.zero,
    };
    final nodeById = {
      for (final node in nodes) node.id: node,
    };
    final edgeStrengths = <String, double>{};
    for (final edge in edges) {
      final key = _edgeKey(edge.sourceId, edge.targetId);
      final current = edgeStrengths[key] ?? 0;
      edgeStrengths[key] = max(current, 0.85 + edge.strength * 0.75);
    }

    var temperature = 1.0;
    for (var iteration = 0; iteration < iterations; iteration++) {
      for (final node in nodes) {
        final memoryAnchor = memoryAnchors[node.id];
        if (memoryAnchor != null) {
          positions[node.id] = memoryAnchor;
          velocities[node.id] = Offset.zero;
          continue;
        }
        final position = positions[node.id] ?? Offset.zero;
        var force = Offset.zero;
        final nodeDegree = adjacency[node.id]?.length ?? 0;

        for (final other in nodes) {
          if (other.id == node.id) {
            continue;
          }
          final otherPosition = positions[other.id] ?? Offset.zero;
          final delta = position - otherPosition;
          final distance = max(delta.distance, 1.0);
          final direction = delta / distance;
          final combinedRadius = minNodeSpacing * 0.45 +
              node.radius +
              other.radius +
              (nodeDegree + (adjacency[other.id]?.length ?? 0)) * 2.2;
          final repulsion = 11000 / (distance * distance);
          force += direction * repulsion;
          if (distance < combinedRadius) {
            force += direction * (combinedRadius - distance) * 1.4;
          }
        }

        for (final neighborId in adjacency[node.id] ?? const <String>{}) {
          final neighbor = nodeById[neighborId];
          final neighborPosition = positions[neighborId];
          if (neighbor == null || neighborPosition == null) {
            continue;
          }
          final delta = neighborPosition - position;
          final distance = max(delta.distance, 1.0);
          final direction = delta / distance;
          final strength = edgeStrengths[_edgeKey(node.id, neighborId)] ?? 1.0;
          final targetDistance = (112 +
                  (5 - min(node.importance, neighbor.importance)) * 12 -
                  strength * 10)
              .clamp(88.0, 156.0);
          force += direction * (distance - targetDistance) * 0.045 * strength;
        }

        final sectorAnchor = sectorAnchors[node.sector] ?? Offset.zero;
        force += (sectorAnchor - position) * (0.012 + sectorAffinity * 0.016);
        force += Offset(-position.dx, -position.dy) * 0.0012;

        final sectorCorrection = _softSectorCorrection(
          node: node,
          position: position,
        );
        force += sectorCorrection * (0.10 + sectorAffinity * 0.22);

        if (position.distance > outerRadius * 0.9) {
          force += Offset(-position.dx, -position.dy) * 0.0048;
        }

        var velocity =
            (velocities[node.id] ?? Offset.zero) + force * temperature;
        velocity *= 0.82;
        final maxStep = 18.0 * temperature + 3;
        if (velocity.distance > maxStep) {
          velocity = velocity / velocity.distance * maxStep;
        }

        positions[node.id] = position + velocity;
        velocities[node.id] = velocity;
      }
      temperature *= 0.972;
    }
  }

  static Offset _softSectorCorrection({
    required GalaxyNodeModel node,
    required Offset position,
  }) {
    if (position.distance <= 1) {
      return Offset.zero;
    }
    final style = SectorConfig.getStyle(node.sector);
    final centerAngle =
        (style.baseAngle + style.sweepAngle / 2 - 90) * pi / 180;
    final currentAngle = atan2(position.dy, position.dx);
    final delta = _wrapAngle(centerAngle - currentAngle);
    final tangent = Offset(-sin(currentAngle), cos(currentAngle));
    return tangent * delta;
  }

  static double _wrapAngle(double angle) {
    var normalized = angle;
    while (normalized > pi) {
      normalized -= 2 * pi;
    }
    while (normalized < -pi) {
      normalized += 2 * pi;
    }
    return normalized;
  }

  static double _stableJitter(String seed) {
    final hash = seed.hashCode & 0x7fffffff;
    return (hash % 1000) / 1000;
  }

  static String _edgeKey(String sourceId, String targetId) =>
      sourceId.compareTo(targetId) <= 0
          ? '$sourceId::$targetId'
          : '$targetId::$sourceId';

  static void _clampToUniverse(Map<String, Offset> positions) {
    positions.updateAll((_, position) {
      final distance = position.distance;
      if (distance <= outerRadius) {
        return position;
      }
      final safeDistance = distance == 0 ? 1.0 : distance;
      return (position / safeDistance) * outerRadius;
    });
  }

  /// 解决节点重叠 - 使用四叉树优化碰撞检测
  static void _resolveOverlaps(
    Map<String, Offset> positions,
    List<GalaxyNodeModel> nodes, {
    Set<String> pinnedNodeIds = const <String>{},
  }) {
    const maxIterations = 50;
    const pushForce = 0.8;

    // OPTIMIZATION: N < 50, skip QuadTree and use brute force O(N^2)
    // Note: Viewport culling is handled by the consumer (Painter/Provider) before rendering,
    // so we only focus on collision resolution here as per spec.
    if (nodes.length < 50) {
      for (var iter = 0; iter < maxIterations; iter++) {
        var hasOverlap = false;
        for (var i = 0; i < nodes.length; i++) {
          final nodeA = nodes[i];
          final posA = positions[nodeA.id]!;

          for (var j = i + 1; j < nodes.length; j++) {
            final nodeB = nodes[j];
            final posB = positions[nodeB.id]!;

            final minDist = minNodeSpacing + nodeA.radius + nodeB.radius;
            final delta = posA - posB;
            final dist = delta.distance;

            if (dist < minDist && dist > 0.1) {
              hasOverlap = true;
              final overlap = minDist - dist;
              final direction = Offset(delta.dx / dist, delta.dy / dist);
              final aPinned = pinnedNodeIds.contains(nodeA.id);
              final bPinned = pinnedNodeIds.contains(nodeB.id);
              if (aPinned && bPinned) {
                continue;
              }
              final push = direction * overlap * pushForce;
              if (aPinned) {
                positions[nodeB.id] = posB - push;
              } else if (bPinned) {
                positions[nodeA.id] = posA + push;
              } else {
                positions[nodeA.id] = posA + push * 0.5;
                positions[nodeB.id] = posB - push * 0.5;
              }
            }
          }
        }
        if (!hasOverlap) break;
      }
      return;
    }

    // 使用四叉树加速碰撞检测
    for (var iter = 0; iter < maxIterations; iter++) {
      var hasOverlap = false;

      // 构建四叉树
      final tree = QuadTree<_LayoutNode>(
        bounds: const Rect.fromLTWH(
          -canvasCenter,
          -canvasCenter,
          canvasSize,
          canvasSize,
        ),
        capacity: 8,
      );

      // 插入所有节点
      for (final node in nodes) {
        final pos = positions[node.id];
        if (pos != null) {
          tree.insert(
            _LayoutNode(
              id: node.id,
              position: pos,
              radius: node.radius,
            ),
          );
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
            final aPinned = pinnedNodeIds.contains(node.id);
            final bPinned = pinnedNodeIds.contains(neighbor.id);
            if (aPinned && bPinned) {
              continue;
            }
            final push = direction * overlap * pushForce;
            if (aPinned) {
              positions[neighbor.id] = posB - push;
            } else if (bPinned) {
              positions[node.id] = posA + push;
            } else {
              positions[node.id] = posA + push * 0.5;
              positions[neighbor.id] = posB - push * 0.5;
            }
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
  static Future<GalaxyLayoutSolverResult> optimizeLayoutAsync({
    required List<GalaxyNodeModel> nodes,
    required List<GalaxyEdgeModel> edges,
    required Map<String, Offset> initialPositions,
    double sectorAffinity = 0.28,
    int iterations = 160,
  }) async {
    final data = _LayoutOptimizationData(
      nodes: nodes
          .map(
            (n) => _SimpleNode(
              id: n.id,
              parentId: n.parentId,
              sector: n.sector,
              importance: n.importance,
            ),
          )
          .toList(),
      edges: edges
          .map(
            (e) => _SimpleEdge(
              sourceId: e.sourceId,
              targetId: e.targetId,
              strength: e.strength,
            ),
          )
          .toList(),
      initialPositions: initialPositions,
      sectorAffinity: sectorAffinity,
      iterations: iterations,
    );

    final optimizedPositions = await compute(_forceDirectedOptimization, data);
    return GalaxyLayoutSolverResult(
      positions: optimizedPositions,
      componentAnchors: _componentAnchorsFor(optimizedPositions, nodes, edges),
      settled: true,
    );
  }

  static Map<String, Offset> _componentAnchorsFor(
    Map<String, Offset> positions,
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
  ) {
    final adjacency = GalaxyLayoutEngine._buildAdjacency(nodes, edges);
    final visited = <String>{};
    final anchors = <String, Offset>{};

    for (final node in nodes) {
      if (!visited.add(node.id)) {
        continue;
      }
      final componentIds = <String>{node.id};
      final queue = Queue<String>()..add(node.id);
      while (queue.isNotEmpty) {
        final current = queue.removeFirst();
        for (final neighborId in adjacency[current] ?? const <String>{}) {
          if (visited.add(neighborId)) {
            componentIds.add(neighborId);
            queue.add(neighborId);
          }
        }
      }

      final center = componentIds.fold<Offset>(
            Offset.zero,
            (sum, nodeId) => sum + (positions[nodeId] ?? Offset.zero),
          ) /
          componentIds.length.toDouble();
      anchors[node.id] = center;
    }
    return anchors;
  }
}

/// 简化的节点数据（用于 Isolate）
class _SimpleNode {
  _SimpleNode({
    required this.id,
    required this.sector,
    required this.importance,
    this.parentId,
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
    required this.sectorAffinity,
    required this.iterations,
  });
  final List<_SimpleNode> nodes;
  final List<_SimpleEdge> edges;
  final Map<String, Offset> initialPositions;
  final double sectorAffinity;
  final int iterations;
}

/// 力导向布局优化（在 Isolate 中运行）
Map<String, Offset> _forceDirectedOptimization(_LayoutOptimizationData data) {
  final nodes = data.nodes
      .map<GalaxyNodeModel>(
        (node) => GalaxyNodeModel(
          id: node.id,
          name: node.id,
          sector: node.sector,
          importance: node.importance,
          parentId: node.parentId,
          isUnlocked: true,
          masteryScore: 0,
        ),
      )
      .toList(growable: false);
  final edges = data.edges
      .map<GalaxyEdgeModel>(
        (edge) => GalaxyEdgeModel(
          id: '${edge.sourceId}-${edge.targetId}',
          sourceId: edge.sourceId,
          targetId: edge.targetId,
          strength: edge.strength,
        ),
      )
      .toList(growable: false);
  final positions = Map<String, Offset>.from(data.initialPositions);
  if (nodes.isEmpty) {
    return positions;
  }

  GalaxyLayoutEngine._solveHybridLayout(
    positions: positions,
    nodes: nodes,
    edges: edges,
    adjacency: GalaxyLayoutEngine._buildAdjacency(nodes, edges),
    sectorAnchors: GalaxyLayoutEngine._buildSectorAnchors(),
    sectorAffinity: data.sectorAffinity,
    iterations: data.iterations,
    memoryAnchors: data.initialPositions,
  );
  GalaxyLayoutEngine._clampToUniverse(positions);
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
  bool isVisible(Offset position) =>
      position.dx >= viewport.left - margin &&
      position.dx <= viewport.right + margin &&
      position.dy >= viewport.top - margin &&
      position.dy <= viewport.bottom + margin;

  /// 过滤可见节点
  List<GalaxyNodeModel> filterVisibleNodes(
    List<GalaxyNodeModel> nodes,
    Map<String, Offset> positions,
  ) =>
      nodes.where((node) {
        final pos = positions[node.id];
        return pos != null && isVisible(pos);
      }).toList();

  /// 过滤可见边
  List<GalaxyEdgeModel> filterVisibleEdges(
    List<GalaxyEdgeModel> edges,
    Map<String, Offset> positions,
  ) =>
      edges.where((edge) {
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
