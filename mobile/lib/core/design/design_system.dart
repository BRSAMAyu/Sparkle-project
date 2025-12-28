/// Sparkle Design System 2.0 - 集成入口
///
/// 这是一个完整的、可扩展的设计系统，提供：
/// - 语义化设计令牌
/// - 动态主题管理
/// - 响应式布局系统
/// - 原子化组件库
/// - 设计验证工具
///
/// 使用示例:
/// ```dart
/// // 1. 初始化主题
/// await ThemeManager().initialize();
///
/// // 2. 在MaterialApp中使用
/// MaterialApp(
///   theme: AppThemes.lightTheme,
///   darkTheme: AppThemes.darkTheme,
///   home: YourApp(),
/// );
///
/// // 3. 在UI中使用设计令牌
/// Container(
///   color: DS.brandPrimary,
///   padding: SpacingSystem.edgeLg,
///   child: SparkleButton.primary(
///     label: '点击',
///     onPressed: () {},
///   ),
/// );
/// ```
library;

// 便捷导入
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/tokens_v2/animation_token.dart';
import 'package:sparkle/core/design/tokens_v2/responsive_system.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/design/tokens_v2/typography_token.dart';

export 'components/atoms/sparkle_button_v2.dart';
export 'tokens_v2/animation_token.dart';
export 'tokens_v2/color_token.dart';
export 'tokens_v2/responsive_system.dart';
export 'tokens_v2/spacing_token.dart';
export 'tokens_v2/theme_manager.dart';
export 'tokens_v2/typography_token.dart';
export 'validation/design_validator.dart';

/// MaterialApp 主题配置
class AppThemes {
  static ThemeData get lightTheme {
    final theme = ThemeManager().themeForBrightness(Brightness.light);
    return _buildThemeData(theme, Brightness.light);
  }

  static ThemeData get darkTheme {
    final theme = ThemeManager().themeForBrightness(Brightness.dark);
    return _buildThemeData(theme, Brightness.dark);
  }

  static ThemeData _buildThemeData(SparkleThemeData theme, Brightness brightness) => ThemeData(
      useMaterial3: true,
      brightness: brightness,
      primaryColor: theme.colors.brandPrimary,
      scaffoldBackgroundColor: theme.colors.surfacePrimary,
      colorScheme: ColorScheme.fromSeed(
        seedColor: theme.colors.brandPrimary,
        brightness: brightness,
        primary: theme.colors.brandPrimary,
        secondary: theme.colors.brandSecondary,
        surface: theme.colors.surfacePrimary,
        error: theme.colors.semanticError,
      ),
      textTheme: _buildTextTheme(theme),
      cardTheme: _buildCardTheme(theme),
      buttonTheme: _buildButtonTheme(theme),
      inputDecorationTheme: _buildInputTheme(theme),
      extensions: [
        _SparkleThemeExtension(theme),
      ],
    );

  static TextTheme _buildTextTheme(SparkleThemeData theme) => TextTheme(
      displayLarge: theme.typography.displayLarge,
      headlineLarge: theme.typography.headingLarge,
      headlineMedium: theme.typography.headingMedium,
      titleLarge: theme.typography.titleLarge,
      bodyLarge: theme.typography.bodyLarge,
      bodyMedium: theme.typography.bodyMedium,
      labelLarge: theme.typography.labelLarge,
      labelSmall: theme.typography.labelSmall,
    );

  static CardThemeData _buildCardTheme(SparkleThemeData theme) => CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
      ),
      color: theme.colors.surfaceSecondary,
    );

  static ButtonThemeData _buildButtonTheme(SparkleThemeData theme) => ButtonThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: theme.spacing.lg,
        vertical: theme.spacing.sm,
      ),
    );

  static InputDecorationTheme _buildInputTheme(SparkleThemeData theme) => InputDecorationTheme(
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
        borderSide: BorderSide(color: theme.colors.surfaceTertiary),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
        borderSide: BorderSide(color: theme.colors.surfaceTertiary),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
        borderSide: BorderSide(color: theme.colors.brandPrimary, width: 2),
      ),
      filled: true,
      fillColor: theme.colors.surfaceSecondary,
      contentPadding: EdgeInsets.all(theme.spacing.lg),
    );
}

