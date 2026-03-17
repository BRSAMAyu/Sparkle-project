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
///   color: DS.brandPrimaryConst,
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
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/breakpoints.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/tokens_v2/animation_token.dart';
import 'package:sparkle/core/design/tokens_v2/responsive_system.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/design/tokens_v2/typography_token.dart';
import 'package:sparkle/core/utils/theme_utils.dart';

export '../statistics/statistics.dart';
export 'breakpoints.dart';
export 'color_extensions.dart';
export 'components/atoms/sparkle_button_v2.dart';
export 'materials.dart';
export 'responsive_widgets.dart';
export 'tokens_v2/animation_token.dart';
export 'tokens_v2/color_token.dart';
export 'tokens_v2/responsive_system.dart';
export 'tokens_v2/spacing_token.dart';
export 'tokens_v2/theme_manager.dart';
export 'tokens_v2/typography_token.dart';
export 'validation/design_validator.dart';
export 'widgets/app_feedback.dart';
export 'widgets/graphite_surfaces.dart';

/// MaterialApp 主题配置
class AppThemes {
  static ThemeData get lightTheme {
    final theme = ThemeManager().current;
    return _buildThemeData(theme, Brightness.light);
  }

  static ThemeData get darkTheme {
    final theme = ThemeManager().current;
    return _buildThemeData(theme, Brightness.dark);
  }

