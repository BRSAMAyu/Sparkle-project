/// V4-F02 · PrimaryAction——单视口主 CTA（像素档）。
///
/// DESIGN_SYSTEM.md 核心组件合同（PrimaryAction 行）：
/// - **loading 不改宽度**：标签始终参与布局（透明占位），指示器叠加，
///   按钮几何在 loading 切换前后恒等（测试断言）；
/// - **重复点击禁写**：loading/锁定期内的重复 press 不再触发回调；
/// - **focus ring 在切角外仍可见**：ring 画在轮廓外侧 2dp 的矩形环，
///   不沿切角轮廓走（切角处 ring 连续不断）；
/// - classic 降级：标准圆角 + 既有对比墨（无像素特色不破）；
/// - 保留原生输入与语义：Semantics(button) + label，FocusNode 可注入，
///   走 Focus 系统原生键盘遍历。
library;

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/design_system.dart';

class PixelPrimaryAction extends StatefulWidget {
  const PixelPrimaryAction({
    required this.label, required this.onPressed, super.key,
    this.icon,
    this.focusNode,
    this.autofocus = false,
    this.semanticLabel,
    this.loading = false,
  });

  final String label;
  final VoidCallback onPressed;
  final IconData? icon;
  final FocusNode? focusNode;
  final bool autofocus;

  /// 覆盖读屏标签（默认用 [label]）。
  final String? semanticLabel;

  /// 受控 loading（外部状态机驱动；与内部锁存共同构成禁写面）。
  final bool loading;

  @override
  State<PixelPrimaryAction> createState() => _PixelPrimaryActionState();
}

class _PixelPrimaryActionState extends State<PixelPrimaryAction> {
  bool _locked = false;
  FocusNode? _internalFocus;

  FocusNode get _effectiveFocus =>
      widget.focusNode ?? (_internalFocus ??= FocusNode());

  @override
  void initState() {
    super.initState();
    // focus 变化 → 重画 ring（focusNode 由 TextButton 内部 Focus 持有）。
    _effectiveFocus.addListener(_onFocusChanged);
  }

  void _onFocusChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _effectiveFocus.removeListener(_onFocusChanged);
    _internalFocus?.dispose();
    super.dispose();
  }

  bool get _busy => widget.loading || _locked;

  Future<void> _handlePress() async {
    // 重复点击禁写：loading 或锁存期内忽略后续 press。
    if (_busy) return;
    setState(() => _locked = true);
    try {
      widget.onPressed();
      // 最小锁存窗 = press 动效预算，防同帧双击穿透。
      final motion = PixelProfileTheme.of(context)?.stateMotion.press ??
          const Duration(milliseconds: 80);
      await Future<void>.delayed(motion);
    } finally {
      if (mounted) setState(() => _locked = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    final typo = context.sparkleTheme.typography;
    final pixel = PixelProfileTheme.of(context);
    final radius = pixel == null ? 18.0 : 0.0; // classic：标准圆角。
    final accentInk = pixel?.accentInk ?? colors.textPrimary;
    // 单一 focus 挂载点：focusNode 交给 TextButton 内部 Focus 持有，
    // 本组件经 listener 观察 hasFocus 画 ring（不再外挂第二个 Focus，
    // 避免「child into a parent of itself」重挂载断言）。
    final focused = _effectiveFocus.hasFocus;

    // 语义：不加外层 Semantics（避免与 TextButton 内建 button 节点
    // 重复标签）；显式读屏标签经 Text.semanticsLabel 注入唯一节点。
    return Padding(
      // ring 画在盒外 2dp：外层预留呼吸位，ring 不被父级裁切。
      padding: const EdgeInsets.all(3),
      child: DecoratedBox(
        decoration: ShapeDecoration(
          color: colors.brandPrimary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radius),
          ),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            TextButton(
              focusNode: _effectiveFocus,
              autofocus: widget.autofocus,
              style: TextButton.styleFrom(
                minimumSize: const Size(48, 48),
                padding: const EdgeInsets.symmetric(horizontal: 20),
                shape: radius > 0
                    ? RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(radius),
                      )
                    : const RoundedRectangleBorder(),
                splashFactory: NoSplash.splashFactory,
              ),
              onPressed: _busy ? null : _handlePress,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // 标签恒在布局中（loading 时透明占位 → 宽度不变）。
                  Opacity(
                    opacity: _busy ? 0 : 1,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (widget.icon != null) ...[
                          Icon(widget.icon, size: 18, color: accentInk),
                          const SizedBox(width: DS.xs),
                        ],
                        Text(
                          widget.label,
                          semanticsLabel: widget.semanticLabel,
                          style: typo.labelLarge.copyWith(color: accentInk),
                        ),
                      ],
                    ),
                  ),
                  // 指示器叠加（不参与宽度计算）。
                  if (_busy)
                    SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(accentInk),
                      ),
                    ),
                ],
              ),
            ),
            // focus ring 在轮廓外侧（切角外仍可见）。
            if (focused)
              Positioned.fill(
                child: IgnorePointer(
                  child: ExcludeSemantics(
                    child: CustomPaint(
                      foregroundPainter: PixelFocusRingPainter(
                        radius: radius,
                        color: colors.semanticInfo,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// 外扩 focus ring 画笔：轮廓外侧 2dp 的圆角矩形环（不贴切角轮廓，
/// 保证「ring 在切角外仍可见」；装饰层 IgnorePointer 不吞手势）。
class PixelFocusRingPainter extends CustomPainter {
  PixelFocusRingPainter({required this.radius, required this.color});

  final double radius;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..color = color;
    final outer = Rect.fromLTWH(-2, -2, size.width + 4, size.height + 4);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        outer,
        Radius.circular(radius > 0 ? radius + 2 : 2),
      ),
      paint,
    );
  }

  @override
  bool shouldRepaint(PixelFocusRingPainter oldDelegate) =>
      oldDelegate.radius != radius || oldDelegate.color != color;
}
