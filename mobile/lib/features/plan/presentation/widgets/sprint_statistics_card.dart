import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/plan/domain/entities/sprint_statistics.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_statistics_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Sprint statistics card widget
///
/// Displays visual statistics for the current sprint including:
/// - Completion rate donut chart
/// - Task status distribution
/// - Daily progress bar chart
class SprintStatisticsCard extends ConsumerWidget {
  const SprintStatisticsCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final stats = ref.watch(sprintStatisticsProvider);

    if (stats.totalTasks == 0) {
      return _buildEmptyState(context, l10n);
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.bar_chart_rounded,
                size: DS.iconSizeSm,
                color: DS.brandPrimaryConst,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                l10n.sprintStatsTitle,
                style: context.sparkleTypography.labelLarge.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // Completion rate donut chart
          _buildCompletionRateSection(context, l10n, stats),

          const SizedBox(height: DS.spacing16),

          // Task status distribution
          _buildTaskStatusSection(context, l10n, stats),

          // Daily progress chart (if data available)
          if (stats.dailyProgress.isNotEmpty) ...[
            const SizedBox(height: DS.spacing16),
            _buildDailyProgressSection(context, l10n, stats),
          ],
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, AppLocalizations l10n) =>
      Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.border,
        ),
      ),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.bar_chart_rounded,
              size: 32,
              color: DS.textSecondary.withValues(alpha: 0.5),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.sprintStatsEmpty,
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );

  Widget _buildCompletionRateSection(
    BuildContext context,
    AppLocalizations l10n,
    SprintStatistics stats,
  ) =>
      Row(
        children: [
          // Donut chart
          SizedBox(
            width: 80,
            height: 80,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 80,
                  height: 80,
                  child: PieChart(
                    PieChartData(
                      sectionsSpace: 0,
                      centerSpaceRadius: 28,
                      sections: [
                        PieChartSectionData(
                          value: stats.completionRate * 100,
                          color: _getCompletionRateColor(stats.completionRate),
                          radius: 32,
                          showTitle: false,
                        ),
                        PieChartSectionData(
                          value: (1 - stats.completionRate) * 100,
                          color: DS.surfaceTertiary,
                          radius: 32,
                          showTitle: false,
                        ),
                      ],
                    ),
                  ),
                ),
                // Center percentage
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${(stats.completionRate * 100).toInt()}%',
                      style: context.sparkleTypography.labelLarge.copyWith(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      l10n.sprintCompletionRate,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        fontSize: 8,
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: DS.spacing16),
          // Stats details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildStatRow(
                  context,
                  label: l10n.sprintTotalTasks,
                  value: l10n.sprintTaskCount(stats.totalTasks),
                  color: DS.textSecondary,
                ),
                const SizedBox(height: DS.spacing4),
                _buildStatRow(
                  context,
                  label: l10n.sprintCompletedTasks,
                  value: l10n.sprintTaskCount(stats.completedTasks),
                  color: DS.semanticSuccess,
                ),
                const SizedBox(height: DS.spacing4),
                _buildStatRow(
                  context,
                  label: l10n.sprintRemainingTasks,
                  value: l10n.sprintTaskCount(stats.remainingTasks),
                  color: DS.semanticWarning,
                ),
              ],
            ),
          ),
        ],
      );

  Widget _buildTaskStatusSection(
    BuildContext context,
    AppLocalizations l10n,
    SprintStatistics stats,
  ) =>
      Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: DS.borderRadius8,
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildStatusItem(
              context,
              label: l10n.sprintStatusTodo,
              count: stats.todoTasks,
              color: DS.semanticWarning,
            ),
          ),
          Container(
            width: 1,
            height: 24,
            color: DS.border,
          ),
          Expanded(
            child: _buildStatusItem(
              context,
              label: l10n.sprintStatusInProgress,
              count: stats.inProgressTasks,
              color: DS.info,
            ),
          ),
          Container(
            width: 1,
            height: 24,
            color: DS.border,
          ),
          Expanded(
            child: _buildStatusItem(
              context,
              label: l10n.sprintStatusCompleted,
              count: stats.completedTasks,
              color: DS.semanticSuccess,
            ),
          ),
        ],
      ),
    );

  Widget _buildDailyProgressSection(
    BuildContext context,
    AppLocalizations l10n,
    SprintStatistics stats,
  ) {
    // Show last 7 days of progress
    final recentProgress = stats.dailyProgress.length > 7
        ? stats.dailyProgress.sublist(stats.dailyProgress.length - 7)
        : stats.dailyProgress;

    final maxValue = recentProgress.isNotEmpty
        ? recentProgress.map((d) => d.tasksCompleted).reduce((a, b) => a > b ? a : b)
        : 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.sprintDailyCompletion,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        SizedBox(
          height: 60,
          child: BarChart(
            BarChartData(
              alignment: BarChartAlignment.spaceAround,
              maxY: (maxValue + 1).toDouble(),
              minY: 0,
              barGroups: recentProgress.asMap().entries.map((entry) => BarChartGroupData(
                  x: entry.key,
                  barRods: [
                    BarChartRodData(
                      toY: entry.value.tasksCompleted.toDouble(),
                      color: DS.brandPrimaryConst,
                      width: 16,
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(4),
                        topRight: Radius.circular(4),
                      ),
                    ),
                  ],
                ),).toList(),
              gridData: const FlGridData(show: false),
              titlesData: FlTitlesData(
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (value, meta) {
                      final index = value.toInt();
                      if (index >= 0 && index < recentProgress.length) {
                        final date = recentProgress[index].date;
                        return Text(
                          '${date.month}/${date.day}',
                          style: TextStyle(
                            fontSize: 8,
                            color: DS.textSecondary,
                          ),
                        );
                      }
                      return const Text('');
                    },
                    reservedSize: 24,
                  ),
                ),
                leftTitles: const AxisTitles(
                  
                ),
                topTitles: const AxisTitles(
                  
                ),
                rightTitles: const AxisTitles(
                  
                ),
              ),
              borderData: FlBorderData(show: false),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatRow(
    BuildContext context, {
    required String label,
    required String value,
    required Color color,
  }) =>
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: color,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      );

  Widget _buildStatusItem(
    BuildContext context, {
    required String label,
    required int count,
    required Color color,
  }) =>
      Column(
        children: [
          Text(
            count.toString(),
            style: context.sparkleTypography.labelLarge.copyWith(
              color: color,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
              fontSize: 10,
            ),
          ),
        ],
      );

  Color _getCompletionRateColor(double rate) {
    if (rate >= 0.75) return DS.semanticSuccess;
    if (rate >= 0.5) return DS.info;
    if (rate >= 0.25) return DS.semanticWarning;
    return DS.semanticError;
  }
}
