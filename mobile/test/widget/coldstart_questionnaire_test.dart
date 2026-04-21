import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/traits_coldstart_questionnaire.dart';
import 'dart:async';

void main() {
  final questions = <Map<String, dynamic>>[
    {
      'id': 'q1',
      'title': '开始新目标时，你更像哪种方式？',
      'options': [
        {'id': 'structured', 'label': '先搭结构再行动'},
        {'id': 'skip', 'label': '跳过'},
      ],
    },
  ];

  testWidgets('coldstart questionnaire renders title and options',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TraitsColdstartQuestionnaire(
            questions: questions,
            onSubmit: (_) async {},
            onSkip: () async {},
          ),
        ),
      ),
    );

    expect(find.text('初始画像'), findsOneWidget);
    expect(find.text('先搭结构再行动'), findsOneWidget);
    expect(find.text('跳过'), findsAtLeastNWidgets(1));
  });

  testWidgets('coldstart questionnaire collects answers before submit',
      (tester) async {
    Map<String, String>? submitted;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TraitsColdstartQuestionnaire(
            questions: questions,
            onSubmit: (answers) async {
              submitted = answers;
            },
            onSkip: () async {},
          ),
        ),
      ),
    );

    await tester.tap(find.text('先搭结构再行动'));
    await tester.pump();
    await tester.tap(find.text('保存'));
    await tester.pumpAndSettle();

    expect(submitted, {'q1': 'structured'});
  });

  testWidgets('coldstart questionnaire triggers skip action', (tester) async {
    var skipped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TraitsColdstartQuestionnaire(
            questions: questions,
            onSubmit: (_) async {},
            onSkip: () async {
              skipped = true;
            },
          ),
        ),
      ),
    );

    await tester.tap(find.widgetWithText(TextButton, '跳过'));
    await tester.pumpAndSettle();

    expect(skipped, isTrue);
  });

  testWidgets('coldstart questionnaire shows submitting state',
      (tester) async {
    final completer = Completer<void>();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TraitsColdstartQuestionnaire(
            questions: questions,
            onSubmit: (_) async {
              await completer.future;
            },
            onSkip: () async {},
          ),
        ),
      ),
    );

    await tester.tap(find.text('保存'));
    await tester.pump();

    expect(find.text('提交中...'), findsOneWidget);
    completer.complete();
    await tester.pumpAndSettle();
  });
}
