import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Key for storing 'Enter to Send' preference in SharedPreferences
const String kEnterToSendKey = 'settings_enter_to_send';
const String kTransparentModeKey = 'settings_transparent_mode';
const String kOnboardingCompletedKey = 'settings_onboarding_completed';
const String kSystemUpdateLevelKey = 'settings_system_update_level';

/// Provider to manage the 'Enter to Send' preference
final enterToSendProvider = StateNotifierProvider<EnterToSendNotifier, bool>(
    (ref) => EnterToSendNotifier(),);

final transparentModeProvider =
    StateNotifierProvider<TransparentModeNotifier, bool>(
        (ref) => TransparentModeNotifier(),);

final onboardingCompletedProvider =
    StateNotifierProvider<OnboardingCompletedNotifier, bool>(
        (ref) => OnboardingCompletedNotifier(),);

final systemUpdateLevelProvider =
    StateNotifierProvider<SystemUpdateLevelNotifier, int>(
        (ref) => SystemUpdateLevelNotifier(),);

class EnterToSendNotifier extends StateNotifier<bool> {
  EnterToSendNotifier() : super(false) {
    _loadSettings();
  }

  /// Load saved setting from SharedPreferences
  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(kEnterToSendKey);
      if (enabled != null) {
        state = enabled;
      }
    } catch (_) {
      // Default to false
      state = false;
    }
  }

  /// Update and persist the setting
  Future<void> setEnabled(bool enabled) async {
    if (state == enabled) return;

    state = enabled;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(kEnterToSendKey, enabled);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  /// Toggle the setting
  void toggle() {
    setEnabled(!state);
  }
}

class TransparentModeNotifier extends StateNotifier<bool> {
  TransparentModeNotifier() : super(false) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(kTransparentModeKey);
      if (enabled != null) {
        state = enabled;
      }
    } catch (_) {
      state = false;
    }
  }

  Future<void> setEnabled(bool enabled) async {
    if (state == enabled) return;

    state = enabled;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(kTransparentModeKey, enabled);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  void toggle() {
    setEnabled(!state);
  }
}

class OnboardingCompletedNotifier extends StateNotifier<bool> {
  OnboardingCompletedNotifier() : super(false) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final enabled = prefs.getBool(kOnboardingCompletedKey);
      if (enabled != null) {
        state = enabled;
      }
    } catch (_) {
      state = false;
    }
  }

  Future<void> setCompleted(bool value) async {
    if (state == value) return;
    state = value;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(kOnboardingCompletedKey, value);
    } catch (_) {
      // Silent fail for persistence
    }
  }
}

class SystemUpdateLevelNotifier extends StateNotifier<int> {
  SystemUpdateLevelNotifier() : super(2) {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final value = prefs.getInt(kSystemUpdateLevelKey);
      if (value != null) {
        state = value;
      }
    } catch (_) {
      state = 2;
    }
  }

  Future<void> setLevel(int level) async {
    if (state == level) return;
    state = level;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(kSystemUpdateLevelKey, level);
    } catch (_) {
      // Silent fail
    }
  }
}
