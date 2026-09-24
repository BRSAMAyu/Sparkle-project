import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';
import '../../../shared/i18n_test_helper.dart';

/// SPEC-J（A-SPEC-V1_1 top10 #10）：galaxy 工作视图最小切片验收。
///
/// 验收条款（REPORT.md §5 #10；4 号条款经 wt324 F-3 修订）：
/// 1. 进图默认视野节点 ≤20；
/// 2. 推荐 chip（「下一个建议碰：X」）同屏 ≤1；
/// 3. chip 点击直达复习流（既有 /chat 路由 + reviewUrgencyReason 理由链）；
/// 4. 无推荐目标时不再无引导（F-3）：相机落到结构锚（importance 最高、
///    图序稳定）邻域作视觉起始引导，仍不挂 chip、不带复习语义。
void main() {
  setUp(setUpI18nForTesting);

  group('SPEC-J galaxy work view', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
    });

    final zh = AppLocalizationsZh();

    testWidgets(
      'recommended node shows exactly one "next touch" chip with its name '
      '(SPEC-J 验收 2：chip 同屏 ≤1)',
      (tester) async {
        final nodes = _gridNodes(count: 12, columns: 4);
        nodes[5] = _withReviewSignal(nodes[5], score: 7.5);
        final container = await _pumpGalaxy(tester, nodes, const []);

        await _pumpUntilWorkViewSettled(tester, anchorId: nodes[5].id);

        expect(
          find.byKey(const ValueKey('galaxy_work_view_chip')),
          findsOneWidget,
        );
        // ≤1 名额铁律：全屏恰好一份推荐文案承载。
        expect(find.textContaining('下一个建议碰'), findsOneWidget);
        expect(
          find.text(zh.galaxyWorkViewNextTouch(nodes[5].name)),
          findsOneWidget,
        );
        container.dispose();
      },
    );

    testWidgets(
      'chip tap goes straight into review flow via /chat with reason-chain '
      'params (SPEC-J 验收 3：点击直达复习流)',
      (tester) async {
        Uri? capturedUri;
        final nodes = _gridNodes(count: 12, columns: 4);
        // recent_errors → 既有理由链映射 error_diagnosis 模式。
        nodes[5] = _withReviewSignal(
          nodes[5],
          score: 7.5,
          reason: 'recent_errors',
        );

        final router = GoRouter(
          initialLocation: '/galaxy',
          routes: [
            GoRoute(
              path: '/galaxy',
              builder: (context, state) => const Scaffold(
                body: GalaxyScreen(),
              ),
            ),
            GoRoute(
              path: '/chat',
              redirect: (context, state) {
                capturedUri = state.uri;
                return '/chat-stub';
              },
            ),
            GoRoute(
              path: '/chat-stub',
              builder: (context, state) =>
                  const Scaffold(body: Text('chat-stub')),
            ),
          ],
        );
        addTearDown(router.dispose);

        final container = ProviderContainer(
          overrides: [
            galaxyProvider.overrideWith(
              (ref) => _LoadedGalaxyNotifier(nodes, const []),
            ),
          ],
        );
        addTearDown(container.dispose);

        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: container,
            child: MaterialApp.router(
              theme: AppThemes.lightTheme,
              locale: const Locale('zh'),
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              routerConfig: router,
            ),
          ),
        );

        await _pumpUntilWorkViewSettled(tester, anchorId: nodes[5].id);

        await tester.tap(
          find.byKey(const ValueKey('galaxy_work_view_chip')),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));

        expect(capturedUri, isNotNull);
        expect(capturedUri!.path, '/chat');
        expect(capturedUri!.queryParameters['target_node_id'], nodes[5].id);
        // 既有理由链：recent_errors → error_diagnosis 模式 + 个性化 prompt。
        expect(capturedUri!.queryParameters['chat_mode'], 'error_diagnosis');
        expect(capturedUri!.queryParameters['prompt'], contains('Node 5'));
      },
    );

    testWidgets(
      'default entry view frames anchor neighborhood with at most 20 visible '
      'nodes (SPEC-J 验收 1：进图默认视野节点 ≤20)',
      (tester) async {
        const total = 40;
        final nodes = _gridNodes(count: total, columns: 8, spacing: 110);
        nodes[22] = _withReviewSignal(nodes[22], score: 5);
        final container = await _pumpGalaxy(tester, nodes, const []);

        await _pumpUntilWorkViewSettled(tester, anchorId: nodes[22].id);

        final painter = _starMapPainter(tester);
        final viewport = painter.camera.viewportSize;
        const margin = 48.0;
        var visible = 0;
        for (final position in painter.positions.values) {
          final screen = painter.camera.worldToScreen(position);
          if (screen.dx >= -margin &&
              screen.dx <= viewport.width + margin &&
              screen.dy >= -margin &&
              screen.dy <= viewport.height + margin) {
            visible++;
          }
        }
        expect(visible, lessThanOrEqualTo(20));
        // 聚焦的是推荐锚点且邻域高亮生效（复用 spotlight 地基）。
        expect(painter.spotlightAnchorId, nodes[22].id);
        expect(painter.spotlightNodeIds, contains(nodes[22].id));
        // 聚焦态下推荐 chip 在屏（唯一承载）。
        expect(
          find.byKey(const ValueKey('galaxy_work_view_chip')),
          findsOneWidget,
        );
        container.dispose();
      },
    );

    testWidgets(
      'no recommendation → structural anchor fallback: camera converges to '
      'highest-importance node, still no chip (F-3：无推荐不再无引导)',
      (tester) async {
        final nodes = _gridNodes(count: 12, columns: 4);
        // 无任何 is_review_recommended：structural anchor = importance 最高
        // 的图序首个 → index 4（importance 5；index 9 同分靠后）。
        final container = await _pumpGalaxy(tester, nodes, const []);

        await _pumpUntilWorkViewSettled(tester, anchorId: nodes[4].id);

        // F-3 契约：无推荐≠无引导——相机落到结构锚邻域并挂 spotlight
        // （含 F-3 锚定指示环的绘制口径），但复习语义不跟来。
        final painter = _starMapPainter(tester);
        expect(painter.spotlightAnchorId, nodes[4].id);
        expect(painter.spotlightNodeIds, contains(nodes[4].id));
        expect(
          find.byKey(const ValueKey('galaxy_work_view_chip')),
          findsNothing,
        );
        expect(find.textContaining('下一个建议碰'), findsNothing);
        container.dispose();
      },
    );

    testWidgets(
      'fresh all-locked graph gets a visible starting focus without review '
      'semantics (F-3：fresh 全锁定初始态起始引导)',
      (tester) async {
        final nodes = _gridNodes(count: 12, columns: 4, unlocked: false);
        final container = await _pumpGalaxy(tester, nodes, const []);

        await _pumpUntilWorkViewSettled(tester, anchorId: nodes[4].id);

        final painter = _starMapPainter(tester);
        // wt324 F-3 现象回归钉：全锁定进图后锚定在视口内可指认
        // （结构锚 = importance 最高、图序稳定），不再停留全图概览。
        expect(painter.spotlightAnchorId, nodes[4].id);
        expect(painter.spotlightNodeIds, contains(nodes[4].id));
        // 锁定节点无复习语义可挂：chip 必须缺席。
        expect(
          find.byKey(const ValueKey('galaxy_work_view_chip')),
          findsNothing,
        );
        container.dispose();
      },
    );
  });
}

