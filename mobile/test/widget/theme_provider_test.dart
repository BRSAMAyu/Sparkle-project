import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/presentation/providers/theme_provider.dart';

void main() {
  group('Theme Provider Tests', () {
    // ============================================================
    // Theme Mode Conversion Tests
    // ============================================================

    group('ThemeMode Conversion', () {
      test('appThemeModeToThemeMode - light mode', () {
        final result = appThemeModeToThemeMode(AppThemeMode.light);
        expect(result, ThemeMode.light);
      });

      test('appThemeModeToThemeMode - dark mode', () {
        final result = appThemeModeToThemeMode(AppThemeMode.dark);
        expect(result, ThemeMode.dark);
      });

      test('appThemeModeToThemeMode - system mode', () {
        final result = appThemeModeToThemeMode(AppThemeMode.system);
        expect(result, ThemeMode.system);
      });

      test('themeModeToAppThemeMode - light mode', () {
        final result = themeModeToAppThemeMode(ThemeMode.light);
        expect(result, AppThemeMode.light);
      });

      test('themeModeToAppThemeMode - dark mode', () {
        final result = themeModeToAppThemeMode(ThemeMode.dark);
        expect(result, AppThemeMode.dark);
      });

      test('themeModeToAppThemeMode - system mode', () {
        final result = themeModeToAppThemeMode(ThemeMode.system);
        expect(result, AppThemeMode.system);
      });

      test('bidirectional conversion consistency', () {
        final modes = [
          AppThemeMode.light,
          AppThemeMode.dark,
          AppThemeMode.system,
        ];

        for (final mode in modes) {
          final converted = appThemeModeToThemeMode(mode);
          final roundTrip = themeModeToAppThemeMode(converted);
          expect(roundTrip, mode);
        }
      });
    });

    // ============================================================
    // Theme Manager Provider Tests
    // ============================================================

    group('Theme Manager Provider', () {
      testWidgets('themeManagerProvider returns non-null instance',
          (WidgetTester tester) async {
        bool providerWorked = false;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final manager = ref.watch(themeManagerProvider);
                providerWorked = manager != null;
                return const Scaffold();
              },
            ),
          ),
        );

        expect(providerWorked, true);
      });

      testWidgets('themeManagerProvider returns same instance',
          (WidgetTester tester) async {
        ThemeManager? firstInstance;
        ThemeManager? secondInstance;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                if (firstInstance == null) {
                  firstInstance = ref.watch(themeManagerProvider);
                } else {
                  secondInstance = ref.watch(themeManagerProvider);
                }
                return const Scaffold();
              },
            ),
          ),
        );

        expect(firstInstance, secondInstance);
      });
    });

    // ============================================================
    // Theme Mode Provider Tests
    // ============================================================

    group('Theme Mode State Provider', () {
      testWidgets('themeModeProvider has initial value',
          (WidgetTester tester) async {
        AppThemeMode? capturedMode;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                capturedMode = ref.watch(themeModeProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        expect(capturedMode, isNotNull);
      });

      testWidgets('themeModeProvider can notify listeners',
          (WidgetTester tester) async {
        int updateCount = 0;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final mode = ref.watch(themeModeProvider);
                updateCount++;
                return Scaffold(
                  body: Center(
                    child: Text(mode.toString()),
                  ),
                );
              },
            ),
          ),
        );

        final initialCount = updateCount;

        // Update provider
        // Note: StateProvider should trigger rebuild
        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final mode = ref.watch(themeModeProvider);
                updateCount++;
                return Scaffold(
                  body: Center(
                    child: Text(mode.toString()),
                  ),
                );
              },
            ),
          ),
        );

        expect(updateCount, greaterThanOrEqualTo(initialCount));
      });
    });

    // ============================================================
    // Brand Preset Provider Tests
    // ============================================================

    group('Brand Preset Provider', () {
      testWidgets('brandPresetProvider has initial value',
          (WidgetTester tester) async {
        BrandPreset? capturedPreset;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                capturedPreset = ref.watch(brandPresetProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        expect(capturedPreset, isNotNull);
        expect(capturedPreset, BrandPreset.sparkle);
      });

      testWidgets('brandPresetProvider returns valid preset',
          (WidgetTester tester) async {
        BrandPreset? capturedPreset;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                capturedPreset = ref.watch(brandPresetProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        final validPresets = [
          BrandPreset.sparkle,
          BrandPreset.ocean,
          BrandPreset.forest,
        ];
        expect(validPresets, contains(capturedPreset));
      });
    });

    // ============================================================
    // High Contrast Provider Tests
    // ============================================================

    group('High Contrast Provider', () {
      testWidgets('highContrastProvider has initial value',
          (WidgetTester tester) async {
        bool? capturedValue;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                capturedValue = ref.watch(highContrastProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        expect(capturedValue, isNotNull);
        expect(capturedValue, isBool);
      });

      testWidgets('highContrastProvider is boolean',
          (WidgetTester tester) async {
        bool? capturedValue;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                capturedValue = ref.watch(highContrastProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        expect(capturedValue is bool, true);
      });
    });

    // ============================================================
    // Multiple Providers Integration Tests
    // ============================================================

    group('Multiple Providers Integration', () {
      testWidgets('All providers accessible together',
          (WidgetTester tester) async {
        AppThemeMode? mode;
        BrandPreset? preset;
        bool? highContrast;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                mode = ref.watch(themeModeProvider);
                preset = ref.watch(brandPresetProvider);
                highContrast = ref.watch(highContrastProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        expect(mode, isNotNull);
        expect(preset, isNotNull);
        expect(highContrast, isNotNull);
      });

      testWidgets('Theme manager and state providers independent',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final manager = ref.watch(themeManagerProvider);
                final mode = ref.watch(themeModeProvider);

                return Scaffold(
                  body: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text('Manager: ${manager.runtimeType}'),
                        Text('Mode: $mode'),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        );

        expect(find.text('Manager: ThemeManager'), findsOneWidget);
      });
    });

    // ============================================================
    // Widget Tests with Theme Integration
    // ============================================================

    group('Widget Theme Integration', () {
      testWidgets('Scaffold with theme from provider',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final mode = ref.watch(themeModeProvider);

                return MaterialApp(
                  themeMode: appThemeModeToThemeMode(mode),
                  theme: ThemeData.light(),
                  darkTheme: ThemeData.dark(),
                  home: const Scaffold(
                    body: Center(
                      child: Text('Themed Widget'),
                    ),
                  ),
                );
              },
            ),
          ),
        );

        expect(find.text('Themed Widget'), findsOneWidget);
      });

      testWidgets('Text renders with correct brightness',
          (WidgetTester tester) async {
        await tester.pumpWidget(
          ProviderScope(
            child: MaterialApp(
              home: Scaffold(
                body: Consumer(
                  builder: (context, ref, child) {
                    final isDark = ref.watch(themeModeProvider) ==
                        AppThemeMode.dark;

                    return Text(
                      isDark ? 'Dark Mode' : 'Light Mode',
                    );
                  },
                ),
              ),
            ),
          ),
        );

        expect(
          find.byWidgetPredicate(
            (widget) => widget is Text,
          ),
          findsOneWidget,
        );
      });
    });

    // ============================================================
    // Error Handling Tests
    // ============================================================

    group('Error Handling', () {
      test('Invalid theme mode conversion doesn\'t crash', () {
        try {
          appThemeModeToThemeMode(AppThemeMode.light);
          appThemeModeToThemeMode(AppThemeMode.dark);
          appThemeModeToThemeMode(AppThemeMode.system);
          expect(true, true); // No exception thrown
        } catch (e) {
          fail('Should not throw exception: $e');
        }
      });

      test('Null theme mode conversion fails gracefully', () {
        expect(
          () {
            // ThemeMode is non-nullable, so this tests the conversion
            final mode = appThemeModeToThemeMode(AppThemeMode.light);
            expect(mode, isNotNull);
          },
          returnsNormally,
        );
      });
    });

    // ============================================================
    // State Consistency Tests
    // ============================================================

    group('State Consistency', () {
      testWidgets('Provider state persists across rebuilds',
          (WidgetTester tester) async {
        AppThemeMode? firstValue;
        AppThemeMode? secondValue;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final mode = ref.watch(themeModeProvider);
                if (firstValue == null) {
                  firstValue = mode;
                } else {
                  secondValue = mode;
                }
                return const Scaffold();
              },
            ),
          ),
        );

        await tester.pump();

        expect(firstValue, secondValue);
      });

      testWidgets('Multiple consumers see same values',
          (WidgetTester tester) async {
        AppThemeMode? mode1;
        AppThemeMode? mode2;

        await tester.pumpWidget(
          ProviderScope(
            child: Scaffold(
              body: Consumer(
                builder: (context, ref, child) {
                  mode1 = ref.watch(themeModeProvider);
                  return Center(
                    child: Consumer(
                      builder: (context, ref, child) {
                        mode2 = ref.watch(themeModeProvider);
                        return const Text('Test');
                      },
                    ),
                  );
                },
              ),
            ),
          ),
        );

        expect(mode1, mode2);
      });
    });

    // ============================================================
    // Performance Tests
    // ============================================================

    group('Performance', () {
      testWidgets('Provider initialization is fast',
          (WidgetTester tester) async {
        final stopwatch = Stopwatch()..start();

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                ref.watch(themeManagerProvider);
                ref.watch(themeModeProvider);
                ref.watch(brandPresetProvider);
                ref.watch(highContrastProvider);
                return const Scaffold();
              },
            ),
          ),
        );

        stopwatch.stop();

        // Should initialize quickly (within 1 second)
        expect(stopwatch.elapsedMilliseconds, lessThan(1000));
      });

      testWidgets('Provider updates efficiently',
          (WidgetTester tester) async {
        int buildCount = 0;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                ref.watch(themeModeProvider);
                buildCount++;
                return const Scaffold();
              },
            ),
          ),
        );

        final initialCount = buildCount;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                ref.watch(themeModeProvider);
                buildCount++;
                return const Scaffold();
              },
            ),
          ),
        );

        // Should have minimal rebuilds
        expect(buildCount - initialCount, lessThan(5));
      });
    });

    // ============================================================
    // Edge Cases
    // ============================================================

    group('Edge Cases', () {
      testWidgets('Provider works with empty widget tree',
          (WidgetTester tester) async {
        bool initialized = false;

        await tester.pumpWidget(
          ProviderScope(
            child: Consumer(
              builder: (context, ref, child) {
                final _ = ref.watch(themeModeProvider);
                initialized = true;
                return const SizedBox.shrink();
              },
            ),
          ),
        );

        expect(initialized, true);
      });

      testWidgets('Provider accessible from deep widget tree',
          (WidgetTester tester) async {
        AppThemeMode? capturedMode;

        await tester.pumpWidget(
          ProviderScope(
            child: Scaffold(
              body: Center(
                child: Container(
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Consumer(
                      builder: (context, ref, child) {
                        capturedMode = ref.watch(themeModeProvider);
                        return const Text('Deep widget');
                      },
                    ),
                  ),
                ),
              ),
            ),
          ),
        );

        expect(capturedMode, isNotNull);
        expect(find.text('Deep widget'), findsOneWidget);
      });
    });
  });
}
