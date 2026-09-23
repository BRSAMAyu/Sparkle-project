import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_camera.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

/// GALAXY-KEYNAV：星图键盘导航验收（wt259 登记保留件
/// GalaxyFocusManager / GalaxyKeyboardNavigation 的接线卡）。
///
/// 验收五条：
/// 1. 方向键按图序遍历（语义清单同序）：焦点移入下一/上一节点条目，
///    画布焦点环参数（StarMapPainter.keyboardFocusNodeId）同步；
/// 2. Tab / Shift+Tab 沿同一图序前后移动（OrderedTraversalPolicy 定序，
///    同位条目不依赖非稳定排序）；
/// 3. Enter 激活与语义 tap 同链路：锁定节点→预览卡，解锁节点→tap 反馈
///    链→详情 sheet；
/// 4. Esc 分层：预览卡在屏先关（焦点保留），再按清键盘焦点（焦点环熄灭）；
/// 5. 键盘焦点→语义焦点同步（hasFocus 标志）+ 焦点变化读屏播报
///    （节点名+掌握度，galaxyA11yNode* 既有文案）。
void main() {
  setUp(setUpI18nForTesting);

  group('galaxy keyboard navigation (GALAXY-KEYNAV)', () {
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
      // 等入场渐变与语义 flush 落地（入场 620ms + 余量）。
      await tester.pump(const Duration(milliseconds: 120));
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      return container;
    }

    GalaxyNodeSemantics entryWidget(WidgetTester tester, String nodeId) =>
        tester.widget<GalaxyNodeSemantics>(
          find.byWidgetPredicate(
            (widget) => widget is GalaxyNodeSemantics && widget.node.id == nodeId,
          ),
        );

    StarMapPainter canvasPainter(WidgetTester tester) => tester
        .widget<CustomPaint>(
          find.byWidgetPredicate(
            (widget) => widget is CustomPaint && widget.painter is StarMapPainter,
          ),
        )
        .painter! as StarMapPainter;

    Future<void> focusEntry(WidgetTester tester, String nodeId) async {
      entryWidget(tester, nodeId).focusNode!.requestFocus();
      await tester.pump();
    }

    bool semanticsFocused(WidgetTester tester, String nodeId) =>
        tester
            .getSemantics(
              find.byWidgetPredicate(
                (widget) =>
                    widget is GalaxyNodeSemantics && widget.node.id == nodeId,
              ),
            )
            .getSemanticsData()
            .flagsCollection
            .isFocused ==
        Tristate.isTrue;

    testWidgets(
      'arrow keys traverse nodes in graph order; painter focus ring follows; '
      'announcements carry name and mastery '
      '(验收 1+5：方向键图序遍历 + 焦点环跟随 + 名称掌握度播报)',
      (tester) async {
        final announcements = <String>[];
        // SystemChannels.accessibility 是 BasicMessageChannel（JSONMessageCodec
        // ），SemanticsService.announce 走 send(AnnounceSemanticsEvent.toMap())
        // ——载荷形如 {'type': 'announce', 'data': {'message': ...}}。
        tester.binding.defaultBinaryMessenger.setMockDecodedMessageHandler(
          SystemChannels.accessibility,
          (dynamic message) async {
            if (message is Map && message['type'] == 'announce') {
              final data = message['data'];
              if (data is Map && data['message'] is String) {
                announcements.add(data['message'] as String);
              }
            }
          },
        );
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          await focusEntry(tester, 'node_0');
          expect(
            semanticsFocused(tester, 'node_0'),
            isTrue,
            reason: '键盘聚焦必须同步语义焦点（hasFocus 标志）',
          );
          expect(canvasPainter(tester).keyboardFocusNodeId, 'node_0');

          // 方向键下移 → 图序下一节点（node_1）。
          await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
          await tester.pump();
          expect(
            canvasPainter(tester).keyboardFocusNodeId,
            'node_1',
            reason: '焦点环参数必须随方向键遍历移到图序下一节点',
          );
          expect(
            FocusManager.instance.primaryFocus,
            entryWidget(tester, 'node_1').focusNode,
            reason: '主焦点必须落在下一节点条目',
          );
          expect(semanticsFocused(tester, 'node_1'), isTrue);
          expect(semanticsFocused(tester, 'node_0'), isFalse);

          // 方向键上移 → 回到 node_0。
          await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
          await tester.pump();
          expect(canvasPainter(tester).keyboardFocusNodeId, 'node_0');

          // 焦点移出清单（外部控件/模态抢焦点同形）：焦点环不残留。
          FocusManager.instance.primaryFocus?.unfocus();
          await tester.pump();
          expect(
            canvasPainter(tester).keyboardFocusNodeId,
            isNull,
            reason: '焦点离开节点清单后焦点环必须熄灭',
          );
          expect(semanticsFocused(tester, 'node_0'), isFalse);

          // 焦点变化播报：既有语义全标签（名称+掌握度，galaxyA11yNode*）。
          expect(
            announcements.any(
              (text) =>
                  text.contains('Node 1') && text.contains('掌握度 87'),
            ),
            isTrue,
            reason: '焦点移入必须播报节点名与掌握度（含「Node 1」「掌握度 87」）',
          );
          expect(
            announcements.any((text) => text.contains('Node 0')),
            isTrue,
            reason: '初次聚焦也要播报（名称+掌握度）',
          );
          container.dispose();
        } finally {
          tester.binding.defaultBinaryMessenger.setMockDecodedMessageHandler(
            SystemChannels.accessibility,
            null,
          );
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'Tab and Shift+Tab move focus along graph order '
      '(验收 2：Tab/Shift+Tab 图序遍历——同位条目显式定序)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          await focusEntry(tester, 'node_0');
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.pump();
          expect(
            FocusManager.instance.primaryFocus,
            entryWidget(tester, 'node_1').focusNode,
            reason: 'Tab 必须沿图序移到下一节点条目（同位 rect 不得乱序）',
          );
          expect(canvasPainter(tester).keyboardFocusNodeId, 'node_1');

          // Shift+Tab：sendKeyEvent 是 down+up 一瞬，须先按住 Shift。
          await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
          await tester.pump();
          expect(
            FocusManager.instance.primaryFocus,
            entryWidget(tester, 'node_0').focusNode,
            reason: 'Shift+Tab 必须回到上一节点条目',
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'Enter on locked node opens preview card; Esc closes it and keeps '
      'focus; Esc again clears keyboard focus '
      '(验收 3+4a：Enter 锁定→预览卡，Esc 分层关闭)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          await focusEntry(tester, 'node_2');
          await tester.sendKeyEvent(LogicalKeyboardKey.enter);
          await tester.pump();
          await tester.pump(const Duration(milliseconds: 200));

          expect(
            find.byType(GalaxyNodePreviewCard),
            findsOneWidget,
            reason: 'Enter 激活锁定节点必须打开预览卡（与语义 tap 同链路）',
          );
          expect(
            canvasPainter(tester).keyboardFocusNodeId,
            'node_2',
            reason: '预览打开后节点焦点保留',
          );

          // Esc 第一层：关预览卡，焦点保留。
          await tester.sendKeyEvent(LogicalKeyboardKey.escape);
          await tester.pump();
          await tester.pump(const Duration(milliseconds: 200));
          expect(
            find.byType(GalaxyNodePreviewCard),
            findsNothing,
            reason: 'Esc 必须先关在屏预览卡',
          );
          expect(
            canvasPainter(tester).keyboardFocusNodeId,
            'node_2',
            reason: '关预览不清键盘焦点（焦点环保持）',
          );

          // Esc 第二层：无在屏覆盖层 → 清键盘焦点，焦点环熄灭。
          await tester.sendKeyEvent(LogicalKeyboardKey.escape);
          await tester.pump();
          expect(
            canvasPainter(tester).keyboardFocusNodeId,
            isNull,
            reason: '第二次 Esc 清键盘焦点，焦点环参数归空',
          );
          expect(semanticsFocused(tester, 'node_2'), isFalse);
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );

    testWidgets(
      'Enter on unlocked node runs the canvas tap-feedback chain and opens '
      'the detail sheet (验收 3b：Enter 解锁→tap 反馈链→详情 sheet)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final container = await pumpLoadedGalaxy(tester, _mixedNodes());

          await focusEntry(tester, 'node_0');
          await tester.sendKeyEvent(LogicalKeyboardKey.enter);
          await tester.pump();

          expect(
            canvasPainter(tester).tapFeedbackNodeId,
            'node_0',
            reason: 'Enter 激活解锁节点必须进画布 tap 反馈链（与点按同链路）',
          );

          // 反馈动画 420ms 完成后自动开详情 sheet。
          await tester.pump(const Duration(milliseconds: 600));
          await tester.pump(const Duration(milliseconds: 400));
          expect(
            find.byType(NodeDetailSheet),
            findsOneWidget,
            reason: 'tap 反馈完成后必须打开详情 sheet（解锁→详情）',
          );
          container.dispose();
        } finally {
          semantics.dispose();
        }
      },
    );
  });

  group('keyboard focus ring paint (GALAXY-KEYNAV)', () {
    test(
      'focus ring draw path executes on canvas paint with focus param '
      '(焦点环渲染断言：带 keyboardFocusNodeId 的画布绘制可执行)',
      () {
        final nodes = _mixedNodes();
        final positions = <String, Offset>{
          for (final node in nodes)
            node.id: Offset(node.positionX!, node.positionY!),
        };
        final painter = StarMapPainter(
          camera: const GalaxyCamera(
            offset: Offset(200, 200),
            scale: 1.0,
            viewportSize: Size(400, 400),
          ),
          nodesById: {for (final node in nodes) node.id: node},
          edges: const <GalaxyEdgeModel>[],
          positions: positions,
          spatialIndex: GalaxySpatialIndex()..build(positions, nodes),
          labelCache: GalaxyLabelCache(),
          backdropPictureCache: GalaxyBackdropPictureCache(),
          parallaxStarLayerCache: GalaxyParallaxStarLayerCache(),
          sceneVersion: 0,
          isDarkMode: true,
          worldBounds: const Rect.fromLTWH(-50, -50, 220, 220),
          blendedColors: {
            for (final node in nodes) node.id: const Color(0xFF66AAFF),
          },
          displaySettings: const GalaxyDisplaySettings(),
          playbackPlan: null,
          playbackElapsedMs: 0,
          preRevealedNodeIds: const <String>{},
          preRevealedEdgeIds: const <String>{},
          nodeConnectionCounts: const <String, int>{},
          keyboardFocusNodeId: 'node_0',
        );
        final recorder = PictureRecorder();
        final canvas = Canvas(recorder);
        // 不抛异常即通过：焦点环与命中高亮同一绘制管线（节点中心同心环 +
        // 虚线外圈），参数接线由 widget 级断言（keyboardFocusNodeId）覆盖。
        painter.paint(canvas, const Size(400, 400));
        final picture = recorder.endRecording();
        expect(picture, isNotNull);
        picture.dispose();
      },
    );
  });
}

/// 双领域混合节点：2 节点 TECH 解锁（不同掌握度/学习次数）+ 1 节点 ART 锁定。
/// 与 galaxy_screen_semantics_test 同构图（同序断言的同一口径）。
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