  static ThemeData _buildThemeData(
    SparkleThemeData theme,
    Brightness brightness,
  ) {
    // 🔧 根据亮度选择正确的 SparkleThemeExtension
    final sparkleExtension = brightness == Brightness.light
        ? SparkleThemeExtension.light()
        : SparkleThemeExtension.dark();

    final colors = theme.colors;
    final isDark = brightness == Brightness.dark;
    final textTheme = _buildTextTheme(theme);

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      primaryColor: colors.brandPrimary,
      scaffoldBackgroundColor: colors.surfacePrimary,
      colorScheme: ColorScheme.fromSeed(
        seedColor: colors.brandPrimary,
        brightness: brightness,
        primary: colors.brandPrimary,
        onPrimary: ThemeUtils.getContrastSafeText(
          colors.brandPrimary,
          darkText: colors.textPrimary,
        ),
        secondary: colors.brandSecondary,
        onSecondary: ThemeUtils.getContrastSafeText(
          colors.brandSecondary,
          darkText: colors.textPrimary,
        ),
        surface: colors.surfacePrimary,
        onSurface: colors.textPrimary,
        error: colors.semanticError,
        onError: ThemeUtils.getContrastSafeText(
          colors.semanticError,
          darkText: colors.textPrimary,
        ),
      ),
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: colors.surfacePrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          color: colors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
        systemOverlayStyle:
            isDark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
        iconTheme: IconThemeData(color: colors.textPrimary),
        actionsIconTheme: IconThemeData(color: colors.textPrimary),
      ),
      dividerColor: colors.surfaceTertiary,
      dividerTheme: DividerThemeData(
        color: colors.surfaceTertiary,
        thickness: 1,
        space: 1,
      ),
      splashFactory: InkSparkle.splashFactory,
      highlightColor: Colors.transparent,
      hoverColor: colors.brandPrimary.withValues(alpha: 0.04),
      splashColor: colors.brandPrimary.withValues(alpha: 0.08),
      cardTheme: _buildCardTheme(theme),
      buttonTheme: _buildButtonTheme(theme),
      inputDecorationTheme: _buildInputTheme(theme),
      listTileTheme: ListTileThemeData(
        iconColor: colors.textSecondary,
        textColor: colors.textPrimary,
        tileColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: colors.surfaceSecondary,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(
            color:
                colors.surfaceTertiary.withValues(alpha: isDark ? 0.95 : 0.8),
          ),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: colors.surfaceSecondary,
        modalBackgroundColor: colors.surfaceSecondary,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: colors.surfaceTertiary,
        contentTextStyle: textTheme.bodyMedium?.copyWith(
          color: colors.textPrimary,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: colors.surfaceSecondary,
        foregroundColor: colors.textPrimary,
        elevation: 0,
        hoverElevation: 0,
        focusElevation: 0,
        highlightElevation: 0,
        splashColor: colors.brandPrimary.withValues(alpha: 0.12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(
            color: colors.surfaceTertiary.withValues(alpha: 0.9),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: colors.surfaceSecondary,
        selectedColor: colors.brandPrimary.withValues(alpha: 0.14),
        disabledColor: colors.surfaceTertiary,
        secondarySelectedColor: colors.brandSecondary.withValues(alpha: 0.12),
        side: BorderSide(color: colors.surfaceTertiary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(999),
        ),
        labelStyle: textTheme.labelSmall?.copyWith(color: colors.textSecondary),
        secondaryLabelStyle: textTheme.labelSmall?.copyWith(
          color: colors.textPrimary,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: colors.brandPrimary,
        linearTrackColor: colors.surfaceTertiary,
        circularTrackColor: colors.surfaceTertiary,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return colors.brandPrimary;
          }
          return isDark ? colors.neutral500 : colors.neutral400;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return colors.brandPrimary.withValues(alpha: 0.36);
          }
          return colors.surfaceTertiary;
        }),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return colors.brandPrimary;
          }
          return Colors.transparent;
        }),
        side: BorderSide(color: colors.surfaceTertiary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
        ),
      ),
      radioTheme: RadioThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return colors.brandPrimary;
          }
          return colors.textSecondary;
        }),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: colors.surfaceSecondary,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: colors.surfaceTertiary),
        ),
        textStyle: textTheme.bodyMedium?.copyWith(color: colors.textPrimary),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor:
            colors.surfaceSecondary.withValues(alpha: isDark ? 0.96 : 0.92),
        height: 72,
        indicatorColor: colors.brandPrimary.withValues(alpha: 0.14),
        elevation: 0,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => textTheme.labelSmall?.copyWith(
            color: states.contains(WidgetState.selected)
                ? colors.textPrimary
                : colors.textSecondary,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w600
                : FontWeight.w500,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? colors.brandPrimary
                : colors.textSecondary,
          ),
        ),
      ),
      tabBarTheme: TabBarThemeData(
        dividerColor: colors.surfaceTertiary,
        labelColor: colors.textPrimary,
        unselectedLabelColor: colors.textSecondary,
        indicator: UnderlineTabIndicator(
          borderSide: BorderSide(color: colors.brandPrimary, width: 2),
        ),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: colors.surfaceTertiary,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: colors.surfaceTertiary.withValues(alpha: 0.9),
          ),
        ),
        textStyle: textTheme.labelSmall?.copyWith(color: colors.textPrimary),
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.macOS: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.linux: FadeForwardsPageTransitionsBuilder(),
          TargetPlatform.windows: FadeForwardsPageTransitionsBuilder(),
        },
      ),
      extensions: [
        _SparkleThemeExtension(theme),
        sparkleExtension, // 🔧 修复：注册公开的 SparkleThemeExtension
      ],
    );
  }

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
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(
            color: theme.colors.surfaceTertiary.withValues(alpha: 0.85),
          ),
        ),
        color: theme.colors.surfaceSecondary,
        surfaceTintColor: Colors.transparent,
      );

  static ButtonThemeData _buildButtonTheme(SparkleThemeData theme) =>
      ButtonThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(theme.spacing.sm),
        ),
        padding: EdgeInsets.symmetric(
          horizontal: theme.spacing.lg,
          vertical: theme.spacing.sm,
        ),
      );

  static InputDecorationTheme _buildInputTheme(SparkleThemeData theme) =>
      InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: theme.colors.surfaceTertiary),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: theme.colors.surfaceTertiary),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: theme.colors.brandPrimary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: theme.colors.semanticError, width: 1.5),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: theme.colors.semanticError, width: 2),
        ),
        filled: true,
        fillColor: theme.colors.surfaceSecondary,
        hintStyle: TextStyle(color: theme.colors.textSecondary),
        contentPadding: EdgeInsets.symmetric(
          horizontal: theme.spacing.lg,
          vertical: theme.spacing.lg,
        ),
      );
}

/// 主题扩展 - 用于访问自定义主题属性
@immutable
class _SparkleThemeExtension extends ThemeExtension<_SparkleThemeExtension> {
  const _SparkleThemeExtension(this.sparkle);
  final SparkleThemeData sparkle;

