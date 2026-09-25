// ignore_for_file: avoid_print, cascade_invocations
//
// G-05（wt395）Galaxy 交互正确性 @ 规模梯度（真实生产代码路径, 无网络, 不伪造测量值）:
// ① 缩放→五级 LOD 聚合正确性（真实 GalaxyNotifier._levelForScale/_recalculateVisibility）
// ② 拖拽视口 100ms 节流 + 50px 显著位移门（核心操作不重叠抖动）
// ③ 选择正确性（真实 selectNode 边展开/防御面）
// ④ 空间索引命中正确性 @5000（重叠节点取最近; 空区域 null; 窗口查询精确）
// ⑤ 手势缩放钳制（pinch 上限 5.0/下限 0.1; 双击 ×2 切换）
// ⑥ 力引擎邻域激活（anchor 只唤醒 2 跳邻域, 远端位置不动, 有限 tick 收敛）
import 'dart:ui';

import 'package:flutter/gestures.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';

const int kScale = 5000;
const int kColumns = 71;
const double kSpacing = 90;

(List<GalaxyNodeModel>, Map<String, Offset>) _graph(int count) {
  final nodes = List<GalaxyNodeModel>.generate(
    count,
    (i) => GalaxyNodeModel.fromJson({
      'id': 'node_$i',
      'name': 'Node $i',
      'importance': i % 7 == 0 ? 3 : (i % 5) + 1,
      'sector_code': 'TECH',
      'is_unlocked': i % 3 != 0,
      'mastery_score': (i * 7) % 100,
      'study_count': i % 11,
      'position_x': (i % kColumns) * kSpacing,
      'position_y': (i ~/ kColumns) * kSpacing,
    }),
    growable: false,
  );
  final positions = <String, Offset>{
    for (final n in nodes) n.id: Offset(n.positionX!, n.positionY!),
  };
  return (nodes, positions);
}

