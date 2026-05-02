import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// FocusCard - Deep Dive Entry Card for Project Cockpit
class FocusCard extends ConsumerStatefulWidget {
  const FocusCard({super.key, this.onTap});
  final VoidCallback? onTap;

  @override
  ConsumerState<FocusCard> createState() => _FocusCardState();
}

class _FocusCardState extends ConsumerState<FocusCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _flameController;
  late Animation<double> _flameAnimation;

  @override
  void initState() {
    super.initState();
    _flameController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    unawaited(_flameController.repeat(reverse: true));

    _flameAnimation = Tween<double>(begin: 0.9, end: 1.1).animate(
      CurvedAnimation(parent: _flameController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _flameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final todayMinutes = dashboardState.flame.todayFocusMinutes;
    final flameLevel = dashboardState.flame.level;
    final tasksCompleted = dashboardState.flame.tasksCompleted;
    final nudgeMessage = dashboardState.flame.nudgeMessage;
    return SparklePressable(
      onTap: widget.onTap,
      padding: EdgeInsets.zero,
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context).copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              Color.lerp(DS.surfaceSecondary, DS.warning, 0.08)!,
              Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.08)!,
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.brandPrimary.withValues(alpha: 0.18),
          borderWidth: 1,
        ),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header with metrics row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    I18nService.instance.isChinese ? '专注核心' : 'Focus Core',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: Color.lerp(DS.surfaceSecondary, DS.flameCore, 0.18) ??
                        DS.surfaceSecondary,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Lv.$flameLevel',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      fontWeight: DS.fontWeightBold,
                      fontSize: 10,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),

            // Content Row: Flame + Nudge + Metrics
            Row(
              children: [
                // Flame Animation + Nudge Message
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Flame and Nudge in same row
                      Row(
                        children: [
                          // Flame Animation
                          AnimatedBuilder(
                            animation: _flameAnimation,
                            builder: (context, child) => Transform.scale(
                              scale: _flameAnimation.value,
                              child: Container(
                                width: 32,
                                height: 32,
                                decoration: BoxDecoration(
                                  gradient: RadialGradient(
                                    colors: [
                                      DS.flameCore,
                                      DS.flameCore.withValues(alpha: 0.4),
                                      DS.surfacePrimary.withValues(alpha: 0),
                                    ],
                                  ),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  Icons.local_fire_department_rounded,
                                  color: DS.warning,
                                  size: 18,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.sm),
                          // Nudge Message
                          Expanded(
                            child: Text(
                              nudgeMessage,
                              style:
                                  context.sparkleTypography.bodyMedium.copyWith(
                                fontSize: 9,
                                height: 1.2,
                                color: DS.textSecondary,
                                fontStyle: FontStyle.italic,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.xs),
                      // Metrics Row (compact)
                      Row(
                        children: [
                          Text(
                            _formatFocusTime(todayMinutes),
                            style:
                                context.sparkleTypography.titleLarge.copyWith(
                              fontSize: 14,
                              fontWeight: DS.fontWeightBold,
                              color: DS.textPrimary,
                            ),
                          ),
                          Text(
                            ' · ',
                            style: TextStyle(
                              fontSize: 12,
                              color: DS.brandPrimary.withValues(alpha: 0.3),
                            ),
                          ),
                          Text(
                            I18nService.instance.isChinese ? '$tasksCompleted完成' : '$tasksCompleted done',
                            style:
                                context.sparkleTypography.labelSmall.copyWith(
                              fontSize: 10,
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatFocusTime(int minutes) {
    if (minutes < 60) return '${minutes}m';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return mins > 0 ? '${hours}h ${mins}m' : '${hours}h';
  }
}
