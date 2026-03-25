# Sparkle 设计系统架构 2.0

## 🎯 设计愿景

构建一个**面向未来、可扩展、类型安全**的设计系统，支持：
- 🚀 **多平台适配**：Mobile、Tablet、Desktop、Web
- 🎨 **动态主题**：实时主题切换、品牌定制、无障碍增强
- ⚡ **性能优先**：编译期优化、零运行时开销
- 🔧 **开发体验**：类型推导、自动补全、可视化工具
- 🌍 **国际化**：RTL支持、本地化适配

---

## 🏗️ 架构演进：从 Tokens 1.0 到 2.0

### 当前状态 (Tokens 1.0)
```
AppDesignTokens (静态类)
├── 静态常量 (const)
├── 简单的getter方法
└── 手动维护的枚举
```

**问题：**
- ❌ 无法动态切换主题
- ❌ 缺少类型安全的设计变体
- ❌ 没有响应式断点系统
- ❌ 手动维护，容易出错
- ❌ 无法进行设计验证

### 目标架构 (Tokens 2.0)
```
DesignSystem (核心)
├── DesignTokens (配置驱动)
├── ThemeManager (状态管理)
├── ResponsiveSystem (响应式)
├── ComponentLibrary (原子组件)
└── ValidationEngine (验证)
```

---

## 📐 核心架构设计

### 1. 设计令牌系统 (DesignTokens)

#### 1.1 语义化颜色系统
```dart
// 新的语义化颜色架构
class SparkleDesignTokens {
  // 品牌色 - 核心识别
  static const brandPrimary = ColorToken('brand.primary', 0xFFFF6B35);
  static const brandSecondary = ColorToken('brand.secondary', 0xFF1A237E);

  // 语义色 - 功能含义
  static const semanticSuccess = ColorToken('semantic.success', 0xFF4CAF50);
  static const semanticWarning = ColorToken('semantic.warning', 0xFFFFA726);
  static const semanticError = ColorToken('semantic.error', 0xFFF44336);
  static const semanticInfo = ColorToken('semantic.info', 0xFF2196F3);

  // 表面色 - UI层级
  static const surfacePrimary = ColorToken('surface.primary', 0xFFFFFFFF);
  static const surfaceSecondary = ColorToken('surface.secondary', 0xFFF5F5F5);
  static const surfaceTertiary = ColorToken('surface.tertiary', 0xFFE0E0E0);

  // 文本色 - 可读性
  static const textPrimary = ColorToken('text.primary', 0xFF212121);
  static const textSecondary = ColorToken('text.secondary', 0xFF757575);
  static const textDisabled = ColorToken('text.disabled', 0xFFBDBDBD);

  // 透明度变体
  static final overlay10 = brandPrimary.withOpacity(0.1);
  static final overlay20 = brandPrimary.withOpacity(0.2);
}
```

#### 1.2 动态颜色变体系统
```dart
/// 颜色变体 - 支持深色模式和高对比度
class ColorVariant {
  final Color light;
  final Color dark;
  final Color highContrast;

  const ColorVariant({
    required this.light,
    required this.dark,
    required this.highContrast,
  });

  Color resolve(Brightness brightness, {bool highContrast = false}) {
    if (highContrast) return this.highContrast;
    return brightness == Brightness.light ? light : dark;
  }
}

// 使用示例
class SparkleColorsV2 {
  static const primary = ColorVariant(
    light: Color(0xFFFF6B35),
    dark: Color(0xFFFF8C5A),
    highContrast: Color(0xFFE55A24),
  );
}
```

#### 1.3 间距系统 (8pt网格 + 比例系统)
```dart
class SpacingSystem {
  // 基础网格 (8pt)
  static const double grid = 8.0;

  // 比例系统 (基于黄金比例 1.618)
  static const double xs   = grid * 0.5;   // 4pt
  static const double sm   = grid * 1;     // 8pt
  static const double md   = grid * 1.5;   // 12pt
  static const double lg   = grid * 2;     // 16pt
  static const double xl   = grid * 3;     // 24pt
  static const double xxl  = grid * 4;     // 32pt
  static const double xxxl = grid * 6;     // 48pt

  // 响应式间距 (自动缩放)
  static double responsive(BuildContext context, double base) {
    final width = MediaQuery.of(context).size.width;
    if (width > 1200) return base * 1.5;
    if (width < 480) return base * 0.75;
    return base;
  }
}
```

