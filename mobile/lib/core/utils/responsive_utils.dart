import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
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
  static bool get isMobilePlatform {
    if (kIsWeb) return false;
    return Platform.isIOS || Platform.isAndroid;
  }

  /// Returns true if the current platform is desktop (macOS, Windows, Linux)
  static bool get isDesktopPlatform {
    if (kIsWeb) return false;
    return Platform.isMacOS || Platform.isWindows || Platform.isLinux;
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
