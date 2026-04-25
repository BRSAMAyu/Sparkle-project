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
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/services/plan_description_codec.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_path_progress_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_phase_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/learning_path_progress_bar.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/widgets/card_picker_sheet.dart';

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
          const SizedBox(height: DS.lg),
          _PlanExecutionSection(
            plan: plan,
            onAddNewTask: () => context.push(
              '/tasks/new?planId=${plan.id}&planName=${Uri.encodeComponent(plan.name)}',
            ),
            onAddExistingTask: () =>
                unawaited(_showAddExistingTaskPicker(context, ref)),
          ),
          const SizedBox(height: DS.lg),
          _PlanPhaseSection(plan: plan),
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

  Future<void> _showAddExistingTaskPicker(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final tasks = <TaskModel>[...ref.read(taskListProvider).tasks];
    if (tasks.isEmpty) {
      try {
        final response =
            await ref.read(taskRepositoryProvider).getTasks(pageSize: 100);
        tasks.addAll(response.items);
      } catch (e) {
        if (!context.mounted) return;
        AppFeedback.error(context, 'Failed to load tasks: $e');
        return;
      }
    }

    if (!context.mounted) return;

    final candidateTasks = tasks
        .where((task) => task.planId != plan.id)
        .toList()
      ..sort((a, b) => a.title.compareTo(b.title));

    if (candidateTasks.isEmpty) {
      AppFeedback.info(context, 'No unassigned or external tasks available');
      return;
    }

    final selectedTaskId = await CardPickerSheet.show(
      context,
      title: 'Add existing task to this plan',
      options: candidateTasks
          .map(
            (task) => CardPickerOption(
              id: task.id,
              title: task.title,
              subtitle: task.planId == null
                  ? 'Unassigned'
                  : 'Currently in another plan',
              group: task.planId == null
                  ? 'Unassigned tasks'
                  : 'Tasks from other plans',
              icon: Icons.task_alt_rounded,
            ),
          )
          .toList(),
    );

    if (!context.mounted || selectedTaskId == null) return;
    final selectedTask = candidateTasks.firstWhere(
      (task) => task.id == selectedTaskId,
    );

    try {
      await ref.read(taskListProvider.notifier).moveTaskToPlan(
            selectedTask.id,
            plan.id,
            previousPlanId: selectedTask.planId,
          );
      if (!context.mounted) return;
      ref.invalidate(planDetailProvider(plan.id));
      AppFeedback.success(context, 'Task added to plan');
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(context, 'Add task failed: $e');
    }
  }
}

class _PlanExecutionSection extends StatelessWidget {
  const _PlanExecutionSection({
    required this.plan,
    required this.onAddNewTask,
    required this.onAddExistingTask,
  });

  final PlanModel plan;
  final VoidCallback onAddNewTask;
  final VoidCallback onAddExistingTask;

  @override
  Widget build(BuildContext context) {
    final tasks = _mergedPlanTasks(plan);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Expanded(child: _SectionHeader(title: '今日聚焦')),
            if (!context.isMobile)
              _PlanTaskActions(
                onAddNewTask: onAddNewTask,
                onAddExistingTask: onAddExistingTask,
              ),
          ],
        ),
        if (context.isMobile) ...[
          const SizedBox(height: DS.spacing12),
          _PlanTaskActions(
            onAddNewTask: onAddNewTask,
            onAddExistingTask: onAddExistingTask,
          ),
        ],
        const SizedBox(height: DS.spacing12),
        if (tasks.isEmpty)
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Text(
              context.l10n.planNoTasks,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          )
        else ...[
          _TodayFocusPlan(plan: plan, tasks: tasks),
          const SizedBox(height: DS.spacing20),
          _ExpandableFullPlan(plan: plan, tasks: tasks),
        ],
      ],
    );
  }
}

class _PlanTaskActions extends StatelessWidget {
  const _PlanTaskActions({
    required this.onAddNewTask,
    required this.onAddExistingTask,
  });

  final VoidCallback onAddNewTask;
  final VoidCallback onAddExistingTask;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: [
          SparkleButton.ghost(
            onPressed: onAddNewTask,
            icon: const Icon(Icons.add_task_rounded),
            label: '新增任务',
          ),
          SparkleButton.ghost(
            onPressed: onAddExistingTask,
            icon: const Icon(Icons.playlist_add_rounded),
            label: '添加已有',
          ),
        ],
      );
}

