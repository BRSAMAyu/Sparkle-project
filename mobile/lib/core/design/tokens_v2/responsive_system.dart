import 'package:flutter/material.dart';

/// 高级响应式断点系统
class ResponsiveSystem {
  const ResponsiveSystem._();

  /// 设备类别映射
  static DeviceCategory categorize(double width) {
    if (width <= 240) return DeviceCategory.watch;
    if (width <= 480) return DeviceCategory.phone;
    if (width <= 768) return DeviceCategory.phablet;
    if (width <= 1024) return DeviceCategory.tablet;
    if (width <= 1440) return DeviceCategory.desktop;
    return DeviceCategory.tv;
  }

  /// 获取当前设备类别
  static DeviceCategory getCategory(BuildContext context) {
    return categorize(MediaQuery.of(context).size.width);
  }

  /// 获取密度等级
  static Density getDensity(BuildContext context) {
    final category = getCategory(context);
    return {
      DeviceCategory.watch: Density.compact,
      DeviceCategory.phone: Density.compact,
      DeviceCategory.phablet: Density.normal,
      DeviceCategory.tablet: Density.comfortable,
      DeviceCategory.desktop: Density.expanded,
      DeviceCategory.tv: Density.large,
    }[category]!;
  }

  /// 是否为移动设备
  static bool isMobile(BuildContext context) {
    final category = getCategory(context);
    return category == DeviceCategory.watch ||
        category == DeviceCategory.phone ||
        category == DeviceCategory.phablet;
  }

  /// 是否为平板
  static bool isTablet(BuildContext context) {
    return getCategory(context) == DeviceCategory.tablet;
  }

  /// 是否为桌面
  static bool isDesktop(BuildContext context) {
    final category = getCategory(context);
    return category == DeviceCategory.desktop || category == DeviceCategory.tv;
  }

  /// 屏幕宽度
  static double width(BuildContext context) {
    return MediaQuery.of(context).size.width;
  }

  /// 屏幕高度
  static double height(BuildContext context) {
    return MediaQuery.of(context).size.height;
  }

  /// 屏幕方向
  static Orientation orientation(BuildContext context) {
    return MediaQuery.of(context).orientation;
  }

  /// 是否横屏
  static bool isLandscape(BuildContext context) {
    return orientation(context) == Orientation.landscape;
  }

  /// 像素密度
  static double pixelRatio(BuildContext context) {
    return MediaQuery.of(context).devicePixelRatio;
  }

  /// 文本比例
  static double textScaleFactor(BuildContext context) {
    return MediaQuery.of(context).textScaleFactor;
  }

  /// 安全区域
  static EdgeInsets safeArea(BuildContext context) {
    return MediaQuery.of(context).padding;
  }

  /// 响应式值解析
  static T resolve<T>({
    required BuildContext context,
    required T mobile,
    T? tablet,
    T? desktop,
    T? wide,
  }) {
    final width = MediaQuery.of(context).size.width;

    if (width >= 1440 && wide != null) return wide;
    if (width >= 1024 && desktop != null) return desktop;
    if (width >= 768 && tablet != null) return tablet;
    return mobile;
  }

  /// 比例缩放
  static double scale(BuildContext context, double base, {double min = 0.75, double max = 1.5}) {
    final width = MediaQuery.of(context).size.width;
    final ratio = width / 375.0;
    return (base * ratio).clamp(base * min, base * max);
  }

  /// 生成响应式断点信息
  static BreakpointInfo getBreakpointInfo(BuildContext context) {
    final width = width(context);
    final category = getCategory(context);
    final density = getDensity(context);

    return BreakpointInfo(
      width: width,
      category: category,
      density: density,
      isMobile: isMobile(context),
      isTablet: isTablet(context),
      isDesktop: isDesktop(context),
      orientation: orientation(context),
    );
  }
}

enum DeviceCategory {
  watch,    // 0-240px
  phone,    // 241-480px
  phablet,  // 481-768px
  tablet,   // 769-1024px
  desktop,  // 1025-1440px
  tv,       // 1441px+
}

enum Density {
  compact,      // 紧凑 - 小屏幕
  normal,       // 正常 - 标准手机
  comfortable,  // 舒适 - 平板
  expanded,     // 扩展 - 桌面
  large,        // 大屏 - TV
}

@immutable
class BreakpointInfo {
  final double width;
  final DeviceCategory category;
  final Density density;
  final bool isMobile;
  final bool isTablet;
  final bool isDesktop;
  final Orientation orientation;

  const BreakpointInfo({
    required this.width,
    required this.category,
    required this.density,
    required this.isMobile,
    required this.isTablet,
    required this.isDesktop,
    required this.orientation,
  });

  bool get isPortrait => orientation == Orientation.portrait;
  bool get isLandscape => orientation == Orientation.landscape;

