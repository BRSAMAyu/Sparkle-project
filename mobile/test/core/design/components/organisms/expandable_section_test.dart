import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/organisms/expandable_section.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N17（A-SPEC3 §4.2 改造 #6）验收：展开族唯一 owner 语法钉子——
/// chevron 旋转状态（折叠 0 → 展开 0.5 圈）、统一动画档、头部披露语义。
void main() {
  setUp(setUpI18nForTesting);

  AnimatedRotation chevronOf(WidgetTester tester) =>
      tester.widget<AnimatedRotation>(find.byType(AnimatedRotation));

  testWidgets('折叠初态：chevron 朝下（turns 0），动画档为 owner 统一档',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ExpandableSection(
            title: '披露区',
            child: Text('内容体'),
          ),
        ),
      ),
    );
    await tester.pump();

    final chevron = chevronOf(tester);
    expect(chevron.turns, 0);
    expect(
      chevron.duration,
      ExpandableSection.expandDuration,
      reason: 'chevron 必须用 ExpandableSection.expandDuration 统一档',
    );
    // 语义钉子：头部披露控件携带 button 角色，折叠态 expanded=false。
    final semantics = tester.widget<Semantics>(
      find.byWidgetPredicate((w) => w is Semantics && (w.properties.button ?? false)),
    );
    expect(semantics.properties.expanded, false);
  });

  testWidgets('点击展开：chevron 旋转半圈（turns 0.5），内容可达，语义翻转',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ExpandableSection(
            title: '披露区',
            child: Text('内容体'),
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('披露区'));
    await tester.pumpAndSettle();

    expect(chevronOf(tester).turns, 0.5);
    expect(tester.getRect(find.text('内容体')).height, greaterThan(0));
    final semantics = tester.widget<Semantics>(
      find.byWidgetPredicate((w) => w is Semantics && (w.properties.button ?? false)),
    );
    expect(semantics.properties.expanded, true);
  });

  testWidgets('再点收起：chevron 回正（turns 0），动画档不随状态改变',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ExpandableSection(
            title: '披露区',
            child: Text('内容体'),
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.text('披露区'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('披露区'));
    await tester.pumpAndSettle();

    expect(chevronOf(tester).turns, 0);
    expect(chevronOf(tester).duration, ExpandableSection.expandDuration);
  });

  testWidgets('initiallyExpanded：初帧即展开态（chevron 0.5，无需动画）',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: ExpandableSection(
            title: '披露区',
            initiallyExpanded: true,
            child: Text('内容体'),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(chevronOf(tester).turns, 0.5);
  });

  testWidgets('统一动画档即 AnimationSystem.quick 档（150ms），不引入散落时长',
      (tester) async {
    expect(ExpandableSection.expandDuration, const Duration(milliseconds: 150));
  });
}
