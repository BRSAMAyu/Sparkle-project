import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_draft_repository.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../shared/i18n_test_helper.dart';

/// V3-FIX-60（Q-03）：星图右缘相机控制竖排 rail（GalaxyControls，画布级
/// Positioned right:16）与草稿提示卡「现在审核」主 CTA 部分重叠——卡片挂
/// top:48 流式列全宽（left:16/right:16）铺满，右缘 ~72px 被 rail 压住。
///
/// 修法口径（卡面：最小布局避让，不动两组件语义）：提示卡在流式列内做
/// 右侧避让缩进，给 rail 让出无遮挡通道；rail 语义与位置不动。
void main() {
  setUp(setUpI18nForTesting);

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
    '「现在审核」CTA 热区不得与相机控制 rail 相交（V3-FIX-60 避让锁）',
    (tester) async {
      // 钉手机比例面（逻辑 390×700）：默认 800×600 测试面上卡片高于 rail 带、
      // 不复现重叠；窄高面下流式列（top:48 起）卡片下行进 rail 带（bottom:16、
      // 高 ~334 → top≈350），与 C02 证据同构。
      tester.view.physicalSize = const Size(1170, 2100);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final nodes = _gridNodes(count: 12, columns: 4);
      final batch = GalaxyDraftBatch(
        id: 'batch_wt418',
        documentId: 'doc_wt418',
        documentName: '操作系统.pdf',
        createdAt: DateTime.utc(2026, 9, 25),
        drafts: const [
          GalaxyDraftNode(
            id: 'draft_1',
            proposedName: '进程与线程',
            proposedDescription: '草稿节点描述',
            excerpts: ['进程是资源分配的基本单位'],
          ),
        ],
      );

      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _LoadedGalaxyNotifier(nodes, const []),
          ),
          galaxyDraftRepositoryProvider.overrideWithValue(
            _PendingDraftsRepository([batch]),
          ),
        ],
      );
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

      // 草稿批经 notifier.refresh() 异步装入；入场编排（建图回放/相机动画）
      // 期间加载覆盖层常驻——轮询泵到 CTA 上树（上限 40s），不做死等。
      for (var i = 0; i < 80 && find.text('现在审核').evaluate().isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 500));
      }
      // 冲刷剩余 timer（贡献榜 provider 的重试/退避等），避免终局 pending-timer。
      for (var i = 0; i < 12; i++) {
        await tester.pump(const Duration(milliseconds: 500));
      }

      expect(
        find.text('现在审核'),
        findsOneWidget,
        reason: '草稿提示卡必须已上树（缺陷前提）',
      );
      expect(
        find.byType(GalaxyControls),
        findsOneWidget,
        reason: '相机控制 rail 必须已上树（缺陷前提）',
      );

      // 断言挂在按钮热区层（FilledButton），不是内部 Text——可点击域才是
      // 用户实际被 rail 截获的面（卡面登记 ~70px 视觉侵占即按钮右缘段）。
      final ctaRect = tester.getRect(
        find.ancestor(
          of: find.text('现在审核'),
          matching: find.byType(FilledButton),
        ),
      );
      final railRect = tester.getRect(find.byType(GalaxyControls));

      // 修前：CTA 右缘（卡片 right:16 铺满）伸进 rail x 带（right:16、宽 ~72）
      // 且 CTA 行 y 落在 rail 高度带内 → 相交，可点击域被 rail 截获。
      expect(
        ctaRect.overlaps(railRect),
        isFalse,
        reason: '「现在审核」CTA ($ctaRect) 不得与相机控制 rail ($railRect) '
            '相交（V3-FIX-60：提示卡须为右缘 rail 让位）',
      );
    },
  );
}

/// 草稿仓桩：返回固定 pending 批（绕开真实 Dio 网络面）。
class _PendingDraftsRepository extends GalaxyDraftRepository {
  _PendingDraftsRepository(this._batches) : super(Dio(), demoMode: false);

  final List<GalaxyDraftBatch> _batches;

  @override
  Future<List<GalaxyDraftBatch>> listPendingDrafts() async => _batches;
}

List<GalaxyNodeModel> _gridNodes({
  required int count,
  required int columns,
  double spacing = 100,
}) =>
    List<GalaxyNodeModel>.generate(count, (index) {
      final row = index ~/ columns;
      final column = index % columns;
      return GalaxyNodeModel.fromJson({
        'id': 'node_$index',
        'name': 'Node $index',
        'importance': (index % 5) + 1,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': (index * 7) % 100,
        'position_x': column * spacing,
        'position_y': row * spacing,
      });
    });

class _LoadedGalaxyNotifier extends _MockGalaxyNotifier {
  _LoadedGalaxyNotifier(
    List<GalaxyNodeModel> nodes,
    List<GalaxyEdgeModel> edges,
  ) : super(
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
          ),
        );

  @override
  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
    // 数据已在：刷新只走 loading 翻转（与 galaxy_work_view_test mock 同约定）——
    // 必须发射状态变更，否则屏幕端 provider listener 不再触发、加载态永真。
    state = state.copyWith(isLoading: true);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    state = state.copyWith(isLoading: false);
  }
}

/// 与 galaxy_work_view_test 同位的最小 mock（只实现测试路径触达的成员）。
class _MockGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _MockGalaxyNotifier(super.state);

  @override
  void selectNode(String nodeId) {}

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
  void beginNodeDrag(String nodeId) {}

  @override
  void updateDraggedNodePosition(String nodeId, Offset newPosition) {}

  @override
  Future<void> endNodeDrag() async {}

  @override
  void setEvidenceHighlight(Set<String> ids, {String? focusId}) {}

  @override
  void clearFocusBounds() {}

  @override
  void clearFocusNode() {}

  @override
  void clearEvidenceHighlight() {}

  @override
  void setFocusNode(String nodeId) {}
}
