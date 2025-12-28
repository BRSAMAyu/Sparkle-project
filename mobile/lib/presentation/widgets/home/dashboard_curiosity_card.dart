import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
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
        borderRadius: DS.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: DS.glassBackground,
              borderRadius: DS.borderRadius20,
              border: Border.all(color: DS.glassBorder),
            ),
            padding: EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Icon(Icons.lightbulb_outline, color: DS.accent, size: 20),
                    if (cognitive.hasNewInsight)
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: DS.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                  ],
                ),
                
                Spacer(),
                
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
                
                SizedBox(height: DS.xs),
                
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
