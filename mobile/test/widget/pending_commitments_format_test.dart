import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/pending_commitments_section.dart';
import '../shared/i18n_test_helper.dart';

/// B1-B / S2 例2：承诺截止时间禁毫秒直出（AUDIT V21「2026-09-20 15:00:00.000」），
/// 文案走 arb（displayDueLabel），时间走 date_formatting 唯一入口。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpI18nForTesting();
  tearDown(tearDownI18n);

  testWidgets('截止行输出「截止: 今天 …」式人话，无毫秒尾巴', (tester) async {
    final due = DateTime.now().add(const Duration(hours: 2));
    await tester.pumpWidget(
      testMaterialApp(
        home: PendingCommitmentsSection(
          items: [
            PendingCommitmentItem(
              id: 'c1',
              summary: '把第三章错题过一遍',
              dueAt: DateTime.parse(
                  '${due.year.toString().padLeft(4, '0')}-${due.month.toString().padLeft(2, '0')}-${due.day.toString().padLeft(2, '0')} 15:00:00.000'),
              subjectType: 'commitment',
            ),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('截止:'), findsOneWidget);
    final dueText =
        tester.widget<Text>(find.textContaining('截止:')).data ?? '';
    expect(dueText.contains('.000'), isFalse, reason: dueText);
    expect(dueText.contains('15:00'), isTrue, reason: dueText);
    expect(find.text('把第三章错题过一遍'), findsOneWidget);
  });
}
