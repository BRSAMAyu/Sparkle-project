import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/settings/presentation/screens/accessibility_settings_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

const bool _enableAccessibilityGolden = bool.fromEnvironment(
  'ENABLE_ACCESSIBILITY_GOLDEN',
);

void main() {
  setUp(setUpI18nForTesting);

  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('renders central accessibility settings controls',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_buildScreen());
    await tester.pump();

    expect(find.text('无障碍与低负荷'), findsOneWidget);
    expect(find.text('字体缩放'), findsOneWidget);
    expect(find.text('高对比度'), findsOneWidget);
    expect(find.text('色盲友好'), findsOneWidget);
    expect(find.text('减弱动画'), findsOneWidget);
    expect(find.text('震动反馈'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('屏幕阅读优化'),
      220,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('屏幕阅读优化'), findsOneWidget);
    expect(find.text('TTS 朗读'), findsOneWidget);

    await expectLater(tester, meetsGuideline(androidTapTargetGuideline));

    await tester.pump(const Duration(seconds: 35));
  });

  testWidgets(
    'matches accessibility settings golden',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(390, 844));
      await tester.pumpWidget(_buildScreen());
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(AccessibilitySettingsScreen),
        matchesGoldenFile('goldens/accessibility_settings_screen.png'),
      );

      await tester.binding.setSurfaceSize(null);
      await tester.pump(const Duration(seconds: 35));
    },
    skip: !_enableAccessibilityGolden,
  );
}

Widget _buildScreen() => ProviderScope(
      child: testMaterialApp(
        home: const AccessibilitySettingsScreen(),
      ),
    );
