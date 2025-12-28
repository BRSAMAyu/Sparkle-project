import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// Provider for theme manager singleton (listens to updates).
final themeManagerProvider = ChangeNotifierProvider<ThemeManager>((ref) {
  return ThemeManager();
});

/// Provider to expose the application's theme mode.
final themeModeProvider = Provider<AppThemeMode>((ref) {
  return ref.watch(themeManagerProvider).mode;
});

/// Provider to expose brand preset.
final brandPresetProvider = Provider<BrandPreset>((ref) {
  return ref.watch(themeManagerProvider).brandPreset;
});

/// Provider to expose high contrast mode.
final highContrastProvider = Provider<bool>((ref) {
  return ref.watch(themeManagerProvider).highContrast;
});

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
