import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';

void main() {
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
}

class _ThemeHarness extends StatefulWidget {
  const _ThemeHarness();

  @override
  State<_ThemeHarness> createState() => _ThemeHarnessState();
}

class _ThemeHarnessState extends State<_ThemeHarness> {
  ThemeMode _themeMode = ThemeMode.light;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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
}
