import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/features/settings/presentation/screens/accessibility_settings_screen.dart';

const bool _enableAccessibilityGolden = bool.fromEnvironment(
  'ENABLE_ACCESSIBILITY_GOLDEN',
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      kAccessibilitySettingsStorageKey:
          '{"font_scale":1.15,"high_contrast":true,"screen_reader_optimized":true,'
              '"touch_target_size":"large","reduce_motion":true,'
              '"color_blind_friendly":false,"tts_enabled":false,'
              '"haptic_feedback":false,"low_load_mode":false}',
    });
  });

  testWidgets('renders central accessibility settings controls',
      (tester) async {
    await tester.pumpWidget(_buildScreen());
    await tester.pumpAndSettle();

    expect(find.text('Accessibility'), findsOneWidget);
    expect(find.text('Font scale'), findsOneWidget);
    expect(find.text('High contrast'), findsOneWidget);
    expect(find.text('Screen reader optimization'), findsOneWidget);
    expect(find.text('WCAG AA checks'), findsOneWidget);

    await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
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
    },
    skip: !_enableAccessibilityGolden,
  );
}

Widget _buildScreen() => const ProviderScope(
      child: MaterialApp(
        home: AccessibilitySettingsScreen(),
      ),
    );
