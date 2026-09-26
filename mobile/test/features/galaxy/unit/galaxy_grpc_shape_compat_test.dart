import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../../../shared/i18n_test_helper.dart';

/// V24-B 根因回归（客户端侧）：
///
/// gateway `GetGraph` 走 gRPC 优先路径时，把 proto `GalaxyNode{node_id,label,...}`
/// 直接塞进 `gin.H{"nodes": resp.Nodes}` 返回（Go json tag = `node_id`/`label`），
/// 与引擎 REST 路径的 `{id, name, mastery_score, ...}` 形状不一致。
/// Flutter 侧 `GalaxyNodeModel.fromJson`（P1-13/F7-10 防御式解析）把缺失的
/// id/name 吞成空串 → 147 个"无名节点"被 `_isRenderableNode` 全部剔除 →
/// 「星图空空如也」；且该"成功"结果被 `_graphCache` 缓存 10 分钟 → 会话内不可自愈，
/// 只有下拉刷新（forceRefresh 绕过缓存）能恢复。
///
/// 本文件锁定两层防线：
/// 1. 解析层兼容 gRPC 形状别名（node_id/label/mastery/relation）；
/// 2. 仓库层不缓存"声明了节点但解析不可用"的图，且返回 failure 而非静默成功。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('GalaxyNodeModel gRPC-shape compatibility', () {
    test('parses gateway gRPC node payload (node_id/label/mastery)', () {
      final node = GalaxyNodeModel.fromJson({
        'node_id': 'node-uuid-1',
        'label': '离散数学',
        'node_type': 'concept',
        'mastery': 40,
        'tags': ['math'],
      });

      expect(node.id, 'node-uuid-1', reason: 'gRPC node_id 必须映射到 id');
      expect(node.name, '离散数学', reason: 'gRPC label 必须映射到 name');
      expect(node.masteryScore, 40);
    });

    test('REST shape still wins when both keys present (no regression)', () {
      final node = GalaxyNodeModel.fromJson({
        'id': 'rest-id',
        'node_id': 'grpc-id',
        'name': 'REST名',
        'label': 'gRPC名',
        'importance_level': 3,
        'sector_code': 'TECH',
        'mastery_score': 55,
      });

      expect(node.id, 'rest-id');
      expect(node.name, 'REST名');
      expect(node.importance, 3);
      expect(node.masteryScore, 55);
    });

    test('gRPC edge payload maps relation alias', () {
      final edge = GalaxyEdgeModel.fromJson({
        'source_id': 'a',
        'target_id': 'b',
        'relation': 'parent',
      });

      expect(edge.sourceId, 'a');
      expect(edge.targetId, 'b');
      expect(edge.relationType, EdgeRelationType.parentChild);
    });

    test('gRPC graph payload yields renderable nodes (screen sanitize safe)',
        () {
      final graph = GalaxyGraphResponse.fromJson(_grpcGraphPayload());
      expect(graph.nodes, hasLength(3));
      expect(graph.nodes.every((n) => n.id.isNotEmpty && n.name.isNotEmpty),
          isTrue,
          reason: '全部节点必须可渲染，否则星图会被判定为空宇宙',);
    });
  });

  group('EnhancedGalaxyRepository.getGraph contract guard', () {
    test('gRPC-shaped success returns usable nodes', () async {
      final repo = EnhancedGalaxyRepository(
        _FakeApiClient(_grpcGraphPayload()),
      );

      final result = await repo.getGraph();

      expect(result.isFailure, isFalse);
      final nodes = result.data?.nodes ?? const <GalaxyNodeModel>[];
      expect(nodes, hasLength(3));
      expect(nodes.every((n) => n.id.isNotEmpty && n.name.isNotEmpty), isTrue);
    });

    test(
      'payload declaring nodes but parsing unusable must fail AND not be cached',
      () async {
        final client = _FakeApiClient({
          'nodes': [
            {'foo': 'bar'},
            {'foo': 'baz'},
          ],
          'edges': <dynamic>[],
          'total_nodes': 147,
          'via': 'grpc',
        });
        final repo = EnhancedGalaxyRepository(client);

        final first = await repo.getGraph();
        expect(first.isFailure, isTrue,
            reason: '声明了节点却解析出 0 个可用节点属于契约破坏，'
                '不得当作"空星图成功"吞掉（V24 的直接死因）',);

        // 第二次调用必须真实发出（断言 client.getCalls == 2），仅绑定会被丢弃
        await repo.getGraph();
        expect(client.getCalls, 2,
            reason: '坏载荷不得进入 _graphCache，否则 10 分钟内所有非 force 刷新'
                '都会复用同一空图（会话内不可自愈的根因）',);
      },
    );

    test('genuine empty universe (no nodes declared) stays a success', () async {
      final client = _FakeApiClient({
        'nodes': <dynamic>[],
        'edges': <dynamic>[],
        'total_nodes': 0,
      });
      final repo = EnhancedGalaxyRepository(client);

      final result = await repo.getGraph();

      expect(result.isFailure, isFalse, reason: '真·空星图是合法成功响应');
      expect(result.data?.nodes, isEmpty);
    });
  });
}

/// gateway GetGraph gRPC 优先路径的实际返回形状
///（proto GalaxyNode/Edge 的 Go json tag 序列化 + total_nodes/via 包装）。
Map<String, dynamic> _grpcGraphPayload() => {
      'nodes': [
        {
          'node_id': 'n1',
          'label': '离散数学',
          'node_type': 'concept',
          'mastery': 40,
          'tags': <String>['math'],
        },
        {
          'node_id': 'n2',
          'label': '高等数学',
          'node_type': 'concept',
          'mastery': 60,
          'tags': <String>[],
        },
        {
          'node_id': 'n3',
          'label': 'TCP 系列',
          'node_type': 'topic',
          'mastery': 0,
          'tags': <String>[],
        },
      ],
      'edges': [
        {'source_id': 'n1', 'target_id': 'n2', 'relation': 'related'},
        {'source_id': 'n1', 'target_id': 'n3', 'relation': 'parent'},
      ],
      'total_nodes': 147,
      'via': 'grpc',
    };

class _FakeApiClient implements ApiClient {
  _FakeApiClient(this.payload);

  final Map<String, dynamic> payload;
  int getCalls = 0;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    getCalls += 1;
    return Response<T>(
      requestOptions: RequestOptions(path: path, queryParameters: queryParameters),
      data: payload as T,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    // post/put/patch/delete/getStream/postStream/dio 在 getGraph 路径不会被触达。
    throw UnimplementedError('${invocation.memberName} not stubbed');
  }
}
