import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/domain/services/emotion_visual_blending_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/layers/weather_layer.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_presentation.dart';

class WeatherGuideScreen extends ConsumerStatefulWidget {
  const WeatherGuideScreen({super.key});

  @override
  ConsumerState<WeatherGuideScreen> createState() => _WeatherGuideScreenState();
}

class _WeatherGuideScreenState extends ConsumerState<WeatherGuideScreen>
    with TickerProviderStateMixin {
  late final AnimationController _mainAnimationController;
  late final AnimationController _particleController;

  List<_WeatherGuideSpec> _specs(AppLocalizations l10n) => [
        _WeatherGuideSpec(
          type: 'sunny',
          title: l10n.weatherTitleSunny,
          previewLabel: l10n.weatherCompactSunny,
          detail: l10n.weatherSubtitleSunny,
          trigger: l10n.weatherGuideRule1Body,
        ),
        _WeatherGuideSpec(
          type: 'cloudy',
          title: l10n.weatherTitleCloudy,
          previewLabel: l10n.weatherCompactCloudy,
          detail: l10n.weatherSubtitleCloudy,
          trigger: l10n.weatherGuideRule2Body,
        ),
        _WeatherGuideSpec(
          type: 'rainy',
          title: l10n.weatherTitleRainy,
          previewLabel: l10n.weatherCompactRainy,
          detail: l10n.weatherSubtitleRainy,
          trigger: l10n.weatherGuideRule3Body,
        ),
        _WeatherGuideSpec(
          type: 'meteor',
          title: l10n.weatherTitleMeteor,
          previewLabel: l10n.weatherCompactMeteor,
          detail: l10n.weatherSubtitleMeteor,
          trigger: l10n.weatherGuideRule5Body,
        ),
      ];

  @override
  void initState() {
    super.initState();
    _mainAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );
    _particleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3200),
    );
    unawaited(_mainAnimationController.repeat(reverse: true));
    unawaited(_particleController.repeat());
  }

  @override
  void dispose() {
    _mainAnimationController.dispose();
    _particleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final currentPresentation = resolveWeatherPresentation(
      context,
      dashboardState.weather.type,
    );

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(context.l10n.weatherGuideTitle),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing24,
          ),
          children: [
            _CurrentWeatherPanel(
              presentation: currentPresentation,
              condition: dashboardState.weather.condition,
            ),
            const SizedBox(height: DS.spacing16),
            _SectionHeader(
              title: context.l10n.weatherGuidePreview,
              subtitle: context.l10n.weatherGuidePreviewSubtitle,
            ),
            const SizedBox(height: DS.spacing10),
            LayoutBuilder(
              builder: (context, constraints) {
                final l10n = context.l10n;
                final compact = constraints.maxWidth < 720;
                final cardWidth = compact
                    ? constraints.maxWidth
                    : (constraints.maxWidth - DS.spacing12) / 2;
                return Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing12,
                  children: _specs(l10n)
                      .map(
                        (spec) => SizedBox(
                          width: cardWidth,
                          child: _WeatherPreviewCard(
                            spec: spec,
                            isCurrent: dashboardState.weather.type == spec.type,
                            mainAnimation: _mainAnimationController,
                            particleAnimation: _particleController,
                          ),
                        ),
                      )
                      .toList(),
                );
              },
            ),
            const SizedBox(height: DS.spacing20),
            _SectionHeader(
              title: context.l10n.weatherGuideCriteria,
              subtitle: context.l10n.weatherGuideCriteriaSubtitle,
            ),
            const SizedBox(height: DS.spacing10),
            _WeatherRuleTile(
              title: context.l10n.weatherGuideRule1Title,
              body: context.l10n.weatherGuideRule1Body,
            ),
            _WeatherRuleTile(
              title: context.l10n.weatherGuideRule2Title,
              body: context.l10n.weatherGuideRule2Body,
            ),
            _WeatherRuleTile(
              title: context.l10n.weatherGuideRule3Title,
              body: context.l10n.weatherGuideRule3Body,
            ),
            _WeatherRuleTile(
              title: context.l10n.weatherGuideRule4Title,
              body: context.l10n.weatherGuideRule4Body,
            ),
            _WeatherRuleTile(
              title: context.l10n.weatherGuideRule5Title,
              body: context.l10n.weatherGuideRule5Body,
            ),
            const SizedBox(height: DS.spacing20),
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing12),
              child: Text(
                context.l10n.weatherGuideDisclaimer,
                style: context.sparkleTypography.labelSmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CurrentWeatherPanel extends StatelessWidget {
  const _CurrentWeatherPanel({
    required this.presentation,
    required this.condition,
  });

  final WeatherPresentationData presentation;
  final String condition;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.weatherGuideCurrentWeather,
                    style: context.sparkleTypography.titleLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
                WeatherStatusBadge(
                  presentation: presentation,
                  condition: condition,
                  density: WeatherStatusDensity.compact,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              presentation.subtitle,
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            const SizedBox(height: DS.spacing10),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: Color.alphaBlend(
                  presentation.softAccent.withValues(alpha: 0.08),
                  DS.surfacePanel,
                ),
                borderRadius: DS.borderRadius16,
                border: Border.all(
                  color: presentation.borderTint.withValues(alpha: 0.75),
                ),
              ),
              child: Text(
                condition.trim().isEmpty
                    ? context.l10n.weatherGuideConditionFallback
                    : context.l10n.weatherGuideConditionPrefix(condition),
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      );
}

class _WeatherPreviewCard extends StatelessWidget {
  const _WeatherPreviewCard({
    required this.spec,
    required this.isCurrent,
    required this.mainAnimation,
    required this.particleAnimation,
  });

  final _WeatherGuideSpec spec;
  final bool isCurrent;
  final Animation<double> mainAnimation;
  final Animation<double> particleAnimation;

  @override
  Widget build(BuildContext context) {
    final presentation = resolveWeatherPresentation(context, spec.type);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: ClipRRect(
        borderRadius: DS.borderRadius20,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 188,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: presentation.headerGradient,
                      ),
                    ),
                  ),
                  IgnorePointer(
                    child: WeatherLayer(
                      weatherType: spec.type,
                      blendParams: _previewBlendParams(spec.type),
                      mainAnimation: mainAnimation,
                      particleAnimation: particleAnimation,
                    ),
                  ),
                  Positioned(
                    left: DS.spacing12,
                    right: DS.spacing12,
                    bottom: DS.spacing12,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: WeatherStatusBadge(
                                presentation: presentation,
                                condition: spec.previewLabel,
                                density: WeatherStatusDensity.compact,
                              ),
                            ),
                            if (isCurrent) ...[
                              const SizedBox(width: DS.spacing8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: DS.spacing8,
                                  vertical: DS.spacing4,
                                ),
                                decoration: BoxDecoration(
                                  color: DS.surfaceOverlay.withValues(
                                    alpha: 0.76,
                                  ),
                                  borderRadius: DS.borderRadiusFull,
                                  border: Border.all(color: DS.borderSubtle),
                                ),
                                child: Text(
                                  context.l10n.weatherGuideCurrent,
                                  style: context.sparkleTypography.labelSmall
                                      .copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: DS.spacing8),
                        Text(
                          spec.title,
                          style: context.sparkleTypography.titleLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Text(
                          presentation.ambientHint,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    spec.detail,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing10,
                      vertical: DS.spacing8,
                    ),
                    decoration: BoxDecoration(
                      color: DS.surfacePanel,
                      borderRadius: DS.borderRadius16,
                      border: Border.all(color: DS.borderSubtle),
                    ),
                    child: Text(
                      context.l10n.weatherGuideTriggerPrefix(spec.trigger),
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  VisualBlendParams _previewBlendParams(String type) {
    switch (type) {
      case 'cloudy':
        return VisualBlendParams(
          primaryTint: DS.neutral400,
          particleDensity: 0.56,
          animationSpeed: 0.55,
          backgroundOpacity: 0.28,
        );
      case 'rainy':
        return VisualBlendParams(
          primaryTint: DS.info,
          particleDensity: 0.72,
          animationSpeed: 0.78,
          backgroundOpacity: 0.32,
        );
      case 'meteor':
        return VisualBlendParams(
          primaryTint: DS.brandSecondary,
          particleDensity: 0.62,
          animationSpeed: 0.88,
          backgroundOpacity: 0.28,
        );
      case 'sunny':
      default:
        return VisualBlendParams(
          primaryTint: DS.brandPrimary,
          particleDensity: 0.48,
          animationSpeed: 0.62,
          backgroundOpacity: 0.24,
        );
    }
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: context.sparkleTypography.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            subtitle,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
        ],
      );
}

class _WeatherRuleTile extends StatelessWidget {
  const _WeatherRuleTile({
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                body,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ],
          ),
        ),
      );
}

class _WeatherGuideSpec {
  const _WeatherGuideSpec({
    required this.type,
    required this.title,
    required this.previewLabel,
    required this.detail,
    required this.trigger,
  });

  final String type;
  final String title;
  final String previewLabel;
  final String detail;
  final String trigger;
}