#### 1.4 排版系统 (Type Scale + 可变字体)
```dart
class TypographySystem {
  // 类型比例 (Modular Scale: 1.25)
  static const double scaleRatio = 1.25;

  // 基础字体大小 (16px)
  static const double baseSize = 16.0;

  // 标准化文本样式
  static final Map<TextStyleKey, TextStyle> styles = {
    TextStyleKey.displayLarge: TextStyle(
      fontSize: baseSize * pow(scaleRatio, 4), // 39.06px
      fontWeight: FontWeight.w800,
      height: 1.2,
      letterSpacing: -0.02,
    ),
    TextStyleKey.headingLarge: TextStyle(
      fontSize: baseSize * pow(scaleRatio, 3), // 31.25px
      fontWeight: FontWeight.w700,
      height: 1.3,
      letterSpacing: -0.01,
    ),
    TextStyleKey.bodyLarge: TextStyle(
      fontSize: baseSize * pow(scaleRatio, 1), // 20px
      fontWeight: FontWeight.w400,
      height: 1.5,
      letterSpacing: 0,
    ),
    TextStyleKey.bodyMedium: TextStyle(
      fontSize: baseSize, // 16px
      fontWeight: FontWeight.w400,
      height: 1.5,
      letterSpacing: 0,
    ),
    TextStyleKey.labelSmall: TextStyle(
      fontSize: baseSize * pow(scaleRatio, -1), // 12.8px
      fontWeight: FontWeight.w500,
      height: 1.3,
      letterSpacing: 0.01,
    ),
  };
}

enum TextStyleKey {
  displayLarge,
  displayMedium,
  displaySmall,
  headingLarge,
  headingMedium,
  headingSmall,
  titleLarge,
  titleMedium,
  titleSmall,
  bodyLarge,
  bodyMedium,
  bodySmall,
  labelLarge,
  labelMedium,
  labelSmall,
}
```

#### 1.5 动画系统 (物理模拟 + 语义化)
```dart
class AnimationSystem {
  // 物理模拟曲线
  static const Curve spring = Curves.elasticOut;
  static const Curve bounce = Curves.bounceOut;
  static const Curve smooth = Curves.easeInOutCubic;

  // 语义化时长
  static const Duration instant = Duration(milliseconds: 0);
  static const Duration quick = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 250);
  static const Duration slow = Duration(milliseconds: 400);
  static const Duration deliberate = Duration(milliseconds: 600);

  // 组合动画配置
  static const Map<AnimationPurpose, AnimationConfig> configs = {
    AnimationPurpose.buttonTap: AnimationConfig(
      duration: Duration(milliseconds: 100),
      curve: Curves.easeOut,
      scale: 0.95,
    ),
    AnimationPurpose.pageTransition: AnimationConfig(
      duration: Duration(milliseconds: 350),
      curve: Curves.easeInOutCubic,
      offset: Offset(0.1, 0),
    ),
    AnimationPurpose.loading: AnimationConfig(
      duration: Duration(milliseconds: 1000),
      curve: Curves.linear,
      rotation: 2 * math.pi,
    ),
  };
}

enum AnimationPurpose {
  buttonTap,
  pageTransition,
  loading,
  feedback,
  expand,
}

class AnimationConfig {
  final Duration duration;
  final Curve curve;
  final double? scale;
  final Offset? offset;
  final double? rotation;

  const AnimationConfig({
    required this.duration,
    required this.curve,
    this.scale,
    this.offset,
    this.rotation,
  });
}
```

---

### 2. 主题管理系统 (ThemeManager)

