import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/chat/presentation/widgets/collapsible_widget_wrapper.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N17（A-SPEC3 §4.2 改造 #6）验收：chat 域特化披露件的 chevron 状态钉子。
/// CollapsibleWidgetWrapper 已登记为 ExpandableSection 的 chat 域特化
/// （chip 形态 + persistId 持久化）；本测试钉住其折叠/展开语法不漂移。
void main() {
  setUp(() {
    setUpI18nForTesting();
    // 头部 chip 的 onTap 会先走 SensoryFeedbackService.emit（读 prefs），
    // 测试环境给 mock 存量，避免 MissingPluginException 干扰交互断言。
    SharedPreferences.setMockInitialValues({});
  });

  AnimatedRotation chevronOf(WidgetTester tester) =>
      tester.widget<AnimatedRotation>(find.byType(AnimatedRotation));

  testWidgets('默认折叠：chevron 朝下（turns 0），展开内容不在树中',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: CollapsibleWidgetWrapper(
            label: '任务',
            icon: Icons.assignment_rounded,
            child: Text('展开后的完整内容'),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(chevronOf(tester).turns, 0);
    expect(find.text('展开后的完整内容'), findsNothing);
  });

  testWidgets('点击 chip：chevron 旋转半圈（turns 0.5），内容展示',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: CollapsibleWidgetWrapper(
            label: '任务',
            icon: Icons.assignment_rounded,
            child: Text('展开后的完整内容'),
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('任务'));
    await tester.pump(const Duration(milliseconds: 250));
    await tester.pump(const Duration(milliseconds: 250));

    expect(chevronOf(tester).turns, 0.5);
    expect(find.text('展开后的完整内容'), findsOneWidget);
  });

  testWidgets('defaultExpanded：初帧即展开（chevron 0.5，内容在树中）',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: CollapsibleWidgetWrapper(
            label: '任务',
            icon: Icons.assignment_rounded,
            defaultExpanded: true,
            child: Text('展开后的完整内容'),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(chevronOf(tester).turns, 0.5);
    expect(find.text('展开后的完整内容'), findsOneWidget);
  });
}