class _TodayFocusPlan extends StatelessWidget {
  const _TodayFocusPlan({required this.plan, required this.tasks});

  final PlanModel plan;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context) {
    final groups = _buildPlanDayGroups(tasks);
    final highlightDay = _highlightDay(plan, groups);
    final highlightedTasks = _highlightTasks(plan, groups, highlightDay);
    final recommendation = _highlightRecommendation(
      plan,
      highlightedTasks,
      highlightDay,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.18)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing8),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 18,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  recommendation,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: DS.textPrimary,
                        height: 1.45,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: DS.spacing12),
        ...highlightedTasks.asMap().entries.map(
              (entry) => Padding(
                padding: EdgeInsets.only(
                  bottom: entry.key == highlightedTasks.length - 1
                      ? 0
                      : DS.spacing12,
                ),
                child: _TodayTaskCard(
                  task: entry.value,
                  sequence: entry.key + 1,
                ),
              ),
            ),
      ],
    );
  }
}

class _TodayTaskCard extends StatelessWidget {
  const _TodayTaskCard({required this.task, required this.sequence});

  final TaskModel task;
  final int sequence;

  @override
  Widget build(BuildContext context) {
    final statusColor = _taskStatusColor(task.status);

    return GraphiteCardSurface(
      onTap: () => context.push('/tasks/${task.id}'),
      borderColor: statusColor.withValues(alpha: 0.32),
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(DS.spacing18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(17),
                ),
                child: task.status == TaskStatus.completed
                    ? Icon(Icons.check_rounded, color: statusColor, size: 20)
                    : Text(
                        '$sequence',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: statusColor,
                                  fontWeight: FontWeight.w800,
                                ),
                      ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  task.title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                        height: 1.25,
                      ),
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: DS.textSecondary),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          _WhyNowNote(text: _taskWhyNow(task)),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _TaskMetaPill(
                icon: Icons.schedule_rounded,
                label: '${task.estimatedMinutes} 分钟',
              ),
              _TaskMetaPill(
                icon: Icons.bolt_rounded,
                label: '难度 ${task.difficulty}',
              ),
              _TaskMetaPill(
                icon: _taskStatusIcon(task.status),
                label: _taskStatusLabel(task.status),
                color: statusColor,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ExpandableFullPlan extends StatelessWidget {
  const _ExpandableFullPlan({required this.plan, required this.tasks});

  final PlanModel plan;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context) {
    final groups = _buildPlanDayGroups(tasks);
    final highlightDay = _highlightDay(plan, groups);
    final futureGroups =
        groups.where((group) => group.day != highlightDay).toList();
    if (futureGroups.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionHeader(title: '完整计划'),
        const SizedBox(height: DS.spacing12),
        ...futureGroups.map(
          (group) => Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing10),
            child: _PlanDayExpansion(group: group),
          ),
        ),
      ],
    );
  }
}

class _PlanDayExpansion extends StatelessWidget {
  const _PlanDayExpansion({required this.group});

  final _PlanDayGroup group;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing4,
          ),
          childrenPadding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing12,
          ),
          shape: const Border(),
          collapsedShape: const Border(),
          title: Text(
            'Day ${group.day}',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          subtitle: Text(
            '${group.tasks.length} 件 · ${group.totalMinutes} 分钟',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          children: group.tasks
              .map(
                (task) => _CompactPlanTaskTile(task: task),
              )
              .toList(),
        ),
      );
}

class _CompactPlanTaskTile extends StatelessWidget {
  const _CompactPlanTaskTile({required this.task});

  final TaskModel task;

  @override
  Widget build(BuildContext context) {
    final statusColor = _taskStatusColor(task.status);

    return InkWell(
      onTap: () => context.push('/tasks/${task.id}'),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  _taskStatusIcon(task.status),
                  size: 18,
                  color: statusColor,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    task.title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: DS.fontWeightBold,
                          height: 1.35,
                        ),
                  ),
                ),
                const Icon(Icons.chevron_right_rounded, size: 18),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Padding(
              padding: const EdgeInsets.only(left: 26),
              child: Text(
                _taskWhyNow(task),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.35,
                    ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WhyNowNote extends StatelessWidget {
  const _WhyNowNote({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceTertiary.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.psychology_alt_rounded,
              size: 17,
              color: DS.textSecondary,
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                text,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ),
          ],
        ),
      );
}

class _TaskMetaPill extends StatelessWidget {
  const _TaskMetaPill({
    required this.icon,
    required this.label,
    this.color,
  });

