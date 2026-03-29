import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('guest can enter app and open core shell chains', (tester) async {
    app.main();
    await _pumpUntil(
      tester,
      () =>
          find.byType(LoginScreen).evaluate().isNotEmpty ||
          find.byType(DashboardScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 20),
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
      timeout: const Duration(seconds: 30),
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
  });
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
