// V4-G01 · 首页/目标/任务/日历家族 四风格走查 + 确定性语义钉。
//
// 复用既有泵制（不造新采集器）：
// - ThemeManager preview 通道（V4-F01/F05 判例）：freshThemeManager →
//   setPixelPreviewProfile → AppThemes.lightTheme 每次泵制时重估（真实
//   live re-theme 管道，非替身）；
// - dashboard_test_harness（首页 provider 栈 + provider 级状态钉）；
// - u08 证据测试同款日历面 fakes；goal A-6 同款 api stub；portfolio
//   同款假仓储。
//
// 每屏 × classic/paperDay/dusk/quiet 四档：
// - 走查（walk）：真实渲染零异常零溢出（含 200% 文本变体）；
// - 语义钉（pins）：seed 关键文案逐档在场 + 像素档扩展挂载断言
//   （dusk 钉死暗亮度）；CI 可失败（无环境门，普通 `flutter test` 全跑）。
// - 状态面：家族级覆盖 空 / 加载 / 部分 / 失败（≥各一面 × 四档）。
library;

import 'dart:async';

import 'package:confetti/confetti.dart' show ConfettiWidget;
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/auth.dart' show currentUserProvider;
import 'package:sparkle/features/calendar/data/datasources/calendar_remote_datasource.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/data/repositories/calendar_repository.dart';
import 'package:sparkle/features/calendar/presentation/screens/calendar_stats_screen.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_detail_screen.dart';
import 'package:sparkle/features/home/data/repositories/dashboard_repository.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/screens/learning_portfolio_screen.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

import '../../../features/home/dashboard_test_harness.dart';
import '../../../shared/i18n_test_helper.dart';
import 'style_preview_test_harness.dart';

/// 四档循环（classic = preview off 既有发布主题，是发布默认锚点）。
const List<PixelPreviewProfile> kG01Profiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

Future<ThemeManager> _switchProfile(PixelPreviewProfile profile) async {
  final manager = await freshThemeManager();
  if (profile != PixelPreviewProfile.classic) {
    await manager.setPixelPreviewProfile(profile);
  }
  return manager;
}

/// 切档 + 重挂泵制（F05 ValueKey 重挂判例）：结构相同的前后两次
/// pumpWidget 会让 element 原位更新、MaterialApp 内主题陈旧不换——
/// 按 profile 换 Key 强制 remount，保证每档从 AppThemes.lightTheme
/// 现值重建（语义钉「dusk 钉暗亮度」依此成立）。
Future<void> _pumpProfiled(
  WidgetTester tester,
  PixelPreviewProfile profile,
  Widget Function() build,
) async {
  // 先切档、后构建宿主：AppThemes.lightTheme 必须在档位切换后求值
  // （Dart 实参先行求值——收 builder 不收现成 widget，防止主题陈旧）。
  await _switchProfile(profile);
  await tester.pumpWidget(
    KeyedSubtree(
      key: ValueKey('g01-style-${profile.name}'),
      child: build(),
    ),
  );
}

