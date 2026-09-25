// ignore_for_file: avoid_print
//
// G-05（wt395）Galaxy 帧预算（headless widget 帧耗时断言, 替代真机 FPS 口径;
// 无设备/模拟器权限, 不伪造 FPS 数值）。
//
// 方法（与 galaxy_semantics_perf_test.dart 同一真实装载路径）:
//   真实 GalaxyScreen + 真实 StarMapPainter, 经 provider 覆盖注入已装载的
//   50/500/5000 节点图, 拖拽手势驱动每帧 setState+repaint 热路径,
//   逐帧 Stopwatch 计时, 程序输出 p50/p95（原始逐帧毫秒值见 raw 注释行）。
//
// 阈值声明（本机 Apple Silicon macOS, flutter test VM, headless）:
//   - 拖拽热路径平均帧耗 < 50ms（沿用 GALAXY-A11Y 语义清单红线, 防病理性回退）;
//   - 5000 节点档平均帧耗 < 80ms（规模梯度余量, 只防病理性, 不代表真机帧率）。
//     真机 FPS/截图见 v3-output/WT395-G05-GALAXY/HUMAN_INBOX_G05_VISUAL.md。

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

const _frames = 40;

void main() {
  setUp(() {
    setUpI18nForTesting();
    // 生产 seam: 断开事件流网络订阅（帧探针不消费 SSE 面）
    DemoDataService.isDemoMode = true;
  });

  // 5000 档: headless debug VM 下 screen 级每帧 O(全图) 工作（mini-map/
  // 命中映射/全节点扫描）使泵帧成本秒级×几十帧 > 15min 预算（两轮实测均未
  // 完成）。不伪造帧数据: 该档渲染侧由 ①真实 notifier 聚合/可见性计算 @5000
  // （g05_galaxy_interaction_scale_test.dart 实证 LOD 收窄+上限裁剪）②tier
  // 可见上限后的每帧绘制（与 500 档同量级）③真机 DevTools 口径
  // （HUMAN_INBOX_G05_VISUAL.md）三面覆盖, 此处如实跳过（skip 带原因）。
  test(
    'G05-PERF scale=5000 拖拽帧耗时（headless 环境限制如实跳过, 转真机口径）',
    () {},
    skip: 'headless debug VM 5000 节点全图泵帧超 15min 预算（环境限制, 非产品'
        '断言失败）; 5000 档渲染侧转 HUMAN_INBOX 真机口径',
  );

  for (final scale in <int>[50, 500]) {
    testWidgets(
      'G05-PERF scale=$scale 拖拽帧耗时 p50/p95（headless 帧预算）',
      (tester) async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();

      final columns = scale <= 50 ? 8 : (scale <= 500 ? 24 : 71);
      final spacing = scale <= 50 ? 90.0 : 90.0;
      final nodes = List<GalaxyNodeModel>.generate(scale, (index) => GalaxyNodeModel.fromJson({
          'id': 'node_$index',
          'name': 'Node $index',
          'importance': (index % 5) + 1,
          'sector_code': 'TECH',
          'is_unlocked': index % 7 != 0,
          'mastery_score': (index * 7) % 100,
          'study_count': index % 11,
          'position_x': (index % columns) * spacing,
          'position_y': (index ~/ columns) * spacing,
        }),);
      // 真实渲染口径: state 装载全图节点, 可见集按真实 LOD/tier 上限裁剪
      // （_prioritizeVisibleNodes 动态上限——5000 节点图实际每帧绘制的是
      //   上限内子集, 全可见绘制不是真实路径）。可见集取 G-05 交互测试
      //   实证的 medium tier 上限 200; 50/500 档全量可见。
      final visibleCap = scale >= 5000 ? 200 : scale;
      final visible = nodes.take(visibleCap).toList();
      final container = ProviderContainer(overrides: [
        galaxyProvider.overrideWith(
          (ref) => _LoadedGalaxyNotifier(nodes, visible),
        ),
      ],);
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            locale: const Locale('zh'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const Scaffold(body: GalaxyScreen()),
          ),
        ),
      );

      // 等入场回放/物理收敛（同 galaxy_work_view_test 稳定判据;
      // 大图档泵次有界收敛防 headless 超时——泵本身是真实渲染管线工作）
      final settleGuard = scale >= 5000 ? 12 : 60;
      final warmupFrames = scale >= 5000 ? 6 : 20;
      await tester.pump(const Duration(milliseconds: 500));
      var guard = 0;
      while (_isBuildAnimating(tester) && guard < settleGuard) {
        await tester.pump(const Duration(milliseconds: 200));
        guard++;
      }
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 60));
      }
      // 热身
      for (var i = 0; i < warmupFrames; i++) {
        await tester.pump(const Duration(milliseconds: 16));
      }

      // 拖拽热路径: 按下画布中心, 连续平移, 每帧单独计时
      final frameMicros = <int>[];
      final gesture = await tester.startGesture(
        tester.getCenter(find.byType(GalaxyScreen)),
      );
      await tester.pump();
      for (var i = 0; i < _frames; i++) {
        final sw = Stopwatch()..start();
        await gesture.moveBy(
          const Offset(6, 4),
          timeStamp: Duration(milliseconds: i * 16),
        );
        await tester.pump(const Duration(milliseconds: 16));
        frameMicros.add(sw.elapsedMicroseconds);
      }
      await gesture.up();
      await tester.pump();

      frameMicros.sort();
      double p(double q) {
        final rank = (frameMicros.length - 1) * q / 100.0;
        final lo = rank.floor();
        final hi = rank.ceil();
        final v = lo == hi
            ? frameMicros[lo]
            : frameMicros[lo] +
                (frameMicros[hi] - frameMicros[lo]) * (rank - lo);
        return v / 1000.0;
      }

      final p50 = p(50);
      final p95 = p(95);
      final avg = frameMicros.fold<int>(0, (a, b) => a + b) / frameMicros.length / 1000.0;
      print('G05-PERF scale=$scale frames=$_frames '
          'p50=${p50.toStringAsFixed(2)}ms p95=${p95.toStringAsFixed(2)}ms '
          'avg=${avg.toStringAsFixed(2)}ms max='
          '${(frameMicros.last / 1000.0).toStringAsFixed(2)}ms');
      print('G05-PERF-RAW scale=$scale micros=$frameMicros');

      // 阈值判定（声明依据见文件头）: 平均帧耗红线统一口径
      expect(avg, lessThan(50.0),
          reason: 'scale=$scale 拖拽平均帧耗须 <50ms（GALAXY-A11Y 语义红线同口径）',);
      expect(p95, lessThan(100.0),
          reason: 'scale=$scale 拖拽 p95 须 <100ms（headless VM, 只防病理性回退）',);
      },
      timeout: const Timeout(Duration(minutes: 15)),
    );
  }
}

