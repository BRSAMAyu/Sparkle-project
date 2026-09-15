import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

enum WeatherStatusDensity {
  compact,
  regular,
}

@immutable
class WeatherPresentationData {
  const WeatherPresentationData({
    required this.type,
    required this.title,
    required this.subtitle,
    required this.compactHint,
    required this.ambientHint,
    required this.icon,
    required this.accent,
    required this.softAccent,
    required this.highlight,
    required this.borderTint,
    required this.glowAlignment,
    required this.glowRadius,
    required this.headerGradient,
    required this.starIntensity,
    required this.driftFactor,
    required this.particleFactor,
    required this.overlayStrength,
  });

  final String type;
  final String title;
  final String subtitle;
  final String compactHint;
  final String ambientHint;
  final IconData icon;
  final Color accent;
  final Color softAccent;
  final Color highlight;
  final Color borderTint;
  final Alignment glowAlignment;
  final double glowRadius;
  final List<Color> headerGradient;
  final double starIntensity;
  final double driftFactor;
  final double particleFactor;
  final double overlayStrength;

  String resolveCondition(String? condition) {
    final trimmed = condition?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      return trimmed;
    }
    return compactHint;
  }
}

WeatherPresentationData resolveWeatherPresentation(
  BuildContext context,
  String type,
) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  final surfaceA = DS.surfacePrimary;
  final surfaceB = DS.surfaceSecondary;
  final surfaceC = DS.surfaceCanvas;

  Color blend(Color a, Color b, double t) => Color.lerp(a, b, t) ?? a;

  switch (type) {
    case 'cloudy':
      final accent = blend(DS.neutral400, DS.brandPrimary, isDark ? 0.18 : 0.1);
      return WeatherPresentationData(
        type: type,
        title: context.l10n.weatherTitleCloudy,
        subtitle: context.l10n.weatherSubtitleCloudy,
        compactHint: context.l10n.weatherCompactCloudy,
        ambientHint: context.l10n.weatherAmbientCloudy,
        icon: Icons.cloud_rounded,
        accent: accent,
        softAccent: blend(surfaceB, accent, isDark ? 0.18 : 0.1),
        highlight: blend(Colors.white, accent, isDark ? 0.24 : 0.12),
        borderTint: blend(DS.borderSubtle, accent, 0.28),
        glowAlignment: const Alignment(-0.42, -0.18),
        glowRadius: 1.08,
        headerGradient: [
          surfaceA,
          blend(surfaceC, accent, isDark ? 0.12 : 0.07),
          blend(surfaceB, accent, isDark ? 0.16 : 0.08),
        ],
        starIntensity: 0.18,
        driftFactor: 0.42,
        particleFactor: 0.78,
        overlayStrength: 0.74,
      );
    case 'rainy':
      final accent = blend(DS.info, DS.brandPrimary, isDark ? 0.18 : 0.1);
      return WeatherPresentationData(
        type: type,
        title: context.l10n.weatherTitleRainy,
        subtitle: context.l10n.weatherSubtitleRainy,
        compactHint: context.l10n.weatherCompactRainy,
        ambientHint: context.l10n.weatherAmbientRainy,
        icon: Icons.thunderstorm_rounded,
        accent: accent,
        softAccent: blend(surfaceB, accent, isDark ? 0.2 : 0.12),
        highlight: blend(Colors.white, accent, isDark ? 0.2 : 0.12),
        borderTint: blend(DS.borderSubtle, accent, 0.26),
        glowAlignment: const Alignment(0.0, -0.3),
        glowRadius: 1.02,
        headerGradient: [
          blend(surfaceA, DS.surfaceAmbient, isDark ? 0.24 : 0.08),
          blend(surfaceC, accent, isDark ? 0.14 : 0.08),
          blend(surfaceB, accent, isDark ? 0.18 : 0.1),
        ],
        starIntensity: 0.1,
        driftFactor: 0.58,
        particleFactor: 1.0,
        overlayStrength: 0.82,
      );
    case 'meteor':
      final accent =
          blend(DS.brandSecondary, DS.brandPrimary, isDark ? 0.12 : 0.08);
      return WeatherPresentationData(
        type: type,
        title: context.l10n.weatherTitleMeteor,
        subtitle: context.l10n.weatherSubtitleMeteor,
        compactHint: context.l10n.weatherCompactMeteor,
        ambientHint: context.l10n.weatherAmbientMeteor,
        icon: Icons.auto_awesome_rounded,
        accent: accent,
        softAccent: blend(surfaceB, accent, isDark ? 0.2 : 0.1),
        highlight: blend(Colors.white, accent, isDark ? 0.28 : 0.14),
        borderTint: blend(DS.borderSubtle, accent, 0.32),
        glowAlignment: const Alignment(0.02, -0.42),
        glowRadius: 1.18,
        headerGradient: [
          blend(surfaceA, DS.surfaceAmbient, isDark ? 0.28 : 0.06),
          blend(surfaceC, accent, isDark ? 0.14 : 0.08),
          blend(surfaceB, accent, isDark ? 0.18 : 0.1),
        ],
        starIntensity: 0.98,
        driftFactor: 0.68,
        particleFactor: 0.86,
        overlayStrength: 0.78,
      );
    case 'sunny':
    default:
      final accent =
          blend(DS.brandPrimary, DS.brandSecondary, isDark ? 0.12 : 0.08);
      return WeatherPresentationData(
        type: 'sunny',
        title: context.l10n.weatherTitleSunny,
        subtitle: context.l10n.weatherSubtitleSunny,
        compactHint: context.l10n.weatherCompactSunny,
        ambientHint: context.l10n.weatherAmbientSunny,
        icon: Icons.wb_sunny_rounded,
        accent: accent,
        softAccent: blend(surfaceB, accent, isDark ? 0.16 : 0.08),
        highlight: blend(Colors.white, accent, isDark ? 0.22 : 0.12),
        borderTint: blend(DS.borderSubtle, accent, 0.26),
        glowAlignment: const Alignment(0.78, -0.24),
        glowRadius: 0.92,
        headerGradient: [
          surfaceA,
          blend(surfaceC, accent, isDark ? 0.1 : 0.05),
          blend(surfaceB, accent, isDark ? 0.14 : 0.07),
        ],
        starIntensity: 0.26,
        driftFactor: 0.34,
        particleFactor: 0.7,
        overlayStrength: 0.66,
      );
  }
}

