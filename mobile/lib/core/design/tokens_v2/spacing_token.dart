import 'package:flutter/material.dart';

/// 间距系统 - 基于8pt网格和黄金比例
@immutable
class SpacingSystem {
  const SpacingSystem._();

  // 基础网格 (8pt)
  static const double grid = 8.0;

  // 标准间距 (8pt网格)
  static const double xs = grid * 0.5; // 4pt
  static const double sm = grid * 1; // 8pt
  static const double md = grid * 1.5; // 12pt
  static const double lg = grid * 2; // 16pt
  static const double xl = grid * 3; // 24pt
  static const double xxl = grid * 4; // 32pt
  static const double xxxl = grid * 6; // 48pt
  static const double huge = grid * 8; // 64pt

  // 边距
  static const EdgeInsets edgeXs = EdgeInsets.all(xs);
  static const EdgeInsets edgeSm = EdgeInsets.all(sm);
  static const EdgeInsets edgeMd = EdgeInsets.all(md);
  static const EdgeInsets edgeLg = EdgeInsets.all(lg);
  static const EdgeInsets edgeXl = EdgeInsets.all(xl);
  static const EdgeInsets edgeXxl = EdgeInsets.all(xxl);
  static const EdgeInsets edgeXxxl = EdgeInsets.all(xxxl);

  // 水平/垂直间距
  static const EdgeInsets horizontalSm = EdgeInsets.symmetric(horizontal: sm);
  static const EdgeInsets horizontalMd = EdgeInsets.symmetric(horizontal: md);
  static const EdgeInsets horizontalLg = EdgeInsets.symmetric(horizontal: lg);
  static const EdgeInsets horizontalXl = EdgeInsets.symmetric(horizontal: xl);

  static const EdgeInsets verticalSm = EdgeInsets.symmetric(vertical: sm);
  static const EdgeInsets verticalMd = EdgeInsets.symmetric(vertical: md);
  static const EdgeInsets verticalLg = EdgeInsets.symmetric(vertical: lg);
  static const EdgeInsets verticalXl = EdgeInsets.symmetric(vertical: xl);

  // 仅顶部/底部/左侧/右侧
  static const EdgeInsets topSm = EdgeInsets.only(top: sm);
  static const EdgeInsets topMd = EdgeInsets.only(top: md);
  static const EdgeInsets topLg = EdgeInsets.only(top: lg);

  static const EdgeInsets bottomSm = EdgeInsets.only(bottom: sm);
  static const EdgeInsets bottomMd = EdgeInsets.only(bottom: md);
  static const EdgeInsets bottomLg = EdgeInsets.only(bottom: lg);

  static const EdgeInsets leftSm = EdgeInsets.only(left: sm);
  static const EdgeInsets leftMd = EdgeInsets.only(left: md);
  static const EdgeInsets leftLg = EdgeInsets.only(left: lg);

  static const EdgeInsets rightSm = EdgeInsets.only(right: sm);
  static const EdgeInsets rightMd = EdgeInsets.only(right: md);
  static const EdgeInsets rightLg = EdgeInsets.only(right: lg);

  /// 响应式间距 - 根据屏幕尺寸自动调整
  static double responsive(
    BuildContext context, {
    required double mobile,
    double? tablet,
    double? desktop,
  }) {
    final width = MediaQuery.of(context).size.width;

    if (width >= 1024 && desktop != null) return desktop;
    if (width >= 768 && tablet != null) return tablet;
    return mobile;
  }

  /// 响应式边距
  static EdgeInsets responsivePadding(
    BuildContext context, {
    required EdgeInsets mobile,
    EdgeInsets? tablet,
    EdgeInsets? desktop,
  }) {
    final width = MediaQuery.of(context).size.width;

    if (width >= 1024 && desktop != null) return desktop;
    if (width >= 768 && tablet != null) return tablet;
    return mobile;
  }

  /// 比例缩放 - 基于屏幕宽度
  static double scale(
    BuildContext context, {
    required double base,
    double min = 0.75,
    double max = 1.5,
  }) {
    final width = MediaQuery.of(context).size.width;
    final ratio = width / 375.0; // 基准宽度
    return (base * ratio).clamp(base * min, base * max);
  }

  /// 密度调整 - 根据设备类别
  static double density(BuildContext context, double base) {
    final width = MediaQuery.of(context).size.width;

    if (width < 480) return base * 0.875; // 紧凑
    if (width < 768) return base; // 正常
    if (width < 1024) return base * 1.125; // 舒适
    return base * 1.25; // 宽松
  }
}

/// 间距令牌 - 语义化命名
@immutable
class SpacingToken {
  const SpacingToken(this.name, this.value);
  final String name;
  final double value;

  /// 转换为EdgeInsets
  EdgeInsets get edge => EdgeInsets.all(value);
  EdgeInsets get horizontal => EdgeInsets.symmetric(horizontal: value);
  EdgeInsets get vertical => EdgeInsets.symmetric(vertical: value);

  /// 响应式变体
  SpacingTokenVariant variant({
    required double tablet,
    required double desktop,
  }) =>
      SpacingTokenVariant(
        mobile: value,
        tablet: tablet,
        desktop: desktop,
      );

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SpacingToken &&
          runtimeType == other.runtimeType &&
          value == other.value;

  @override
  int get hashCode => value.hashCode;
}

/// 响应式间距变体
@immutable
class SpacingTokenVariant {
  const SpacingTokenVariant({
    required this.mobile,
    required this.tablet,
    required this.desktop,
  });
  final double mobile;
  final double tablet;
  final double desktop;

  double resolve(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width >= 1024) return desktop;
    if (width >= 768) return tablet;
    return mobile;
  }

  EdgeInsets edge(BuildContext context) => EdgeInsets.all(resolve(context));
}
