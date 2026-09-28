// V4-F06 · 星图连接文本列表 + reduce-motion 入场静态分支 + 200% 文本缩放
// （galaxy 模块面：验收②「星图列表替代」扩展 + 验收③）。
//
// 每验收面一正一反：
//   G+（验收②/资产合同「连接有文本列表」）：带边图的节点语义标签尾含
//      「，连接：…」——CustomPaint 连线零语义（R06），连接经节点条目
//      线性可读；G-：无边图不造连接子句（V3 标签字节不变）；
//   H+（验收③ reduce-motion）：disableAnimations 下入场直落终态
//      （入场模糊 sigma=0）/ H-：常规路径首帧模糊在航（探针活性）；
//   I+（验收③ 200%）：200% 文本 + 减弱动效整屏零异常、画布摘要与节点
//      语义存活 / I-：无。
import 'dart:io' as io;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show RenderSemanticsAnnotations;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

void main() {
  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  Future<ProviderContainer> pumpGalaxy(
    WidgetTester tester, {
    required List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges = const [],
    TextScaler? textScaler,
    bool disableAnimations = false,
    GlobalKey? repaintKey,
  }) async {
    final container = ProviderContainer(
      overrides: [
        galaxyProvider.overrideWith(
          (ref) => _LoadedGalaxyNotifier(nodes, edges),
        ),
      ],
    );
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: AppThemes.lightTheme,
          // 断言走中文语义文案，显式锁 zh（test 默认 en_US）。
          locale: const Locale('zh'),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: textScaler,
              disableAnimations: disableAnimations,
            ),
            child: child ?? const SizedBox.shrink(),
          ),
          home: RepaintBoundary(
            key: repaintKey,
            child: const Scaffold(body: GalaxyScreen()),
          ),
        ),
      ),
    );
    await tester.pump();
    // 生产时序：首帧布局（viewport 落定）→ init _loadGraph → 10ms 后图
    // 到达 → apply → 入场分支执行。冲刷装载链与入场首帧。
    await tester.pump(const Duration(milliseconds: 60));
    await tester.pump();
    return container;
  }

  /// 证据落盘（GALAXY_A11Y_EVIDENCE_DIR 设置时）：整屏 PNG + 语义树 dump
  /// （元素树口径，与 F04 shell_evidence_test 同源）。常规跑不写文件。
  Future<void> dumpEvidence(
    WidgetTester tester,
    GlobalKey repaintKey,
    String variant,
  ) async {
    final dir = io.Platform.environment['GALAXY_A11Y_EVIDENCE_DIR'];
    if (dir == null || dir.isEmpty) {
      return;
    }
    await tester.pump();
    // 纯同步语义树 dump（元素树口径，与 F04 shell_evidence_test 同源）。
    // 故不做 runAsync/toImage PNG 面——真实异步窗会拉入 auth/网络插件链；
    // PNG 证据面由像素故事页证据测试承担，本处承载连接子句语义文本。
    final rootElement = tester.binding.rootElement;
    final buf = StringBuffer();
    void visit(Element el, int depth) {
      final ro = el.renderObject;
      final indent = '  ' * depth;
      if (ro is RenderSemanticsAnnotations) {
        var isButton = false;
        try {
          isButton = (ro as dynamic).button as bool? ?? false;
        } on NoSuchMethodError {
          isButton = false;
        }
        buf.writeln(
          '$indent- label="${ro.properties.label}" isButton=$isButton',
        );
        depth += 1;
      }
      el.visitChildElements((child) => visit(child, depth));
    }

    final root = rootElement;
    if (root != null) {
      visit(root, 0);
    }
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) outDir.createSync(recursive: true);
    io.File('$dir/galaxy_edge_list_${variant}_semantics.txt')
        .writeAsStringSync(buf.toString());
  }

  /// 入场进度（galaxy_screen 入场 AnimatedBuilder 绑定的 620ms 控制器值；
  /// 0=入场起点，1=静态终态——reduce-motion 分支直落 1.0）。
  double? entranceProgress(WidgetTester tester) {
    final candidates = tester
        .widgetList<AnimatedBuilder>(find.byType(AnimatedBuilder))
        .where(
          (ab) =>
              ab.animation is AnimationController &&
              (ab.animation as AnimationController).duration ==
                  const Duration(milliseconds: 620),
        )
        .toList();
    if (candidates.isEmpty) return null;
    return (candidates.single.animation as AnimationController).value;
  }

  group('验收② · 星图连接文本列表（ACCESSIBILITY_ASSETS「连接有文本列表」）', () {
    testWidgets('G+：带边图的节点标签含连接子句（连接线性可读）', (tester) async {
      final semantics = tester.ensureSemantics();
      final repaintKey = GlobalKey();
      final container = await pumpGalaxy(
        tester,
        nodes: _nodes(),
        edges: const [
          GalaxyEdgeModel(id: 'edge_0', sourceId: 'node_0', targetId: 'node_1'),
          GalaxyEdgeModel(id: 'edge_1', sourceId: 'node_1', targetId: 'node_2'),
        ],
        repaintKey: repaintKey,
      );

      // Node 0 ↔ Node 1（双向展开）：Node 0 的标签读出「连接：Node 1」。
      expect(
        find.bySemanticsLabel(
          RegExp('科技 Node 0（已解锁，掌握度 42 分，已学习 3 次，重要度.+）?，连接：Node 1'),
        ),
        findsOneWidget,
        reason: '节点 Node 0 的读屏标签必须含连接子句「，连接：Node 1」',
      );
      // Node 1 连接两个端（去重、按图序）。
      expect(
        find.bySemanticsLabel(RegExp('连接：Node 0、Node 2')),
        findsOneWidget,
        reason: 'Node 1 的连接子句须按图序列出两个邻接且去重',
      );
      // 画布摘要语义仍在（容器级口径不被连接子句破坏）。
      expect(
        find.bySemanticsLabel('知识星图：3 个知识点，覆盖 2 个领域'),
        findsOneWidget,
      );
      await dumpEvidence(tester, repaintKey, 'connected');
      container.dispose();
      semantics.dispose();
    });

    testWidgets('G-：无边图不造连接子句（V3 既有标签口径字节不变）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      final container = await pumpGalaxy(tester, nodes: _nodes());

      // 三个节点的完整标签都不含连接子句（空邻接不追加、不造默认值）。
      for (final name in const ['Node 0', 'Node 1', 'Node 2']) {
        final node = tester.getSemantics(
          find.bySemanticsLabel(RegExp('Node 0'.replaceFirst('Node 0', name))),
        );
        expect(
          node.getSemanticsData().label.contains('，连接：'),
          isFalse,
          reason: '无边图 $name 不得出现连接子句（连接文本列表只由真实边驱动）',
        );
      }
      // V3 标签形态完好：解锁态标签仍以重要度右括号收尾（字节不变口径）。
      final node0 = tester.getSemantics(
        find.bySemanticsLabel(
          RegExp(RegExp.escape('科技 Node 0（已解锁，掌握度 42 分')),
        ),
      );
      expect(
        node0.getSemanticsData().label,
        '科技 Node 0（已解锁，掌握度 42 分，已学习 3 次，重要度基础）',
        reason: '无边图标签须与 V3 既有口径逐字相等',
      );
      container.dispose();
      semantics.dispose();
    });
  });

  group('验收③ · galaxy 入场 reduce-motion 静态分支与 200% 文本', () {
    testWidgets('H+：disableAnimations 下入场直落终态（模糊 sigma=0）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      final container = await pumpGalaxy(
        tester,
        nodes: _nodes(),
        disableAnimations: true,
      );

      final progress = entranceProgress(tester);
      expect(progress, isNotNull, reason: '入场控制器应在树');
      expect(
        progress,
        1.0,
        reason: '减弱动效下入场进度必须直落终态 1.0（模糊 sigma=0、不透明度 1，无 620ms 运动）',
      );
      expect(tester.takeException(), isNull);
      container.dispose();
      semantics.dispose();
    });

    testWidgets('H-：常规路径入场首帧模糊在航（探针活性）', (tester) async {
      final semantics = tester.ensureSemantics();
      final container = await pumpGalaxy(tester, nodes: _nodes());

      final progress = entranceProgress(tester);
      expect(progress, isNotNull);
      expect(
        progress,
        lessThan(1.0),
        reason: '常规路径首帧入场必须在航（否则 H+ 的终态断言无判别力）',
      );
      container.dispose();
      semantics.dispose();
    });

    testWidgets('I+：200% 文本 + 减弱动效整屏零异常，摘要与节点语义存活',
        (tester) async {
      final semantics = tester.ensureSemantics();
      final container = await pumpGalaxy(
        tester,
        nodes: _nodes(),
        edges: const [
          GalaxyEdgeModel(id: 'edge_0', sourceId: 'node_0', targetId: 'node_1'),
        ],
        textScaler: const TextScaler.linear(2.0),
        disableAnimations: true,
      );

      expect(
        tester.takeException(),
        isNull,
        reason: '200% 文本 + 减弱动效不得在星图屏产生布局异常（零 duration 崩溃面）',
      );
      expect(
        find.bySemanticsLabel('知识星图：3 个知识点，覆盖 2 个领域'),
        findsOneWidget,
        reason: '200% 下画布摘要语义必须在场',
      );
      expect(
        find.bySemanticsLabel(RegExp(RegExp.escape('科技 Node 0（已解锁'))),
        findsOneWidget,
        reason: '200% 下节点语义条目必须在场',
      );
      container.dispose();
      semantics.dispose();
    });
  });
}

