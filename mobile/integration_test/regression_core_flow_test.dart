import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;

/// Regression Core Flow Test
/// Full path: launch → login → home → galaxy → chat → community → profile → back
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('core navigation regression: all tabs reachable', (tester) async {
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;

    app.main();

    try {
      await BgmService.setEnabled(false);
      await BgmService.stop();

      // ── Step 1: Launch → reach auth or home ──
      await _pumpUntil(
        tester,
        () =>
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 45),
      );

      // ── Step 2: Login if needed ──
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

      // ── Step 3: Verify dashboard ──
      await _pumpUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 60),
      );
      expect(find.byType(DashboardScreen), findsOneWidget);

      // ── Step 4: Navigate Galaxy tab ──
      await _openTab(tester, labels: const ['星图', 'Galaxy']);
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // ── Step 5: Navigate Chat tab ──
      await _openTab(tester, labels: const ['对话', '聊天', 'Chat']);
      await tester.pumpAndSettle(const Duration(seconds: 3));
      expect(find.byType(ChatScreen), findsOneWidget);

      // ── Step 6: Open chat history sheet ──
      final historyButton = find.byIcon(Icons.history);
      if (historyButton.evaluate().isNotEmpty) {
        await tester.ensureVisible(historyButton.first);
        await tester.tap(historyButton.first);
        await tester.pumpAndSettle(const Duration(seconds: 2));

        // Close it
        final closeButton = find.byIcon(Icons.close_rounded);
        if (closeButton.evaluate().isNotEmpty) {
          await tester.tap(closeButton.first);
          await tester.pumpAndSettle(const Duration(seconds: 2));
        }
      }

      // ── Step 7: Navigate Community tab ──
      await _openTab(tester, labels: const ['社群', 'Community']);
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // ── Step 8: Navigate Profile tab ──
      await _openTab(tester, labels: const ['我的', 'Profile']);
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // ── Step 9: Navigate back Home ──
      await _openTab(tester, labels: const ['驾驶舱', '首页', 'Home']);
      await tester.pumpAndSettle(const Duration(seconds: 3));

      // ── Step 10: Verify we're back on home ──
      expect(find.byType(DashboardScreen), findsOneWidget);

      // ── Final: No crashes anywhere ──
      final errorWidgets = find.byType(ErrorWidget).evaluate();
      expect(errorWidgets.isEmpty, isTrue,
          reason: 'No ErrorWidget in entire core flow');
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
      await tester.pump();
      await _pumpUntil(
        tester,
        () => _currentRoutePath() != null,
        timeout: const Duration(seconds: 10),
      );
      return;
    }
  }
  final textFinder = find.byWidgetPredicate(
    (widget) => widget is Text && labels.contains(widget.data),
  );
  if (textFinder.evaluate().isNotEmpty) {
    await tester.ensureVisible(textFinder.first);
    await tester.tap(textFinder.first, warnIfMissed: false);
    await tester.pump();
  }
}

String? _currentRoutePath() {
  final context = navigatorKey.currentContext;
  if (context == null) return null;
  return GoRouter.of(context).routeInformationProvider.value.uri.path;
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
