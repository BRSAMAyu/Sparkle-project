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
///   color: AppDesignTokens.brandPrimary,
///   padding: SpacingSystem.edgeLg,
///   child: SparkleButton.primary(
///     label: '点击',
///     onPressed: () {},
///   ),
/// );
/// ```
library;

export 'tokens_v2/color_token.dart';
export 'tokens_v2/spacing_token.dart';
export 'tokens_v2/typography_token.dart';
export 'tokens_v2/animation_token.dart';
export 'tokens_v2/theme_manager.dart';
export 'tokens_v2/responsive_system.dart';

export 'components/atoms/sparkle_button_v2.dart';

export 'validation/design_validator.dart';

// 便捷导入
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme_manager.dart';

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

  static ThemeData _buildThemeData(SparkleThemeData theme, Brightness brightness) {
    return ThemeData(
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
  }

  static TextTheme _buildTextTheme(SparkleThemeData theme) {
    return TextTheme(
      displayLarge: theme.typography.displayLarge,
      headlineLarge: theme.typography.headingLarge,
      headlineMedium: theme.typography.headingMedium,
      titleLarge: theme.typography.titleLarge,
      bodyLarge: theme.typography.bodyLarge,
      bodyMedium: theme.typography.bodyMedium,
      labelLarge: theme.typography.labelLarge,
      labelSmall: theme.typography.labelSmall,
    );
  }

  static CardThemeData _buildCardTheme(SparkleThemeData theme) {
    return CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
      ),
      color: theme.colors.surfaceSecondary,
    );
  }

  static ButtonThemeData _buildButtonTheme(SparkleThemeData theme) {
    return ButtonThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(theme.spacing.sm),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: theme.spacing.lg,
        vertical: theme.spacing.sm,
      ),
    );
  }

  static InputDecorationTheme _buildInputTheme(SparkleThemeData theme) {
    return InputDecorationTheme(
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
}

/// 主题扩展 - 用于访问自定义主题属性
@immutable
class _SparkleThemeExtension extends ThemeExtension<_SparkleThemeExtension> {
  final SparkleThemeData sparkle;

  const _SparkleThemeExtension(this.sparkle);

  @override
  _SparkleThemeExtension copyWith({SparkleThemeData? sparkle}) {
    return _SparkleThemeExtension(sparkle ?? this.sparkle);
  }

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

/// 设计令牌快捷访问
class DS {
  DS._();

  // 颜色
  static Color get brandPrimary => ThemeManager().current.colors.brandPrimary;
  static Color get brandSecondary => ThemeManager().current.colors.brandSecondary;
  static Color get success => ThemeManager().current.colors.semanticSuccess;
  static Color get warning => ThemeManager().current.colors.semanticWarning;
  static Color get error => ThemeManager().current.colors.semanticError;
  static Color get info => ThemeManager().current.colors.semanticInfo;

  // 间距
  static double get xs => SpacingSystem.xs;
  static double get sm => SpacingSystem.sm;
  static double get md => SpacingSystem.md;
  static double get lg => SpacingSystem.lg;
  static double get xl => SpacingSystem.xl;
  static double get xxl => SpacingSystem.xxl;
  static double get xxxl => SpacingSystem.xxxl;

  // 动画
  static Duration get quick => AnimationSystem.quick;
  static Duration get normal => AnimationSystem.normal;
  static Duration get slow => AnimationSystem.slow;

  // 排版
  static TextStyle get displayLarge => TypographySystem.displayLarge();
  static TextStyle get headingLarge => TypographySystem.headingLarge();
  static TextStyle get bodyLarge => TypographySystem.bodyLarge();
  static TextStyle get labelLarge => TypographySystem.labelLarge();
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
  static Map<String, dynamic> get status {
    return {
      'initialized': _initialized,
      'themeMode': ThemeManager().mode.name,
      'brandPreset': ThemeManager().brandPreset.name,
      'highContrast': ThemeManager().highContrast,
      'version': '2.0.0',
    };
  }
}