/// 主题扩展 - 用于访问自定义主题属性
@immutable
class _SparkleThemeExtension extends ThemeExtension<_SparkleThemeExtension> {

  const _SparkleThemeExtension(this.sparkle);
  final SparkleThemeData sparkle;

  @override
  _SparkleThemeExtension copyWith({SparkleThemeData? sparkle}) => _SparkleThemeExtension(sparkle ?? this.sparkle);

  @override
  _SparkleThemeExtension lerp(ThemeExtension<_SparkleThemeExtension>? other, double t) {
    if (other is! _SparkleThemeExtension) return this;
    return _SparkleThemeExtension(sparkle);
  }
}

/// 便捷上下文扩展
extension SparkleContext on BuildContext {
  /// 访问当前主题数据
  SparkleThemeData get sparkleTheme {
    final extension = Theme.of(this).extension<_SparkleThemeExtension>();
    return extension?.sparkle ?? ThemeManager().current;
  }

  /// 访问颜色
  SparkleColors get sparkleColors => sparkleTheme.colors;

  /// 访问排版
  SparkleTypography get sparkleTypography => sparkleTheme.typography;

  /// 访问间距
  SparkleSpacing get sparkleSpacing => sparkleTheme.spacing;

  /// 访问动画
  SparkleAnimations get sparkleAnimations => sparkleTheme.animations;

  /// 访问阴影
  SparkleShadows get sparkleShadows => sparkleTheme.shadows;

  /// Legacy shorthand used across the UI
  SparkleColorAliases get colors => SparkleColorAliases(sparkleTheme);

  /// 响应式信息
  BreakpointInfo get breakpointInfo => ResponsiveSystem.getBreakpointInfo(this);

  /// 是否为移动设备
  bool get isMobile => ResponsiveSystem.isMobile(this);

  /// 是否为平板
  bool get isTablet => ResponsiveSystem.isTablet(this);

  /// 是否为桌面
  bool get isDesktop => ResponsiveSystem.isDesktop(this);

  /// 是否横屏
  bool get isLandscape => ResponsiveSystem.isLandscape(this);
}

/// Legacy color aliases used by older widgets.
@immutable
class SparkleColorAliases {
  SparkleColorAliases(this._theme);
  final SparkleThemeData _theme;

  Color get surfaceCard => _theme.colors.surfaceSecondary;
  Color get surfaceElevated => _theme.colors.surfaceTertiary;
  Color get surfaceGlass => _theme.colors.surfacePrimary;
  Color get border => DS.border;
  Color get textPrimary => _theme.colors.textPrimary;
  Color get textSecondary => _theme.colors.textSecondary;

  LinearGradient getTaskGradient(String taskType) => _theme.colors.getTaskGradient(taskType);
  Color getTaskColor(String taskType) => _theme.colors.getTaskColor(taskType);
  Color getPlanColor(String planType) => _theme.colors.getPlanColor(planType);
}

/// 设计令牌快捷访问
class DS {
  DS._();

  // 缓存 ThemeManager 实例以提升性能
  static SparkleThemeData get _theme => ThemeManager().current;
  static bool get _isDark => _theme.colors.brightness == Brightness.dark;

  static Color _blend(Color a, Color b, double t) => Color.lerp(a, b, t) ?? a;

  static Color _shiftLightness(Color color, double amount) {
    final hsl = HSLColor.fromColor(color);
    final lightness = (hsl.lightness + amount).clamp(0.0, 1.0);
    return hsl.withLightness(lightness).toColor();
  }

  static LinearGradient _buildGradient(
    Color start,
    Color end, {
    Alignment begin = Alignment.topLeft,
    Alignment endAlignment = Alignment.bottomRight,
  }) => LinearGradient(
      colors: [start, end],
      begin: begin,
      end: endAlignment,
    );

