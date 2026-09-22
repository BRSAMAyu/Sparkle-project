// S11 回归 · 最低达标线空态卡不得携带「确认」主 CTA（批1-A 信任地基）。
//
// AUDIT S11 / D9 空态规范：空态必须回答「为什么空」，且只允许
// 单一明确 CTA 或无 CTA。此前 `if (!criteria.isConfirmed)` 独立于
// emptiness 渲染——thresholds 为空时「还没有最低达标线」文案下面
// 仍挂着一颗棕色主 CTA「确认」（空无一物时确认什么？）。
// 修复后：无达标线 → 纯文案；有达标线且未确认 → 确认/修改；
// 已确认 → 无操作按钮。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/goal/presentation/widgets/minimum_criteria_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

Widget _wrap(Widget child) => MaterialApp(
      locale: const Locale('en'),
      supportedLocales: const [Locale('en'), Locale('zh')],
      localizationsDelegates: const [AppLocalizations.delegate],
      home: Scaffold(body: child),
    );

void main() {
  testWidgets('空达标线：只渲染空态文案，不出现「确认」主 CTA', (tester) async {
    await tester.pumpWidget(_wrap(MinimumCriteriaCard(
      criteria: const MinimumAcceptanceCriteria(
        description: '',
        status: 'pending_confirmation',
        thresholds: [],
      ),
      onConfirm: () {},
    ),),);

    expect(find.byType(FilledButton), findsNothing,
        reason: '空态卡不得携带主 CTA（S11 / D9）',);
    expect(find.text('No minimum bar yet. Start with the smallest step for today.'),
        findsOneWidget, reason: '空态必须解释为什么空',);
  });

  testWidgets('有达标线且未确认：渲染「确认」主 CTA', (tester) async {
    await tester.pumpWidget(_wrap(MinimumCriteriaCard(
      criteria: const MinimumAcceptanceCriteria(
        description: '',
        status: 'pending_confirmation',
        thresholds: [
          CriteriaThreshold(id: 'c1', label: '图论概念梳理完成', met: false),
        ],
      ),
      onConfirm: () {},
    ),),);

    expect(find.byType(FilledButton), findsOneWidget);
    expect(find.text('Confirm'), findsOneWidget);
  });

  testWidgets('已确认：不渲染「确认」按钮', (tester) async {
    await tester.pumpWidget(_wrap(MinimumCriteriaCard(
      criteria: const MinimumAcceptanceCriteria(
        description: '',
        status: 'confirmed',
        thresholds: [
          CriteriaThreshold(id: 'c1', label: '图论概念梳理完成', met: true),
        ],
      ),
      onConfirm: () {},
    ),),);

    expect(find.byType(FilledButton), findsNothing);
  });
}
