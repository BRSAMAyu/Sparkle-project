import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/offline_banner.dart';
import 'package:sparkle/core/design/widgets/pulse_scope.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/app_link_router_service.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/tts_service.dart';
import 'package:sparkle/core/services/unified_push_service.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
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
    // Watch providers that should stay alive and rebuild the app shell.
    ref
      ..watch(themeManagerProvider)
      ..watch(deferredSyncBootstrapProvider)
      ..watch(pushInitProvider)
      ..watch(ttsServiceProvider);
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
      builder: (context, child) {
        final mediaQuery = MediaQuery.of(context);
        final accessibility = ref.watch(accessibilitySettingsProvider);
        if (accessibility.isLoaded) {
          _syncAccessibilityToTheme(accessibility);
        }
        return Column(
          children: [
            const OfflineBanner(),
            Expanded(
              child: _ThemeTransitionShell(
                theme: Theme.of(context),
                child: MediaQuery(
                  data: mediaQuery.copyWith(
                    textScaler: accessibility.isLoaded
                        ? TextScaler.linear(accessibility.fontScale)
                        : mediaQuery.textScaler.clamp(
                            minScaleFactor: 0.85,
                            maxScaleFactor: 1.35,
                          ),
                    disableAnimations: accessibility.isLoaded
                        ? accessibility.reduceMotion
                        : mediaQuery.disableAnimations,
                    accessibleNavigation: accessibility.isLoaded
                        ? accessibility.screenReaderOptimized
                        : mediaQuery.accessibleNavigation,
                  ),
                  child: PulseScope(
                    child: EmotionResponsiveAppWrapper(
                      config: emotionConfig,
                      child: DefaultTextStyle.merge(
                        style: const TextStyle(
                          fontFamilyFallback: sparkleFontFallback,
                        ),
                        child: _ColdStartFade(
                          child: child ?? const SizedBox.shrink(),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _ThemeTransitionShell extends StatelessWidget {
  const _ThemeTransitionShell({
    required this.theme,
    required this.child,
  });

  static const _duration = Duration(milliseconds: 280);

  final ThemeData theme;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final transitionKey = ValueKey<Object>(
      Object.hash(
        theme.brightness,
        theme.colorScheme.surface,
        theme.colorScheme.primary,
        theme.focusColor,
      ),
    );

    return AnimatedTheme(
      data: theme,
      duration: _duration,
      curve: Curves.easeInOut,
      child: TweenAnimationBuilder<double>(
        key: transitionKey,
        tween: Tween<double>(begin: 0.06, end: 0),
        duration: _duration,
        curve: Curves.easeOutCubic,
        child: child,
        builder: (context, overlayOpacity, child) => Stack(
          children: [
            child ?? const SizedBox.shrink(),
            if (overlayOpacity > 0)
              Positioned.fill(
                child: IgnorePointer(
                  child: ColoredBox(
                    color: theme.colorScheme.surface.withValues(
                      alpha: overlayOpacity,
                    ),
                  ),
                ),
              ),
          ],
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
    );
    unawaited(_controller.forward());
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

/// Sync accessibility settings to ThemeManager (high contrast, color blind mode).
/// Called from MaterialApp builder when accessibility state changes.
void _syncAccessibilityToTheme(AccessibilitySettings settings) {
  final tm = ThemeManager();
  if (tm.highContrast != settings.highContrast) {
    unawaited(tm.toggleHighContrast(settings.highContrast));
  }
  if (tm.colorBlindFriendly != settings.colorBlindFriendly) {
    unawaited(tm.setColorBlindMode(settings.colorBlindFriendly));
  }
}
