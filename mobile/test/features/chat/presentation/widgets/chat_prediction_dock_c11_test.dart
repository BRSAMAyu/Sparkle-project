import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_prediction_dock.dart';
import '../../../../shared/i18n_test_helper.dart';

/// C-11 裁决回归：话术 chip ≤3 填入式 + §8.2-1 建议卡默认收起。
void main() {
  setUp(setUpI18nForTesting);

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('resolveChipBudgets（C-11 chip ≤3 预算）', () {
    test('话术优先占 2 席，预测占剩余 1 席', () {
      final (predictions, starters) = ChatPredictionDock.resolveChipBudgets(
        predictionCount: 5,
        starterCount: 2,
      );
      expect(starters, 2);
      expect(predictions, 1);
    });

    test('无话术时预测至多 3', () {
      final (predictions, starters) = ChatPredictionDock.resolveChipBudgets(
        predictionCount: 6,
        starterCount: 0,
      );
      expect(starters, 0);
      expect(predictions, 3);
    });

    test('合计永不超 3', () {
      for (var p = 0; p <= 6; p++) {
        for (var s = 0; s <= 4; s++) {
          final (rp, rs) = ChatPredictionDock.resolveChipBudgets(
            predictionCount: p,
            starterCount: s,
          );
          expect(rp + rs, lessThanOrEqualTo(3));
        }
      }
    });
  });

  group('ChatPredictionDock 默认收起 + 填入式', () {
    Widget host({
      required List<String> promptStarters,
      required ValueChanged<String> onPromptSelected,
    }) {
      return ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: Center(
              child: ChatPredictionDock(
                promptStarters: promptStarters,
                onPromptSelected: onPromptSelected,
              ),
            ),
          ),
        ),
      );
    }

    /// 泄掉 dock 的 18s followup 定时器，避免测试收尾报 pending timer。
    Future<void> flushTimers(WidgetTester tester) async {
      await tester.pump(const Duration(seconds: 20));
    }

    testWidgets('默认收起为单行 headline（输入条关联区），无 chip 常驻',
        (tester) async {
      await tester.pumpWidget(host(
        promptStarters: const ['帮我整理错题', '讲解这道题'],
        onPromptSelected: (_) {},
      ));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('帮我整理错题'), findsNothing);
      expect(find.text('讲解这道题'), findsNothing);
      // 收起单行存在（展开控件图标）。
      expect(find.byIcon(Icons.unfold_more_rounded), findsOneWidget);

      await flushTimers(tester);
    });

    testWidgets('展开态话术 chip ≤3 且点按走填入回调（不直接发送）', (tester) async {
      var filledCount = 0;
      String? lastFilled;
      await tester.pumpWidget(host(
        promptStarters: const ['帮我整理错题', '讲解这道题', '出三道练习题', '换一个思路'],
        onPromptSelected: (prompt) {
          filledCount++;
          lastFilled = prompt;
        },
      ));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      await tester.tap(find.byIcon(Icons.unfold_more_rounded));
      await tester.pump(const Duration(milliseconds: 50));

      // 只显示前 2 条话术（预算 2 席）。
      expect(find.text('帮我整理错题'), findsOneWidget);
      expect(find.text('讲解这道题'), findsOneWidget);
      expect(find.text('出三道练习题'), findsNothing);
      expect(find.text('换一个思路'), findsNothing);

      await tester.tap(find.text('帮我整理错题'));
      await tester.pump(const Duration(milliseconds: 50));

      expect(filledCount, 1, reason: '点 chip 只触发填入回调');
      expect(lastFilled, '帮我整理错题');

      await flushTimers(tester);
    });
  });
}
