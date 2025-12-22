import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/app/theme.dart';

/// FocusCard - Deep Dive Entry Card for Project Cockpit
class FocusCard extends ConsumerStatefulWidget {
  final VoidCallback? onTap;

  const FocusCard({super.key, this.onTap});

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

    return GestureDetector(
      onTap: widget.onTap,
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppDesignTokens.flameCore.withAlpha(40),
                  AppDesignTokens.glassBackground,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '专注核心',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textOnDark(context).withOpacity(0.7),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppDesignTokens.flameCore.withAlpha(40),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        'Lv.$flameLevel',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textOnDark(context),
                        ),
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Center(
                  child: AnimatedBuilder(
                    animation: _flameAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _flameAnimation.value,
                        child: Container(
                          width: 70,
                          height: 70,
                          decoration: BoxDecoration(
                            gradient: RadialGradient(
                              colors: [
                                AppDesignTokens.flameCore,
                                AppDesignTokens.flameCore.withAlpha(100),
                                Colors.transparent,
                              ],
                            ),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            Icons.local_fire_department_rounded,
                            color: AppColors.iconOnDark(context),
                            size: 36,
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const Spacer(),
                Center(
                  child: Column(
                    children: [
                      Text(
                        _formatFocusTime(todayMinutes),
                        style: TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textOnDark(context),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '今日专注时长',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textOnDark(context).withOpacity(0.6),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withAlpha(20),
                      borderRadius: BorderRadius.circular(15),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          dashboardState.weather.type == 'sunny' ? '心流状态' : '进入驾驶舱',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textOnDark(context),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(Icons.chevron_right_rounded, color: AppColors.iconOnDark(context), size: 14),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
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
