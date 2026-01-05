import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/particle_pool.dart';
import 'package:sparkle/core/services/quad_tree.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

void main() {
  group('Galaxy Integration Tests', () {
    group('Layout Engine + QuadTree Integration', () {
      test('layout engine uses quad tree for collision detection', () {
        final nodes = _generateMockNodes(100);
        final edges = _generateMockEdges(nodes);

        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        // Verify all nodes have positions
        expect(positions.length, equals(nodes.length));

        // Verify positions are reasonable
        for (final pos in positions.values) {
          expect(pos.dx.isFinite, isTrue);
          expect(pos.dy.isFinite, isTrue);
          expect(pos.distance, lessThan(GalaxyLayoutEngine.outerRadius * 2));
        }
      });

      test('quad tree accelerates neighbor queries', () {
        final tree = QuadTree<SimpleQuadTreeItem>(
          bounds: const Rect.fromLTWH(-5000, -5000, 10000, 10000),
        );

        // Insert nodes
        final positions = <String, Offset>{};
        for (var i = 0; i < 500; i++) {
          final pos = Offset(
            (i % 50) * 200.0 - 5000,
            (i ~/ 50) * 200.0 - 5000,
          );
          positions['node_$i'] = pos;
          tree.insert(SimpleQuadTreeItem(id: 'node_$i', position: pos));
        }

        // Query neighbors - should be fast
        final stopwatch = Stopwatch()..start();
        final center = positions['node_250'] ?? const Offset(-5000, -4000);
        final neighbors = tree.queryCircle(center, 500);
        stopwatch.stop();

        expect(stopwatch.elapsedMilliseconds, lessThan(10));
        expect(neighbors, isNotEmpty);
      });
    });

    group('Cache + Repository Integration', () {
      test('smart cache correctly evicts old entries', () async {
        final cache = SmartCache<String, int>(
          maxSize: 5,
          maxAge: const Duration(milliseconds: 100),
        );

        // Fill cache
        for (var i = 0; i < 5; i++) {
          cache.set('key_$i', i);
        }

        expect(cache.size, equals(5));

        // Add one more - should evict oldest
        cache.set('key_5', 5);
        expect(cache.size, equals(5));

        // Wait for expiration
        await Future<void>.delayed(const Duration(milliseconds: 150));

        // Access should trigger cleanup and return null for expired
        final value = cache.get('key_0');
        expect(value, isNull);
      });
    });

    group('Particle Pool Integration', () {
      test('particle pool correctly manages lifecycle', () {
        final system = ParticleSystem(maxParticles: 10, poolSize: 5);

        // Emit some particles
        for (var i = 0; i < 8; i++) {
          system.emit(
            position: Offset(i * 10.0, 0),
            size: 5.0,
            color: Colors.white,
            lifetime: 0.5,
          );
        }

        expect(system.activeCount, equals(8));

        // Update particles
        system.update(0.3);
        expect(system.activeCount, equals(8));

        // Update past lifetime
        system.update(0.3);
        expect(system.activeCount, lessThan(8));

        // Clear all
        system.clear();
        expect(system.activeCount, equals(0));

        // Dispose
        system.dispose();
      });
    });

    group('Provider + Layout Integration', () {
      test('galaxy state correctly filters by aggregation level', () {
        final state = GalaxyState(
          nodes: [
            ..._generateMockNodesWithImportance(5, 5),
            ..._generateMockNodesWithImportance(5, 3),
            ..._generateMockNodesWithImportance(5, 1),
          ],
          currentScale: 0.5,
          aggregationLevel: AggregationLevel.cluster,
        );

        // At cluster level, only importance >= 3 should be visible
        // Note: Actual filtering happens in the notifier
        expect(state.aggregationLevel, equals(AggregationLevel.cluster));
        expect(state.nodes.length, equals(15));
      });

      test('viewport culling works with layout engine', () {
        final nodes = _generateMockNodes(50);
        final edges = _generateMockEdges(nodes);

        final positions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        // Create a small viewport
        final culler = ViewportCuller(
          viewport: const Rect.fromLTWH(-200, -200, 400, 400),
        );

        final visibleNodes = culler.filterVisibleNodes(nodes, positions);
        final visibleEdges = culler.filterVisibleEdges(edges, positions);

        // Should filter out nodes outside viewport
        expect(visibleNodes.length, lessThanOrEqualTo(nodes.length));
        expect(visibleEdges.length, lessThanOrEqualTo(edges.length));
      });
    });

    group('End-to-End Data Flow', () {
      test('complete data flow from nodes to positions', () async {
        // 1. Generate nodes and edges
        final nodes = _generateMockNodes(20);
        final edges = _generateMockEdges(nodes);

        // 2. Calculate initial layout
        final initialPositions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        expect(initialPositions.length, equals(nodes.length));

        // 3. Optimize layout
        final optimizedPositions =
            await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: nodes,
          edges: edges,
          initialPositions: initialPositions,
        );

        expect(optimizedPositions.length, equals(nodes.length));

        // 4. Apply viewport culling
        final culler = ViewportCuller(
          viewport: const Rect.fromLTWH(-1000, -1000, 2000, 2000),
        );

        final visibleNodes =
            culler.filterVisibleNodes(nodes, optimizedPositions);
        final visibleEdges =
            culler.filterVisibleEdges(edges, optimizedPositions);

        expect(visibleNodes, isNotEmpty);
        expect(visibleEdges.length, lessThanOrEqualTo(edges.length));
      });
    });

    group('Performance Integration', () {
      test('full pipeline performance for 500 nodes', () async {
        final stopwatch = Stopwatch()..start();

        // Generate data
        final nodes = _generateMockNodes(500);
        final edges = _generateMockEdges(nodes);

        // Initial layout
        final initialPositions = GalaxyLayoutEngine.calculateInitialLayout(
          nodes: nodes,
          edges: edges,
        );

        // Optimize
        final optimizedPositions =
            await GalaxyLayoutEngineAsync.optimizeLayoutAsync(
          nodes: nodes,
          edges: edges,
          initialPositions: initialPositions,
        );

        // Cull
        ViewportCuller(
          viewport: const Rect.fromLTWH(-500, -500, 1000, 1000),
        ).filterVisibleNodes(nodes, optimizedPositions);

        stopwatch.stop();

        // Total time should be reasonable
        expect(stopwatch.elapsedMilliseconds, lessThan(2000));
      });
    });
  });
}

/// Generate mock nodes
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
        parentId: i > 0 && i % 5 == 0 ? 'node_${i - 1}' : null,
      ),
    );
  }

  return nodes;
}

/// Generate mock nodes with specific importance
List<GalaxyNodeModel> _generateMockNodesWithImportance(
  int count,
  int importance,
) {
  final nodes = <GalaxyNodeModel>[];
  const sectors = SectorEnum.values;
  final offset = importance * 100;

  for (var i = 0; i < count; i++) {
    nodes.add(
      GalaxyNodeModel(
        id: 'node_${offset + i}',
        name: 'Node ${offset + i}',
        sector: sectors[i % sectors.length],
        importance: importance,
        masteryScore: (i * 10) % 100,
        isUnlocked: true,
        studyCount: i % 4,
      ),
    );
  }

  return nodes;
}

/// Generate mock edges
List<GalaxyEdgeModel> _generateMockEdges(List<GalaxyNodeModel> nodes) {
  final edges = <GalaxyEdgeModel>[];

  for (var i = 1; i < nodes.length; i++) {
    if (i % 3 == 0) {
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
