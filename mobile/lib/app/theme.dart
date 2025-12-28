import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// App Colors - now using Design Tokens
class AppColors {
  static const primary = AppDesignTokens.primaryBase;
  static const secondary = AppDesignTokens.secondaryBase;
  static const accent = AppDesignTokens.accent;

  // Light Theme
  static const lightBackground = AppDesignTokens.neutral100;
  static const lightCard = DS.brandPrimary;
  static const lightText = AppDesignTokens.neutral900;
  static const lightTextSecondary = AppDesignTokens.neutral700;
  static const lightIcon = AppDesignTokens.neutral800;
  static const lightBorder = AppDesignTokens.neutral300;
  static const lightDivider = AppDesignTokens.neutral200;

  // Dark Theme
  static const darkBackground = AppDesignTokens.neutral900;
  static const darkCard = AppDesignTokens.neutral800;
  static const darkText = AppDesignTokens.neutral50;
  static const darkTextSecondary = AppDesignTokens.neutral300;
  static const darkIcon = AppDesignTokens.neutral100;
  static const darkBorder = AppDesignTokens.neutral700;
  static const darkDivider = AppDesignTokens.neutral600;

  // Semantic colors for both themes
  static Color surfaceBright(BuildContext context) {
    return Theme.of(context).brightness == Brightness.light
        ? DS.brandPrimary
        : AppDesignTokens.neutral800;
  }

  static Color textOnBright(BuildContext context) {
    return Theme.of(context).brightness == Brightness.light
        ? AppDesignTokens.neutral900
        : DS.brandPrimary;
  }

  static Color textOnDark(BuildContext context) {
    // For dark backgrounds, always use light text for maximum contrast
    return DS.brandPrimary;
  }

  static Color iconOnBright(BuildContext context) {
    return Theme.of(context).brightness == Brightness.light
        ? AppDesignTokens.neutral800
        : AppDesignTokens.neutral100;
  }

