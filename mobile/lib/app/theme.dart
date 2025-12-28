import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// App Colors - now using Design Tokens
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
  static Color surfaceBright(BuildContext context) => Theme.of(context).brightness == Brightness.light
        ? DS.brandPrimary
        : DS.neutral800;

  static Color textOnBright(BuildContext context) => Theme.of(context).brightness == Brightness.light
        ? DS.neutral900
        : DS.brandPrimary;

  static Color textOnDark(BuildContext context) {
    // For dark backgrounds, always use light text for maximum contrast
    return DS.brandPrimary;
  }

  static Color iconOnBright(BuildContext context) => Theme.of(context).brightness == Brightness.light
        ? DS.neutral800
        : DS.neutral100;

  static Color iconOnDark(BuildContext context) {
    // For dark backgrounds, always use light icons for maximum contrast
    return DS.brandPrimary;
  }
}

/// Theme Extension for custom properties
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
  }) => AppThemeExtension(
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
      onPrimary: DS.brandPrimary,
      onSecondary: DS.brandPrimary,
      onSurface: AppColors.lightText,
      error: DS.error,
      onError: DS.brandPrimary,
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
      SparkleColors.light,
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
        padding: EdgeInsets.symmetric(
          horizontal: DS.spacing24,
          vertical: DS.spacing12,
        ),
        textStyle: TextStyle(
          fontSize: DS.fontSizeBase,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    ),

    // Text button theme
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        padding: EdgeInsets.symmetric(
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
        padding: EdgeInsets.symmetric(
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
      contentPadding: EdgeInsets.all(DS.spacing16),
    ),

    // Chip theme
    chipTheme: ChipThemeData(
      backgroundColor: DS.neutral100,
      selectedColor: AppColors.primary,
      labelStyle: TextStyle(fontSize: DS.fontSizeSm),
      padding: EdgeInsets.symmetric(
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
      titleTextStyle: TextStyle(
        fontSize: DS.fontSizeLg,
        fontWeight: DS.fontWeightBold,
        color: Color(0xFF212121),
      ),
    ),

    // Text theme
    textTheme: TextTheme(
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
      onPrimary: DS.brandPrimary,
      onSecondary: DS.brandPrimary,
      onSurface: AppColors.darkText,
      error: DS.error,
      onError: DS.brandPrimary,
    ),

    // Extensions - use brighter secondary gradient for dark mode
    extensions: <ThemeExtension<dynamic>>[
      AppThemeExtension(
        primaryGradient: DS.primaryGradient,
        secondaryGradient: DS.secondaryGradientDark,
        cardGradient: LinearGradient( // Darker gradient for dark mode
          colors: [DS.neutral800, DS.neutral700],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        cardShadow: DS.shadowMd,
        elevatedShadow: DS.shadowLg,
      ),
      SparkleColors.dark,
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
        padding: EdgeInsets.symmetric(
          horizontal: DS.spacing24,
          vertical: DS.spacing12,
        ),
        textStyle: TextStyle(
          fontSize: DS.fontSizeBase,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    ),

    // Text button theme
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primary,
        padding: EdgeInsets.symmetric(
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
        padding: EdgeInsets.symmetric(
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
      contentPadding: EdgeInsets.all(DS.spacing16),
    ),

    // Chip theme
    chipTheme: ChipThemeData(
      backgroundColor: DS.neutral800,
      selectedColor: AppColors.primary,
      labelStyle: TextStyle(fontSize: DS.fontSizeSm),
      padding: EdgeInsets.symmetric(
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
    appBarTheme: AppBarTheme(
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
    textTheme: TextTheme(
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

/// Sparkle 应用专用颜色扩展 - 支持深色/浅色模式
@immutable
class SparkleColors extends ThemeExtension<SparkleColors> {

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

  /// 浅色主题配色
  static SparkleColors get light => SparkleColors(
    // 任务类型 - 使用饱和度适中的颜色
    taskLearning: Color(0xFF64B5F6),
    taskTraining: Color(0xFFFF9800),
    taskErrorFix: Color(0xFFEF5350),
    taskReflection: Color(0xFF9C27B0),
    taskSocial: Color(0xFF81C784),
    taskPlanning: Color(0xFF009688),
    // 计划类型
    planSprint: Color(0xFFE53935),
    planGrowth: Color(0xFF43A047),
    // 表面颜色
    surfaceCard: Color(0xFFFFFFFF),
    surfaceElevated: Color(0xFFFAFAFA),
    surfaceGlass: Color(0xF0FFFFFF),
    // 文本颜色
    textPrimary: DS.neutral900,
    textSecondary: DS.neutral700,
    textTertiary: DS.neutral500,
    textOnPrimary: Color(0xFFFFFFFF),
    // 边框和分割线
    border: DS.neutral300,
    divider: DS.neutral200,
  );

  /// 深色主题配色
  static SparkleColors get dark => SparkleColors(
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
    surfaceCard: DS.neutral800,
    surfaceElevated: DS.neutral700,
    surfaceGlass: Color(0xF0424242),
    // 文本颜色
    textPrimary: DS.neutral50,
    textSecondary: DS.neutral300,
    textTertiary: DS.neutral500,
    textOnPrimary: Color(0xFFFFFFFF),
    // 边框和分割线
    border: DS.neutral700,
    divider: DS.neutral600,
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
  }) => SparkleColors(
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
