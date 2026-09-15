import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// Visual element color palette for themed display elements.
///
/// NOTE: This palette uses hardcoded colors rather than DS tokens because
/// visual elements require specific color characteristics (glow, shimmer)
/// that may not map 1:1 to standard design tokens. Future work should
/// consider adding visual-element-specific tokens to SparkleColors when
/// the design system is next updated.

class VisualElementPalette {
  const VisualElementPalette._();

  static const Color moonless = Color(0xFF050A12);
  static const Color inkBlue = Color(0xFF071523);
  static const Color surface = Color(0xFF0B1D2C);
  static const Color panel = Color(0xFF10283A);
  static const Color blueWash = Color(0xFF14384A);
  static const Color cyan = Color(0xFF8FB8C8);
  static const Color gold = Color(0xFFD9B66F);
  static const Color textPrimary = Color(0xFFEAF3F5);
  static const Color textSecondary = Color(0xFF9CB4BD);
  static const Color hairline = Color(0x334F7D8F);

  static VisualElementPaletteData of(BuildContext context) =>
      forBrightness(Theme.of(context).brightness);

  static VisualElementPaletteData forBrightness(Brightness brightness) =>
      brightness == Brightness.dark
          ? const VisualElementPaletteData.dark()
          : const VisualElementPaletteData.light();

  static VisualElementRarityColors rarityColors(
    VisualElementRarity rarity,
  ) {
    switch (rarity) {
      case VisualElementRarity.common:
        return const VisualElementRarityColors(
          background: Color(0xFF102436),
          border: Color(0xFF668696),
          text: Color(0xFFC6D6DB),
        );
      case VisualElementRarity.rare:
        return const VisualElementRarityColors(
          background: Color(0xFF0C2A37),
          border: Color(0xFF58C0D7),
          text: Color(0xFFC6F2F7),
        );
      case VisualElementRarity.epic:
        return const VisualElementRarityColors(
          background: Color(0xFF17253A),
          border: Color(0xFF91A9FF),
          text: Color(0xFFDCE5FF),
        );
      case VisualElementRarity.legendary:
        return const VisualElementRarityColors(
          background: Color(0xFF312813),
          border: Color(0xFFD9B66F),
          text: Color(0xFFFFE7A8),
        );
    }
  }
}

class VisualElementPaletteData {
  const VisualElementPaletteData({
    required this.moonless,
    required this.inkBlue,
    required this.surface,
    required this.panel,
    required this.blueWash,
    required this.cyan,
    required this.gold,
    required this.textPrimary,
    required this.textSecondary,
    required this.hairline,
    required this.isDark,
  });

  const VisualElementPaletteData.dark()
      : this(
          moonless: VisualElementPalette.moonless,
          inkBlue: VisualElementPalette.inkBlue,
          surface: VisualElementPalette.surface,
          panel: VisualElementPalette.panel,
          blueWash: VisualElementPalette.blueWash,
          cyan: VisualElementPalette.cyan,
          gold: VisualElementPalette.gold,
          textPrimary: VisualElementPalette.textPrimary,
          textSecondary: VisualElementPalette.textSecondary,
          hairline: VisualElementPalette.hairline,
          isDark: true,
        );

  const VisualElementPaletteData.light()
      : this(
          moonless: const Color(0xFFF7FAFC),
          inkBlue: const Color(0xFFEFF6F8),
          surface: const Color(0xFFFFFFFF),
          panel: const Color(0xFFE6F0F4),
          blueWash: const Color(0xFFD5E7ED),
          cyan: const Color(0xFF287A91),
          gold: const Color(0xFF8B681F),
          textPrimary: const Color(0xFF17252D),
          textSecondary: const Color(0xFF526B75),
          hairline: const Color(0x334B6F7A),
          isDark: false,
        );

  final Color moonless;
  final Color inkBlue;
  final Color surface;
  final Color panel;
  final Color blueWash;
  final Color cyan;
  final Color gold;
  final Color textPrimary;
  final Color textSecondary;
  final Color hairline;
  final bool isDark;

  LinearGradient get pageHeaderGradient => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors:
            isDark ? [moonless, inkBlue, surface] : [moonless, inkBlue, panel],
      );

  LinearGradient get panelGradient => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: isDark ? [panel, surface, blueWash] : [surface, inkBlue, panel],
      );

  Color elevatedTint(Color accent, [double amount = 0.16]) =>
      Color.lerp(surface, accent, amount) ?? surface;

  VisualElementRarityColors rarityColors(VisualElementRarity rarity) {
    if (isDark) {
      return VisualElementPalette.rarityColors(rarity);
    }

    switch (rarity) {
      case VisualElementRarity.common:
        return const VisualElementRarityColors(
          background: Color(0xFFE9F0F3),
          border: Color(0xFF5F7D89),
          text: Color(0xFF2F4750),
        );
      case VisualElementRarity.rare:
        return const VisualElementRarityColors(
          background: Color(0xFFE0F5F8),
          border: Color(0xFF15839B),
          text: Color(0xFF0D5263),
        );
      case VisualElementRarity.epic:
        return const VisualElementRarityColors(
          background: Color(0xFFE9ECFF),
          border: Color(0xFF566ED6),
          text: Color(0xFF34479B),
        );
      case VisualElementRarity.legendary:
        return const VisualElementRarityColors(
          background: Color(0xFFFFF3D5),
          border: Color(0xFF967023),
          text: Color(0xFF62460F),
        );
    }
  }
}

class VisualElementRarityColors {
  const VisualElementRarityColors({
    required this.background,
    required this.border,
    required this.text,
  });

  final Color background;
  final Color border;
  final Color text;
}