/// 家族屏通用宿主：AppThemes.lightTheme 在泵制时经 ThemeManager 重估
/// （F05 同机制），中文 pinned（与家族既有语义断言同口径）。
Widget g01Host({Widget? child, GoRouter? router}) {
  assert(
    (child != null) != (router != null),
    'g01Host: exactly one of child/router is required',
  );
  final themeData = AppThemes.lightTheme;
  if (router != null) {
    return MaterialApp.router(
      routerConfig: router,
      theme: themeData,
      locale: const Locale('zh'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
  return MaterialApp(
    theme: themeData,
    locale: const Locale('zh'),
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    home: child,
  );
}

GoRouter _portfolioRouter() => GoRouter(
      initialLocation: '/exam-sprint/portfolio',
      routes: [
        GoRoute(
          path: '/exam-sprint/portfolio',
          builder: (context, state) => const LearningPortfolioScreen(),
        ),
      ],
    );

void main() {
  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  group('G01 四风格走查｜首页 dashboard（provider 栈真实泵制）', () {
    testWidgets('内容态 × 四档：零异常零溢出，seed 语义逐档在场', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await initializeDashboardTestEnvironment();
        await _pumpProfiled(
          tester,
          profile,
          () => buildDashboardTestHarness(
            theme: AppThemes.lightTheme,
            extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
          ),
        );
        for (var i = 0; i < 8; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(
          tester.takeException(),
          isNull,
          reason: '$profile 内容态渲染异常',
        );
        await tester.pump(const Duration(seconds: 10));
        // 语义钉：seed 关键文案逐档在场（当前目标 → 下一步的排序锚）。
        // 简报锚（当前目标→下一步的排序锚）：简报区标题 + 「主行动」
        // 摘要行 + 目标上下文（计划名）。headline 全文在折叠段内，展开
        // 交互归既有 dashboard 结构测试；本钉只钉逐档在场的基础语义。
        expect(
          find.textContaining('今日简报'),
          findsWidgets,
          reason: '$profile 语义钉：简报区缺席',
        );
        expect(
          find.textContaining('1 main move'),
          findsWidgets,
          reason: '$profile 语义钉：主行动摘要缺席（下一步锚）',
        );
        expect(
          find.textContaining('Dashboard Polish'),
          findsWidgets,
          reason: '$profile 语义钉：当前目标上下文缺席',
        );
      }
    });

    testWidgets('加载态 × 四档：骨架面零异常（加载覆盖）', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await initializeDashboardTestEnvironment();
        await _pumpProfiled(
          tester,
          profile,
          () => buildDashboardTestHarness(
            theme: AppThemes.lightTheme,
            dashboardState: DashboardState.loading(),
            extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$profile 加载态异常');
        // 冲刷错误/反馈件的延时 Timer，避免用例收尾时报 pending timer。
        await tester.pump(const Duration(seconds: 10));
      }
    });

    testWidgets('部分内容态 × 四档：可选卡缺席不破面（部分覆盖）', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await initializeDashboardTestEnvironment();
        await _pumpProfiled(
          tester,
          profile,
          () => buildDashboardTestHarness(
            theme: AppThemes.lightTheme,
            // sprint / 预测 / what-changed 等可选槽全空 = 部分内容。
            dashboardState: DashboardState(
              weather: WeatherData(type: 'sunny', condition: 'clear'),
              flame: FlameData(
                level: 1,
                brightness: 0.2,
                todayFocusMinutes: 0,
              ),
              sprint: null,
              nextActions: const [],
              cognitive: CognitiveData(status: 'empty'),
            ),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$profile 部分内容态异常');
        await tester.pump(const Duration(seconds: 10));
      }
    });

    testWidgets('失败态 × 四档：错误面零异常（失败覆盖）', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await initializeDashboardTestEnvironment();
        await _pumpProfiled(
          tester,
          profile,
          () => buildDashboardTestHarness(
            theme: AppThemes.lightTheme,
            dashboardState: DashboardState.error('network unavailable'),
            extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));
        expect(tester.takeException(), isNull, reason: '$profile 失败态异常');
        await tester.pump(const Duration(seconds: 10));
      }
    });
  });

  group('G01 四风格走查｜任务列表', () {
    testWidgets('内容态 × 四档：零异常，seed 任务逐档在场', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: ProviderScope(
              overrides: [staticTaskListOverride(_g01SampleTasks())],
              child: const TaskListScreen(),
            ),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 任务列表异常');
        expect(
          find.textContaining('特征值专项练习'),
          findsWidgets,
          reason: '$profile 语义钉：seed 任务标题缺席',
        );
      }
    });

    testWidgets('空态 × 四档：引导空态零异常（空覆盖）', (tester) async {
      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: ProviderScope(
              overrides: [
                staticTaskListOverride(const []),
              ],
              child: const TaskListScreen(),
            ),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 空态异常');
        expect(
          find.text('今天还没有待办事项'),
          findsOneWidget,
          reason: '$profile 语义钉：任务空态引导文案缺席',
        );
      }
    });

    testWidgets('失败态 × 四档：重试面零异常且人话文案（失败覆盖）', (tester) async {
      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: ProviderScope(
              overrides: [
                taskListProvider.overrideWith(
                  (ref) => _FailedTaskNotifier(),
                ),
              ],
              child: const TaskListScreen(),
            ),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 失败态异常');
      }
    });

    testWidgets('200% 文本 × 四档：零溢出，主 CTA 文案完整在场', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => MediaQuery(
            data: const MediaQueryData(textScaler: TextScaler.linear(2.0)),
            child: g01Host(
              child: ProviderScope(
                overrides: [staticTaskListOverride(_g01SampleTasks())],
                child: const TaskListScreen(),
              ),
            ),
          ),
        );
        await settlePreview(tester);
        expect(
          tester.takeException(),
          isNull,
          reason: '$profile 200% 文本异常',
        );
        expect(
          find.textContaining('特征值专项练习'),
          findsWidgets,
          reason: '$profile 200%：任务标题文本缺席（截断/丢弃）',
        );
      }
    });
  });

  group('G01 四风格走查｜目标详情', () {
    testWidgets('内容态 × 四档：零异常，结果标准区 seed 逐档在场', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(780, 1688);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();

      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: ProviderScope(
              overrides: [
                apiClientProvider.overrideWithValue(
                  _G01GoalApiStub(_g01GoalPayload()),
                ),
              ],
              child: const GoalDetailScreen(goalId: 'g01-seed'),
            ),
          ),
        );
        await settlePreview(tester);
        await tester.pump(const Duration(milliseconds: 400));
        expect(tester.takeException(), isNull, reason: '$profile 目标详情异常');
        expect(
          find.textContaining('数据结构期中冲刺'),
          findsWidgets,
          reason: '$profile 语义钉：目标标题缺席',
        );
      }
    });

    testWidgets('失败态 × 四档：goal-detail 拒答不炸面（失败覆盖）', (tester) async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();

      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: ProviderScope(
              overrides: [
                apiClientProvider.overrideWithValue(
                  _G01GoalApiStub(null),
                ),
              ],
              child: const GoalDetailScreen(goalId: 'g01-missing'),
            ),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 目标失败态异常');
      }
    });
  });

  group('G01 四风格走查｜计划（学习档案 + 考试冲刺卡）', () {
    testWidgets('档案内容态 × 四档：零异常，掌握度药丸逐档在场', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(1800, 3600);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      for (final profile in kG01Profiles) {
        final router = _portfolioRouter();
        addTearDown(router.dispose);
        await _pumpProfiled(
          tester,
          profile,
          () => ProviderScope(
            overrides: [
              examSprintRepositoryProvider.overrideWithValue(
                _G01PortfolioRepo(result: _g01Portfolio()),
              ),
              currentUserProvider.overrideWithValue(_g01User()),
              userRepositoryProvider.overrideWithValue(
                _G01NoServerUserRepository(),
              ),
            ],
            child: g01Host(router: router),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 档案内容态异常');
        expect(
          find.textContaining('操作系统'),
          findsWidgets,
          reason: '$profile 语义钉：档案条目科目缺席',
        );
        expect(
          find.textContaining('18%'),
          findsWidgets,
          reason: '$profile 语义钉：掌握度药丸缺席',
        );
      }
    });

    testWidgets('档案空/加载/失败 × 四档：三态零异常（空/加载/失败覆盖）', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(1800, 3600);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      Future<void> pumpVariant(
        PixelPreviewProfile profile,
        _G01PortfolioRepo repo,
      ) async {
        final router = _portfolioRouter();
        addTearDown(router.dispose);
        await _pumpProfiled(
          tester,
          profile,
          () => ProviderScope(
            overrides: [
              examSprintRepositoryProvider.overrideWithValue(repo),
              currentUserProvider.overrideWithValue(_g01User()),
              userRepositoryProvider.overrideWithValue(
                _G01NoServerUserRepository(),
              ),
            ],
            child: g01Host(router: router),
          ),
        );
        await settlePreview(tester);
      }

      for (final profile in kG01Profiles) {
        // 空。
        await pumpVariant(
          profile,
          _G01PortfolioRepo(
            result: const LearningPortfolioResult(
              entries: [],
              totalMasteredNodes: 0,
              activeCount: 0,
              completedCount: 0,
              plannedCount: 0,
            ),
          ),
        );
        expect(tester.takeException(), isNull, reason: '$profile 档案空态异常');
        expect(
          find.textContaining('还没有任何冲刺记录'),
          findsOneWidget,
          reason: '$profile 语义钉：档案空态文案缺席',
        );

        // 加载（永不完成的 future → 骨架面）。
        final pending = Completer<LearningPortfolioResult>();
        await pumpVariant(
          profile,
          _G01PortfolioRepo(pendingFuture: pending.future),
        );
        expect(tester.takeException(), isNull, reason: '$profile 档案加载态异常');
        pending.complete(_g01Portfolio());
        await settlePreview(tester);

        // 失败。
        await pumpVariant(
          profile,
          _G01PortfolioRepo(
            handler: () async => throw Exception('portfolio 500'),
          ),
        );
        await settlePreview(tester);
        expect(tester.takeException(), isNull, reason: '$profile 档案失败态异常');
        expect(
          find.textContaining('portfolio 500'),
          findsAtLeastNWidgets(1),
          reason: '$profile 语义钉：档案失败态错误信息缺席',
        );
      }
    });

    testWidgets('考试冲刺卡 × 四档：剩余天数语义逐档在场', (tester) async {
      for (final profile in kG01Profiles) {
        await _pumpProfiled(
          tester,
          profile,
          () => g01Host(
            child: SingleChildScrollView(
              child: ExamSprintDashboardCard(data: _g01ExamPayload()),
            ),
          ),
        );
        await tester.pump();
        await tester.pumpAndSettle(const Duration(milliseconds: 1200));
        expect(tester.takeException(), isNull, reason: '$profile 冲刺卡异常');
        expect(
          find.text('还有 5 天'),
          findsOneWidget,
          reason: '$profile 语义钉：冲刺剩余天数缺席',
        );
      }
    });
  });

  group('G01 四风格走查｜日历（密集信息可读性面）', () {
    testWidgets('内容态 × 四档：月历+agenda 零异常，改期按钮逐档在场', (tester) async {
      tester.view.devicePixelRatio = 3.0;
      tester.view.physicalSize = const Size(1170, 2100);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      TestWidgetsFlutterBinding.ensureInitialized()
          .defaultBinaryMessenger
          .setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      );

      for (final profile in kG01Profiles) {
        final container = ProviderContainer(
          overrides: [
            apiClientProvider.overrideWithValue(_G01SilentApiClient()),
            taskRepositoryProvider.overrideWithValue(
              _G01CalendarTaskRepository(),
            ),
            calendarRepositoryProvider.overrideWithValue(
              _G01CalendarRepository(),
            ),
            taskNotificationSchedulerProvider.overrideWithValue(
              _G01StubScheduler(),
            ),
            dashboardProvider.overrideWith(_G01StaticDashboardNotifier.new),
            planListProvider.overrideWith(_G01StaticPlanNotifier.new),
          ],
        );
        addTearDown(container.dispose);
        await _pumpProfiled(
          tester,
          profile,
          () => UncontrolledProviderScope(
            container: container,
            child: g01Host(child: const Scaffold(body: CalendarStatsScreen())),
          ),
        );
        await tester.pump();
        for (var i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(tester.takeException(), isNull, reason: '$profile 日历面异常');
        expect(
          find.byKey(const ValueKey('calendar-reschedule-task-open')),
          findsOneWidget,
          reason: '$profile 语义钉：日历待办改期按钮（拖拽替代）缺席',
        );
      }
    });
  });

  group('G01 语义钉｜像素档挂载与亮度合同', () {
    testWidgets('paperDay/quiet 钉浅亮度、dusk 钉暗亮度、classic 无像素扩展',
        (tester) async {
      await _pumpProfiled(
          tester,
          PixelPreviewProfile.classic,
          () => g01Host(child: const Scaffold()),
        );
      expect(
        Theme.of(
          tester.element(find.byType(Scaffold).first),
        ).extension<PixelProfileTheme>(),
        isNull,
        reason: 'classic（preview off）不得携带像素扩展（发布面零差量）',
      );

      for (final entry in <PixelPreviewProfile, Brightness>{
        PixelPreviewProfile.paperDay: Brightness.light,
        PixelPreviewProfile.quiet: Brightness.light,
        PixelPreviewProfile.dusk: Brightness.dark,
      }.entries) {
        await _pumpProfiled(
          tester,
          entry.key,
          () => g01Host(child: const Scaffold()),
        );
        final theme = Theme.of(
          tester.element(find.byType(Scaffold).first),
        );
        expect(
          theme.extension<PixelProfileTheme>()?.profile,
          entry.key,
          reason: '${entry.key} 像素扩展未挂载',
        );
        expect(
          theme.brightness,
          entry.value,
          reason: '${entry.key} 亮度钉死失效',
        );
      }
    });

    testWidgets('reduce-motion：纸屑视觉层静态缺席，child 与生命周期保持',
        (tester) async {
      await _pumpProfiled(
          tester,
          PixelPreviewProfile.classic,
          () => MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: g01Host(
            child: const SparkleConfetti(
              play: true,
              intensity: SparkleCelebrationIntensity.small,
              enableSensory: false,
              child: Text('celebration-card'),
            ),
          ),
        ),
        );
      await settlePreview(tester);
      expect(tester.takeException(), isNull);
      expect(find.text('celebration-card'), findsOneWidget);
      // 静态分支钉：纸屑渲染件不在树中（静止终态=已落出屏）。
      expect(
        find.byType(ConfettiWidget),
        findsNothing,
        reason: 'reduce-motion 下纸屑视觉层必须缺席（静态终态等价）',
      );
    });

    testWidgets('常规路径：纸屑渲染件在场（探针有判别力）', (tester) async {
      await _pumpProfiled(
          tester,
          PixelPreviewProfile.classic,
          () => g01Host(
          child: const SparkleConfetti(
            play: true,
            intensity: SparkleCelebrationIntensity.small,
            enableSensory: false,
            child: Text('celebration-card'),
          ),
        ),
        );
      await settlePreview(tester);
      expect(tester.takeException(), isNull);
      expect(
        find.byType(ConfettiWidget),
        findsOneWidget,
        reason: '常规路径纸屑渲染件必须在场（控制组证明静态分支有判别力）',
      );
    });
  });
}