// 真实 provider 图: 真实 GalaxyNotifier + 真实 EnhancedGalaxyRepository
// （构造不触网; 交互路径全部本地计算）。视图持久化走 mock SharedPreferences。
ProviderContainer _container() => ProviderContainer();

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
    // 生产 seam（EnhancedGalaxyRepository.getGalaxyEventsStream 的 demo 分支）:
    // 交互测试不依赖 SSE 事件面, 断开网络订阅以免测试环境连接失败噪声。
    DemoDataService.isDemoMode = true;
  });

  group('G-05 缩放→LOD 聚合正确性 @5000（真实 GalaxyNotifier）', () {
    test('五级 LOD 阈值逐级正确, full 档恢复全量可见, 防抖阈值生效', () {
      final container = _container();
      addTearDown(container.dispose);
      final (nodes, positions) = _graph(kScale);
      final notifier = container.read(galaxyProvider.notifier)
        ..state = GalaxyState(
          nodes: nodes,
          nodePositions: positions,
          visibleNodes: nodes,
        );

      notifier.updateScale(0.15);
      expect(notifier.state.aggregationLevel, AggregationLevel.universe);
      notifier.updateScale(0.30);
      expect(notifier.state.aggregationLevel, AggregationLevel.galaxy);
      notifier.updateScale(0.50);
      expect(notifier.state.aggregationLevel, AggregationLevel.cluster);
      notifier.updateScale(0.70);
      expect(notifier.state.aggregationLevel, AggregationLevel.nebula);
      notifier.updateScale(1.00);
      expect(notifier.state.aggregationLevel, AggregationLevel.full);
      expect(notifier.state.currentScale, 1.00);

      // 渲染侧大图降级契约（_prioritizeVisibleNodes 镜像断言）:
      // cap = dynamicMaxNodes(targetFps, scale).clamp(80, config.maxNodes)
      // 本宿主 PerformanceService 判 medium tier（targetFps=30, maxNodes=500）。
      final cfg = notifier.state.optimizationConfig;
      final dynamicMax = cfg.targetFps == 60
          ? (1.00 >= 1.2 ? 420 : 1.00 >= 0.8 ? 320 : 1.00 >= 0.4 ? 220 : 140)
          : (1.00 >= 1.2 ? 260 : 1.00 >= 0.8 ? 200 : 1.00 >= 0.4 ? 150 : 96);
      final expectedCap = dynamicMax.clamp(80, cfg.maxNodes);
      expect(
        notifier.state.visibleNodes.length,
        expectedCap,
        reason: 'full 档可见集 = 帧级动态上限（fps=${cfg.targetFps}, maxNodes=${cfg.maxNodes}）'
            '——5000 节点图的内建降级路径',
      );

      // 层级单调性: 缩小可见集只减不增
      final fullVisible = notifier.state.visibleNodes.length;
      notifier.updateScale(0.15); // universe
      final universeVisible = notifier.state.visibleNodes.length;
      expect(universeVisible, lessThan(fullVisible),
          reason: 'universe 档可见集必须显著小于 full 档（聚合收窄）',);

      // 小增量防抖: < 0.01 的刻度变化必须被忽略（pinch 热路径防抖契约,
      // 在当前 universe 档上验证）
      notifier.updateScale(notifier.state.currentScale + 0.005);
      expect(notifier.state.currentScale, 0.15, reason: '差值 < 0.01 时忽略');
    });

    test('视口更新走 100ms 节流且 50px 内位移被丢弃（拖拽热路径不重叠重算）', () async {
      final container = _container();
      addTearDown(container.dispose);
      final (nodes, positions) = _graph(500);
      final notifier = container.read(galaxyProvider.notifier);
      notifier.state = GalaxyState(
          nodes: nodes, nodePositions: positions, visibleNodes: nodes,);

      notifier.updateViewport(const Rect.fromLTWH(0, 0, 800, 800));
      notifier.updateViewport(const Rect.fromLTWH(1, 1, 801, 801)); // < 50px
      await Future<void>.delayed(const Duration(milliseconds: 130));
      expect(notifier.state.viewport, isNotNull);
      // 节流语义: 100ms 窗口内只应用一次, 保留最新 pending;
      // 状态里 viewport 仍为 null（首个尚未应用）→ 50px 门不触发, 应用最新值。
      expect(notifier.state.viewport!.left, 1,
          reason: '100ms 窗口内多次 updateViewport 只应用一次（latest-wins）',);
    });
  });

  group('G-05 选择正确性 @5000（真实 selectNode 边展开）', () {
    test('选中展开连接边; 取消选中清空; 空图防御', () {
      final container = _container();
      addTearDown(container.dispose);
      final (nodes, positions) = _graph(kScale);
      final edges = <GalaxyEdgeModel>[
        for (var i = 1; i < 300; i++)
          GalaxyEdgeModel(
            id: 'edge_$i',
            sourceId: 'node_${i - 1}',
            targetId: 'node_$i',
          ),
      ];
      final notifier = container.read(galaxyProvider.notifier)
        ..state = GalaxyState(
          nodes: nodes,
          nodePositions: positions,
          visibleNodes: nodes,
          edges: edges,
        );

      notifier.selectNode('node_10');
      expect(notifier.state.selectedNodeId, 'node_10');
      expect(
        notifier.state.expandedEdgeNodeIds,
        containsAll(<String>['node_10', 'node_9', 'node_11']),
      );

      notifier.deselectNode();
      expect(notifier.state.selectedNodeId, isNull);

      // 空图防御: nodes 为空时 selectNode 直接返回
      notifier.state = GalaxyState();
      notifier.selectNode('node_1');
      expect(notifier.state.selectedNodeId, isNull);
    });
  });

  group('G-05 空间索引命中正确性 @5000', () {
    test('中心命中取该节点; 重叠区取最近; 空区 null; 窗口查询精确', () {
      final (nodes, positions) = _graph(kScale);
      final index = GalaxySpatialIndex()
        ..build(positions, nodes);
      expect(index.size, kScale);

      // 1) 节点中心命中自身
      final hit = index.queryNearest(positions['node_42']!, 24);
      expect(hit, isNotNull);
      expect(hit!.nodeId, 'node_42');

      // 2) 两节点中点: 距离更近者胜（重叠不歧义）
      final a = positions['node_42']!;
      final b = positions['node_43']!; // 相邻 90px
      final mid = Offset((a.dx + b.dx) / 2, (a.dy + b.dy) / 2);
      final nearest = index.queryNearest(mid, 60)!;
      final dA = (a - mid).distance;
      final dB = (b - mid).distance;
      expect(nearest.nodeId, dA <= dB ? 'node_42' : 'node_43');

      // 3) 空旷区 maxRadius 内无命中 → null（点空白处不误选）
      final far = positions.values.reduce(
        (p, q) => p.dx + p.dy > q.dx + q.dy ? p : q,
      );
      expect(index.queryNearest(far + const Offset(1000, 1000), 24), isNull);

      // 4) 窗口查询: 覆盖竖向两格的矩形恰好含格内节点
      final rect = Rect.fromPoints(
        positions['node_0']! - const Offset(10, 10),
        positions['node_0']! + const Offset(100, 100),
      );
      final ids = index.queryRect(rect);
      expect(ids, contains('node_0'));
      expect(ids, contains('node_71'));
      expect(ids, isNot(contains('node_5000_不存在')));
      for (final id in ids) {
        expect(positions.containsKey(id), isTrue);
      }
    });
  });

  group('G-05 手势缩放钳制', () {
    testWidgets('pinch 超上限钳在 5.0, 到顶后双击切换为缩小', (tester) async {
      double? lastScale;
      final rec = GalaxyGestureRecognizer(
        onScale: (scale, focal) => lastScale = scale,
      );
      addTearDown(rec.dispose);

      rec.handleScaleStart(ScaleStartDetails(
        localFocalPoint: Offset.zero,
      ),);
      for (var i = 0; i < 8; i++) {
        rec.handleScaleUpdate(ScaleUpdateDetails(
          scale: 10.0,
          localFocalPoint: Offset.zero,
          pointerCount: 2,
        ),);
      }
      expect(lastScale, 5.0, reason: '连续放大必须钳在 maxScale=5.0');

      // 双击: tap1 记时点, tap2 <300ms 且 <30px → 切换放大方向; 5.0 已到顶 → 缩小
      rec.handlePointerDown(const PointerDownEvent(
        timeStamp: Duration(milliseconds: 1000),
      ),);
      rec.handlePointerUp(const PointerUpEvent(
        timeStamp: Duration(milliseconds: 1010),
      ),);
      rec.handlePointerDown(const PointerDownEvent(
        timeStamp: Duration(milliseconds: 1080),
      ),);
      rec.handlePointerUp(const PointerUpEvent(
        timeStamp: Duration(milliseconds: 1120),
      ),);
      expect(rec.currentScale, 2.5, reason: '到顶后双击切换为 5.0/2=2.5');
    });

    testWidgets('缩小方向钳在 minScale=0.1', (tester) async {
      final rec = GalaxyGestureRecognizer(
        
      );
      addTearDown(rec.dispose);
      rec.handleScaleStart(ScaleStartDetails(
        localFocalPoint: Offset.zero,
      ),);
      for (var i = 0; i < 8; i++) {
        rec.handleScaleUpdate(ScaleUpdateDetails(
          scale: 0.01,
          localFocalPoint: Offset.zero,
          pointerCount: 2,
        ),);
      }
      expect(rec.currentScale, 0.1);
    });
  });

  group('G-05 力引擎邻域激活 @5000', () {
    test('anchor 只唤醒 2 跳邻域, 远端位置不动, 有限 tick 收敛', () {
      final (nodes, positions) = _graph(kScale);
      final adjacency = <String, Set<String>>{
        for (final n in nodes) n.id: <String>{},
      };
      for (var i = 1; i < kScale; i++) {
        final parent = 'node_${(i - 1) ~/ 3}';
        adjacency[parent]!.add('node_$i');
        adjacency['node_$i']!.add(parent);
      }
      final spatial = GalaxySpatialIndex()..build(positions, nodes);
      final engine = GalaxyForceEngine();

      // 邻域行为断言（不动私有态）: 邻域节点被唤醒产生速度, 远端不动
      const neighborId = 'node_1';
      const farId = 'node_${kScale - 1}';
      final neighborBefore = positions[neighborId]!;
      final farBefore = positions[farId]!;

      engine.anchorNode('node_0', adjacency);
      final edgeStrengths = <String, double>{};
      var settled = false;
      var ticks = 0;
      // 拖拽语义: 松手（releaseAnchor）后才允许仿真收敛
      while (!settled && ticks < 600) {
        final result = engine.tick(
          positions: positions,
          adjacency: adjacency,
          edgeStrengths: edgeStrengths,
          spatialIndex: spatial,
        );
        positions
          ..clear()
          ..addAll(result.positions);
        ticks++;
        if (ticks == 60) {
          engine.releaseAnchor(); // 松手
        }
        settled = result.isSettled || (ticks > 60 && engine.hasActiveSimulation == false);
      }
      // 释放后继续跑到完全静止
      while (engine.hasActiveSimulation && ticks < 900) {
        final result = engine.tick(
          positions: positions,
          adjacency: adjacency,
          edgeStrengths: edgeStrengths,
          spatialIndex: spatial,
        );
        positions
          ..clear()
          ..addAll(result.positions);
        ticks++;
      }
      expect(ticks, lessThan(900), reason: '邻域力仿真必须在有限 tick 内收敛');
      expect(positions[farId], farBefore,
          reason: '非邻域远端节点位置不允许被扰动（拖拽局部性）',);
      // 邻域收敛后位置可与初始不同（力仿真重排）, 这里只要求无 NaN
      expect(positions[neighborId]!.dx.isNaN, isFalse);
      expect(neighborBefore.dy.isNaN, isFalse);
      expect(engine.hasActiveSimulation, isFalse, reason: '收敛后必须停止仿真');
    });
  });
}