#### 2.1 动态主题引擎
```dart
/// 主题管理器 - 支持运行时切换
class ThemeManager extends ChangeNotifier {
  static final ThemeManager _instance = ThemeManager._internal();
  factory ThemeManager() => _instance;
  ThemeManager._internal();

  ThemeMode _mode = ThemeMode.system;
  ThemeMode get mode => _mode;

  // 当前主题数据
  SparkleThemeData _currentTheme = SparkleThemeData.light();
  SparkleThemeData get current => _currentTheme;

  // 品牌定制
  BrandPreset _brandPreset = BrandPreset.sparkle;
  BrandPreset get brandPreset => _brandPreset;

  // 高对比度模式
  bool _highContrast = false;
  bool get highContrast => _highContrast;

  // 切换主题模式
  Future<void> setThemeMode(ThemeMode mode) async {
    _mode = mode;
    _currentTheme = await _loadThemeForMode(mode);
    notifyListeners();

    // 持久化
    await _saveToPrefs();
  }

  // 切换品牌预设
  Future<void> setBrandPreset(BrandPreset preset) async {
    _brandPreset = preset;
    _currentTheme = SparkleThemeData.fromPreset(preset);
    notifyListeners();
    await _saveToPrefs();
  }

  // 切换高对比度
  Future<void> toggleHighContrast(bool enabled) async {
    _highContrast = enabled;
    _currentTheme = _currentTheme.copyWith(
      colors: _currentTheme.colors.toHighContrast(enabled),
    );
    notifyListeners();
    await _saveToPrefs();
  }

  // 加载保存的主题
  Future<void> loadSavedTheme() async {
    final prefs = await SharedPreferences.getInstance();
    final modeIndex = prefs.getInt('theme_mode') ?? ThemeMode.system.index;
    final brandIndex = prefs.getInt('brand_preset') ?? BrandPreset.sparkle.index;
    final highContrast = prefs.getBool('high_contrast') ?? false;

    await setThemeMode(ThemeMode.values[modeIndex]);
    await setBrandPreset(BrandPreset.values[brandIndex]);
    await toggleHighContrast(highContrast);
  }

  Future<void> _saveToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('theme_mode', _mode.index);
    await prefs.setInt('brand_preset', _brandPreset.index);
    await prefs.setBool('high_contrast', _highContrast);
  }

  Future<SparkleThemeData> _loadThemeForMode(ThemeMode mode) async {
    switch (mode) {
      case ThemeMode.light:
        return SparkleThemeData.light(highContrast: _highContrast);
      case ThemeMode.dark:
        return SparkleThemeData.dark(highContrast: _highContrast);
      case ThemeMode.system:
        final brightness = WidgetsBinding.instance.platformDispatcher.platformBrightness;
        return brightness == Brightness.light
          ? SparkleThemeData.light(highContrast: _highContrast)
          : SparkleThemeData.dark(highContrast: _highContrast);
    }
  }
}

/// 主题数据容器
class SparkleThemeData {
  final SparkleColors colors;
  final SparkleTypography typography;
  final SparkleSpacing spacing;
  final SparkleAnimations animations;
  final SparkleShadows shadows;

  const SparkleThemeData({
    required this.colors,
    required this.typography,
    required this.spacing,
    required this.animations,
    required this.shadows,
  });

  factory SparkleThemeData.light({bool highContrast = false}) {
    return SparkleThemeData(
      colors: SparkleColors.light(highContrast: highContrast),
      typography: SparkleTypography.standard(),
      spacing: SpacingSystem(),
      animations: SparkleAnimations.standard(),
      shadows: SparkleShadows.light(),
    );
  }

  factory SparkleThemeData.dark({bool highContrast = false}) {
    return SparkleThemeData(
      colors: SparkleColors.dark(highContrast: highContrast),
      typography: SparkleTypography.standard(),
      spacing: SpacingSystem(),
      animations: SparkleAnimations.standard(),
      shadows: SparkleShadows.dark(),
    );
  }

  factory SparkleThemeData.fromPreset(BrandPreset preset) {
    // 支持不同品牌预设
    switch (preset) {
      case BrandPreset.sparkle:
        return SparkleThemeData.light();
      case BrandPreset.ocean:
        return SparkleThemeData.ocean();
      case BrandPreset.forest:
        return SparkleThemeData.forest();
    }
  }

  SparkleThemeData copyWith({
    SparkleColors? colors,
    SparkleTypography? typography,
    SparkleSpacing? spacing,
    SparkleAnimations? animations,
    SparkleShadows? shadows,
  }) {
    return SparkleThemeData(
      colors: colors ?? this.colors,
      typography: typography ?? this.typography,
      spacing: spacing ?? this.spacing,
      animations: animations ?? this.animations,
      shadows: shadows ?? this.shadows,
    );
  }
}

enum ThemeMode { system, light, dark }
enum BrandPreset { sparkle, ocean, forest }
```

