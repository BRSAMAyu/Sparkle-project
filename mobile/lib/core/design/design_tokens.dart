import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Design Tokens for Sparkle Application
///
/// This file contains all design constants including colors, spacing,
/// border radius, shadows, animation durations, and typography scales.
///
/// Usage: Import this file and use the static constants throughout the app
/// to ensure design consistency.

class AppDesignTokens {
  AppDesignTokens._(); // Private constructor to prevent instantiation

  // ==================== Color System ====================

  /// Primary brand colors
  static const Color primaryBase = DS.brandPrimary;
  static const Color primaryLight = Color(0xFFFF8C5A);
  static const Color primaryDark = Color(0xFFE55A24);

  /// Primary gradient
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [primaryBase, primaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Secondary brand colors
  static const Color secondaryBase = DS.brandSecondary;
  static const Color secondaryLight = Color(0xFF3949AB);
  static const Color secondaryDark = Color(0xFF000051);

  /// Secondary colors for dark mode (brighter for readability)
  static const Color secondaryBaseDark = Color(0xFF5C6BC0);
  static const Color secondaryLightDark = Color(0xFF7986CB);

  /// Secondary gradient
  static const LinearGradient secondaryGradient = LinearGradient(
    colors: [secondaryBase, secondaryLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Secondary gradient for dark mode (brighter for readability)
  static const LinearGradient secondaryGradientDark = LinearGradient(
    colors: [secondaryBaseDark, secondaryLightDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Accent color
  static const Color accent = Color(0xFFFFD93D);
  static const LinearGradient accentGradient = LinearGradient(
    colors: [Color(0xFFFFD93D), Color(0xFFFFC107)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Semantic colors
  static const Color success = DS.success;
  static const Color successLight = Color(0xFF81C784);
  static const LinearGradient successGradient = LinearGradient(
    colors: [DS.success, Color(0xFF66BB6A)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const Color warning = DS.warning;
  static const Color warningLight = Color(0xFFFFB74D);
  static const LinearGradient warningGradient = LinearGradient(
    colors: [DS.warning, Color(0xFFFFB74D)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const Color error = DS.error;
  static const Color errorLight = Color(0xFFEF5350);
  static const LinearGradient errorGradient = LinearGradient(
    colors: [DS.error, Color(0xFFE57373)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const Color info = DS.info;
  static const Color infoLight = Color(0xFF42A5F5);
  static const LinearGradient infoGradient = LinearGradient(
    colors: [DS.info, Color(0xFF42A5F5)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  /// Neutral colors (grayscale)
  static const Color neutral50 = Color(0xFFFAFAFA);
  static const Color neutral100 = Color(0xFFF5F5F5);
  static const Color neutral200 = Color(0xFFEEEEEE);
  static const Color neutral300 = Color(0xFFE0E0E0);
  static const Color neutral400 = Color(0xFFBDBDBD);
  static const Color neutral500 = Color(0xFF9E9E9E);
  static const Color neutral600 = Color(0xFF757575);
  static const Color neutral700 = Color(0xFF616161);
  static const Color neutral800 = Color(0xFF424242);
  static const Color neutral900 = Color(0xFF212121);

  /// Overlay colors (semi-transparent black/white)
  static final Color overlay10 = DS.brandPrimary.withValues(alpha: 0.1);
  static final Color overlay20 = DS.brandPrimary.withValues(alpha: 0.2);
  static final Color overlay30 = DS.brandPrimary.withValues(alpha: 0.3);
  static final Color overlay40 = DS.brandPrimary.withValues(alpha: 0.4);
  static final Color overlay50 = DS.brandPrimary.withValues(alpha: 0.5);
  static final Color overlay60 = DS.brandPrimary.withValues(alpha: 0.6);

  static final Color overlayLight10 = DS.brandPrimary.withValues(alpha: 0.1);
  static final Color overlayLight20 = DS.brandPrimary.withValues(alpha: 0.2);
  static final Color overlayLight30 = DS.brandPrimary.withValues(alpha: 0.3);

  // ==================== Deep Space Theme (v2.3) ====================

  /// Deep Space background colors
  static const Color deepSpaceStart = Color(0xFF0D1B2A);
  static const Color deepSpaceEnd = Color(0xFF1B263B);
  static const Color deepSpaceSurface = Color(0xFF1B2838);

  /// Deep Space gradient (radial for background)
  static const LinearGradient deepSpaceGradient = LinearGradient(
    colors: [deepSpaceStart, deepSpaceEnd],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  /// Glassmorphism colors
  static final Color glassBackground = DS.brandPrimary.withValues(alpha: 0.08);
  static final Color glassBorder = DS.brandPrimary.withValues(alpha: 0.15);
  static final Color glassHighlight = DS.brandPrimary.withValues(alpha: 0.25);

  /// Weather theme colors
  static const Color weatherSunny = Color(0xFFFFD93D);
  static const Color weatherCloudy = Color(0xFF90A4AE);
  static const Color weatherRainy = Color(0xFF5C6BC0);
  static const Color weatherMeteor = DS.brandPrimary;

  /// Cognitive Prism colors
  static const Color prismPurple = Color(0xFF9C27B0);
  static const Color prismBlue = Color(0xFF3F51B5);
  static const Color prismGreen = DS.success;

  /// Focus flame colors
  static const Color flameCore = DS.brandPrimary;
  static const Color flameGlow = Color(0xFFFFAB91);
  static const LinearGradient flameGradient = LinearGradient(
    colors: [Color(0xFFFF8A65), DS.brandPrimary, Color(0xFFE64A19)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  /// Card gradients for different contexts
  static const LinearGradient cardGradientPrimary = LinearGradient(
    colors: [DS.brandPrimary, Color(0xFFFF8C5A)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradientSecondary = LinearGradient(
    colors: [DS.brandSecondary, Color(0xFF3949AB)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient cardGradientNeutral = LinearGradient(
    colors: [Color(0xFFF5F5F5), DS.brandPrimary],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ==================== Spacing System (8pt grid) ====================

  static const double spacing4 = 4.0;
  static const double spacing8 = 8.0;
  static const double spacing10 = 10.0;
  static const double spacing12 = 12.0;
  static const double spacing16 = 16.0;
  static const double spacing20 = 20.0;
  static const double spacing24 = 24.0;
  static const double spacing32 = 32.0;
  static const double spacing40 = 40.0;
  static const double spacing48 = 48.0;
  static const double spacing64 = 64.0;

  // ==================== Border Radius System ====================

  static const double radius4 = 4.0;
  static const double radius8 = 8.0;
  static const double radius12 = 12.0;
  static const double radius16 = 16.0;
  static const double radius20 = 20.0;
  static const double radius24 = 24.0;
  static const double radius32 = 32.0;
  static const double radiusFull = 9999.0; // Circular

  /// Convenience BorderRadius objects
  static final BorderRadius borderRadius4 = BorderRadius.circular(radius4);
  static final BorderRadius borderRadius8 = BorderRadius.circular(radius8);
  static final BorderRadius borderRadius12 = BorderRadius.circular(radius12);
  static final BorderRadius borderRadius16 = BorderRadius.circular(radius16);
  static final BorderRadius borderRadius20 = BorderRadius.circular(radius20);
  static final BorderRadius borderRadius24 = BorderRadius.circular(radius24);
  static final BorderRadius borderRadius32 = BorderRadius.circular(radius32);
  static final BorderRadius borderRadiusFull = BorderRadius.circular(radiusFull);

  // ==================== Shadow System ====================

  /// Small elevation shadow
  static List<BoxShadow> get shadowSm => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.05),
      blurRadius: 4,
      offset: const Offset(0, 2),
    ),
  ];

  /// Medium elevation shadow
  static List<BoxShadow> get shadowMd => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.08),
      blurRadius: 8,
      offset: const Offset(0, 4),
    ),
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.03),
      blurRadius: 3,
      offset: const Offset(0, 1),
    ),
  ];

  /// Large elevation shadow
  static List<BoxShadow> get shadowLg => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.10),
      blurRadius: 16,
      offset: const Offset(0, 8),
    ),
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.05),
      blurRadius: 6,
      offset: const Offset(0, 2),
    ),
  ];

  /// Extra large elevation shadow
  static List<BoxShadow> get shadowXl => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.12),
      blurRadius: 24,
      offset: const Offset(0, 12),
    ),
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.06),
      blurRadius: 8,
      offset: const Offset(0, 4),
    ),
  ];

  /// 2X large elevation shadow
  static List<BoxShadow> get shadow2xl => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.15),
      blurRadius: 32,
      offset: const Offset(0, 16),
    ),
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.08),
      blurRadius: 12,
      offset: const Offset(0, 6),
    ),
  ];

