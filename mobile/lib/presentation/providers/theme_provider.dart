import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// Provider for theme manager singleton
final themeManagerProvider = Provider((ref) => ThemeManager());

/// Provider to manage the application's ThemeMode (Light, Dark, System)
final themeModeProvider = StateProvider<AppThemeMode>((ref) => ThemeManager().mode);

/// Provider to manage brand preset
final brandPresetProvider = StateProvider<BrandPreset>((ref) => ThemeManager().brandPreset);

/// Provider to manage high contrast mode
final highContrastProvider = StateProvider<bool>((ref) => ThemeManager().highContrast);

/// Helper to convert AppThemeMode to ThemeMode
ThemeMode appThemeModeToThemeMode(AppThemeMode mode) {
  switch (mode) {
    case AppThemeMode.light:
      return ThemeMode.light;
    case AppThemeMode.dark:
      return ThemeMode.dark;
    case AppThemeMode.system:
      return ThemeMode.system;
  }
}

/// Helper to convert ThemeMode to AppThemeMode
AppThemeMode themeModeToAppThemeMode(ThemeMode mode) {
  switch (mode) {
    case ThemeMode.light:
      return AppThemeMode.light;
    case ThemeMode.dark:
      return AppThemeMode.dark;
    case ThemeMode.system:
      return AppThemeMode.system;
  }
}
