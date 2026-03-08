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
}
