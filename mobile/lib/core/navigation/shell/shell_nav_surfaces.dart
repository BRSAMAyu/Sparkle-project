/// V4-F04 · Shell 导航面共享件——角标图标与像素装饰沿。
///
/// 依赖面（零环）：只 import material 与 design 叶子文件
/// （pixel_geometry / pixel_preview_theme），不 import design_system 伞
/// （design_system 导出 responsive_widgets，responsate_widgets 又组装本
/// 文件，伞 import 会成环）；颜色一律取 `Theme.of(context).colorScheme`
/// ——生产路径 AppThemes 以 `colors.semanticError`/`colors.brandPrimary`
/// 构建 colorScheme（design_system.dart `_buildThemeData`），与旧
/// `DS.semanticError` 取值逐位一致（classic 零差量），像素档自动随档。
library;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/pixel/pixel_geometry.dart';
import 'package:sparkle/core/design/tokens_v2/pixel_preview_theme.dart';
import 'package:sparkle/core/navigation/shell/shell_destination.dart';

/// 带未读角标的导航图标（自 shell_navigation._buildBadgedIcon 原样迁出，
/// 三档呈现面共用——底栏 / 平板 rail / 桌面侧栏）。
///
/// 语义合同沿用：count == 0 时是普通图标；count > 0 时 [Semantics] 以
/// [badgeSemanticsLabel]（如「3 条未读通知」）替换图标节点语义，角标
/// 数字不重复进语义树。视觉参数（DS.semanticError 底 / 白字 10/w600 /
/// tabular figures / 8dp 圆角 / -8,-4 偏移）逐位保留。
class ShellNavBadgeIcon extends StatelessWidget {
  const ShellNavBadgeIcon({
    required this.icon,
    required this.count,
    required this.badgeSemanticsLabel,
    this.badgeOverflowLabel = '9+',
    super.key,
  });

  final IconData icon;
  final int count;
  final String badgeSemanticsLabel;
  final String badgeOverflowLabel;

  @override
  Widget build(BuildContext context) {
    if (count == 0) return Icon(icon);
    return Semantics(
      label: badgeSemanticsLabel,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(icon),
          Positioned(
            right: -8,
            top: -4,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              // 与旧 DS.semanticError 逐位一致：AppThemes 将
              // colors.semanticError 原样写入 colorScheme.error。
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.error,
                borderRadius: BorderRadius.circular(8),
              ),
              constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
              child: Text(
                count > 9 ? badgeOverflowLabel : '$count',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 底栏图标位（按角标选择普通/角标图标）。
Widget shellNavIconFor(ShellDestination d, {required bool selected}) =>
    selected ? _iconFor(d, d.selectedIcon) : _iconFor(d, d.icon);

Widget _iconFor(ShellDestination d, IconData icon) => d.hasBadge
    ? ShellNavBadgeIcon(
        icon: icon,
        count: d.badgeCount,
        badgeSemanticsLabel: d.badgeSemanticsLabel ?? d.semanticsLabel,
        badgeOverflowLabel: d.badgeOverflowLabel,
      )
    : Icon(icon);

/// 像素档（preview 通道）Shell 装饰沿——底栏顶部的 2dp 像素沿。
///
/// **classic 零差量由调用点举证**（F02 一审 N2 注记：接入即随调用点
/// 重新举证，不沿用组件级断言）：`PixelProfileTheme.of == null`
/// （classic / preview off，发布默认）渲染 `SizedBox.shrink`——零装饰
/// 绘制节点；仅在开发 preview 档（paperDay/dusk/quiet）出现。
///
/// 装饰层合同与 F02 PixelFrame 同制：`IgnorePointer + ExcludeSemantics`
/// （不能吞手势、Semantics 由内容层提供）；沿高 = pixelStep 2dp 吸附
/// 物理像素（[snapLengthToPhysical]），颜色 = colorScheme.primary
/// （像素档下即 proposal accent；classic 不渲染故不参与零差量对照）。
class PixelShellTopEdge extends StatelessWidget {
  const PixelShellTopEdge({super.key, this.color});

  /// 装饰沿颜色（缺省 colorScheme.primary）。
  final Color? color;

  /// 装饰沿高度（pixelStep 2dp 物理吸附；classic 也是本值，但整体不渲染）。
  @visibleForTesting
  static double heightFor(double pixelStep, double devicePixelRatio) =>
      snapLengthToPhysical(pixelStep, devicePixelRatio);

  @override
  Widget build(BuildContext context) {
    final pixel = PixelProfileTheme.of(context);
    // classic（preview off）：零装饰——发布面零差量的构造性保证。
    if (pixel == null) return const SizedBox.shrink();
    final dpr = MediaQuery.maybeOf(context)?.devicePixelRatio ?? 1.0;
    return SizedBox(
      width: double.infinity,
      height: heightFor(pixel.pixelStep, dpr),
      child: IgnorePointer(
        child: ExcludeSemantics(
          child: CustomPaint(
            painter: _PixelEdgePainter(
              color ?? Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
      ),
    );
  }
}

/// 装饰沿画笔（实心像素沿；类型名供测试反例断言 classic 无渗漏）。
class _PixelEdgePainter extends CustomPainter {
  const _PixelEdgePainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = color);
  }

  @override
  bool shouldRepaint(_PixelEdgePainter oldDelegate) =>
      oldDelegate.color != color;
}

/// 底栏呈现面：Material3 NavigationBar + 像素装饰沿（仅 preview 档）。
///
/// classic 结构 = 单一 [NavigationBar]（+ 零尺寸 Positioned shrink），
/// 与 F04 前 shell_navigation 直排 NavigationBar 视觉/命中逐位一致。
class ShellBottomBar extends StatelessWidget {
  const ShellBottomBar({
    required this.destinations,
    required this.currentIndex,
    required this.onDestinationSelected,
    super.key,
  });

  final List<ShellDestination> destinations;
  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;

  @override
  Widget build(BuildContext context) => Stack(
        children: [
          NavigationBar(
            selectedIndex: currentIndex,
            onDestinationSelected: onDestinationSelected,
            destinations: destinations
                .map(
                  (d) => NavigationDestination(
                    icon: shellNavIconFor(d, selected: false),
                    selectedIcon: shellNavIconFor(d, selected: true),
                    // 语义独立：tooltip 供长按提示与语义摘要，取显式
                    // semanticsLabel（当前与 label 同源 l10n）。
                    label: d.label,
                    tooltip: d.semanticsLabel,
                  ),
                )
                .toList(),
          ),
          // 像素装饰沿：classic 渲染 shrink（零绘制/零命中/零语义）。
          const Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: PixelShellTopEdge(),
          ),
        ],
      );
}
