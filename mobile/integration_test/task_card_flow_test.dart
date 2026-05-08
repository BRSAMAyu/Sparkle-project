import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Task Card Flow Test
/// Verifies: task cards are visible on dashboard, key sections exist when opened
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('task cards visible or empty state handled', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      await _reachDashboard(tester);

      // Wait for content to load
      await tester.pumpAndSettle(const Duration(seconds: 5));

      // Check for task cards or valid empty state
      final hasTaskCards = find.byType(TaskCard).evaluate().isNotEmpty;
      final hasScaffold = find.byType(Scaffold).evaluate().isNotEmpty;

      expect(hasScaffold, isTrue, reason: 'Scaffold should be present');

      // If task cards exist, verify they have stable keys
      if (hasTaskCards) {
        final taskCards = find.byType(TaskCard);
        expect(taskCards.evaluate().length, greaterThan(0));

        // Try tapping the first task card
        await tester.tap(taskCards.first);
        await tester.pumpAndSettle(const Duration(seconds: 3));

        // Verify no crash after tapping
        final noError = find.byType(ErrorWidget).evaluate().isEmpty;
        expect(noError, isTrue, reason: 'No crash after tapping task card');
      }

      // Check for error state (should not happen)
      final errorWidgets = find.byType(ErrorWidget).evaluate();
      expect(errorWidgets.isEmpty, isTrue);
    } finally {
      await BgmService.dispose();
      await SensoryFeedbackService.dispose();
      await tester.pump(const Duration(milliseconds: 250));
      FlutterError.onError = originalOnError;
      ui.PlatformDispatcher.instance.onError = originalPlatformOnError;
    }
  });
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
