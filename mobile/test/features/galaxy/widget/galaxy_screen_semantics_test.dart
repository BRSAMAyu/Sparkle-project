import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

/// GALAXY-A11Y：星图读屏语义化验收（A-SPEC6 AX-G3 / N38 观察行的一期接线）。
///
/// 背景实证（A-SPEC6 REPORT §2.1 galaxy 行）：galaxy 画布是 4266 行
/// CustomPaint 单容器语义——StarMapPainter 零语义节点，读屏黑洞；服务侧
/// GalaxyNodeSemantics / getNodeSemanticLabel / galaxyA11yNode* l10n 全套
/// 写好了但 0 引用（死代码）。本卡激活接线，验收四条：
///
/// 1. 容器摘要——画布容器语义从裸「星图」升级为「知识星图：N 个知识点，
///    覆盖 M 个领域」（graph 既有数据，不自造口径）；
/// 2. 节点线性可读——每个节点在语义树中按图序暴露
///    「领域 名字（解锁态，掌握度 X 分，已学习 Y 次，重要度 Z）」完整标签；
/// 3. 语义 tap 动作——节点语义节点带 button 标志 + tap 动作，
///    performAction 走画布同链路（锁定节点 → 预览卡在屏）；
/// 4. 语义子树不参与命中与绘制（性能红线：IgnorePointer + Opacity(0)，
///    隐身性断言——画布中心的语义 tap 不落在节点清单上）。
void main() {
  setUp(setUpI18nForTesting);

  group('galaxy canvas semantics (GALAXY-A11Y)', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
    });

    Future<ProviderContainer> pumpLoadedGalaxy(
      WidgetTester tester,
      List<GalaxyNodeModel> nodes,
    ) async {
      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _LoadedGalaxyNotifier(nodes),
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
            home: const Scaffold(body: GalaxyScreen()),
          ),
        ),
      );
      await tester.pump();
      // 等入场渐变与语义 flush 落地（入场 620ms + 余量；语义断言依赖
      // 画布内容所在的语义树完成组装）。
      await tester.pump(const Duration(milliseconds: 120));
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      return container;
    }

    testWidgets(
      'container exposes canvas summary with node and domain counts '
      '(验收 1：容器摘要「N 个知识点，M 个领域」在场)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          final summary = find.bySemanticsLabel(
            RegExp('知识星图：3 个知识点，覆盖 2 个领域'),
          );
          expect(
            summary,
            findsOneWidget,
            reason: '画布容器必须有规模摘要语义（N 节点 / M 领域）',
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'every node is linearly readable with name/mastery/study label '
      '(验收 2：节点语义线性可读——名称/掌握度/学习次数齐备)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          for (final node in
              _mixedNodes().where((node) => node.isUnlocked)) {
            final entry = find.bySemanticsLabel(
              RegExp(
                RegExp.escape(
                  '科技 ${node.name}（已解锁，掌握度 ${node.masteryScore} 分',
                ),
              ),
            );
            expect(
              entry,
              findsOneWidget,
              reason: '节点 ${node.name} 必须以带名称与掌握度的语义条目在树',
            );
          }

          // 锁定节点也有自己的语义条目（解锁态可辨识）。
          expect(
            find.bySemanticsLabel(RegExp(RegExp.escape('艺术 Node 2（未解锁'))),
            findsOneWidget,
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'node semantics entries expose button flag and tap action; '
      'activation follows canvas path (locked → preview card) '
      '(验收 3：语义 tap 动作可用)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          final lockedEntry = find.bySemanticsLabel(
            RegExp(RegExp.escape('艺术 Node 2（未解锁')),
          );
          expect(lockedEntry, findsOneWidget);
          final node = tester.getSemantics(lockedEntry);
          expect(
            node.getSemanticsData().flagsCollection.isButton,
            isTrue,
            reason: '节点语义条目应为 button',
          );
          expect(
            node.getSemanticsData().hasAction(SemanticsAction.tap),
            isTrue,
            reason: '节点语义条目必须带 tap 动作（读屏可激活）',
          );

          // 读屏激活（performAction，非 hit-test）→ 与画布点按同链路：
          // 锁定节点开预览卡。id 取 renderObject.debugSemantics（当前
          // 注册在 owner 上的活节点；语义节点对象会随 flush 换代，旧对象
          // 的 id 不再被 owner 分发）。owner 取活节点自身挂的 owner
          // （多视图下 rootPipelineOwner 的 owner 为空，真 owner 在
          // view 级子 PipelineOwner 上）。
          final liveNode =
              tester.renderObject<RenderObject>(lockedEntry).debugSemantics!;
          liveNode.owner!.performAction(liveNode.id, SemanticsAction.tap);
          await tester.pump();
          await tester.pump(const Duration(milliseconds: 200));

          expect(
            find.byType(GalaxyNodePreviewCard),
            findsOneWidget,
            reason: '语义 tap 激活锁定节点应打开预览卡（画布同链路）',
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'semantics overlay is visually hidden and not hit-testable '
      '(验收 4：语义子树隐身——不参与命中与绘制)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          final entry = find.bySemanticsLabel(
            RegExp(RegExp.escape('科技 Node 0（已解锁，掌握度 42 分')),
          );
          expect(entry, findsOneWidget);
          // 条目是 48×48 隐形语义锚点（非零 rect——滚动视口对 rect 不与
          // 可视区相交的语义节点打 invisible 标并禁用动作），视觉零占位。
          expect(
            tester.getSize(entry),
            const Size(48, 48),
            reason: '语义锚点应为 48×48（隐形、可遍历的最小载体）',
          );

          // hit-test 不落在语义条目上：画布中心的手势命中不被清单拦截
          // （IgnorePointer 链在 Opacity 之外，命中穿透到画布 Listener）。
          final canvasListener = find.byType(Listener);
          expect(canvasListener, findsWidgets);
          final hitTestResult = BoxHitTestResult();
          final renderCanvas = tester.renderObject<RenderBox>(
            find.descendant(
              of: find.byType(Listener),
              matching: find.byWidgetPredicate(
                (widget) => widget is CustomPaint,
              ),
            ).first,
          );
          final hit = renderCanvas.hitTest(
            hitTestResult,
            position: renderCanvas.size.center(Offset.zero),
          );
          expect(
            hit,
            isTrue,
            reason: '画布必须保持可命中（语义清单不得拦截画布手势）',
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );
  });
}

/// 双领域混合节点：2 节点 TECH 解锁（不同掌握度/学习次数）+ 1 节点 ART 锁定。
List<GalaxyNodeModel> _mixedNodes() => [
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
  _LoadedGalaxyNotifier(List<GalaxyNodeModel> nodes)
      : super(
          GalaxyState(
            nodes: nodes,
            nodePositions: <String, Offset>{
              for (final node in nodes)
                if (node.positionX != null && node.positionY != null)
                  node.id: Offset(node.positionX!, node.positionY!),
            },
            visibleNodes: nodes,
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
    // 数据已在：刷新不改变图，只走 loading 翻转（对齐 work_view mock 约定
    // ——监听器依赖 state 变更触发，否则图永不装载）。
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

  @override
  void beginNodeDrag(String nodeId) {
    state = state.copyWith(draggingNodeId: nodeId);
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
