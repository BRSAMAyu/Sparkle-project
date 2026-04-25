import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

class LongTermPlanCard extends ConsumerWidget {
  const LongTermPlanCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final growth = dashboardState.growth;

    return SparklePressable(
      onTap: () => context.push(
        growth == null ? '/plans/new?type=growth' : '/growth',
      ),
      padding: EdgeInsets.zero,
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context),
        borderRadius: DS.borderRadius20,
        padding: EdgeInsets.all(
          compact ? (dense ? DS.spacing10 : DS.spacing12) : DS.lg,
        ),
        child: growth != null
            ? _buildContent(context, growth)
            : _buildEmptyState(context),
      ),
    );
  }

  Widget _buildContent(BuildContext context, GrowthData growth) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkleStaggerItem(
          index: 0,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '长期计划',
                style: TextStyle(
                  fontSize: dense ? 10 : (compact ? 11 : 12),
                  fontWeight: DS.fontWeightMedium,
                  color: DS.textSecondary,
                ),
              ),
              Icon(
                Icons.spa_rounded,
                color: DS.success,
                size: dense ? 14 : (compact ? 15 : 16),
              ),
            ],
          ),
        ),
        const Spacer(),
        Center(
          child: Column(
            children: [
              SparkleStaggerItem(
                index: 1,
                child: Text(
                  '${(growth.progress * 100).toInt()}%',
                  style: TextStyle(
                    fontSize: dense ? 16 : (compact ? 18 : 20),
                    fontWeight: FontWeight.bold,
                    color: DS.success,
                  ),
                ),
              ),
              const SizedBox(height: DS.xs),
              SparkleStaggerItem(
                index: 2,
                child: SizedBox(
                  height: 4,
                  width: compact ? 52 : 60,
                  child: LinearProgressIndicator(
                    value: growth.progress,
                    backgroundColor: isDark ? DS.neutral800 : DS.neutral200,
                    valueColor: AlwaysStoppedAnimation<Color>(DS.success),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ],
          ),
        ),
        const Spacer(),
        SparkleStaggerItem(
          index: 3,
          child: Text(
            growth.name,
            style: TextStyle(
              fontSize: dense ? 10 : (compact ? 11 : 12),
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
            maxLines: dense ? 2 : 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(height: 2),
        SparkleStaggerItem(
          index: 4,
          child: Text(
            dense
                ? '掌握 ${(growth.masteryLevel * 100).toInt()}%'
                : 'Mastery: ${(growth.masteryLevel * 100).toInt()}%',
            style: TextStyle(
              fontSize: dense ? 9 : (compact ? 9 : 10),
              color: DS.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          Icons.add_circle_outline,
          color: isDark ? DS.neutral500 : DS.neutral400,
          size: 32,
        ),
        const SizedBox(height: DS.smConst),
        Text(
          '创建长期计划',
          style: TextStyle(
            fontSize: dense ? 10 : (compact ? 11 : 12),
            color: DS.textSecondary,
          ),
        ),
      ],
    );
  }
}
