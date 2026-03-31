import 'dart:async';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/services/plan_description_codec.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_path_progress_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/learning_path_progress_bar.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PlanDetailScreen extends ConsumerWidget {
  const PlanDetailScreen({required this.planId, super.key});
  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final planAsync = ref.watch(planDetailProvider(planId));

    return DefaultTabController(
      length: 2,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(l10n.planDetailTitle),
          actions: [
            planAsync.maybeWhen(
              data: (plan) => Tooltip(
                message: l10n.planShare,
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  icon: const Icon(Icons.share_outlined),
                  onPressed: () => unawaited(_showShareSheet(context, plan)),
                ),
              ),
              orElse: () => const SizedBox.shrink(),
            ),
            planAsync.maybeWhen(
              data: (plan) => Tooltip(
                message: '编辑计划',
                child: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  icon: const Icon(Icons.edit_outlined),
                  onPressed: () => context.push('/plans/${plan.id}/edit'),
                ),
              ),
              orElse: () => const SizedBox.shrink(),
            ),
          ],
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.planTabOverview),
              Tab(text: l10n.planTabProgress),
            ],
          ),
        ),
        child: planAsync.when(
          data: (plan) => TabBarView(
            children: [
              _PlanOverviewTab(plan: plan),
              _PlanProgressTab(plan: plan),
            ],
          ),
          loading: () => const Center(child: LoadingIndicator()),
          error: (err, _) => CustomErrorWidget.page(
            context: context,
            message: l10n.planLoadFailed(err.toString()),
            onRetry: () => ref.refresh(planDetailProvider(planId)),
          ),
        ),
      ),
    );
  }

  Future<void> _showShareSheet(BuildContext context, PlanModel plan) async {
    final tasks = plan.tasks ?? const <TaskModel>[];
    final completedTasks =
        tasks.where((task) => task.status == TaskStatus.completed).length;

    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: ShareableContentType.planProgress,
        resourceId: plan.id,
        title: plan.name,
        subtitle: plan.description ?? plan.subject ?? '',
        description: plan.description,
        metadata: {
          'progress': plan.progress,
          'completed_tasks': completedTasks,
          'total_tasks': tasks.length,
          'deadline': plan.targetDate?.toIso8601String(),
          'subject': plan.subject,
        },
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
    );
  }
}

