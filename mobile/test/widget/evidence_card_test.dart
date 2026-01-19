import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';

void main() {
  testWidgets('Evidence card renders event payload', (WidgetTester tester) async {
    final item = EvidenceResolveItem(
      type: 'event',
      id: 'evt_1',
      status: 'ok',
      payload: const {
        'event': {'event_type': 'question_submit', 'ts_ms': 12345}
      },
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: EvidenceCard(item: item)),
      ),
    );

    expect(find.textContaining('question_submit'), findsOneWidget);
    expect(find.textContaining('12345'), findsOneWidget);
  });
}
