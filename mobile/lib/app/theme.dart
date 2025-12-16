import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// App Colors - now using Design Tokens
class AppColors {
  static const primary = AppDesignTokens.primaryBase;
  static const secondary = AppDesignTokens.secondaryBase;
  static const accent = AppDesignTokens.accent;

  // Light Theme
  static const lightBackground = AppDesignTokens.neutral100;
  static const lightCard = Colors.white;
  static const lightText = AppDesignTokens.neutral900;

  // Dark Theme
  static const darkBackground = AppDesignTokens.neutral900;
  static const darkCard = AppDesignTokens.neutral800;
  static const darkText = AppDesignTokens.neutral50;
}

/// Theme Extension for custom properties
class AppThemeExtension extends ThemeExtension<AppThemeExtension> {
  final LinearGradient primaryGradient;
  final LinearGradient secondaryGradient;
  final LinearGradient cardGradient;
  final List<BoxShadow> cardShadow;
  final List<BoxShadow> elevatedShadow;

  const AppThemeExtension({
    required this.primaryGradient,
    required this.secondaryGradient,
    required this.cardGradient,
    required this.cardShadow,
    required this.elevatedShadow,
  });

  @override
  AppThemeExtension copyWith({
    LinearGradient? primaryGradient,
    LinearGradient? secondaryGradient,
    LinearGradient? cardGradient,
    List<BoxShadow>? cardShadow,
    List<BoxShadow>? elevatedShadow,
  }) {
    return AppThemeExtension(
      primaryGradient: primaryGradient ?? this.primaryGradient,
      secondaryGradient: secondaryGradient ?? this.secondaryGradient,
      cardGradient: cardGradient ?? this.cardGradient,
      cardShadow: cardShadow ?? this.cardShadow,
      elevatedShadow: elevatedShadow ?? this.elevatedShadow,
    );
  }

  @override
  AppThemeExtension lerp(ThemeExtension<AppThemeExtension>? other, double t) {
    if (other is! AppThemeExtension) {
      return this;
    }
    return AppThemeExtension(
      primaryGradient: LinearGradient.lerp(primaryGradient, other.primaryGradient, t)!,
      secondaryGradient: LinearGradient.lerp(secondaryGradient, other.secondaryGradient, t)!,
      cardGradient: LinearGradient.lerp(cardGradient, other.cardGradient, t)!,
      cardShadow: t < 0.5 ? cardShadow : other.cardShadow,
      elevatedShadow: t < 0.5 ? elevatedShadow : other.elevatedShadow,
    );
  }
}

class AppThemes {
  /// Light theme with design tokens
  static final ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    primaryColor: AppColors.primary,
    scaffoldBackgroundColor: AppColors.lightBackground,

    // Color scheme
    colorScheme: const ColorScheme.light(
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      surface: AppColors.lightCard,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: AppColors.lightText,
      error: AppDesignTokens.error,
      onError: Colors.white,
    ),

    // Extensions
    extensions: <ThemeExtension<dynamic>>[
      AppThemeExtension(
        primaryGradient: AppDesignTokens.primaryGradient,
        secondaryGradient: AppDesignTokens.secondaryGradient,
        cardGradient: AppDesignTokens.cardGradientNeutral,
        cardShadow: AppDesignTokens.shadowMd,
        elevatedShadow: AppDesignTokens.shadowLg,
      ),
    ],

