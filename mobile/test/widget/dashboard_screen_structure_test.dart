import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';

import '../features/home/dashboard_test_harness.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Dashboard screen structure', () {
    testWidgets('briefing details expand and collapse', (tester) async {
      await initializeDashboardTestEnvironment();
      // J-03：dailyBriefing 槽改为默认折叠（首屏唯一主行动卡=Today
      // Cockpit），折叠态下 briefing toggle 不进树；与下方 wt296 用例
      // 同款注入「全展开」基线后再验证展开/折叠行为本身。
      await tester.pumpWidget(
        buildDashboardTestHarness(
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      await _pumpDashboard(tester);

      expect(find.text('Active Plan'), findsNothing);

      final briefingToggle = find.byKey(const ValueKey('dashboard-briefing-toggle'));
      await tester.ensureVisible(briefingToggle);
      await tester.pump();
      await tester.tap(briefingToggle);
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(find.text('Active Plan'), findsOneWidget);
    });

    testWidgets('updates section expands to reveal recent insights', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      // wt296：dashboardUpdates 槽位在折叠系统上线后默认收起，折叠态下
      // section 内容不进树；结构测试注入「全展开」基线。
      await tester.pumpWidget(
        buildDashboardTestHarness(
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      await _pumpDashboard(tester);

      await _scrollToSection(
        tester,
        find.byKey(const ValueKey('dashboard-updates-section')),
      );

      expect(find.byType(RecentInsightsCard), findsNothing);

      await tester.tap(find.byKey(const ValueKey('dashboard-updates-toggle')));
      await _pumpDashboard(tester);

      expect(find.byType(RecentInsightsCard), findsOneWidget);
    });

    testWidgets('curated sections stay in fixed vertical order', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      // wt296：注入「全展开」slot 基线（折叠系统上线后 dashboardUpdates 等槽
      // 默认收起，折叠态下 key 不进树）。
      await tester.pumpWidget(
        buildDashboardTestHarness(
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      await _pumpDashboard(tester);

      final scrollable = find.byType(Scrollable).first;
      final scrollPosition = tester.state<ScrollableState>(scrollable).position;
      final briefingFinder = find.byKey(
        const ValueKey('dashboard-briefing-section'),
      );
      final updatesFinder =
          find.byKey(const ValueKey('dashboard-updates-section'));
      final workspaceFinder = find.byKey(
        const ValueKey('dashboard-workspace-section'),
      );

      final briefingOffset =
          _absoluteTop(tester, scrollPosition, briefingFinder);
      await _scrollToSection(tester, updatesFinder);
      final updatesOffset = _absoluteTop(tester, scrollPosition, updatesFinder);

      await _scrollToSection(tester, workspaceFinder);
      final workspaceOffset = _absoluteTop(
        tester,
        scrollPosition,
        workspaceFinder,
      );

      expect(briefingOffset, lessThan(updatesOffset));
      expect(updatesOffset, lessThan(workspaceOffset));
      // wt296：task_board 槽在本 harness 的静态数据下由产品侧门控不渲染
      // （probe 实测 slot 列表无该 section，见 REPORT），顺序断言收敛到
      // briefing → updates → workspace 三个可达锚点。
    });

    testWidgets('module area keeps secondary customize affordance', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      // J-03：workspaceCards 槽随首屏去竞争默认折叠，section 内容（含
      // customize action）折叠态不进树；注入「全展开」基线后验证 affordance。
      await tester.pumpWidget(
        buildDashboardTestHarness(
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      await _pumpDashboard(tester);

      await _scrollToSection(
        tester,
        find.byKey(const ValueKey('dashboard-workspace-section')),
      );

      expect(
        find.byKey(const ValueKey('dashboard-customize-action')),
        findsOneWidget,
      );
      expect(find.byType(DashboardScreen), findsOneWidget);
    });

    testWidgets('english locale keeps dashboard copy coherent', (tester) async {
      await initializeDashboardTestEnvironment();
      // wt296：注入「全展开」slot 基线；briefing 详情默认折叠后需先展开
      // 才能看到 'Start With This' eyebrow。
      await tester.pumpWidget(
        buildDashboardTestHarness(
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      await _pumpDashboard(tester);

      expect(find.text('Today Briefing'), findsOneWidget);

      final briefingToggle =
          find.byKey(const ValueKey('dashboard-briefing-toggle'));
      await tester.ensureVisible(briefingToggle);
      await tester.pump();
      await tester.tap(briefingToggle);
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(find.text('Start With This'), findsOneWidget);
      expect(find.text('View Tasks'), findsOneWidget);

      await _scrollToSection(
        tester,
        find.byKey(const ValueKey('dashboard-updates-section')),
      );
      await tester.tap(find.byKey(const ValueKey('dashboard-updates-toggle')));
      await _pumpDashboard(tester);

      expect(find.text('System Prediction'), findsOneWidget);
      expect(find.text('Recent Insights'), findsOneWidget);
    });
  });
}

Future<void> _pumpDashboard(WidgetTester tester) async {
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _scrollToSection(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    240,
    scrollable: find.byType(Scrollable).first,
  );
  await _pumpDashboard(tester);
}

double _absoluteTop(
  WidgetTester tester,
  ScrollPosition position,
  Finder finder,
) =>
    position.pixels + tester.getTopLeft(finder).dy;
