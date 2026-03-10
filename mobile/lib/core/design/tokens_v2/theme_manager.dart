import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 主题管理器 - 支持动态切换和持久化
/// 支持商城皮肤系统
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

  // 🆕 商城皮肤支持
  String? _equippedSkinId; // 装备的皮肤ID（如 "skin_galaxy_nova_001"）
  String? get equippedSkinId => _equippedSkinId;
  Map<String, dynamic>? _skinConfig; // 皮肤配置（{theme, colors}）
  Map<String, dynamic>? get skinConfig => _skinConfig;

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

    _mode = AppThemeMode
        .values[prefs.getInt('theme_mode') ?? AppThemeMode.system.index];
    _brandPreset = BrandPreset
        .values[prefs.getInt('brand_preset') ?? BrandPreset.sparkle.index];
    _highContrast = prefs.getBool('high_contrast') ?? false;

    // 🆕 加载商城皮肤配置
    _equippedSkinId = prefs.getString('equipped_skin_id');
    final skinConfigJson = prefs.getString('skin_config');
    if (skinConfigJson != null) {
      try {
        _skinConfig = Map<String, dynamic>.from(
          // 简单的JSON解析（实际项目中应该用dart:convert）
          _parseSimpleJson(skinConfigJson),
        );
      } catch (e) {
        // 解析失败，忽略皮肤配置
        _equippedSkinId = null;
      }
    }

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
    final newMode =
        _mode == AppThemeMode.dark ? AppThemeMode.light : AppThemeMode.dark;
    await setAppThemeMode(newMode);
  }

  /// 重置为默认
  Future<void> reset() async {
    _mode = AppThemeMode.system;
    _brandPreset = BrandPreset.sparkle;
    _highContrast = false;
    _equippedSkinId = null;
    _skinConfig = null;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 🆕 装备商城皮肤
  ///
  /// [skinId] - 皮肤ID（如 "skin_galaxy_nova_001"）
  /// [skinConfig] - 皮肤配置，格式：{theme: "nova", colors: ["#FF6B6B", "#4ECDC4"]}
  Future<void> equipShopSkin(
    String skinId,
    Map<String, dynamic> skinConfig,
  ) async {
    _equippedSkinId = skinId;
    _skinConfig = skinConfig;
    await _saveToPrefs();
    notifyListeners();
  }

  /// 🆕 卸载当前皮肤
  Future<void> unequipSkin() async {
    _equippedSkinId = null;
    _skinConfig = null;
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
        brightness =
            WidgetsBinding.instance.platformDispatcher.platformBrightness;
    }

    final baseTheme = brightness == Brightness.light
        ? SparkleThemeData.light(highContrast: _highContrast)
        : SparkleThemeData.dark(highContrast: _highContrast);

    // 🆕 优先应用商城皮肤（如果装备了皮肤）
    if (_equippedSkinId != null && _skinConfig != null) {
      return _applyShopSkin(baseTheme);
    }

    return _applyBrandPreset(baseTheme);
  }

  /// 🆕 应用商城皮肤配置
  ///
  /// 皮肤配置格式：{theme: "nova", colors: ["#FF6B6B", "#4ECDC4"]}
  SparkleThemeData _applyShopSkin(SparkleThemeData base) {
    if (_skinConfig == null) return base;

    final colors = _skinConfig!['colors'] as List?;
    if (colors == null || colors.length < 2) return base;

    // 解析颜色
    final primaryColor = _parseColor(colors[0]);
    final secondaryColor = _parseColor(colors[1]);

    if (primaryColor == null) return base;

    // 应用皮肤颜色
    final newColors = base.colors.copyWith(
      brandPrimary: primaryColor,
      brandSecondary: secondaryColor ?? primaryColor,
    );

    final shadows = newColors.brightness == Brightness.light
        ? SparkleShadows.light()
        : SparkleShadows.dark();

    return base.copyWith(colors: newColors, shadows: shadows);
  }

  /// 解析颜色字符串（支持 #RGB, #RRGGBB, #RRGGBBAA 格式）
  Color? _parseColor(dynamic colorString) {
    if (colorString == null) return null;
    if (colorString is Color) return colorString;
    if (colorString is! String) return null;

    final hex = colorString.replaceAll('#', '');
    if (hex.length == 6) {
      return Color(int.parse('FF$hex', radix: 16));
    } else if (hex.length == 8) {
      return Color(int.parse(hex, radix: 16));
    } else if (hex.length == 3) {
      // #RGB 格式
      final r = hex[0];
      final g = hex[1];
      final b = hex[2];
      return Color(int.parse('FF$r$r$g$g$b$b', radix: 16));
    }
    return null;
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
        ? SparkleShadows.light()
        : SparkleShadows.dark();

    return base.copyWith(colors: colors, shadows: shadows);
  }

  /// 保存到持久化存储
  Future<void> _saveToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('theme_mode', _mode.index);
    await prefs.setInt('brand_preset', _brandPreset.index);
    await prefs.setBool('high_contrast', _highContrast);

    // 🆕 保存商城皮肤配置
    if (_equippedSkinId != null) {
      await prefs.setString('equipped_skin_id', _equippedSkinId!);
      await prefs.setString('skin_config', _stringifySimpleJson(_skinConfig));
    } else {
      await prefs.remove('equipped_skin_id');
      await prefs.remove('skin_config');
    }
  }

  /// 简单的JSON字符串解析（用于皮肤配置）
  Map<String, dynamic> _parseSimpleJson(String jsonStr) {
    // 简化版解析，实际应该用 dart:convert
    final result = <String, dynamic>{};
    final cleanStr = jsonStr.replaceAll('{', '').replaceAll('}', '').trim();
    if (cleanStr.isEmpty) return result;

    final pairs = cleanStr.split(',');
    for (final pair in pairs) {
      final parts = pair.split(':');
      if (parts.length == 2) {
        final key = parts[0].trim().replaceAll('"', '').replaceAll("'", '');
        final value = parts[1].trim();
        if (value.startsWith('[') && value.endsWith(']')) {
          // 数组
          final arrayStr = value.substring(1, value.length - 1);
          result[key] = arrayStr.isEmpty
              ? <String>[]
              : arrayStr
                  .split(',')
                  .map((e) => e.trim().replaceAll('"', '').replaceAll("'", ''))
                  .toList();
        } else {
          result[key] = value.replaceAll('"', '').replaceAll("'", '');
        }
      }
    }
    return result;
  }

  /// 简单的JSON字符串化（用于皮肤配置）
  String _stringifySimpleJson(Map<String, dynamic>? map) {
    if (map == null) return '{}';
    final buffer = StringBuffer()..write('{');
    var first = true;
    map.forEach((key, value) {
      if (!first) buffer.write(', ');
      first = false;
      buffer.write('"$key": ');
      if (value is List) {
        buffer.write('[${value.map((e) => '"$e"').join(', ')}]');
      } else if (value is String) {
        buffer.write('"$value"');
      } else {
        buffer.write('$value');
      }
    });
    buffer.write('}');
    return buffer.toString();
  }

  @override
  // ignore: must_call_super
  void dispose() {
    // Prevent disposal of the singleton instance by Riverpod or other owners.
    // This instance is meant to live for the entire application lifecycle.
    // Calling super.dispose() would mark it as disposed and prevent future use.
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
      shadows: SparkleShadows.light(),
    );
  }

  factory SparkleThemeData.dark({bool highContrast = false}) {
    final colors = SparkleColors.dark(highContrast: highContrast);
    return SparkleThemeData(
      colors: colors,
      typography: SparkleTypography.standard(),
      spacing: const SparkleSpacing(),
      animations: const SparkleAnimations(),
      shadows: SparkleShadows.dark(),
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
  }) =>
      SparkleThemeData(
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
    required this.surfaceAmbient,
    required this.rimLight,
    required this.glowPrimary,
    required this.noiseColor,
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
    // Chat bubble colors
    required this.chatBubbleUser,
    required this.chatBubbleUserText,
    required this.chatBubbleOther,
    required this.chatBubbleOtherText,
    // Galaxy colors
    required this.galaxyBackground,
    required this.galaxyShadow,
  });

  factory SparkleColors.light({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        brandPrimary: Color(0xFF7A5430),
        brandSecondary: Color(0xFF516079),
        semanticSuccess: Color(0xFF006400),
        semanticWarning: Color(0xFF8B4500),
        semanticError: Color(0xFF8B0000),
        semanticInfo: Color(0xFF00008B),
        surfacePrimary: Color(0xFFF4F1EA),
        surfaceSecondary: Color(0xFFE8E1D7),
        surfaceTertiary: Color(0xFFD8CFC3),
        surfaceAmbient: Color(0xFFF8F5EE),
        rimLight: Color(0xFFFFFFFF),
        glowPrimary: Color(0x00000000),
        noiseColor: Color(0x00000000),
        textPrimary: Color(0xFF171717),
        textSecondary: Color(0xFF171717),
        textDisabled: Color(0xFF666666),
        brightness: Brightness.light,
        taskLearning: Color(0xFF687A96),
        taskTraining: Color(0xFFB2844A),
        taskErrorFix: Color(0xFFB85F52),
        taskReflection: Color(0xFF7B6E8D),
        taskSocial: Color(0xFF5F8672),
        taskPlanning: Color(0xFF50737D),
        planSprint: Color(0xFF9D5B4F),
        planGrowth: Color(0xFF5D7B63),
        statusOnline: Color(0xFF2ECC71),
        statusOffline: Color(0xFF95A5A6),
        statusInvisible: Color(0xFF34495E),
        neutral200: Color(0xFFF0ECE4),
        neutral300: Color(0xFFD8D0C5),
        neutral400: Color(0xFFB1A89C),
        neutral500: Color(0xFF857B6D),
        neutral600: Color(0xFF5A5148),
        // Chat bubble colors
        chatBubbleUser: Color(0xFF4F637D),
        chatBubbleUserText: Colors.white,
        chatBubbleOther: Color(0xFFEAE4DA),
        chatBubbleOtherText: Color(0xFF171717),
        // Galaxy colors
        galaxyBackground: Color(0xFFECE8E0),
        galaxyShadow: Color(0xFFD9D0C2),
      );
    }
    return const SparkleColors(
      brandPrimary: Color(0xFFA77D63),
      brandSecondary: Color(0xFF7589A8),
      semanticSuccess: Color(0xFF7E9C87),
      semanticWarning: Color(0xFFC59A67),
      semanticError: Color(0xFFC17A70),
      semanticInfo: Color(0xFF7893B2),
      surfacePrimary: Color(0xFFF8F4EF),
      surfaceSecondary: Color(0xFFF1EBE4),
      surfaceTertiary: Color(0xFFE7DED4),
      surfaceAmbient: Color(0xFFFCF8F3),
      rimLight: Color(0x99FFFFFF), // white 0.6
      glowPrimary: Color(0x24A77D63),
      noiseColor: Color(0x0D000000), // black 0.05
      textPrimary: Color(0xFF171717),
      textSecondary: Color(0xFF6C655D),
      textDisabled: Color(0xFFA49B90),
      brightness: Brightness.light,
      taskLearning: Color(0xFF7893B2),
      taskTraining: Color(0xFFC59A67),
      taskErrorFix: Color(0xFFC17A70),
      taskReflection: Color(0xFF9A88B7),
      taskSocial: Color(0xFF769083),
      taskPlanning: Color(0xFF6A8790),
      planSprint: Color(0xFFB3756B),
      planGrowth: Color(0xFF73907A),
      statusOnline: Color(0xFF2ECC71),
      statusOffline: Color(0xFF95A5A6),
      statusInvisible: Color(0xFF34495E),
      neutral200: Color(0xFFF4EFE9),
      neutral300: Color(0xFFDED5CB),
      neutral400: Color(0xFFBBB0A4),
      neutral500: Color(0xFF958A80),
      neutral600: Color(0xFF6A6057),
      // Chat bubble colors
      chatBubbleUser: Color(0xFF6C84A4),
      chatBubbleUserText: Colors.white,
      chatBubbleOther: Color(0xFFF5F0E8),
      chatBubbleOtherText: Color(0xFF171717),
      // Galaxy colors
      galaxyBackground: Color(0xFFECE7DE),
      galaxyShadow: Color(0xFFD7CDBC),
    );
  }

  factory SparkleColors.dark({bool highContrast = false}) {
    if (highContrast) {
      return const SparkleColors(
        brandPrimary: Color(0xFFE0B172),
        brandSecondary: Color(0xFF95A6C8),
        semanticSuccess: Color(0xFF00FF00),
        semanticWarning: Color(0xFFFFFF00),
        semanticError: Color(0xFFFF0000),
        semanticInfo: Color(0xFF00FFFF),
        // High contrast dark: deeper blacks with subtle elevation hints
        surfacePrimary: Color(0xFF0E1013),
        surfaceSecondary: Color(0xFF171A1F),
        surfaceTertiary: Color(0xFF23272E),
        surfaceAmbient: Color(0xFF090B0E),
        rimLight: Color(0xFFFFFFFF),
        glowPrimary: Color(0x00000000),
        noiseColor: Color(0x00000000),
        textPrimary: Color(0xFFFFFFFF),
        textSecondary: Color(0xFFFFFFFF),
        textDisabled: Color(0xFF999999),
        brightness: Brightness.dark,
        taskLearning: Color(0xFF95A6C8),
        taskTraining: Color(0xFFE0B172),
        taskErrorFix: Color(0xFFD37B72),
        taskReflection: Color(0xFFA696C0),
        taskSocial: Color(0xFF83A18C),
        taskPlanning: Color(0xFF7B9AA3),
        planSprint: Color(0xFFD37B72),
        planGrowth: Color(0xFF83A18C),
        statusOnline: Color(0xFF2ECC71),
        statusOffline: Color(0xFF95A5A6),
        statusInvisible: Color(0xFF34495E),
        neutral200: Color(0xFF2B3038),
        neutral300: Color(0xFF404650),
        neutral400: Color(0xFF626A77),
        neutral500: Color(0xFF848D99),
        neutral600: Color(0xFFB2BCCB),
        // Chat bubble colors
        chatBubbleUser: Color(0xFF65789A),
        chatBubbleUserText: Colors.white,
        chatBubbleOther: Color(0xFF23272D),
        chatBubbleOtherText: Color(0xFFF5F5F5),
        // Galaxy colors
        galaxyBackground: Color(0xFF0A0E14),
        galaxyShadow: Color(0xFF05070B),
      );
    }
    return const SparkleColors(
      brandPrimary: Color(0xFFC97A43),
      brandSecondary: Color(0xFF7E8FAE),
      semanticSuccess: Color(0xFF7A9A83),
      semanticWarning: Color(0xFFD2A56D),
      semanticError: Color(0xFFD37B72),
      semanticInfo: Color(0xFF8CA5C8),
      // Dark mode surface hierarchy (Material 3 elevation system)
      surfacePrimary: Color(0xFF0F1217),
      surfaceSecondary: Color(0xFF171B22),
      surfaceTertiary: Color(0xFF222831),
      surfaceAmbient: Color(0xFF0B0E12),
      rimLight: Color(0x33FFFFFF), // white 0.2
      glowPrimary: Color(0x42C97A43),
      noiseColor: Color(0x08FFFFFF), // white 0.03
      textPrimary: Color(0xFFF4F1EB),
      textSecondary: Color(0xFFB8B1A6),
      textDisabled: Color(0xFF6B737E),
      brightness: Brightness.dark,
      taskLearning: Color(0xFF8CA5C8),
      taskTraining: Color(0xFFD2A56D),
      taskErrorFix: Color(0xFFD37B72),
      taskReflection: Color(0xFFA08AB8),
      taskSocial: Color(0xFF7A9A83),
      taskPlanning: Color(0xFF7E9AA1),
      planSprint: Color(0xFFCE817A),
      planGrowth: Color(0xFF7A9980),
      statusOnline: Color(0xFF2ECC71),
      statusOffline: Color(0xFF95A5A6),
      statusInvisible: Color(0xFF34495E),
      neutral200: Color(0xFF2B313A),
      neutral300: Color(0xFF3D4550),
      neutral400: Color(0xFF5E6874),
      neutral500: Color(0xFF808996),
      neutral600: Color(0xFFADB7C8),
      // Chat bubble colors
      chatBubbleUser: Color(0xFF657A96),
      chatBubbleUserText: Colors.white,
      chatBubbleOther: Color(0xFF20262D),
      chatBubbleOtherText: Color(0xFFF4F1EB),
      // Galaxy colors
      galaxyBackground: Color(0xFF070B12),
      galaxyShadow: Color(0xFF04070C),
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
  final Color surfaceAmbient;

  final Color rimLight;
  final Color glowPrimary;
  final Color noiseColor;

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

  // Chat bubble colors
  final Color chatBubbleUser;
  final Color chatBubbleUserText;
  final Color chatBubbleOther;
  final Color chatBubbleOtherText;

  // Galaxy colors
  final Color galaxyBackground;
  final Color galaxyShadow;

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
    Color? surfaceAmbient,
    Color? rimLight,
    Color? glowPrimary,
    Color? noiseColor,
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
    Color? chatBubbleUser,
    Color? chatBubbleUserText,
    Color? chatBubbleOther,
    Color? chatBubbleOtherText,
    Color? galaxyBackground,
    Color? galaxyShadow,
  }) =>
      SparkleColors(
        brandPrimary: brandPrimary ?? this.brandPrimary,
        brandSecondary: brandSecondary ?? this.brandSecondary,
        semanticSuccess: semanticSuccess ?? this.semanticSuccess,
        semanticWarning: semanticWarning ?? this.semanticWarning,
        semanticError: semanticError ?? this.semanticError,
        semanticInfo: semanticInfo ?? this.semanticInfo,
        surfacePrimary: surfacePrimary ?? this.surfacePrimary,
        surfaceSecondary: surfaceSecondary ?? this.surfaceSecondary,
        surfaceTertiary: surfaceTertiary ?? this.surfaceTertiary,
        surfaceAmbient: surfaceAmbient ?? this.surfaceAmbient,
        rimLight: rimLight ?? this.rimLight,
        glowPrimary: glowPrimary ?? this.glowPrimary,
        noiseColor: noiseColor ?? this.noiseColor,
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
        chatBubbleUser: chatBubbleUser ?? this.chatBubbleUser,
        chatBubbleUserText: chatBubbleUserText ?? this.chatBubbleUserText,
        chatBubbleOther: chatBubbleOther ?? this.chatBubbleOther,
        chatBubbleOtherText: chatBubbleOtherText ?? this.chatBubbleOtherText,
        galaxyBackground: galaxyBackground ?? this.galaxyBackground,
        galaxyShadow: galaxyShadow ?? this.galaxyShadow,
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
        displayLarge: TextStyle(
          fontSize: 46.0,
          fontWeight: FontWeight.w700,
          height: 1.08,
          letterSpacing: -0.8,
        ),
        headingLarge: TextStyle(
          fontSize: 30.0,
          fontWeight: FontWeight.w700,
          height: 1.12,
          letterSpacing: -0.4,
        ),
        headingMedium: TextStyle(
          fontSize: 24.0,
          fontWeight: FontWeight.w600,
          height: 1.18,
          letterSpacing: -0.2,
        ),
        titleLarge: TextStyle(
          fontSize: 19.0,
          fontWeight: FontWeight.w600,
          height: 1.32,
          letterSpacing: -0.1,
        ),
        bodyLarge: TextStyle(
          fontSize: 16.0,
          fontWeight: FontWeight.w400,
          height: 1.58,
          letterSpacing: 0.1,
        ),
        bodyMedium: TextStyle(
          fontSize: 14.0,
          fontWeight: FontWeight.w400,
          height: 1.52,
          letterSpacing: 0.1,
        ),
        labelLarge: TextStyle(
          fontSize: 14.0,
          fontWeight: FontWeight.w500,
          height: 1.18,
          letterSpacing: 0.12,
        ),
        labelSmall: TextStyle(
          fontSize: 12.0,
          fontWeight: FontWeight.w500,
          height: 1.16,
          letterSpacing: 0.18,
        ),
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
  final Duration quick = const Duration(milliseconds: 120);
  final Duration normal = const Duration(milliseconds: 180);
  final Duration slow = const Duration(milliseconds: 260);
}

