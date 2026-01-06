import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

void main() {
  group('GalaxyLayoutEngine', () {
    late List<GalaxyNodeModel> testNodes;
    late List<GalaxyEdgeModel> testEdges;

    setUp(() {
      testNodes = _generateMockNodes(10);
      testEdges = _generateMockEdges(testNodes);
    });

    group('calculateInitialLayout', () {
      test('returns valid positions for all nodes', () {
        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        expect(positions, isNotEmpty);
        expect(positions.length, equals(testNodes.length));

        // 验证每个节点都有位置
        for (final node in testNodes) {
          expect(positions.containsKey(node.id), isTrue);
        }
      });

      test('positions are within bounds', () {
        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        for (final pos in positions.values) {
          // 位置应该在宇宙边界内
          expect(
            pos.distance,
            lessThanOrEqualTo(GalaxyLayoutEngine.outerRadius * 1.5),
          );
        }
      });

      test('nodes have minimum spacing', () {
        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        // 验证节点之间有最小间距
        for (var i = 0; i < testNodes.length; i++) {
          for (var j = i + 1; j < testNodes.length; j++) {
            final pos1 = positions[testNodes[i].id]!;
            final pos2 = positions[testNodes[j].id]!;
            final distance = (pos1 - pos2).distance;

            // 间距应该大于0（不完全重叠）
            expect(distance, greaterThan(0));
          }
        }
      });

      test('respects existing positions when provided', () {
        final existingPositions = {
          testNodes[0].id: const Offset(100, 200),
          testNodes[1].id: const Offset(300, 400),
        };

        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
          existingPositions: existingPositions,
        );

        // 验证现有位置被保留（允许碰撞调整带来的小幅偏移）
        final firstDelta =
            (positions[testNodes[0].id]! - const Offset(100, 200)).distance;
        final secondDelta =
            (positions[testNodes[1].id]! - const Offset(300, 400)).distance;
        expect(firstDelta, lessThan(25));
        expect(secondDelta, lessThan(25));
      });

      test('handles empty node list', () {
        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: [],
          edges: [],
        );

        expect(positions, isEmpty);
      });

      test('handles single node', () {
        final singleNode = [testNodes[0]];

        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: singleNode,
          edges: [],
        );

        expect(positions.length, equals(1));
        expect(positions.containsKey(singleNode[0].id), isTrue);
      });

      test('groups nodes by sector', () {
        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        // 按星域分组节点
        final sectorPositions = <SectorEnum, List<Offset>>{};
        for (final node in testNodes) {
          final pos = positions[node.id]!;
          sectorPositions.putIfAbsent(node.sector, () => []);
          sectorPositions[node.sector]!.add(pos);
        }

        // 验证同一星域的节点在相近的角度范围内
        for (final entry in sectorPositions.entries) {
          if (entry.value.length > 1) {
            // 计算角度
            final angles = entry.value
                .map((pos) => _normalizeAngle(Offset(pos.dx, pos.dy).direction))
                .toList();

            // 角度范围应该在合理的扇形内
            final minAngle = angles.reduce((a, b) => a < b ? a : b);
            final maxAngle = angles.reduce((a, b) => a > b ? a : b);
            final spread = maxAngle - minAngle;

            // 同一星域的节点角度分布不应超过180度
            expect(spread, lessThan(3.14159));
          }
        }
      });
    });

    group('optimizeLayoutAsync', () {
      test('returns optimized positions', () async {
        final initialPositions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        final optimizedPositions =
            await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: testNodes,
          edges: testEdges,
          initialPositions: initialPositions,
        );

        expect(optimizedPositions, isNotEmpty);
        expect(optimizedPositions.length, equals(testNodes.length));
      });

      test('optimized layout has valid positions', () async {
        final initialPositions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: testNodes,
          edges: testEdges,
        );

        final optimizedPositions =
            await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: testNodes,
          edges: testEdges,
          initialPositions: initialPositions,
        );

        for (final pos in optimizedPositions.values) {
          // 位置应该在宇宙边界内
          expect(
              pos.distance, lessThanOrEqualTo(GalaxyLayoutEngine.outerRadius),);
          expect(pos.distance, greaterThanOrEqualTo(0));
        }
      });

      test('handles empty input', () async {
        final positions = await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: [],
          edges: [],
          initialPositions: {},
        );

        expect(positions, isEmpty);
      });
    });
  });

  group('ViewportCuller', () {
    late List<GalaxyNodeModel> testNodes;
    late Map<String, Offset> positions;

    setUp(() {
      testNodes = _generateMockNodes(20);
      positions = {
        for (var i = 0; i < testNodes.length; i++)
          testNodes[i].id: Offset(i * 100.0, i * 100.0),
      };
    });

    test('filters visible nodes correctly', () {
      final culler = ViewportCuller(
        viewport: const Rect.fromLTWH(0, 0, 500, 500),
      );

      final visibleNodes = culler.filterVisibleNodes(testNodes, positions);

      // 只有前几个节点应该在视口内
      expect(visibleNodes.length, lessThan(testNodes.length));
      expect(visibleNodes.length, greaterThan(0));
    });

    test('returns all nodes when viewport is large', () {
      final culler = ViewportCuller(
        viewport: const Rect.fromLTWH(-1000, -1000, 5000, 5000),
      );

      final visibleNodes = culler.filterVisibleNodes(testNodes, positions);

      expect(visibleNodes.length, equals(testNodes.length));
    });

    test('returns empty when viewport misses all nodes', () {
      final culler = ViewportCuller(
        viewport: const Rect.fromLTWH(-1000, -1000, 100, 100),
      );

      final visibleNodes = culler.filterVisibleNodes(testNodes, positions);

      expect(visibleNodes, isEmpty);
    });

    test('respects margin', () {
      final cullerWithMargin = ViewportCuller(
        viewport: const Rect.fromLTWH(0, 0, 100, 100),
        margin: 100,
      );

      final cullerWithoutMargin = ViewportCuller(
        viewport: const Rect.fromLTWH(0, 0, 100, 100),
        margin: 0,
      );

      final visibleWithMargin =
          cullerWithMargin.filterVisibleNodes(testNodes, positions);
      final visibleWithoutMargin =
          cullerWithoutMargin.filterVisibleNodes(testNodes, positions);

      expect(visibleWithMargin.length,
          greaterThanOrEqualTo(visibleWithoutMargin.length),);
    });

    test('filters edges correctly', () {
      final edges = _generateMockEdges(testNodes);
      final culler = ViewportCuller(
        viewport: const Rect.fromLTWH(0, 0, 500, 500),
      );

      final visibleEdges = culler.filterVisibleEdges(edges, positions);

      // 应该过滤掉完全在视口外的边
      expect(visibleEdges.length, lessThanOrEqualTo(edges.length));
    });
  });
}

