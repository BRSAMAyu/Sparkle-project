import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

void main() {
  group('Galaxy Widget Tests', () {
    testWidgets('GalaxyState renders loading indicator when loading', (
      tester,
    ) async {
      // Create a provider override with loading state
      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _MockGalaxyNotifier(GalaxyState(isLoading: true)),
          ),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(
            home: Scaffold(
              body: _TestGalaxyLoadingWidget(),
            ),
          ),
        ),
      );

      // Should show loading indicator
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      container.dispose();
    });

    testWidgets('GalaxyState shows content when loaded', (tester) async {
      final testNodes = _generateMockNodes(5);
      final testPositions = <String, Offset>{};
      for (var i = 0; i < testNodes.length; i++) {
        testPositions[testNodes[i].id] = Offset(i * 100.0, i * 100.0);
      }

      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _MockGalaxyNotifier(
              GalaxyState(
                nodes: testNodes,
                nodePositions: testPositions,
                visibleNodes: testNodes,
              ),
            ),
          ),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(
            home: Scaffold(
              body: _TestGalaxyContentWidget(),
            ),
          ),
        ),
      );

      // Should show content
      expect(find.text('5 nodes loaded'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsNothing);

      container.dispose();
    });

    testWidgets('Node selection updates state', (tester) async {
      final testNodes = _generateMockNodes(3);
      final testPositions = <String, Offset>{};
      for (var i = 0; i < testNodes.length; i++) {
        testPositions[testNodes[i].id] = Offset(i * 100.0, i * 100.0);
      }

      final notifier = _MockGalaxyNotifier(
        GalaxyState(
          nodes: testNodes,
          nodePositions: testPositions,
          visibleNodes: testNodes,
        ),
      );

      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith((ref) => notifier),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            home: Scaffold(
              body: _TestNodeSelectionWidget(
                onSelect: () => notifier.selectNode('node_0'),
              ),
            ),
          ),
        ),
      );

      // Tap to select node
      await tester.tap(find.byType(ElevatedButton));
      await tester.pump();

      // Check state was updated
      expect(container.read(galaxyProvider).selectedNodeId, equals('node_0'));

      container.dispose();
    });

    testWidgets('Scale changes update aggregation level', (tester) async {
      final notifier = _MockGalaxyNotifier(
        GalaxyState(
          nodes: _generateMockNodes(10),
        ),
      );

      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith((ref) => notifier),
        ],
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            home: Scaffold(
              body: _TestScaleWidget(notifier: notifier),
            ),
          ),
        ),
      );

      // Test scale changes
      await tester.tap(find.text('Universe'));
      await tester.pump();
      expect(
        container.read(galaxyProvider).aggregationLevel,
        equals(AggregationLevel.universe),
      );

      await tester.tap(find.text('Full'));
      await tester.pump();
      expect(
        container.read(galaxyProvider).aggregationLevel,
        equals(AggregationLevel.full),
      );

      container.dispose();
    });
  });

  group('GalaxyState Tests', () {
    test('copyWith creates correct copy', () {
      final original = GalaxyState(
        nodes: _generateMockNodes(5),
        isLoading: true,
        currentScale: 1.5,
        selectedNodeId: 'test',
      );

      final copy = original.copyWith(isLoading: false);

      expect(copy.nodes.length, equals(5));
      expect(copy.isLoading, isFalse);
      expect(copy.currentScale, equals(1.5));
      expect(copy.selectedNodeId, equals('test'));
    });

    test('copyWith handles all fields', () {
      final original = GalaxyState();
      final newNodes = _generateMockNodes(3);
      final newEdges = _generateMockEdges(newNodes);
      final newPositions = {'node_0': const Offset(100, 200)};

      final copy = original.copyWith(
        nodes: newNodes,
        edges: newEdges,
        nodePositions: newPositions,
        isLoading: true,
        isOptimizing: true,
        currentScale: 2.0,
        aggregationLevel: AggregationLevel.galaxy,
        selectedNodeId: 'node_1',
        expandedEdgeNodeIds: {'node_0', 'node_1'},
      );

      expect(copy.nodes, equals(newNodes));
      expect(copy.edges, equals(newEdges));
      expect(copy.nodePositions, equals(newPositions));
      expect(copy.isLoading, isTrue);
      expect(copy.isOptimizing, isTrue);
      expect(copy.currentScale, equals(2.0));
      expect(copy.aggregationLevel, equals(AggregationLevel.galaxy));
      expect(copy.selectedNodeId, equals('node_1'));
      expect(copy.expandedEdgeNodeIds, contains('node_0'));
    });
  });

  group('ClusterInfo Tests', () {
    test('creates cluster with all properties', () {
      final cluster = ClusterInfo(
        id: 'cluster_1',
        name: 'Test Cluster',
        position: const Offset(100, 200),
        nodeCount: 10,
        totalMastery: 75.0,
        sector: SectorEnum.cosmos,
        childNodeIds: ['a', 'b', 'c'],
      );

      expect(cluster.id, equals('cluster_1'));
      expect(cluster.name, equals('Test Cluster'));
      expect(cluster.position, equals(const Offset(100, 200)));
      expect(cluster.nodeCount, equals(10));
      expect(cluster.totalMastery, equals(75.0));
      expect(cluster.sector, equals(SectorEnum.cosmos));
      expect(cluster.childNodeIds, hasLength(3));
    });
  });
}