  final IconData icon;
  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final resolvedColor = color ?? DS.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: resolvedColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: resolvedColor),
          const SizedBox(width: DS.spacing6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: resolvedColor,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
        ],
      ),
    );
  }
}

class _PlanDayGroup {
  _PlanDayGroup({required this.day, required this.tasks});

  final int day;
  final List<TaskModel> tasks;

  int get totalMinutes =>
      tasks.fold<int>(0, (sum, task) => sum + task.estimatedMinutes);
}

List<TaskModel> _mergedPlanTasks(PlanModel plan) {
  final merged = <TaskModel>[];
  final seen = <String>{};

  void addTask(TaskModel task) {
    if (seen.add(task.id)) merged.add(task);
  }

  (plan.tasks ?? const <TaskModel>[]).forEach(addTask);
  (plan.dayHighlights?.tasks ?? const <TaskModel>[]).forEach(addTask);

  merged.sort(
    (a, b) {
      final byOrder = a.orderIndex.compareTo(b.orderIndex);
      if (byOrder != 0) return byOrder;
      return a.createdAt.compareTo(b.createdAt);
    },
  );
  return merged;
}

List<_PlanDayGroup> _buildPlanDayGroups(List<TaskModel> tasks) {
  final groups = <int, List<TaskModel>>{};
  for (final task in tasks) {
    groups.putIfAbsent(_taskDay(task), () => <TaskModel>[]).add(task);
  }
  final result = groups.entries
      .map((entry) => _PlanDayGroup(day: entry.key, tasks: entry.value))
      .toList()
    ..sort((a, b) => a.day.compareTo(b.day));
  for (final group in result) {
    group.tasks.sort(
      (a, b) {
        final byOrder = a.orderIndex.compareTo(b.orderIndex);
        if (byOrder != 0) return byOrder;
        return a.createdAt.compareTo(b.createdAt);
      },
    );
  }
  return result;
}

int _taskDay(TaskModel task) {
  if (task.orderIndex >= 1000) {
    return task.orderIndex ~/ 1000;
  }
  for (final tag in task.tags) {
    if (!tag.startsWith('day:')) continue;
    final parsed = int.tryParse(tag.substring(4));
    if (parsed != null && parsed > 0) return parsed;
  }
  return 1;
}

int _highlightDay(PlanModel plan, List<_PlanDayGroup> groups) {
  final serverDay = plan.dayHighlights?.day;
  if (serverDay != null && serverDay > 0) return serverDay;
  if (groups.any((group) => group.day == 1)) return 1;
  return groups.isEmpty ? 1 : groups.first.day;
}

List<TaskModel> _highlightTasks(
  PlanModel plan,
  List<_PlanDayGroup> groups,
  int day,
) {
  final serverTasks = plan.dayHighlights?.tasks ?? const <TaskModel>[];
  if (serverTasks.isNotEmpty) return serverTasks;
  return groups
      .firstWhere(
        (group) => group.day == day,
        orElse: () => groups.isEmpty
            ? _PlanDayGroup(day: day, tasks: const <TaskModel>[])
            : groups.first,
      )
      .tasks;
}

String _highlightRecommendation(
  PlanModel plan,
  List<TaskModel> tasks,
  int day,
) {
  final serverText = plan.dayHighlights?.recommendation.trim();
  if (serverText != null && serverText.isNotEmpty) return serverText;
  final thingLabel = tasks.length == 1 ? '这 1 件事' : '这 ${tasks.length} 件事';
  if (day == 1) {
    return '今天先做好$thingLabel，你已经走在正确路上了。';
  }
  return '先看 Day $day 的$thingLabel，把节奏稳稳接上。';
}

String _taskWhyNow(TaskModel task) {
  final guide = task.guideJson;
  final whyNow = guide == null ? '' : '${guide['why_now'] ?? ''}'.trim();
  if (whyNow.isNotEmpty) return whyNow;
  switch (task.type) {
    case TaskType.learning:
      return '现在先处理它，是为了把今天的学习推进变成一个看得见的输出。';
    case TaskType.training:
      return '现在做练习，能尽快确认刚学的内容是不是真的会用。';
    case TaskType.errorFix:
      return '现在修这个错因，能避免后面的任务被同一个漏洞反复拖住。';
    case TaskType.reflection:
      return '现在复盘，能把今天的结果转成明天更轻的选择。';
    case TaskType.social:
      return '现在完成协作动作，能让外部反馈及时接进你的学习节奏。';
    case TaskType.planning:
      return '现在整理计划，能让下一步执行少一点犹豫。';
    case TaskType.ocr:
      return '现在处理资料，能先把可用信息变成后续任务的入口。';
  }
}

