import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/features/settings/presentation/screens/accessibility_settings_screen.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(setUpI18nForTesting);

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  Future<void> pumpScreen(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: const AccessibilitySettingsScreen(),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('centralizes the required accessibility controls',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await pumpScreen(tester);

    expect(find.text('无障碍与低负荷'), findsOneWidget);
    expect(find.text('字体缩放'), findsOneWidget);
    expect(find.text('100%'), findsOneWidget);
    expect(find.text('高对比度'), findsOneWidget);
    expect(find.text('色盲友好'), findsOneWidget);
    expect(find.text('舒适 48dp'), findsOneWidget);
    expect(find.text('减弱动画'), findsOneWidget);
    expect(find.text('震动反馈'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('屏幕阅读优化'),
      220,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('屏幕阅读优化'), findsOneWidget);
    expect(find.text('TTS 朗读'), findsOneWidget);
  });

  testWidgets('low-load mode enables reduced motion default', (tester) async {
    await pumpScreen(tester);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(AccessibilitySettingsScreen)),
    );
    await tester.scrollUntilVisible(
      find.text('启用低负荷体验'),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.widgetWithText(SwitchListTile, '启用低负荷体验'));
    await tester.pump();

    final settings = container.read(accessibilitySettingsProvider);
    expect(settings.lowLoadMode, isTrue);
    expect(settings.reduceMotion, isTrue);
    expect(settings.screenReaderOptimized, isTrue);
    expect(settings.touchTargetSize, TouchTargetSize.large);
  });

  testWidgets('haptic feedback toggle updates centralized state',
      (tester) async {
    await pumpScreen(tester);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(AccessibilitySettingsScreen)),
    );
    await tester.scrollUntilVisible(
      find.text('震动反馈'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.widgetWithText(SwitchListTile, '震动反馈'));
    await tester.pump();

    expect(
      container.read(accessibilitySettingsProvider).hapticFeedback,
      isFalse,
    );
  });
}