#### 2.2 主题上下文提供者
```dart
/// 主题提供者 - Riverpod集成
@riverpod
class ThemeProvider extends _$ThemeProvider {
  @override
  SparkleThemeData build() {
    // 监听系统主题变化
    final platformBrightness = MediaQuery.of(ref.watch(appContextProvider)).platformBrightness;

    // 加载用户偏好
    final prefs = ref.watch(userPreferencesProvider);

    return _resolveTheme(prefs.themeMode, platformBrightness);
  }

  SparkleThemeData _resolveTheme(ThemeMode mode, Brightness systemBrightness) {
    // 实现主题解析逻辑
    // ...
  }

  // 切换主题
  Future<void> toggleTheme() async {
    final current = state;
    final newMode = current.colors.brightness == Brightness.light
      ? ThemeMode.dark
      : ThemeMode.light;

    state = await _loadThemeForMode(newMode);
    await _saveThemeMode(newMode);
  }

  // 应用品牌预设
  Future<void> applyBrandPreset(BrandPreset preset) async {
    state = SparkleThemeData.fromPreset(preset);
    await _saveBrandPreset(preset);
  }
}

/// 便捷的上下文扩展
extension ThemeContext on BuildContext {
  SparkleThemeData get theme => ThemeProvider.of(this);
  SparkleColors get colors => theme.colors;
  SparkleTypography get typography => theme.typography;
  SparkleSpacing get spacing => theme.spacing;
  SparkleAnimations get animations => theme.animations;

  bool get isDarkMode => Theme.of(this).brightness == Brightness.dark;
  bool get isLightMode => !isDarkMode;

  // 响应式断点
  LayoutType get layoutType => getLayoutType(this);
  bool get isMobile => layoutType == LayoutType.mobile;
  bool get isTablet => layoutType == LayoutType.tablet;
  bool get isDesktop => layoutType == LayoutType.desktop;
}
```

---

### 3. 响应式系统 (ResponsiveSystem)

#### 3.1 高级响应式断点
```dart
/// 响应式断点系统
class ResponsiveBreakpoints {
  static const Map<DeviceCategory, Breakpoint> values = {
    DeviceCategory.watch: Breakpoint(min: 0, max: 240, density: Density.compact),
    DeviceCategory.phone: Breakpoint(min: 241, max: 480, density: Density.compact),
    DeviceCategory.phablet: Breakpoint(min: 481, max: 768, density: Density.normal),
    DeviceCategory.tablet: Breakpoint(min: 769, max: 1024, density: Density.comfortable),
    DeviceCategory.desktop: Breakpoint(min: 1025, max: 1440, density: Density.expanded),
    DeviceCategory.tv: Breakpoint(min: 1441, max: double.infinity, density: Density.large),
  };

  static DeviceCategory categorize(double width) {
    return values.entries
        .firstWhere((entry) => width >= entry.value.min && width <= entry.value.max)
        .key;
  }

  static Density getDensity(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final category = categorize(width);
    return values[category]!.density;
  }
}

class Breakpoint {
  final double min;
  final double max;
  final Density density;

  const Breakpoint({
    required this.min,
    required this.max,
    required this.density,
  });
}

enum DeviceCategory { watch, phone, phablet, tablet, desktop, tv }
enum Density { compact, normal, comfortable, expanded, large }

/// 响应式值解析器
class ResponsiveValue<T> {
  final T mobile;
  final T? tablet;
  final T? desktop;
  final T? wide;

  const ResponsiveValue({
    required this.mobile,
    this.tablet,
    this.desktop,
    this.wide,
  });

  T resolve(BuildContext context) {
    final width = MediaQuery.of(context).size.width;

    if (width >= 1440 && wide != null) return wide!;
    if (width >= 1024 && desktop != null) return desktop!;
    if (width >= 768 && tablet != null) return tablet!;
    return mobile;
  }
}

// 使用示例
final padding = ResponsiveValue(
  mobile: EdgeInsets.all(16),
  tablet: EdgeInsets.all(24),
  desktop: EdgeInsets.all(32),
  wide: EdgeInsets.all(48),
);

final fontSize = ResponsiveValue(
  mobile: 14.0,
  tablet: 16.0,
  desktop: 18.0,
);
```

