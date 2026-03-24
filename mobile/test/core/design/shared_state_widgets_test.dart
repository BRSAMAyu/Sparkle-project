import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
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

    testWidgets('LoadingIndicator skeleton disables shimmer when reduce motion is on', (
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
  });
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
      themeMode: brightness == Brightness.dark ? ThemeMode.dark : ThemeMode.light,
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
