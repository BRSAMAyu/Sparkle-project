import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// a11y_batch2_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH3（N32 续 · 无名钮批三：群组族 / galaxy / insights /
/// plan_create + bare Icon「Semantics+tooltip 同源」形制统一）：
///
/// 1. 9 个新 l10n 键 zh 侧可取值（en 侧由 parity 守卫 + 编译期保证）；
/// 2. 代表性标注面按名可定位且带按钮角色（semantics finder 断言）；
/// 3. 同源形制双断言——
///    a. Tooltip 包装的 SparkleIconButton（squad 入口形制）：按钮名由
///       semanticLabel 承载（与 Tooltip message 同一 l10n 键）；隐藏期
///       Tooltip 只挂 semantics.tooltip 不构成按钮名，semanticLabel 是
///       按钮名唯一事实源；
///    b. bare material IconButton（galaxy 控件/plan 移除任务/群聊清除
///       形制）：tooltip 与 Icon semanticLabel 同常量——名字、按钮角色
///       与 tap 动作合并在同一语义节点播报（widget 实测：外挂
///       Semantics(label:) 形制会把 label 与按钮拆成两个节点）。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('9 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    expect(zh.groupMembersInvite, '邀请成员');
    expect(zh.groupDetailMoreOptions, '更多群组操作');
    expect(zh.groupDetailEditAnnouncement, '编辑公告');
    expect(zh.groupDiscoverCreateGroup, '创建群组');
    expect(zh.groupKnowledgeMarkOfficial, '设为官方资料');
    expect(zh.groupKnowledgeUnmarkOfficial, '取消官方资料');
    expect(zh.groupKnowledgeSwitchToList, '切换为列表视图');
    expect(zh.groupKnowledgeSwitchToGrid, '切换为网格视图');
    expect(zh.planCreateRemoveTask, '移除该任务');
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

    testWidgets('galaxy 草稿箱返回钮：按「返回」可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          semanticLabel: zh.back,
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('返回');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('insights 预测刷新钮：按「刷新」可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.refresh),
          semanticLabel: zh.commonRefresh,
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('刷新');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('squad 创建入口（Tooltip+semanticLabel 同源）：Tooltip 隐藏期仍按名可定位',
        (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 squad_list_screen 同形：外层 Tooltip（悬停提示，隐藏期零语义），
      // 内层 SparkleIconButton 的 semanticLabel 与 message 同一 l10n 键。
      await pumpButton(
        tester,
        Tooltip(
          message: zh.squadCreateEntry,
          child: SparkleIconButton(
            icon: const Icon(Icons.add),
            semanticLabel: zh.squadCreateEntry,
            onPressed: () {},
          ),
        ),
      );

      final handle = find.bySemanticsLabel('创建小队');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('bare material IconButton（tooltip+Icon semanticLabel 同常量）：单节点有名按钮',
        (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 galaxy_controls / plan_create 移除任务 / 群聊清除钮同形：
      // tooltip 与 Icon semanticLabel 同一常量——隐藏期 Tooltip 只挂
      // semantics.tooltip（非按钮名），名字由 Icon semanticLabel 反推
      // 上提，与按钮角色/tap 动作合并在同一语义节点播报。
      await pumpButton(
        tester,
        IconButton(
          tooltip: zh.planCreateRemoveTask,
          onPressed: () {},
          icon: Icon(
            Icons.delete_outline_rounded,
            semanticLabel: zh.planCreateRemoveTask,
          ),
        ),
      );

      final handle = find.bySemanticsLabel('移除该任务');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });
  });
}
