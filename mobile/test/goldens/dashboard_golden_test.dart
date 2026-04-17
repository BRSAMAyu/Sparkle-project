/// Golden Tests for Dashboard Screen
/// Dashboard屏幕Golden测试
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';

import '../features/home/dashboard_test_harness.dart';

const bool _enableDashboardGoldens = bool.fromEnvironment(
  'ENABLE_DASHBOARD_GOLDEN',
);

void main() {
  group('Dashboard Golden Tests', () {
    testGoldens(
      'Dashboard light theme',
      (tester) async {
        await initializeDashboardTestEnvironment();
        await tester.pumpWidget(
          buildDashboardTestHarness(theme: ThemeData.light()),
        );

        await _pumpDashboard(tester);

        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('dashboard_light.png'),
        );
      },
      skip: !_enableDashboardGoldens,
    );

    testGoldens(
      'Dashboard dark theme',
      (tester) async {
        await initializeDashboardTestEnvironment();
        await tester.pumpWidget(
          buildDashboardTestHarness(theme: ThemeData.dark()),
        );

        await _pumpDashboard(tester);

        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('dashboard_dark.png'),
        );
      },
      skip: !_enableDashboardGoldens,
    );

    testGoldens(
      'Dashboard responsive layout - mobile',
      (tester) async {
        await initializeDashboardTestEnvironment();
        await tester.pumpWidget(
          buildDashboardTestHarness(
            size: const Size(375, 667),
          ),
        );

        await _pumpDashboard(tester);

        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('dashboard_mobile.png'),
        );
      },
      skip: !_enableDashboardGoldens,
    );

    testGoldens(
      'Dashboard responsive layout - tablet',
      (tester) async {
        await initializeDashboardTestEnvironment();
        await tester.pumpWidget(
          buildDashboardTestHarness(
            size: const Size(768, 1024),
          ),
        );

        await _pumpDashboard(tester);

        await expectLater(
          find.byType(MaterialApp),
          matchesGoldenFile('dashboard_tablet.png'),
        );
      },
      skip: !_enableDashboardGoldens,
    );
  });
}

Future<void> _pumpDashboard(WidgetTester tester) async {
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}
