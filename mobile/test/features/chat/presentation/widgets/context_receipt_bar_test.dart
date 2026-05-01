import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/context_receipt_bar.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('receipt actions emit corrective prompts', (tester) async {
    String? selectedPrompt;

    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(
          body: ContextReceiptBar(
            rawMetadata: const {
              'context_receipt': {
                'used_count': 1,
                'excluded_count': 0,
                'used_names': <String>['线性代数课件'],
                'excluded_names': <String>[],
                'decision_reason': '已优先引用课件',
                'retrieval_mode': 'courseware',
              },
            },
            onActionSelected: (prompt) => selectedPrompt = prompt,
          ),
        ),),
    );

    await tester.tap(find.text('已优先引用课件'));
    await tester.pumpAndSettle();

    expect(find.text('按课件重讲'), findsOneWidget);
    expect(find.text('排除此资料'), findsOneWidget);
    expect(find.text('换成历年真题'), findsOneWidget);

    await tester.tap(find.text('排除此资料'));
    await tester.pumpAndSettle();

    expect(selectedPrompt, contains('线性代数课件'));
    expect(selectedPrompt, contains('排除'));
    expect(find.text('排除此资料'), findsNothing);
  });
}
