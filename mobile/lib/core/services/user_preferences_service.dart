import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Simple local persistence for user preferences used by settings screens.
class UserPreferencesService {
  UserPreferencesService(this._prefs);

  static const String _prefsKey = 'user_preferences';

  final SharedPreferences _prefs;

  Future<Map<String, dynamic>> getPreferences() async {
    final raw = _prefs.getString(_prefsKey);
    if (raw == null || raw.isEmpty) {
      return <String, dynamic>{};
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {
      // Fall through to return empty preferences on decode errors.
    }
    return <String, dynamic>{};
  }

  Future<void> updatePreferences(Map<String, dynamic> updates) async {
    final current = await getPreferences();
    current.addAll(updates);
    await _prefs.setString(_prefsKey, jsonEncode(current));
  }
}

final userPreferencesServiceProvider = Provider<UserPreferencesService>((ref) {
  throw UnimplementedError('UserPreferencesService must be overridden in main.dart');
});
