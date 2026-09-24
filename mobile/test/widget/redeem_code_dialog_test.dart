import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/data/models/redeem_code_result.dart';
import 'package:sparkle/features/user/presentation/widgets/redeem_code_dialog.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> openDialog(
    WidgetTester tester, {
    required Future<RedeemCodeResult> Function(String) onRedeem,
  }) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => RedeemCodeDialog.show(context, onRedeem: onRedeem),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
  }

  testWidgets('成功核销：提交后弹窗关闭并 toast 档位与到期', (tester) async {
    final submitted = <String>[];
    await openDialog(tester, onRedeem: (code) async {
      submitted.add(code);
      return RedeemCodeResult(
        status: RedeemCodeStatus.success,
        tier: 'pro',
        expiresAt: DateTime(2026, 10, 22),
      );
    },);

    expect(find.text('兑换码'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'SPARK-ABCD-EFGH-JKLM');
    await tester.tap(find.text('兑换'));
    await tester.pumpAndSettle();

    expect(submitted, ['SPARK-ABCD-EFGH-JKLM']);
    expect(find.text('兑换码'), findsNothing); // 弹窗已关
    expect(find.textContaining('兑换成功'), findsOneWidget); // success toast
  });

  testWidgets('已用完码：弹窗不关且展示失败反馈', (tester) async {
    await openDialog(tester, onRedeem: (_) async => const RedeemCodeResult(status: RedeemCodeStatus.exhausted),);

    await tester.enterText(find.byType(TextField), 'SPARK-ABCD-EFGH-JKLM');
    await tester.tap(find.text('兑换'));
    await tester.pumpAndSettle();

    expect(find.text('兑换码'), findsOneWidget); // 弹窗仍在
    expect(find.textContaining('已被使用'), findsOneWidget);
  });

  testWidgets('过期码：展示过期反馈且弹窗保留可改输入', (tester) async {
    await openDialog(tester, onRedeem: (_) async => const RedeemCodeResult(status: RedeemCodeStatus.expired),);

    await tester.enterText(find.byType(TextField), 'SPARK-OLD1-CODE-XXXX');
    await tester.tap(find.text('兑换'));
    await tester.pumpAndSettle();

    expect(find.text('兑换码'), findsOneWidget);
    expect(find.textContaining('已过期'), findsOneWidget);
  });

  testWidgets('取消：不触发核销直接关闭', (tester) async {
    var calls = 0;
    await openDialog(tester, onRedeem: (_) async {
      calls += 1;
      return const RedeemCodeResult(status: RedeemCodeStatus.error);
    },);

    await tester.tap(find.text('取消'));
    await tester.pumpAndSettle();

    expect(calls, 0);
    expect(find.text('兑换码'), findsNothing);
  });
}
