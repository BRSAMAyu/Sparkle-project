/// V4-F02 · PixelFrame——像素轮廓与 surface（装饰层）。
///
/// DESIGN_SYSTEM.md 核心组件合同（PixelFrame 行）：
/// - **仅装饰**：Semantics 由 child 提供（本组件不加语义容器，
///   装饰绘制层包 `ExcludeSemantics`）；
/// - **不能吞手势**：轮廓绘制层整体 `IgnorePointer`；
/// - 主卡 = 一条深墨轮廓 + 1 个 4/8dp 阶梯角；次卡 = 单线或轻底色；
/// - DPR：stroke 宽度与顶点经 [PixelOutlineGeometry] 吸附物理像素；
/// - classic（preview off）：`PixelProfileTheme.of == null`，降级为既有
///   发布语言的标准圆角轮廓（无像素特色，行为零差量红线）。
library;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_geometry.dart';

/// 轮廓强度（主卡/次卡；来自 DESIGN_SYSTEM.md「视觉语法」两档制）。
enum PixelFrameEmphasis {
  /// 主卡：深墨轮廓 + 右上角一个阶梯切角（像素档）。
  primary,

  /// 次卡：单线或轻底色，无切角。
  secondary,
}

/// 像素轮廓容器。
///
/// 结构（装饰/内容分层是验收 3 的实现面）：
/// ```
/// Stack
///  ├─ IgnorePointer + excludeFromSemantics + CustomPaint（轮廓装饰层）
///  └─ Padding(child)（内容层：child 自带语义与手势）
/// ```
class PixelFrame extends StatelessWidget {
  const PixelFrame({
    required this.child, super.key,
    this.emphasis = PixelFrameEmphasis.secondary,
    this.padding = const EdgeInsets.all(16),
    this.cutCorner = false,
    this.fill = false,
  });

  final Widget child;
  final PixelFrameEmphasis emphasis;

  /// 内容内边距（默认 cardPaddingContent 档）。
  final EdgeInsetsGeometry padding;

  /// 像素档下右上角切阶梯角（主卡语义位）。
  final bool cutCorner;

  /// 次卡的轻底色变体（「单线或轻底色」）。
  final bool fill;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    final pixel = PixelProfileTheme.of(context);
    final isPrimary = emphasis == PixelFrameEmphasis.primary;
    // 主卡深墨轮廓；次卡单线（neutral300 / border）。
    final strokeColor =
        isPrimary ? colors.textPrimary : (fill ? colors.border : colors.neutral300);
    final hasPixel = pixel != null;
    // 像素档：主卡可切 8dp 阶梯角（4/8/12 阶梯中档）；classic 一律圆角。
    final cut = hasPixel && cutCorner ? pixel.cornerCut[1] : 0.0;
    final radius = hasPixel ? 0.0 : 22.0; // classic 降级：既有卡圆角。

    return Stack(
      children: [
        Positioned.fill(
          // 装饰层：不参与命中测试与语义（合同「不能吞手势」「Semantics
          // 由 child 提供」）。
          child: IgnorePointer(
            child: ExcludeSemantics(
              child: CustomPaint(
                painter: PixelOutlinePainter(
                  cut: cut,
                  strokeColor: strokeColor,
                  // 主卡承 surface 面；次卡默认透明（单线），fill 开轻底。
                  fillColor:
                      isPrimary || fill ? colors.surfaceSecondary : null,
                  radius: radius,
                ),
                child: const SizedBox.expand(),
              ),
            ),
          ),
        ),
        Padding(padding: padding, child: child),
      ],
    );
  }
}

/// 轮廓画笔（[geometryFor] 暴露纯几何供测试断言；顶点物理像素对齐）。
class PixelOutlinePainter extends CustomPainter {
  PixelOutlinePainter({
    required this.cut,
    required this.strokeColor,
    required this.fillColor,
    this.radius = 0,
    this.strokeWidth = 1.5,
  });

  /// 阶梯切角深度（逻辑 dp；0 = 无切角）。
  final double cut;
  final Color strokeColor;
  final Color? fillColor;

  /// classic 降级圆角（像素档恒 0）。
  final double radius;

  /// 期望线宽（逻辑 dp；实际吸附物理像素，见几何结果）。
  final double strokeWidth;

  /// 与 paint() 完全同参的纯几何构建（测试断言入口）。
  PixelOutlineGeometry geometryFor(Size size, double dpr) =>
      PixelOutlineGeometry.stair(
        size: size,
        cut: cut,
        strokeWidth: strokeWidth,
        dpr: dpr,
        radius: radius,
      );

  @override
  void paint(Canvas canvas, Size size) {
    final dpr = WidgetsBinding
        .instance.platformDispatcher.views.first.devicePixelRatio;
    final geo = geometryFor(size, dpr);
    if (fillColor != null) {
      canvas.drawPath(geo.path, Paint()..color = fillColor!);
    }
    canvas.drawPath(
      geo.path,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = geo.strokeWidth
        ..color = strokeColor,
    );
  }

  @override
  bool shouldRepaint(PixelOutlinePainter oldDelegate) =>
      oldDelegate.cut != cut ||
      oldDelegate.strokeColor != strokeColor ||
      oldDelegate.fillColor != fillColor ||
      oldDelegate.radius != radius ||
      oldDelegate.strokeWidth != strokeWidth;
}

/// 像素分隔线（视觉语法「列表：用留白与分割」；厚度物理对齐）。
class PixelDivider extends StatelessWidget {
  const PixelDivider({super.key, this.indent = 0});

  final double indent;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkleTheme.colors;
    return LayoutBuilder(
      builder: (context, constraints) {
        final dpr = MediaQuery.maybeOf(context)?.devicePixelRatio ?? 1.0;
        final thickness = snapLengthToPhysical(1.0, dpr);
        return Padding(
          padding: EdgeInsets.only(left: indent),
          child: SizedBox(
            width: (constraints.maxWidth - indent).clamp(0, double.infinity),
            height: thickness,
            child: DecoratedBox(
              decoration: BoxDecoration(color: colors.neutral200),
            ),
          ),
        );
      },
    );
  }
}

/// surface 色便捷（供组件族统一取面；唯一令牌源转发）。
Color pixelSurfaceFor(SparkleColors colors) => colors.surfaceSecondary;
