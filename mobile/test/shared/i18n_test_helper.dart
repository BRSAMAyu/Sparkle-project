import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// Call in setUp or testWidgets to ensure I18nService defaults to Chinese.
///
/// Most widget tests assert Chinese text because that was the original language
/// before the F-03 i18n bilingual conversion. Setting the service to Chinese
/// ensures existing assertions continue to match.
void setUpI18nForTesting() {
  I18nService.instance.updateLocale(
    const Locale('zh'),
    AppLocalizationsZh(),
  );
}

/// Call in tearDown to reset I18nService back to platform default.
void tearDownI18n() {
  I18nService.instance.reset();
}

/// Creates a MaterialApp with Chinese localization delegates configured.
/// Use this instead of plain MaterialApp in widget tests to ensure
/// context.l10n works correctly.
///
/// U-03 harness repair（与 galaxy/profile 测试同款存量修复）：默认挂上
/// SparkleThemeExtension —— owner 组件（SemanticPill/SparkleRefreshIndicator
/// 等）构建即读 `context.sparkle`，未注册直接断言失败。传入的 [theme] 仍可
/// 覆盖/追加。
Widget testMaterialApp({
  required Widget home,
  ThemeData? theme,
  GlobalKey<NavigatorState>? navigatorKey,
}) {
  return MaterialApp(
    theme: (theme ?? ThemeData()).copyWith(
      extensions: [
        ...?(theme?.extensions.values.toList()),
        SparkleThemeExtension.light(),
      ],
    ),
    home: home,
    navigatorKey: navigatorKey,
    locale: const Locale('zh'),
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
  );
}