  // 颜色
  static Color get brandPrimary => _theme.colors.brandPrimary;
  static Color get brandSecondary => _theme.colors.brandSecondary;
  static Color get success => _theme.colors.semanticSuccess;
  static Color get warning => _theme.colors.semanticWarning;
  static Color get error => _theme.colors.semanticError;
  static Color get info => _theme.colors.semanticInfo;
  static Color get primaryBase => brandPrimary;
  static Color get secondaryBase => brandSecondary;
  static Color get accent => brandSecondary;
  static Color get primaryDark => _shiftLightness(brandPrimary, _isDark ? 0.1 : -0.15);
  static Color get secondaryDark => _shiftLightness(brandSecondary, _isDark ? 0.1 : -0.15);
  static Color get secondaryBaseDark => _shiftLightness(brandSecondary, _isDark ? 0.2 : -0.2);
  static Color get secondaryLight => _shiftLightness(brandSecondary, 0.2);
  static Color get successLight => _shiftLightness(success, _isDark ? 0.15 : 0.2);
  static Color get warningLight => _shiftLightness(warning, _isDark ? 0.15 : 0.2);
  static Color get errorLight => _shiftLightness(error, _isDark ? 0.15 : 0.2);
  static Color get infoLight => _shiftLightness(info, _isDark ? 0.15 : 0.2);

  // Surface colors
  static Color get surfacePrimary => _theme.colors.surfacePrimary;
  static Color get surfaceSecondary => _theme.colors.surfaceSecondary;
  static Color get surfaceTertiary => _theme.colors.surfaceTertiary;
  static Color get surfaceHigh => _theme.colors.surfaceSecondary; // Alias for surfaceSecondary
  static Color get surface => surfaceSecondary;

  // Text colors
  static Color get textPrimary => _theme.colors.textPrimary;
  static Color get textSecondary => _theme.colors.textSecondary;
  static Color get textTertiary => _theme.colors.textSecondary.withValues(alpha: 0.6); // Derived
  static Color get border => _isDark ? neutral600 : neutral300;
  static Color get overlay30 => (_isDark ? Colors.white : Colors.black).withValues(alpha: 0.3);

  static Color get brandPrimary10 => brandPrimary.withValues(alpha: 0.1);
  static Color get brandPrimary12 => brandPrimary.withValues(alpha: 0.12);
  static Color get brandPrimary24 => brandPrimary.withValues(alpha: 0.24);
  static Color get brandPrimary26 => brandPrimary.withValues(alpha: 0.26);
  static Color get brandPrimary30 => brandPrimary.withValues(alpha: 0.3);
  static Color get brandPrimary38 => brandPrimary.withValues(alpha: 0.38);
  static Color get brandPrimary45 => brandPrimary.withValues(alpha: 0.45);
  static Color get brandPrimary54 => brandPrimary.withValues(alpha: 0.54);
  static Color get brandPrimary70 => brandPrimary.withValues(alpha: 0.7);
  static Color get brandPrimary87 => brandPrimary.withValues(alpha: 0.87);
  static Color get brandPrimaryAccent => brandSecondary;
  static Color get successAccent => success.withValues(alpha: 0.2);
  static Color get errorAccent => error.withValues(alpha: 0.2);
  static Color get warningAccent => warning.withValues(alpha: 0.2);

  // Material Design shade-like color variants
  static Color get brandPrimary50 => brandPrimary.withValues(alpha: 0.05);
  static Color get brandPrimary100 => brandPrimary.withValues(alpha: 0.1);
  static Color get brandPrimary200 => brandPrimary.withValues(alpha: 0.2);
  static Color get brandPrimary300 => brandPrimary.withValues(alpha: 0.3);
  static Color get brandPrimary400 => brandPrimary.withValues(alpha: 0.4);
  static Color get brandPrimary500 => brandPrimary; // Base
  static Color get brandPrimary600 => brandPrimary.withValues(alpha: 0.7);
  static Color get brandPrimary700 => brandPrimary.withValues(alpha: 0.8);
  static Color get brandPrimary800 => brandPrimary.withValues(alpha: 0.9);
  static Color get brandPrimary900 => brandPrimary; // Fully opaque
  