// ---------------------------------------------------------------------------
// seed 数据（家族四档共用，确定性）。
// ---------------------------------------------------------------------------

List<TaskModel> _g01SampleTasks() {
  final now = DateTime(2026, 4, 8, 9);
  return [
    TaskModel(
      id: 'g01-task-1',
      userId: 'user-1',
      title: '特征值专项练习',
      type: TaskType.learning,
      tags: const ['线性代数'],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.pending,
      priority: 1,
      createdAt: now,
      updatedAt: now,
      dueDate: now,
    ),
  ];
}

Map<String, dynamic> _g01GoalPayload() => <String, dynamic>{
      'goal': <String, dynamic>{
        'id': 'g01-seed',
        'title': '数据结构期中冲刺',
        'goal_type': 'exam',
        'status': 'active',
        'target_date': '2026-05-20T00:00:00.000Z',
        'mastery': 0.42,
        'progress': 0.6,
        'priority': 'high',
      },
      'minimum_acceptance_criteria': <String, dynamic>{},
      'plan_health': <String, dynamic>{},
      'current_phase': <String, dynamic>{},
      'todays_minimal_next_step': <String, dynamic>{},
      'knowledge_bottlenecks': <dynamic>[],
      'accountability_status': <String, dynamic>{},
      'related_sources': <dynamic>[],
    };

