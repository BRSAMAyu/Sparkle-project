import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/contextual_correction_bar.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets(
      'predicted chip exposes label for chat text and semantic value for telemetry',
      (
    tester,
  ) async {
    AuroraPredictedReplyOption? selected;
    String? selectedGroupId;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextualCorrectionBar(
            predictedReplyGroups: [
              AuroraPredictedReplyGroup(
                groupId: 'group-risk',
                question: 'Was Aurora wrong?',
                questionType: 'assumption_check',
                contextNote: '',
                options: [
                  AuroraPredictedReplyOption(
                    id: 'opt-risk',
                    label: 'That is not what happened',
                    semanticValue: 'risk_false_positive',
                    replyType: 'assumption_check',
                    confidence: 0.95,
                    modelWriteEffect: null,
                    isDisconfirming: true,
                    isFreeform: false,
                    contextSource: 'chat',
                    telemetryId: 'telemetry-risk',
                  ),
                  AuroraPredictedReplyOption(
                    id: 'opt-freeform',
                    label: 'I will explain',
                    semanticValue: 'freeform_correction',
                    replyType: 'freeform',
                    confidence: 0.1,
                    modelWriteEffect: null,
                    isDisconfirming: true,
                    isFreeform: true,
                    contextSource: 'chat',
                    telemetryId: 'telemetry-freeform',
                  ),
                ],
              ),
            ],
            onSendCorrection: (option, groupId) {
              selected = option;
              selectedGroupId = groupId;
            },
            onRecalibrate: () {},
          ),
        ),
      ),
    );

    await tester.tap(find.text('That is not what happened'));
    await tester.pump();

    expect(selected?.label, 'That is not what happened');
    expect(selected?.semanticValue, 'risk_false_positive');
    expect(selectedGroupId, 'group-risk');
    expect(selected?.label, isNot(selected?.semanticValue));
  });
}
