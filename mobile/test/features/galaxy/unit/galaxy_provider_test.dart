import 'dart:async';
import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';
// ignore_for_file: cascade_invocations

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

class FakeEnhancedGalaxyRepository implements EnhancedGalaxyRepository {
  FakeEnhancedGalaxyRepository({
    NetworkResult<GalaxyGraphResponse>? graphResult,
    Stream<SSEEvent>? eventsStreamOverride,
  })  : graphResult = graphResult ??
            NetworkResult.failure(GalaxyError.unknown('Not initialized')),
        eventsStream = eventsStreamOverride ?? const Stream.empty();

  NetworkResult<GalaxyGraphResponse> graphResult;
  Stream<SSEEvent> eventsStream;
  int getGraphCalls = 0;
  int sparkNodeCalls = 0;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async {
    getGraphCalls++;
    return graphResult;
  }

  @override
  Stream<SSEEvent> getGalaxyEventsStream() => eventsStream;

  @override
  Future<NetworkResult<void>> sparkNode(String id) async {
    sparkNodeCalls++;
    return NetworkResult.success(null);
  }

  @override
  Future<NetworkResult<void>> toggleFavorite(String nodeId) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> pauseDecay(String nodeId, bool pause) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<KnowledgeDetailResponse>> getNodeDetail(
          String nodeId,) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<KnowledgeDetailResponse?>> predictNextNode() async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<List<GalaxySearchResult>>> searchNodes(
          String query,) async =>
      NetworkResult.success(const []);

  @override
  void clearCache() {}

  @override
  CircuitState get circuitBreakerState => CircuitState.closed;

  @override
  void resetCircuitBreaker() {}

  @override
  Map<String, CacheStats> get cacheStats => const {};
}

