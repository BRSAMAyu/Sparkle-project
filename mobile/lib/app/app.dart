import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/app_link_router_service.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/unified_push_service.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Provider for initializing push service once
final pushInitProvider = FutureProvider<void>((ref) async {
  final authState = ref.watch(authProvider);
  final user = authState.user;
  if (authState.isLoading || !authState.isAuthenticated || user == null) {
    return;
  }
  if (user.registrationSource == 'guest') {
    return;
  }
  final pushService = ref.watch(unifiedPushServiceProvider);
  await pushService.initialize();
});

/// Provider for booting the sync engine after the shell is already interactive.
final deferredSyncBootstrapProvider = FutureProvider<void>((ref) async {
  final authState = ref.watch(authProvider);
  if (authState.isLoading || !authState.isAuthenticated) {
    return;
  }
  await Future<void>.delayed(const Duration(milliseconds: 900));
  ref.read(syncEngineProvider);
});

/// Sparkle Application Root Widget
class SparkleApp extends ConsumerStatefulWidget {
  const SparkleApp({super.key});

  @override
  ConsumerState<SparkleApp> createState() => _SparkleAppState();
}

class _SparkleAppState extends ConsumerState<SparkleApp> {
  @override
  void initState() {
    super.initState();
    unawaited(AppLinkRouterService.instance.initialize());
  }

  @override
  Widget build(BuildContext context) {
    final apiClient = ref.watch(apiClientProvider);
    final router = ref.watch(routerProvider);
    ClientObservabilityService.instance.attachDio(apiClient.dio);
    // Watch the manager to rebuild when theme changes (colors, high contrast, etc.)
    ref.watch(themeManagerProvider);
    // Defer sync startup until auth has settled and the shell is visible.
    ref.watch(deferredSyncBootstrapProvider);
    // Initialize unified push service (FCM + JPush)
    ref.watch(pushInitProvider);
    // Watch the mode specifically for MaterialApp.themeMode
    final themeMode = ref.watch(themeModeProvider);
    final locale = ref.watch(localeProvider);
    final emotionConfig = ref.watch(emotionResponsiveConfigProvider);

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
      builder: (context, child) => EmotionResponsiveAppWrapper(
        config: emotionConfig,
        child: DefaultTextStyle.merge(
          style: const TextStyle(fontFamilyFallback: sparkleFontFallback),
          child: _ColdStartFade(
            child: child ?? const SizedBox.shrink(),
          ),
        ),
      ),
    );
  }
}

class _ColdStartFade extends StatefulWidget {
  const _ColdStartFade({required this.child});

  final Widget child;

  @override
  State<_ColdStartFade> createState() => _ColdStartFadeState();
}

class _ColdStartFadeState extends State<_ColdStartFade>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    )..forward();
    _opacity = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOutCubic,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
        opacity: _opacity,
        child: widget.child,
      );
}
