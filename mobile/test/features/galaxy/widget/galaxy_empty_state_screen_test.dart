import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/retry_strategy.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/galaxy/data/models/user_galaxy_contribution.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets('galaxy screen shows guided empty state for empty graph', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FakeEnhancedGalaxyRepository(),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const GalaxyScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('星图空空如也'), findsOneWidget);
    expect(find.text('去创建学习任务'), findsOneWidget);
  });

  testWidgets(
      'galaxy screen shows mastery onboarding banner when mastery is zero',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FakeEnhancedGalaxyRepository(
              graph: GalaxyGraphResponse(
                nodes: <GalaxyNodeModel>[
                  GalaxyNodeModel(
                    id: 'node-1',
                    name: '代数基础',
                    importance: 2,
                    sector: SectorEnum.tech,
                    isUnlocked: true,
                    masteryScore: 0,
                  ),
                ],
                userFlameIntensity: 0,
              ),
            ),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const GalaxyScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('还没有点亮掌握记录'), findsOneWidget);
    expect(find.text('去学习'), findsOneWidget);
  });

  // G-03 状态面对齐：错误态走人话文案 + SparkleButton 动作（库空态
  // 形制的动作 owner），整块带 liveRegion 语义可读。
  testWidgets('galaxy screen shows aligned error panel with retry action', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FailingEnhancedGalaxyRepository(),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const GalaxyScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('星图加载失败'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
    // 动作 owner 归位 SparkleButton（不再用裸 FilledButton）。
    expect(find.byType(SparkleButton), findsOneWidget);
  });

  // G-03「焦点随相机」×F-3「锚定可感知」：进图后结构锚（importance 最高、
  // 图序稳定）即工作视野锚；用户平移视口、锚节点出视口后，spotlight 锚
  // 重定到新视口内距中心最近的节点。拖拽步数按落位后的真实相机 scale 与
  // 节点位置换算（对力布局收敛漂移鲁棒），缓速 <420px/s 不触发 fling。
  testWidgets('panning the viewport re-anchors spotlight to nearest node', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          enhancedGalaxyRepositoryProvider.overrideWithValue(
            _FakeEnhancedGalaxyRepository(
              graph: GalaxyGraphResponse(
                nodes: <GalaxyNodeModel>[
                  GalaxyNodeModel(
                    id: 'node-a',
                    name: '左节点',
                    importance: 5,
                    sector: SectorEnum.tech,
                    isUnlocked: true,
                    masteryScore: 50,
                    positionX: 0,
                    positionY: 0,
                  ),
                  GalaxyNodeModel(
                    id: 'node-b',
                    name: '右节点',
                    importance: 1,
                    sector: SectorEnum.life,
                    isUnlocked: true,
                    masteryScore: 50,
                    positionX: 1200,
                    positionY: 0,
                  ),
                ],
                userFlameIntensity: 0,
              ),
            ),
          ),
        ],
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const GalaxyScreen(),
        ),
      ),
    );

    // 排干入场编排：入场相机动画（1400ms）+ 构建回放 + 工作视野聚焦
    // 轮询（250ms×40 failsafe = 10s）。ambient ticker 常驻，
    // pumpAndSettle 会超时——全部用定长 pump。
    await tester.pump();
    for (var i = 0; i < 52; i++) {
      await tester.pump(const Duration(milliseconds: 250));
    }

    // 观测缝 getter 挂在私有 State 上，测试侧只能经 dynamic 触达
    //（@visibleForTesting debugSpotlightAnchorId，见 galaxy_screen.dart）。
    final state = tester.state(find.byType(GalaxyScreen)) as dynamic;
    // F-3 起始引导基线：进图后结构锚（importance 5 的 node-a）即当前锚，
    // 用户第一眼有可指认的落点（不再是「诚实无锚」的全图漂泊）。
    // ignore: avoid_dynamic_calls
    expect(state.debugSpotlightAnchorId, 'node-a');

    // 缓速拖拽（<420px/s fling 阈值）：30px/步、每步 100ms = 300px/s。
    // 步数按落位后的真实相机与节点距离换算：把 node-b 拖到视口中心并
    // 越过 4 步，保证 node-a（preferred 锚）确定出视口、锚权交还几何。
    final painter = _starMapPainter(tester);
    final worldPerStep = 30 / painter.camera.scale;
    final anchorX = painter.positions['node-a']!.dx;
    final targetX = painter.positions['node-b']!.dx;
    final steps = ((targetX - anchorX) / worldPerStep).ceil() + 4;
    final center = tester.getCenter(find.byType(GalaxyScreen));
    final gesture = await tester.startGesture(center);
    for (var i = 0; i < steps; i++) {
      await gesture.moveBy(const Offset(-30, 0));
      await tester.pump(const Duration(milliseconds: 100));
    }
    await gesture.up();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // ignore: avoid_dynamic_calls
    expect(state.debugSpotlightAnchorId, 'node-b');
  });
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

/// 图加载恒失败——固化错误态面板（G-03 状态面对齐验收）。
class _FailingEnhancedGalaxyRepository extends EnhancedGalaxyRepository {
  _FailingEnhancedGalaxyRepository() : super(_NoopApiClient());

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async =>
      NetworkResult.failure(GalaxyError.circuitBreakerOpen());

  @override
  Future<NetworkResult<UserGalaxyContribution>> getContributionStats() async =>
      NetworkResult.failure(GalaxyError.circuitBreakerOpen());

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      const Stream<SSEEvent>.empty();
}

class _FakeEnhancedGalaxyRepository extends EnhancedGalaxyRepository {
  _FakeEnhancedGalaxyRepository({
    GalaxyGraphResponse? graph,
  })  : graph = graph ??
            GalaxyGraphResponse(
              nodes: const <GalaxyNodeModel>[],
              userFlameIntensity: 0,
            ),
        super(_NoopApiClient());

  final GalaxyGraphResponse graph;

  @override
  Future<NetworkResult<GalaxyGraphResponse>> getGraph({
    double zoomLevel = 1.0,
    bool forceRefresh = false,
  }) async =>
      NetworkResult.success(graph);

  @override
  Future<NetworkResult<UserGalaxyContribution>> getContributionStats() async =>
      NetworkResult.success(UserGalaxyContribution.empty);

  @override
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      const Stream<SSEEvent>.empty();
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
