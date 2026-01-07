import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

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

    return GestureDetector(
      onTap: widget.onTap,
      child: MaterialStyler(
        material: AppMaterials.neoGlass.copyWith(
           rimLightColor: DS.brandPrimary.withValues(alpha: 0.3),
        ),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '专注核心',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary.withValues(alpha: 0.7),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.flameCore.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    'Lv.$flameLevel',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      fontWeight: FontWeight.bold,
                      fontSize: 11,
                      color: DS.textSecondary,
                    ),
                  ),
                ),
              ],
            ),

            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Flame Animation
                  AnimatedBuilder(
                    animation: _flameAnimation,
                    builder: (context, child) => Transform.scale(
                      scale: _flameAnimation.value,
                      child: Container(
                        width: 60,
                        height: 60,
                        decoration: BoxDecoration(
                          gradient: RadialGradient(
                            colors: [
                              DS.flameCore,
                              DS.flameCore.withValues(alpha: 0.4),
                              Colors.transparent,
                            ],
                          ),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.local_fire_department_rounded,
                          color: DS.warning,
                          size: 32,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.md),
                  // Nudge Message
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: DS.brandPrimary.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      nudgeMessage,
                      textAlign: TextAlign.center,
                      style: context.sparkleTypography.bodyMedium.copyWith(
                        fontSize: 11,
                        height: 1.3,
                        color: DS.textSecondary.withValues(alpha: 0.9),
                        fontStyle: FontStyle.italic,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: DS.sm),

            // Metrics Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildMetric(
                  context,
                  _formatFocusTime(todayMinutes),
                  '今日专注',
                ),
                Container(height: 20, width: 1, color: DS.brandPrimary12),
                _buildMetric(context, '$tasksCompleted', '今日完成'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetric(BuildContext context, String value, String label) =>
      Column(
        children: [
          Text(
            value,
            style: context.sparkleTypography.titleLarge.copyWith(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: context.sparkleTypography.labelSmall.copyWith(
              fontSize: 10,
              color: DS.textSecondary.withValues(alpha: 0.6),
            ),
          ),
        ],
      );

  String _formatFocusTime(int minutes) {
    if (minutes < 60) return '${minutes}m';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return mins > 0 ? '${hours}h ${mins}m' : '${hours}h';
  }
}
