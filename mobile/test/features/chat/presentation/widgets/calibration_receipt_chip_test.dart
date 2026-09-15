import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/calibration_receipt_chip.dart';
import 'package:sparkle/features/chat/presentation/widgets/context_receipt_bar.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('renders backend calibration summary and can be dismissed',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: CalibrationReceiptChip(
            receipt: {
              'receipt_type': 'calibration_receipt',
              'correction_id': 'corr-1',
              'summary': {
                'zh': 'Aurora 调整了关于压力判断的理解',
                'en': 'Aurora adjusted its read on pressure',
              },
              'what_changed': '把压力判断的置信度降下来',
              'why_changed': '你说明只是临时赶进度',
              'next_time': '下次会先确认再提醒',
              'semantic_value': 'risk_false_positive_internal',
              'affected_states': ['user.risk.stress'],
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Aurora 调整了关于压力判断的理解'), findsOneWidget);
    expect(find.text('把压力判断的置信度降下来'), findsNothing);
    expect(find.text('risk_false_positive_internal'), findsNothing);
    expect(find.text('user.risk.stress'), findsNothing);

    await tester.tap(find.byIcon(Icons.close_rounded));
    await tester.pumpAndSettle();

    expect(find.text('Aurora 调整了关于压力判断的理解'), findsNothing);
  });

  testWidgets('expands inline through context receipt metadata',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ContextReceiptBar(
            rawMetadata: {
              'calibration_receipt': json.encode({
                'receipt_type': 'calibration_receipt',
                'correction_id': 'corr-2',
                'summary': 'Aurora 调整了关于计划节奏的理解',
                'what_changed': '把下一步建议从加速改成先稳定',
                'why_changed': '你说今天只适合低负荷推进',
                'next_time': '下次会优先给更轻的开始动作',
                'semantic_value': 'strategy_adjust_internal',
              }),
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Aurora 调整了关于计划节奏的理解'), findsOneWidget);

    await tester.tap(find.text('Aurora 调整了关于计划节奏的理解'));
    await tester.pumpAndSettle();

    expect(find.text('调整了什么'), findsOneWidget);
    expect(find.text('把下一步建议从加速改成先稳定'), findsOneWidget);
    expect(find.text('为什么调整'), findsOneWidget);
    expect(find.text('你说今天只适合低负荷推进'), findsOneWidget);
    expect(find.text('下次会怎样'), findsOneWidget);
    expect(find.text('下次会优先给更轻的开始动作'), findsOneWidget);
    expect(find.text('strategy_adjust_internal'), findsNothing);
  });
}
