import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/data/episode_resume_models.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/today_cockpit_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

import '../../../../shared/i18n_test_helper.dart';
import '../../dashboard_test_harness.dart';

/// V4-U01 · 首页接续 × 第一主动作集成验收（cockpit 卡内组合面）。
///
/// 三条卡面验收的可失败断言（每面一正一反）：
/// 1. 接续面：新鲜视图 → 「上次/下一步」如实可见，主 CTA 收敛「继续这一步」
///    且全卡唯一 primary（无竞争 CTA）；stale → 只说明不接续，CTA 照旧；
/// 2. 零假历史：回执 off / 视图降级 → 接续条缺席，无任何占位历史文案；
/// 3. 退出重进：零自动导航、零成就重播、纯静态内容可复现。

/// I01 端点桩（Dart 库级私有 → 本文件独立一份；getStream 给空流供 chat 链）。
class _StubApiClient implements ApiClient {
  _StubApiClient(this.response);

  Object? response;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      Response<T>(
        requestOptions: RequestOptions(path: path),
        data: response as T,
      );

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  // chat 链构建期读 dio（ChatRepository 构造）；给裸实例，零真实网络。
  @override
  Dio get dio => Dio();

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('stub only implements get');
}

Map<String, dynamic> _receiptPayload() => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_U01TEST',
        'selection_role': 'resume_view',
        'decision_id': null,
        'input_versions': {
          'memory_epoch': 3,
          'selector_version': 'context_pack.v4-i06.v1',
        },
        'candidates': <Map<String, dynamic>>[
          {'ref': 'task://t1', 'status': 'selected', 'reason_code': null, 'note': null},
        ],
        'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
        'why_now': null,
      },
      'source_verification': <Map<String, dynamic>>[],
      'resolved_selected_count': 1,
    };

Map<String, dynamic> _resumeViewPayload({String expiresAt = '2099-01-01T00:00:00'}) =>
    {
      'view': {
        'schema_version': 'episode_resume_view.v1',
        'goal_ref': 'goal://g1',
        'task_ref': 'task://t1',
        'run_ref': null,
        'last_valid_outcome': null,
        'last_confirmed_step': {
          'step_ref': 'subtask://s1',
          'description': '读完第三章前两节',
          'confirmed_at': '2026-09-28T10:05:00',
          'version_token': 'tok-1',
        },
        'pending_human_step': {
          'description': '做第三章末尾的三道练习题',
          'cognitive_ownership': 'user_led',
          'execution_mode': 'assisted',
        },
        'why_now': null,
        'expires_at': expiresAt,
        'freshness': {
          'context_receipt_ref': 'context_selection://csr_U01TEST',
          'computed_at': '2026-09-28T12:00:00',
          'memory_epoch_at_compute': 3,
        },
      },
      'reason_code': null,
      'warnings': <String>[],
    };

