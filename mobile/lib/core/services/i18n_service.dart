import 'dart:ui' show Locale, PlatformDispatcher;

import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// Global i18n service for context-free localization access.
///
/// This singleton provides access to localized strings without requiring
/// a BuildContext, useful in services, providers, and other non-widget code.
///
/// Usage:
/// ```dart
/// import 'package:sparkle/core/services/i18n_service.dart';
///
/// // Using the global shortcut
/// final label = S.aiStatusThinking;
///
/// // Or via instance
/// final l10n = I18nService.instance.l10n;
/// ```
class I18nService {
  I18nService._();

  static final I18nService instance = I18nService._();

  Locale? _currentLocale;
  AppLocalizations? _l10n;

  static Locale resolveSupportedLocale([Locale? preferred]) {
    final candidate = preferred ?? PlatformDispatcher.instance.locale;
    for (final locale in AppLocalizations.supportedLocales) {
      if (locale.languageCode == candidate.languageCode) {
        return locale;
      }
    }
    return const Locale('en');
  }

  static AppLocalizations _buildFallbackLocalizations(Locale locale) {
    switch (locale.languageCode) {
      case 'zh':
        return AppLocalizationsZh();
      case 'en':
      default:
        return AppLocalizationsEn();
    }
  }

  /// Get the current localizations instance.
  /// Falls back to the resolved app locale if not initialized.
  AppLocalizations get l10n =>
      _l10n ?? _buildFallbackLocalizations(currentLocale);

  /// Get the current locale.
  /// Falls back to the resolved app locale if not initialized.
  Locale get currentLocale => _currentLocale ?? resolveSupportedLocale();

  /// Check if current locale is Chinese.
  bool get isChinese => currentLocale.languageCode == 'zh';

  /// Check if current locale is English.
  bool get isEnglish => currentLocale.languageCode == 'en';

  /// Update the current locale and localizations.
  /// Called by LocaleNotifier when locale changes.
  void updateLocale(Locale locale, AppLocalizations l10n) {
    _currentLocale = locale;
    _l10n = l10n;
  }

  /// Reset the service (useful for testing).
  void reset() {
    _currentLocale = null;
    _l10n = null;
  }
}

/// Global shortcut for accessing localizations.
///
/// Example:
/// ```dart
/// Text(S.aiStatusThinking)
/// ```
AppLocalizations get S => I18nService.instance.l10n;
