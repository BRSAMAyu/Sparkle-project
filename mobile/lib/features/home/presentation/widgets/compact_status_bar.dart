import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
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

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing8,
          DS.spacing16,
          DS.spacing8,
        ),
        child: DashboardEntrance(
          slideOffset: const Offset(0, -0.05),
          child: MaterialStyler(
            material: AppMaterials.ceramic,
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing8,
            ),
            child: SizedBox(
              height: 48,
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 14,
                    backgroundImage: user?.avatarUrl != null
                        ? NetworkImage(user!.avatarUrl!)
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
                        Flexible(
                          child: Text(
                            nickname,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style:
                                context.sparkleTypography.labelLarge.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                        ),
                        const SizedBox(width: DS.spacing8),
                        _MiniBadge(label: 'Lv.${user?.flameLevel ?? 1}'),
                      ],
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  _MiniInfoChip(
                    icon: Icons.local_fire_department_rounded,
                    label: 'Lv.${dashboardState.flame.level}',
                    color: DS.warning,
                    animateLabel: true,
                  ),
                  const SizedBox(width: DS.spacing6),
                  _MiniInfoChip(
                    icon: _weatherIconForType(dashboardState.weather.type),
                    label: dashboardState.weather.condition,
                    color: DS.brandPrimary,
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
              ),
            ),
          ),
        ),
      ),
    );
  }

  IconData _weatherIconForType(String type) {
    switch (type) {
      case 'sunny':
        return Icons.wb_sunny_rounded;
      case 'cloudy':
        return Icons.cloud_rounded;
      case 'rainy':
        return Icons.thunderstorm_rounded;
      case 'meteor':
        return Icons.auto_awesome_rounded;
      default:
        return Icons.wb_sunny_rounded;
    }
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
        ),
        child: Text(
          label,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.warning,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _MiniInfoChip extends StatelessWidget {
  const _MiniInfoChip({
    required this.icon,
    required this.label,
    required this.color,
    this.animateLabel = false,
  });

  final IconData icon;
  final String label;
  final Color color;
  final bool animateLabel;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 112),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing4),
            Flexible(
              child: AnimatedSwitcher(
                duration: DS.durationFast,
                switchInCurve: DS.motionCurve(SparkleMotionToken.micro),
                switchOutCurve: DS.motionCurve(SparkleMotionToken.micro),
                child: Text(
                  label,
                  key: ValueKey(animateLabel ? label : '$icon-$label'),
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
        ),
      );
}
