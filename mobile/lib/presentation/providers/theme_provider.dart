import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider to manage the application's ThemeMode (Light, Dark, System)
final themeModeProvider = StateProvider<ThemeMode>((ref) {
  // TODO: Load from SharedPreferences
  return ThemeMode.system;
});
