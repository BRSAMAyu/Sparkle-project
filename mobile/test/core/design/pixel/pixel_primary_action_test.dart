// V4-F02 · PrimaryAction 合同：loading 不改宽度 / 重复点击禁写 /
// focus ring 在切角外仍可见 / classic 降级。
import 'package:flutter/material.dart';
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

Size _ctaSize(WidgetTester tester) =>
    tester.getSize(find.byType(PixelPrimaryAction));

void main() {
  testWidgets('loading 切换前后按钮几何恒等（loading 不改宽度）',
      (tester) async {
    await _pumpPixel(
      tester,
      Center(
        child: PixelPrimaryAction(
          label: '开始专注',
          icon: Icons.play_arrow,
          onPressed: () {},
        ),
      ),
    );
    final idle = _ctaSize(tester);

    await _pumpPixel(
      tester,
      Center(
        child: PixelPrimaryAction(
          label: '开始专注',
          icon: Icons.play_arrow,
          loading: true,
          onPressed: () {},
        ),
      ),
    );
    final loading = _ctaSize(tester);

    expect(loading.width, idle.width,
        reason: 'loading 指示器改变了按钮宽度（应叠加不占位）',);
    expect(loading.height, idle.height);
    // loading 中指示器可见、标签透明但仍参与布局（宽度守恒的机制面）。
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('开始专注'), findsOneWidget);
  });

  testWidgets('重复点击禁写：锁存窗内第二次 press 不触发回调', (tester) async {
    var calls = 0;
    await _pumpPixel(
      tester,
      Center(
        child: PixelPrimaryAction(
          label: '提交',
          onPressed: () => calls++,
        ),
      ),
    );
    // 同帧双击：两次 tap 都落在重建之前。
    await tester.tap(find.byType(PixelPrimaryAction), warnIfMissed: false);
    await tester.tap(find.byType(PixelPrimaryAction), warnIfMissed: false);
    await tester.pump();
    expect(calls, 1, reason: '同帧双击穿透了禁写锁存');
    // 走完锁存窗（press 动效预算 80ms），不留挂起 Timer。
    await tester.pump(const Duration(milliseconds: 120));
  });

  testWidgets('loading 期间 press 禁写（onPressed 恒不触发）', (tester) async {
    var calls = 0;
    await _pumpPixel(
      tester,
      Center(
        child: PixelPrimaryAction(
          label: '提交',
          loading: true,
          onPressed: () => calls++,
        ),
      ),
    );
    await tester.tap(find.byType(PixelPrimaryAction), warnIfMissed: false);
    await tester.pump();
    expect(calls, 0, reason: 'loading 态仍可触发写入');
    await tester.pump(const Duration(milliseconds: 120));
  });

  testWidgets('focus ring 画在按钮盒外侧（切角外仍可见）', (tester) async {
    final node = FocusNode();
    addTearDown(node.dispose);
    await _pumpPixel(
      tester,
      Center(
        child: PixelPrimaryAction(
          label: '聚焦我',
          focusNode: node,
          onPressed: () {},
        ),
      ),
    );
    // 未聚焦：无 ring。
    expect(
      find.byWidgetPredicate(
        (w) => w is CustomPaint && w.foregroundPainter is PixelFocusRingPainter,
      ),
      findsNothing,
    );
    node.requestFocus();
    await tester.pump();
    await tester.pump();
    // 聚焦：ring 出现；ring 的绘制矩形外扩 2dp（盒外侧）。
    final ringFinder = find.byWidgetPredicate(
      (w) => w is CustomPaint && w.foregroundPainter is PixelFocusRingPainter,
    );
    expect(ringFinder, findsOneWidget);
    final ringBox = tester.getSize(ringFinder);
    final buttonBox = tester.getSize(find.byType(PixelPrimaryAction));
    // ring 层覆盖整盒（外扩部分由 painter 越界绘制，父级已留呼吸位）。
    expect(ringBox.height, buttonBox.height - 6 /* 两侧 3dp 呼吸位 */);
  });

  testWidgets('classic 降级：标准圆角、无像素档、按钮可用（零差量红线）',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    final manager = ThemeManager();
    if (!manager.initialized) await manager.initialize();
    await manager.setPixelPreviewProfile(PixelPreviewProfile.classic);
    var calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: Center(
            child: PixelPrimaryAction(
              label: 'classic 按钮',
              onPressed: () => calls++,
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    expect(ThemeManager().pixelPreviewEnabled, isFalse);
    await tester.tap(find.text('classic 按钮'));
    await tester.pump();
    expect(calls, 1);
    await tester.pump(const Duration(milliseconds: 120));
    // 无像素装饰类型渗漏。
    expect(find.byType(PixelSuccessBadge), findsNothing);
    expect(
      find.byWidgetPredicate(
        (w) => w is CustomPaint && w.painter is PixelOutlinePainter,
      ),
      findsNothing,
    );
  });
}
