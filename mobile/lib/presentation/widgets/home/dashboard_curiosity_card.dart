import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

class DashboardCuriosityCard extends ConsumerWidget {
  const DashboardCuriosityCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final cognitive = dashboardState.cognitive;

    return GestureDetector(
      onTap: () => context.push('/curiosity-capsule'),
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: AppDesignTokens.glassBackground,
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Icon(Icons.lightbulb_outline, color: AppDesignTokens.accent, size: 20),
                    if (cognitive.hasNewInsight)
                      Container(
                        width: 8,
                        height: 8,
                        decoration: const BoxDecoration(
                          color: AppDesignTokens.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                  ],
                ),
                
                const Spacer(),
                
                Text(
                  cognitive.weeklyPattern ?? '探索未知',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: DS.brandPrimaryConst,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                
                const SizedBox(height: DS.xs),
                
                Text(
                  '好奇心胶囊',
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.brandPrimary.withAlpha(150),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