LearningPortfolioResult _g01Portfolio() => LearningPortfolioResult(
      totalMasteredNodes: 18,
      activeCount: 1,
      completedCount: 0,
      plannedCount: 0,
      entries: <LearningPortfolioEntry>[
        LearningPortfolioEntry(
          planId: 'g01-plan-active',
          planName: '14天操作系统冲刺',
          subject: '操作系统',
          sprintMode: 'fourteen_day_build_and_retrieve',
          status: 'active',
          masteredNodesCount: 18,
          startedAt: DateTime(2026, 4, 17, 9),
          targetDate: DateTime(2026, 4, 30),
          progress: 0.3,
          headline: '进行到第 4 天，还剩 10 天。',
          weakestPoints: const <String>['死锁'],
          proudNodes: const <String>['完成 4 / 14 天'],
        ),
      ],
    );

UserModel _g01User() {
  final now = DateTime(2026, 4, 25, 9);
  return UserModel(
    id: 'user-1',
    username: 'g01-tester',
    email: 'g01@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    createdAt: now,
    updatedAt: now,
  );
}

ExamSprintDashboardData _g01ExamPayload() => const ExamSprintDashboardData(
      planId: 'g01-plan-sprint',
      planName: '操作系统期末冲刺',
      subject: 'Operating Systems',
      daysLeft: 5,
      targetMode: 'pass',
      todayProgress: ExamSprintTodayProgress(
        completed: 2,
        total: 3,
        completionRate: 0.667,
      ),
      highFreqCoverage: 0.75,
      highFreqCoveredCount: 15,
      highFreqTotalCount: 20,
      mistakeFixRate: 0.6,
      fixedMistakeCount: 6,
      totalMistakeCount: 10,
      streakDays: 3,
      taskGroups: [],
    );

