import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// ResponsiveUtils - Utility class for handling multi-platform and responsive layouts
class ResponsiveUtils {
  ResponsiveUtils._();

  /// Returns true if the screen width is mobile scale
  static bool isMobile(BuildContext context) =>
      MediaQuery.of(context).size.width < DS.breakpointTablet;

  /// Returns true if the screen width is tablet scale
  static bool isTablet(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    return width >= DS.breakpointTablet && width < DS.breakpointDesktop;
  }

  /// Returns true if the screen width is desktop scale
  static bool isDesktop(BuildContext context) =>
      MediaQuery.of(context).size.width >= DS.breakpointDesktop;

  /// Returns the current screen width
  static double screenWidth(BuildContext context) =>
      MediaQuery.of(context).size.width;

  /// Returns the current screen height
  static double screenHeight(BuildContext context) =>
      MediaQuery.of(context).size.height;

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
