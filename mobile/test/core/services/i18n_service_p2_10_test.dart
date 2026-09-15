import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

void main() {
  setUp(I18nService.instance.reset);
  tearDown(I18nService.instance.reset);

  test('resolveSupportedLocale keeps supported Chinese variants in zh', () {
    final locale = I18nService.resolveSupportedLocale(
      const Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hans'),
    );

    expect(locale.languageCode, 'zh');
  });

  test('resolveSupportedLocale falls back to English for unsupported locales',
      () {
    final locale = I18nService.resolveSupportedLocale(const Locale('fr'));

    expect(locale.languageCode, 'en');
  });

  test('updateLocale switches the singleton into Chinese mode', () {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());

    expect(I18nService.instance.currentLocale.languageCode, 'zh');
    expect(I18nService.instance.isChinese, isTrue);
    expect(I18nService.instance.isEnglish, isFalse);
    expect(I18nService.instance.l10n.appTitle, 'Sparkle 星火');
  });

  test('updateLocale switches the singleton into English mode', () {
    I18nService.instance.updateLocale(const Locale('en'), AppLocalizationsEn());

    expect(I18nService.instance.currentLocale.languageCode, 'en');
    expect(I18nService.instance.isEnglish, isTrue);
    expect(I18nService.instance.isChinese, isFalse);
    expect(I18nService.instance.l10n.home, 'Cockpit');
  });

  test('global S shortcut follows the latest service locale', () {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
    expect(S.tasks, '任务');

    I18nService.instance.updateLocale(const Locale('en'), AppLocalizationsEn());
    expect(S.tasks, 'Tasks');
  });

  test('reset clears explicit localizations and rebuilds a fallback instance',
      () {
    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());

    I18nService.instance.reset();

    expect(I18nService.instance.l10n, isNotNull);
    expect(
      I18nService.resolveSupportedLocale(const Locale('zz')).languageCode,
      'en',
    );
  });
}
