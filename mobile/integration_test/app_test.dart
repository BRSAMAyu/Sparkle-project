import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'dart:ui' as ui;
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('guest can enter app and open core shell chains', (tester) async {
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
        timeout: const Duration(seconds: 35),
      );

      if (find.byType(LoginScreen).evaluate().isNotEmpty) {
        final guestButton = find.byWidgetPredicate(
          (widget) =>
              widget is Text &&
              (widget.data == '以访客身份继续' || widget.data == 'Continue as Guest'),
        );
        await tester.scrollUntilVisible(
          guestButton,
          180,
          scrollable: find.byType(Scrollable).first,
        );
        await tester.tap(guestButton);
        await tester.pump();
      }

      await _pumpUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 60),
      );

      expect(find.byType(DashboardScreen), findsOneWidget);

      await _openTab(
        tester,
        labels: const ['星图', 'Galaxy'],
        expectedPath: '/galaxy',
      );
      await _openTab(
        tester,
        labels: const ['对话', '聊天', 'Chat'],
        expectedPath: '/chat',
      );
      expect(find.byType(ChatScreen), findsOneWidget);
      await _openChatHistorySheet(tester);
      await _openTab(
        tester,
        labels: const ['社群', 'Community'],
        expectedPath: '/community',
      );
      await _openTab(
        tester,
        labels: const ['我的', 'Profile'],
        expectedPath: '/profile',
      );
      await _openTab(
        tester,
        labels: const ['驾驶舱', '首页', 'Home'],
        expectedPath: '/home',
      );
    } finally {
      await BgmService.dispose();
      await SensoryFeedbackService.dispose();
      await tester.pump(const Duration(milliseconds: 250));
      FlutterError.onError = originalOnError;
      ui.PlatformDispatcher.instance.onError = originalPlatformOnError;
    }
  });
}

Future<void> _openChatHistorySheet(WidgetTester tester) async {
  final historyButton = find.byIcon(Icons.history);
  expect(historyButton, findsOneWidget);
  await tester.ensureVisible(historyButton);
  await tester.tap(historyButton);
  await tester.pump();
  await _pumpUntil(
    tester,
    () =>
        find.text('历史对话').evaluate().isNotEmpty ||
        find.text('Chat History').evaluate().isNotEmpty,
    timeout: const Duration(seconds: 20),
  );

  final closeButton = find.byIcon(Icons.close_rounded);
  expect(closeButton, findsOneWidget);
  await tester.tap(closeButton.first);
  await tester.pump();
  await _pumpUntil(
    tester,
    () =>
        find.text('历史对话').evaluate().isEmpty &&
        find.text('Chat History').evaluate().isEmpty,
    timeout: const Duration(seconds: 10),
  );
}

Future<void> _openTab(
  WidgetTester tester, {
  required List<String> labels,
  required String expectedPath,
}) async {
  final destination = _findNavDestination(labels);
  await tester.ensureVisible(destination.first);
  await tester.tap(destination.first, warnIfMissed: false);
  await tester.pump();
  await _pumpUntil(
    tester,
    () => _currentRoutePath() == expectedPath,
    timeout: const Duration(seconds: 20),
  );
  expect(_currentRoutePath(), expectedPath);
}

Finder _findNavDestination(List<String> labels) {
  for (final label in labels) {
    final tooltipFinder = find.byTooltip(label);
    if (tooltipFinder.evaluate().isNotEmpty) {
      return tooltipFinder;
    }
  }
  return find.byWidgetPredicate(
    (widget) => widget is Text && labels.contains(widget.data),
  );
}

String? _currentRoutePath() {
  final context = navigatorKey.currentContext;
  if (context == null) {
    return null;
  }
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
    if (condition()) {
      return;
    }
  }
  expect(condition(), isTrue);
}