// Test widgets
class _TestGalaxyLoadingWidget extends ConsumerWidget {
  const _TestGalaxyLoadingWidget();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(galaxyProvider);
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    return const Text('Loaded');
  }
}

class _TestGalaxyContentWidget extends ConsumerWidget {
  const _TestGalaxyContentWidget();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(galaxyProvider);
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    return Text('${state.nodes.length} nodes loaded');
  }
}

class _TestNodeSelectionWidget extends ConsumerWidget {
  const _TestNodeSelectionWidget({required this.onSelect});

  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(galaxyProvider);
    return Column(
      children: [
        Text('Selected: ${state.selectedNodeId ?? 'none'}'),
        ElevatedButton(
          onPressed: onSelect,
          child: const Text('Select Node'),
        ),
      ],
    );
  }
}

class _TestScaleWidget extends StatelessWidget {
  const _TestScaleWidget({required this.notifier});

  final _MockGalaxyNotifier notifier;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          TextButton(
            onPressed: () => notifier.updateScale(0.1),
            child: const Text('Universe'),
          ),
          TextButton(
            onPressed: () => notifier.updateScale(0.3),
            child: const Text('Galaxy'),
          ),
          TextButton(
            onPressed: () => notifier.updateScale(0.5),
            child: const Text('Cluster'),
          ),
          TextButton(
            onPressed: () => notifier.updateScale(0.7),
            child: const Text('Nebula'),
          ),
          TextButton(
            onPressed: () => notifier.updateScale(0.9),
            child: const Text('Full'),
          ),
        ],
      );
}

// Mock notifier for testing
class _MockGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _MockGalaxyNotifier(super.state);

  @override
  void selectNode(String nodeId) {
    state = state.copyWith(
      selectedNodeId: nodeId,
      expandedEdgeNodeIds: {nodeId},
    );
  }

  @override
  void deselectNode() {
    state = GalaxyState(
      nodes: state.nodes,
      edges: state.edges,
      nodePositions: state.nodePositions,
      visibleNodes: state.visibleNodes,
      visibleEdges: state.visibleEdges,
      isLoading: state.isLoading,
      currentScale: state.currentScale,
      aggregationLevel: state.aggregationLevel,
    );
  }

  @override
  void updateScale(double scale) {
    AggregationLevel newLevel;
    if (scale < 0.2) {
      newLevel = AggregationLevel.universe;
    } else if (scale < 0.4) {
      newLevel = AggregationLevel.galaxy;
    } else if (scale < 0.6) {
      newLevel = AggregationLevel.cluster;
    } else if (scale < 0.8) {
      newLevel = AggregationLevel.nebula;
    } else {
      newLevel = AggregationLevel.full;
    }
    state = state.copyWith(currentScale: scale, aggregationLevel: newLevel);
  }

  @override
  void updateViewport(Rect viewport) {
    state = state.copyWith(viewport: viewport);
  }

  @override
  Future<void> loadGalaxy({bool forceRefresh = false}) async {
    state = state.copyWith(isLoading: true);
    await Future<void>.delayed(const Duration(milliseconds: 100));
    state = state.copyWith(isLoading: false);
  }

  @override
  Future<GalaxyError?> sparkNode(String id) async => null;

  @override
  Future<String?> predictNextNode() async => null;

  @override
  Future<List<GalaxySearchResult>> searchNodes(String query) async => [];
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