  static Color iconOnDark(BuildContext context) {
    // For dark backgrounds, always use light icons for maximum contrast
    return DS.brandPrimary;
  }
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
      onPrimary: DS.brandPrimary,
      onSecondary: DS.brandPrimary,
      onSurface: AppColors.lightText,
      error: AppDesignTokens.error,
      onError: DS.brandPrimary,
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
      SparkleColors.light,
    ],

    // Card theme with precise shadows
    cardTheme: CardThemeData(
      elevation: 0, // We use custom shadows
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius12,
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

    // Color scheme - use brighter secondary for dark mode
    colorScheme: const ColorScheme.dark(
      primary: AppColors.primary,
      secondary: AppDesignTokens.secondaryBaseDark,
      surface: AppColors.darkCard,
      onPrimary: DS.brandPrimary,
      onSecondary: DS.brandPrimary,
      onSurface: AppColors.darkText,
      error: AppDesignTokens.error,
      onError: DS.brandPrimary,
    ),

    // Extensions - use brighter secondary gradient for dark mode
    extensions: <ThemeExtension<dynamic>>[
      AppThemeExtension(
        primaryGradient: AppDesignTokens.primaryGradient,
        secondaryGradient: AppDesignTokens.secondaryGradientDark,
        cardGradient: const LinearGradient( // Darker gradient for dark mode
          colors: [AppDesignTokens.neutral800, AppDesignTokens.neutral700],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        cardShadow: AppDesignTokens.shadowMd,
        elevatedShadow: AppDesignTokens.shadowLg,
      ),
      SparkleColors.dark,
    ],

    // Card theme
    cardTheme: CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius12,
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

/// Sparkle 应用专用颜色扩展 - 支持深色/浅色模式
@immutable
class SparkleColors extends ThemeExtension<SparkleColors> {
  // 任务类型颜色
  final Color taskLearning;
  final Color taskTraining;
  final Color taskErrorFix;
  final Color taskReflection;
  final Color taskSocial;
  final Color taskPlanning;

  // 计划类型颜色
  final Color planSprint;
  final Color planGrowth;

  // 表面颜色
  final Color surfaceCard;
  final Color surfaceElevated;
  final Color surfaceGlass;

  // 文本颜色
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color textOnPrimary;

  // 边框和分割线颜色
  final Color border;
  final Color divider;

  const SparkleColors({
    required this.taskLearning,
    required this.taskTraining,
    required this.taskErrorFix,
    required this.taskReflection,
    required this.taskSocial,
    required this.taskPlanning,
    required this.planSprint,
    required this.planGrowth,
    required this.surfaceCard,
    required this.surfaceElevated,
    required this.surfaceGlass,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.textOnPrimary,
    required this.border,
    required this.divider,
  });

  /// 浅色主题配色
  static const light = SparkleColors(
    // 任务类型 - 使用饱和度适中的颜色
    taskLearning: DS.info,
    taskTraining: Color(0xFFFF9800),
    taskErrorFix: DS.error,
    taskReflection: Color(0xFF9C27B0),
    taskSocial: DS.success,
    taskPlanning: Color(0xFF009688),
    // 计划类型
    planSprint: Color(0xFFE53935),
    planGrowth: Color(0xFF43A047),
    // 表面颜色
    surfaceCard: DS.brandPrimary,
    surfaceElevated: Color(0xFFFAFAFA),
    surfaceGlass: Color(0xF0FFFFFF),
    // 文本颜色
    textPrimary: AppDesignTokens.neutral900,
    textSecondary: AppDesignTokens.neutral700,
    textTertiary: AppDesignTokens.neutral500,
    textOnPrimary: DS.brandPrimary,
    // 边框和分割线
    border: AppDesignTokens.neutral300,
    divider: AppDesignTokens.neutral200,
  );

  /// 深色主题配色
  static const dark = SparkleColors(
    // 任务类型 - 使用更亮的颜色以提高对比度
    taskLearning: Color(0xFF64B5F6),
    taskTraining: Color(0xFFFFB74D),
    taskErrorFix: Color(0xFFEF5350),
    taskReflection: Color(0xFFBA68C8),
    taskSocial: Color(0xFF81C784),
    taskPlanning: Color(0xFF4DB6AC),
    // 计划类型
    planSprint: Color(0xFFFF5252),
    planGrowth: Color(0xFF66BB6A),
    // 表面颜色
    surfaceCard: AppDesignTokens.neutral800,
    surfaceElevated: AppDesignTokens.neutral700,
    surfaceGlass: Color(0xF0424242),
    // 文本颜色
    textPrimary: AppDesignTokens.neutral50,
    textSecondary: AppDesignTokens.neutral300,
    textTertiary: AppDesignTokens.neutral500,
    textOnPrimary: DS.brandPrimary,
    // 边框和分割线
    border: AppDesignTokens.neutral700,
    divider: AppDesignTokens.neutral600,
  );

  @override
  SparkleColors copyWith({
    Color? taskLearning,
    Color? taskTraining,
    Color? taskErrorFix,
    Color? taskReflection,
    Color? taskSocial,
    Color? taskPlanning,
    Color? planSprint,
    Color? planGrowth,
    Color? surfaceCard,
    Color? surfaceElevated,
    Color? surfaceGlass,
    Color? textPrimary,
    Color? textSecondary,
    Color? textTertiary,
    Color? textOnPrimary,
    Color? border,
    Color? divider,
  }) {
    return SparkleColors(
      taskLearning: taskLearning ?? this.taskLearning,
      taskTraining: taskTraining ?? this.taskTraining,
      taskErrorFix: taskErrorFix ?? this.taskErrorFix,
      taskReflection: taskReflection ?? this.taskReflection,
      taskSocial: taskSocial ?? this.taskSocial,
      taskPlanning: taskPlanning ?? this.taskPlanning,
      planSprint: planSprint ?? this.planSprint,
      planGrowth: planGrowth ?? this.planGrowth,
      surfaceCard: surfaceCard ?? this.surfaceCard,
      surfaceElevated: surfaceElevated ?? this.surfaceElevated,
      surfaceGlass: surfaceGlass ?? this.surfaceGlass,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textTertiary: textTertiary ?? this.textTertiary,
      textOnPrimary: textOnPrimary ?? this.textOnPrimary,
      border: border ?? this.border,
      divider: divider ?? this.divider,
    );
  }

  @override
  SparkleColors lerp(ThemeExtension<SparkleColors>? other, double t) {
    if (other is! SparkleColors) return this;
    return SparkleColors(
      taskLearning: Color.lerp(taskLearning, other.taskLearning, t)!,
      taskTraining: Color.lerp(taskTraining, other.taskTraining, t)!,
      taskErrorFix: Color.lerp(taskErrorFix, other.taskErrorFix, t)!,
      taskReflection: Color.lerp(taskReflection, other.taskReflection, t)!,
      taskSocial: Color.lerp(taskSocial, other.taskSocial, t)!,
      taskPlanning: Color.lerp(taskPlanning, other.taskPlanning, t)!,
      planSprint: Color.lerp(planSprint, other.planSprint, t)!,
      planGrowth: Color.lerp(planGrowth, other.planGrowth, t)!,
      surfaceCard: Color.lerp(surfaceCard, other.surfaceCard, t)!,
      surfaceElevated: Color.lerp(surfaceElevated, other.surfaceElevated, t)!,
      surfaceGlass: Color.lerp(surfaceGlass, other.surfaceGlass, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textTertiary: Color.lerp(textTertiary, other.textTertiary, t)!,
      textOnPrimary: Color.lerp(textOnPrimary, other.textOnPrimary, t)!,
      border: Color.lerp(border, other.border, t)!,
      divider: Color.lerp(divider, other.divider, t)!,
    );
  }

  /// 根据任务类型获取颜色
  Color getTaskColor(String taskType) {
    switch (taskType.toLowerCase()) {
      case 'learning':
        return taskLearning;
      case 'training':
        return taskTraining;
      case 'error_fix':
        return taskErrorFix;
      case 'reflection':
        return taskReflection;
      case 'social':
        return taskSocial;
      case 'planning':
        return taskPlanning;
      default:
        return taskLearning;
    }
  }

  /// 根据计划类型获取颜色
  Color getPlanColor(String planType) {
    switch (planType.toLowerCase()) {
      case 'sprint':
        return planSprint;
      case 'growth':
        return planGrowth;
      default:
        return planSprint;
    }
  }

  /// 创建任务类型渐变
  LinearGradient getTaskGradient(String taskType) {
    final color = getTaskColor(taskType);
    return LinearGradient(
      colors: [color, color.withValues(alpha: 0.7)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }
}

/// 便捷访问扩展
extension SparkleColorsExtension on BuildContext {
  SparkleColors get colors =>
      Theme.of(this).extension<SparkleColors>() ?? SparkleColors.light;
}
