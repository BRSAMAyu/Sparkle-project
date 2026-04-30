import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/traits_prior_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('traits prior card hides when there is no confident trait',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: TraitsPriorCard(traits: <Map<String, dynamic>>[]),
        ),
      ),
    );

    expect(find.text('长期倾向'), findsNothing);
  });

  testWidgets('traits prior card renders confident dimensions', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: TraitsPriorCard(
            traits: <Map<String, dynamic>>[
              {
                'dim': 'conscientiousness',
                'value': 0.42,
                'confidence': 0.15,
                'source': 'merged',
              },
            ],
          ),
        ),
      ),
    );

    expect(find.text('长期倾向'), findsOneWidget);
    expect(find.text('尽责性'), findsOneWidget);
    expect(find.text('15%'), findsOneWidget);
  });

  test('traits prior parser filters low confidence items from profile context',
      () {
    final items = TraitsPriorCard.fromProfileContext({
      'user_insight_state': {
        'traits_prior': {
          'openness': {
            'value': 0.4,
            'confidence': 0.09,
            'source': 'coldstart',
          },
          'agreeableness': {
            'value': 0.2,
            'confidence': 0.12,
            'source': 'merged',
          },
        },
      },
    });

    expect(items.length, 1);
    expect(items.first['dim'], 'agreeableness');
  });
}
