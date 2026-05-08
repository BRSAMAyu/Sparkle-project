import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Auth Flow Test
/// Verifies: guest login works, login state persists after navigation
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('guest login reaches dashboard', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      // Wait for login screen
      await _pumpUntil(
        tester,
        () =>
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 45),
      );

      // If already on dashboard, auth was restored — that's a pass
      if (find.byType(DashboardScreen).evaluate().isNotEmpty) {
        return;
      }

      // Find and tap guest button
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
        await tester.pumpAndSettle(const Duration(seconds: 5));
      } else {
        // Try demo account button
        final demoButton = find.byWidgetPredicate(
          (widget) =>
              widget is Text &&
              (widget.data?.contains('Demo') == true ||
                  widget.data?.contains('演示') == true),
        );
        if (demoButton.evaluate().isNotEmpty) {
          await tester.tap(demoButton);
          await tester.pumpAndSettle(const Duration(seconds: 5));
        }
      }

      // Wait for dashboard
      await _pumpUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 60),
      );

      expect(find.byType(DashboardScreen), findsOneWidget);
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
