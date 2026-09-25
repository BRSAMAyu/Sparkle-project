import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';

/// WT373 缺陷扫雷 #2（a11y）· SparkleButton 合并装配双播报红绿契约.
///
/// 缺陷（wt365 U-08 返工探针 G 登记）：SparkleButton 外层
/// `Semantics(label: label)` 与内部 `Text(label)` 同串都进语义树——合并装配
/// 下折叠为单节点后 label 以 `\n` 拼接，读屏播报「重试\n重试」两遍。
///
/// 钉住的不变式（对读屏的可感知性）：
/// 1. 按钮语义名唯一：合并节点 label 恰为语义名一次，不含同串重复；
///    `semanticLabel` 覆盖时视觉文案不得混入播报；
/// 2. 修复不得丢功能：button 语义与语义 tap（辅助技术激活路径）保持可达。
///
/// 手法与 a11y_u08 相同：真实泵入渲染树后从元素→renderObject.debugSemantics
/// 枚举带 label 节点（与 semantics finder 同源）。
void main() {
  /// 当前语义树上「有可读 label」的节点集合。
  Set<SemanticsNode> labeledNodes(WidgetTester tester) {
    final nodes = <SemanticsNode>{};
    for (final el in tester.allElements) {
      if (el is! RenderObjectElement) continue;
      final node = el.renderObject.debugSemantics;
      if (node != null && node.label.trim().isNotEmpty) nodes.add(node);
    }
    return nodes;
  }

  Widget host(Widget child) => MaterialApp(
        home: Scaffold(body: Center(child: child)),
      );

  testWidgets(
    '裸按钮：合并语义节点 label 单播报（不含同串重复）',
    (tester) async {
      final semantics = tester.ensureSemantics();
      var taps = 0;
      await tester.pumpWidget(
        host(
          SparkleButton(
            label: '重试',
            onPressed: () => taps++,
          ),
        ),
      );
      await tester.pump();

      final labeled = labeledNodes(tester);
      expect(labeled, hasLength(1), reason: '整个按钮应只有一个可读语义节点');
      final node = labeled.single;
      // 缺陷形态：合并装配把外层 Semantics(label) 与内部 Text 同串拼接成
      // 「重试\n重试」，读屏播报两遍。
      expect(node.label, '重试', reason: '语义名应单播报，实际「${node.label}」');
      expect(node.flagsCollection.isButton, isTrue);

      // 功能不回退：语义 tap（TalkBack/VoiceOver 激活路径）真实触发回调。
      tester.binding.renderViews
          .map((rv) => rv.owner?.semanticsOwner)
          .whereType<SemanticsOwner>()
          .first
          .performAction(node.id, SemanticsAction.tap);
      await tester.pump();
      expect(taps, 1);
      semantics.dispose();
    },
  );

  testWidgets(
    '合并装配宿主（container 折叠，如状态播报块）：label 不重复',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        host(
          // 复刻 wt365 探针 G 形态：状态播报块 Semantics(container:true) 把
          // 子树折叠合并进单节点（label 按 \n 拼接）。
          Semantics(
            container: true,
            child: SparkleButton(label: '重试', onPressed: () {}),
          ),
        ),
      );
      await tester.pump();

      final merged = find.bySemanticsLabel(RegExp('重试'));
      expect(merged, findsOneWidget);
      final node = tester.getSemantics(merged);
      expect(node.label, '重试', reason: '折叠节点应单播报，实际「${node.label}」');
      expect(node.flagsCollection.isButton, isTrue);
      semantics.dispose();
    },
  );

  testWidgets(
    'semanticLabel 覆盖：语义名唯一且视觉文案不混入播报',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        host(
          SparkleButton(
            label: '重试',
            semanticLabel: '重新加载今日洞察',
            onPressed: () {},
          ),
        ),
      );
      await tester.pump();

      final labeled = labeledNodes(tester);
      expect(labeled, hasLength(1));
      final node = labeled.single;
      expect(
        node.label,
        '重新加载今日洞察',
        reason: '语义名应取 semanticLabel 且不混入视觉文案，实际「${node.label}」',
      );
      expect(node.flagsCollection.isButton, isTrue);
      semantics.dispose();
    },
  );
}
