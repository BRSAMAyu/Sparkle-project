import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Provider for focus mode state
/// Manages the user's focus mode preference and persists it to shared preferences
final focusModeProvider = StateNotifierProvider<FocusModeNotifier, bool>(
    (ref) => FocusModeNotifier(),);

/// Notifier for managing focus mode state
class FocusModeNotifier extends StateNotifier<bool> {
  FocusModeNotifier() : super(false) {
    _loadFromPrefs();
  }

  /// Load focus mode state from shared preferences
  Future<void> _loadFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    state = prefs.getBool('focus_mode') ?? false;
  }

  /// Toggle focus mode and persist the new state
  Future<void> toggle() async {
    state = !state;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('focus_mode', state);
    // TRACKED(TD-004): Update user status to backend when focus mode changes
    // This would require accessing CommunityRepository here
  }
}
