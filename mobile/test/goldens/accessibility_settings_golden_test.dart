import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/settings/presentation/screens/accessibility_settings_screen.dart';

import '../shared/i18n_test_helper.dart';

const bool _enableAccessibilityGoldens = bool.fromEnvironment(
  'ENABLE_ACCESSIBILITY_GOLDEN',
);

void main() {
  setUp(setUpI18nForTesting);

  testGoldens(
    'accessibility settings mobile layout',
    (tester) async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      await loadAppFonts();
      await tester.pumpWidgetBuilder(
        ProviderScope(
          child: testMaterialApp(
            home: const AccessibilitySettingsScreen(),
            theme: ThemeData.light(),
          ),
        ),
        surfaceSize: const Size(390, 844),
      );
      await tester.pump();

      await screenMatchesGolden(
        tester,
        'accessibility_settings_mobile',
      );
    },
    skip: !_enableAccessibilityGoldens,
  );
}
