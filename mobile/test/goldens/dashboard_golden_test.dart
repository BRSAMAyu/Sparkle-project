/// Golden Tests for Dashboard Screen
/// Dashboard屏幕Golden测试
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';

void main() {
  group('Dashboard Golden Tests', () {
    testGoldens('Dashboard light theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: const DashboardScreen(),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_light.png'),
      );
    });

    testGoldens('Dashboard dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: const DashboardScreen(),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_dark.png'),
      );
    });

    testGoldens('Dashboard with omnibar focused', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: DashboardScreen(),
        ),
      );

      await tester.pumpAndSettle();

      // Tap on omnibar
      await tester.tap(find.byType(TextField));
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_omnibar_focused.png'),
      );
    });

    testGoldens('Dashboard with task board expanded', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: DashboardScreen(),
        ),
      );

      await tester.pumpAndSettle();

      // Tap on task board
      await tester.tap(find.text('Tasks'));
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_tasks_expanded.png'),
      );
    });

    testGoldens('Dashboard responsive layout - mobile', (tester) async {
      await tester.pumpWidgetBuilder(
        const MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(size: Size(375, 667)), // iPhone SE
            child: DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_mobile.png'),
      );
    });

    testGoldens('Dashboard responsive layout - tablet', (tester) async {
      await tester.pumpWidgetBuilder(
        const MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(size: Size(768, 1024)), // iPad
            child: DashboardScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_tablet.png'),
      );
    });

    testGoldens('Dashboard with notifications', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: DashboardScreen(
            notifications: [
              NotificationItem(
                title: 'Welcome!',
                message: 'Get started with Sparkle',
                timestamp: DateTime.now(),
              ),
            ],
          ),
        ),
      );

      await tester.pumpAndSettle();

      await expectLater(
        find.byType(DashboardScreen),
        matchesGoldenFile('dashboard_with_notifications.png'),
      );
    });
  });
}

// Mock classes and types
class NotificationItem {

  NotificationItem({
    required this.title,
    required this.message,
    required this.timestamp,
  });
  final String title;
  final String message;
  final DateTime timestamp;
}