String _taskStatusLabel(TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return '待开始';
    case TaskStatus.inProgress:
      return '进行中';
    case TaskStatus.completed:
      return '已完成';
    case TaskStatus.abandoned:
      return '已放弃';
  }
}

IconData _taskStatusIcon(TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return Icons.radio_button_unchecked_rounded;
    case TaskStatus.inProgress:
      return Icons.play_circle_outline_rounded;
    case TaskStatus.completed:
      return Icons.check_circle_rounded;
    case TaskStatus.abandoned:
      return Icons.pause_circle_outline_rounded;
  }
}

Color _taskStatusColor(TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return DS.brandPrimary;
    case TaskStatus.inProgress:
      return DS.info;
    case TaskStatus.completed:
      return DS.success;
    case TaskStatus.abandoned:
      return DS.textSecondary;
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
                    fontWeight: DS.fontWeightBold,
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
                          fontWeight: DS.fontWeightBold,
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

class _PlanPhaseSection extends ConsumerWidget {
  const _PlanPhaseSection({required this.plan});

  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final phasesAsync = ref.watch(planPhasesProvider(plan.id));

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: phasesAsync.when(
        loading: () => const Padding(
          padding: EdgeInsets.symmetric(vertical: DS.spacing24),
          child: Center(child: LoadingIndicator()),
        ),
        error: (err, _) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _SectionHeader(title: '计划阶段'),
            const SizedBox(height: DS.spacing12),
            Text(
              '阶段加载失败: $err',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.semanticError,
                  ),
            ),
          ],
        ),
        data: (bundle) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(child: _SectionHeader(title: '计划阶段')),
                SparkleButton.ghost(
                  onPressed: () => _showCreatePhaseDialog(context, ref, bundle),
                  label: '新增阶段',
                  icon: const Icon(Icons.add_rounded),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            if (bundle.weightedProgress != null)
              Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing12),
                child: Text(
                  'Weighted progress ${(bundle.weightedProgress! * 100).round()}%',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ),
            if (bundle.phases.isEmpty)
              Text(
                '还没有真实阶段，先创建第一个 phase，把长期计划拆成可执行的小段。',
                style: Theme.of(context).textTheme.bodyMedium,
              )
            else
              Column(
                children: bundle.phases
                    .map(
                      (phase) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing12),
                        child: _PhaseCard(
                          phase: phase,
                          isCurrent: bundle.currentPhaseCardId == phase.cardId,
                          onActivate: () => _activatePhase(context, ref, phase),
                          onComplete: () => _completePhase(context, ref, phase),
                          onFeedback: () =>
                              _submitFeedback(context, ref, phase),
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _showCreatePhaseDialog(
    BuildContext context,
    WidgetRef ref,
    PlanPhaseBundle bundle,
  ) async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Create phase'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Phase name',
            hintText: 'Foundation / Build / Review',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(dialogContext).pop(controller.text.trim()),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (!context.mounted || name == null || name.isEmpty) return;

    try {
      await ref.read(planPhaseControllerProvider).createPhase(
            plan.id,
            name: name,
            phaseIndex: bundle.phases.length + 1,
          );
      if (context.mounted) {
        AppFeedback.success(context, 'Phase created');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, 'Create phase failed: $e');
      }
    }
  }

  Future<void> _activatePhase(
    BuildContext context,
    WidgetRef ref,
    PlanPhaseModel phase,
  ) async {
    try {
      await ref.read(planPhaseControllerProvider).activatePhase(
            plan.id,
            phase.cardId,
          );
      if (context.mounted) {
        AppFeedback.success(context, 'Phase activated');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, 'Activate failed: $e');
      }
    }
  }

  Future<void> _completePhase(
    BuildContext context,
    WidgetRef ref,
    PlanPhaseModel phase,
  ) async {
    try {
      final result = await ref.read(planPhaseControllerProvider).completePhase(
            plan.id,
            phase.cardId,
          );
      if (!context.mounted) return;
      final status = result['status']?.toString();
      if (status == 'NEEDS_FEEDBACK') {
        AppFeedback.info(context, 'This phase needs feedback before advancing');
      } else {
        AppFeedback.success(context, 'Phase completed');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, 'Complete phase failed: $e');
      }
    }
  }

  Future<void> _submitFeedback(
    BuildContext context,
    WidgetRef ref,
    PlanPhaseModel phase,
  ) async {
    var rating = 4.0;
    var blocked = false;
    var lifeChanged = false;
    var requestCompassReview = false;
    final reflectionController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setState) => AlertDialog(
          title: Text('Phase feedback · ${phase.title}'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'How aligned did this phase feel?',
                  style: Theme.of(dialogContext).textTheme.bodyMedium,
                ),
                Slider(
                  value: rating,
                  min: 1,
                  max: 5,
                  divisions: 4,
                  label: rating.toStringAsFixed(0),
                  onChanged: (value) => setState(() => rating = value),
                ),
                TextField(
                  controller: reflectionController,
                  minLines: 3,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: 'Reflection',
                    hintText: 'What worked, what failed, what changed?',
                  ),
                ),
                CheckboxListTile(
                  value: blocked,
                  onChanged: (value) =>
                      setState(() => blocked = value ?? false),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('I felt blocked this phase'),
                ),
                CheckboxListTile(
                  value: lifeChanged,
                  onChanged: (value) =>
                      setState(() => lifeChanged = value ?? false),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('My life conditions changed'),
                ),
                CheckboxListTile(
                  value: requestCompassReview,
                  onChanged: (value) => setState(
                    () => requestCompassReview = value ?? false,
                  ),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Request compass review'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Submit'),
            ),
          ],
        ),
      ),
    );

    if (!context.mounted || confirmed != true) return;

    try {
      final result = await ref.read(planPhaseControllerProvider).submitFeedback(
            plan.id,
            phase.cardId,
            rating: rating,
            reflection: reflectionController.text.trim(),
            blocked: blocked,
            lifeChanged: lifeChanged,
            requestCompassReview: requestCompassReview,
          );
      if (!context.mounted) return;
      final triggered = result['trigger_compass_review'] == true;
      AppFeedback.success(
        context,
        triggered
            ? 'Feedback saved, compass review suggested'
            : 'Feedback saved',
      );
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, 'Submit feedback failed: $e');
      }
    }
  }
}