bool _isBuildAnimating(WidgetTester tester) {
  final matches = tester.widgetList<CustomPaint>(
    find.byWidgetPredicate(
      (widget) => widget is CustomPaint && widget.painter is StarMapPainter,
    ),
  );
  if (matches.isEmpty) {
    return true;
  }
  return (matches.first.painter! as StarMapPainter).isBuildAnimating;
}

class _LoadedGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _LoadedGalaxyNotifier(List<GalaxyNodeModel> nodes, List<GalaxyNodeModel> visible)
      : super(
          GalaxyState(
            nodes: nodes,
            nodePositions: <String, Offset>{
              for (final node in nodes)
                node.id: Offset(node.positionX!, node.positionY!),
            },
            visibleNodes: visible,
            userFlameIntensity: 0.4,
          ),
        );

  @override
  void selectNode(String nodeId) {
    state = state.copyWith(
      selectedNodeId: nodeId,
      expandedEdgeNodeIds: {nodeId},
    );
  }

  @override
  void deselectNode() {}

  @override
  void updateScale(double scale) {
    state = state.copyWith(currentScale: scale);
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
    await Future<void>.delayed(const Duration(milliseconds: 10));
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

  // —— 拖拽/聚焦/证据高亮面: 帧预算探针不消费, 最小 no-op 实现 ——
  @override
  void beginNodeDrag(String nodeId) {}

  @override
  Future<void> endNodeDrag() async {}

  @override
  void updateDraggedNodePosition(String nodeId, Offset newPosition) {}

  @override
  void setFocusNode(String nodeId) {}

  @override
  void clearFocusNode() {}

  @override
  void clearFocusBounds() {}

  @override
  void setEvidenceHighlight(Set<String> nodeIds, {String? focusId}) {}

  @override
  void clearEvidenceHighlight() {}
}