Future<ProviderContainer> _pumpGalaxy(
  WidgetTester tester,
  List<GalaxyNodeModel> nodes,
  List<GalaxyEdgeModel> edges,
) async {
  final container = ProviderContainer(
    overrides: [
      galaxyProvider.overrideWith((ref) => _LoadedGalaxyNotifier(nodes, edges)),
    ],
  );
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        // 断言走中文文案，显式锁 zh（test 默认 en_US）。
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: const Scaffold(body: GalaxyScreen()),
      ),
    ),
  );
  return container;
}

/// 等入场编排（构建回放/相机动画/布局收敛）与工作视野聚焦全部落地：
/// 连续 3 拍 painter 的位置与相机无变化且回放结束；带锚点时还要求
/// spotlight 已挂到锚点（聚焦动画完成）。
Future<void> _pumpUntilWorkViewSettled(
  WidgetTester tester, {
  required String? anchorId,
  int maxIterations = 90,
}) async {
  var stableRuns = 0;
  var previousPositions = <String, Offset>{};
  var previousScale = double.nan;
  var previousOffset = const Offset(double.nan, double.nan);
  for (var i = 0; i < maxIterations; i++) {
    await tester.pump(const Duration(milliseconds: 500));
    final painter = _starMapPainter(tester);
    final camera = painter.camera;
    final positionsStable =
        _samePositions(painter.positions, previousPositions);
    final cameraStable =
        camera.scale == previousScale && camera.offset == previousOffset;
    if (!painter.isBuildAnimating && positionsStable && cameraStable) {
      stableRuns++;
      if (stableRuns >= 3 &&
          (anchorId == null || painter.spotlightNodeIds.contains(anchorId))) {
        return;
      }
    } else {
      stableRuns = 0;
    }
    previousPositions = painter.positions;
    previousScale = camera.scale;
    previousOffset = camera.offset;
  }
  // 不 fail 在此——由调用方按验收条款断言实际终态。
}

