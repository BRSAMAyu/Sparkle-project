import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    )..repeat(reverse: true);

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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final headerColor = isDark ? DS.textPrimary : DS.textSecondary;
    final secondaryColor = isDark ? DS.textPrimary : DS.textSecondary;

    return GestureDetector(
      onTap: widget.onTap,
      child: MaterialStyler(
        material: AppMaterials.neoGlass.copyWith(
          rimLightColor: DS.brandPrimary.withValues(alpha: 0.3),
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
                    '专注核心',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: headerColor.withValues(alpha: 0.85),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Container(
                  padding: EdgeInsets.symmetric(
                    horizontal: DS.spacing6,
                    vertical: DS.spacing4 / 2,
                  ),
                  decoration: BoxDecoration(
                    color: DS.flameCore.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'Lv.$flameLevel',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                      color: secondaryColor,
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
                                color: secondaryColor.withValues(alpha: 0.9),
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
                              fontWeight: FontWeight.bold,
                              color: secondaryColor,
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
                            '$tasksCompleted完成',
                            style:
                                context.sparkleTypography.labelSmall.copyWith(
                              fontSize: 10,
                              color: secondaryColor.withValues(alpha: 0.7),
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
