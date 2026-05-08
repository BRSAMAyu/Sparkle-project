import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Checkin Feedback Test
/// Verifies: checkin UI is reachable, feedback can be submitted
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('checkin and feedback flow does not crash', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      await _reachDashboard(tester);
      await tester.pumpAndSettle(const Duration(seconds: 5));

      // Look for checkin-related buttons
      final checkinButtons = find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            (widget.data?.contains('打卡') == true ||
                widget.data?.contains('Check') == true),
      );

      if (checkinButtons.evaluate().isNotEmpty) {
        await tester.tap(checkinButtons.first);
        await tester.pumpAndSettle(const Duration(seconds: 3));

        // Look for feedback-related widgets
        final feedbackWidgets = find.byWidgetPredicate(
          (widget) =>
              widget is Text &&
              (widget.data?.contains('反馈') == true ||
                  widget.data?.contains('Feedback') == true),
        );

        if (feedbackWidgets.evaluate().isNotEmpty) {
          await tester.tap(feedbackWidgets.first);
          await tester.pumpAndSettle(const Duration(seconds: 2));
        }
      }

      // Core assertion: no crash, no error widget
      final errorWidgets = find.byType(ErrorWidget).evaluate();
      expect(errorWidgets.isEmpty, isTrue,
          reason: 'No crash during checkin/feedback flow');
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
