/// Golden Tests for Dashboard Screen
/// Dashboard屏幕Golden测试
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';

const bool _enableDashboardGoldens = bool.fromEnvironment(
  'ENABLE_DASHBOARD_GOLDEN',
  defaultValue: false,
);

void main() {
  group('Dashboard Golden Tests', () {
    testGoldens('Dashboard light theme', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: ThemeData.light(),
            home: const DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_light.png'),
      );
    }, skip: !_enableDashboardGoldens);

    testGoldens('Dashboard dark theme', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: ThemeData.dark(),
            home: const DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_dark.png'),
      );
    }, skip: !_enableDashboardGoldens);

    testGoldens('Dashboard responsive layout - mobile', (tester) async {
      await tester.pumpWidgetBuilder(
        const ProviderScope(
          child: MaterialApp(
            home: MediaQuery(
              data: MediaQueryData(size: Size(375, 667)), // iPhone SE
              child: DashboardScreen(),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_mobile.png'),
      );
    }, skip: !_enableDashboardGoldens);

    testGoldens('Dashboard responsive layout - tablet', (tester) async {
      await tester.pumpWidgetBuilder(
        const ProviderScope(
          child: MaterialApp(
            home: MediaQuery(
              data: MediaQueryData(size: Size(768, 1024)), // iPad
              child: DashboardScreen(),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_tablet.png'),
      );
    }, skip: !_enableDashboardGoldens);
  });
}
