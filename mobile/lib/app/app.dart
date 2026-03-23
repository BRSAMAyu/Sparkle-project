import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/unified_push_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Provider for initializing push service once
final pushInitProvider = FutureProvider<void>((ref) async {
  final pushService = ref.watch(unifiedPushServiceProvider);
  await pushService.initialize();
});

/// Sparkle Application Root Widget
class SparkleApp extends ConsumerWidget {
  const SparkleApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final apiClient = ref.watch(apiClientProvider);
    final router = ref.watch(routerProvider);
    ClientObservabilityService.instance.attachDio(apiClient.dio);
    // Watch the manager to rebuild when theme changes (colors, high contrast, etc.)
    ref.watch(themeManagerProvider);
    // Initialize sync engine early.
    ref.watch(syncEngineProvider);
    // Initialize unified push service (FCM + JPush)
    ref.watch(pushInitProvider);
    // Watch the mode specifically for MaterialApp.themeMode
    final themeMode = ref.watch(themeModeProvider);
    final locale = ref.watch(localeProvider);

    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle,
      debugShowCheckedModeBanner: false,
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode: themeMode,
      routerConfig: router,
      locale: locale,
      // Localization
      localizationsDelegates: const [
        ...AppLocalizations.localizationsDelegates,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
}