  @override
  String toString() {
    return 'BreakpointInfo(${category.name}, ${width.toStringAsFixed(0)}px, $density)';
  }
}

/// 响应式值容器
@immutable
class ResponsiveValue<T> {
  final T mobile;
  final T? tablet;
  final T? desktop;
  final T? wide;

  const ResponsiveValue({
    required this.mobile,
    this.tablet,
    this.desktop,
    this.wide,
  });

  T resolve(BuildContext context) {
    return ResponsiveSystem.resolve(
      context: context,
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
      wide: wide,
    );
  }

  /// 便捷方法
  static ResponsiveValue<double> spacing({
    required double mobile,
    double? tablet,
    double? desktop,
    double? wide,
  }) {
    return ResponsiveValue(
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
      wide: wide,
    );
  }

  static ResponsiveValue<EdgeInsets> padding({
    required EdgeInsets mobile,
    EdgeInsets? tablet,
    EdgeInsets? desktop,
    EdgeInsets? wide,
  }) {
    return ResponsiveValue(
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
      wide: wide,
    );
  }

  static ResponsiveValue<TextStyle> textStyle({
    required TextStyle mobile,
    TextStyle? tablet,
    TextStyle? desktop,
    TextStyle? wide,
  }) {
    return ResponsiveValue(
      mobile: mobile,
      tablet: tablet,
      desktop: desktop,
      wide: wide,
    );
  }
}

/// 响应式组件构建器
class ResponsiveBuilder extends StatelessWidget {
  final Widget Function(BuildContext, BreakpointInfo) builder;

  const ResponsiveBuilder({
    required this.builder,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    return builder(context, info);
  }
}

/// 自适应布局包装器
class AdaptiveLayout extends StatelessWidget {
  final Widget mobile;
  final Widget? tablet;
  final Widget? desktop;
  final Widget? wide;

  const AdaptiveLayout({
    required this.mobile,
    this.tablet,
    this.desktop,
    this.wide,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return ResponsiveBuilder(
      builder: (context, info) {
        if (info.width >= 1440 && wide != null) return wide!;
        if (info.width >= 1024 && desktop != null) return desktop!;
        if (info.width >= 768 && tablet != null) return tablet!;
        return mobile;
      },
    );
  }
}

/// 响应式网格系统
class ResponsiveGridSystem {
  /// 计算列数
  static int columns(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    switch (info.category) {
      case DeviceCategory.watch:
      case DeviceCategory.phone:
        return 1;
      case DeviceCategory.phablet:
        return 2;
      case DeviceCategory.tablet:
        return 3;
      case DeviceCategory.desktop:
        return 4;
      case DeviceCategory.tv:
        return 6;
    }
  }

  /// 计算间距
  static double spacing(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    switch (info.density) {
      case Density.compact:
        return 8.0;
      case Density.normal:
        return 12.0;
      case Density.comfortable:
        return 16.0;
      case Density.expanded:
        return 20.0;
      case Density.large:
        return 24.0;
    }
  }

  /// 计算子项宽高比
  static double aspectRatio(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    if (info.isLandscape) return 1.5;
    switch (info.category) {
      case DeviceCategory.watch:
      case DeviceCategory.phone:
        return 1.2;
      case DeviceCategory.phablet:
        return 1.3;
      case DeviceCategory.tablet:
        return 1.4;
      case DeviceCategory.desktop:
      case DeviceCategory.tv:
        return 1.6;
    }
  }

  /// 创建响应式网格代理
  static SliverGridDelegateWithFixedCrossAxisCount delegate(BuildContext context) {
    return SliverGridDelegateWithFixedCrossAxisCount(
      crossAxisCount: columns(context),
      crossAxisSpacing: spacing(context),
      mainAxisSpacing: spacing(context),
      childAspectRatio: aspectRatio(context),
    );
  }
}

/// 内容约束系统
class ContentConstraintSystem {
  /// 最大内容宽度
  static double maxWidth(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    switch (info.category) {
      case DeviceCategory.watch:
      case DeviceCategory.phone:
        return double.infinity;
      case DeviceCategory.phablet:
        return 600.0;
      case DeviceCategory.tablet:
        return 840.0;
      case DeviceCategory.desktop:
        return 1200.0;
      case DeviceCategory.tv:
        return 1600.0;
    }
  }

  /// 水平边距
  static double horizontalPadding(BuildContext context) {
    final info = ResponsiveSystem.getBreakpointInfo(context);
    switch (info.density) {
      case Density.compact:
        return 16.0;
      case Density.normal:
        return 20.0;
      case Density.comfortable:
        return 24.0;
      case Density.expanded:
        return 32.0;
      case Density.large:
        return 48.0;
    }
  }

  /// 应用内容约束
  static Widget apply(BuildContext context, {required Widget child}) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth(context)),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: horizontalPadding(context)),
          child: child,
        ),
      ),
    );
  }
}