#### 3.2 自适应布局组件
```dart
/// 自适应Scaffold - 智能导航
class AdaptiveScaffold extends StatelessWidget {
  final Widget body;
  final List<NavigationItem> items;
  final int currentIndex;
  final ValueChanged<int> onSelected;
  final Widget? floatingActionButton;
  final PreferredSizeWidget? appBar;

  const AdaptiveScaffold({
    required this.body,
    required this.items,
    required this.currentIndex,
    required this.onSelected,
    this.floatingActionButton,
    this.appBar,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final category = ResponsiveBreakpoints.categorize(
      MediaQuery.of(context).size.width,
    );

    switch (category) {
      case DeviceCategory.watch:
        return _buildWatchLayout(context);
      case DeviceCategory.phone:
      case DeviceCategory.phablet:
        return _buildPhoneLayout(context);
      case DeviceCategory.tablet:
        return _buildTabletLayout(context);
      case DeviceCategory.desktop:
      case DeviceCategory.tv:
        return _buildDesktopLayout(context);
    }
  }

  Widget _buildPhoneLayout(BuildContext context) {
    return Scaffold(
      appBar: appBar,
      body: body,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: onSelected,
        destinations: items.map((item) => item.toNavDestination()).toList(),
      ),
      floatingActionButton: floatingActionButton,
    );
  }

  Widget _buildTabletLayout(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: currentIndex,
            onDestinationSelected: onSelected,
            labelType: NavigationRailLabelType.all,
            destinations: items.map((item) => item.toRailDestination()).toList(),
          ),
          const VerticalDivider(width: 1),
          Expanded(child: Scaffold(appBar: appBar, body: body)),
        ],
      ),
    );
  }

  Widget _buildDesktopLayout(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          SizedBox(
            width: 280,
            child: NavigationDrawer(
              selectedIndex: currentIndex,
              onDestinationSelected: onSelected,
              children: [
                _buildDrawerHeader(context),
                const Divider(),
                ...items.map((item) => item.toDrawerDestination()).toList(),
              ],
            ),
          ),
          const VerticalDivider(width: 1),
          Expanded(
            child: Scaffold(
              appBar: appBar,
              body: body,
              floatingActionButton: floatingActionButton,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWatchLayout(BuildContext context) {
    // 极简布局，适合小屏幕
    return Scaffold(
      body: body,
      floatingActionButton: floatingActionButton,
    );
  }

  Widget _buildDrawerHeader(BuildContext context) {
    return Padding(
      padding: EdgeInsets.all(context.spacing.lg),
      child: Row(
        children: [
          Icon(Icons.local_fire_department,
            color: context.colors.brandPrimary,
            size: 32,
          ),
          SizedBox(width: context.spacing.md),
          Text(
            'Sparkle',
            style: context.typography.headingLarge,
          ),
        ],
      ),
    );
  }
}

class NavigationItem {
  final String label;
  final Widget icon;
  final Widget? selectedIcon;
  final Widget? trailing;

  const NavigationItem({
    required this.label,
    required this.icon,
    this.selectedIcon,
    this.trailing,
  });

  NavigationDestination toNavDestination() {
    return NavigationDestination(
      icon: icon,
      selectedIcon: selectedIcon ?? icon,
      label: label,
    );
  }

  NavigationRailDestination toRailDestination() {
    return NavigationRailDestination(
      icon: icon,
      selectedIcon: selectedIcon ?? icon,
      label: Text(label),
    );
  }

  NavigationDrawerDestination toDrawerDestination() {
    return NavigationDrawerDestination(
      icon: icon,
      selectedIcon: selectedIcon ?? icon,
      label: Text(label),
    );
  }
}
```

---

### 4. 组件库架构 (Component Library)

#### 4.1 原子化设计系统
```
components/
├── atoms/              # 原子组件 (不可再分)
│   ├── buttons/
│   │   ├── sparkle_button.dart
│   │   ├── sparkle_icon_button.dart
│   │   └── sparkle_text_button.dart
│   ├── inputs/
│   │   ├── sparkle_text_field.dart
│   │   ├── sparkle_search_bar.dart
│   │   └── sparkle_dropdown.dart
│   ├── display/
│   │   ├── sparkle_card.dart
│   │   ├── sparkle_badge.dart
│   │   └── sparkle_divider.dart
│   └── feedback/
│       ├── sparkle_toast.dart
│       ├── sparkle_dialog.dart
│       └── sparkle_progress.dart
│
├── molecules/          # 分子组件 (原子组合)
│   ├── form/
│   │   ├── sparkle_form_field.dart
│   │   └── sparkle_form_group.dart
│   ├── list/
│   │   ├── sparkle_list_tile.dart
│   │   └── sparkle_expandable_tile.dart
│   └── navigation/
│       ├── sparkle_tab_bar.dart
│       └── sparkle_bottom_sheet.dart
│
├── organisms/          # 有机体 (复杂功能)
│   ├── cards/
│   │   ├── sparkle_task_card.dart
│   │   ├── sparkle_insight_card.dart
│   │   └── sparkle_stat_card.dart
│   ├── forms/
│   │   ├── sparkle_login_form.dart
│   │   └── sparkle_settings_form.dart
│   └── lists/
│       ├── sparkle_feed_list.dart
│       └── sparkle_calendar_grid.dart
│
└── templates/          # 模板 (页面布局)
    ├── dashboard_template.dart
    ├── detail_template.dart
    └── wizard_template.dart
```