  // Const variants for backward compatibility (for const constructors)
  static Color get brandPrimaryConst => brandPrimary;
  static Color get brandPrimary10Const => brandPrimary10;
  static Color get brandPrimary30Const => brandPrimary30;
  static Color get brandPrimary38Const => brandPrimary38;
  static Color get brandPrimary54Const => brandPrimary54;
  static Color get brandPrimary70Const => brandPrimary70;

  static Color get error50 => error.withValues(alpha: 0.05);
  static Color get error100 => error.withValues(alpha: 0.1);
  static Color get error200 => error.withValues(alpha: 0.2);
  static Color get error300 => error.withValues(alpha: 0.3);
  static Color get error400 => error.withValues(alpha: 0.4);
  static Color get error500 => error; // Base
  static Color get error600 => error.withValues(alpha: 0.7);
  static Color get error700 => error.withValues(alpha: 0.8);
  static Color get error800 => error.withValues(alpha: 0.9);
  static Color get error900 => error; // Fully opaque

  static Color get success50 => success.withValues(alpha: 0.05);
  static Color get success100 => success.withValues(alpha: 0.1);
  static Color get success200 => success.withValues(alpha: 0.2);
  static Color get success300 => success.withValues(alpha: 0.3);
  static Color get success400 => success.withValues(alpha: 0.4);
  static Color get success500 => success; // Base
  static Color get success600 => success.withValues(alpha: 0.7);
  static Color get success700 => success.withValues(alpha: 0.8);
  static Color get success800 => success.withValues(alpha: 0.9);
  static Color get success900 => success; // Fully opaque
  
  // Const variants for semantic colors
  static Color get successConst => success;

  // Special surfaces and accents
  static Color get deepSpaceStart => _blend(neutral900, brandPrimary, _isDark ? 0.12 : 0.22);
  static Color get deepSpaceEnd => _blend(neutral800, brandSecondary, _isDark ? 0.1 : 0.18);
  static Color get deepSpaceSurface => _blend(surfacePrimary, deepSpaceStart, 0.6);
  static Color get glassBackground => surfacePrimary.withValues(alpha: _isDark ? 0.2 : 0.7);
  static Color get glassBorder => _blend(surfaceTertiary, brandPrimary, 0.4).withValues(alpha: 0.25);
  static Color get prismBlue => info;
  static Color get prismGreen => success;
  static Color get prismPurple => brandSecondary;
  static Color get flameCore => _blend(warning, brandPrimary, 0.4);

  // Gradients
  static LinearGradient get primaryGradient => _buildGradient(brandPrimary, brandSecondary);
  static LinearGradient get secondaryGradient => _buildGradient(brandSecondary, brandPrimary);
  static LinearGradient get secondaryGradientDark => _buildGradient(secondaryBaseDark, brandPrimary);
  static LinearGradient get accentGradient => _buildGradient(accent, _shiftLightness(accent, _isDark ? 0.1 : -0.05));
  static LinearGradient get infoGradient => _buildGradient(info, info.withValues(alpha: 0.7));
  static LinearGradient get warningGradient => _buildGradient(warning, warning.withValues(alpha: 0.7));
  static LinearGradient get successGradient => _buildGradient(success, success.withValues(alpha: 0.7));
  static LinearGradient get errorGradient => _buildGradient(error, error.withValues(alpha: 0.7));
  static LinearGradient get cardGradientNeutral => _buildGradient(surfaceSecondary, surfacePrimary);
  static LinearGradient get deepSpaceGradient => _buildGradient(
      deepSpaceStart,
      deepSpaceEnd,
      begin: Alignment.topCenter,
      endAlignment: Alignment.bottomCenter,
    );
  static LinearGradient get flameGradient => _buildGradient(
      flameCore,
      warning,
      begin: Alignment.topCenter,
      endAlignment: Alignment.bottomCenter,
    );

