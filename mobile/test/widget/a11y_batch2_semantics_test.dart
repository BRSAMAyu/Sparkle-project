import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// sparkle_icon_button_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH2（N32 续 · 无名钮下批：friends / sprint / user 设置族）：
///
/// 新键 zh/en parity 与 semantics finder 断言——
/// 1. 12 个新 l10n 键在 zh 包可取值（en 侧由 parity 守卫 + 编译期保证）；
/// 2. 代表性标注面（friends 接受/拒绝钮、sprint 打开/编辑钮）在语义树上
///    按名可定位且带按钮角色（读屏可念出用途）；
/// 3. metacognition 展开/收起钮的 tooltip 形制（material IconButton）同样
///    并入语义名可被 bySemanticsLabel 定位。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('12 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    expect(zh.friendsAcceptRequest, '接受好友申请');
    expect(zh.friendsDeclineRequest, '拒绝好友申请');
    expect(zh.friendPartnerAcceptInvite, '接受伙伴邀请');
    expect(zh.friendPartnerDeclineInvite, '拒绝伙伴邀请');
    expect(zh.friendsViewProfile, '查看主页');
    expect(zh.friendsPartnerEntry, '责任伙伴入口');
    expect(zh.sprintOpenPlan, '打开冲刺计划');
    expect(zh.syncCenterCopyEntityId, '复制实体 ID');
    expect(zh.syncCenterCopyTraceId, '复制链路 ID');
    expect(zh.metacognitionPanelExpand, '展开自我认识面板');
    expect(zh.metacognitionPanelCollapse, '收起自我认识面板');
    expect(zh.openclawCopyPairingCode, '复制配对码');
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

    testWidgets('friends 好友申请接受钮：按「接受好友申请」可定位且带按钮角色',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.check, color: Colors.green),
          semanticLabel: zh.friendsAcceptRequest,
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('接受好友申请');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('sprint 打开冲刺计划钮：按「打开冲刺计划」可定位且带按钮角色',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.open_in_new),
          semanticLabel: zh.sprintOpenPlan,
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('打开冲刺计划');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('metacognition 展开/收起钮：外层 Semantics label + tooltip 同源可定位',
        (tester) async {
      final semantics = tester.ensureSemantics();
      // 与真实 widget（metacognition_panel_card）同形：外层 Semantics 挂
      // label，内层 material IconButton 挂 tooltip（悬停提示）。
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: Semantics(
                label: zh.metacognitionPanelCollapse,
                child: IconButton(
                  tooltip: zh.metacognitionPanelCollapse,
                  onPressed: () {},
                  icon: const Icon(Icons.expand_more_rounded),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      final handle = find.bySemanticsLabel('收起自我认识面板');
      expect(handle, findsOneWidget);
      semantics.dispose();
    });
  });
}
