import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

void main() {
  tearDown(I18nService.instance.reset);

  test('default locale resolves to a supported locale', () {
    final locale = I18nService.resolveSupportedLocale();
    expect(
      AppLocalizations.supportedLocales
          .map((l) => l.languageCode)
          .contains(locale.languageCode),
      isTrue,
    );
  });

  test('resolveSupportedLocale prefers exact language match', () {
    final locale = I18nService.resolveSupportedLocale(const Locale('zh'));
    expect(locale.languageCode, 'zh');
  });

  test('resolveSupportedLocale falls back to en for unsupported locale', () {
    final locale = I18nService.resolveSupportedLocale(const Locale('xx'));
    expect(locale.languageCode, 'en');
  });

  test('isChinese returns true after updating to zh locale', () {
    I18nService.instance.updateLocale(
      const Locale('zh'),
      AppLocalizationsZh(),
    );
    expect(I18nService.instance.isChinese, isTrue);
    expect(I18nService.instance.isEnglish, isFalse);
  });

  test('isEnglish returns true when locale is en', () {
    I18nService.instance.updateLocale(
      const Locale('en'),
      AppLocalizationsZh(), // type doesn't matter for locale check
    );
    expect(I18nService.instance.isEnglish, isTrue);
    expect(I18nService.instance.isChinese, isFalse);
  });

  test('reset clears locale back to resolved default', () {
    I18nService.instance.updateLocale(
      const Locale('zh'),
      AppLocalizationsZh(),
    );
    expect(I18nService.instance.isChinese, isTrue);

    I18nService.instance.reset();

    // After reset, it falls back to resolved locale
    expect(I18nService.instance.currentLocale, isNotNull);
  });

  test('l10n returns fallback when not explicitly set', () {
    // Before any updateLocale call, l10n should still return a non-null instance
    expect(I18nService.instance.l10n, isNotNull);
  });
}
