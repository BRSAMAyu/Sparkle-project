import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('Galaxy Widget Tests', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
    });

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

    testWidgets('mastery colors differ for sprint progress nodes', (
      tester,
    ) async {
      final lowMasteryNode = GalaxyNodeModel.fromJson({
        'id': 'low',
        'name': 'Low mastery',
        'importance': 3,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 0.1,
      });
      final highMasteryNode = GalaxyNodeModel.fromJson({
        'id': 'high',
        'name': 'High mastery',
        'importance': 3,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 0.6,
      });
      final lowColor = galaxyMasteryNodeColor(
        masteryScore: lowMasteryNode.masteryScore,
        isDarkMode: true,
      );
      final highColor = galaxyMasteryNodeColor(
        masteryScore: highMasteryNode.masteryScore,
        isDarkMode: true,
      );

      expect(lowMasteryNode.masteryScore, equals(10));
      expect(highMasteryNode.masteryScore, equals(60));
      expect(highColor, isNot(lowColor));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _MasteryColorProbe(
                    key: const ValueKey('low-mastery-node-color'),
                    color: lowColor,
                  ),
                  _MasteryColorProbe(
                    key: const ValueKey('high-mastery-node-color'),
                    color: highColor,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      final lowBox = tester.widget<DecoratedBox>(
        find.descendant(
          of: find.byKey(const ValueKey('low-mastery-node-color')),
          matching: find.byType(DecoratedBox),
        ),
      );
      final highBox = tester.widget<DecoratedBox>(
        find.descendant(
          of: find.byKey(const ValueKey('high-mastery-node-color')),
          matching: find.byType(DecoratedBox),
        ),
      );
      final lowDecoration = lowBox.decoration as BoxDecoration;
      final highDecoration = highBox.decoration as BoxDecoration;

      expect(lowDecoration.color, isNot(highDecoration.color));
    });

    testWidgets('GalaxyScreen shows retry state and reloads after retry',
        (tester) async {
      final notifier = _RetryGalaxyScreenNotifier();
      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith((ref) => notifier),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const GalaxyScreen(),
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      expect(find.textContaining('galaxy 500'), findsOneWidget);
      expect(find.byType(FilledButton), findsWidgets);

      await tester.tap(find.byType(FilledButton).first);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1200));

      expect(notifier.loadCalls, equals(2));
      expect(find.textContaining('galaxy 500'), findsNothing);
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

class FakeEnhancedGalaxyRepository implements EnhancedGalaxyRepository {
  FakeEnhancedGalaxyRepository();

  int getGraphCalls = 0;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraphForViewport({
    required Rect viewport,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<UserGalaxyContribution>> getContributionStats() async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<void>> updateNodePositions(
    Map<String, Offset> positions,
  ) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> updateNodePosition(
    String nodeId,
    Offset position,
  ) async =>
      updateNodePositions(<String, Offset>{nodeId: position});

  @override
  Future<NetworkResult<Map<String, dynamic>>> updateNodeMastery(
    String nodeId, {
    required int mastery,
    String reason = 'manual_update',
  }) async =>
      NetworkResult.success(<String, dynamic>{});

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<NetworkResult<void>> sparkNode(String id) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> toggleFavorite(String nodeId) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<void>> pauseDecay(String nodeId, bool pause) async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<KnowledgeDetailResponse>> getNodeDetail(
    String nodeId,
  ) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<GalaxyNodeHistory>> getNodeHistory(
    String nodeId, {
    String? packId,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  Future<NetworkResult<KnowledgeDetailResponse?>> predictNextNode() async =>
      NetworkResult.success(null);

  @override
  Future<NetworkResult<List<GalaxySearchResult>>> searchNodes(
    String query,
  ) async =>
      NetworkResult.success(const <GalaxySearchResult>[]);

  @override
  Future<NetworkResult<NodeChunksResponse>> getNodeSourceChunks(
    String nodeId, {
    int page = 1,
    int pageSize = 100,
  }) async =>
      NetworkResult.failure(GalaxyError.unknown('Not implemented'));

  @override
  void clearCache() {}

  @override
  CircuitState get circuitBreakerState => CircuitState.closed;

  @override
  void resetCircuitBreaker() {}

  @override
  Map<String, CacheStats> get cacheStats => const <String, CacheStats>{};
}

// Test widgets
class _MasteryColorProbe extends StatelessWidget {
  const _MasteryColorProbe({super.key, required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        child: const SizedBox.square(dimension: 24),
      );
}

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
  Stream<MasteryMilestoneEvent> get masteryMilestones => const Stream.empty();

  @override
  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
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

  @override
  Future<void> refreshForTaskCompletion({
    Map<String, dynamic>? galaxyUpdate,
  }) async {}

  @override
  void beginNodeDrag(String nodeId) {
    state = state.copyWith(
      draggingNodeId: nodeId,
      selectedNodeId: nodeId,
      expandedEdgeNodeIds: {nodeId},
    );
  }

  @override
  void updateDraggedNodePosition(String nodeId, Offset newPosition) {
    final positions = Map<String, Offset>.from(state.nodePositions)
      ..[nodeId] = newPosition;
    state = state.copyWith(nodePositions: positions);
  }

  @override
  Future<void> endNodeDrag() async {
    state = state.copyWith(draggingNodeId: null);
  }

  @override
  void setEvidenceHighlight(Set<String> ids, {String? focusId}) {
    state = state.copyWith(
      highlightedNodeIdHashes: ids.map((e) => e.hashCode).toSet(),
    );
  }

  @override
  void clearFocusBounds() {
    state = state.copyWith(focusBounds: null);
  }

  @override
  void clearFocusNode() {
    state = state.copyWith(focusNodeId: null);
  }

  @override
  void clearEvidenceHighlight() {
    state = state.copyWith(
      highlightedNodeIdHashes: const {},
      highlightRevision: state.highlightRevision + 1,
    );
  }

  @override
  void setFocusNode(String nodeId) {
    state = state.copyWith(focusNodeId: nodeId);
  }
}

class _RetryGalaxyScreenNotifier extends _MockGalaxyNotifier {
  _RetryGalaxyScreenNotifier() : super(GalaxyState());

  int loadCalls = 0;

  @override
  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
    loadCalls += 1;
    state = state.copyWith(isLoading: true, lastError: null);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    if (loadCalls == 1) {
      state = state.copyWith(
        isLoading: false,
        lastError: GalaxyError.unknown('galaxy 500'),
      );
      return;
    }

    final nodes = _generateMockNodes(3);
    final edges = _generateMockEdges(nodes);
    final positions = <String, Offset>{
      for (var i = 0; i < nodes.length; i++) nodes[i].id: Offset(i * 80, 0),
    };
    state = state.copyWith(
      isLoading: false,
      lastError: null,
      nodes: nodes,
      edges: edges,
      nodePositions: positions,
      visibleNodes: nodes,
      visibleEdges: edges,
      userFlameIntensity: 0.4,
    );
  }
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
