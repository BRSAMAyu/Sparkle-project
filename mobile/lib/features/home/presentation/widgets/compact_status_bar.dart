import 'package:cached_network_image/cached_network_image.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_presentation.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class CompactStatusBar extends StatelessWidget {
  const CompactStatusBar({
    required this.user,
    required this.dashboardState,
    super.key,
  });

  final UserModel? user;
  final DashboardState dashboardState;

  @override
  Widget build(BuildContext context) {
    final nickname = user?.nickname ?? user?.username ?? 'Sparkle';
    final weatherSummary = dashboardState.weather.condition;
    final weatherPresentation = resolveWeatherPresentation(
      context,
      dashboardState.weather.type,
    );
    final textScale = MediaQuery.textScalerOf(context).scale(1);

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing8,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardEntrance(
          slideOffset: const Offset(0, -0.05),
          child: MaterialStyler(
            material: AppMaterials.ceramic(context),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing8,
            ),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: textScale > 1.18 ? 56 : 48,
              ),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth;
                  final showUserBadge = width >= 316 && textScale < 1.15;
                  final showFlameChip = width >= 352 && textScale < 1.1;
                  final showWeatherLabel = width >= 390 && textScale < 1.05;

                  return Row(
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundImage: user?.avatarUrl != null
                            ? CachedNetworkImageProvider(user!.avatarUrl!)
                            : null,
                        backgroundColor: DS.avatarFallbackBackground,
                        child: user?.avatarUrl == null
                            ? Text(
                                nickname[0].toUpperCase(),
                                style: TextStyle(
                                  color: DS.avatarFallbackForeground,
                                  fontWeight: DS.fontWeightBold,
                                ),
                              )
                            : null,
                      ),
                      const SizedBox(width: DS.spacing10),
                      Expanded(
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    nickname,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: context.sparkleTypography.labelLarge
                                        .copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: DS.fontWeightBold,
                                    ),
                                  ),
                                  Text(
                                    showWeatherLabel
                                        ? _weatherSentence(
                                            weatherPresentation,
                                            weatherSummary,
                                          )
                                        : I18nService.instance.isChinese ? '今天适合保持节奏' : 'Keep your rhythm today',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: context.sparkleTypography.labelSmall
                                        .copyWith(
                                      color: DS.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (showUserBadge) ...[
                              const SizedBox(width: DS.spacing8),
                              _MiniBadge(
                                label: width < 352
                                    ? 'L${user?.flameLevel ?? 1}'
                                    : 'Lv.${user?.flameLevel ?? 1}',
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(width: DS.spacing8),
                      if (showFlameChip) ...[
                        _MiniInfoChip(
                          icon: Icons.local_fire_department_rounded,
                          label: width >= 376
                              ? 'Lv.${dashboardState.flame.level}'
                              : null,
                          color: DS.warning,
                          animateLabel: true,
                          maxWidth: width >= 376 ? 76 : 32,
                        ),
                        const SizedBox(width: DS.spacing6),
                      ],
                      _MiniInfoChip(
                        icon: weatherPresentation.icon,
                        label: showWeatherLabel
                            ? weatherPresentation.resolveCondition(
                                dashboardState.weather.condition,
                              )
                            : null,
                        color: weatherPresentation.accent,
                        tintColor: weatherPresentation.softAccent,
                        borderColor: weatherPresentation.borderTint,
                        maxWidth: showWeatherLabel ? 88 : 32,
                        onTap: () {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          unawaited(context.push(HomeRoutes.weatherGuide));
                        },
                      ),
                      const SizedBox(width: DS.spacing6),
                      InkWell(
                        onTap: () => context.push(UserRoutes.settings),
                        borderRadius: BorderRadius.circular(999),
                        child: Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: DS.surfaceOverlay,
                            shape: BoxShape.circle,
                            border: Border.all(color: DS.borderSubtle),
                          ),
                          child: Icon(
                            Icons.settings_outlined,
                            size: 18,
                            color: DS.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _weatherSentence(
    WeatherPresentationData presentation,
    String weatherSummary,
  ) {
    final zh = I18nService.instance.isChinese;
    if (weatherSummary.trim().isNotEmpty) {
      return zh ? '今天适合${presentation.compactHint}，$weatherSummary' : 'Great for ${presentation.compactHint}, $weatherSummary';
    }
    return zh ? '今天适合${presentation.compactHint}' : 'Great for ${presentation.compactHint}';
  }
}

class _MiniBadge extends StatelessWidget {
  const _MiniBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          label,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _MiniInfoChip extends StatelessWidget {
  const _MiniInfoChip({
    required this.icon,
    required this.color,
    this.label,
    this.animateLabel = false,
    this.maxWidth = 112,
    this.tintColor,
    this.borderColor,
    this.onTap,
  });

  final IconData icon;
  final String? label;
  final Color color;
  final bool animateLabel;
  final double maxWidth;
  final Color? tintColor;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = Container(
      constraints: BoxConstraints(maxWidth: maxWidth),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          (tintColor ?? Colors.transparent).withValues(alpha: 0.1),
          DS.surfacePanel,
        ),
        borderRadius: DS.borderRadiusFull,
        border: Border.all(color: borderColor ?? DS.borderSubtle),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          if (label != null) ...[
            const SizedBox(width: DS.spacing4),
            Flexible(
              child: AnimatedSwitcher(
                duration: DS.durationFast,
                switchInCurve: DS.motionCurve(SparkleMotionToken.micro),
                switchOutCurve: DS.motionCurve(SparkleMotionToken.micro),
                child: Text(
                  label!,
                  key: ValueKey(
                    animateLabel ? label! : '$icon-$label',
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemiBold,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );

    if (onTap == null) {
      return content;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadiusFull,
        child: content,
      ),
    );
  }
}
