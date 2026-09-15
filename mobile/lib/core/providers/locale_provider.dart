import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Key for storing language preference in SharedPreferences
const String kLocaleKey = 'app_locale';

/// Provider to manage the application's Locale
final localeProvider =
    StateNotifierProvider<LocaleNotifier, Locale>((ref) => LocaleNotifier());

class LocaleNotifier extends StateNotifier<Locale> {
  LocaleNotifier() : super(I18nService.resolveSupportedLocale()) {
    _syncI18nService();
    unawaited(_loadLocale());
  }

  /// Load saved locale from SharedPreferences
  Future<void> _loadLocale() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final localeCode = prefs.getString(kLocaleKey);
      state = localeCode != null
          ? I18nService.resolveSupportedLocale(Locale(localeCode))
          : I18nService.resolveSupportedLocale();
      // Sync with I18nService
      _syncI18nService();
    } catch (e) {
      // Default to a supported system locale if an error occurs.
      state = I18nService.resolveSupportedLocale();
      _syncI18nService();
    }
  }

  /// Sync the current locale with I18nService
  void _syncI18nService() {
    final l10n = lookupAppLocalizations(state);
    I18nService.instance.updateLocale(state, l10n);
  }

  /// Change and persist the locale
  Future<void> setLocale(Locale locale) async {
    final resolvedLocale = I18nService.resolveSupportedLocale(locale);
    if (state == resolvedLocale) return;

    state = resolvedLocale;
    // Sync with I18nService
    _syncI18nService();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kLocaleKey, resolvedLocale.languageCode);
    } catch (_) {
      // Silent fail for persistence
    }
  }

  /// Toggle between zh and en
  void toggleLocale() {
    if (state.languageCode == 'zh') {
      unawaited(setLocale(const Locale('en')));
    } else {
      unawaited(setLocale(const Locale('zh')));
    }
  }
}
