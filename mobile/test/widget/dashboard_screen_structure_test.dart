import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';

import '../features/home/dashboard_test_harness.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Dashboard screen structure', () {
    testWidgets('briefing details expand and collapse', (tester) async {
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(buildDashboardTestHarness());
      await _pumpDashboard(tester);

      expect(find.text('Active Plan'), findsNothing);

      final briefingToggle = find.byKey(const ValueKey('dashboard-briefing-toggle'));
      await tester.ensureVisible(briefingToggle);
      await tester.tap(briefingToggle);
      await _pumpDashboard(tester);

      expect(find.text('Active Plan'), findsOneWidget);
    });

    testWidgets('updates section expands to reveal recent insights', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(buildDashboardTestHarness());
      await _pumpDashboard(tester);

      await _scrollToSection(
        tester,
        find.byKey(const ValueKey('dashboard-updates-section')),
      );

      expect(find.text('Weekly learning report'), findsNothing);

      await tester.tap(find.byKey(const ValueKey('dashboard-updates-toggle')));
      await _pumpDashboard(tester);

      expect(find.text('Weekly learning report'), findsOneWidget);
    });

    testWidgets('curated sections stay in fixed vertical order', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(buildDashboardTestHarness());
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
      final taskBoardFinder = find.byKey(
        const ValueKey('dashboard-task-board-section'),
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

      await _scrollToSection(tester, taskBoardFinder);
      final taskBoardOffset = _absoluteTop(
        tester,
        scrollPosition,
        taskBoardFinder,
      );

      expect(briefingOffset, lessThan(updatesOffset));
      expect(updatesOffset, lessThan(workspaceOffset));
      expect(workspaceOffset, lessThan(taskBoardOffset));
    });

    testWidgets('module area keeps secondary customize affordance', (
      tester,
    ) async {
      await initializeDashboardTestEnvironment();
      await tester.pumpWidget(buildDashboardTestHarness());
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
      await tester.pumpWidget(buildDashboardTestHarness());
      await _pumpDashboard(tester);

      expect(find.text('Today Briefing'), findsOneWidget);
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
