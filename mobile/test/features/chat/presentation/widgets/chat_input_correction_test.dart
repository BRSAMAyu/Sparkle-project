import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('freeform correction button submits outside normal chat send', (
    tester,
  ) async {
    String? correctionText;
    String? sentText;

    await tester.pumpWidget(
      testMaterialApp(
        home: ProviderScope(
          child: Scaffold(
            body: ChatInput(
              onSend: (text, {replyToId}) => sentText = text,
              onFreeformCorrection: (text) => correctionText = text,
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Aurora 理解错了？'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, '  我只是忙，不是焦虑  ');
    await tester.tap(find.text('发送'));
    await tester.pumpAndSettle();

    expect(correctionText, '我只是忙，不是焦虑');
    expect(sentText, isNull);
  });
}
