import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum AuroraPresenceLevel {
  ambient,
  active,
  metaSurface,
}

extension AuroraPresenceLevelLabel on AuroraPresenceLevel {
  String get label => switch (this) {
        AuroraPresenceLevel.ambient => 'Ambient',
        AuroraPresenceLevel.active => 'Active',
        AuroraPresenceLevel.metaSurface => 'Meta surface',
      };
}

class AuroraIndicator extends StatelessWidget {
  const AuroraIndicator({
    super.key,
    this.presenceLevel = AuroraPresenceLevel.ambient,
    this.enabled = false,
    this.compact = false,
  });

  final AuroraPresenceLevel presenceLevel;
  final bool enabled;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (!enabled) {
      return const SizedBox.shrink();
    }

    final style = _styleFor(context, presenceLevel);
    final reduceMotion = context.reduceMotion;
    final animationDuration = reduceMotion
        ? Duration.zero
        : switch (presenceLevel) {
            AuroraPresenceLevel.ambient => const Duration(milliseconds: 220),
            AuroraPresenceLevel.active => const Duration(milliseconds: 180),
            AuroraPresenceLevel.metaSurface =>
              const Duration(milliseconds: 160),
          };

    return AnimatedContainer(
      duration: animationDuration,
      curve: Curves.easeOutCubic,
      padding: EdgeInsets.symmetric(
        horizontal: compact ? DS.spacing10 : DS.spacing12,
        vertical: compact ? DS.spacing8 : DS.spacing10,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            style.tint.withValues(alpha: style.backgroundAlpha),
            DS.surfaceSecondary,
          ],
        ),
        borderRadius: BorderRadius.circular(compact ? 16 : 20),
        border: Border.all(
          color: style.tint.withValues(alpha: style.borderAlpha),
        ),
        boxShadow: [
          BoxShadow(
            color: style.tint.withValues(alpha: style.shadowAlpha),
            blurRadius: compact ? 14 : 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _PresenceGlyph(style: style, compact: compact),
          SizedBox(width: compact ? DS.spacing8 : DS.spacing10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Aurora',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              Text(
                presenceLevel.label,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  _PresenceStyle _styleFor(BuildContext context, AuroraPresenceLevel level) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return switch (level) {
      AuroraPresenceLevel.ambient => _PresenceStyle(
          tint: DS.brandPrimary,
          dots: 1,
          backgroundAlpha: isDark ? 0.10 : 0.06,
          borderAlpha: isDark ? 0.22 : 0.14,
          shadowAlpha: 0.08,
        ),
      AuroraPresenceLevel.active => _PresenceStyle(
          tint: DS.brandSecondary,
          dots: 2,
          backgroundAlpha: isDark ? 0.14 : 0.08,
          borderAlpha: isDark ? 0.28 : 0.18,
          shadowAlpha: 0.10,
        ),
      AuroraPresenceLevel.metaSurface => _PresenceStyle(
          tint: DS.semanticWarning,
          dots: 3,
          backgroundAlpha: isDark ? 0.16 : 0.10,
          borderAlpha: isDark ? 0.34 : 0.20,
          shadowAlpha: 0.12,
        ),
    };
  }
}

class _PresenceGlyph extends StatelessWidget {
  const _PresenceGlyph({
    required this.style,
    required this.compact,
  });

  final _PresenceStyle style;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final size = compact ? 28.0 : 34.0;
    final dotSize = compact ? 6.0 : 7.0;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: style.tint.withValues(alpha: 0.16),
              shape: BoxShape.circle,
            ),
          ),
          Container(
            width: size * 0.64,
            height: size * 0.64,
            decoration: BoxDecoration(
              color: style.tint.withValues(alpha: 0.32),
              shape: BoxShape.circle,
            ),
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(
              style.dots,
              (_) => Padding(
                padding: EdgeInsets.symmetric(horizontal: compact ? 1.2 : 1.6),
                child: Container(
                  width: dotSize,
                  height: dotSize,
                  decoration: BoxDecoration(
                    color: DS.textPrimary,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PresenceStyle {
  const _PresenceStyle({
    required this.tint,
    required this.dots,
    required this.backgroundAlpha,
    required this.borderAlpha,
    required this.shadowAlpha,
  });

  final Color tint;
  final int dots;
  final double backgroundAlpha;
  final double borderAlpha;
  final double shadowAlpha;
}