/// 生成模拟节点
List<GalaxyNodeModel> _generateMockNodes(int count) {
  final nodes = <GalaxyNodeModel>[];
  const sectors = SectorEnum.values;

  for (var i = 0; i < count; i++) {
    nodes.add(
      GalaxyNodeModel(
        id: 'node_$i',
        name: 'Node $i',
        sector: sectors[i % sectors.length],
        importance: (i % 5) + 1,
        masteryScore: (i * 10) % 100,
        isUnlocked: i % 3 != 0,
        studyCount: i % 4,
        parentId: i > 0 && i % 3 == 0 ? 'node_${i - 1}' : null,
      ),
    );
  }

  return nodes;
}

/// 生成模拟边
List<GalaxyEdgeModel> _generateMockEdges(List<GalaxyNodeModel> nodes) {
  final edges = <GalaxyEdgeModel>[];

  for (var i = 1; i < nodes.length; i++) {
    if (i.isEven) {
      edges.add(
        GalaxyEdgeModel(
          id: 'edge_$i',
          sourceId: nodes[i - 1].id,
          targetId: nodes[i].id,
          strength: 0.5 + (i % 5) * 0.1,
        ),
      );
    }
  }

  return edges;
}

/// 归一化角度到 [-PI, PI]
double _normalizeAngle(double angle) {
  while (angle > 3.14159) {
    angle -= 2 * 3.14159;
  }
  while (angle < -3.14159) {
    angle += 2 * 3.14159;
  }
  return angle;
}
