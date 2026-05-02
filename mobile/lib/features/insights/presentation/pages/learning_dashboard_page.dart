import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';
import 'package:sparkle/features/insights/presentation/providers/growth_dashboard_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/model_update_receipt.dart';

class LearningDashboardPage extends ConsumerWidget {
  const LearningDashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(growthDashboardProvider);
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(context.l10n.gdLearningDashboardTitle),
      ),
      child: ContentConstraint(
        child: dashboardAsync.when(
          data: (dashboard) => _DashboardContent(dashboard: dashboard),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _DashboardError(
            onRetry: () => ref.read(growthDashboardProvider.notifier).refresh(),
          ),
        ),
      ),
    );
  }
}

class _DashboardContent extends ConsumerWidget {
  const _DashboardContent({required this.dashboard});

  final GrowthDashboard dashboard;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasData = dashboard.timeDistribution.isNotEmpty ||
        dashboard.weaknessRadar.isNotEmpty ||
        dashboard.knowledgeChanges.isNotEmpty ||
        dashboard.efficiencyMetrics.tasksCompleted > 0;
    return RefreshIndicator(
      onRefresh: () => ref.read(growthDashboardProvider.notifier).refresh(),
      child: Semantics(
        label: context.l10n.gdDashboardSemantics,
        container: true,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing24,
          ),
          children: [
            if (!hasData)
              EmptyState(
                icon: Icons.dashboard_customize_rounded,
                title: context.l10n.gdNoDataTitle,
                description: context.l10n.gdNoDataDesc,
              ),
            _SectionCard(
              title: context.l10n.gdTimeDistribution,
              icon: Icons.bar_chart_rounded,
              child: _TimeDistributionChart(items: dashboard.timeDistribution),
            ),
            const SizedBox(height: DS.spacing12),
            _SectionCard(
              title: context.l10n.gdEfficiency,
              icon: Icons.speed_rounded,
              child: _EfficiencyPanel(metrics: dashboard.efficiencyMetrics),
            ),
            const SizedBox(height: DS.spacing12),
            _SectionCard(
              title: context.l10n.gdWeaknessRadar,
              icon: Icons.radar_rounded,
              child: _WeaknessRadar(items: dashboard.weaknessRadar),
            ),
            const SizedBox(height: DS.spacing12),
            _SectionCard(
              title: context.l10n.gdKnowledgeChanges,
              icon: Icons.trending_up_rounded,
              child: _KnowledgeChanges(items: dashboard.knowledgeChanges),
            ),
            const SizedBox(height: DS.spacing12),
            _SectionCard(
              title: context.l10n.gdPlanStability,
              icon: Icons.account_tree_rounded,
              child: _PlanStabilityPanel(stability: dashboard.planStability),
            ),
            if (dashboard.modelUpdates.isNotEmpty) ...[
              const SizedBox(height: DS.spacing12),
              ...dashboard.modelUpdates.map(
                (update) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing12),
                  child: ModelUpdateReceipt(update: update),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: colors.outlineVariant,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: colors.primary),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing14),
          child,
        ],
      ),
    );
  }
}

class _TimeDistributionChart extends StatelessWidget {
  const _TimeDistributionChart({required this.items});

  final List<TimeDistributionItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _InlineEmpty();
    }
    final colors = Theme.of(context).colorScheme;
    final maxHours = items.map((item) => item.hours).fold<double>(0, math.max);
    return Column(
      children: items.map((item) {
        final value = maxHours == 0 ? 0.0 : item.hours / maxHours;
        return Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing10),
          child: Row(
            children: [
              SizedBox(
                width: 104,
                child: Text(
                  _categoryLabel(context, item.category),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: value.clamp(0.0, 1.0),
                    minHeight: 12,
                    backgroundColor: colors.surfaceContainerHighest,
                    color: colors.primary,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.gdTimeHours(item.hours.toStringAsFixed(1)),
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
        );
      }).toList(growable: false),
    );
  }
}

class _EfficiencyPanel extends StatelessWidget {
  const _EfficiencyPanel({required this.metrics});

  final EfficiencyMetrics metrics;

  @override
  Widget build(BuildContext context) {
    final percent = (metrics.onTimeRate * 100).clamp(0, 100).toStringAsFixed(0);
    return Row(
      children: [
        SizedBox.square(
          dimension: 92,
          child: _RingMetric(
            value: metrics.onTimeRate,
            label: '$percent%',
          ),
        ),
        const SizedBox(width: DS.spacing16),
        Expanded(
          child: Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                  label: context.l10n
                      .gdTasksCompletedCount(metrics.tasksCompleted)),
              _MetricChip(
                  label: context.l10n.gdAvgMinutes(
                      metrics.avgCompletionTime.toStringAsFixed(0))),
              _MetricChip(label: context.l10n.gdOnTimeRate(percent)),
            ],
          ),
        ),
      ],
    );
  }
}

class _WeaknessRadar extends StatelessWidget {
  const _WeaknessRadar({required this.items});

