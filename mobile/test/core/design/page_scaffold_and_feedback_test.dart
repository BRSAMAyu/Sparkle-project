import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import '../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ThemeManager().reset();
  });

  testWidgets('SparklePageScaffold renders child content for page role',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        home: const SparklePageScaffold(
          role: SparklePageRole.settings,
          child: Text('settings-body'),
        ),
      ),
    );

    expect(find.text('settings-body'), findsOneWidget);
    expect(find.byType(Scaffold), findsOneWidget);
  });

  testWidgets('AppFeedback.undoable shows action label', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        home: Scaffold(
          body: Builder(
            builder: (context) => Center(
              child: TextButton(
                onPressed: () {
                  AppFeedback.undoable(
                    context: context,
                    message: '操作已完成',
                    actionLabel: '撤销',
                    onAction: () {},
                  );
                },
                child: const Text('show'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('show'));
    await tester.pump();

    expect(find.text('操作已完成'), findsOneWidget);
    expect(find.text('撤销'), findsOneWidget);
  });

  testWidgets('page scaffold and card surface stay stable on theme changes',
      (tester) async {
    await tester.pumpWidget(const _ThemeHarness());

    expect(find.text('card-body'), findsOneWidget);

    await tester.tap(find.text('toggle-theme'));
    await tester.pumpAndSettle();

    expect(find.text('card-body'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('page scaffold follows platform brightness in system mode',
      (tester) async {
    final manager = ThemeManager();
    await manager.initialize();
    await manager.setAppThemeMode(AppThemeMode.system);
    tester.platformDispatcher.platformBrightnessTestValue = Brightness.light;
    addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

    await tester.pumpWidget(
      const ProviderScope(
        child: _SystemThemeHarness(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('theme:light'), findsOneWidget);
    expect(find.text('token:light'), findsOneWidget);

    tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    tester.binding.handlePlatformBrightnessChanged();
    await tester.pumpAndSettle();

    expect(find.text('theme:dark'), findsOneWidget);
    expect(find.text('token:dark'), findsOneWidget);
    expect(find.text('card-body'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

class _ThemeHarness extends StatefulWidget {
  const _ThemeHarness();

  @override
  State<_ThemeHarness> createState() => _ThemeHarnessState();
}

class _ThemeHarnessState extends State<_ThemeHarness> {
  ThemeMode _themeMode = ThemeMode.light;

  @override
  Widget build(BuildContext context) => MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        themeMode: _themeMode,
        home: SparklePageScaffold(
          role: SparklePageRole.content,
          child: Column(
            children: [
              TextButton(
                onPressed: () {
                  setState(() {
                    _themeMode = _themeMode == ThemeMode.light
                        ? ThemeMode.dark
                        : ThemeMode.light;
                  });
                },
                child: const Text('toggle-theme'),
              ),
              const GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Text('card-body'),
              ),
            ],
          ),
        ),
      );
}

class _SystemThemeHarness extends ConsumerStatefulWidget {
  const _SystemThemeHarness();

  @override
  ConsumerState<_SystemThemeHarness> createState() =>
      _SystemThemeHarnessState();
}

class _SystemThemeHarnessState extends ConsumerState<_SystemThemeHarness> {
  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode: themeMode,
      home: SparklePageScaffold(
        role: SparklePageRole.content,
        child: Builder(
          builder: (context) {
            final themeBrightness = Theme.of(context).brightness.name;
            final tokenBrightness = context.sparkleColors.brightness.name;

            return Column(
              children: [
                Text('theme:$themeBrightness'),
                Text('token:$tokenBrightness'),
                const GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Text('card-body'),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
