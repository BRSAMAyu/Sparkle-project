// ignore_for_file: avoid_print

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

/// GALAXY-A11Y 性能探针：语义子树（节点语义清单）不得明显拖慢画布帧率。
///
/// 方法：300 节点真实装载路径进图，语义开启（ensureSemantics，对应读屏
/// 用户环境），拖拽手势驱动每帧 setState+repaint+语义 flush（最坏情况：
/// 相机平移热路径），取 150 帧平均墙钟帧耗。
///
/// A/B 口径：本文件同时跑在 worktree（含语义清单）与 HEAD 基线克隆
/// （无语义清单，`git clone` 天然基线），同机同进程对比。
/// 门限只设防病理性回退的宽松绝对值；精细 A/B 数字进本卡 REPORT。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
    '300-node galaxy drag frames stay within budget with semantics on '
    '(GALAXY-A11Y 性能红线)',
    (tester) async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();

      final nodes = _gridNodes(300, columns: 20, spacing: 90);
      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _LoadedGalaxyNotifier(nodes),
          ),
        ],
      );
      addTearDown(container.dispose);

      final semantics = tester.ensureSemantics();
      try {
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

        // 等入场回放/物理收敛（同 galaxy_work_view_test 的稳定判据，
        // 简化为回放结束 + 定量拍）。
        await tester.pump(const Duration(milliseconds: 500));
        var guard = 0;
        while (_isBuildAnimating(tester) && guard < 60) {
          await tester.pump(const Duration(milliseconds: 200));
          guard++;
        }
        for (var i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 60));
        }

        // 热身。
        for (var i = 0; i < 20; i++) {
          await tester.pump(const Duration(milliseconds: 16));
        }

        // 拖拽热路径：按下画布中心，150 帧连续平移，每帧一拍。
        const frames = 150;
        final gesture = await tester.startGesture(
          tester.getCenter(find.byType(GalaxyScreen)),
        );
        await tester.pump();
        final stopwatch = Stopwatch()..start();
        for (var i = 0; i < frames; i++) {
          await gesture.moveBy(
            const Offset(6, 4),
            timeStamp: Duration(milliseconds: i * 16),
          );
          await tester.pump(const Duration(milliseconds: 16));
        }
        stopwatch.stop();
        await gesture.up();
        await tester.pump();

        final avgFrameMicros = stopwatch.elapsedMicroseconds / frames;
        print('GALAXY-A11Y-PERF avg_frame_micros=$avgFrameMicros');

        // 宽松绝对门：单帧 < 50ms（防病理性回退，不作精细基线）。
        expect(avgFrameMicros, lessThan(50000));
      } finally {
        semantics.dispose();
      }
    },
  );
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

List<GalaxyNodeModel> _gridNodes(
  int count, {
  required int columns,
  required double spacing,
}) =>
    List<GalaxyNodeModel>.generate(count, (index) {
      final row = index ~/ columns;
      final column = index % columns;
      return GalaxyNodeModel.fromJson({
        'id': 'node_$index',
        'name': 'Node $index',
        'importance': (index % 5) + 1,
        'sector_code': 'TECH',
        'is_unlocked': index % 7 != 0,
        'mastery_score': (index * 7) % 100,
        'study_count': index % 11,
        'position_x': column * spacing,
        'position_y': row * spacing,
      });
    });

class _LoadedGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _LoadedGalaxyNotifier(List<GalaxyNodeModel> nodes)
      : super(
          GalaxyState(
            nodes: nodes,
            nodePositions: <String, Offset>{
              for (final node in nodes)
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
    // 数据已在：刷新不改变图，只走 loading 翻转（触发监听器装载图）。
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
