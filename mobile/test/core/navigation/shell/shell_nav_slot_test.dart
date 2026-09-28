import 'dart:ui' show Size;

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/navigation/shell/shell_nav_slot.dart';

/// V4-F04 验收面「360宽 / 800×600 / 1280×720 断点行为可测」的纯函数层。
///
/// 槽位解析唯一权威 = LayoutBreakpoints（tablet 768 / desktop 1200）；
/// 每个验收尺寸一正一反：正例钉住应得槽位，反例钉住相邻档位边界
/// （映射回归时必红）。
void main() {
  group('resolveShellNavSlot · 三个验收尺寸', () {
    test('360×800（手机竖屏）→ 底栏', () {
      expect(resolveShellNavSlot(const Size(360, 800)), ShellNavSlot.bottomBar);
    });

    test('800×600（窄短边小窗）→ 底栏（与升级前一致，不误升 rail）', () {
      expect(resolveShellNavSlot(const Size(800, 600)), ShellNavSlot.bottomBar);
    });

    test('1280×720（桌面窗口）→ 常驻侧栏（升级点：旧分类停在底栏）', () {
      expect(resolveShellNavSlot(const Size(1280, 720)), ShellNavSlot.sideNav);
    });
  });

  group('resolveShellNavSlot · 其余真实形态', () {
    test('768×1024（iPad 竖屏）→ 侧栏 rail', () {
      expect(resolveShellNavSlot(const Size(768, 1024)), ShellNavSlot.sideRail);
    });

    test('1024×768（iPad 横屏）→ 侧栏 rail', () {
      expect(resolveShellNavSlot(const Size(1024, 768)), ShellNavSlot.sideRail);
    });

    test('1440×900（桌面）→ 常驻侧栏', () {
      expect(resolveShellNavSlot(const Size(1440, 900)), ShellNavSlot.sideNav);
    });

    test('1920×1080（宽桌面/TV 档宽）→ 常驻侧栏', () {
      expect(resolveShellNavSlot(const Size(1920, 1080)), ShellNavSlot.sideNav);
    });

    test('844×390（横屏手机）→ 保持底栏（不误升 rail）', () {
      expect(
        resolveShellNavSlot(const Size(844, 390)),
        isNot(ShellNavSlot.sideRail),
      );
      expect(resolveShellNavSlot(const Size(844, 390)), ShellNavSlot.bottomBar);
    });
  });

  group('resolveShellNavSlot · 断点边界反例（可失败）', () {
    test('1199×800：差 1px 不得进桌面侧栏', () {
      expect(
        resolveShellNavSlot(const Size(1199, 800)),
        isNot(ShellNavSlot.sideNav),
      );
      expect(resolveShellNavSlot(const Size(1199, 800)), ShellNavSlot.sideRail);
    });

    test('767×1024：差 1px 不得进平板 rail', () {
      expect(
        resolveShellNavSlot(const Size(767, 1024)),
        isNot(ShellNavSlot.sideRail),
      );
      expect(resolveShellNavSlot(const Size(767, 1024)),
          ShellNavSlot.bottomBar,);
    });

    test('1200×600：桌面宽度即使短边窄也走侧栏（宽度主导）', () {
      expect(resolveShellNavSlot(const Size(1200, 600)), ShellNavSlot.sideNav);
    });
  });
}
