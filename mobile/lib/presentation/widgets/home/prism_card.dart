import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

/// PrismCard - Cognitive Prism Card for v2.3 dashboard
///
/// 1x1 small card displaying:
/// - Current behavior pattern keyword
/// - Breathing animation when new insights available
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
    _breathingAnimation = Tween<double>(begin: 0.3, end: 0.6).animate(
      CurvedAnimation(parent: _breathingController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _breathingController.dispose();
    super.dispose();
  }

  void _updateBreathingState(bool hasNewInsight) {
    if (hasNewInsight && !_breathingController.isAnimating) {
      _breathingController.repeat(reverse: true);
    } else if (!hasNewInsight && _breathingController.isAnimating) {
      _breathingController.stop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final cognitive = dashboardState.cognitive;
    final hasNewInsight = cognitive.hasNewInsight;
    final weeklyPattern = cognitive.weeklyPattern;

    // Update breathing animation based on new insight status
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _updateBreathingState(hasNewInsight);
    });

    return GestureDetector(
      onTap: () => context.go('/cognitive/patterns'),
      child: AnimatedBuilder(
        animation: _breathingAnimation,
        builder: (context, child) {
          return ClipRRect(
            borderRadius: AppDesignTokens.borderRadius20,
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppDesignTokens.prismPurple.withAlpha(hasNewInsight ? 60 : 30),
                      AppDesignTokens.glassBackground,
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: AppDesignTokens.borderRadius20,
                  border: Border.all(
                    color: hasNewInsight
                        ? AppDesignTokens.prismPurple.withAlpha(
                            (_breathingAnimation.value * 255).toInt(),
                          )
                        : AppDesignTokens.glassBorder,
                    width: hasNewInsight ? 1.5 : 1,
                  ),
                  boxShadow: hasNewInsight
                      ? [
                          BoxShadow(
                            color: AppDesignTokens.prismPurple.withAlpha(
                              (_breathingAnimation.value * 100).toInt(),
                            ),
                            blurRadius: 20,
                            spreadRadius: 2,
                          ),
                        ]
                      : null,
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: AppDesignTokens.prismPurple.withAlpha(40),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Icon(
                            Icons.diamond_outlined,
                            color: Colors.white,
                            size: 20,
                          ),
                        ),
                        if (hasNewInsight)
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: AppDesignTokens.prismPurple,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppDesignTokens.prismPurple.withAlpha(150),
                                  blurRadius: 8,
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),

                    const Spacer(),

                    // Pattern keyword or empty state
                    if (weeklyPattern != null) ...[
                      Text(
                        '#$weeklyPattern',
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        hasNewInsight ? '新洞察' : '本周定式',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.white.withAlpha(150),
                        ),
                      ),
                    ] else ...[
                      const Text(
                        '认知棱镜',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '记录你的想法',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.white.withAlpha(150),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
