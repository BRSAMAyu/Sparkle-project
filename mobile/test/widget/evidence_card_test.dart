import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';
import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('Evidence card renders event payload', (WidgetTester tester) async {
    final item = EvidenceResolveItem(
      type: 'event',
      id: 'evt_1',
      status: 'ok',
      payload: const {
        'event': {'event_type': 'question_submit', 'ts_ms': 12345},
      },
    );

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(body: EvidenceCard(item: item)),
      ),
    );

    // TIER1: summary shows event type
    expect(find.textContaining('question_submit'), findsOneWidget);

    // Tap to expand TIER2 key fields
    await tester.tap(find.byType(InkWell).first);
    await tester.pumpAndSettle();

    // TIER2: key fields show ts_ms value
    expect(find.textContaining('12345'), findsOneWidget);
  });
}
