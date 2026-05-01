import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/contextual_correction_bar.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets(
      'predicted chip uses natural text while preserving semantic value', (
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
                    label: 'risk_false_positive',
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

    expect(find.text('risk_false_positive'), findsNothing);
    expect(find.text('我其实不焦虑，只是忙'), findsOneWidget);
    expect(find.text('判断偏高'), findsOneWidget);

    await tester.tap(find.text('我其实不焦虑，只是忙'));
    await tester.pump();

    expect(find.text('已收到'), findsOneWidget);
    expect(selected?.label, 'risk_false_positive');
    expect(selected?.semanticValue, 'risk_false_positive');
    expect(selectedGroupId, 'group-risk');
  });

  testWidgets('freeform chip opens the independent correction lane', (
    tester,
  ) async {
    var requested = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextualCorrectionBar(
            predictedReplyGroups: [
              AuroraPredictedReplyGroup(
                groupId: 'group-freeform',
                question: 'Was Aurora wrong?',
                questionType: 'assumption_check',
                contextNote: '',
                options: [
                  AuroraPredictedReplyOption(
                    id: 'opt-freeform',
                    label: 'freeform_correction',
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
            onFreeformCorrectionRequested: () => requested = true,
            onRecalibrate: () {},
          ),
        ),
      ),
    );

    expect(find.text('freeform_correction'), findsNothing);
    await tester.tap(find.text('Aurora 理解错了？'));
    await tester.pump();

    expect(requested, isTrue);
  });
}
