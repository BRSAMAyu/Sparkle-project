import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// PrismCard - Cognitive Prism Card (2x1 wide)
class PrismCard extends ConsumerStatefulWidget {
  const PrismCard({super.key});

  @override
  ConsumerState<PrismCard> createState() => _PrismCardState();
}

class _PrismCardState extends ConsumerState<PrismCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;

  @override
  void initState() {
    super.initState();
    _breathingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );
    unawaited(_breathingController.repeat(reverse: true));
    _breathingAnimation = Tween<double>(begin: 0.1, end: 0.3).animate(
      CurvedAnimation(parent: _breathingController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _breathingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final cognitive = dashboardState.cognitive;
    final weeklyPattern = cognitive.weeklyPattern;

    return GestureDetector(
      onTap: () => context.push('/cognitive/patterns'),
      child: ClipRRect(
        borderRadius: DS.borderRadius20,
        child: MaterialStyler(
          material: AppMaterials.ceramic.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.prismPurple.withValues(alpha: 0.08),
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.prismPurple.withValues(alpha: 0.25),
            borderWidth: 1.0,
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.lg),
          child: Stack(
            clipBehavior: Clip.antiAlias,
            children: [
            // Prism refraction effect (animated)
            Positioned(
              right: -10,
              bottom: -10,
              child: AnimatedBuilder(
                animation: _breathingAnimation,
                builder: (context, child) => Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        DS.prismPurple.withValues(
                            alpha: _breathingAnimation.value * 0.5),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
            ),

            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Icon(Icons.diamond_outlined,
                        color: DS.prismPurple, size: 18,),
                    const SizedBox(width: DS.sm),
                    Text(
                      '认知棱镜',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: DS.textPrimary,
                      ),
                    ),
                    const Spacer(),
                    if (cognitive.hasNewInsight)
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: DS.prismPurple,
                          shape: BoxShape.circle,
                        ),
                      ),
                  ],
                ),
                const Spacer(),
                if (weeklyPattern != null) ...[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _buildTag(context, '#$weeklyPattern'),
                      if (dashboardState.weather.type == 'rainy')
                        _buildTag(context, '#焦虑波峰'),
                    ],
                  ),
                  const SizedBox(height: DS.xs),
                  Text(
                    '行为定式分析已更新',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  GestureDetector(
                    onTap: () => context.push('/errors?dimension=analysis'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: DS.prismPurple.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: DS.prismPurple.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.error_outline, size: 12, color: DS.prismPurple),
                          const SizedBox(width: 4),
                          Text(
                            '复习弱项: 分析',
                            style: context.sparkleTypography.labelSmall.copyWith(
                              fontWeight: FontWeight.bold,
                              fontSize: 10,
                              color: DS.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ] else ...[
                  Text(
                    '点击同步闪念，发现你的行为定式',
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      fontSize: 12,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
      ),
    );
  }

  Widget _buildTag(BuildContext context, String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: DS.prismPurple.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: DS.prismPurple.withValues(alpha: 0.2)),
        ),
        child: Text(
          text,
          style: context.sparkleTypography.labelSmall.copyWith(
            fontWeight: FontWeight.bold,
            fontSize: 11,
            color: DS.textPrimary,
          ),
        ),
      );
}
