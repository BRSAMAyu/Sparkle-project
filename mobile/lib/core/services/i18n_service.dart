import 'dart:ui' show Locale;

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

  /// 中文优先解析（batch3 W-7 裁决：竞赛产品中文优先）。
  ///
  /// - 显式偏好（设置页选择 / 持久化恢复）按语言码匹配支持档；
  /// - 无偏好或不可匹配（含系统 locale 不在支持档）一律回退 zh——
  ///   不再跟随系统 locale 猜测默认语言。en 仍可在设置中显式选择
  ///   （持久化后经 [preferred] 分支命中）。
  static Locale resolveSupportedLocale([Locale? preferred]) {
    if (preferred != null) {
      for (final locale in AppLocalizations.supportedLocales) {
        if (locale.languageCode == preferred.languageCode) {
          return locale;
        }
      }
    }
    return const Locale('zh');
  }

  static AppLocalizations _buildFallbackLocalizations(Locale locale) {
    switch (locale.languageCode) {
      case 'en':
        return AppLocalizationsEn();
      case 'zh':
      default:
        // Chinese-first fallback (batch3 W-7): unknown codes land on zh.
        return AppLocalizationsZh();
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
