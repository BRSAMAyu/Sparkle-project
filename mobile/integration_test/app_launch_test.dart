import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// App Launch Test
/// Verifies: app starts, no crash, core entry point exists
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('app launches without crash and reaches auth or home', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      await _pumpUntil(
        tester,
        () =>
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 45),
      );

      final reachedLogin = find.byType(LoginScreen).evaluate().isNotEmpty;
      final reachedHome = find.byType(DashboardScreen).evaluate().isNotEmpty;

      expect(reachedLogin || reachedHome, isTrue,
          reason: 'App should reach either LoginScreen or DashboardScreen');

      // Check for red screen of death
      final redScreen = find.byType(ColoredBox).evaluate().where((e) {
        final widget = e.widget as ColoredBox;
        return widget.color == const Color(0xFFFF0000);
      });
      expect(redScreen.isEmpty, isTrue, reason: 'No red screen of death');
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
