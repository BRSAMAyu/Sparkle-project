import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/galaxy_layout_engine.dart';
import 'package:sparkle/core/services/quad_tree.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/presentation/widgets/galaxy/sector_config.dart';

void main() {
  group('Galaxy Performance Benchmarks', () {
    group('Layout Engine Performance', () {
      test('calculates initial layout for 100 nodes under 50ms', () {
        final nodes = _generateMockNodes(100);
        final edges = _generateMockEdges(nodes);

        final stopwatch = Stopwatch()..start();

        GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        stopwatch.stop();

        print('100 nodes initial layout: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(50));
      });

      test('calculates initial layout for 500 nodes under 200ms', () {
        final nodes = _generateMockNodes(500);
        final edges = _generateMockEdges(nodes);

        final stopwatch = Stopwatch()..start();

        GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        stopwatch.stop();

        print('500 nodes initial layout: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(200));
      });

      test('calculates initial layout for 1000 nodes under 500ms', () {
        final nodes = _generateMockNodes(1000);
        final edges = _generateMockEdges(nodes);

        final stopwatch = Stopwatch()..start();

        GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        stopwatch.stop();

        print('1000 nodes initial layout: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(500));
      });

      test('optimizes layout for 100 nodes under 500ms', () async {
        final nodes = _generateMockNodes(100);
        final edges = _generateMockEdges(nodes);
        final initial = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        final stopwatch = Stopwatch()..start();

        await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: nodes,
          edges: edges,
          initialPositions: initial,
        );

        stopwatch.stop();

        print('100 nodes layout optimization: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(500));
      });
    });

    group('QuadTree Performance', () {
      test('inserts 1000 items under 50ms', () {
        final tree = QuadTree<SimpleQuadTreeItem>(
          bounds: const Rect.fromLTWH(-5000, -5000, 10000, 10000),
        );

        final stopwatch = Stopwatch()..start();

        for (var i = 0; i < 1000; i++) {
          tree.insert(SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(
              (i % 100) * 100.0 - 5000,
              (i ~/ 100) * 100.0 - 5000,
            ),
          ),);
        }

        stopwatch.stop();

        print('1000 items QuadTree insert: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(50));
      });

      test('queries range for 10000 items under 10ms', () {
        final tree = QuadTree<SimpleQuadTreeItem>(
          bounds: const Rect.fromLTWH(-5000, -5000, 10000, 10000),
        );

        // 插入10000个节点
        for (var i = 0; i < 10000; i++) {
          tree.insert(SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(
              (i % 100) * 100.0 - 5000,
              (i ~/ 100) * 100.0 - 5000,
            ),
          ),);
        }

        final stopwatch = Stopwatch()..start();

        // 执行100次查询
        for (var i = 0; i < 100; i++) {
          tree.queryRange(const Rect.fromLTWH(-500, -500, 1000, 1000));
        }

        stopwatch.stop();

        print('100 range queries on 10000 items: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(100)); // 平均每次 < 1ms
      });

      test('finds nearest neighbors for 5000 items under 5ms per query', () {
        final tree = QuadTree<SimpleQuadTreeItem>(
          bounds: const Rect.fromLTWH(-5000, -5000, 10000, 10000),
        );

        // 插入5000个节点
        for (var i = 0; i < 5000; i++) {
          tree.insert(SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(
              (i % 71) * 140.0 - 5000, // 使用质数避免规律
              (i ~/ 71) * 140.0 - 5000,
            ),
          ),);
        }

        final stopwatch = Stopwatch()..start();

        // 执行50次最近邻查询
        for (var i = 0; i < 50; i++) {
          tree.findNearestNeighbors(
            Offset(i * 100.0 - 2500, i * 100.0 - 2500),
            10,
          );
        }

        stopwatch.stop();

        print('50 kNN queries on 5000 items: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(250)); // 平均每次 < 5ms
      });
    });

    group('ViewportCuller Performance', () {
      test('filters 1000 nodes under 5ms', () {
        final nodes = _generateMockNodes(1000);
        final positions = <String, Offset>{};
        for (var i = 0; i < nodes.length; i++) {
          positions[nodes[i].id] = Offset(
            (i % 50) * 100.0 - 2500,
            (i ~/ 50) * 100.0 - 2500,
          );
        }

        final culler = ViewportCuller(
          viewport: const Rect.fromLTWH(-500, -500, 1000, 1000),
        );

        final stopwatch = Stopwatch()..start();

        for (var i = 0; i < 100; i++) {
          culler.filterVisibleNodes(nodes, positions);
        }

        stopwatch.stop();

        print('100 viewport culling operations on 1000 nodes: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(50)); // 平均每次 < 0.5ms
      });

      test('filters 1000 edges under 10ms', () {
        final nodes = _generateMockNodes(1000);
        final edges = _generateMockEdges(nodes);
        final positions = <String, Offset>{};
        for (var i = 0; i < nodes.length; i++) {
          positions[nodes[i].id] = Offset(
            (i % 50) * 100.0 - 2500,
            (i ~/ 50) * 100.0 - 2500,
          );
        }

        final culler = ViewportCuller(
          viewport: const Rect.fromLTWH(-500, -500, 1000, 1000),
        );

        final stopwatch = Stopwatch()..start();

        for (var i = 0; i < 100; i++) {
          culler.filterVisibleEdges(edges, positions);
        }

        stopwatch.stop();

        print('100 edge culling operations: ${stopwatch.elapsedMilliseconds}ms');
        expect(stopwatch.elapsedMilliseconds, lessThan(100)); // 平均每次 < 1ms
      });
    });

    group('Memory Usage Simulation', () {
      test('position map memory for 1000 nodes is reasonable', () {
        final positions = <String, Offset>{};

        for (var i = 0; i < 1000; i++) {
          positions['node_$i'] = Offset(i * 1.0, i * 1.0);
        }

        // 估算内存: 每个entry约 ~50-100 bytes
        // 1000 nodes * 100 bytes = ~100KB
        // 这是合理的

        expect(positions.length, equals(1000));
        // 无法直接测量内存，但可以验证结构正确
      });

      test('QuadTree memory for 1000 items is reasonable', () {
        final tree = QuadTree<SimpleQuadTreeItem>(
          bounds: const Rect.fromLTWH(-5000, -5000, 10000, 10000),
        );

        for (var i = 0; i < 1000; i++) {
          tree.insert(SimpleQuadTreeItem(
            id: 'item$i',
            position: Offset(
              (i % 100) * 100.0 - 5000,
              (i ~/ 100) * 100.0 - 5000,
            ),
          ),);
        }

        final stats = tree.getStats();

        // 节点数应该合理
        expect(stats.nodeCount, lessThan(500)); // 不应该过度分裂
        expect(stats.totalItems, equals(1000));
      });
    });
  });
}

/// 生成模拟节点
List<GalaxyNodeModel> _generateMockNodes(int count) {
  final nodes = <GalaxyNodeModel>[];
  const sectors = SectorEnum.values;

  for (var i = 0; i < count; i++) {
    nodes.add(GalaxyNodeModel(
      id: 'node_$i',
      name: 'Node $i',
      sector: sectors[i % sectors.length],
      importance: (i % 5) + 1,
      masteryScore: (i * 10) % 100,
      isUnlocked: i % 3 != 0,
      studyCount: i % 4,
      parentId: i > 0 && i % 5 == 0 ? 'node_${i - 1}' : null,
    ),);
  }

  return nodes;
}

/// 生成模拟边
List<GalaxyEdgeModel> _generateMockEdges(List<GalaxyNodeModel> nodes) {
  final edges = <GalaxyEdgeModel>[];

  for (var i = 1; i < nodes.length; i++) {
    if (i % 3 == 0) {
      edges.add(GalaxyEdgeModel(
        id: 'edge_$i',
        sourceId: nodes[i - 1].id,
        targetId: nodes[i].id,
        strength: 0.5 + (i % 5) * 0.1,
      ),);
    }
  }

  return edges;
}
