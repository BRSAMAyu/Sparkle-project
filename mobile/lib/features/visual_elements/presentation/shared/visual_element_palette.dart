import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

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
