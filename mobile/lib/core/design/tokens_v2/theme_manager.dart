import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 主题管理器 - 支持动态切换和持久化
class ThemeManager extends ChangeNotifier {
  factory ThemeManager() => _instance;
  ThemeManager._internal();
  static final ThemeManager _instance = ThemeManager._internal();

  AppThemeMode _mode = AppThemeMode.system;
  AppThemeMode get mode => _mode;

  BrandPreset _brandPreset = BrandPreset.sparkle;
  BrandPreset get brandPreset => _brandPreset;

  bool _highContrast = false;
  bool get highContrast => _highContrast;

  bool _initialized = false;
  bool get initialized => _initialized;

  /// 当前主题数据
  SparkleThemeData get current {
    if (!_initialized) {
      return SparkleThemeData.light();
    }
    return _resolveCurrentTheme();
  }

  /// 初始化 - 加载保存的设置
  Future<void> initialize() async {
    if (_initialized) return;

    final prefs = await SharedPreferences.getInstance();

    _mode = AppThemeMode.values[prefs.getInt('theme_mode') ?? AppThemeMode.system.index];
    _brandPreset = BrandPreset.values[prefs.getInt('brand_preset') ?? BrandPreset.sparkle.index];
    _highContrast = prefs.getBool('high_contrast') ?? false;

    _initialized = true;
    notifyListeners();
  }

