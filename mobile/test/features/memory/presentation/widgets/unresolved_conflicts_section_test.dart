import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/unresolved_conflicts_section.dart';

void main() {
  testWidgets('unresolved conflicts section renders candidates and actions', (
    WidgetTester tester,
  ) async {
    String? tapped;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: UnresolvedConflictsSection(
            items: [
              UnresolvedConflictItem(
                id: 'conflict_1',
                conflictKey: 'commitment:probability',
                status: 'pending_user',
                leftCandidate: UnresolvedConflictCandidate(
                  summary: '准备今晚复习概率论',
                  lane: 'inferred_extraction',
                  evidenceToken: 'turn-left',
                ),
                rightCandidate: UnresolvedConflictCandidate(
                  summary: '今晚先刷概率论错题',
                  lane: 'inferred_extraction',
                  evidenceToken: 'turn-right',
                ),
              ),
            ],
            processingIds: const <String>{},
            onSelectLeft: (item) async => tapped = 'left:${item.id}',
            onSelectRight: (item) async => tapped = 'right:${item.id}',
            onSelectNone: (item) async => tapped = 'none:${item.id}',
          ),
        ),
      ),
    );

    expect(find.text('待你确认'), findsOneWidget);
    expect(find.text('准备今晚复习概率论'), findsOneWidget);
    expect(find.textContaining('evidence_token: turn-left'), findsOneWidget);

    await tester.tap(find.text('选 B'));
    await tester.pumpAndSettle();

    expect(tapped, 'right:conflict_1');
  });
}