/// 阴影系统
@immutable
class SparkleShadows {
  const SparkleShadows({
    required this.small,
    required this.medium,
    required this.large,
  });

  factory SparkleShadows.light() => const SparkleShadows(
        small: [
          BoxShadow(
            color: Color(0x12000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
          BoxShadow(
            color: Color(0x18000000),
            blurRadius: 18,
            offset: Offset(0, 8),
          ),
        ],
        medium: [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
          BoxShadow(
            color: Color(0x1A000000),
            blurRadius: 24,
            offset: Offset(0, 10),
          ),
        ],
        large: [
          BoxShadow(
            color: Color(0x16000000),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
          BoxShadow(
            color: Color(0x20000000),
            blurRadius: 32,
            offset: Offset(0, 14),
          ),
        ],
      );

  factory SparkleShadows.dark() => const SparkleShadows(
        small: [
          BoxShadow(
            color: Color(0x66000000),
            blurRadius: 14,
            offset: Offset(0, 5),
          ),
        ],
        medium: [
          BoxShadow(
            color: Color(0x73000000),
            blurRadius: 20,
            offset: Offset(0, 10),
          ),
        ],
        large: [
          BoxShadow(
            color: Color(0x8A000000),
            blurRadius: 34,
            offset: Offset(0, 18),
          ),
        ],
      );
  final List<BoxShadow> small;
  final List<BoxShadow> medium;
  final List<BoxShadow> large;
}
