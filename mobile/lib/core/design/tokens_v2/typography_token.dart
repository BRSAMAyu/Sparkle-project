import 'package:flutter/material.dart';

/// 排版系统 - 基于模块化比例 (1.25)
@immutable
class TypographySystem {
  const TypographySystem._();

  // 模块化比例
  static const double ratio = 1.25;
  static const double baseSize = 16.0;

  // 字体大小比例 (基于16px基础)
  static const double sizeXs   = baseSize / ratio;        // ~12.8px
  static const double sizeSm   = baseSize;                // 16px
  static const double sizeMd   = baseSize * ratio;        // ~20px
  static const double sizeLg   = baseSize * ratio * ratio; // ~25px
  static const double sizeXl   = baseSize * ratio * ratio * ratio; // ~31.25px
  static const double size2xl  = baseSize * ratio * ratio * ratio * ratio; // ~39px
  static const double size3xl  = baseSize * ratio * ratio * ratio * ratio * ratio; // ~48.8px

  // 字重
  static const FontWeight weightLight = FontWeight.w300;
  static const FontWeight weightRegular = FontWeight.w400;
  static const FontWeight weightMedium = FontWeight.w500;
  static const FontWeight weightSemibold = FontWeight.w600;
  static const FontWeight weightBold = FontWeight.w700;
  static const FontWeight weightExtrabold = FontWeight.w800;

  // 行高
  static const double leadingTight = 1.2;
  static const double leadingNormal = 1.5;
  static const double leadingRelaxed = 1.75;

  // 字符间距
  static const double trackingTight = -0.02;
  static const double trackingNormal = 0.0;
  static const double trackingWide = 0.02;

  /// 标准文本样式
  static TextStyle displayLarge() => const TextStyle(
    fontSize: size3xl,
    fontWeight: weightExtrabold,
    height: leadingTight,
    letterSpacing: trackingTight,
  );

  static TextStyle headingLarge() => const TextStyle(
    fontSize: size2xl,
    fontWeight: weightBold,
    height: leadingTight,
    letterSpacing: trackingTight,
  );

  static TextStyle headingMedium() => const TextStyle(
    fontSize: sizeXl,
    fontWeight: weightSemibold,
    height: leadingTight,
    letterSpacing: trackingNormal,
  );

  static TextStyle titleLarge() => const TextStyle(
    fontSize: sizeLg,
    fontWeight: weightSemibold,
    height: leadingNormal,
    letterSpacing: trackingNormal,
  );

  static TextStyle bodyLarge() => const TextStyle(
    fontSize: sizeMd,
    fontWeight: weightRegular,
    height: leadingNormal,
    letterSpacing: trackingNormal,
  );

  static TextStyle bodyMedium() => const TextStyle(
    fontSize: sizeSm,
    fontWeight: weightRegular,
    height: leadingNormal,
    letterSpacing: trackingNormal,
  );

  static TextStyle labelLarge() => const TextStyle(
    fontSize: sizeSm,
    fontWeight: weightMedium,
    height: leadingTight,
    letterSpacing: trackingWide,
  );

  static TextStyle labelSmall() => const TextStyle(
    fontSize: sizeXs,
    fontWeight: weightMedium,
    height: leadingTight,
    letterSpacing: trackingWide,
  );
}

/// 排版令牌 - 语义化样式
@immutable
class TypographyToken {
  final String name;
  final TextStyle style;

  const TypographyToken(this.name, this.style);

  /// 应用颜色
  TypographyToken withColor(Color color) {
    return TypographyToken(
      name,
      style.copyWith(color: color),
    );
  }

  /// 应用字重
  TypographyToken withWeight(FontWeight weight) {
    return TypographyToken(
      name,
      style.copyWith(fontWeight: weight),
    );
  }

  /// 应用字号
  TypographyToken withSize(double size) {
    return TypographyToken(
      name,
      style.copyWith(fontSize: size),
    );
  }

  /// 响应式变体
  TypographyTokenVariant variant({
    required TextStyle tablet,
    required TextStyle desktop,
  }) {
    return TypographyTokenVariant(
      mobile: style,
      tablet: tablet,
      desktop: desktop,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TypographyToken && runtimeType == other.runtimeType && style == other.style;

  @override
  int get hashCode => style.hashCode;
}

/// 响应式排版变体
@immutable
class TypographyTokenVariant {
  final TextStyle mobile;
  final TextStyle tablet;
  final TextStyle desktop;

  const TypographyTokenVariant({
    required this.mobile,
    required this.tablet,
    required this.desktop,
  });

  TextStyle resolve(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    if (width >= 1024) return desktop;
    if (width >= 768) return tablet;
    return mobile;
  }
}

/// 文本样式键 - 用于主题系统
enum TextKey {
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

/// 排版主题扩展
extension TypographyThemeExtension on ThemeData {
  Map<TextKey, TextStyle> get sparkleTypography => {
    TextKey.displayLarge: TypographySystem.displayLarge().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.headingLarge: TypographySystem.headingLarge().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.headingMedium: TypographySystem.headingMedium().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.titleLarge: TypographySystem.titleLarge().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.bodyLarge: TypographySystem.bodyLarge().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.bodyMedium: TypographySystem.bodyMedium().copyWith(
      color: colorScheme.onSurface,
    ),
    TextKey.labelLarge: TypographySystem.labelLarge().copyWith(
      color: colorScheme.primary,
    ),
    TextKey.labelSmall: TypographySystem.labelSmall().copyWith(
      color: colorScheme.onSurface.withOpacity(0.7),
    ),
  };
}
