import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';
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
    AuroraCorrectionPayload? selectedPayload;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextualCorrectionBar(
            predictedReplyGroups: const [
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
            bandStatus: 'needs_confirm',
            conversationId: 'conversation-1',
            messageId: 'message-1',
            onSendCorrectionPayload: (payload) => selectedPayload = payload,
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
    expect(selectedPayload?.surface, AuroraCorrectionSurface.chat);
    expect(selectedPayload?.source, AuroraCorrectionSource.predictedChip);
    expect(selectedPayload?.label, '我其实不焦虑，只是忙');
    expect(selectedPayload?.semanticValue, 'risk_false_positive');
    expect(selectedPayload?.isDisconfirming, isTrue);
    expect(selectedPayload?.bandStatus, 'needs_confirm');
    expect(selectedPayload?.telemetryId, 'telemetry-risk');
    expect(selectedPayload?.groupId, 'group-risk');
    expect(selectedPayload?.conversationId, 'conversation-1');
    expect(selectedPayload?.messageId, 'message-1');
  });

  testWidgets('freeform chip opens the independent correction lane', (
    tester,
  ) async {
    var requested = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextualCorrectionBar(
            predictedReplyGroups: const [
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
