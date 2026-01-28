import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PlanDetailScreen extends ConsumerWidget {
  const PlanDetailScreen({required this.planId, super.key});
  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planAsync = ref.watch(planDetailProvider(planId));

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: const Text('计划详情'),
          actions: [
            planAsync.maybeWhen(
              data: (plan) => IconButton(
                icon: const Icon(Icons.share_outlined),
                onPressed: () => showShareResourceSheet(
                  context,
                  resourceType: 'plan',
                  resourceId: plan.id,
                  title: plan.name,
                  subtitle: plan.description ?? plan.subject ?? '',
                ),
              ),
              orElse: () => const SizedBox.shrink(),
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: '概览'),
              Tab(text: '进度'),
            ],
          ),
        ),
        body: planAsync.when(
          data: (plan) => TabBarView(
            children: [
              _PlanOverviewTab(plan: plan),
              _PlanProgressTab(plan: plan),
            ],
          ),
          loading: () => const Center(child: LoadingIndicator()),
          error: (err, _) => CustomErrorWidget.page(
            context: context,
            message: '计划加载失败：$err',
            onRetry: () => ref.refresh(planDetailProvider(planId)),
          ),
        ),
      ),
    );
  }
}

class _PlanOverviewTab extends ConsumerWidget {
  const _PlanOverviewTab({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final targetDate = plan.targetDate != null
        ? DateFormat.yMMMd().format(plan.targetDate!)
        : null;

    return ContentConstraint(
      child: ListView(
        padding: const EdgeInsets.all(DS.lg),
        children: [
          Card(
            elevation: 2,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plan.name,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  if (plan.description != null &&
                      plan.description!.isNotEmpty) ...[
                    const SizedBox(height: DS.sm),
                    Text(
                      plan.description!,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                  const SizedBox(height: DS.lg),
                  LinearProgressIndicator(
                    value: plan.progress,
                    minHeight: 8,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  const SizedBox(height: DS.sm),
                  Text('${(plan.progress * 100).toStringAsFixed(0)}% 进度'),
                  if (targetDate != null) ...[
                    const SizedBox(height: DS.md),
                    Row(
                      children: [
                        Icon(Icons.event, size: 16, color: DS.textSecondary),
                        const SizedBox(width: DS.xs),
                        Text('目标日期: $targetDate'),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: DS.lg),
          Text('相关任务', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: DS.sm),
          if (plan.tasks == null || plan.tasks!.isEmpty)
            Text('暂无任务', style: TextStyle(color: DS.textSecondary))
          else
            ...plan.tasks!.map(
              (task) => ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(task.title),
                subtitle: Text(task.status.name),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push('/tasks/${task.id}'),
              ),
            ),
          const SizedBox(height: DS.lg),
          _buildArchiveActions(context, ref),
        ],
      ),
    );
  }

  Widget _buildArchiveActions(BuildContext context, WidgetRef ref) {
    if (plan.isActive) {
      return ElevatedButton.icon(
        onPressed: () => _confirmArchive(context, ref),
        icon: const Icon(Icons.archive_outlined),
        label: const Text('归档计划'),
        style: ElevatedButton.styleFrom(
          backgroundColor: DS.error.withValues(alpha: 0.08),
          foregroundColor: DS.error,
        ),
      );
    }

    return ElevatedButton.icon(
      onPressed: () async {
        await ref.read(planListProvider.notifier).restorePlan(plan.id);
        ref.invalidate(planDetailProvider(plan.id));
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('计划已恢复')),
          );
        }
      },
      icon: const Icon(Icons.restore_rounded),
      label: const Text('恢复计划'),
    );
  }

  Future<void> _confirmArchive(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('归档计划'),
        content: const Text('归档后将从活跃列表移除，可在历史计划中恢复。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('确认归档'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    await ref.read(planListProvider.notifier).archivePlan(plan.id);
    ref.invalidate(planDetailProvider(plan.id));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('计划已归档')),
      );
    }
  }
}

class _PlanProgressTab extends StatelessWidget {
  const _PlanProgressTab({required this.plan});

  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final tasks = plan.tasks ?? [];
    if (tasks.isEmpty) {
      return const Center(child: Text('暂无可视化数据'));
    }

    final completed = tasks.where((t) => t.status == TaskStatus.completed).length;
    final total = tasks.length;
    final completionRate = total > 0 ? completed / total : 0.0;

    final byType = <TaskType, int>{};
    for (final task in tasks) {
      byType[task.type] = (byType[task.type] ?? 0) + 1;
    }

    final dayBuckets = _buildDailyCompletionBuckets(tasks);

