import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';

/// App Colors - now using Design Tokens
/// @deprecated Use [DS] from `package:sparkle/core/design/design_system.dart` instead.
@Deprecated('Use DS from package:sparkle/core/design/design_system.dart')
class AppColors {
  static Color get primary => DS.primaryBase;
  static Color get secondary => DS.secondaryBase;
  static Color get accent => DS.accent;

  // Light Theme
  static Color get lightBackground => DS.neutral100;
  static Color get lightCard => DS.brandPrimary;
  static Color get lightText => DS.neutral900;
  static Color get lightTextSecondary => DS.neutral700;
  static Color get lightIcon => DS.neutral800;
  static Color get lightBorder => DS.neutral300;
  static Color get lightDivider => DS.neutral200;

  // Dark Theme
  static Color get darkBackground => DS.neutral900;
  static Color get darkCard => DS.neutral800;
  static Color get darkText => DS.neutral50;
  static Color get darkTextSecondary => DS.neutral300;
  static Color get darkIcon => DS.neutral100;
  static Color get darkBorder => DS.neutral700;
  static Color get darkDivider => DS.neutral600;

  // Semantic colors for both themes
  static Color surfaceBright(BuildContext context) =>
      Theme.of(context).brightness == Brightness.light
          ? DS.primaryBase
          : DS.neutral800;

  static Color textOnBright(BuildContext context) =>
      Theme.of(context).brightness == Brightness.light
          ? DS.neutral900
          : DS.neutral100;

  // For dark backgrounds, always use light text for maximum contrast
  static Color textOnDark(BuildContext context) => DS.neutral100;

  static Color iconOnBright(BuildContext context) =>
      Theme.of(context).brightness == Brightness.light
          ? DS.neutral800
          : DS.neutral100;

  // For dark backgrounds, always use light icons for maximum contrast
  static Color iconOnDark(BuildContext context) => DS.neutral100;
}

/// Theme Extension for custom properties
/// @deprecated Use [ThemeManager] and [DesignSystem] instead.
@Deprecated('Use ThemeManager and DesignSystem instead')
class AppThemeExtension extends ThemeExtension<AppThemeExtension> {
  const AppThemeExtension({
    required this.primaryGradient,
    required this.secondaryGradient,
    required this.cardGradient,
    required this.cardShadow,
    required this.elevatedShadow,
  });
  final LinearGradient primaryGradient;
  final LinearGradient secondaryGradient;
  final LinearGradient cardGradient;
  final List<BoxShadow> cardShadow;
  final List<BoxShadow> elevatedShadow;

  @override
  AppThemeExtension copyWith({
    LinearGradient? primaryGradient,
    LinearGradient? secondaryGradient,
    LinearGradient? cardGradient,
    List<BoxShadow>? cardShadow,
    List<BoxShadow>? elevatedShadow,
  }) =>
      AppThemeExtension(
        primaryGradient: primaryGradient ?? this.primaryGradient,
        secondaryGradient: secondaryGradient ?? this.secondaryGradient,
        cardGradient: cardGradient ?? this.cardGradient,
        cardShadow: cardShadow ?? this.cardShadow,
        elevatedShadow: elevatedShadow ?? this.elevatedShadow,
      );

  @override
  AppThemeExtension lerp(ThemeExtension<AppThemeExtension>? other, double t) {
    if (other is! AppThemeExtension) {
      return this;
    }
    return AppThemeExtension(
      primaryGradient:
          LinearGradient.lerp(primaryGradient, other.primaryGradient, t)!,
      secondaryGradient:
          LinearGradient.lerp(secondaryGradient, other.secondaryGradient, t)!,
      cardGradient: LinearGradient.lerp(cardGradient, other.cardGradient, t)!,
      cardShadow: t < 0.5 ? cardShadow : other.cardShadow,
      elevatedShadow: t < 0.5 ? elevatedShadow : other.elevatedShadow,
    );
  }
}

/// @deprecated Use [AppThemes] from `package:sparkle/core/design/design_system.dart` instead.
@Deprecated('Use AppThemes from package:sparkle/core/design/design_system.dart')
class AppThemes {
  /// Light theme with design tokens
  static ThemeData get lightTheme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        primaryColor: AppColors.primary,
        scaffoldBackgroundColor: AppColors.lightBackground,

