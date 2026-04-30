import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/widgets/idiographic_summary_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  test('fromProfileContext_returns_null_below_confidence_threshold', () {
    expect(
      IdiographicSummaryCard.fromProfileContext({
        'idiographic_summary': {
          'mode': 'live',
          'confidence': 0.49,
          'disclaimer_text': '这只是你数据中的模式，不代表因果关系。',
          'top_associations': const [
            {
              'displayed': true,
              'rendered_text': '在你最近 45 天的数据里，学习节奏和专注时长有同步变化的趋势。',
            },
          ],
        },
      }),
      isNull,
    );
  });

  test('fromProfileContext_requires_disclaimer_text', () {
    expect(
      IdiographicSummaryCard.fromProfileContext({
        'idiographic_summary': {
          'mode': 'live',
          'confidence': 0.62,
          'disclaimer_text': '',
          'top_associations': const [
            {
              'displayed': true,
              'rendered_text': '在你最近 45 天的数据里，学习节奏和专注时长有同步变化的趋势。',
            },
          ],
        },
      }),
      isNull,
    );
  });

  testWidgets('idiographic summary card renders visible associations', (tester) async {
    final parsed = IdiographicSummaryCard.fromProfileContext({
      'idiographic_summary': {
        'mode': 'live',
        'confidence': 0.66,
        'disclaimer_text': '这只是你数据中的模式，不代表因果关系。',
        'top_associations': const [
          {
            'displayed': true,
            'rendered_text': '在你最近 45 天的数据里，学习节奏和专注时长有同步变化的趋势。',
          },
        ],
      },
    });

    expect(parsed, isNotNull);

    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(
          body: IdiographicSummaryCard(
            summaryLines: (parsed!['summaryLines'] as List<dynamic>).cast<String>(),
            disclaimerText: parsed['disclaimerText'] as String,
          ),
        ),),
    );

    expect(find.text('近期关联观察'), findsOneWidget);
    expect(
      find.text('在你最近 45 天的数据里，学习节奏和专注时长有同步变化的趋势。'),
      findsOneWidget,
    );
    expect(find.text('这只是你数据中的模式，不代表因果关系。'), findsOneWidget);
  });
}
