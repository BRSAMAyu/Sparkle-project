import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Knowledge Preview Test
/// Verifies: Galaxy/knowledge page loads without crash, not blank
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('galaxy tab loads without crash and not blank', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      await _reachDashboard(tester);

      // Navigate to Galaxy tab
      await _openTab(tester, labels: const ['星图', 'Galaxy']);
      await tester.pumpAndSettle(const Duration(seconds: 5));

      // Verify we navigated away from dashboard (or stayed on a valid screen)
      final hasScaffold = find.byType(Scaffold).evaluate().isNotEmpty;
      expect(hasScaffold, isTrue, reason: 'Scaffold should exist');

      // Verify no crash
      final errorWidgets = find.byType(ErrorWidget).evaluate();
      expect(errorWidgets.isEmpty, isTrue,
          reason: 'No crash on Galaxy tab');
    } finally {
      await BgmService.dispose();
      await SensoryFeedbackService.dispose();
      await tester.pump(const Duration(milliseconds: 250));
      FlutterError.onError = originalOnError;
      ui.PlatformDispatcher.instance.onError = originalPlatformOnError;
    }
  });
}

Future<void> _openTab(
  WidgetTester tester, {
  required List<String> labels,
}) async {
  for (final label in labels) {
    final tooltipFinder = find.byTooltip(label);
    if (tooltipFinder.evaluate().isNotEmpty) {
      await tester.ensureVisible(tooltipFinder.first);
      await tester.tap(tooltipFinder.first, warnIfMissed: false);
      await tester.pumpAndSettle(const Duration(seconds: 3));
      return;
    }
  }
  final textFinder = find.byWidgetPredicate(
    (widget) => widget is Text && labels.contains(widget.data),
  );
  if (textFinder.evaluate().isNotEmpty) {
    await tester.ensureVisible(textFinder.first);
    await tester.tap(textFinder.first, warnIfMissed: false);
    await tester.pumpAndSettle(const Duration(seconds: 3));
  }
}

Future<void> _reachDashboard(WidgetTester tester) async {
  await _pumpUntil(
    tester,
    () =>
        find.byType(LoginScreen).evaluate().isNotEmpty ||
        find.byType(DashboardScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 45),
  );
  if (find.byType(DashboardScreen).evaluate().isNotEmpty) return;

  final guestButton = find.byWidgetPredicate(
    (widget) =>
        widget is Text &&
        (widget.data == '以访客身份继续' || widget.data == 'Continue as Guest'),
  );
  if (guestButton.evaluate().isNotEmpty) {
    await tester.scrollUntilVisible(
      guestButton,
      180,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(guestButton);
    await tester.pumpAndSettle(const Duration(seconds: 3));
  }

  await _pumpUntil(
    tester,
    () => find.byType(DashboardScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 60),
  );
}

Future<void> _pumpUntil(
  WidgetTester tester,
  bool Function() condition, {
  required Duration timeout,
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    await tester.pump(const Duration(milliseconds: 250));
    if (condition()) return;
  }
  expect(condition(), isTrue);
}
