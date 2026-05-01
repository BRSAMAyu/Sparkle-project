import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/materials.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('shared state widgets', () {
    testWidgets('EmptyState renders in light and dark with large text', (
      tester,
    ) async {
      for (final brightness in [Brightness.light, Brightness.dark]) {
        await tester.pumpWidget(
          _TestShell(
            brightness: brightness,
            disableAnimations: true,
            textScaleFactor: 1.4,
            child: EmptyState.noTasks(
              onCreateTask: () {},
            ),
          ),
        );

        await tester.pump();
        expect(find.byType(EmptyState), findsOneWidget);
        expect(find.byIcon(Icons.task_alt_rounded), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });

    testWidgets(
        'LoadingIndicator skeleton disables shimmer when reduce motion is on', (
      tester,
    ) async {
      await tester.pumpWidget(
        _TestShell(
          disableAnimations: true,
          child: LoadingIndicator.skeleton(
            variant: SkeletonVariant.listItem,
            count: 2,
          ),
        ),
      );

      await tester.pump();
      expect(find.byType(ListItemSkeleton), findsNWidgets(2));
      expect(find.byType(Shimmer), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('CustomErrorWidget retry action remains functional', (
      tester,
    ) async {
      var retried = false;

      await tester.pumpWidget(
        _TestShell(
          disableAnimations: true,
          child: CustomErrorWidget(
            type: ErrorType.page,
            message: '网络连接失败',
            onRetry: () => retried = true,
          ),
        ),
      );

      await tester.pump();
      await tester.tap(find.text('重试'));
      await tester.pump();

      expect(retried, isTrue);
      expect(tester.takeException(), isNull);
    });

    testWidgets('shared theme-aware components update in system mode', (
      tester,
    ) async {
      tester.platformDispatcher.platformBrightnessTestValue = Brightness.light;
      addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

      await tester.pumpWidget(const _SystemThemeComponentsShell());
      await tester.pumpAndSettle();

      expect(find.text('theme:light'), findsOneWidget);

      final lightButtonColor = _materialColor(
        tester,
        ancestorKey: const Key('sparkle-button'),
      );
      final lightCapsuleColor = _materialColor(
        tester,
        ancestorKey: const Key('status-capsule'),
      );
      final lightSurfaceColor = _decoratedContainerColor(
        tester,
        ancestorKey: const Key('material-styler'),
      );

      tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
      tester.binding.handlePlatformBrightnessChanged();
      await tester.pumpAndSettle();

      expect(find.text('theme:dark'), findsOneWidget);

      final darkButtonColor = _materialColor(
        tester,
        ancestorKey: const Key('sparkle-button'),
      );
      final darkCapsuleColor = _materialColor(
        tester,
        ancestorKey: const Key('status-capsule'),
      );
      final darkSurfaceColor = _decoratedContainerColor(
        tester,
        ancestorKey: const Key('material-styler'),
      );

      expect(darkButtonColor, isNot(equals(lightButtonColor)));
      expect(darkCapsuleColor, isNot(equals(lightCapsuleColor)));
      expect(darkSurfaceColor, isNot(equals(lightSurfaceColor)));
      expect(tester.takeException(), isNull);
    });
  });
}

Color? _materialColor(WidgetTester tester, {required Key ancestorKey}) => tester
    .widget<Material>(
      find
          .descendant(
            of: find.byKey(ancestorKey),
            matching: find.byType(Material),
          )
          .first,
    )
    .color;

Color? _decoratedContainerColor(WidgetTester tester,
    {required Key ancestorKey}) {
  final container = tester.widget<Container>(
    find
        .descendant(
          of: find.byKey(ancestorKey),
          matching: find.byWidgetPredicate(
            (widget) =>
                widget is Container &&
                widget.decoration is BoxDecoration &&
                (widget.decoration as BoxDecoration).color != null,
          ),
        )
        .first,
  );

  return (container.decoration! as BoxDecoration).color;
}

class _TestShell extends StatelessWidget {
  const _TestShell({
    required this.child,
    this.brightness = Brightness.light,
    this.disableAnimations = false,
    this.textScaleFactor = 1.0,
  });

  final Widget child;
  final Brightness brightness;
  final bool disableAnimations;
  final double textScaleFactor;

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQueryData(
      platformBrightness: brightness,
      disableAnimations: disableAnimations,
      boldText: textScaleFactor >= 1.3,
      textScaler: TextScaler.linear(textScaleFactor),
    );

    return MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode:
          brightness == Brightness.dark ? ThemeMode.dark : ThemeMode.light,
      localizationsDelegates: const [
        ...AppLocalizations.localizationsDelegates,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: mediaQuery,
        child: Scaffold(body: Center(child: child)),
      ),
    );
  }
}

class _SystemThemeComponentsShell extends StatelessWidget {
  const _SystemThemeComponentsShell();

  @override
  Widget build(BuildContext context) => MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        themeMode: ThemeMode.system,
        home: Builder(
          builder: (context) => Scaffold(
            body: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('theme:${Theme.of(context).brightness.name}'),
                SparkleButton(
                  key: const Key('sparkle-button'),
                  label: 'Action',
                  variant: ButtonVariant.ghost,
                  onPressed: () {},
                ),
                const SizedBox(height: 12),
                const AiStatusCapsule(
                  key: Key('status-capsule'),
                  label: 'Online',
                ),
                const SizedBox(height: 12),
                MaterialStyler(
                  key: const Key('material-styler'),
                  material: AppMaterials.ceramic(context),
                  child: const SizedBox(width: 80, height: 32),
                ),
              ],
            ),
          ),
        ),
      );
}
