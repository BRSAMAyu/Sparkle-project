import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/metacognition_panel_card.dart';

void main() {
  testWidgets('metacognition panel renders registered dashboard copy',
      (tester) async {
    var hidden = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MetacognitionPanelCard(
            cards: const [
              {
                'title': '时间预估',
                'status': 'ready',
                'body': '你过去 10 次对完成时间估得偏乐观 2.3 小时。',
                'trend_text': '最近几周正在变稳。',
              },
            ],
            generatedAt: '2026-04-22T10:00:00',
            onHide: () {
              hidden = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('自我认识'), findsOneWidget);
    expect(find.text('时间预估'), findsOneWidget);
    expect(find.text('你过去 10 次对完成时间估得偏乐观 2.3 小时。'), findsOneWidget);
    expect(find.text('最近几周正在变稳。'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.visibility_off_outlined));
    expect(hidden, isTrue);
  });

  test('fromProfileContext_returns_null_when_hidden_or_unavailable', () {
    expect(
      MetacognitionPanelCard.fromProfileContext({
        'metacognition_dashboard': {
          'available': false,
          'hidden': false,
          'cards': const [],
        },
      }),
      isNull,
    );
    expect(
      MetacognitionPanelCard.fromProfileContext({
        'metacognition_dashboard': {
          'available': true,
          'hidden': true,
          'cards': const [
            {'title': '时间预估', 'body': '样本不足，继续观察中。'},
          ],
        },
      }),
      isNull,
    );
  });

  test('fromProfileContext_extracts_cards_for_visible_payload', () {
    final payload = MetacognitionPanelCard.fromProfileContext({
      'metacognition_dashboard': {
        'available': true,
        'hidden': false,
        'generated_at': '2026-04-22T10:00:00',
        'cards': const [
          {'title': '时间预估', 'body': '样本不足，继续观察中。'},
        ],
      },
    });

    expect(payload, isNotNull);
    expect((payload!['cards'] as List).length, 1);
    expect(payload['generatedAt'], '2026-04-22T10:00:00');
  });
}
