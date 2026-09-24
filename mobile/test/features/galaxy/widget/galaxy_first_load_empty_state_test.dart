import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/smart_cache.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import '../../../shared/i18n_test_helper.dart';

/// V24-B 回归：首次进入 galaxy 星图页（真实 GalaxyScreen + 真实 GalaxyNotifier +
/// 延迟返回 147 节点的仓库），graph 200 后 UI 不得停留在「星图空空如也」空态，
/// 也不应依赖下拉刷新才能恢复。
void main() {
  setUp(setUpI18nForTesting);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
    'V24: first graph load (147 nodes) must render star map without pull-to-refresh',
    (tester) async {
      final repository = _DelayedGraphFakeRepository(
        responseDelay: const Duration(milliseconds: 350),
      );
      final container = ProviderContainer(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(repository),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          // 需挂 DS 主题，否则 SparkleThemeExtension 未注册，构建即抛断言。
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const GalaxyScreen(),
          ),
        ),
      );

      // First frame: initState post-frame callback schedules _loadGraph.
      await tester.pump();
      // Post-frame callback runs; loading panel expected while request in flight.
      await tester.pump();
      expect(
        find.text('加载中'),
        findsOneWidget,
        reason: 'graph 请求在途时应显示加载态',
      );

      // Response arrives (147 nodes, 200 OK parsed through real fromJson).
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 100));

      expect(
        find.text('星图空空如也'),
        findsNothing,
        reason:
            'graph 已成功返回 147 节点，首进不得停留在「星图空空如也」空态（V24-B），'
            '更不应依赖下拉刷新恢复',
      );
      expect(
        find.text('加载中'),
        findsNothing,
        reason: 'graph 已成功返回，加载态应退位',
      );
      // Star map actually painted (node positions computed for the graph).
      final state = container.read(galaxyProvider);
      expect(state.nodes, hasLength(147));
      expect(state.isLoading, isFalse);

      // 收尾：先卸载 UI（屏幕 State 取消自身 timer），再释放 container
      // （notifier dispose 取消 SSE 重连/性能监控 timer），最后冲刷剩余单次 timer，
      // 避免 flutter_test 的 pending-timer 不变量误报。
      await tester.pumpWidget(const SizedBox.shrink());
      container.dispose();
      await tester.pump(const Duration(seconds: 10));
    },
  );

  testWidgets(
    'V24: gateway gRPC-shape payload (node_id/label) must still render star map',
    (tester) async {
      // gateway GetGraph gRPC 优先路径返回 proto 形状（node_id/label/mastery），
      // 与 REST 形状（id/name/mastery_score）不同。V24 现场首载即该形状：
      // 200 + 147 节点却解析成 147 个无名壳 → 全部被剔除 → 「星图空空如也」。
      final repository = _DelayedGraphFakeRepository(
        responseDelay: const Duration(milliseconds: 350),
        payloadBuilder: _grpcShapePayload,
      );
      final container = ProviderContainer(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(repository),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const GalaxyScreen(),
          ),
        ),
      );

      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 100));

      expect(
        find.text('星图空空如也'),
        findsNothing,
        reason: 'gRPC 形状载荷解析后必须可渲染，不得误判为空星图（V24-B）',
      );
      final state = container.read(galaxyProvider);
      expect(state.nodes, hasLength(147));
      expect(
        state.nodes.every((node) => node.id.isNotEmpty && node.name.isNotEmpty),
        isTrue,
        reason: '不允许出现无名节点壳（会被 _isRenderableNode 全数剔除）',
      );

      await tester.pumpWidget(const SizedBox.shrink());
      container.dispose();
      await tester.pump(const Duration(seconds: 10));
    },
  );
}

/// gateway GetGraph gRPC 优先路径的实际返回形状。
Map<String, dynamic> _grpcShapePayload() {
  final rest = _graphPayload(nodeCount: 147);
  final nodes = (rest['nodes'] as List<Map<String, dynamic>>)
      .map((node) => {
            'node_id': node['id'],
            'label': node['name'],
            'node_type': 'concept',
            'mastery': node['mastery_score'],
          },)
      .toList();
  final edges = ((rest['edges'] as List<Map<String, dynamic>>).isNotEmpty
          ? rest['edges']
          : <Map<String, dynamic>>[]) as List<Map<String, dynamic>>;
  return {
    'nodes': nodes,
    'edges': edges
        .map((edge) => {
              'source_id': edge['source_id'],
              'target_id': edge['target_id'],
              'relation': 'parent',
            },)
        .toList(),
    'total_nodes': 147,
    'via': 'grpc',
  };
}

class _DelayedGraphFakeRepository implements EnhancedGalaxyRepository {
  _DelayedGraphFakeRepository({
    this.responseDelay = Duration.zero,
    Map<String, dynamic> Function()? payloadBuilder,
  })  : _payloadBuilder =
            payloadBuilder ?? (() => _graphPayload(nodeCount: 147));

  final Duration responseDelay;
  final Map<String, dynamic> Function() _payloadBuilder;

  int getGraphCalls = 0;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async {
    getGraphCalls += 1;
    await Future<void>.delayed(responseDelay);
    return NetworkResult.success(
      GalaxyGraphResponse.fromJson(_payloadBuilder()),
    );
  }

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
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) {
    // 永不结束的空事件流：模拟已建流的 SSE 连接（立即 done 会触发 5s 重连循环）。
    final controller = StreamController<SSEEvent>();
    _eventStreamControllers.add(controller);
    return controller.stream;
  }

  final _eventStreamControllers = <StreamController<SSEEvent>>[];

  void close() {
    for (final controller in _eventStreamControllers) {
      unawaited(controller.close());
    }
  }

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

/// 模拟后端 /galaxy/graph 真实载荷形状：147 节点 + 父子树 + 边。
Map<String, dynamic> _graphPayload({required int nodeCount}) {
  final sectors = [
    'TECH',
    'SCIENCE',
    'HUMANITIES',
    'ARTS',
    'LIFE',
    'COSMOS',
  ];
  final nodes = <Map<String, dynamic>>[];
  final edges = <Map<String, dynamic>>[];
  for (var i = 0; i < nodeCount; i++) {
    final isRoot = i % 12 == 0;
    final parentId = isRoot ? null : 'node_${(i ~/ 12) * 12}';
    nodes.add({
      'id': 'node_$i',
      'name': '知识点 $i',
      'importance': isRoot ? 5 : (i % 4) + 1,
      'sector_code': sectors[i % sectors.length],
      'parent_id': parentId,
      'is_unlocked': true,
      'mastery_score': (i * 7) % 100,
      'study_count': i % 5,
    });
    if (parentId != null) {
      edges.add({
        'id': 'edge_parent_$i',
        'source_id': parentId,
        'target_id': 'node_$i',
        'relation_type': 'parent_child',
        'strength': 0.8,
      });
    }
  }
  return {
    'nodes': nodes,
    'edges': edges,
    'user_flame_intensity': 0.42,
  };
}