#### 4.2 组件设计模式
```dart
/// 统一的组件接口
abstract class SparkleComponent<T extends StatefulWidget> extends State<T> {
  /// 组件验证
  void validate() {
    // 子类实现验证逻辑
  }

  /// 组件可访问性检查
  AccessibilityInfo getAccessibilityInfo() {
    return AccessibilityInfo(
      label: '',
      hint: '',
      isFocusable: true,
    );
  }

  /// 性能指标
  PerformanceMetrics getPerformanceMetrics() {
    return PerformanceMetrics(
      buildTime: Duration.zero,
      complexity: Complexity.low,
    );
  }
}

/// 按钮组件示例
class SparkleButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final ButtonSize size;
  final Widget? icon;
  final bool loading;
  final bool disabled;

  const SparkleButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = ButtonVariant.primary,
    this.size = ButtonSize.medium,
    this.icon,
    this.loading = false,
    this.disabled = false,
  });

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final spacing = context.spacing;
    final animations = context.animations;

    return AnimatedContainer(
      duration: animations.configs[AnimationPurpose.buttonTap]!.duration,
      curve: animations.configs[AnimationPurpose.buttonTap]!.curve,
      child: Material(
        color: _getBackgroundColor(colors),
        borderRadius: BorderRadius.circular(spacing.sm),
        child: InkWell(
          onTap: disabled || loading ? null : onPressed,
          borderRadius: BorderRadius.circular(spacing.sm),
          child: Container(
            padding: _getPadding(spacing),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (loading) ...[
                  SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation(_getTextColor(colors)),
                    ),
                  ),
                  SizedBox(width: spacing.sm),
                ] else if (icon != null) ...[
                  IconTheme(
                    data: IconThemeData(color: _getTextColor(colors), size: 20),
                    child: icon!,
                  ),
                  SizedBox(width: spacing.sm),
                ],
                Text(
                  label,
                  style: _getTextStyle(context),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _getBackgroundColor(SparkleColors colors) {
    if (disabled) return colors.surfaceTertiary;
    switch (variant) {
      case ButtonVariant.primary:
        return colors.brandPrimary;
      case ButtonVariant.secondary:
        return colors.brandSecondary;
      case ButtonVariant.outline:
        return Colors.transparent;
      case ButtonVariant.ghost:
        return colors.surfacePrimary.withOpacity(0.1);
    }
  }

  Color _getTextColor(SparkleColors colors) {
    if (disabled) return colors.textDisabled;
    switch (variant) {
      case ButtonVariant.primary:
      case ButtonVariant.secondary:
        return colors.textOnPrimary;
      case ButtonVariant.outline:
      case ButtonVariant.ghost:
        return colors.brandPrimary;
    }
  }

  EdgeInsets _getPadding(SpacingSystem spacing) {
    switch (size) {
      case ButtonSize.small:
        return EdgeInsets.symmetric(horizontal: spacing.md, vertical: spacing.xs);
      case ButtonSize.medium:
        return EdgeInsets.symmetric(horizontal: spacing.lg, vertical: spacing.sm);
      case ButtonSize.large:
        return EdgeInsets.symmetric(horizontal: spacing.xl, vertical: spacing.md);
    }
  }

  TextStyle _getTextStyle(BuildContext context) {
    final base = context.typography.labelLarge;
    return base.copyWith(
      color: _getTextColor(context.colors),
      fontWeight: size == ButtonSize.large ? FontWeight.w600 : FontWeight.w500,
    );
  }
}

enum ButtonVariant { primary, secondary, outline, ghost }
enum ButtonSize { small, medium, large }

/// 组件变体系统
extension ButtonVariants on SparkleButton {
  static SparkleButton primary({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
    bool loading = false,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.primary,
      icon: icon,
      loading: loading,
    );
  }

  static SparkleButton outline({
    required String label,
    required VoidCallback onPressed,
    Widget? icon,
  }) {
    return SparkleButton(
      label: label,
      onPressed: onPressed,
      variant: ButtonVariant.outline,
      icon: icon,
    );
  }
}
```

