import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/domain/entities/sprint_statistics.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_statistics_provider.dart';

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
    final stats = ref.watch(sprintStatisticsProvider);

    if (stats.totalTasks == 0) {
      return _buildEmptyState(context);
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.border,
          width: 1,
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
                color: DS.brandPrimary,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '冲刺统计',
                style: context.sparkleTypography.labelLarge.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),

          // Completion rate donut chart
          _buildCompletionRateSection(context, stats),

          const SizedBox(height: DS.spacing16),

          // Task status distribution
          _buildTaskStatusSection(context, stats),

          // Daily progress chart (if data available)
          if (stats.dailyProgress.isNotEmpty) ...[
            const SizedBox(height: DS.spacing16),
            _buildDailyProgressSection(context, stats),
          ],
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: DS.border,
          width: 1,
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
              '暂无统计数据',
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );

  Widget _buildCompletionRateSection(BuildContext context, SprintStatistics stats) => Row(
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
                      '完成率',
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
                  label: '总任务',
                  value: '${stats.totalTasks} 个',
                  color: DS.textSecondary,
                ),
                const SizedBox(height: DS.spacing4),
                _buildStatRow(
                  context,
                  label: '已完成',
                  value: '${stats.completedTasks} 个',
                  color: DS.semanticSuccess,
                ),
                const SizedBox(height: DS.spacing4),
                _buildStatRow(
                  context,
                  label: '剩余',
                  value: '${stats.remainingTasks} 个',
                  color: DS.semanticWarning,
                ),
              ],
            ),
          ),
        ],
      );

  Widget _buildTaskStatusSection(BuildContext context, SprintStatistics stats) => Container(
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
              label: '待办',
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
              label: '进行中',
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
              label: '已完成',
              count: stats.completedTasks,
              color: DS.semanticSuccess,
            ),
          ),
        ],
      ),
    );

  Widget _buildDailyProgressSection(BuildContext context, SprintStatistics stats) {
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
          '每日完成',
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
              barGroups: recentProgress.asMap().entries.map((entry) {
                return BarChartGroupData(
                  x: entry.key,
                  barRods: [
                    BarChartRodData(
                      toY: entry.value.tasksCompleted.toDouble(),
                      color: DS.brandPrimary,
                      width: 16,
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(4),
                        topRight: Radius.circular(4),
                      ),
                    ),
                  ],
                );
              }).toList(),
              gridData: FlGridData(show: false),
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
                  sideTitles: SideTitles(showTitles: false),
                ),
                topTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                rightTitles: const AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
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