  /// Colored shadow for primary elements
  static List<BoxShadow> get shadowPrimary => [
    BoxShadow(
      color: primaryBase.withValues(alpha: 0.3),
      blurRadius: 16,
      offset: const Offset(0, 8),
    ),
  ];

  /// Inner shadow effect
  static List<BoxShadow> get shadowInner => [
    BoxShadow(
      color: DS.brandPrimary.withValues(alpha: 0.05),
      blurRadius: 4,
      offset: const Offset(0, 2),
      spreadRadius: -2,
    ),
  ];

  // ==================== Animation Durations ====================

  static const Duration durationInstant = Duration(milliseconds: 0);
  static const Duration durationFast = Duration(milliseconds: 150);
  static const Duration durationNormal = Duration(milliseconds: 250);
  static const Duration durationSlow = Duration(milliseconds: 350);
  static const Duration durationSlower = Duration(milliseconds: 500);

  // ==================== Animation Curves ====================

  static const Curve curveEaseIn = Curves.easeIn;
  static const Curve curveEaseOut = Curves.easeOut;
  static const Curve curveEaseInOut = Curves.easeInOut;
  static const Curve curveSpring = Curves.elasticOut;
  static const Curve curveBounce = Curves.bounceOut;

  // ==================== Typography System ====================