void main() {
  late FakeEnhancedGalaxyRepository mockRepository;
  late ProviderContainer container;

  setUp(() {
    mockRepository = FakeEnhancedGalaxyRepository();

    container = ProviderContainer(
      overrides: [
        enhancedGalaxyRepositoryProvider.overrideWithValue(mockRepository),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('GalaxyNotifier', () {
    group('Initial State', () {
      test('starts with empty state', () {
        final state = container.read(galaxyProvider);

        expect(state.nodes, isEmpty);
        expect(state.edges, isEmpty);
        expect(state.nodePositions, isEmpty);
        expect(state.isLoading, isFalse);
        expect(state.isOptimizing, isFalse);
        expect(state.selectedNodeId, isNull);
        expect(state.aggregationLevel, AggregationLevel.full);
      });
    });

    group('loadGalaxy', () {
      test('sets loading state and loads data', () async {
        final testNodes = _generateMockNodes(10);
        final testEdges = _generateMockEdges(testNodes);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: testEdges,
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);

        // Start loading
        final loadFuture = notifier.loadGalaxy();

        // Check loading state
        await Future<void>.delayed(const Duration(milliseconds: 10));

        // Wait for completion
        await loadFuture;

        final state = container.read(galaxyProvider);
        expect(state.nodes.length, equals(10));
        expect(state.edges.length, equals(testEdges.length));
        expect(state.nodePositions, isNotEmpty);
        expect(state.userFlameIntensity, equals(0.5));
      });

      test('preserves existing positions on reload', () async {
        final testNodes = _generateMockNodes(5);
        final testEdges = _generateMockEdges(testNodes);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: testEdges,
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);

        // First load
        await notifier.loadGalaxy();
        final firstPositions = Map<String, Offset>.from(
          container.read(galaxyProvider).nodePositions,
        );

        // Second load
        await notifier.loadGalaxy();
        final secondPositions = container.read(galaxyProvider).nodePositions;

        // Positions should be preserved
        for (final nodeId in firstPositions.keys) {
          expect(secondPositions[nodeId], equals(firstPositions[nodeId]));
        }
      });

      test('handles errors gracefully', () async {
        mockRepository.graphResult =
            NetworkResult.failure(GalaxyError.unknown('Network error'));

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        final state = container.read(galaxyProvider);
        expect(state.isLoading, isFalse);
        expect(state.nodes, isEmpty);
      });
    });

    group('Node Selection', () {
      test('selectNode updates selected node and expands connections',
          () async {
        final testNodes = _generateMockNodes(10);
        final testEdges = _generateMockEdges(testNodes);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: testEdges,
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // Select a node
        notifier.selectNode('node_0');

        final state = container.read(galaxyProvider);
        expect(state.selectedNodeId, equals('node_0'));
        expect(state.expandedEdgeNodeIds, contains('node_0'));
      });

      test('deselectNode clears selection and expanded edges', () async {
        final testNodes = _generateMockNodes(5);
        final testEdges = _generateMockEdges(testNodes);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: testEdges,
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        notifier.selectNode('node_0');
        expect(container.read(galaxyProvider).selectedNodeId, isNotNull);

        notifier.deselectNode();

        final state = container.read(galaxyProvider);
        expect(state.selectedNodeId, isNull);
        expect(state.expandedEdgeNodeIds, isEmpty);
      });
    });

    group('Scale and Aggregation', () {
      test('updateScale changes aggregation level correctly', () async {
        final testNodes = _generateMockNodes(20);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // Test different scale levels
        notifier.updateScale(0.1);
        expect(
          container.read(galaxyProvider).aggregationLevel,
          equals(AggregationLevel.universe),
        );

        notifier.updateScale(0.3);
        expect(
          container.read(galaxyProvider).aggregationLevel,
          equals(AggregationLevel.galaxy),
        );

        notifier.updateScale(0.5);
        expect(
          container.read(galaxyProvider).aggregationLevel,
          equals(AggregationLevel.cluster),
        );

        notifier.updateScale(0.7);
        expect(
          container.read(galaxyProvider).aggregationLevel,
          equals(AggregationLevel.nebula),
        );

        notifier.updateScale(0.9);
        expect(
          container.read(galaxyProvider).aggregationLevel,
          equals(AggregationLevel.full),
        );
      });

      test('aggregation level filters visible nodes correctly', () async {
        final testNodes = [
          ..._generateMockNodesWithImportance(5, 5), // importance 5
          ..._generateMockNodesWithImportance(5, 3), // importance 3
          ..._generateMockNodesWithImportance(5, 1), // importance 1
        ];

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // At cluster level (importance >= 3)
        notifier.updateScale(0.5);
        notifier
            .updateViewport(const Rect.fromLTWH(-5000, -5000, 10000, 10000));
        await Future<void>.delayed(
          const Duration(milliseconds: 150),
        ); // Wait for throttle

        final clusterState = container.read(galaxyProvider);
        final visibleImportances =
            clusterState.visibleNodes.map((n) => n.importance);
        expect(visibleImportances.every((i) => i >= 3), isTrue);
      });
    });

    group('Viewport Culling', () {
      test('updateViewport filters nodes outside viewport', () async {
        final testNodes = _generateMockNodes(100);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // Set a small viewport
        notifier.updateViewport(const Rect.fromLTWH(-100, -100, 200, 200));
        await Future<void>.delayed(
          const Duration(milliseconds: 150),
        ); // Wait for throttle

        final state = container.read(galaxyProvider);
        // Should have fewer visible nodes than total
        expect(state.visibleNodes.length, lessThan(testNodes.length));
      });

      test('viewport throttling prevents excessive updates', () async {
        final testNodes = _generateMockNodes(10);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        var updateCount = 0;
        container.listen(galaxyProvider, (previous, next) {
          if (previous?.viewport != next.viewport) {
            updateCount++;
          }
        });

        // Rapid viewport updates
        for (var i = 0; i < 10; i++) {
          notifier.updateViewport(Rect.fromLTWH(i * 10.0, 0, 500, 500));
        }

        await Future<void>.delayed(const Duration(milliseconds: 200));

        // Should have throttled updates
        expect(updateCount, lessThan(10));
      });
    });

    group('Spark Node', () {
      test('sparkNode calls repository and reloads', () async {
        final testNodes = _generateMockNodes(5);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );
        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        await notifier.sparkNode('node_0');

        expect(mockRepository.sparkNodeCalls, 1);
        // Should have reloaded (getGraph called twice)
        expect(mockRepository.getGraphCalls, 2);
      });
    });

    group('Cluster Calculation', () {
      test('calculates sector clusters at galaxy level', () async {
        final testNodes = _generateMockNodes(30);

        mockRepository.graphResult = NetworkResult.success(
          GalaxyGraphResponse(
            nodes: testNodes,
            edges: [],
            userFlameIntensity: 0.5,
          ),
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // Set galaxy level (0.2-0.4)
        notifier.updateScale(0.3);

        final state = container.read(galaxyProvider);
        expect(state.clusters, isNotEmpty);

        // Should have clusters for each sector
        final clusterIds = state.clusters.keys;
        expect(clusterIds.any((id) => id.startsWith('sector_')), isTrue);
      });
    });

    group('Event Handling', () {
      test('handles galaxy.node.updated and performs optimistic update',
          () async {
        final testNodes = _generateMockNodes(5);
        final targetNodeId = testNodes[0].id;
        final initialMastery = testNodes[0].masteryScore;
        final newMastery = initialMastery + 20;

        final eventsController = StreamController<SSEEvent>();
        mockRepository = FakeEnhancedGalaxyRepository(
          graphResult: NetworkResult.success(
            GalaxyGraphResponse(
              nodes: testNodes,
              edges: [],
              userFlameIntensity: 0.5,
            ),
          ),
          eventsStreamOverride: eventsController.stream,
        );

        // Re-override to use the new mock with events controller
        container = ProviderContainer(
          overrides: [
            enhancedGalaxyRepositoryProvider.overrideWithValue(mockRepository),
          ],
        );

        final notifier = container.read(galaxyProvider.notifier);
        await notifier.loadGalaxy();

        // Verify initial state
        expect(container.read(galaxyProvider).nodes[0].masteryScore,
            equals(initialMastery),);

        // Simulate event from backend
        eventsController.add(SSEEvent(
          event: 'galaxy.node.updated',
          data: '{"node_id": "$targetNodeId", "new_mastery": $newMastery}',
        ),);

        // Wait for event loop to process
        await Future<void>.delayed(const Duration(milliseconds: 10));

        // Verify state was updated optimistically without full reload
        final state = container.read(galaxyProvider);
        expect(state.nodes[0].masteryScore, equals(newMastery));
        expect(mockRepository.getGraphCalls, 1); // No reload triggered

        eventsController.close();
      });

      test('handles nodes_expanded and triggers reload', () async {
        final eventsController = StreamController<SSEEvent>();
        mockRepository.eventsStream = eventsController.stream;

        final notifier = container.read(galaxyProvider.notifier);

        // Simulate expansion event
        eventsController.add(SSEEvent(
          event: 'nodes_expanded',
          data: '{"nodes": []}',
        ),);

        // Wait for event loop
        await Future<void>.delayed(const Duration(milliseconds: 10));

        // Should have triggered loadGalaxy
        expect(mockRepository.getGraphCalls, 1);

        eventsController.close();
      });
    });
  });

  group('GalaxyState', () {
    test('copyWith preserves non-null values', () {
      final original = GalaxyState(
        nodes: _generateMockNodes(5),
        currentScale: 1.5,
        selectedNodeId: 'test_node',
      );

      final copied = original.copyWith(
        currentScale: 2.0,
      );

      expect(copied.nodes.length, equals(original.nodes.length));
      expect(copied.currentScale, equals(2.0));
      expect(copied.selectedNodeId, equals('test_node'));
    });
  });

  group('ClusterInfo', () {
    test('creates cluster with correct properties', () {
      final cluster = ClusterInfo(
        id: 'cluster_1',
        name: 'Test Cluster',
        position: const Offset(100, 200),
        nodeCount: 10,
        totalMastery: 75.5,
        sector: SectorEnum.cosmos,
        childNodeIds: ['node_1', 'node_2'],
      );

      expect(cluster.id, equals('cluster_1'));
      expect(cluster.name, equals('Test Cluster'));
      expect(cluster.position, equals(const Offset(100, 200)));
      expect(cluster.nodeCount, equals(10));
      expect(cluster.totalMastery, equals(75.5));
      expect(cluster.sector, equals(SectorEnum.cosmos));
      expect(cluster.childNodeIds, hasLength(2));
    });
  });

  group('AggregationLevel', () {
    test('has correct order', () {
      expect(
        AggregationLevel.universe.index,
        lessThan(AggregationLevel.galaxy.index),
      );
      expect(
        AggregationLevel.galaxy.index,
        lessThan(AggregationLevel.cluster.index),
      );
      expect(
        AggregationLevel.cluster.index,
        lessThan(AggregationLevel.nebula.index),
      );
      expect(
        AggregationLevel.nebula.index,
        lessThan(AggregationLevel.full.index),
      );
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
        parentId: i > 0 && i % 3 == 0 ? 'node_${i - 1}' : null,
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
  final offset = importance * 100; // Unique ID offset

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