// ---------------------------------------------------------------------------
// fakes（各家族既有测试同款最小桩）。
// ---------------------------------------------------------------------------

class _FailedTaskNotifier extends TaskNotifier {
  _FailedTaskNotifier()
      : super(
          _G01NoopTaskRepository(),
          _G01StubScheduler(),
          _G01UnusedRef(),
        ) {
    state = TaskListState(error: UiErrorCategory.server);
  }

  @override
  Future<void> loadTasks({TaskFilter? filter}) async {}

  @override
  Future<void> loadTodayTasks() async {}

  @override
  Future<void> loadRecommendedTasks() async {}

  @override
  Future<void> refreshTasks() async {}
}

class _G01GoalApiStub implements ApiClient {
  _G01GoalApiStub(this.goalDetailPayload);

  final Map<String, dynamic>? goalDetailPayload;

  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    if (goalDetailPayload != null && path.contains('/experience/goal-detail/')) {
      return Response<T>(
        data: goalDetailPayload as T?,
        requestOptions: RequestOptions(path: path),
      );
    }
    throw UnimplementedError('Not stubbed: $path');
  }

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? headers,
    Map<String, dynamic>? queryParameters,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  Response<T> _empty<T>(String path) => Response<T>(
        statusCode: 404,
        requestOptions: RequestOptions(path: path),
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _G01PortfolioRepo extends ExamSprintRepository {
  _G01PortfolioRepo({
    LearningPortfolioResult? result,
    Future<LearningPortfolioResult> Function()? handler,
    Future<LearningPortfolioResult>? pendingFuture,
  })  : _result = result,
        _handler = handler,
        _pending = pendingFuture,
        super(_G01NoopApiClient());

  final LearningPortfolioResult? _result;
  final Future<LearningPortfolioResult> Function()? _handler;
  final Future<LearningPortfolioResult>? _pending;

  @override
  Future<LearningPortfolioResult> fetchLearningPortfolio({
    String? userId,
    int page = 1,
    int pageSize = 20,
  }) async {
    final pending = _pending;
    if (pending != null) {
      return pending;
    }
    final handler = _handler;
    if (handler != null) {
      return handler();
    }
    final result = _result;
    if (result != null) {
      return result;
    }
    throw StateError('g01 portfolio repo: no result configured');
  }
}

class _G01NoServerUserRepository extends UserRepository {
  _G01NoServerUserRepository() : super(_G01NoopApiClient());

  @override
  Future<Map<String, dynamic>> fetchUserSettings() async =>
      const <String, dynamic>{};

  @override
  Future<void> updateUserSettings(Map<String, dynamic> payload) async {}
}

class _G01SilentApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  Response<T> _empty<T>(String path) => Response<T>(
        statusCode: 200,
        data: <String, dynamic>{} as T,
        requestOptions: RequestOptions(path: path),
      );

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _empty<T>(path);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _G01CalendarTaskRepository extends TaskRepository {
  _G01CalendarTaskRepository() : super(_G01NoopApiClient());

  final DateTime today = DateTime.now();

  TaskModel _task(String id, TaskStatus status) => TaskModel(
        id: id,
        userId: 'user-1',
        title: id == 'task-open' ? '未完成任务：算法错题重练' : '已完成任务：英语听力',
        type: TaskType.learning,
        tags: const [],
        estimatedMinutes: 30,
        difficulty: 2,
        energyCost: 1,
        priority: 1,
        status: status,
        createdAt: DateTime(2026),
        updatedAt: DateTime(2026),
        dueDate: DateTime(today.year, today.month, today.day),
      );

  @override
  Future<PaginatedResponse<TaskModel>> getTasks({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      PaginatedResponse<TaskModel>(
        items: [
          _task('task-open', TaskStatus.pending),
          _task('task-done', TaskStatus.completed),
        ],
        total: 2,
        page: 1,
        pageSize: pageSize,
      );

  @override
  Future<CacheAwareResult<PaginatedResponse<TaskModel>>> getTasksCached({
    Map<String, dynamic>? filters,
    int page = 1,
    int pageSize = 50,
  }) async =>
      CacheAwareResult<PaginatedResponse<TaskModel>>(
        PaginatedResponse<TaskModel>(
          items: [
            _task('task-open', TaskStatus.pending),
            _task('task-done', TaskStatus.completed),
          ],
          total: 2,
          page: 1,
          pageSize: pageSize,
        ),
      );

  @override
  Future<CacheAwareResult<List<TaskModel>>> getTodayTasksCached() async =>
      const CacheAwareResult<List<TaskModel>>(<TaskModel>[]);

  @override
  Future<List<TaskModel>> getRecommendedTasks({int limit = 5}) async =>
      <TaskModel>[];

  @override
  Future<List<TaskModel>> getTasksByDateRange(
    DateTime start,
    DateTime end,
  ) async =>
      [
        _task('task-open', TaskStatus.pending),
        _task('task-done', TaskStatus.completed),
      ];
}

class _G01CalendarRepository extends CalendarRepository {
  _G01CalendarRepository()
      : super(
          NotificationService(_G01UnusedRef(), autoInitialize: false),
          CalendarRemoteDataSource(_G01NoopApiClient()),
        );

  @override
  Future<List<CalendarEventModel>> getEvents({
    DateTime? startDate,
    DateTime? endDate,
    bool forceRemote = false,
  }) async =>
      const <CalendarEventModel>[];

  @override
  Future<CalendarEventModel?> syncTaskLinkedEvent(TaskModel task) async => null;

  @override
  Future<void> removeTaskLinkedEvent(String taskId) async {}
}

class _G01StubScheduler extends TaskNotificationScheduler {
  _G01StubScheduler()
      : super(
          NotificationService(_G01UnusedRef(), autoInitialize: false),
          TaskNotificationIdMapper(),
        );

  @override
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      const <int>[];

  @override
  Future<List<int>> rescheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async =>
      const <int>[];

  @override
  Future<void> cancelTaskReminders(String taskId) async {}
}

class _G01StaticDashboardNotifier extends DashboardNotifier {
  _G01StaticDashboardNotifier(Ref _) : super(_G01UnusedDashboardRepo());

  @override
  Future<void> fetchData() async {}
}

class _G01UnusedDashboardRepo extends DashboardRepository {
  _G01UnusedDashboardRepo() : super(_G01NoopApiClient());
}

class _G01StaticPlanNotifier extends PlanNotifier {
  _G01StaticPlanNotifier(Ref ref) : super(_G01UnusedPlanRepo(), ref);

  @override
  Future<void> loadPlans({PlanType? type}) async {}

  @override
  Future<void> loadActivePlans() async {}
}

class _G01UnusedPlanRepo extends PlanRepository {
  _G01UnusedPlanRepo() : super(_G01NoopApiClient());
}

class _G01NoopTaskRepository extends TaskRepository {
  _G01NoopTaskRepository() : super(_G01NoopApiClient());
}

class _G01NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _G01UnusedRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}