  @override
  _SparkleThemeExtension copyWith({SparkleThemeData? sparkle}) =>
      _SparkleThemeExtension(sparkle ?? this.sparkle);

  @override
  _SparkleThemeExtension lerp(
    ThemeExtension<_SparkleThemeExtension>? other,
    double t,
  ) {
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

  /// Whether the OS requests reduced motion or simplified navigation effects.
  bool get reduceMotion {
    final mediaQuery = MediaQuery.maybeOf(this);
    if (mediaQuery == null) return false;
    return mediaQuery.disableAnimations || mediaQuery.accessibleNavigation;
  }
}

/// Legacy color aliases used by older widgets.
@immutable
class SparkleColorAliases {
  const SparkleColorAliases(this._theme);
  final SparkleThemeData _theme;

  Color get surfaceCard => _theme.colors.surfaceSecondary;
  Color get surfaceElevated => _theme.colors.surfaceTertiary;
  Color get surfaceGlass => _theme.colors.surfacePrimary;
  Color get border => DS.border;
  Color get textPrimary => _theme.colors.textPrimary;
  Color get textSecondary => _theme.colors.textSecondary;

  LinearGradient getTaskGradient(String taskType) =>
      _theme.colors.getTaskGradient(taskType);
  Color getTaskColor(String taskType) => _theme.colors.getTaskColor(taskType);
  Color getPlanColor(String planType) => _theme.colors.getPlanColor(planType);
}

enum SparkleSurfaceRole {
  canvas,
  panel,
  card,
  elevated,
  glass,
  modal,
  accent,
}

enum SparkleFeedbackRole {
  info,
  success,
  warning,
  error,
  loading,
  undoable,
}

enum SparklePageRole {
  auth,
  dashboard,
  content,
  settings,
  immersive,
}

enum SparkleMotionToken {
  micro,
  standard,
  scene,
  hero,
}

@immutable
class SparkleFeedbackStyle {
  const SparkleFeedbackStyle({
    required this.backgroundColor,
    required this.foregroundColor,
    required this.icon,
    required this.duration,
  });