/// 双领域节点：Node 0/Node 1 解锁（TECH）+ Node 2 锁定（ART）。
List<GalaxyNodeModel> _nodes() => [
      GalaxyNodeModel.fromJson(const {
        'id': 'node_0',
        'name': 'Node 0',
        'importance': 2,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 42,
        'study_count': 3,
        'position_x': 0.0,
        'position_y': 0.0,
      }),
      GalaxyNodeModel.fromJson(const {
        'id': 'node_1',
        'name': 'Node 1',
        'importance': 4,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 87,
        'study_count': 9,
        'position_x': 120.0,
        'position_y': 0.0,
      }),
      GalaxyNodeModel.fromJson(const {
        'id': 'node_2',
        'name': 'Node 2',
        'importance': 3,
        'sector_code': 'ART',
        'is_unlocked': false,
        'mastery_score': 0,
        'position_x': 0.0,
        'position_y': 120.0,
      }),
    ];

class _LoadedGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _LoadedGalaxyNotifier(this._nodes, this._edges)
      // 生产时序镜像：初始为装载中空图（图异步到达），星图屏首帧先完成
      // 布局（viewport 落定），图经 loadGalaxy 完成后才 apply——入场路径
      // 在真实 viewport 下执行（而非首帧 viewport=0 的早退分支）。
      : super(
          GalaxyState(
            userFlameIntensity: 0.4,
            isLoading: true,
          ),
        );

  final List<GalaxyNodeModel> _nodes;
  final List<GalaxyEdgeModel> _edges;

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
    state = GalaxyState(
      nodes: _nodes,
      edges: _edges,
      nodePositions: <String, Offset>{
        for (final node in _nodes)
          if (node.positionX != null && node.positionY != null)
            node.id: Offset(node.positionX!, node.positionY!),
      },
      visibleNodes: _nodes,
      userFlameIntensity: 0.4,
    );
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
    state = state.copyWith(draggingNodeId: nodeId);
  }

  @override
  void updateDraggedNodePosition(String nodeId, Offset newPosition) {
    state = state.copyWith(nodePositions: Map<String, Offset>.from(state.nodePositions)
      ..[nodeId] = newPosition,);
  }

  @override
  Future<void> endNodeDrag() async {}

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
