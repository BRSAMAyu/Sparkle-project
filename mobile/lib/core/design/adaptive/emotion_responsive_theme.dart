import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum EmotionAdaptiveIntensity {
  normal,
  lowStimulus;

  bool get isLowStimulus => this == EmotionAdaptiveIntensity.lowStimulus;
}

@immutable
class EmotionResponsiveConfig {
  const EmotionResponsiveConfig({
    required this.intensity,
    required this.fontSizeDelta,
    required this.reduceMotion,
    required this.simplifyCardHierarchy,
    required this.dimColorTemperature,
    required this.hideChallengeBadges,
  });

  const EmotionResponsiveConfig.normal()
      : intensity = EmotionAdaptiveIntensity.normal,
        fontSizeDelta = 0,
        reduceMotion = false,
        simplifyCardHierarchy = false,
        dimColorTemperature = false,
        hideChallengeBadges = false;

  const EmotionResponsiveConfig.lowStimulus()
      : intensity = EmotionAdaptiveIntensity.lowStimulus,
        fontSizeDelta = 1,
        reduceMotion = true,
        simplifyCardHierarchy = true,
        dimColorTemperature = true,
        hideChallengeBadges = true;

  final EmotionAdaptiveIntensity intensity;
  final double fontSizeDelta;
  final bool reduceMotion;
  final bool simplifyCardHierarchy;
  final bool dimColorTemperature;
  final bool hideChallengeBadges;

  bool get isLowStimulus => intensity.isLowStimulus;
}

class EmotionResponsiveTheme extends InheritedWidget {
  const EmotionResponsiveTheme({
    required this.config,
    required super.child,
    super.key,
  });

  final EmotionResponsiveConfig config;

  static EmotionResponsiveConfig of(BuildContext context) =>
      context
          .dependOnInheritedWidgetOfExactType<EmotionResponsiveTheme>()
          ?.config ??
      const EmotionResponsiveConfig.normal();

  static EmotionResponsiveConfig maybeOf(BuildContext context) =>
      context
          .dependOnInheritedWidgetOfExactType<EmotionResponsiveTheme>()
          ?.config ??
      const EmotionResponsiveConfig.normal();

  static ThemeData applyToTheme(
    ThemeData baseTheme,
    EmotionResponsiveConfig config,
  ) {
    if (!config.isLowStimulus) {
      return baseTheme;
    }

    TextStyle? lift(TextStyle? style) =>
        style?.copyWith(fontSize: (style.fontSize ?? DS.fontSizeBase) + 1);

    final textTheme = baseTheme.textTheme.copyWith(
      displayLarge: lift(baseTheme.textTheme.displayLarge),
      displayMedium: lift(baseTheme.textTheme.displayMedium),
      displaySmall: lift(baseTheme.textTheme.displaySmall),
      headlineLarge: lift(baseTheme.textTheme.headlineLarge),
      headlineMedium: lift(baseTheme.textTheme.headlineMedium),
      headlineSmall: lift(baseTheme.textTheme.headlineSmall),
      titleLarge: lift(baseTheme.textTheme.titleLarge),
      titleMedium: lift(baseTheme.textTheme.titleMedium),
      titleSmall: lift(baseTheme.textTheme.titleSmall),
      bodyLarge: lift(baseTheme.textTheme.bodyLarge),
      bodyMedium: lift(baseTheme.textTheme.bodyMedium),
      bodySmall: lift(baseTheme.textTheme.bodySmall),
      labelLarge: lift(baseTheme.textTheme.labelLarge),
      labelMedium: lift(baseTheme.textTheme.labelMedium),
      labelSmall: lift(baseTheme.textTheme.labelSmall),
    );

    final cardShape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(14),
      side: BorderSide(
        color: baseTheme.colorScheme.outlineVariant.withValues(alpha: 0.7),
      ),
    );

    return baseTheme.copyWith(
      textTheme: textTheme,
      splashFactory: NoSplash.splashFactory,
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: NoTransitionsBuilder(),
          TargetPlatform.iOS: NoTransitionsBuilder(),
          TargetPlatform.macOS: NoTransitionsBuilder(),
          TargetPlatform.linux: NoTransitionsBuilder(),
          TargetPlatform.windows: NoTransitionsBuilder(),
        },
      ),
      cardTheme: baseTheme.cardTheme.copyWith(
        elevation: 0,
        shape: cardShape,
        surfaceTintColor: Colors.transparent,
      ),
      chipTheme: baseTheme.chipTheme.copyWith(
        elevation: 0,
        pressElevation: 0,
      ),
      visualDensity: VisualDensity.standard,
    );
  }

  @override
  bool updateShouldNotify(EmotionResponsiveTheme oldWidget) =>
      oldWidget.config != config;
}

class EmotionResponsiveAppWrapper extends StatelessWidget {
  const EmotionResponsiveAppWrapper({
    required this.config,
    required this.child,
    super.key,
  });

  final EmotionResponsiveConfig config;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.maybeOf(context);
    final themedChild = Theme(
      data: EmotionResponsiveTheme.applyToTheme(Theme.of(context), config),
      child: EmotionResponsiveTheme(
        config: config,
        child: _EmotionColorTemperatureLayer(
          enabled: config.dimColorTemperature,
          child: child,
        ),
      ),
    );

    if (mediaQuery == null || !config.reduceMotion) {
      return themedChild;
    }

    return MediaQuery(
      data: mediaQuery.copyWith(
        disableAnimations: true,
        accessibleNavigation: true,
      ),
      child: themedChild,
    );
  }
}

// Light mode: warm dimming (slightly more red/green, less blue)
const _lightLowStimulusFilter = ColorFilter.matrix(<double>[
  0.94, 0, 0, 0, 0, //
  0, 0.96, 0, 0, 0, //
  0, 0, 1.02, 0, 0, //
  0, 0, 0, 1, 0, //
]);

// Dark mode: uniform brightness reduction, no color shift
const _darkLowStimulusFilter = ColorFilter.matrix(<double>[
  0.94, 0, 0, 0, 0, //
  0, 0.94, 0, 0, 0, //
  0, 0, 0.94, 0, 0, //
  0, 0, 0, 1, 0, //
]);

class _EmotionColorTemperatureLayer extends StatelessWidget {
  const _EmotionColorTemperatureLayer({
    required this.enabled,
    required this.child,
  });

  final bool enabled;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (!enabled) return child;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ColorFiltered(
      colorFilter:
          isDark ? _darkLowStimulusFilter : _lightLowStimulusFilter,
      child: child,
    );
  }
}

class NoTransitionsBuilder extends PageTransitionsBuilder {
  const NoTransitionsBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) =>
      child;
}

extension EmotionResponsiveContext on BuildContext {
  EmotionResponsiveConfig get emotionResponsive =>
      EmotionResponsiveTheme.of(this);

  bool get emotionLowStimulus => EmotionResponsiveTheme.of(this).isLowStimulus;

  bool get hideChallengeBadges =>
      EmotionResponsiveTheme.of(this).hideChallengeBadges;
}
