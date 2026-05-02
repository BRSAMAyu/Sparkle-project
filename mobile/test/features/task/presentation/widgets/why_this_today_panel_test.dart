import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/task/data/models/priority_reasoning.dart';
import 'package:sparkle/features/task/presentation/widgets/why_this_today_panel.dart';

void main() {
  testWidgets(
      'renders expanded priority reasoning with signals and skipped option',
      (tester) async {
    final reasoning = PriorityReasoning(
      taskId: 'task-1',
      generatedAt: DateTime(2026),
      selectedScore: 82,
      primaryReason: 'Matrix inverse is due for spaced repetition today.',
      supportingSignals: const [
        PrioritySignal(
          type: 'spaced_repetition',
          weight: 0.4,
          detail: 'Review is due.',
        ),
        PrioritySignal(
          type: 'goal_progress',
          weight: 0.3,
          detail: 'Goal moves forward.',
        ),
        PrioritySignal(
          type: 'energy_match',
          weight: 0.2,
          detail: 'Energy matches.',
        ),
        PrioritySignal(
          type: 'social_context',
          weight: 0.1,
          detail: 'Peer signal.',
        ),
      ],
      alternativeOptionsSkipped: const [
        AlternativeOptionSkipped(
          taskId: 'task-2',
          title: 'Practice determinants',
          score: 64,
          reason: '18.0 points lower than this task.',
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: WhyThisTodayPanel(
              taskId: 'task-1',
              reasoning: reasoning,
              initiallyExpanded: true,
            ),
          ),
        ),
      ),
    );

    expect(
      find.text('Matrix inverse is due for spaced repetition today.'),
      findsOneWidget,
    );
    expect(find.text('Practice determinants'), findsOneWidget);
    expect(find.text('40%'), findsOneWidget);
    expect(find.text('30%'), findsOneWidget);
    expect(find.text('20%'), findsOneWidget);
    expect(find.text('10%'), findsOneWidget);
  });
}
