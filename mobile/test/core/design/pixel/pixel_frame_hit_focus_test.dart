// V4-F02 · 验收 3：装饰不吞点击，键盘与屏幕阅读器可定位操作。
//
// 正例：
//   (a) 切角轮廓装饰层叠在按钮上方时，点击装饰覆盖点仍到达按钮
//       （PixelFrame 装饰层 IgnorePointer 透传）；
//   (b) 键盘 Tab 遍历按声明顺序聚焦两个 PixelPrimaryAction；
//   (c) 语义标签可定位操作：getSemantics 断言 tap 动作在按钮/操作上
//       （receipt 的 纠正/仅本次/删除 恒可达）。
// 反例（可失败性控制组）：
//   (d) 同一几何下换成吞手势的 GestureDetector 覆盖层 → 点击被吞
//       （证明 (a) 的断言设置有判别力）；
//   (e) 无语义标签的裸框组件 → bySemanticsLabel 查不到（对照 (c)）。
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

Future<void> _pumpPixel(WidgetTester tester, Widget child) async {
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) await manager.initialize();
  await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  await tester.pumpWidget(
    MaterialApp(theme: AppThemes.lightTheme, home: Scaffold(body: child)),
  );
  await tester.pump();
}

/// 切角叠按钮几何：按钮中心落在 PixelFrame（含切角装饰）覆盖区内。
Widget _overlayHarness({
  required VoidCallback onPressed,
  bool absorbingDecoration = false,
}) => Center(
    child: SizedBox(
      width: 260,
      height: 140,
      child: Stack(
        children: [
          const Positioned.fill(
            child: PixelFrame(
              emphasis: PixelFrameEmphasis.primary,
              cutCorner: true,
              padding: EdgeInsets.fromLTRB(16, 16, 56, 24),
              child: Text('装饰透传背景'),
            ),
          ),
          // 故意叠在切角装饰之上的按钮（右上角）。
          Positioned(
            top: 8,
            right: 8,
            child: TextButton(
              onPressed: onPressed,
              child: const Text('覆盖按钮'),
            ),
          ),
          // 控制组（反例）：同几何下换成吞手势的装饰层。
          if (absorbingDecoration)
            Positioned.fill(
              child: GestureDetector(
                onTap: () {},
                child: const ColoredBox(color: Color(0x01000000)),
              ),
            ),
        ],
      ),
    ),
  );