class _PlanOverviewTab extends ConsumerWidget {
  const _PlanOverviewTab({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final targetDate = plan.targetDate != null
        ? Formatters.formatDateMedium(plan.targetDate!)
        : null;
    final parsedDescription = PlanDescriptionCodec.parse(plan.description);

    return ContentConstraint(
      child: ListView(
        padding: const EdgeInsets.all(DS.lg),
        children: [
          if (plan.source == 'learning_path') ...[
            Consumer(
              builder: (context, ref, child) {
                final progressAsync = ref.watch(
                  learningPathProgressProvider(plan.id),
                );
                return progressAsync.when(
                  data: (progress) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.lg),
                    child: LearningPathProgressBar(progress: progress),
                  ),
                  loading: () => const Padding(
                    padding: EdgeInsets.only(bottom: DS.lg),
                    child: Center(child: LoadingIndicator()),
                  ),
                  error: (err, _) => const SizedBox.shrink(),
                );
              },
            ),
          ],
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _PlanMetaChip(
                      icon: Icons.flag_outlined,
                      label: plan.subject ?? l10n.planTabOverview,
                    ),
                    _PlanMetaChip(
                      icon: Icons.task_alt_rounded,
                      label:
                          '${plan.tasks?.where((task) => task.status == TaskStatus.completed).length ?? 0}/${plan.tasks?.length ?? 0} 任务',
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  plan.name,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                if (parsedDescription.overview.isNotEmpty) ...[
                  const SizedBox(height: DS.sm),
                  Text(
                    parsedDescription.overview,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ] else if (plan.description != null &&
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
                Text(
                  l10n.planProgressPercent(
                    (plan.progress * 100).toStringAsFixed(0),
                  ),
                ),
                if (targetDate != null) ...[
                  const SizedBox(height: DS.md),
                  Row(
                    children: [
                      Icon(Icons.event, size: 16, color: DS.textSecondary),
                      const SizedBox(width: DS.xs),
                      Text(l10n.planTargetDate(targetDate)),
                    ],
                  ),
                ],
              ],
            ),
          ),
          if (parsedDescription.hasStructuredSections) ...[
            const SizedBox(height: DS.lg),
            if (parsedDescription.schedule.isNotEmpty)
              _PlanRichSection(
                title: '每日节奏',
                icon: Icons.schedule_rounded,
                content: parsedDescription.schedule,
              ),
            if (parsedDescription.scope.isNotEmpty)
              _PlanRichSection(
                title: '计划边界',
                icon: Icons.rule_folder_outlined,
                content: parsedDescription.scope,
              ),
            if (parsedDescription.taskBlueprint.isNotEmpty)
              _PlanRichSection(
                title: '任务编排',
                icon: Icons.account_tree_outlined,
                content: parsedDescription.taskBlueprint,
              ),
            if (parsedDescription.guide.isNotEmpty)
              _PlanRichSection(
                title: 'AI执行指南',
                icon: Icons.auto_awesome_rounded,
                content: parsedDescription.guide,
              ),
          ],
          const SizedBox(height: DS.lg),
          Row(
            children: [
              Expanded(
                child: Text(
                  l10n.planRelatedTasks,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              SparkleButton.ghost(
                onPressed: () => context.push(
                  '/tasks/new?planId=${plan.id}&planName=${Uri.encodeComponent(plan.name)}',
                ),
                icon: const Icon(Icons.add_task_rounded),
                label: '新增计划任务',
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          if (plan.tasks == null || plan.tasks!.isEmpty)
            Text(l10n.planNoTasks, style: TextStyle(color: DS.textSecondary))
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
      return SparkleButton.destructive(
        onPressed: () => _confirmArchive(context, ref),
        icon: const Icon(Icons.archive_outlined),
        label: context.l10n.planArchive,
      );
    }

    return SparkleButton(
      onPressed: () async {
        await ref.read(planListProvider.notifier).restorePlan(plan.id);
        ref.invalidate(planDetailProvider(plan.id));
        if (context.mounted) {
          AppFeedback.success(context, context.l10n.planRestoredSuccess);
        }
      },
      icon: const Icon(Icons.restore_rounded),
      label: context.l10n.planRestore,
    );
  }

  Future<void> _confirmArchive(BuildContext context, WidgetRef ref) async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: GraphiteModalSurface(
          title: context.l10n.planArchiveTitle,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.planArchiveMessage,
                style: Theme.of(dialogContext).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      onPressed: () => Navigator.of(dialogContext).pop(false),
                      label: context.l10n.cancel,
                      expand: true,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: SparkleButton(
                      onPressed: () => Navigator.of(dialogContext).pop(true),
                      label: context.l10n.planArchiveConfirm,
                      expand: true,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );

    if (confirmed != true) return;

    await ref.read(planListProvider.notifier).archivePlan(plan.id);
    ref.invalidate(planDetailProvider(plan.id));
    if (context.mounted) {
      AppFeedback.success(context, context.l10n.planArchivedSuccess);
    }
  }
}

class _PlanMetaChip extends StatelessWidget {
  const _PlanMetaChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
      );
}

class _PlanRichSection extends StatelessWidget {
  const _PlanRichSection({
    required this.title,
    required this.icon,
    required this.content,
  });

  final String title;
  final IconData icon;
  final String content;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing16),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 18, color: DS.brandPrimaryConst),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              SelectableText(
                content,
                style: DS.bodyMedium.copyWith(height: 1.6),
              ),
            ],
          ),
        ),
      );
}

class _PlanProgressTab extends StatelessWidget {
  const _PlanProgressTab({required this.plan});

  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final tasks = plan.tasks ?? [];
    if (tasks.isEmpty) {
      return Center(child: Text(l10n.planNoVisualizationData));
    }

    final completed =
        tasks.where((t) => t.status == TaskStatus.completed).length;
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
          _SectionHeader(title: l10n.planSectionCompletionRate),
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
                        titleStyle: TextStyle(
                          color: DS.textOnPrimary,
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
          _SectionHeader(title: l10n.planSectionTaskTypeDistribution),
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
                            style:
                                TextStyle(color: DS.neutral500, fontSize: 10),
                          ),
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          getTitlesWidget: (value, meta) {
                            final label =
                                _taskTypeLabel(l10n, _taskTypes[value.toInt()]);
                            return Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                label,
                                style: TextStyle(
                                  color: DS.neutral500,
                                  fontSize: 10,
                                ),
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
          _SectionHeader(title: l10n.planSectionDailyCompletion),
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
                            style:
                                TextStyle(color: DS.neutral500, fontSize: 10),
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
                                  color: DS.neutral500,
                                  fontSize: 10,
                                ),
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
      return _DayBucket(label: Formatters.formatDateMonthDay(day), date: day);
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

  String _taskTypeLabel(AppLocalizations l10n, TaskType type) {
    switch (type) {
      case TaskType.learning:
        return l10n.taskTypeLearning;
      case TaskType.training:
        return l10n.taskTypeTraining;
      case TaskType.errorFix:
        return l10n.taskTypeFix;
      case TaskType.reflection:
        return l10n.taskTypeReflection;
      case TaskType.social:
        return l10n.taskTypeSocial;
      case TaskType.planning:
        return l10n.taskTypePlanning;
      case TaskType.ocr:
        return l10n.taskTypeOcr;
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