    return ContentConstraint(
      child: ListView(
        padding: const EdgeInsets.all(DS.lg),
        children: [
          const _SectionHeader(title: '完成率'),
          const SizedBox(height: DS.spacing12),
          LayoutBuilder(
            builder: (context, constraints) {
              final chartHeight = context.isMobile ? 220.0 : 280.0;
              return SizedBox(
                height: chartHeight,
                child: PieChart(
                  PieChartData(
                    centerSpaceRadius: 60,
                    sectionsSpace: 2,
                    sections: [
                      PieChartSectionData(
                        value: completed.toDouble(),
                        title: '${(completionRate * 100).toStringAsFixed(0)}%',
                        color: DS.primaryBase,
                        radius: 55,
                        titleStyle: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                      PieChartSectionData(
                        value: (total - completed).toDouble(),
                        title: '',
                        color: DS.neutral300,
                        radius: 45,
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: DS.spacing24),
          const _SectionHeader(title: '任务类型分布'),
          const SizedBox(height: DS.spacing12),
          LayoutBuilder(
            builder: (context, constraints) {
              final chartHeight = context.isMobile ? 220.0 : 280.0;
              return SizedBox(
                height: chartHeight,
                child: BarChart(
                  BarChartData(
                    alignment: BarChartAlignment.spaceAround,
                    maxY: (byType.values.isEmpty
                            ? 1
                            : byType.values.reduce((a, b) => a > b ? a : b)) +
                        1,
                    titlesData: FlTitlesData(
                      topTitles: const AxisTitles(),
                      rightTitles: const AxisTitles(),
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 28,
                          interval: 1,
                          getTitlesWidget: (value, meta) => Text(
                            value.toInt().toString(),
                            style: TextStyle(color: DS.neutral500, fontSize: 10),
                          ),
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          getTitlesWidget: (value, meta) {
                            final label =
                                _taskTypeLabel(_taskTypes[value.toInt()]);
                            return Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                label,
                                style: TextStyle(
                                    color: DS.neutral500, fontSize: 10),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    gridData: FlGridData(
                      horizontalInterval: 1,
                      getDrawingHorizontalLine: (value) => FlLine(
                        color: DS.neutral200,
                        strokeWidth: 1,
                      ),
                    ),
                    borderData: FlBorderData(show: false),
                    barGroups: List.generate(
                      _taskTypes.length,
                      (index) {
                        final type = _taskTypes[index];
                        final count = byType[type] ?? 0;
                        return BarChartGroupData(
                          x: index,
                          barRods: [
                            BarChartRodData(
                              toY: count.toDouble(),
                              color: DS.brandPrimaryConst,
                              borderRadius: BorderRadius.circular(6),
                              width: 16,
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: DS.spacing24),
          const _SectionHeader(title: '每日完成趋势'),
          const SizedBox(height: DS.spacing12),
          LayoutBuilder(
            builder: (context, constraints) {
              final chartHeight = context.isMobile ? 220.0 : 280.0;
              return SizedBox(
                height: chartHeight,
                child: LineChart(
                  LineChartData(
                    titlesData: FlTitlesData(
                      topTitles: const AxisTitles(),
                      rightTitles: const AxisTitles(),
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 28,
                          interval: 1,
                          getTitlesWidget: (value, meta) => Text(
                            value.toInt().toString(),
                            style: TextStyle(color: DS.neutral500, fontSize: 10),
                          ),
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          interval: 1,
                          getTitlesWidget: (value, meta) {
                            final index = value.toInt();
                            if (index < 0 || index >= dayBuckets.length) {
                              return const SizedBox.shrink();
                            }
                            return Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                dayBuckets[index].label,
                                style: TextStyle(
                                    color: DS.neutral500, fontSize: 10),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    gridData: FlGridData(
                      horizontalInterval: 1,
                      getDrawingHorizontalLine: (value) => FlLine(
                        color: DS.neutral200,
                        strokeWidth: 1,
                      ),
                    ),
                    borderData: FlBorderData(show: false),
                    lineBarsData: [
                      LineChartBarData(
                        spots: [
                          for (var i = 0; i < dayBuckets.length; i++)
                            FlSpot(
                              i.toDouble(),
                              dayBuckets[i].count.toDouble(),
                            ),
                        ],
                        isCurved: true,
                        color: DS.secondaryBase,
                        barWidth: 3,
                        belowBarData: BarAreaData(
                          show: true,
                          color: DS.secondaryBase.withValues(alpha: 0.2),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  List<_DayBucket> _buildDailyCompletionBuckets(List<TaskModel> tasks) {
    final now = DateTime.now();
    final buckets = List.generate(7, (index) {
      final day = DateTime(now.year, now.month, now.day)
          .subtract(Duration(days: 6 - index));
      return _DayBucket(label: DateFormat.Md().format(day), date: day);
    });

    for (final task in tasks) {
      if (task.completedAt == null) continue;
      final completedDate = DateTime(
        task.completedAt!.year,
        task.completedAt!.month,
        task.completedAt!.day,
      );
      for (final bucket in buckets) {
        if (bucket.date == completedDate) {
          bucket.count += 1;
          break;
        }
      }
    }

    return buckets;
  }

  static const _taskTypes = [
    TaskType.learning,
    TaskType.training,
    TaskType.errorFix,
    TaskType.reflection,
    TaskType.social,
    TaskType.planning,
  ];

  String _taskTypeLabel(TaskType type) {
    switch (type) {
      case TaskType.learning:
        return '学习';
      case TaskType.training:
        return '训练';
      case TaskType.errorFix:
        return '纠错';
      case TaskType.reflection:
        return '复盘';
      case TaskType.social:
        return '社交';
      case TaskType.planning:
        return '规划';
    }
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: 4,
            height: 16,
            decoration: BoxDecoration(
              color: DS.primaryBase,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ],
      );
}

class _DayBucket {
  _DayBucket({
    required this.label,
    required this.date,
  });

  final String label;
  final DateTime date;
  int count = 0;
}