StarMapPainter _starMapPainter(WidgetTester tester) {
  final matches = tester.widgetList<CustomPaint>(
    find.byWidgetPredicate(
      (widget) => widget is CustomPaint && widget.painter is StarMapPainter,
    ),
  );
  expect(matches, isNotEmpty, reason: 'StarMapPainter 应已上树');
  return matches.first.painter! as StarMapPainter;
}

bool _samePositions(
  Map<String, Offset> a,
  Map<String, Offset> b,
) {
  if (a.length != b.length) {
    return false;
  }
  for (final entry in a.entries) {
    if (b[entry.key] != entry.value) {
      return false;
    }
  }
  return true;
}

/// 网格布点（带 position_x/y 稳定位），模拟真实图密度。
List<GalaxyNodeModel> _gridNodes({
  required int count,
  required int columns,
  double spacing = 100,
  bool unlocked = true,
}) =>
    List<GalaxyNodeModel>.generate(count, (index) {
      final row = index ~/ columns;
      final column = index % columns;
      return GalaxyNodeModel.fromJson({
        'id': 'node_$index',
        'name': 'Node $index',
        'importance': (index % 5) + 1,
        'sector_code': 'TECH',
        'is_unlocked': unlocked,
        'mastery_score': (index * 7) % 100,
        'position_x': column * spacing,
        'position_y': row * spacing,
      });
    });

/// 挂上服务端既有推荐信号（is_review_recommended / review_urgency_score /
/// review_urgency_reason——与预览卡推荐理由链同一数据源）。
GalaxyNodeModel _withReviewSignal(
  GalaxyNodeModel node, {
  required double score,
  String reason = 'decay_risk',
}) {
  final refreshed = GalaxyNodeModel.fromJson({
    'id': node.id,
    'name': node.name,
    'importance': node.importance,
    'sector_code': node.sector.name,
    'is_unlocked': node.isUnlocked,
    'mastery_score': node.masteryScore,
    'position_x': node.positionX,
    'position_y': node.positionY,
    'is_review_recommended': true,
    'review_urgency_score': score,
    'review_urgency_reason': reason,
  });
  return refreshed;
}

class _LoadedGalaxyNotifier extends _MockGalaxyNotifier {
  _LoadedGalaxyNotifier(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
  ) : super(_initialState(nodes, edges));

  static GalaxyState _initialState(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
  ) =>
      GalaxyState(
        nodes: nodes,
        edges: edges,
        nodePositions: <String, Offset>{
          for (final node in nodes)
            if (node.positionX != null && node.positionY != null)
              node.id: Offset(node.positionX!, node.positionY!),
        },
        visibleNodes: nodes,
        visibleEdges: edges,
        userFlameIntensity: 0.4,
      );

  @override
  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
    // 数据已在：刷新不改变图，只走 loading 翻转（对齐既有 mock 约定）。
    state = state.copyWith(isLoading: true);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    state = state.copyWith(isLoading: false);
  }
}

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
    // 本卡用例不依赖取消选中的语义（与 galaxy_screen_test mock 同位）。
  }

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
  }) async {}

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