  /// Font weights
  static const FontWeight fontWeightLight = FontWeight.w300;
  static const FontWeight fontWeightRegular = FontWeight.w400;
  static const FontWeight fontWeightMedium = FontWeight.w500;
  static const FontWeight fontWeightSemibold = FontWeight.w600;
  static const FontWeight fontWeightBold = FontWeight.w700;
  static const FontWeight fontWeightExtrabold = FontWeight.w800;

  /// Font sizes (using a modular scale)
  static const double fontSizeXs = 12.0;
  static const double fontSizeSm = 14.0;
  static const double fontSizeBase = 16.0;
  static const double fontSizeLg = 18.0;
  static const double fontSizeXl = 20.0;
  static const double fontSize2xl = 24.0;
  static const double fontSize3xl = 30.0;
  static const double fontSize4xl = 36.0;
  static const double fontSize5xl = 48.0;
  static const double fontSize6xl = 60.0;

  /// Line heights
  static const double lineHeightTight = 1.2;
  static const double lineHeightNormal = 1.5;
  static const double lineHeightRelaxed = 1.75;

  // ==================== Icon Sizes ====================

  static const double iconSizeXs = 16.0;
  static const double iconSizeSm = 20.0;
  static const double iconSizeBase = 24.0;
  static const double iconSizeLg = 32.0;
  static const double iconSizeXl = 40.0;
  static const double iconSize2xl = 48.0;
  static const double iconSize3xl = 64.0;

  // ==================== Z-Index (for Stack widgets) ====================

  static const int zIndexBase = 0;
  static const int zIndexDropdown = 1000;
  static const int zIndexSticky = 1100;
  static const int zIndexFixed = 1200;
  static const int zIndexModalBackdrop = 1300;
  static const int zIndexModal = 1400;
  static const int zIndexPopover = 1500;
  static const int zIndexTooltip = 1600;

  // ==================== Responsive Breakpoints ====================

  static const double breakpointMobile = 480.0;
  static const double breakpointTablet = 768.0;
  static const double breakpointDesktop = 1024.0;
  static const double breakpointWide = 1440.0;

  // ==================== Content Width Constraints ====================

  /// Maximum content width for different screen sizes
  static const double contentMaxWidthMobile = 600.0;
  static const double contentMaxWidthTablet = 840.0;
  static const double contentMaxWidthDesktop = 1200.0;

  // ==================== Opacity Levels ====================

  static const double opacityDisabled = 0.5;
  static const double opacitySubtle = 0.7;
  static const double opacityMedium = 0.8;
  static const double opacityFull = 1.0;

  // ==================== Component-Specific Tokens ====================

  /// Chat bubble maximum width as a factor of screen width
  static const double chatBubbleMaxWidthFactor = 0.75;

  /// Task card type indicator stripe width
  static const double cardStripeWidth = 4.0;

  /// Minimum touch target size for accessibility (WCAG 2.1)
  static const double touchTargetMinSize = 48.0;

  /// Standard divider thickness
  static const double dividerThickness = 1.0;

  /// Card elevation heights
  static const double elevationNone = 0.0;
  static const double elevationLow = 2.0;
  static const double elevationMedium = 4.0;
  static const double elevationHigh = 8.0;
}