  final List<WeaknessRadarItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _InlineEmpty();
    }
    final colors = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 220,
          child: CustomPaint(
            painter: _RadarPainter(
              items: items,
              color: colors.primary,
              gridColor: colors.outlineVariant,
            ),
            child: const SizedBox.expand(),
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: items
              .map(
                (item) => _MetricChip(
                  label:
                      '${item.area} · ${context.l10n.gdGap((item.gap * 100).toStringAsFixed(0))}',
                ),
              )
              .toList(growable: false),
        ),
      ],
    );
  }
}

class _KnowledgeChanges extends StatelessWidget {
  const _KnowledgeChanges({required this.items});

  final List<KnowledgeChangeItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _InlineEmpty();
    }
    final colors = Theme.of(context).colorScheme;
    return Column(
      children: items.map((item) {
        final before = (item.masteryBefore * 100).toStringAsFixed(0);
        final after = (item.masteryAfter * 100).toStringAsFixed(0);
        final improved = item.masteryAfter >= item.masteryBefore;
        return Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing10),
          child: Row(
            children: [
              Icon(
                improved
                    ? Icons.arrow_upward_rounded
                    : Icons.arrow_downward_rounded,
                color: improved ? colors.primary : colors.error,
                size: 18,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  item.nodeLabel,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.gdMasteryMove(before, after),
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: colors.onSurfaceVariant,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
        );
      }).toList(growable: false),
    );
  }
}

class _PlanStabilityPanel extends StatelessWidget {
  const _PlanStabilityPanel({required this.stability});

  final PlanStability stability;

  @override
  Widget build(BuildContext context) {
    final percent =
        (stability.abandonmentRate * 100).clamp(0, 100).toStringAsFixed(0);
    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: [
        _MetricChip(
            label: context.l10n.gdInterruptionsCount(stability.interruptions)),
        _MetricChip(
            label: context.l10n.gdAdjustmentsCount(stability.adjustments)),
        _MetricChip(label: context.l10n.gdAbandonmentRate(percent)),
      ],
    );
  }
}

class _RingMetric extends StatelessWidget {
  const _RingMetric({
    required this.value,
    required this.label,
  });

  final double value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Stack(
      alignment: Alignment.center,
      children: [
        CircularProgressIndicator(
          value: value.clamp(0.0, 1.0),
          strokeWidth: 10,
          backgroundColor: colors.surfaceContainerHighest,
          color: colors.primary,
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w900,
              ),
        ),
      ],
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: colors.secondaryContainer,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: colors.onSecondaryContainer,
              fontWeight: FontWeight.w800,
            ),
      ),
    );
  }
}

class _InlineEmpty extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Text(
      context.l10n.gdNoDataDesc,
      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
            height: 1.45,
          ),
    );
  }
}

class _DashboardError extends StatelessWidget {
  const _DashboardError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: EmptyState(
        icon: Icons.error_outline_rounded,
        title: context.l10n.gdLoadFailed,
        description: context.l10n.gdNoDataDesc,
        actionText: context.l10n.gdRetry,
        onAction: onRetry,
      ),
    );
  }
}

class _RadarPainter extends CustomPainter {
  _RadarPainter({
    required this.items,
    required this.color,
    required this.gridColor,
  });

  final List<WeaknessRadarItem> items;
  final Color color;
  final Color gridColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (items.length < 3) {
      return;
    }
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.38;
    final gridPaint = Paint()
      ..color = gridColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final fillPaint = Paint()
      ..color = color.withValues(alpha: 0.18)
      ..style = PaintingStyle.fill;
    final strokePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    for (var ring = 1; ring <= 4; ring++) {
      final ringRadius = radius * ring / 4;
      canvas.drawCircle(center, ringRadius, gridPaint);
    }

    final path = Path();
    for (var index = 0; index < items.length; index++) {
      final angle = -math.pi / 2 + index * 2 * math.pi / items.length;
      final score = items[index].currentScore.clamp(0.0, 1.0);
      final point =
          center + Offset(math.cos(angle), math.sin(angle)) * radius * score;
      final axisEnd =
          center + Offset(math.cos(angle), math.sin(angle)) * radius;
      canvas.drawLine(center, axisEnd, gridPaint);
      if (index == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();
    canvas.drawPath(path, fillPaint);
    canvas.drawPath(path, strokePaint);
  }

  @override
  bool shouldRepaint(covariant _RadarPainter oldDelegate) {
    return oldDelegate.items != items ||
        oldDelegate.color != color ||
        oldDelegate.gridColor != gridColor;
  }
}

String _categoryLabel(BuildContext context, String category) {
  return switch (category.toUpperCase()) {
    'LEARNING' => context.l10n.gdCategoryLearning,
    'TRAINING' => context.l10n.gdCategoryTraining,
    'ERROR_FIX' => context.l10n.gdCategoryErrorFix,
    'REFLECTION' => context.l10n.gdCategoryReflection,
    'SOCIAL' => context.l10n.gdCategorySocial,
    'PLANNING' => context.l10n.gdCategoryPlanning,
    'OCR' => context.l10n.gdCategoryOcr,
    _ => context.l10n.gdCategoryUnassigned,
  };
}