class _PhaseCard extends StatelessWidget {
  const _PhaseCard({
    required this.phase,
    required this.isCurrent,
    required this.onActivate,
    required this.onComplete,
    required this.onFeedback,
  });

  final PlanPhaseModel phase;
  final bool isCurrent;
  final VoidCallback onActivate;
  final VoidCallback onComplete;
  final VoidCallback onFeedback;

  @override
  Widget build(BuildContext context) {
    final dateLabel = [
      if (phase.estimatedStart != null)
        Formatters.formatDateMedium(phase.estimatedStart!),
      if (phase.estimatedEnd != null)
        Formatters.formatDateMedium(phase.estimatedEnd!),
    ].join(' -> ');

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: isCurrent
                      ? DS.primaryBase.withValues(alpha: 0.12)
                      : DS.surfaceSecondary,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text('P${phase.phaseIndex}'),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  phase.title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightSemiBold,
                      ),
                ),
              ),
              if (isCurrent) Icon(Icons.bolt_rounded, color: DS.primaryBase),
            ],
          ),
          if ((phase.objective ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(phase.objective!),
          ],
          const SizedBox(height: DS.spacing12),
          LinearProgressIndicator(
            value: phase.progress.clamp(0, 1),
            minHeight: 8,
            borderRadius: BorderRadius.circular(999),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '${(phase.progress * 100).round()}% · ${phase.completedOccurrenceCount}/${phase.occurrenceCount} occurrences · ${phase.taskCount} tasks',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          if (dateLabel.isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              dateLabel,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              if (!isCurrent && phase.lifecycleStatus != 'COMPLETED')
                SparkleButton.secondary(
                  onPressed: onActivate,
                  label: 'Activate',
                  icon: const Icon(Icons.play_arrow_rounded),
                ),
              if (phase.lifecycleStatus == 'ACTIVE')
                SparkleButton.ghost(
                  onPressed: onComplete,
                  label: 'Complete',
                  icon: const Icon(Icons.check_rounded),
                ),
              if (phase.needsFeedback || phase.lifecycleStatus == 'ACTIVE')
                SparkleButton.ghost(
                  onPressed: onFeedback,
                  label: 'Feedback',
                  icon: const Icon(Icons.rate_review_outlined),
                ),
            ],
          ),
        ],
      ),
    );
  }
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
