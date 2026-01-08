import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';

/// Provider for theme manager singleton - observing changes
final themeManagerProvider = ChangeNotifierProvider<ThemeManager>((ref) => ThemeManager());

/// Provider to access the current ThemeMode directly
final themeModeProvider = Provider<ThemeMode>((ref) {
  final manager = ref.watch(themeManagerProvider);
  return appThemeModeToThemeMode(manager.mode);
});

/// Provider to access the current AppThemeMode
final appThemeModeProvider = Provider<AppThemeMode>((ref) => ref.watch(themeManagerProvider).mode);

/// Provider to manage brand preset
final brandPresetProvider = Provider<BrandPreset>((ref) => ref.watch(themeManagerProvider).brandPreset);

/// Provider to manage high contrast mode
final highContrastProvider = Provider<bool>((ref) => ref.watch(themeManagerProvider).highContrast);

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

