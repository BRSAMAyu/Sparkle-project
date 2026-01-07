import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Key for storing language preference in SharedPreferences
const String kLocaleKey = 'app_locale';

/// Provider to manage the application's Locale
final localeProvider =
    StateNotifierProvider<LocaleNotifier, Locale>((ref) => LocaleNotifier());

class LocaleNotifier extends StateNotifier<Locale> {
  LocaleNotifier() : super(const Locale('zh')) {
    _loadLocale();
  }

  /// Load saved locale from SharedPreferences
  Future<void> _loadLocale() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final localeCode = prefs.getString(kLocaleKey);
      if (localeCode != null) {
        state = Locale(localeCode);
      }
    } catch (e) {
      // Default to zh if error occurs
      state = const Locale('zh');
    }
  }

  /// Change and persist the locale
  Future<void> setLocale(Locale locale) async {
    if (state == locale) return;

    state = locale;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kLocaleKey, locale.languageCode);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  /// Toggle between zh and en
  void toggleLocale() {
    if (state.languageCode == 'zh') {
      setLocale(const Locale('en'));
    } else {
      setLocale(const Locale('zh'));
    }
  }
}