        // Color scheme
        colorScheme: ColorScheme.light(
          primary: AppColors.primary,
          secondary: AppColors.secondary,
          surface: AppColors.lightCard,
          onPrimary: DS.neutral100,
          onSecondary: DS.neutral100,
          onSurface: AppColors.lightText,
          error: DS.error,
          onError: DS.neutral100,
        ),

        // Extensions
        extensions: <ThemeExtension<dynamic>>[
          AppThemeExtension(
            primaryGradient: DS.primaryGradient,
            secondaryGradient: DS.secondaryGradient,
            cardGradient: DS.cardGradientNeutral,
            cardShadow: DS.shadowMd,
            elevatedShadow: DS.shadowLg,
          ),
          SparkleThemeExtension.light(), // 🔧 修复：注册 SparkleThemeExtension
        ],

        // Card theme with precise shadows
        cardTheme: CardThemeData(
          elevation: 0, // We use custom shadows
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(DS.radius12),
          ),
          color: AppColors.lightCard,
          shadowColor: DS.brandPrimary.withValues(alpha: 0.1),
        ),

        // Elevated button theme with gradient support
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: DS.brandPrimary,
            elevation: 0, // Flat by default, add shadow manually if needed
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(DS.radius8),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing24,
              vertical: DS.spacing12,
            ),
            textStyle: const TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),

        // Text button theme
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.primary,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing8,
            ),
          ),
        ),

        // Outlined button theme
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            side: BorderSide(color: AppColors.primary, width: 1.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(DS.radius8),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing24,
              vertical: DS.spacing12,
            ),
          ),
        ),

        // Input decoration theme
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: DS.neutral300),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: DS.neutral300),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: AppColors.primary, width: 2),
          ),
          filled: true,
          fillColor: DS.neutral50,
          contentPadding: const EdgeInsets.all(DS.spacing16),
        ),

        // Chip theme
        chipTheme: ChipThemeData(
          backgroundColor: DS.neutral100,
          selectedColor: AppColors.primary,
          labelStyle: const TextStyle(fontSize: DS.fontSizeSm),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing4,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(DS.radius16),
          ),
        ),

        // Bottom navigation bar theme
        bottomNavigationBarTheme: BottomNavigationBarThemeData(
          selectedItemColor: AppColors.primary,
          unselectedItemColor: DS.neutral500,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
          backgroundColor: AppColors.lightCard,
        ),

        // App bar theme
        appBarTheme: AppBarTheme(
          centerTitle: false,
          elevation: 0,
          backgroundColor: Colors.transparent,
          foregroundColor: AppColors.lightText,
          titleTextStyle: const TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFF212121),
          ),
        ),

        // Text theme
        textTheme: const TextTheme(
          displayLarge: TextStyle(
            fontSize: DS.fontSize6xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFF212121),
          ),
          displayMedium: TextStyle(
            fontSize: DS.fontSize5xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFF212121),
          ),
          displaySmall: TextStyle(
            fontSize: DS.fontSize4xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFF212121),
          ),
          headlineLarge: TextStyle(
            fontSize: DS.fontSize3xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFF212121),
          ),
          headlineMedium: TextStyle(
            fontSize: DS.fontSize2xl,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFF212121),
          ),
          headlineSmall: TextStyle(
            fontSize: DS.fontSizeXl,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFF212121),
          ),
          titleLarge: TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFF212121),
          ),
          titleMedium: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFF212121),
          ),
          titleSmall: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFF212121),
          ),
          bodyLarge: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFF212121),
          ),
          bodyMedium: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFF212121),
          ),
          bodySmall: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFF212121),
          ),
          labelLarge: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFF212121),
          ),
          labelMedium: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFF212121),
          ),
          labelSmall: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFF212121),
          ),
        ),
      );

  /// Dark theme with design tokens
  static ThemeData get darkTheme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        primaryColor: AppColors.primary,
        scaffoldBackgroundColor: AppColors.darkBackground,

        // Color scheme - use brighter secondary for dark mode
        colorScheme: ColorScheme.dark(
          primary: AppColors.primary,
          secondary: DS.secondaryBaseDark,
          surface: AppColors.darkCard,
          onPrimary: DS.neutral100,
          onSecondary: DS.neutral100,
          onSurface: AppColors.darkText,
          error: DS.error,
          onError: DS.neutral100,
        ),

        // Extensions - use brighter secondary gradient for dark mode
        extensions: <ThemeExtension<dynamic>>[
          AppThemeExtension(
            primaryGradient: DS.primaryGradient,
            secondaryGradient: DS.secondaryGradientDark,
            cardGradient: LinearGradient(
              // Darker gradient for dark mode
              colors: [DS.neutral800, DS.neutral700],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            cardShadow: DS.shadowMd,
            elevatedShadow: DS.shadowLg,
          ),
          SparkleThemeExtension.dark(), // 🔧 修复：注册 SparkleThemeExtension
        ],

        // Card theme
        cardTheme: CardThemeData(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(DS.radius12),
          ),
          color: AppColors.darkCard,
          shadowColor: DS.brandPrimary.withValues(alpha: 0.3),
        ),

        // Elevated button theme
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: DS.brandPrimary,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(DS.radius8),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing24,
              vertical: DS.spacing12,
            ),
            textStyle: const TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),

        // Text button theme
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.primary,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing8,
            ),
          ),
        ),

        // Outlined button theme
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            side: BorderSide(color: AppColors.primary, width: 1.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(DS.radius8),
            ),
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing24,
              vertical: DS.spacing12,
            ),
          ),
        ),

        // Input decoration theme
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: DS.neutral700),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: DS.neutral700),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(DS.radius8),
            borderSide: BorderSide(color: AppColors.primary, width: 2),
          ),
          filled: true,
          fillColor: DS.neutral800,
          contentPadding: const EdgeInsets.all(DS.spacing16),
        ),

        // Chip theme
        chipTheme: ChipThemeData(
          backgroundColor: DS.neutral800,
          selectedColor: AppColors.primary,
          labelStyle: const TextStyle(fontSize: DS.fontSizeSm),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing4,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(DS.radius16),
          ),
        ),

        // Bottom navigation bar theme
        bottomNavigationBarTheme: BottomNavigationBarThemeData(
          selectedItemColor: AppColors.primary,
          unselectedItemColor: DS.neutral500,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
          backgroundColor: AppColors.darkCard,
        ),

        // App bar theme
        appBarTheme: const AppBarTheme(
          centerTitle: false,
          elevation: 0,
          backgroundColor: Colors.transparent,
          foregroundColor: Color(0xFFE0E0E0),
          titleTextStyle: TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFFE0E0E0),
          ),
        ),

        // Text theme
        textTheme: const TextTheme(
          displayLarge: TextStyle(
            fontSize: DS.fontSize6xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFFE0E0E0),
          ),
          displayMedium: TextStyle(
            fontSize: DS.fontSize5xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFFE0E0E0),
          ),
          displaySmall: TextStyle(
            fontSize: DS.fontSize4xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFFE0E0E0),
          ),
          headlineLarge: TextStyle(
            fontSize: DS.fontSize3xl,
            fontWeight: DS.fontWeightBold,
            color: Color(0xFFE0E0E0),
          ),
          headlineMedium: TextStyle(
            fontSize: DS.fontSize2xl,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFFE0E0E0),
          ),
          headlineSmall: TextStyle(
            fontSize: DS.fontSizeXl,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFFE0E0E0),
          ),
          titleLarge: TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightSemibold,
            color: Color(0xFFE0E0E0),
          ),
          titleMedium: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFFE0E0E0),
          ),
          titleSmall: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFFE0E0E0),
          ),
          bodyLarge: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFFE0E0E0),
          ),
          bodyMedium: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFFE0E0E0),
          ),
          bodySmall: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightRegular,
            color: Color(0xFFE0E0E0),
          ),
          labelLarge: TextStyle(
            fontSize: DS.fontSizeBase,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFFE0E0E0),
          ),
          labelMedium: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFFE0E0E0),
          ),
          labelSmall: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: Color(0xFFE0E0E0),
          ),
        ),
      );
}

/// Helper extension to access custom theme properties
extension ThemeExtensionHelper on ThemeData {
  AppThemeExtension? get appExtension => extension<AppThemeExtension>();
}
