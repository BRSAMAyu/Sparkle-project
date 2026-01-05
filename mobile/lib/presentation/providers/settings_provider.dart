import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Key for storing 'Enter to Send' preference in SharedPreferences
const String kEnterToSendKey = 'settings_enter_to_send';

/// Provider to manage the 'Enter to Send' preference
final enterToSendProvider = StateNotifierProvider<EnterToSendNotifier, bool>(
    (ref) => EnterToSendNotifier(),);

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
