/// V4-F04 · Shell 导航槽位解析——手机底栏 / 平板侧栏 / 桌面常驻侧栏。
///
/// 断点唯一权威 = `core/design/breakpoints.dart` 的 [LayoutBreakpoints]
/// （本文件不新增断点常量，不造第二权威）。
///
/// 与既有 `ResponsiveSystem.categorizeSize`（shortestSide 主导）的差异
/// 只有一档：width ≥ desktop(1200) 一律走桌面侧栏。旧分类把 1280×720
/// 这类桌面窗口（shortestSide 720 < 768）停在手机底栏上，桌面档位对
/// 宽窗形同虚设；本解析改宽度主导后：
/// - 360×800（手机竖屏）→ 底栏（不变）；
/// - 800×600（窄短边小窗/小平板横屏）→ 底栏（不变，验收尺寸之一）；
/// - 768×1024 / 1024×768（平板）→ 侧栏 rail（不变）；
/// - 1280×720 / 1440×900 / 1920×1080（桌面窗口）→ 常驻侧栏（升级）。
/// 横屏手机（shortestSide < 768 且 width < 1200）保持底栏，与
/// `ResponsiveSystem.resolve`「横屏手机保持 mobile 值」同口径。
library;

import 'dart:ui' show Size;

import 'package:sparkle/core/design/breakpoints.dart';

/// Shell 导航呈现槽位（呈现层选择，不改五 Tab 路由合同）。
enum ShellNavSlot {
  /// 手机/窄窗：底部导航栏。
  bottomBar,

  /// 平板：左侧导航栏（NavigationRail，图标 + 全部标签）。
  sideRail,

  /// 桌面/宽窗（width ≥ 1200）：常驻侧栏（extended rail，品牌头 + 图标 + 标签）。
  sideNav,
}

/// 按窗口尺寸解析 Shell 导航槽位。
///
/// 纯函数（无 BuildContext/widget 依赖），是验收「360宽 / 800×600 /
/// 1280×720 断点行为可测」的可失败断言入口。
ShellNavSlot resolveShellNavSlot(Size size) {
  // 桌面档：宽度主导（1200+ 一律常驻侧栏，覆盖 1280×720 桌面窗口）。
  if (size.width >= LayoutBreakpoints.desktop) return ShellNavSlot.sideNav;
  // 窄短边（手机竖屏 + 横屏手机）：保持底栏。
  if (size.shortestSide < LayoutBreakpoints.tablet) {
    return ShellNavSlot.bottomBar;
  }
  // 平板档：768 ≤ width < 1200。
  if (size.width >= LayoutBreakpoints.tablet) return ShellNavSlot.sideRail;
  return ShellNavSlot.bottomBar;
}
