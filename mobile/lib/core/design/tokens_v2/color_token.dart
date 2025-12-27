import 'package:flutter/material.dart';

/// 颜色令牌 - 支持语义化和动态变体
@immutable
class ColorToken {
  final String name;
  final int value;

  const ColorToken(this.name, this.value);

  /// 获取Color对象
  Color get color => Color(value);

  /// 创建透明度变体
  ColorToken withOpacity(double opacity) {
    return ColorToken('$name.opacity$opacity', (value & 0x00FFFFFF) | ((opacity * 255).toInt() << 24));
  }

  /// 深色模式变体
  ColorTokenVariant variant({
    required Color dark,
    required Color highContrast,
  }) {
    return ColorTokenVariant(
      light: color,
      dark: dark,
      highContrast: highContrast,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ColorToken && runtimeType == other.runtimeType && value == other.value;

  @override
  int get hashCode => value.hashCode;

  @override
  String toString() => 'ColorToken($name, ${value.toRadixString(16).padLeft(8, '0')})';
}

/// 颜色变体 - 支持多模式
@immutable
class ColorTokenVariant {
  final Color light;
  final Color dark;
  final Color highContrast;

  const ColorTokenVariant({
    required this.light,
    required this.dark,
    required this.highContrast,
  });

  Color resolve(Brightness brightness, {bool highContrast = false}) {
    if (highContrast) return this.highContrast;
    return brightness == Brightness.light ? light : dark;
  }

  ColorTokenVariant copyWith({
    Color? light,
    Color? dark,
    Color? highContrast,
  }) {
    return ColorTokenVariant(
      light: light ?? this.light,
      dark: dark ?? this.dark,
      highContrast: highContrast ?? this.highContrast,
    );
  }
}

/// 颜色组 - 用于品牌系统
@immutable
class ColorGroup {
  final ColorToken primary;
  final ColorToken? light;
  final ColorToken? dark;
  final ColorToken? contrast;

  const ColorGroup({
    required this.primary,
    this.light,
    this.dark,
    this.contrast,
  });

  ColorToken get base => primary;
  ColorToken get lighter => light ?? primary;
  ColorToken get darker => dark ?? primary;
  ColorToken get onColor => contrast ?? primary;
}