    // Card theme with precise shadows
    cardTheme: CardThemeData(
      elevation: 0, // We use custom shadows
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius12,
      ),
      color: AppColors.lightCard,
      shadowColor: Colors.black.withOpacity(0.1),
    ),

    // Elevated button theme with gradient support
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0, // Flat by default, add shadow manually if needed
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing24,
          vertical: AppDesignTokens.spacing12,
        ),
        textStyle: const TextStyle(
          fontSize: AppDesignTokens.fontSizeBase,
          fontWeight: AppDesignTokens.fontWeightSemibold,
        ),
      ),
    ),

    // Text button theme
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing16,
          vertical: AppDesignTokens.spacing8,
        ),
      ),
    ),

    // Outlined button theme
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary, width: 1.5),
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing24,
          vertical: AppDesignTokens.spacing12,
        ),
      ),
    ),

    // Input decoration theme
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppDesignTokens.neutral300),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppDesignTokens.neutral300),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      filled: true,
      fillColor: AppDesignTokens.neutral50,
      contentPadding: const EdgeInsets.all(AppDesignTokens.spacing16),
    ),

    // Chip theme
    chipTheme: ChipThemeData(
      backgroundColor: AppDesignTokens.neutral100,
      selectedColor: AppColors.primary,
      labelStyle: const TextStyle(fontSize: AppDesignTokens.fontSizeSm),
      padding: const EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing12,
        vertical: AppDesignTokens.spacing4,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius16,
      ),
    ),

    // Bottom navigation bar theme
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppDesignTokens.neutral500,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
      backgroundColor: AppColors.lightCard,
    ),

    // App bar theme
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.lightText,
      titleTextStyle: TextStyle(
        fontSize: AppDesignTokens.fontSizeLg,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.lightText,
      ),
    ),

    // Text theme
    textTheme: const TextTheme(
      displayLarge: TextStyle(
        fontSize: AppDesignTokens.fontSize6xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.lightText,
      ),
      displayMedium: TextStyle(
        fontSize: AppDesignTokens.fontSize5xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.lightText,
      ),
      displaySmall: TextStyle(
        fontSize: AppDesignTokens.fontSize4xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.lightText,
      ),
      headlineLarge: TextStyle(
        fontSize: AppDesignTokens.fontSize3xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.lightText,
      ),
      headlineMedium: TextStyle(
        fontSize: AppDesignTokens.fontSize2xl,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.lightText,
      ),
      headlineSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXl,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.lightText,
      ),
      titleLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeLg,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.lightText,
      ),
      titleMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.lightText,
      ),
      titleSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.lightText,
      ),
      bodyLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.lightText,
      ),
      bodyMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.lightText,
      ),
      bodySmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXs,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.lightText,
      ),
      labelLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.lightText,
      ),
      labelMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.lightText,
      ),
      labelSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXs,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.lightText,
      ),
    ),
  );

  /// Dark theme with design tokens
  static final ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    primaryColor: AppColors.primary,
    scaffoldBackgroundColor: AppColors.darkBackground,

    // Color scheme
    colorScheme: const ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      surface: AppColors.darkCard,
      onPrimary: Colors.white,
      onSecondary: Colors.white,
      onSurface: AppColors.darkText,
      error: AppDesignTokens.error,
      onError: Colors.white,
    ),

    // Extensions
    extensions: <ThemeExtension<dynamic>>[
      AppThemeExtension(
        primaryGradient: AppDesignTokens.primaryGradient,
        secondaryGradient: AppDesignTokens.secondaryGradient,
        cardGradient: const LinearGradient( // Darker gradient for dark mode
          colors: [AppDesignTokens.neutral800, AppDesignTokens.neutral700],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        cardShadow: AppDesignTokens.shadowMd,
        elevatedShadow: AppDesignTokens.shadowLg,
      ),
    ],

    // Card theme
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius12,
      ),
      color: AppColors.darkCard,
      shadowColor: Colors.black.withOpacity(0.3),
    ),

    // Elevated button theme
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing24,
          vertical: AppDesignTokens.spacing12,
        ),
        textStyle: const TextStyle(
          fontSize: AppDesignTokens.fontSizeBase,
          fontWeight: AppDesignTokens.fontWeightSemibold,
        ),
      ),
    ),

    // Text button theme
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing16,
          vertical: AppDesignTokens.spacing8,
        ),
      ),
    ),

    // Outlined button theme
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary, width: 1.5),
        shape: RoundedRectangleBorder(
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing24,
          vertical: AppDesignTokens.spacing12,
        ),
      ),
    ),

    // Input decoration theme
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppDesignTokens.neutral700),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppDesignTokens.neutral700),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppDesignTokens.borderRadius8,
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      filled: true,
      fillColor: AppDesignTokens.neutral800,
      contentPadding: const EdgeInsets.all(AppDesignTokens.spacing16),
    ),

    // Chip theme
    chipTheme: ChipThemeData(
      backgroundColor: AppDesignTokens.neutral800,
      selectedColor: AppColors.primary,
      labelStyle: const TextStyle(fontSize: AppDesignTokens.fontSizeSm),
      padding: const EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing12,
        vertical: AppDesignTokens.spacing4,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius16,
      ),
    ),

    // Bottom navigation bar theme
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      selectedItemColor: AppColors.primary,
      unselectedItemColor: AppDesignTokens.neutral500,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
      backgroundColor: AppColors.darkCard,
    ),

    // App bar theme
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      elevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.darkText,
      titleTextStyle: TextStyle(
        fontSize: AppDesignTokens.fontSizeLg,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.darkText,
      ),
    ),

    // Text theme
    textTheme: const TextTheme(
      displayLarge: TextStyle(
        fontSize: AppDesignTokens.fontSize6xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.darkText,
      ),
      displayMedium: TextStyle(
        fontSize: AppDesignTokens.fontSize5xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.darkText,
      ),
      displaySmall: TextStyle(
        fontSize: AppDesignTokens.fontSize4xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.darkText,
      ),
      headlineLarge: TextStyle(
        fontSize: AppDesignTokens.fontSize3xl,
        fontWeight: AppDesignTokens.fontWeightBold,
        color: AppColors.darkText,
      ),
      headlineMedium: TextStyle(
        fontSize: AppDesignTokens.fontSize2xl,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.darkText,
      ),
      headlineSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXl,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.darkText,
      ),
      titleLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeLg,
        fontWeight: AppDesignTokens.fontWeightSemibold,
        color: AppColors.darkText,
      ),
      titleMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.darkText,
      ),
      titleSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.darkText,
      ),
      bodyLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.darkText,
      ),
      bodyMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.darkText,
      ),
      bodySmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXs,
        fontWeight: AppDesignTokens.fontWeightRegular,
        color: AppColors.darkText,
      ),
      labelLarge: TextStyle(
        fontSize: AppDesignTokens.fontSizeBase,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.darkText,
      ),
      labelMedium: TextStyle(
        fontSize: AppDesignTokens.fontSizeSm,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.darkText,
      ),
      labelSmall: TextStyle(
        fontSize: AppDesignTokens.fontSizeXs,
        fontWeight: AppDesignTokens.fontWeightMedium,
        color: AppColors.darkText,
      ),
    ),
  );
}

/// Helper extension to access custom theme properties
extension ThemeExtensionHelper on ThemeData {
  AppThemeExtension? get appExtension => extension<AppThemeExtension>();
}