import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// a11y_batch5_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH6B（N32 收口批 · 单钮长尾清零）：
///
/// 1. 4 个新 l10n 键 zh 侧可取值（en 侧由 l10n regen parity 守卫 +
///    编译期保证；批内另有 5 个既有键复用：back / close / commonRefresh /
///    share / photonRedeemProEntryTooltip）；
/// 2. 甲式（SparkleIconButton semanticLabel）与乙式（material IconButton
///    tooltip + Icon semanticLabel 同键）代表面按名可定位且带按钮角色
///    （semantics finder 断言，乙式钉死单节点）；
/// 3. 两态钮按当前态命名（plan_context_summary 展开形制，照批 5 置顶形制）；
/// 4. 全域收口由 a11y_batch2_domain_labels_guard_test 静态守卫承载
///    （剩余域全量入扫 + 6A 在航豁免登记）。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('4 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    // photon（1）
    expect(zh.ptAmountSelect, '选择转账数量');
    // task（1）
    expect(zh.taskClearDueDate, '清除截止日期');
    // plan（2，两态对）
    expect(zh.planContextExpand, '展开计划上下文');
    expect(zh.planContextCollapse, '收起计划上下文');
  });

  group('批域标注面 semantics finder 断言', () {
    Future<void> pumpButton(WidgetTester tester, Widget button) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            accessibilitySettingsProvider
                .overrideWith(_StubAccessibilitySettingsNotifier.new),
          ],
          child: MaterialApp(home: Scaffold(body: Center(child: button))),
        ),
      );
      await tester.pump();
    }

    testWidgets(
        '甲式（back 返回形制）：SparkleIconButton semanticLabel '
        '按名可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 auth/calendar/cognitive/focus/leaderboard/photon/plan/report/
      // reviews/simulation/task 各域 AppBar 返回钮同形（本批 19 处 back
      // 复用既有键）。
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          semanticLabel: zh.back,
          onPressed: () {},
          variant: ButtonVariant.ghost,
        ),
      );

      final handle = find.bySemanticsLabel('返回');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '甲式两态钮按当前态命名（plan_context_summary 展开形制）：'
        '态翻转后语义名随之翻转', (tester) async {
      final semantics = tester.ensureSemantics();
      var expanded = false;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            accessibilitySettingsProvider
                .overrideWith(_StubAccessibilitySettingsNotifier.new),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: Center(
                child: StatefulBuilder(
                  builder: (context, setState) => SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    semanticLabel: expanded
                        ? zh.planContextCollapse
                        : zh.planContextExpand,
                    icon: Icon(
                      expanded
                          ? Icons.keyboard_arrow_up_rounded
                          : Icons.keyboard_arrow_down_rounded,
                    ),
                    onPressed: () => setState(() => expanded = !expanded),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.bySemanticsLabel('展开计划上下文'), findsOneWidget);
      expect(find.bySemanticsLabel('收起计划上下文'), findsNothing);

      await tester.tap(find.byIcon(Icons.keyboard_arrow_down_rounded));
      await tester.pump();

      expect(find.bySemanticsLabel('收起计划上下文'), findsOneWidget);
      expect(find.bySemanticsLabel('展开计划上下文'), findsNothing);
      semantics.dispose();
    });
  });

  testWidgets(
      '乙式（execution_result_renderer 关闭形制）：tooltip+Icon semanticLabel '
      '同键——单节点有名按钮（label 节点自身 isButton，钉死单节点）',
      (tester) async {
    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: IconButton(
              tooltip: zh.close,
              onPressed: () {},
              icon: Icon(
                Icons.close_rounded,
                semanticLabel: zh.close,
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    final handle = find.bySemanticsLabel('关闭');
    expect(handle, findsOneWidget);
    expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
    semantics.dispose();
  });
}