/// 消费端解析锚：合法视图可解析（字段级降级契约在 models 单测钉死）。
final EpisodeResumeViewData? kParsedViewAnchor =
    EpisodeResumeViewData.tryParse(_resumeViewPayload()['view'] as Map<String, dynamic>);

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  ActiveGoalSnapshot goal(String title) => ActiveGoalSnapshot(
        id: 'goal-1',
        title: title,
        goalType: 'exam',
        healthScore: 0.7,
        weeklyConflictCount: 0,
      );

  HomeGrowthState growthWithTask() => const HomeGrowthState(
        planHealth: 0.8,
        tasksTotal: 3,
        tasksCompleted: 0,
        streak: 0,
        activePlan: HomeActivePlanStatus(
          id: 'plan-1',
          name: 'Final Sprint',
          healthScore: 0.8,
        ),
        nextAction: HomeGrowthTask(
          id: 't1',
          title: 'Read chapter 3',
          priority: 4,
          isCompleted: false,
        ),
      );

  /// 接续链 override（goals + 回执读面 + I01 端点 + today 选择流）。
  List<Override> resumeOverrides({
    Object? receiptPayload,
    Object? resumePayload,
    HomeGrowthState? growthState,
  }) =>
      [
        multiGoalOverviewProvider.overrideWith(
          (ref) async => MultiGoalOverview(
            goals: [goal('Pass the exam')],
            selectedGoalId: 'goal-1',
          ),
        ),
        homeGrowthStateProvider.overrideWith(
          (ref) async => growthState ?? growthWithTask(),
        ),
        // 与默认工厂同构：创建即 load（异步落 ready 态）。
        contextReceiptProvider.overrideWith(
          (ref) {
            final notifier = ContextReceiptNotifier(
              _StubApiClient(receiptPayload ?? _receiptPayload()),
            );
            unawaited(notifier.load());
            return notifier;
          },
        ),
        apiClientProvider.overrideWithValue(
          _StubApiClient(resumePayload ?? _resumeViewPayload()),
        ),
      ];

  Future<void> pumpCockpit(
    WidgetTester tester, {
    Object? receiptPayload,
    Object? resumePayload,
    HomeGrowthState? growthState,
  }) async {
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(buildDashboardWidgetHarness(
      child: const TodayCockpitCard(),
      extraOverrides: resumeOverrides(
        receiptPayload: receiptPayload,
        resumePayload: resumePayload,
        growthState: growthState,
      ),
    ),);
    // 回执读面 load（异步）→ episodeResumeProvider 重算 → 视图渲染。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pumpAndSettle();
  }

  /// 主 CTA 可见标签（唯一 primary 按钮内文本）。
  List<String> primaryLabels(WidgetTester tester) => tester
      .widgetList<SparkleButton>(find.byType(SparkleButton))
      .where((button) => button.variant == ButtonVariant.primary)
      .map((b) => b.label)
      .toList();

  group('U01 验收1 · 接续面与唯一主行动', () {
    testWidgets('正：新鲜视图 → 上次/下一步如实可见，主 CTA 收敛「继续这一步」且全卡唯一 primary',
        (tester) async {
      await pumpCockpit(tester);

      expect(kParsedViewAnchor, isNotNull);
      expect(find.byKey(const ValueKey('episode-resume-strip')), findsOneWidget);
      expect(find.text('Last time: 读完第三章前两节'), findsOneWidget);
      expect(find.text('Next: 做第三章末尾的三道练习题'), findsOneWidget);
      // 主 CTA 收敛 + 全卡唯一 primary（无竞争 CTA）。
      expect(primaryLabels(tester), ['Continue this step']);
    });

    testWidgets('反：stale 视图 → 只出现过期说明，无上次/下一步内容，主 CTA 照旧「先做这个」',
        (tester) async {
      await pumpCockpit(
        tester,
        resumePayload: _resumeViewPayload(expiresAt: '2020-01-01T00:00:00'),
      );

      expect(
        find.byKey(const ValueKey('episode-resume-stale-line')),
        findsOneWidget,
      );
      expect(
        find.text(
          'Your last progress info may be out of date — recalibrate in the '
          'task before continuing',
        ),
        findsOneWidget,
      );
      // 过期内容零渲染（B05 §9：过期视图不接续）。
      expect(find.text('Last time: 读完第三章前两节'), findsNothing);
      expect(find.text('Next: 做第三章末尾的三道练习题'), findsNothing);
      // 主 CTA 不被 stale 视图改写（先做这个 = 既有 fresh 态行为）。
      expect(primaryLabels(tester), ['Start Here']);
    });

    testWidgets('正（续）：继续 CTA 点击 → 落在既有任务链路（同一目标，只改标签不改跳转）',
        (tester) async {
      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => const Scaffold(
              body: SingleChildScrollView(child: TodayCockpitCard()),
            ),
          ),
          GoRoute(
            path: '/tasks/:id',
            builder: (context, state) =>
                Scaffold(body: Text('U01-TASKS-${state.pathParameters['id']}')),
          ),
        ],
      );
      await initializeDashboardTestEnvironment();
      // a11y_u08 同款：VM 钉 fresh/startTask（真实派生逻辑已在 cockpit 单测覆盖），
      // 接续链（回执/端点/growth）走真实 provider 桩；chatProvider 不被触达。
      await tester.pumpWidget(ProviderScope(
        overrides: [
          todayCockpitProvider.overrideWithValue(
            const TodayCockpitVm(
              mode: TodayCockpitMode.fresh,
              action: TodayCockpitAction.startTask,
              taskToStart: HomeGrowthTask(
                id: 't1',
                title: 'Read chapter 3',
                priority: 4,
                isCompleted: false,
              ),
            ),
          ),
          ...resumeOverrides(),
        ],
        child: testMaterialApp(routerConfig: router),
      ),);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pumpAndSettle();

      // testMaterialApp 锁 zh locale：收敛标签为中文。
      expect(find.text('继续这一步'), findsOneWidget);
      await tester.tap(find.text('继续这一步'));
      await tester.pumpAndSettle();

      // 与原 dashboard _startNextAction 相同的跳转目标（taskModel 缺省 →
      // /tasks/{id}），接续只是主 CTA 的标签收敛，不另建通道。
      expect(find.text('U01-TASKS-t1'), findsOneWidget);
    });
  });

  group('U01 验收2 · 新用户零假历史', () {
    testWidgets('反：回执读面 off（modeGated）→ 接续条缺席，零占位历史文案，cockpit 行为照旧',
        (tester) async {
      await pumpCockpit(
        tester,
        receiptPayload: {
          'mode': 'off',
          'schema_version': 'context_selection_receipt.v1',
          'receipt': null,
        },
      );

      expect(find.byKey(const ValueKey('episode-resume-strip')), findsNothing);
      expect(find.byKey(const ValueKey('episode-resume-stale-line')), findsNothing);
      // 零假历史：无任何「上次/下一步/过期」占位渲染。
      expect(find.textContaining('Last time:'), findsNothing);
      expect(find.textContaining('Next:'), findsNothing);
      // cockpit 主行动与既有基线完全一致。
      expect(primaryLabels(tester), ['Start Here']);
    });

    testWidgets('反：视图端点降级（view=null）→ 同样缺席（不渲染半真视图）', (tester) async {
      await pumpCockpit(
        tester,
        resumePayload: {
          'view': null,
          'reason_code': 'goal_changed_requires_calibration',
          'warnings': <String>[],
        },
      );

      expect(find.byKey(const ValueKey('episode-resume-strip')), findsNothing);
      expect(find.textContaining('Last time:'), findsNothing);
    });
  });

  group('U01 验收3 · 退出/重进零自动播放、零重播成就', () {
    testWidgets('正：卸载重挂（等价退出重进）→ 零额外导航、零 dialog/snackbar，内容纯静态可复现',
        (tester) async {
      await pumpCockpit(tester);
      expect(find.byKey(const ValueKey('episode-resume-strip')), findsOneWidget);

      // 退出：卸载整树。
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();
      // 重进：同数据重挂。
      await pumpCockpit(tester);

      // 无自动导航（仍在 cockpit 面上）；
      expect(find.byType(TodayCockpitCard), findsOneWidget);
      // 无成就/播放类表面（dialog / snackbar 零出现）。
      expect(find.byType(Dialog), findsNothing);
      expect(find.byType(SnackBar), findsNothing);
      // 内容纯静态复现：同一「上次/下一步」事实。
      expect(find.text('Last time: 读完第三章前两节'), findsOneWidget);
      expect(find.text('Next: 做第三章末尾的三道练习题'), findsOneWidget);
      // 零进行中动画帧（无 auto-play 遗留）。
      expect(tester.binding.transientCallbackCount, 0);
      expect(tester.takeException(), isNull);
    });
  });

  group('U01 验收1（续） · 360 宽首屏主 CTA 不靠滚动', () {
    testWidgets('360×800 整屏装载：接续条在场时主 CTA 仍在首屏视口内可点', (tester) async {
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(
        buildDashboardTestHarness(
          size: const Size(360, 800),
          extraOverrides: resumeOverrides(),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pumpAndSettle();

      // 接续证据条在场（新鲜视图）；
      expect(find.byKey(const ValueKey('episode-resume-strip')), findsOneWidget);
      // 主 CTA 渲染且完整落在首屏（无需滚动即可见）；
      final ctaRect = tester.getRect(
        find.byKey(const ValueKey('today-cockpit-primary-cta')),
      );
      expect(ctaRect.bottom, lessThanOrEqualTo(800));
      expect(ctaRect.top, greaterThanOrEqualTo(0));
      // 命中测试通过（不被遮挡、可点）。
      await tester.ensureVisible(
        find.byKey(const ValueKey('today-cockpit-primary-cta')),
      );
      expect(
        tester.getRect(find.byKey(const ValueKey('today-cockpit-primary-cta'))).bottom,
        lessThanOrEqualTo(800),
      );
      expect(tester.takeException(), isNull);
    });
  });
}
