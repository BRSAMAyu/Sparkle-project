import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U05 整改（一审 R1-C1）· screen→sheet 同源接线钉。
///
/// 一审突变记录：直构 [NodeDetailSheet] 的抽屉测试不经过 galaxy_screen，
/// 「`_openNodeDetailSheet` 不传 capability+graphEventSources（同源断链）」
/// 类突变后仍全绿——screen→sheet 接线（galaxy_screen `_openNodeDetailSheet`
/// 把同一 [GalaxyNodeModel] 快照的 `capability` + `graphEventSources` 传入
/// sheet）此前零测试钉。本测泵起**真实 GalaxyScreen** → 触发节点点开
/// （键盘 Enter 与画布点按/读屏 tap 同一激活链路：`_startTapFeedback` →
/// `_openNodeDetailSheet`）→ 断言抽屉出现，且展示的节点身份/通道徽章/
/// 溯源行/投影版本与该节点的 [GalaxyNodeModel] 快照一致；unknown 降级面
/// （证据通道未知/暂无来源记录/投影版本未知）绝不出现——同源断链类突变
/// （绕过接线直接开 sheet / 丢参）必红。
void main() {
  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
    // 与 u05_evidence_test 同款：星图页挂载后的延迟刷新会走认证拦截器读
    // 安全存储（测试环境无插件实现），按值打桩后请求方走离线降级，不
    // 影响本测的星图/抽屉接线面。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  testWidgets(
    '真实 GalaxyScreen 泵起点开节点：抽屉的节点/溯源行/投影版本与该节点'
    '模型同快照（R1-C1 接线钉）',
    (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _WiredGalaxyNotifier([_wiredNode()]),
          ),
          sharedPreferencesProvider.overrideWithValue(prefs),
          // /history 打桩走成功分支：本测钉的是 screen→sheet 的能力快照
          // 接线（与 /history 网络面无关）——测试 HttpClient 恒回 400 会把
          // sheet 打进错误态（错误态不渲染能力面），与被钉接线无关。
          enhancedGalaxyRepositoryProvider.overrideWith(
            (ref) => _StubHistoryRepository(ref.watch(apiClientProvider)),
          ),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            theme: AppThemes.lightTheme,
            // 断言走中文语义文案，显式锁 zh（与 keynav/证据测同口径）。
            locale: const Locale('zh'),
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: const Scaffold(body: GalaxyScreen()),
          ),
        ),
      );
      await tester.pump();
      // 等入场渐变与语义 flush 落地（入场 620ms + 余量；keynav 同款泵序）。
      await tester.pump(const Duration(milliseconds: 120));
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(tester.takeException(), isNull);

      // 键盘 Enter 与画布点按/读屏 tap 同链路（GALAXY-KEYNAV 验收 3b 既有
      // 结论）：聚焦节点语义条目 → Enter → tap 反馈链 → 详情 sheet。
      final entry = tester.widget<GalaxyNodeSemantics>(
        find.byWidgetPredicate(
          (widget) =>
              widget is GalaxyNodeSemantics && widget.node.id == 'node_wired',
        ),
      );
      entry.focusNode!.requestFocus();
      await tester.pump();
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      // tap 反馈 420ms + sheet 进场 + 余量（keynav 同款泵序）；末尾追加
      // 冲洗泵，让 sheet 进场帧排程的一次性 stagger Timer 落地（避免
      // 「Timer is still pending」invariant 误报）。
      await tester.pump(const Duration(milliseconds: 600));
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump();
      expect(tester.takeException(), isNull);

      expect(
        find.byType(NodeDetailSheet),
        findsOneWidget,
        reason: '真实 GalaxyScreen 触发节点点开必须打开详情抽屉',
      );
      // 抽屉展示的三面全部来自同一 GalaxyNodeModel 快照（galaxy_screen
      // `_openNodeDetailSheet` 传 node.capability + node.graphEventSources）：
      expect(
        find.text('同源快照的星'),
        findsOneWidget,
        reason: '抽屉节点身份必须是被点开的节点（nodeLabel=node.name）',
      );
      expect(
        find.text('独立检验通过'),
        findsOneWidget,
        reason: '通道徽章必须来自 node.capability（verified）',
      );
      expect(
        find.textContaining('第 3 章单元测验'),
        findsOneWidget,
        reason: '溯源行必须来自 node.graphEventSources',
      );
      expect(
        find.text('投影版本 v7'),
        findsOneWidget,
        reason: '投影版本必须来自 node.capability.projectionVersion',
      );
      // 同源断链类突变（绕过 _openNodeDetailSheet 直接开 sheet / 丢参）会让
      // 抽屉退化为 unknown 降级面——反例断言让该类突变必红。
      expect(find.text('证据通道未知'), findsNothing);
      expect(find.text('暂无来源记录'), findsNothing);
      expect(find.text('投影版本未知'), findsNothing);
    },
  );
}

/// 接线钉节点：verified 通道 + 投影版本 v7 + quiz 溯源行，全部同一份
/// 节点 JSON 快照解析（与 u05_evidence_test 同构口径）。
GalaxyNodeModel _wiredNode() => GalaxyNodeModel.fromJson(const {
      'id': 'node_wired',
      'name': '同源快照的星',
      'importance': 4,
      'sector_code': 'TECH',
      'is_unlocked': true,
      'mastery_score': 92,
      'study_count': 9,
      'position_x': 0.0,
      'position_y': 0.0,
      'user_status': {
        'mastery_evidence': {
          'capability_channel': 'verified',
          'evidence_count': 2,
        },
        'projection_version': 7,
      },
      'graph_event_sources': [
        {
          'source_type': 'quiz_feedback',
          'label': '第 3 章单元测验',
          'reference_id': 'quiz_1',
          'recorded_at': '2026-09-20T10:00:00.000Z',
        },
      ],
    });

/// /history 打桩：返回成功历史（与线上常态同分支，FutureBuilder 走
/// `_HistoryContent`——能力证据面以 `capabilitySection` 参数同屏渲染）。
/// 出网被隔离：测试 HttpClient 恒回 400 与本测无关，不参与被钉接线。
class _StubHistoryRepository extends EnhancedGalaxyRepository {
  _StubHistoryRepository(super.client);

  @override
  Future<NetworkResult<GalaxyNodeHistory>> getNodeHistory(
    String nodeId, {
    String? packId,
  }) async =>
      NetworkResult.success(
        GalaxyNodeHistory(
          nodeId: nodeId,
          nodeLabel: '同源快照的星',
          mastery: 0.85,
          studyCount: 9,
        ),
      );
}

class _WiredGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _WiredGalaxyNotifier(List<GalaxyNodeModel> nodes)
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
