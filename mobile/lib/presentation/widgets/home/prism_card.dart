import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

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
    )..repeat(reverse: true);
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
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppDesignTokens.prismPurple.withAlpha(40),
                  AppDesignTokens.glassBackground,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: const EdgeInsets.all(DS.lg),
            child: Stack(
              children: [
                // Prism refraction effect (animated)
                Positioned(
                  right: -20,
                  bottom: -20,
                  child: AnimatedBuilder(
                    animation: _breathingAnimation,
                    builder: (context, child) => Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              AppDesignTokens.prismPurple.withValues(alpha: _breathingAnimation.value),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                  ),
                ),
                
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.diamond_outlined, color: DS.brandPrimary, size: 18),
                        const SizedBox(width: DS.sm),
                        const Text(
                          '认知棱镜',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: DS.brandPrimary,
                          ),
                        ),
                        const Spacer(),
                        if (cognitive.hasNewInsight)
                          Container(
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              color: AppDesignTokens.prismPurple,
                              shape: BoxShape.circle,
                            ),
                          ),
                      ],
                    ),
                    const Spacer(),
                    if (weeklyPattern != null) ...[
                      Wrap(
                        spacing: 8,
                        children: [
                          _buildTag('#$weeklyPattern'),
                          if (dashboardState.weather.type == 'rainy') _buildTag('#焦虑波峰'),
                        ],
                      ),
                      const SizedBox(height: DS.xs),
                      Text(
                        '行为定式分析已更新',
                        style: TextStyle(
                          fontSize: 11,
                          color: DS.brandPrimary.withAlpha(150),
                        ),
                      ),
                    ] else ...[
                      const Text(
                        '点击同步闪念，发现你的行为定式',
                        style: TextStyle(
                          fontSize: 12,
                          color: DS.brandPrimary70,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTag(String text) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withAlpha(20),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.brandPrimary.withAlpha(30)),
      ),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: DS.brandPrimary,
        ),
      ),
    );
}