  // 间距 (常量版本用于const构造函数)
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
  static const double xxxl = 64.0;

  static const double spacing4 = 4.0;
  static const double spacing8 = 8.0;
  static const double spacing10 = 10.0;
  static const double spacing12 = 12.0;
  static const double spacing16 = 16.0;
  static const double spacing20 = 20.0;
  static const double spacing24 = 24.0;
  static const double spacing32 = 32.0;
  static const double spacing40 = 40.0;
  static const double spacing64 = 64.0;

  // Const aliases for backward compatibility
  static const double smConst = 8.0;

  // Layout and sizing
  static const double breakpointTablet = 768.0;
  static const double breakpointDesktop = 1024.0;
  static const double contentMaxWidthTablet = 720.0;
  static const double contentMaxWidthDesktop = 1200.0;
  static const double touchTargetMinSize = 48.0;
  static const double opacityDisabled = 0.4;

  // Radius
  static const double radius8 = 8.0;
  static const double radius12 = 12.0;
  static const double radius16 = 16.0;
  static const double radius20 = 20.0;
  static const BorderRadius borderRadius4 = BorderRadius.all(Radius.circular(4.0));
  static const BorderRadius borderRadius8 = BorderRadius.all(Radius.circular(radius8));
  static const BorderRadius borderRadius12 = BorderRadius.all(Radius.circular(radius12));
  static const BorderRadius borderRadius16 = BorderRadius.all(Radius.circular(radius16));
  static const BorderRadius borderRadius20 = BorderRadius.all(Radius.circular(radius20));
  static const BorderRadius borderRadiusFull = BorderRadius.all(Radius.circular(999.0));

  // Icon sizes
  static const double iconSizeXs = 16.0;
  static const double iconSizeSm = 20.0;
  static const double iconSizeBase = 24.0;
  static const double iconSizeLg = 32.0;
  static const double iconSize3xl = 48.0;

  // Typography
  static const double _fontRatio = 1.25;
  static const double fontSizeXs = 12.0;
  static const double fontSizeSm = 14.0;
  static const double fontSizeBase = 16.0;
  static const double fontSizeLg = fontSizeBase * _fontRatio;
  static const double fontSizeXl = fontSizeLg * _fontRatio;
  static const double fontSize2xl = fontSizeXl * _fontRatio;
  static const double fontSize3xl = fontSize2xl * _fontRatio;
  static const double fontSize4xl = fontSize3xl * _fontRatio;
  static const double fontSize5xl = fontSize4xl * _fontRatio;
  static const double fontSize6xl = fontSize5xl * _fontRatio;
  static const FontWeight fontWeightRegular = TypographySystem.weightRegular;
  static const FontWeight fontWeightMedium = TypographySystem.weightMedium;
  static const FontWeight fontWeightSemibold = TypographySystem.weightSemibold;
  static const FontWeight fontWeightBold = TypographySystem.weightBold;
  static const double lineHeightNormal = TypographySystem.leadingNormal;

  // 动画
  static Duration get quick => AnimationSystem.quick;
  static Duration get normal => AnimationSystem.normal;
  static Duration get slow => AnimationSystem.slow;
  static Duration get durationFast => AnimationSystem.quick;
  static Duration get durationNormal => AnimationSystem.normal;
  static Duration get durationSlow => AnimationSystem.slow;
  static Curve get curveEaseOut => AnimationSystem.easeOut;
  static Curve get curveEaseInOut => Curves.easeInOut;

  // 排版
  static TextStyle get displayLarge => TypographySystem.displayLarge();
  static TextStyle get headingLarge => TypographySystem.headingLarge();
  static TextStyle get bodyLarge => TypographySystem.bodyLarge();
  static TextStyle get labelLarge => TypographySystem.labelLarge();