  /// 切换主题模式
  Future<void> setAppThemeMode(AppThemeMode mode) async {
    _mode = mode;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 切换品牌预设
  Future<void> setBrandPreset(BrandPreset preset) async {
    _brandPreset = preset;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 切换高对比度
  Future<void> toggleHighContrast(bool enabled) async {
    _highContrast = enabled;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 切换深色/浅色模式
  Future<void> toggleDarkMode() async {
    final newMode = _mode == AppThemeMode.dark ? AppThemeMode.light : AppThemeMode.dark;
    await setAppThemeMode(newMode);
  }

  /// 重置为默认
  Future<void> reset() async {
    _mode = AppThemeMode.system;
    _brandPreset = BrandPreset.sparkle;
    _highContrast = false;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 解析当前主题
  SparkleThemeData _resolveCurrentTheme() {
    Brightness brightness;

    switch (_mode) {
      case AppThemeMode.light:
        brightness = Brightness.light;
      case AppThemeMode.dark:
        brightness = Brightness.dark;
      case AppThemeMode.system:
        brightness = WidgetsBinding.instance.platformDispatcher.platformBrightness;
    }

    final baseTheme = brightness == Brightness.light
        ? SparkleThemeData.light(highContrast: _highContrast)
        : SparkleThemeData.dark(highContrast: _highContrast);

    return _applyBrandPreset(baseTheme);
  }

  /// 应用品牌预设
  SparkleThemeData _applyBrandPreset(SparkleThemeData base) {
    var colors = base.colors;
    switch (_brandPreset) {
      case BrandPreset.sparkle:
        return base;
      case BrandPreset.ocean:
        colors = base.colors.copyWith(
          brandPrimary: const Color(0xFF0077BE),
          brandSecondary: const Color(0xFF00A8E8),
        );
      case BrandPreset.forest:
        colors = base.colors.copyWith(
          brandPrimary: const Color(0xFF2D6A4F),
          brandSecondary: const Color(0xFF52B788),
        );
    }

    if (identical(colors, base.colors)) {
      return base;
    }

    final shadows = colors.brightness == Brightness.light
        ? SparkleShadows.light(brandPrimary: colors.brandPrimary)
        : SparkleShadows.dark(brandPrimary: colors.brandPrimary);

    return base.copyWith(colors: colors, shadows: shadows);
  }

  /// 保存到持久化存储
  Future<void> _saveToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('theme_mode', _mode.index);
    await prefs.setInt('brand_preset', _brandPreset.index);
    await prefs.setBool('high_contrast', _highContrast);
  }
}

enum AppThemeMode { system, light, dark }
enum BrandPreset { sparkle, ocean, forest }

/// 主题数据容器
@immutable
class SparkleThemeData {

  const SparkleThemeData({
    required this.colors,
    required this.typography,
    required this.spacing,
    required this.animations,
    required this.shadows,
  });

  factory SparkleThemeData.light({bool highContrast = false}) {
    final colors = SparkleColors.light(highContrast: highContrast);
    return SparkleThemeData(
      colors: colors,
      typography: SparkleTypography.standard(),
      spacing: const SparkleSpacing(),
      animations: const SparkleAnimations(),
      shadows: SparkleShadows.light(brandPrimary: colors.brandPrimary),
    );
  }

  factory SparkleThemeData.dark({bool highContrast = false}) {
    final colors = SparkleColors.dark(highContrast: highContrast);
    return SparkleThemeData(
      colors: colors,
      typography: SparkleTypography.standard(),
      spacing: const SparkleSpacing(),
      animations: const SparkleAnimations(),
      shadows: SparkleShadows.dark(brandPrimary: colors.brandPrimary),
    );
  }
  final SparkleColors colors;
  final SparkleTypography typography;
  final SparkleSpacing spacing;
  final SparkleAnimations animations;
  final SparkleShadows shadows;

  SparkleThemeData copyWith({
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    SparkleAnimations? animations,
    SparkleShadows? shadows,
  }) => SparkleThemeData(
      colors: colors ?? this.colors,
      typography: typography ?? this.typography,
      spacing: spacing ?? this.spacing,
      animations: animations ?? this.animations,
      shadows: shadows ?? this.shadows,
    );
}

/// 颜色系统
@immutable
class SparkleColors {

  const SparkleColors({
    required this.brandPrimary,
    required this.brandSecondary,
    required this.semanticSuccess,
    required this.semanticWarning,
    required this.semanticError,
    required this.semanticInfo,
    required this.surfacePrimary,
    required this.surfaceSecondary,
    required this.surfaceTertiary,
    required this.textPrimary,
    required this.textSecondary,
    required this.textDisabled,
    required this.brightness,
    required this.taskLearning,
    required this.taskTraining,
    required this.taskErrorFix,
    required this.taskReflection,
    required this.taskSocial,
    required this.taskPlanning,
    required this.planSprint,
    required this.planGrowth,
    required this.statusOnline,
    required this.statusOffline,
    required this.statusInvisible,
    required this.neutral200,
    required this.neutral300,
    required this.neutral400,
    required this.neutral500,
    required this.neutral600,
  });

  factory SparkleColors.light({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        brandPrimary: Color(0xFFFF6B35),
        brandSecondary: Color(0xFFFF6B35),
        semanticSuccess: Color(0xFF006400),
        semanticWarning: Color(0xFF8B4500),
        semanticError: Color(0xFF8B0000),
        semanticInfo: Color(0xFF00008B),
        surfacePrimary: Color(0xFFFFFFFF),
        surfaceSecondary: Color(0xFFE0E0E0),
        surfaceTertiary: Color(0xFFC0C0C0),
        textPrimary: Color(0xFF000000),
        textSecondary: Color(0xFF000000),
        textDisabled: Color(0xFF666666),
        brightness: Brightness.light,
        taskLearning: Color(0xFF64B5F6),
        taskTraining: Color(0xFFFF9800),
        taskErrorFix: Color(0xFFEF5350),
        taskReflection: Color(0xFF9C27B0),
        taskSocial: Color(0xFF81C784),
        taskPlanning: Color(0xFF009688),
        planSprint: Color(0xFFE53935),
        planGrowth: Color(0xFF43A047),
        statusOnline: Color(0xFF2ECC71),
        statusOffline: Color(0xFF95A5A6),
        statusInvisible: Color(0xFF34495E),
        neutral200: Color(0xFFF5F5F5),
        neutral300: Color(0xFFE0E0E0),
        neutral400: Color(0xFFBDBDBD),
        neutral500: Color(0xFF9E9E9E),
        neutral600: Color(0xFF757575),
      );
    }
    return const SparkleColors(
      brandPrimary: Color(0xFFFF6B35),
      brandSecondary: Color(0xFF5C6BC0),
      semanticSuccess: Color(0xFF81C784),
      semanticWarning: Color(0xFFFFB74D),
      semanticError: Color(0xFFEF5350),
      semanticInfo: Color(0xFF64B5F6),
      surfacePrimary: Color(0xFFFFFFFF),
      surfaceSecondary: Color(0xFFF5F5F5),
      surfaceTertiary: Color(0xFFE0E0E0),
      textPrimary: Color(0xFF212121),
      textSecondary: Color(0xFF757575),
      textDisabled: Color(0xFFBDBDBD),
      brightness: Brightness.light,
      taskLearning: Color(0xFF64B5F6),
      taskTraining: Color(0xFFFF9800),
      taskErrorFix: Color(0xFFEF5350),
      taskReflection: Color(0xFF9C27B0),
      taskSocial: Color(0xFF81C784),
      taskPlanning: Color(0xFF009688),
      planSprint: Color(0xFFE53935),
      planGrowth: Color(0xFF43A047),
      statusOnline: Color(0xFF2ECC71),
      statusOffline: Color(0xFF95A5A6),
      statusInvisible: Color(0xFF34495E),
      neutral200: Color(0xFFF5F5F5),
      neutral300: Color(0xFFE0E0E0),
      neutral400: Color(0xFFBDBDBD),
      neutral500: Color(0xFF9E9E9E),
      neutral600: Color(0xFF757575),
    );
  }

  factory SparkleColors.dark({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        brandPrimary: Color(0xFFFF8C5A),
        brandSecondary: Color(0xFFFF8C5A),
        semanticSuccess: Color(0xFF00FF00),
        semanticWarning: Color(0xFFFFFF00),
        semanticError: Color(0xFFFF0000),
        semanticInfo: Color(0xFF00FFFF),
        surfacePrimary: Color(0xFF000000),
        surfaceSecondary: Color(0xFF1A1A1A),
        surfaceTertiary: Color(0xFF333333),
        textPrimary: Color(0xFFFFFFFF),
        textSecondary: Color(0xFFFFFFFF),
        textDisabled: Color(0xFF999999),
        brightness: Brightness.dark,
        taskLearning: Color(0xFF64B5F6),
        taskTraining: Color(0xFFFFB74D),
        taskErrorFix: Color(0xFFEF5350),
        taskReflection: Color(0xFFBA68C8),
        taskSocial: Color(0xFF81C784),
        taskPlanning: Color(0xFF4DB6AC),
        planSprint: Color(0xFFFF5252),
        planGrowth: Color(0xFF66BB6A),
        statusOnline: Color(0xFF2ECC71),
        statusOffline: Color(0xFF95A5A6),
        statusInvisible: Color(0xFF34495E),
        neutral200: Color(0xFF2D2D2D),
        neutral300: Color(0xFF424242),
        neutral400: Color(0xFF616161),
        neutral500: Color(0xFF757575),
        neutral600: Color(0xFF9E9E9E),
      );
    }
    return const SparkleColors(
      brandPrimary: Color(0xFFFF8C5A),
      brandSecondary: Color(0xFF5C6BC0),
      semanticSuccess: Color(0xFF81C784),
      semanticWarning: Color(0xFFFFB74D),
      semanticError: Color(0xFFEF5350),
      semanticInfo: Color(0xFF64B5F6),
      surfacePrimary: Color(0xFF121212),
      surfaceSecondary: Color(0xFF1E1E1E),
      surfaceTertiary: Color(0xFF2D2D2D),
      textPrimary: Color(0xFFFFFFFF),
      textSecondary: Color(0xFFE0E0E0),
      textDisabled: Color(0xFF757575),
      brightness: Brightness.dark,
      taskLearning: Color(0xFF64B5F6),
      taskTraining: Color(0xFFFFB74D),
      taskErrorFix: Color(0xFFEF5350),
      taskReflection: Color(0xFFBA68C8),
      taskSocial: Color(0xFF81C784),
      taskPlanning: Color(0xFF4DB6AC),
      planSprint: Color(0xFFFF5252),
      planGrowth: Color(0xFF66BB6A),
      statusOnline: Color(0xFF2ECC71),
      statusOffline: Color(0xFF95A5A6),
      statusInvisible: Color(0xFF34495E),
      neutral200: Color(0xFF2D2D2D),
      neutral300: Color(0xFF424242),
      neutral400: Color(0xFF616161),
      neutral500: Color(0xFF757575),
      neutral600: Color(0xFF9E9E9E),
    );
  }
  final Color brandPrimary;
  final Color brandSecondary;

  final Color semanticSuccess;
  final Color semanticWarning;
  final Color semanticError;
  final Color semanticInfo;

  final Color surfacePrimary;
  final Color surfaceSecondary;
  final Color surfaceTertiary;

  final Color textPrimary;
  final Color textSecondary;
  final Color textDisabled;

  // Task and plan type colors
  final Color taskLearning;
  final Color taskTraining;
  final Color taskErrorFix;
  final Color taskReflection;
  final Color taskSocial;
  final Color taskPlanning;
  final Color planSprint;
  final Color planGrowth;

  // User status colors
  final Color statusOnline;
  final Color statusOffline;
  final Color statusInvisible;

  // Neutral colors
  final Color neutral200;
  final Color neutral300;
  final Color neutral400;
  final Color neutral500;
  final Color neutral600;

  final Brightness brightness;

  SparkleColors copyWith({
    Color? brandPrimary,
    Color? brandSecondary,
    Color? semanticSuccess,
    Color? semanticWarning,
    Color? semanticError,
    Color? semanticInfo,
    Color? surfacePrimary,
    Color? surfaceSecondary,
    Color? surfaceTertiary,
    Color? textPrimary,
    Color? textSecondary,
    Color? textDisabled,
    Color? taskLearning,
    Color? taskTraining,
    Color? taskErrorFix,
    Color? taskReflection,
    Color? taskSocial,
    Color? taskPlanning,
    Color? planSprint,
    Color? planGrowth,
    Color? statusOnline,
    Color? statusOffline,
    Color? statusInvisible,
    Color? neutral200,
    Color? neutral300,
    Color? neutral400,
    Color? neutral500,
    Color? neutral600,
  }) => SparkleColors(
      brandPrimary: brandPrimary ?? this.brandPrimary,
      brandSecondary: brandSecondary ?? this.brandSecondary,
      semanticSuccess: semanticSuccess ?? this.semanticSuccess,
      semanticWarning: semanticWarning ?? this.semanticWarning,
      semanticError: semanticError ?? this.semanticError,
      semanticInfo: semanticInfo ?? this.semanticInfo,
      surfacePrimary: surfacePrimary ?? this.surfacePrimary,
      surfaceSecondary: surfaceSecondary ?? this.surfaceSecondary,
      surfaceTertiary: surfaceTertiary ?? this.surfaceTertiary,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textDisabled: textDisabled ?? this.textDisabled,
      brightness: brightness,
      taskLearning: taskLearning ?? this.taskLearning,
      taskTraining: taskTraining ?? this.taskTraining,
      taskErrorFix: taskErrorFix ?? this.taskErrorFix,
      taskReflection: taskReflection ?? this.taskReflection,
      taskSocial: taskSocial ?? this.taskSocial,
      taskPlanning: taskPlanning ?? this.taskPlanning,
      planSprint: planSprint ?? this.planSprint,
      planGrowth: planGrowth ?? this.planGrowth,
      statusOnline: statusOnline ?? this.statusOnline,
      statusOffline: statusOffline ?? this.statusOffline,
      statusInvisible: statusInvisible ?? this.statusInvisible,
      neutral200: neutral200 ?? this.neutral200,
      neutral300: neutral300 ?? this.neutral300,
      neutral400: neutral400 ?? this.neutral400,
      neutral500: neutral500 ?? this.neutral500,
      neutral600: neutral600 ?? this.neutral600,
    );

  SparkleColors toHighContrast(bool enabled) => brightness == Brightness.light
        ? SparkleColors.light(highContrast: enabled)
        : SparkleColors.dark(highContrast: enabled);

  /// Get task color by type
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

  /// Get plan color by type
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

  /// Create gradient for task type
  LinearGradient getTaskGradient(String taskType) {
    final color = getTaskColor(taskType);
    return LinearGradient(
      colors: [color, color.withValues(alpha: 0.7)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }

  /// Get status color by user status
  Color getStatusColor(String userStatus) {
    switch (userStatus.toLowerCase()) {
      case 'online':
        return statusOnline;
      case 'offline':
        return statusOffline;
      case 'invisible':
        return statusInvisible;
      default:
        return statusOffline;
    }
  }
}

/// 排版系统
@immutable
class SparkleTypography {

  const SparkleTypography({
    required this.displayLarge,
    required this.headingLarge,
    required this.headingMedium,
    required this.titleLarge,
    required this.bodyLarge,
    required this.bodyMedium,
    required this.labelLarge,
    required this.labelSmall,
  });

  factory SparkleTypography.standard() => const SparkleTypography(
      displayLarge: TextStyle(fontSize: 48.8, fontWeight: FontWeight.w800, height: 1.2, letterSpacing: -0.02),
      headingLarge: TextStyle(fontSize: 31.25, fontWeight: FontWeight.w700, height: 1.2, letterSpacing: -0.01),
      headingMedium: TextStyle(fontSize: 25.0, fontWeight: FontWeight.w600, height: 1.3, letterSpacing: 0),
      titleLarge: TextStyle(fontSize: 20.0, fontWeight: FontWeight.w600, height: 1.5, letterSpacing: 0),
      bodyLarge: TextStyle(fontSize: 16.0, fontWeight: FontWeight.w400, height: 1.5, letterSpacing: 0),
      bodyMedium: TextStyle(fontSize: 14.0, fontWeight: FontWeight.w400, height: 1.5, letterSpacing: 0),
      labelLarge: TextStyle(fontSize: 14.0, fontWeight: FontWeight.w500, height: 1.2, letterSpacing: 0.01),
      labelSmall: TextStyle(fontSize: 12.8, fontWeight: FontWeight.w500, height: 1.2, letterSpacing: 0.01),
    );
  final TextStyle displayLarge;
  final TextStyle headingLarge;
  final TextStyle headingMedium;
  final TextStyle titleLarge;
  final TextStyle bodyLarge;
  final TextStyle bodyMedium;
  final TextStyle labelLarge;
  final TextStyle labelSmall;
}

/// 间距系统
@immutable
class SparkleSpacing {

  const SparkleSpacing();
  final double xs = 4.0;
  final double sm = 8.0;
  final double md = 12.0;
  final double lg = 16.0;
  final double xl = 24.0;
  final double xxl = 32.0;
  final double xxxl = 48.0;

  EdgeInsets edge({double? all, double? horizontal, double? vertical}) {
    if (all != null) return EdgeInsets.all(all);
    return EdgeInsets.symmetric(
      horizontal: horizontal ?? 0,
      vertical: vertical ?? 0,
    );
  }
}

/// 动画系统
@immutable
class SparkleAnimations {

  const SparkleAnimations();
  final Duration quick = const Duration(milliseconds: 150);
  final Duration normal = const Duration(milliseconds: 250);
  final Duration slow = const Duration(milliseconds: 400);
}

/// 阴影系统
@immutable
class SparkleShadows {

  const SparkleShadows({
    required this.small,
    required this.medium,
    required this.large,
  });

  factory SparkleShadows.light({Color? brandPrimary}) => SparkleShadows(
      small: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF6B35)).withOpacity(0.05),
          blurRadius: 4,
          offset: const Offset(0, 2),
        ),
      ],
      medium: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF6B35)).withOpacity(0.08),
          blurRadius: 8,
          offset: const Offset(0, 4),
        ),
      ],
      large: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF6B35)).withOpacity(0.10),
          blurRadius: 16,
          offset: const Offset(0, 8),
        ),
      ],
    );

  factory SparkleShadows.dark({Color? brandPrimary}) => SparkleShadows(
      small: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF8C5A)).withOpacity(0.2),
          blurRadius: 4,
          offset: const Offset(0, 2),
        ),
      ],
      medium: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF8C5A)).withOpacity(0.3),
          blurRadius: 8,
          offset: const Offset(0, 4),
        ),
      ],
      large: [
        BoxShadow(
          color: (brandPrimary ?? const Color(0xFFFF8C5A)).withOpacity(0.4),
          blurRadius: 16,
          offset: const Offset(0, 8),
        ),
      ],
    );
  final List<BoxShadow> small;
  final List<BoxShadow> medium;
  final List<BoxShadow> large;
}
