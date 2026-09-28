/// V4-F02 · 像素几何原语——DPR 感知的物理像素对齐（纯函数，可失败测试面）。
///
/// DESIGN_SYSTEM.md「DPR处理」合同：
/// - **stroke 中心与填充边缘各自对齐物理像素**：线宽先吸附到 `1/dpr` 的
///   整数倍，路径顶点吸附到物理像素网格（半开边约定：顶点落在物理像素
///   *边界* 上，而非像素中心）；
/// - **布局保持逻辑 dp 连续**：吸附只发生在几何绘制层，本模块不改变
///   布局盒的约束/尺寸，也不用 Transform 缩放；
/// - **像素图形统一 2dp 概念网格**：阶梯角以 `PixelProfileTheme.pixelStep`
///   （默认 2dp）为一步，步数 = cut/pixelStep，与 DPR 无关。
///
/// 纯 Dart 函数（无 Flutter widget 依赖，仅 dart:ui几何类型），
/// widget 测试在五档 devicePixelRatio 下直接断言吸附结果。
library;

import 'dart:math' as math;
import 'dart:ui' show Offset, Path, RRect, Radius, Rect, Size;

/// 把逻辑坐标 [v] 吸附到物理像素网格（`v * dpr` 取整）。
///
/// 顶点落在物理像素边界上：`snap(v) * dpr` 为整数。
double snapToPhysicalGrid(double v, double dpr) {
  final physical = v * dpr;
  return physical.roundToDouble() / dpr;
}

/// 把逻辑长度 [v] 吸附到物理像素的整数倍（至少 1 物理像素）。
///
/// 线宽/分隔厚度用：`snapLength(1.0, 3.0) == 1/3`（3 物理像素线在 dpr=3
/// 下逻辑宽 1/3），保证描边恰好覆盖整数条物理像素扫描线。
double snapLengthToPhysical(double v, double dpr) {
  final px = (v * dpr).round().clamp(1, 1 << 20).toDouble();
  return px / dpr;
}

/// 阶梯角（stair corner）轮廓的几何描述。
///
/// 一次构建同时产出：
/// - [path]：主轮廓路径（顺时针，从左上角起始），顶点全部物理对齐；
/// - [vertices]：路径顶点（测试断言用，与 path 逐点一致）;
/// - [stairSteps]：切角处的阶梯步数（DPR 无关的几何不变量）；
/// - [physicalBoundsDeviation]：路径物理包围盒与目标逻辑盒的偏差
///   （物理像素计；吸附策略保证 ≤ 0.5px）。
class PixelOutlineGeometry {
  PixelOutlineGeometry._({
    required this.path,
    required this.vertices,
    required this.stairSteps,
    required this.strokeWidth,
    required this.dpr,
    required this.physicalBoundsDeviation,
  });

  /// 构建主轮廓。
  ///
  /// - [size]：目标逻辑盒；
  /// - [cut]：右上角阶梯切角深度（逻辑 dp；≤0 或 < pixelStep 时无切角）；
  /// - [pixelStep]：概念网格（TOKENS.proposal `pixel_step_dp` = 2）；
  /// - [strokeWidth]：期望线宽（逻辑 dp，TOKENS.proposal `stroke_dp`
  ///   1/2 档；实际线宽吸附到物理像素整数倍，见 [strokeWidth]）；
  /// - [dpr]：devicePixelRatio；[radius]：无像素档时的标准圆角
  ///   （classic 降级路径，radius > 0 时走圆角矩形）。
  ///
  /// 吸附策略（stroke 中心对齐物理像素）：外沿 = 盒边界内缩半线宽，
  /// 顶点吸附到物理网格；线宽吸附为物理像素整数倍。
  factory PixelOutlineGeometry.stair({
    required Size size,
    required double cut,
    required double strokeWidth,
    required double dpr,
    double pixelStep = 2.0,
    double radius = 0,
  }) {
    assert(size.width > 0 && size.height > 0);
    assert(dpr > 0);
    final sw = snapLengthToPhysical(strokeWidth, dpr);
    final half = sw / 2;
    final hasPixelStair =
        radius <= 0 && cut >= pixelStep && size.width > cut && size.height > cut;
    // 逻辑盒内缩半线宽后的外沿盒（顶点再逐个物理吸附）。
    final left = snapToPhysicalGrid(half, dpr);
    final top = snapToPhysicalGrid(half, dpr);
    final right = snapToPhysicalGrid(size.width - half, dpr);
    final bottom = snapToPhysicalGrid(size.height - half, dpr);

    if (radius > 0) {
      // classic 降级：标准圆角矩形（半径不吸附——圆角属既有发布语言，
      // 像素吸附不越界改写 classic 行为）。
      final r = radius.clamp(0.0, math.min(size.width, size.height) / 2);
      final path = Path()
        ..addRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTRB(left, top, right, bottom),
            Radius.circular(r),
          ),
        );
      return PixelOutlineGeometry._(
        path: path,
        vertices: const [],
        stairSteps: 0,
        strokeWidth: sw,
        dpr: dpr,
        physicalBoundsDeviation: 0,
      );
    }

    final vertices = <Offset>[];
    var stairStepCount = 0;
    if (!hasPixelStair) {
      vertices
        ..add(Offset(left, top))
        ..add(Offset(right, top))
        ..add(Offset(right, bottom))
        ..add(Offset(left, bottom));
    } else {
      // 阶梯切角：沿右上角按 pixelStep 逐级下落。步数 = cut/pixelStep，
      // 每级在物理网格上取整；物理偏差累计 ≤ 1px。
      final steps = (cut / pixelStep).floor().clamp(1, 64);
      stairStepCount = steps;
      final stepLogical = cut / steps; // 概念步长（≈ pixelStep）
      var x = right;
      var y = top;
      vertices.add(Offset(x, y));
      for (var i = 0; i < steps; i++) {
        x = snapToPhysicalGrid(x - stepLogical, dpr);
        vertices.add(Offset(x, y));
        y = snapToPhysicalGrid(y + stepLogical, dpr);
        vertices.add(Offset(x, y));
      }
      vertices
        ..add(Offset(x, bottom))
        ..add(Offset(left, bottom))
        ..add(Offset(left, top));
    }

    final path = Path()..moveTo(vertices.first.dx, vertices.first.dy);
    for (final v in vertices.skip(1)) {
      path.lineTo(v.dx, v.dy);
    }
    path.close();

    final bounds = path.getBounds();
    // 与「内缩半线宽后的目标盒」的逐边物理偏差（round 吸附保证每边
    // ≤ 0.5 物理像素；圆角路径 bounds 与矩形一致）。
    final dev = (bounds.left - half).abs() * dpr +
        (bounds.top - half).abs() * dpr +
        (bounds.right - (size.width - half)).abs() * dpr +
        (bounds.bottom - (size.height - half)).abs() * dpr;
    return PixelOutlineGeometry._(
      path: path,
      vertices: List<Offset>.unmodifiable(vertices),
      stairSteps: stairStepCount,
      strokeWidth: sw,
      dpr: dpr,
      physicalBoundsDeviation: dev,
    );
  }

  final Path path;
  final List<Offset> vertices;

  /// 阶梯步数；0 = 无阶梯（含 classic 圆角降级）。
  final int stairSteps;

  /// 吸附后的实际线宽（物理像素整数倍）。
  final double strokeWidth;
  final double dpr;

  /// 路径物理包围盒相对「内缩半线宽目标盒」的逐边偏差之和
  /// （物理像素；吸附保证 ≤ 2.0 = 4 边 × 0.5px）。
  final double physicalBoundsDeviation;
}
