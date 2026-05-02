import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class DashboardCuriosityCard extends ConsumerWidget {
  const DashboardCuriosityCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final cognitive = dashboardState.cognitive;
    final padding = compact ? (dense ? DS.spacing10 : DS.spacing12) : DS.lg;
    final iconSize = dense ? 16.0 : (compact ? 18.0 : 20.0);
    final description = cognitive.description?.trim();
    final solutionText = cognitive.solutionText?.trim();
    final snippet = (description?.isNotEmpty ?? false)
        ? description
        : (solutionText?.isNotEmpty ?? false)
            ? solutionText
            : null;

    return SparklePressable(
      onTap: () => context.push('/curiosity-capsule'),
      padding: EdgeInsets.zero,
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context),
        borderRadius: DS.borderRadius20,
        padding: EdgeInsets.all(padding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(Icons.lightbulb_outline, color: DS.accent, size: iconSize),
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
              cognitive.weeklyPattern ?? (I18nService.instance.isChinese ? '探索未知' : 'Explore the unknown'),
              style: context.sparkleTypography.labelLarge.copyWith(
                fontSize: dense ? 13 : null,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
              maxLines: dense ? 2 : (compact ? 3 : 2),
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: DS.xs),
            Text(
              I18nService.instance.isChinese ? '好奇心胶囊' : 'Curiosity Capsule',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            if (snippet != null) ...[
              SizedBox(height: dense ? DS.spacing4 : DS.spacing6),
              Text(
                snippet,
                maxLines: dense ? 2 : 3,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