---

### 5. 验证与测试系统

#### 5.1 设计令牌验证
```dart
/// 设计系统验证器
class DesignValidator {
  /// 验证颜色对比度 (WCAG 2.1)
  static bool validateContrast(Color foreground, Color background, {Level level = Level.AA}) {
    final ratio = _calculateContrastRatio(foreground, background);
    switch (level) {
      case Level.AA:
        return ratio >= 4.5;
      case Level.AAA:
        return ratio >= 7.0;
      case Level.AA_Large:
        return ratio >= 3.0;
    }
  }

  /// 验证间距倍数
  static bool validateSpacing(double value) {
    return value % 4 == 0; // 必须是4的倍数
  }

  /// 验证字体大小
  static bool validateFontSize(double size) {
    return size >= 12 && size <= 72; // 合理范围
  }

  /// 验证动画时长
  static bool validateAnimationDuration(Duration duration) {
    return duration.inMilliseconds >= 50 && duration.inMilliseconds <= 1000;
  }

  static double _calculateContrastRatio(Color c1, Color c2) {
    final l1 = _relativeLuminance(c1);
    final l2 = _relativeLuminance(c2);
    final lighter = math.max(l1, l2);
    final darker = math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  static double _relativeLuminance(Color color) {
    final r = _srgbToLinear(color.red / 255);
    final g = _srgbToLinear(color.green / 255);
    final b = _srgbToLinear(color.blue / 255);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  static double _srgbToLinear(double value) {
    return value <= 0.03928
      ? value / 12.92
      : math.pow((value + 0.055) / 1.055, 2.4).toDouble();
  }
}

enum Level { AA, AAA, AA_Large }

/// 组件一致性检查
class ComponentValidator {
  /// 检查是否使用了设计令牌
  static List<String> validateWidgetUsage(Widget widget) {
    final violations = <String>[];
    // 通过反射或代码分析检查硬编码值
    // ...
    return violations;
  }

  /// 生成设计系统报告
  static Future<DesignReport> generateReport() async {
    return DesignReport(
      timestamp: DateTime.now(),
      violations: await _scanForViolations(),
      metrics: await _collectMetrics(),
      recommendations: _generateRecommendations(),
    );
  }

  static Future<List<Violation>> _scanForViolations() async {
    // 扫描代码库中的硬编码值
    return [];
  }

  static Future<Metrics> _collectMetrics() async {
    return Metrics(
      componentCoverage: 0.0,
      tokenUsage: 0.0,
      accessibilityScore: 0.0,
    );
  }

  static List<String> _generateRecommendations() {
    return [
      '使用 AppDesignTokens 替代硬编码颜色',
      '确保所有交互元素 ≥ 48x48px',
      '使用响应式间距系统',
    ];
  }
}

class DesignReport {
  final DateTime timestamp;
  final List<Violation> violations;
  final Metrics metrics;
  final List<String> recommendations;

  const DesignReport({
    required this.timestamp,
    required this.violations,
    required this.metrics,
    required this.recommendations,
  });

  bool get isValid => violations.isEmpty;

  String toMarkdown() {
    return '''
# 设计系统验证报告
生成时间: ${timestamp.toIso8601String()}

## 指标
- 组件覆盖率: ${(metrics.componentCoverage * 100).toStringAsFixed(1)}%
- 令牌使用率: ${(metrics.tokenUsage * 100).toStringAsFixed(1)}%
- 无障碍评分: ${(metrics.accessibilityScore * 100).toStringAsFixed(1)}%

## 违规项 (${violations.length})
${violations.map((v) => '- ${v.description}').join('\n')}

## 建议
${recommendations.map((r) => '- $r').join('\n')}
''';
  }
}

class Violation {
  final String file;
  final int line;
  final String description;
  final Severity severity;

  const Violation({
    required this.file,
    required this.line,
    required this.description,
    required this.severity,
  });
}

enum Severity { low, medium, high, critical }

class Metrics {
  final double componentCoverage;
  final double tokenUsage;
  final double accessibilityScore;

  const Metrics({
    required this.componentCoverage,
    required this.tokenUsage,
    required this.accessibilityScore,
  });
}
```

