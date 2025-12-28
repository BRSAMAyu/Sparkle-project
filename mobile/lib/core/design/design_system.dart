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

// 便捷导入
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

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
    final theme = ThemeManager().current;
    return _buildThemeData(theme, Brightness.light);
  }

  static ThemeData get darkTheme {
    final theme = ThemeManager().current;
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

  // 缓存 ThemeManager 实例以提升性能
  static SparkleThemeData get _theme => ThemeManager().current;

  // ==================== 静态常量定义 (定义时严谨) ====================

  // 颜色常量 (使用硬编码值，确保const兼容性)
  static const Color brandPrimaryConst = Color(0xFFFF6B35);
  static const Color brandSecondaryConst = Color(0xFF1A237E);
  static const Color successConst = Color(0xFF4CAF50);
  static const Color warningConst = Color(0xFFFF9800);
  static const Color errorConst = Color(0xFFF44336);
  static const Color infoConst = Color(0xFF2196F3);

  // 透明度变体常量
  static const Color brandPrimary10Const = Color(0x1AFF6B35);
  static const Color brandPrimary12Const = Color(0x1FFF6B35);
  static const Color brandPrimary24Const = Color(0x3DFF6B35);
  static const Color brandPrimary26Const = Color(0x42FF6B35);
  static const Color brandPrimary30Const = Color(0x4DFF6B35);
  static const Color brandPrimary38Const = Color(0x61FF6B35);
  static const Color brandPrimary45Const = Color(0x73FF6B35);
  static const Color brandPrimary54Const = Color(0x8AFF6B35);
  static const Color brandPrimary70Const = Color(0xB3FF6B35);
  static const Color brandPrimary87Const = Color(0xDEFF6B35);

  // 间距常量
  static const double xsConst = 4.0;
  static const double smConst = 8.0;
  static const double mdConst = 12.0;
  static const double lgConst = 16.0;
  static const double xlConst = 20.0;
  static const double xxlConst = 24.0;
  static const double xxxlConst = 32.0;

  // 圆角常量
  static const double radiusSmConst = 4.0;
  static const double radiusMdConst = 8.0;
  static const double radiusLgConst = 12.0;
  static const double radiusXlConst = 16.0;
  static const double radiusFullConst = 9999.0;

  // ==================== 动态getter (运行时主题切换) ====================

  // 颜色
  static Color get brandPrimary => _theme.colors.brandPrimary;
  static Color get brandSecondary => _theme.colors.brandSecondary;
  static Color get success => _theme.colors.semanticSuccess;
  static Color get warning => _theme.colors.semanticWarning;
  static Color get error => _theme.colors.semanticError;
  static Color get info => _theme.colors.semanticInfo;

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
