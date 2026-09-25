import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// ResponsiveUtils - Utility class for handling multi-platform and responsive layouts
class ResponsiveUtils {
  ResponsiveUtils._();

  /// Returns true if the screen width is mobile scale
  static bool isMobile(BuildContext context) =>
      ResponsiveSystem.isMobile(context);

  /// Returns true if the screen width is tablet scale
  static bool isTablet(BuildContext context) =>
      ResponsiveSystem.isTablet(context);

  /// Returns true if the screen width is desktop scale
  static bool isDesktop(BuildContext context) =>
      ResponsiveSystem.isDesktop(context);

  /// Returns the current screen width
  static double screenWidth(BuildContext context) =>
      ResponsiveSystem.width(context);

  /// Returns the current screen height
  static double screenHeight(BuildContext context) =>
      ResponsiveSystem.height(context);

  /// Returns true if the current platform is mobile (iOS or Android)
  ///
  /// U-09 平台判定接缝契约：与 app 其余平台分支（api_constants 等）
  /// 同源 `defaultTargetPlatform`，而非 dart:io Platform——Platform 读
  /// 的是**宿主机器**（测试宿主=macOS 时 android 目标也会判成桌面），
  /// 与框架目标平台可相互矛盾且无法被平台覆盖测试钉住。交付平台集上
  /// 两者取值一致，故此修复零生产行为变化，只恢复同源与可测性。
  static bool get isMobilePlatform {
    if (kIsWeb) return false;
    return defaultTargetPlatform == TargetPlatform.iOS ||
        defaultTargetPlatform == TargetPlatform.android;
  }

  /// Returns true if the current platform is desktop (macOS, Windows, Linux)
  static bool get isDesktopPlatform {
    if (kIsWeb) return false;
    return defaultTargetPlatform == TargetPlatform.macOS ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux;
  }

  /// Returns true if running on web
  static bool get isWeb => kIsWeb;

  /// Dynamically scales a value based on screen width relative to a base width (e.g., 375 for mobile)
  static double scale(BuildContext context, double value,
      {double baseWidth = 375,}) {
    if (isDesktop(context)) return value; // Don't over-scale on desktop
    return value * (screenWidth(context) / baseWidth);
  }

  /// Returns a responsive value based on current screen size
  static T valueByScreen<T>(
    BuildContext context, {
    required T mobile,
    T? tablet,
    T? desktop,
  }) {
    if (isDesktop(context)) return desktop ?? tablet ?? mobile;
    if (isTablet(context)) return tablet ?? mobile;
    return mobile;
  }
}