#### 5.2 自动化测试
```dart
/// 设计系统测试套件
void main() {
  group('Design Tokens', () {
    test('所有颜色都符合WCAG对比度标准', () {
      final colors = [
        (AppDesignTokens.primaryBase, Colors.white),
        (AppDesignTokens.textPrimary, AppDesignTokens.surfacePrimary),
        // ...
      ];

      for (final (fg, bg) in colors) {
        expect(
          DesignValidator.validateContrast(fg, bg, level: Level.AA),
          isTrue,
          reason: '颜色组合 ${fg.value} / ${bg.value} 不符合对比度标准',
        );
      }
    });

    test('所有间距都是4的倍数', () {
      final spacings = [
        AppDesignTokens.spacing4,
        AppDesignTokens.spacing8,
        AppDesignTokens.spacing16,
        // ...
      ];

      for (final spacing in spacings) {
        expect(
          DesignValidator.validateSpacing(spacing),
          isTrue,
          reason: '间距 $spacing 不是4的倍数',
        );
      }
    });

    test('字体大小在合理范围内', () {
      final sizes = [
        AppDesignTokens.fontSizeXs,
        AppDesignTokens.fontSizeBase,
        AppDesignTokens.fontSize6xl,
        // ...
      ];

      for (final size in sizes) {
        expect(
          DesignValidator.validateFontSize(size),
          isTrue,
          reason: '字体大小 $size 超出合理范围',
        );
      }
    });
  });

  group('Component Consistency', () {
    test('所有按钮使用统一的SparkleButton', () async {
      final report = await ComponentValidator.generateReport();
      expect(report.violations.where((v) => v.description.contains('Button')), isEmpty);
    });

    test('所有卡片使用设计令牌', () async {
      final report = await ComponentValidator.generateReport();
      expect(report.violations.where((v) => v.description.contains('Card')), isEmpty);
    });
  });

  group('Accessibility', () {
    test('所有交互元素满足最小触控目标', () {
      // 通过Widget测试验证
      tester.pumpWidget(SparkleButton(label: 'Test', onPressed: () {}));
      final size = tester.getSize(find.byType(SparkleButton));
      expect(size.width, greaterThanOrEqualTo(48));
      expect(size.height, greaterThanOrEqualTo(48));
    });
  });
}
```

---

## 📊 实施路线图

### Phase 1: 核心重构 (Week 1-2)
- [ ] 迁移现有 `AppDesignTokens` 到新架构
- [ ] 实现 `ThemeManager` 和动态主题
- [ ] 建立语义化颜色系统
- [ ] 创建基础原子组件

### Phase 2: 响应式系统 (Week 3-4)
- [ ] 实现高级断点系统
- [ ] 重构 `ResponsiveScaffold` 为 `AdaptiveScaffold`
- [ ] 添加响应式值解析器
- [ ] 优化平板和桌面布局

### Phase 3: 组件库 (Week 5-6)
- [ ] 创建原子组件库 (Atoms)
- [ ] 构建分子组件 (Molecules)
- [ ] 实现复杂有机体 (Organisms)
- [ ] 建立组件文档和示例

### Phase 4: 验证与工具 (Week 7-8)
- [ ] 实现设计验证器
- [ ] 创建自动化测试套件
- [ ] 开发设计系统可视化工具
- [ ] 建立CI/CD集成

---

## 🎯 预期收益

### 开发效率
- ⚡ **+40%** 组件开发速度
- 🐛 **-60%** UI相关bug
- 📚 **+80%** 代码可维护性

### 用户体验
- 🎨 **100%** 设计一致性
- ♿ **WCAG 2.1 AAA** 级无障碍
- 📱 **全平台** 优秀体验

### 团队协作
- 📖 **统一** 设计语言
- 🔧 **自动化** 质量检查
- 🚀 **快速** 新功能迭代

---

## 🔗 相关文档

- [设计令牌规范](./design-tokens-spec.md)
- [组件开发指南](./component-guide.md)
- [无障碍标准](./accessibility-guide.md)
- [性能优化手册](./performance-guide.md)
