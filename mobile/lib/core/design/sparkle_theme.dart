import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

class SparkleTheme {
  // 核心调色板 - 融合星空与火焰
  static const Color primary = Color(0xFF6750A4); // 深紫 (星空)
  static const Color secondary = Color(0xFFE67E22); // 橙色 (火苗)
  static const Color tertiary = Color(0xFFF1C40F); // 金色 (能量)
  static const Color background = Color(0xFFF8F9FA);
  static const Color surface = DS.brandPrimary;
  static const Color error = Color(0xFFB00020);
  
  // 在线状态颜色
  static const Color online = Color(0xFF2ECC71);
  static const Color offline = Color(0xFF95A5A6);
  static const Color invisible = Color(0xFF34495E);

  // 动效配置
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration medium = Duration(milliseconds: 400);
  static const Curve curve = Curves.easeInOutCubic;

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        secondary: secondary,
        tertiary: tertiary,
        surface: background,
      ),
      scaffoldBackgroundColor: background,
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: -0.5),
        titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        bodyMedium: TextStyle(fontSize: 14, height: 1.5),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        color: surface, // Material 3 uses color for CardTheme
      ),
    );
  }
}