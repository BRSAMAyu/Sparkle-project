import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// a11y_batch4_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH5（N32 续 · 无名钮批五：memory / achievement / home / tools
/// 四域清零）：
///
/// 1. 18 个新 l10n 键 zh 侧可取值（en 侧由 l10n regen parity 守卫 +
///    编译期保证；批内另有 8 个既有键复用：back / close / commonRefresh /
///    share / commonClear / achievementMapFocusTooltip / taskCompleteTask /
///    toolsWbDelete）；
/// 2. 甲式（SparkleIconButton semanticLabel）与乙式（material IconButton
///    tooltip + Icon semanticLabel 同键）代表面按名可定位且带按钮角色
///    （semantics finder 断言）；
/// 3. 单节点钉死——乙式下 bySemanticsLabel 命中的节点必须自身 isButton
///    （外挂 Semantics 反形制会把 label 拆成无角色的独立节点）；
/// 4. 两态钮按当前态命名（achievement 置顶形制）。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('18 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    // memory（5）
    expect(zh.memoryDetailCopy, '复制详情');
    expect(zh.memoryDetailExport, '导出详情');
    expect(zh.memoryDetailEvidence, '查看证据');
    expect(zh.memoryCommitmentResolve, '兑现承诺');
    expect(zh.memoryCommitmentDismiss, '忽略承诺');
    // achievement（2）
    expect(zh.achievementPin, '置顶成就');
    expect(zh.achievementUnpin, '取消置顶成就');
    // home（4）
    expect(zh.homePredictedIntentExpand, '展开系统预测');
    expect(zh.homePredictedIntentCollapse, '收起系统预测');
    expect(zh.homeRecentInsightsExpand, '展开近期洞察');
    expect(zh.homeRecentInsightsCollapse, '收起近期洞察');
    // tools（7）
    expect(zh.toolsSearchClear, '清除搜索');
    expect(zh.toolsPinTool, '置顶工具');
    expect(zh.toolsUnpinTool, '取消置顶工具');
    expect(zh.toolsTransClearInput, '清空原文');
    expect(zh.toolsTransFavorite, '收藏译文');
    expect(zh.toolsTransUnfavorite, '取消收藏译文');
    expect(zh.toolsCalcReuseHistory, '复用该算式');
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
        '甲式（memory_detail 返回形制）：SparkleIconButton semanticLabel '
        '按名可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 memory_detail / memory_panel / understanding / achievement 族 /
      // weather_guide / task_monitor 同形。
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
        '乙式（pending_commitments 兑现承诺形制）：tooltip+Icon semanticLabel '
        '同键——单节点有名按钮（双节点反形制下 label 节点无按钮角色，'
        '本断言即钉死单节点）', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 evidence_drawer 关闭 / tool_library 搜索清除 / translator 清空
      // 原文 / wordbook 删除 / calculator 复用算式同形。
      await pumpButton(
        tester,
        IconButton(
          tooltip: zh.memoryCommitmentResolve,
          onPressed: () {},
          icon: Icon(
            Icons.check,
            size: 16,
            semanticLabel: zh.memoryCommitmentResolve,
          ),
        ),
      );

      final handle = find.bySemanticsLabel('兑现承诺');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '两态钮按当前态命名（achievement 置顶形制）：态翻转后语义名随之翻转',
        (tester) async {
      final semantics = tester.ensureSemantics();
      var pinned = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: StatefulBuilder(
                builder: (context, setState) => IconButton(
                  tooltip: pinned
                      ? zh.achievementUnpin
                      : zh.achievementPin,
                  onPressed: () => setState(() => pinned = !pinned),
                  icon: Icon(
                    pinned ? Icons.push_pin : Icons.push_pin_outlined,
                    semanticLabel: pinned
                        ? zh.achievementUnpin
                        : zh.achievementPin,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.bySemanticsLabel('置顶成就'), findsOneWidget);
      expect(find.bySemanticsLabel('取消置顶成就'), findsNothing);

      await tester.tap(find.byIcon(Icons.push_pin_outlined));
      await tester.pump();

      expect(find.bySemanticsLabel('取消置顶成就'), findsOneWidget);
      expect(find.bySemanticsLabel('置顶成就'), findsNothing);
      semantics.dispose();
    });

    testWidgets(
        '同域双钮各归其名（memory_detail AppBar 三钮形制）：copy/export/'
        'evidence 各自按名可定位', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SparkleIconButton(
              icon: const Icon(Icons.copy),
              semanticLabel: zh.memoryDetailCopy,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
            SparkleIconButton(
              icon: const Icon(Icons.file_download),
              semanticLabel: zh.memoryDetailExport,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
            SparkleIconButton(
              icon: const Icon(Icons.link),
              semanticLabel: zh.memoryDetailEvidence,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
      );

      expect(find.bySemanticsLabel('复制详情'), findsOneWidget);
      expect(find.bySemanticsLabel('导出详情'), findsOneWidget);
      expect(find.bySemanticsLabel('查看证据'), findsOneWidget);
      semantics.dispose();
    });
  });
}
