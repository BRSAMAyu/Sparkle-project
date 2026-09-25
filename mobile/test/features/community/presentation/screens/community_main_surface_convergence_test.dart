import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/presentation/screens/community_main_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

/// 卡 S-03（v2）· Squad/Sprint/Check-in 产品表面收敛 —— 社群壳层断言。
///
/// 验收口径（headless）：
/// 1. 四入口（小队/冲刺/今日打卡/成果反馈）在默认首 Tab（群组协作）真实可达，
///    且 Tab 标签顺序与 Tab 内容严格对位。v1 收敛（41d83f83）把 children 排成
///    [Groups, Partners, Feed] 却漏改 tabLabels，造成「首 Tab 挂『伙伴』标签
///    渲染群组内容」的标签/内容错位——本组断言红在基线，修复后锁死；
/// 2. feed 降级断言：公共动态不在首屏/核心位（末位 Tab、协作者 Tab 无发帖
///    FAB），但路径仍可达（末位 Tab → 发帖 FAB → push 落点屏）。
///
/// 打卡/成果反馈/小队列表的真实数据流断言由 groups_hub_view_test.dart 既有
/// 组覆盖（同一 GroupsTab 内容面），此处不造并行真源。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  Future<void> pumpShell(WidgetTester tester, GoRouter router) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          theme: AppThemes.lightTheme.copyWith(
            splashFactory: NoSplash.splashFactory,
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            ...AppLocalizations.localizationsDelegates,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          routerConfig: router,
        ),
      ),
    );
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }

  GoRouter hubRouter() => GoRouter(
        navigatorKey: GlobalKey<NavigatorState>(),
        initialLocation: '/community',
        routes: [
          GoRoute(
            path: '/community',
            builder: (_, __) => const CommunityMainScreen(),
          ),
          GoRoute(
            path: '/community/posts/create',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('发布动态'))),
          ),
          GoRoute(
            path: '/community/squads',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('小队列表'))),
          ),
        ],
      );

  group('CommunityMainScreen S-03 surface convergence (v2)', () {
    testWidgets(
      'tab labels align with tab content: [Groups, Partners, Feed]',
      (tester) async {
        final router = hubRouter();
        addTearDown(router.dispose);
        DemoDataService.isDemoMode = true;
        await pumpShell(tester, router);

        // ① 标签顺序锁：群组协作者首屏（默认 Tab），伙伴次之，
        //    公共动态降级末位。基线红：tabLabels 停在旧顺序
        //    [伙伴, 动态, 群组]——首 Tab 挂「伙伴」标签渲染群组内容。
        final tabTexts = [
          tester.widget<Tab>(find.byType(Tab).at(0)).text,
          tester.widget<Tab>(find.byType(Tab).at(1)).text,
          tester.widget<Tab>(find.byType(Tab).at(2)).text,
        ];
        expect(tabTexts, ['群组', '伙伴', '动态']);

        // ② 默认 Tab（index 0）内容 = 群组协作面：小队入口真实在首屏
        //    （四入口之首的可达性证据；数据流由 hub 测试组覆盖）。
        expect(
          find.byKey(const ValueKey('community-squads-entry')),
          findsOneWidget,
        );
        expect(tester.takeException(), isNull);
      },
    );

    testWidgets(
      'feed is demoted: no FAB on collab tabs, reachable at last tab',
      (tester) async {
        final router = hubRouter();
        addTearDown(router.dispose);
        DemoDataService.isDemoMode = true;
        await pumpShell(tester, router);

        // ① 首屏（群组协作 Tab）不出现发帖 FAB——公共帖子不占首屏。
        expect(find.byIcon(Icons.edit), findsNothing);

        // ② 伙伴 Tab 同样无发帖 FAB。
        await tester.tap(find.byType(Tab).at(1));
        await tester.pump(const Duration(milliseconds: 300));
        await tester.pump(const Duration(milliseconds: 400));
        expect(find.byIcon(Icons.edit), findsNothing);

        // ③ 路径仍可达：末位 Tab（index 2）= 公共动态，FAB 回归。
        //    FAB 出场缩放动画需要足够帧才到满几何（tap 命中前提）。
        await tester.tap(find.byType(Tab).at(2));
        for (var i = 0; i < 12; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(find.byIcon(Icons.edit), findsOneWidget);

        // ④ 发帖入口 push 落点屏真实可达（feed 链路 alive）。
        await tester.tap(find.byIcon(Icons.edit));
        await tester.pumpAndSettle();
        expect(find.text('发布动态'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  });
}