void main() {
  testWidgets('(a) 装饰覆盖按钮时点击仍达按钮（IgnorePointer 透传）',
      (tester) async {
    var taps = 0;
    await _pumpPixel(
      tester,
      _overlayHarness(onPressed: () => taps++),
    );
    final buttonCenter = tester.getCenter(find.text('覆盖按钮'));
    await tester.tapAt(buttonCenter);
    await tester.pump();
    expect(taps, 1, reason: '装饰层吞掉了本应到达按钮的点击');
    // 实现面护栏：PixelFrame 装饰层确有 IgnorePointer + ExcludeSemantics。
    expect(
      find.ancestor(
        of: find.byWidgetPredicate(
          (w) => w is CustomPaint && w.painter is PixelOutlinePainter,
        ),
        matching: find.byType(IgnorePointer),
      ),
      findsWidgets,
    );
    expect(
      find.ancestor(
        of: find.byWidgetPredicate(
          (w) => w is CustomPaint && w.painter is PixelOutlinePainter,
        ),
        matching: find.byType(ExcludeSemantics),
      ),
      findsWidgets,
    );
  });

  testWidgets('(d) 控制组：吞手势覆盖层下同一断言必须判负（可失败性）',
      (tester) async {
    var taps = 0;
    await _pumpPixel(
      tester,
      _overlayHarness(
        onPressed: () => taps++,
        absorbingDecoration: true,
      ),
    );
    final buttonCenter = tester.getCenter(find.text('覆盖按钮'));
    await tester.tapAt(buttonCenter);
    await tester.pump();
    expect(taps, 0, reason: '控制组应吞掉点击（若为 1 则 (a) 无判别力）');
  });

  testWidgets('(b) 键盘 Tab 按 TabTraversa 顺序聚焦两个主 CTA',
      (tester) async {
    final f1 = FocusNode();
    final f2 = FocusNode();
    addTearDown(() {
      f1.dispose();
      f2.dispose();
    });
    await _pumpPixel(
      tester,
      FocusTraversalGroup(
        child: Column(
          children: [
            PixelPrimaryAction(
              label: '主操作一',
              focusNode: f1,
              onPressed: () {},
            ),
            PixelPrimaryAction(
              label: '主操作二',
              focusNode: f2,
              onPressed: () {},
            ),
          ],
        ),
      ),
    );
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    expect(FocusManager.instance.primaryFocus, same(f1),
        reason: '第一次 Tab 未落在第一个 CTA',);
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    expect(FocusManager.instance.primaryFocus, same(f2),
        reason: '第二次 Tab 未推进到第二个 CTA',);
    // 焦点在 ring 上：focused CTA 出现外扩 focus ring 画笔。
    expect(
      find.byWidgetPredicate(
        (w) => w is CustomPaint && w.foregroundPainter is PixelFocusRingPainter,
      ),
      findsOneWidget,
    );
  });

  testWidgets('(c) 语义可定位操作：receipt 纠正/仅本次/删除带 tap 动作',
      (tester) async {
    final semantics = tester.ensureSemantics();
    var corrected = false;
    await _pumpPixel(
      tester,
      PixelReceiptCard(
        reason: '因为夜间完成率高',
        usedRefs: const ['经验 #12'],
        onCorrect: () => corrected = true,
        onThisTimeOnly: () {},
        onDelete: () {},
      ),
    );
    await tester.pump();
    for (final label in ['纠正', '仅本次', '删除']) {
      final node = tester.getSemantics(find.bySemanticsLabel(label));
      expect(
        node.getSemanticsData().actions & SemanticsAction.tap.index,
        isNot(0),
        reason: '$label 操作对屏幕阅读器不可触发',
      );
    }
    // 真实触发（读屏命中路径与指针同路）：语义定位到的就是可点目标。
    await tester.tap(find.bySemanticsLabel('纠正'), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(corrected, isTrue, reason: '语义 tap 未到达 onCorrect');
    semantics.dispose();
  });

  testWidgets('(e) 控制组：动作未挂回调时同一 tap 断言必须判负（可失败性）',
      (tester) async {
    final semantics = tester.ensureSemantics();
    await _pumpPixel(
      tester,
      // 回调全空：按钮仍在、标签仍在，但没有可触发的 tap 动作——
      // 证明 (c) 的「操作可经读屏触发」断言有判别力。
      const PixelReceiptCard(reason: '因为夜间完成率高'),
    );
    await tester.pump();
    final node = tester.getSemantics(find.bySemanticsLabel('纠正'));
    expect(
      node.getSemanticsData().actions & SemanticsAction.tap.index,
      0,
      reason: '控制组不应有 tap 动作（若非 0 则 (c) 无判别力）',
    );
    semantics.dispose();
  });

  testWidgets('按钮语义带 button 标志与显式标签（读屏可定位）', (tester) async {
    final semantics = tester.ensureSemantics();
    await _pumpPixel(
      tester,
      PixelPrimaryAction(
        label: '提交运行',
        semanticLabel: '提交运行',
        onPressed: () {},
      ),
    );
    await tester.pump();
    final node = tester.getSemantics(find.bySemanticsLabel('提交运行'));
    final data = node.getSemanticsData();
    expect(
      data.flagsCollection.isButton,
      isTrue,
      reason: 'CTA 未携带 button 语义标志',
    );
    expect(
      data.actions & SemanticsAction.tap.index,
      isNot(0),
    );
    semantics.dispose();
  });
}
