import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// a11y_batch3_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH4（N32 续 · 无名钮批四：seed_library / error_book / chat
/// 非群组 / community 非群组 + 域外 3 双源漂移 + metacognition 双节点
/// 形制修正）：
///
/// 1. 10 个新 l10n 键 zh 侧可取值（en 侧由 parity 守卫 + 编译期保证）；
/// 2. 甲式（Tooltip + SparkleIconButton semanticLabel 同键）与乙式
///    （material IconButton tooltip + Icon semanticLabel 同键）代表面
///    按名可定位且带按钮角色（semantics finder 断言）；
/// 3. 双节点反形制修正断言——外挂 Semantics(label:) 会把 label 与按钮
///    拆成两个语义节点（label 节点无按钮角色）；乙式单节点下
///    bySemanticsLabel 命中的节点必须自身 isButton；
/// 4. 两态钮按当前态命名（metacognition 展开/收起形制）。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('10 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    expect(zh.seedTagAdd, '添加标签');
    expect(zh.seedLibraryAddItem, '添加条目');
    expect(zh.seedLibraryImportItems, '导入条目');
    expect(zh.communityChatOpenTools, '打开消息工具');
    expect(zh.communityChatBackToText, '返回文字输入');
    expect(zh.communityChatSwipeToSwitch, '左右滑动切换输入模式');
    expect(zh.communityChatQuickShare, '打开快捷分享');
    expect(zh.communityChatCancelQuote, '取消引用消息');
    expect(zh.communityPreviousMonth, '上个月');
    expect(zh.communityNextMonth, '下个月');
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
        '甲式（error_book 退出复习形制）：Tooltip+semanticLabel 同键，'
        'Tooltip 隐藏期仍按名可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 review_screen / plan_history 恢复钮 / growth 归档钮同形。
      await pumpButton(
        tester,
        Tooltip(
          message: zh.ebExitReview,
          child: SparkleIconButton(
            icon: const Icon(Icons.close),
            semanticLabel: zh.ebExitReview,
            onPressed: () {},
          ),
        ),
      );

      final handle = find.bySemanticsLabel('退出复习');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '乙式（community_chat_input 打开工具形制）：tooltip+Icon '
        'semanticLabel 同键——单节点有名按钮（双节点反形制下 label 节点'
        '无按钮角色，本断言即钉死单节点）', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        IconButton(
          tooltip: zh.communityChatOpenTools,
          onPressed: () {},
          icon: Icon(
            Icons.add_circle_outline_rounded,
            semanticLabel: zh.communityChatOpenTools,
          ),
        ),
      );

      final handle = find.bySemanticsLabel('打开消息工具');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '两态钮按当前态命名（metacognition 展开/收起形制）：'
        '态翻转后语义名随之翻转', (tester) async {
      final semantics = tester.ensureSemantics();
      var expanded = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: StatefulBuilder(
                builder: (context, setState) => IconButton(
                  tooltip: expanded
                      ? zh.metacognitionPanelCollapse
                      : zh.metacognitionPanelExpand,
                  onPressed: () => setState(() => expanded = !expanded),
                  icon: Icon(
                    Icons.expand_more_rounded,
                    semanticLabel: expanded
                        ? zh.metacognitionPanelCollapse
                        : zh.metacognitionPanelExpand,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.bySemanticsLabel('展开自我认识面板'), findsOneWidget);
      expect(find.bySemanticsLabel('收起自我认识面板'), findsNothing);

      await tester.tap(find.byIcon(Icons.expand_more_rounded));
      await tester.pump();

      expect(find.bySemanticsLabel('收起自我认识面板'), findsOneWidget);
      expect(find.bySemanticsLabel('展开自我认识面板'), findsNothing);
      semantics.dispose();
    });

    testWidgets(
        'SparkleIconButton semanticLabel 反推链仍生效（seed_library '
        ' AppBar 形制）：按名可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 seed_library_detail / list AppBar 五钮同形（乙式反推链之外的
      // 甲式裸挂形制）。
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: Icon(
            Icons.filter_list,
            color: DS.textSecondary,
          ),
          semanticLabel: zh.seedLibraryFilter,
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('筛选');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });
  });
}