  // Shadows
  static List<BoxShadow> get shadowSm => _theme.shadows.small;
  static List<BoxShadow> get shadowMd => _theme.shadows.medium;
  static List<BoxShadow> get shadowLg => _theme.shadows.large;
  static List<BoxShadow> get shadowXl => [
      BoxShadow(
        color: brandPrimary.withValues(alpha: _isDark ? 0.25 : 0.12),
        blurRadius: 24,
        offset: const Offset(0, 12),
      ),
    ];
  static List<BoxShadow> get shadowPrimary => [
      BoxShadow(
        color: brandPrimary.withValues(alpha: _isDark ? 0.3 : 0.2),
        blurRadius: 16,
        offset: const Offset(0, 8),
      ),
    ];

  // 任务类型颜色
  static Color getTaskColor(String taskType) => _theme.colors.getTaskColor(taskType);
  static Color getPlanColor(String planType) => _theme.colors.getPlanColor(planType);
  static LinearGradient getTaskGradient(String taskType) => _theme.colors.getTaskGradient(taskType);

  // 任务类型颜色快捷方式
  static Color get taskLearning => _theme.colors.taskLearning;
  static Color get taskTraining => _theme.colors.taskTraining;
  static Color get taskErrorFix => _theme.colors.taskErrorFix;
  static Color get taskReflection => _theme.colors.taskReflection;
  static Color get taskSocial => _theme.colors.taskSocial;
  static Color get taskPlanning => _theme.colors.taskPlanning;
  static Color get planSprint => _theme.colors.planSprint;
  static Color get planGrowth => _theme.colors.planGrowth;

  // 用户状态颜色
  static Color getStatusColor(String userStatus) => _theme.colors.getStatusColor(userStatus);
  static Color get statusOnline => _theme.colors.statusOnline;
  static Color get statusOffline => _theme.colors.statusOffline;
  static Color get statusInvisible => _theme.colors.statusInvisible;

  // 中性色
  static Color get neutral50 => _blend(surfacePrimary, _theme.colors.neutral200, 0.4);
  static Color get neutral100 => _blend(surfacePrimary, _theme.colors.neutral200, 0.7);
  static Color get neutral200 => _theme.colors.neutral200;
  static Color get neutral300 => _theme.colors.neutral300;
  static Color get neutral400 => _theme.colors.neutral400;
  static Color get neutral500 => _theme.colors.neutral500;
  static Color get neutral600 => _theme.colors.neutral600;
  static Color get neutral700 => _blend(_theme.colors.neutral600, _theme.colors.textPrimary, 0.35);
  static Color get neutral800 => _blend(_theme.colors.neutral600, _theme.colors.textPrimary, 0.7);
  static Color get neutral900 => _theme.colors.textPrimary;
}

/// Extension on Color to provide Material Design shade-like methods
extension ColorShades on Color {
  /// Returns a new color with the given alpha value
  Color withAlphaValue(double alpha) => withValues(alpha: alpha);

  /// Material Design shade-like getters
  Color get shade50 => withValues(alpha: 0.05);
  Color get shade100 => withValues(alpha: 0.1);
  Color get shade200 => withValues(alpha: 0.2);
  Color get shade300 => withValues(alpha: 0.3);
  Color get shade400 => withValues(alpha: 0.4);
  Color get shade500 => this; // Base color
  Color get shade600 => withValues(alpha: 0.7);
  Color get shade700 => withValues(alpha: 0.8);
  Color get shade800 => withValues(alpha: 0.9);
  Color get shade900 => this; // Fully opaque
}

/// 设计系统初始化器
class DesignSystemInitializer {
  static bool _initialized = false;

  /// 初始化设计系统
  static Future<void> initialize() async {
    if (_initialized) return;

    // 初始化主题管理器
    await ThemeManager().initialize();

    _initialized = true;
  }

  /// 重置为默认设置
  static Future<void> reset() async {
    await ThemeManager().reset();
  }

  /// 检查系统状态
  static Map<String, dynamic> get status => {
      'initialized': _initialized,
      'themeMode': ThemeManager().mode.name,
      'brandPreset': ThemeManager().brandPreset.name,
      'highContrast': ThemeManager().highContrast,
      'version': '2.0.0',
    };
}