class WeatherStatusBadge extends StatelessWidget {
  const WeatherStatusBadge({
    required this.presentation,
    this.condition,
    this.density = WeatherStatusDensity.regular,
    super.key,
  });

  final WeatherPresentationData presentation;
  final String? condition;
  final WeatherStatusDensity density;

  @override
  Widget build(BuildContext context) {
    final compact = density == WeatherStatusDensity.compact;
    final label = presentation.resolveCondition(condition);
    final background = Color.alphaBlend(
      presentation.softAccent.withValues(alpha: compact ? 0.1 : 0.12),
      DS.surfaceOverlay.withValues(alpha: compact ? 0.94 : 0.9),
    );

    return Container(
      constraints: BoxConstraints(maxWidth: compact ? 136 : 168),
      padding: EdgeInsets.symmetric(
        horizontal: compact ? DS.spacing10 : DS.spacing12,
        vertical: compact ? DS.spacing8 : DS.spacing10,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: compact ? DS.borderRadius12 : DS.borderRadius16,
        border:
            Border.all(color: presentation.borderTint.withValues(alpha: 0.9)),
        boxShadow: [
          BoxShadow(
            color: presentation.accent.withValues(alpha: compact ? 0.06 : 0.08),
            blurRadius: compact ? 10 : 14,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: compact ? 24 : 28,
            height: compact ? 24 : 28,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: presentation.accent.withValues(alpha: 0.12),
            ),
            child: Icon(
              presentation.icon,
              size: compact ? 14 : 16,
              color: presentation.accent,
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  presentation.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: compact ? DS.fontSizeXs : DS.fontSizeSm,
                    fontWeight: DS.fontWeightBold,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing2),
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
