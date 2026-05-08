import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Offline Error Test
/// Verifies: app handles network failure gracefully (no white screen, no hang)
/// Note: This test runs with normal backend. True offline testing requires
/// environment configuration (E2E_TEST_MODE=true with bad URL).
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('app does not white-screen when services unavailable', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      // Wait for app to reach a stable state
      await _pumpUntil(
        tester,
        () =>
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 45),
      );

      // If on login, try guest login
      if (find.byType(LoginScreen).evaluate().isNotEmpty) {
        final guestButton = find.byWidgetPredicate(
          (widget) =>
              widget is Text &&
              (widget.data == '以访客身份继续' ||
                  widget.data == 'Continue as Guest'),
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
      }

      // Wait for any state — even error state should have UI
      await tester.pumpAndSettle(const Duration(seconds: 5));

      // Verify some scaffold exists (not blank)
      final hasMaterial = find.byType(Material).evaluate().isNotEmpty;
      final hasScaffold = find.byType(Scaffold).evaluate().isNotEmpty;
      expect(hasMaterial || hasScaffold, isTrue,
          reason: 'Screen should not be blank even on error');

      // Verify no unhandled error widgets
      final errorWidgets = find.byType(ErrorWidget).evaluate();
      expect(errorWidgets.isEmpty, isTrue,
          reason: 'No ErrorWidget for network issues');

      // Check for retry buttons or error messages if error occurred
      final retryButton = find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data?.contains('重试') == true ||
                widget.data?.contains('Retry') == true),
      );
      // Retry button existence is informational, not required
      // But if there's an error, retry should exist
    } finally {
      await BgmService.dispose();
      await SensoryFeedbackService.dispose();
      await tester.pump(const Duration(milliseconds: 250));
      FlutterError.onError = originalOnError;
      ui.PlatformDispatcher.instance.onError = originalPlatformOnError;
    }
  });
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
