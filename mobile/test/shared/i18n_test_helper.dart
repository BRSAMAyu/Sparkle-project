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
///
/// HYGIENE-DEBT（wt239 登记）：支持 [routerConfig]（GoRouter）——feature 屏
/// （TaskListScreen 等）build/交互走 `context.push/go/pop` 扩展，harness 缺
/// GoRouter 时 tap 路径必炸。传 [routerConfig] 走 MaterialApp.router（go_router
/// 的 GoRouter 即 RouterConfig<Object>），与 [home] 二选一。
Widget testMaterialApp({
  Widget? home,
  ThemeData? theme,
  GlobalKey<NavigatorState>? navigatorKey,
  RouterConfig<Object>? routerConfig,
}) {
  assert(
    (home != null) != (routerConfig != null),
    'testMaterialApp: exactly one of home/routerConfig is required',
  );
  final themeData = (theme ?? ThemeData()).copyWith(
    extensions: [
      ...?(theme?.extensions.values.toList()),
      SparkleThemeExtension.light(),
    ],
  );
  if (routerConfig != null) {
    return MaterialApp.router(
      routerConfig: routerConfig,
      theme: themeData,
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
  final resolvedHome = home;
  if (resolvedHome == null) {
    throw StateError(
      'testMaterialApp: home is required when routerConfig is absent',
    );
  }
  return MaterialApp(
    theme: themeData,
    home: resolvedHome,
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