  final Color backgroundColor;
  final Color foregroundColor;
  final IconData icon;
  final Duration duration;
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
  }) =>
      LinearGradient(
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
  static Color get semanticSuccess => _theme.colors.semanticSuccess;
  static Color get semanticWarning => _theme.colors.semanticWarning;
  static Color get semanticError => _theme.colors.semanticError;
  static Color get info => _theme.colors.semanticInfo;
  static Color get primaryBase => brandPrimary;
  static Color get secondaryBase => brandSecondary;
  static Color get accent => brandSecondary;
  static Color get primaryDark =>
      _shiftLightness(brandPrimary, _isDark ? 0.1 : -0.15);
  static Color get secondaryDark =>
      _shiftLightness(brandSecondary, _isDark ? 0.1 : -0.15);
  static Color get secondaryBaseDark =>
      _shiftLightness(brandSecondary, _isDark ? 0.2 : -0.2);
  static Color get secondaryLight => _shiftLightness(brandSecondary, 0.2);
  static Color get successLight =>
      _shiftLightness(success, _isDark ? 0.15 : 0.2);
  static Color get warningLight =>
      _shiftLightness(warning, _isDark ? 0.15 : 0.2);
  static Color get errorLight => _shiftLightness(error, _isDark ? 0.15 : 0.2);
  static Color get infoLight => _shiftLightness(info, _isDark ? 0.15 : 0.2);

  // Surface colors
  static Color get surfacePrimary => _theme.colors.surfacePrimary;
  static Color get surfaceSecondary => _theme.colors.surfaceSecondary;
  static Color get surfaceTertiary => _theme.colors.surfaceTertiary;
  static Color get surfaceAmbient => _theme.colors.surfaceAmbient;
  static Color get surfacePrimaryElevated => _blend(
        surfacePrimary,
        surfaceTertiary,
        _isDark ? 0.35 : 0.12,
      );
  static Color get surfacePanel => _blend(
        surfaceSecondary,
        surfaceTertiary,
        _isDark ? 0.18 : 0.06,
      );
  static Color get surfaceOverlay => _isDark
      ? surfaceSecondary.withValues(alpha: 0.92)
      : surfacePrimary.withValues(alpha: 0.92);
  static Color get surfaceCanvas =>
      _blend(surfaceAmbient, surfacePrimary, 0.75);
  static Color get surfaceHigh =>
      _theme.colors.surfaceSecondary; // Alias for surfaceSecondary
  static Color get surface => surfaceSecondary;
  static Color get surfaceBase =>
      surfaceSecondary; // Alias for backward compatibility

  // Text colors
  static Color get textPrimary => _theme.colors.textPrimary;
  static Color get textSecondary => _theme.colors.textSecondary;
  static Color get textTertiary =>
      _theme.colors.textSecondary.withValues(alpha: 0.6); // Derived
  static Color get textDisabled => _theme.colors.textDisabled;
  static Color get textOnPrimary => ThemeUtils.getContrastSafeText(
        brandPrimary,
        darkText: neutral900,
      );
  static Color get onBrandPrimary => textOnPrimary;
  static Color get border => _isDark ? neutral600 : neutral300;
  static Color get borderStrong =>
      _blend(border, textPrimary, _isDark ? 0.16 : 0.08);
  static Color get borderSubtle =>
      border.withValues(alpha: _isDark ? 0.6 : 0.72);
  static Color get overlay30 =>
      (_isDark ? Colors.white : Colors.black).withValues(alpha: 0.3);
  static Color get overlay50 =>
      (_isDark ? Colors.white : Colors.black).withValues(alpha: 0.5);

  static Color get brandPrimary10 => brandPrimary.withValues(alpha: 0.1);
  static Color get brandPrimary20 => brandPrimary.withValues(alpha: 0.2);
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
  static Color get warning100 => warning.withValues(alpha: 0.1);
  static Color get warning200 => warning.withValues(alpha: 0.2);
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
  // Deep space colors use surfaceAmbient and surfacePrimary for proper dark mode support
  static Color get deepSpaceStart => _isDark
      ? _blend(
          _theme.colors.galaxyBackground, _theme.colors.surfaceAmbient, 0.5,)
      : _blend(neutral50, brandSecondary, 0.12);
  static Color get deepSpaceEnd => _isDark
      ? _blend(_theme.colors.galaxyShadow, _theme.colors.surfacePrimary, 0.42)
      : _blend(neutral100, brandPrimary, 0.08);
  static Color get deepSpaceSurface => _isDark
      ? _theme.colors.surfacePrimary
      : _blend(surfacePrimary, deepSpaceStart, 0.6);
  static Color get glassBackground =>
      surfacePrimary.withValues(alpha: _isDark ? 0.2 : 0.7);
  static Color get glassBorder =>
      _blend(surfaceTertiary, brandPrimary, 0.4).withValues(alpha: 0.25);
  static Color get avatarFallbackBackground => _isDark
      ? _blend(surfaceTertiary, brandSecondary, 0.18)
      : _blend(surfaceSecondary, brandSecondary, 0.12);
  static Color get avatarFallbackForeground =>
      _isDark ? textPrimary : _shiftLightness(brandSecondary, -0.18);
  static Color get prismBlue => info;
  static Color get prismGreen => success;
  static Color get prismPurple => brandSecondary;
  static Color get flameCore => _blend(warning, brandPrimary, 0.4);
  static Color get capsuleAccent =>
      _shiftLightness(brandSecondary, _isDark ? 0.12 : -0.05);

  // Gradients
  static LinearGradient get primaryGradient => _buildGradient(
        _isDark
            ? _blend(surfaceSecondary, brandSecondary, 0.12)
            : _blend(surfacePrimaryElevated, brandSecondary, 0.05),
        _isDark ? surfaceTertiary : surfaceSecondary,
      );
  static LinearGradient get secondaryGradient => _buildGradient(
        _isDark ? surfaceTertiary : surfacePrimaryElevated,
        _isDark
            ? _blend(surfaceSecondary, brandSecondary, 0.08)
            : _blend(surfaceSecondary, brandSecondary, 0.04),
      );
  static LinearGradient get secondaryGradientDark =>
      _buildGradient(secondaryBaseDark, brandPrimary);
  static LinearGradient get accentGradient =>
      _buildGradient(accent, _shiftLightness(accent, _isDark ? 0.1 : -0.05));
  static LinearGradient get infoGradient =>
      _buildGradient(info, info.withValues(alpha: 0.7));
  static LinearGradient get warningGradient =>
      _buildGradient(warning, warning.withValues(alpha: 0.7));
  static LinearGradient get successGradient =>
      _buildGradient(success, success.withValues(alpha: 0.7));
  static LinearGradient get errorGradient =>
      _buildGradient(error, error.withValues(alpha: 0.7));
  static LinearGradient get cardGradientNeutral =>
      _buildGradient(surfaceSecondary, surfacePrimary);
  static LinearGradient get deepSpaceGradient => _buildGradient(
        deepSpaceStart,
        deepSpaceEnd,
        begin: Alignment.topCenter,
        endAlignment: Alignment.bottomCenter,
      );
  static LinearGradient pageGradientForRole(SparklePageRole role) {
    switch (role) {
      case SparklePageRole.auth:
        return LinearGradient(
          colors: [
            surfacePrimary,
            _blend(surfacePrimary, surfaceCanvas, _isDark ? 0.52 : 0.36),
            surfaceCanvas,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case SparklePageRole.dashboard:
        return LinearGradient(
          colors: [
            _blend(surfacePrimary, surfaceCanvas, _isDark ? 0.42 : 0.28),
            _blend(surfaceCanvas, surfaceSecondary, _isDark ? 0.36 : 0.18),
            surfaceCanvas,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case SparklePageRole.content:
        return LinearGradient(
          colors: [
            surfacePrimary,
            _blend(surfacePrimary, surfaceCanvas, _isDark ? 0.64 : 0.48),
            surfaceCanvas,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case SparklePageRole.settings:
        return LinearGradient(
          colors: [
            surfacePrimary,
            _blend(surfacePrimary, surfaceSecondary, _isDark ? 0.52 : 0.32),
            surfaceCanvas,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case SparklePageRole.immersive:
        return LinearGradient(
          colors: [
            deepSpaceStart,
            _blend(deepSpaceStart, deepSpaceEnd, 0.4),
            deepSpaceEnd,
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
    }
  }

  static LinearGradient get flameGradient => _buildGradient(
        flameCore,
        warning,
        begin: Alignment.topCenter,
        endAlignment: Alignment.bottomCenter,
      );

  static Color pageScaffoldBackground(SparklePageRole role) {
    switch (role) {
      case SparklePageRole.immersive:
        return galaxyBackground;
      case SparklePageRole.dashboard:
        return surfaceCanvas;
      case SparklePageRole.auth:
      case SparklePageRole.content:
      case SparklePageRole.settings:
        return surfacePrimary;
    }
  }

  static Color surfaceRoleColor(SparkleSurfaceRole role) {
    switch (role) {
      case SparkleSurfaceRole.canvas:
        return surfaceCanvas;
      case SparkleSurfaceRole.panel:
        return surfacePanel;
      case SparkleSurfaceRole.card:
        return surfaceOverlay;
      case SparkleSurfaceRole.elevated:
        return surfacePrimaryElevated;
      case SparkleSurfaceRole.glass:
        return glassBackground;
      case SparkleSurfaceRole.modal:
        return _blend(surfaceOverlay, surfaceSecondary, _isDark ? 0.18 : 0.1);
      case SparkleSurfaceRole.accent:
        return _blend(surfacePanel, brandPrimary, _isDark ? 0.12 : 0.08);
    }
  }

  static SparkleFeedbackStyle feedbackStyle(SparkleFeedbackRole role) {
    final backgroundColor = switch (role) {
      SparkleFeedbackRole.info => surfaceTertiary,
      SparkleFeedbackRole.success => success,
      SparkleFeedbackRole.warning => warning,
      SparkleFeedbackRole.error => error,
      SparkleFeedbackRole.loading =>
        _blend(surfaceTertiary, brandSecondary, _isDark ? 0.28 : 0.18),
      SparkleFeedbackRole.undoable =>
        _blend(surfaceTertiary, brandPrimary, _isDark ? 0.22 : 0.12),
    };

    final foregroundColor = role == SparkleFeedbackRole.info ||
            role == SparkleFeedbackRole.loading ||
            role == SparkleFeedbackRole.undoable
        ? textPrimary
        : ThemeUtils.getContrastSafeText(
            backgroundColor,
            darkText: textPrimary,
          );

    final icon = switch (role) {
      SparkleFeedbackRole.info => Icons.info_outline,
      SparkleFeedbackRole.success => Icons.check_circle_outline,
      SparkleFeedbackRole.warning => Icons.warning_amber_rounded,
      SparkleFeedbackRole.error => Icons.error_outline,
      SparkleFeedbackRole.loading => Icons.hourglass_top_rounded,
      SparkleFeedbackRole.undoable => Icons.undo_rounded,
    };

    final duration = switch (role) {
      SparkleFeedbackRole.loading => const Duration(milliseconds: 1400),
      SparkleFeedbackRole.undoable => const Duration(seconds: 4),
      SparkleFeedbackRole.info ||
      SparkleFeedbackRole.success ||
      SparkleFeedbackRole.warning ||
      SparkleFeedbackRole.error =>
        const Duration(seconds: 3),
    };

    return SparkleFeedbackStyle(
      backgroundColor: backgroundColor,
      foregroundColor: foregroundColor,
      icon: icon,
      duration: duration,
    );
  }

  // 间距 (常量版本用于const构造函数)
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
  static const double xxxl = 64.0;

  static const double spacing2 = 2.0;
  static const double spacing4 = 4.0;
  static const double spacing6 = 6.0;
  static const double spacing8 = 8.0;
  static const double spacing10 = 10.0;
  static const double spacing12 = 12.0;
  static const double spacing16 = 16.0;
  static const double spacing18 = 18.0;
  static const double spacing20 = 20.0;
  static const double spacing24 = 24.0;
  static const double spacing32 = 32.0;
  static const double spacing40 = 40.0;
  static const double spacing64 = 64.0;

  // Const aliases for backward compatibility
  static const double smConst = 8.0;

  // Layout and sizing
  static const double breakpointTablet = LayoutBreakpoints.tablet;
  static const double breakpointDesktop = LayoutBreakpoints.desktop;
  static const double breakpointNarrow = Breakpoints.narrow;
  static const double breakpointStandard = Breakpoints.standard;
  static const double breakpointWide = Breakpoints.wide;
  static const double contentMaxWidthTablet = 720.0;
  static const double contentMaxWidthDesktop = 1200.0;
  static const double touchTargetMinSize = 48.0;
  static const double opacityDisabled = 0.4;

  // Radius
  static const double radius6 = 6.0;
  static const double radius8 = 8.0;
  static const double radius12 = 12.0;
  static const double radius16 = 16.0;
  static const double radius20 = 20.0;
  static const BorderRadius borderRadius4 =
      BorderRadius.all(Radius.circular(4.0));
  static const BorderRadius borderRadius6 =
      BorderRadius.all(Radius.circular(radius6));
  static const BorderRadius borderRadius8 =
      BorderRadius.all(Radius.circular(radius8));
  static const BorderRadius borderRadius12 =
      BorderRadius.all(Radius.circular(radius12));
  static const BorderRadius borderRadius16 =
      BorderRadius.all(Radius.circular(radius16));
  static const BorderRadius borderRadius20 =
      BorderRadius.all(Radius.circular(radius20));
  static const BorderRadius borderRadiusFull =
      BorderRadius.all(Radius.circular(999.0));
  static const double borderRadiusLg = radius16;
  static const double borderRadiusXl = radius20;

  // Icon sizes
  static const double iconSizeXs = 16.0;
  static const double iconSizeSm = 20.0;
  static const double iconSizeBase = 24.0;
  static const double iconSizeMd = iconSizeBase;
  static const double iconSizeLg = 32.0;
  static const double iconSizeXl = 40.0;
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
  static const FontWeight fontWeightSemiBold = fontWeightSemibold;
  static const FontWeight fontWeightBold = TypographySystem.weightBold;
  static const double lineHeightNormal = TypographySystem.leadingNormal;

  // 动画
  static Duration get quick => AnimationSystem.quick;
  static Duration get normal => AnimationSystem.normal;
  static Duration get slow => AnimationSystem.slow;
  static Duration get durationFast => AnimationSystem.quick;
  static Duration get durationNormal => AnimationSystem.normal;
  static Duration get durationSlow => AnimationSystem.slow;
  static Duration motionDuration(
    SparkleMotionToken token, {
    bool reduceMotion = false,
  }) {
    if (reduceMotion) {
      return Duration.zero;
    }

    switch (token) {
      case SparkleMotionToken.micro:
        return AnimationSystem.micro;
      case SparkleMotionToken.standard:
        return AnimationSystem.standard;
      case SparkleMotionToken.scene:
        return AnimationSystem.scene;
      case SparkleMotionToken.hero:
        return AnimationSystem.hero;
    }
  }

  static Curve motionCurve(SparkleMotionToken token) {
    switch (token) {
      case SparkleMotionToken.micro:
        return AnimationSystem.easeOut;
      case SparkleMotionToken.standard:
        return AnimationSystem.smooth;
      case SparkleMotionToken.scene:
        return Curves.easeInOutCubicEmphasized;
      case SparkleMotionToken.hero:
        return Curves.easeOutCubic;
    }
  }

  static Curve get curveEaseOut => AnimationSystem.easeOut;
  static Curve get curveEaseInOut => Curves.easeInOut;

  // 排版
  static TextStyle get displayLarge => TypographySystem.displayLarge();
  static TextStyle get headingLarge => TypographySystem.headingLarge();
  static TextStyle get titleLarge => TypographySystem.titleLarge();
  static TextStyle get bodyLarge => TypographySystem.bodyLarge();
  static TextStyle get bodyMedium => TypographySystem.bodyMedium();
  static TextStyle get bodySmall => TypographySystem.labelSmall();
  static TextStyle get labelLarge => TypographySystem.labelLarge();
  static TextStyle get labelSmall => TypographySystem.labelSmall();

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
          color: brandPrimary.withValues(alpha: _isDark ? 0.18 : 0.12),
          blurRadius: 18,
          offset: const Offset(0, 10),
        ),
      ];

  // 任务类型颜色
  static Color getTaskColor(String taskType) =>
      _theme.colors.getTaskColor(taskType);
  static Color getPlanColor(String planType) =>
      _theme.colors.getPlanColor(planType);
  static LinearGradient getTaskGradient(String taskType) =>
      _theme.colors.getTaskGradient(taskType);

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
  static Color getStatusColor(String userStatus) =>
      _theme.colors.getStatusColor(userStatus);
  static Color get statusOnline => _theme.colors.statusOnline;
  static Color get statusOffline => _theme.colors.statusOffline;
  static Color get statusInvisible => _theme.colors.statusInvisible;

  // 中性色
  static Color get neutral0 => _isDark ? const Color(0xFFF4F1EB) : Colors.white;
  static Color get neutral50 =>
      _blend(surfacePrimary, _theme.colors.neutral200, 0.4);
  static Color get neutral100 =>
      _blend(surfacePrimary, _theme.colors.neutral200, 0.7);
  static Color get neutral200 => _theme.colors.neutral200;
  static Color get neutral300 => _theme.colors.neutral300;
  static Color get neutral400 => _theme.colors.neutral400;
  static Color get neutral500 => _theme.colors.neutral500;
  static Color get neutral600 => _theme.colors.neutral600;
  static Color get neutral700 =>
      _blend(_theme.colors.neutral600, _theme.colors.textPrimary, 0.35);
  static Color get neutral800 =>
      _blend(_theme.colors.neutral600, _theme.colors.textPrimary, 0.7);
  static Color get neutral900 => _theme.colors.textPrimary;

  // 聊天气泡颜色
  static Color get chatBubbleUser => _theme.colors.chatBubbleUser;
  static Color get chatBubbleUserText => _theme.colors.chatBubbleUserText;
  static Color get chatBubbleOther => _theme.colors.chatBubbleOther;
  static Color get chatBubbleOtherText => _theme.colors.chatBubbleOtherText;

  // Galaxy专用颜色
  static Color get galaxyBackground => _theme.colors.galaxyBackground;
  static Color get galaxyShadow => _theme.colors.galaxyShadow;

  // ============================================
  // 稀有度系统颜色 (Rarity System)
  // ============================================

  /// 普通稀有度 - 灰色系
  static Color get rarityCommon => neutral400;
  static Color get rarityCommonBg => neutral200;
  static Color get rarityCommonText => neutral700;

  /// 稀有 - 金色系
  static const Color rarityRare = Color(0xFFFFD700);
  static Color get rarityRareBg => _isDark
      ? const Color(0xFF3D3000) // 深色模式下的暗金背景
      : const Color(0xFFFFF8DC);
  static const Color rarityRareText = Color(0xFFB8860B);

  /// 史诗 - 紫色系
  static const Color rarityEpic = Color(0xFF9B59B6);
  static Color get rarityEpicBg => _isDark
      ? const Color(0xFF2D1F3D) // 深色模式下的暗紫背景
      : const Color(0xFFF3E5F5);
  static const Color rarityEpicText = Color(0xFF7B1FA2);

  /// 传说 - 彩虹/红色系
  static const Color rarityLegendary = Color(0xFFFF6B6B);
  static Color get rarityLegendaryBg => _isDark
      ? const Color(0xFF3D1F1F) // 深色模式下的暗红背景
      : const Color(0xFFFFEBEE);
  static const Color rarityLegendaryText = Color(0xFFD32F2F);

  /// 获取稀有度颜色
  static Color getRarityColor(String rarity) {
    switch (rarity.toLowerCase()) {
      case 'rare':
        return rarityRare;
      case 'epic':
        return rarityEpic;
      case 'legendary':
        return rarityLegendary;
      default:
        return rarityCommon;
    }
  }

  /// 获取稀有度背景色
  static Color getRarityBackground(String rarity) {
    switch (rarity.toLowerCase()) {
      case 'rare':
        return rarityRareBg;
      case 'epic':
        return rarityEpicBg;
      case 'legendary':
        return rarityLegendaryBg;
      default:
        return rarityCommonBg;
    }
  }

  // ============================================
  // 连胜等级颜色 (Streak Tier System)
  // ============================================

  /// 入门级 (< 7天) - 使用 warning 色
  static Color get streakBeginner => warning;

  /// 进阶级 (7-13天) - 橙色
  static const Color streakIntermediate = Color(0xFFFF9500);

  /// 专家级 (14-29天) - 橙红色
  static const Color streakExpert = Color(0xFFFF6B00);

  /// 大师级 (30天+) - 金色
  static const Color streakMaster = Color(0xFFFFD700);

  /// 根据连胜天数获取火焰颜色
  static Color getStreakColor(int streakDays) {
    if (streakDays >= 30) return streakMaster;
    if (streakDays >= 14) return streakExpert;
    if (streakDays >= 7) return streakIntermediate;
    return streakBeginner;
  }

  // ============================================
  // 向后兼容属性（用于统计模块）
  // ============================================

  /// 文本样式快捷方式
  static TextStyle get textStyle => TextStyle(
        fontSize: fontSizeBase,
        fontWeight: fontWeightRegular,
        color: textPrimary,
      );

  static TextStyle get headlineStyle => TextStyle(
        fontSize: fontSizeLg,
        fontWeight: fontWeightSemibold,
        color: textPrimary,
      );

  static TextStyle get bodyStyle => TextStyle(
        fontSize: fontSizeBase,
        fontWeight: fontWeightRegular,
        color: textSecondary,
      );

  static TextStyle get captionStyle => TextStyle(
        fontSize: fontSizeSm,
        fontWeight: fontWeightRegular,
        color: textTertiary,
      );

  /// 颜色快捷方式
  static const Color white = Colors.white;
  static const Color black = Colors.black;

  /// 圆角快捷方式（用于DSC替代）
  static const double borderRadiusSM = radius8;
  static const double borderRadiusMD = radius12;
  static const double borderRadiusLG = radius16;
  static const double borderRadiusXL = radius20;

  /// 字体大小快捷方式（别名）
  static const double fontSizeSM = fontSizeSm;
  static const double fontSizeMD = fontSizeBase;
  static const double fontSizeLG = fontSizeLg;
  static const double fontSizeXL = fontSizeXl;
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
