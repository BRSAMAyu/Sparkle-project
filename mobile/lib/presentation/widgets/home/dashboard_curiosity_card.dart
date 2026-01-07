import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
      child: MaterialStyler(
        material: AppMaterials.ceramic,
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.lg),
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
            const Spacer(),
            Text(
              cognitive.weeklyPattern ?? '探索未知',
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: FontWeight.bold,
                color: DS.textPrimary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: DS.xs),
            Text(
              '好奇心胶囊',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.brandPrimary.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
