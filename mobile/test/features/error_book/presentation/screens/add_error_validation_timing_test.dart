import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/error_book/presentation/screens/add_error_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N25（A-SPEC5 v1.5）校验三段制时序断言（add_error 屏）：
/// 报告点名「题目≥5 字规则提交才知」——首提交后转 onUserInteraction，
/// 输入到第 5 个字符错误即时消，不必再点一次保存。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> enlargeViewport(WidgetTester tester) async {
    tester.view
      ..physicalSize = const Size(800, 2600)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('未提交不报长度错；提交爆出全量错误；题目写满 5 字即时消错',
      (tester) async {
    await enlargeViewport(tester);
    await tester.pumpWidget(
      ProviderScope(child: testMaterialApp(home: const AddErrorScreen())),
    );
    await tester.pumpAndSettle();

    final questionField = find.byType(TextFormField).at(1);
    final answerField = find.byType(TextFormField).at(2);
    final correctField = find.byType(TextFormField).at(3);

    // ① 未提交：题目 3 个字（<5）不提前报错。
    await tester.enterText(questionField, 'abc');
    await tester.pump();
    expect(find.text('题目内容至少需要 5 个字符'), findsNothing,
        reason: '未提交前不得提前报错（三段制第一段）',);

    // ② 提交：题目过短 + 两处必填错误一并行内爆出。
    await tester.tap(find.widgetWithText(FilledButton, '保存错题'));
    await tester.pump();
    expect(find.text('题目内容至少需要 5 个字符'), findsOneWidget,
        reason: '提交时全量兜底（三段制第二段）',);
    expect(find.text('请输入你的答案'), findsOneWidget);
    expect(find.text('请输入正确答案'), findsOneWidget);

    // ③ 题目补到 5 字 → 即时消错；答案必填错误保持。
    await tester.enterText(questionField, 'abcde');
    await tester.pump();
    expect(find.text('题目内容至少需要 5 个字符'), findsNothing,
        reason: '首提交后输入即校验，改对即时消错（三段制第三段）',);
    expect(find.text('请输入你的答案'), findsOneWidget);
    expect(find.text('请输入正确答案'), findsOneWidget);

    // 字段序 sanity：answerField/correctField 与断言字段一致。
    expect(find.descendant(of: find.byType(TextFormField).at(2), matching: find.text('abcde')),
        findsNothing,);
    await tester.enterText(answerField, '我的答案');
    await tester.pump();
    expect(find.text('请输入你的答案'), findsNothing);
    await tester.enterText(correctField, '正确答案');
    await tester.pump();
    expect(find.text('请输入正确答案'), findsNothing);
  });
}
