import 'dart:async';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/models/plan_phase_model.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
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

class PlanDetailScreen extends ConsumerStatefulWidget {
  const PlanDetailScreen({required this.planId, super.key});
  final String planId;

  @override
  ConsumerState<PlanDetailScreen> createState() => _PlanDetailScreenState();
}

class _PlanDetailScreenState extends ConsumerState<PlanDetailScreen> {
  bool _completionCheckInFlight = false;
  String? _lastCompletionProbeSignature;
  String? _lastPlanErrorMessage;
  final Set<String> _navigatedCompletionPlanIds = <String>{};

  @override
  void initState() {
    super.initState();
    ref.listenManual<AsyncValue<PlanModel>>(
      planDetailProvider(widget.planId),
      (previous, next) {
        next.whenOrNull(
          error: (error, _) {
            final message = error.toString();
            if (!mounted || message == _lastPlanErrorMessage) {
              return;
            }
            _lastPlanErrorMessage = message;
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                SparkleSnackBar.error(
                  context.l10n.planLoadFailed(message),
                  onRetry: () => ref.refresh(planDetailProvider(widget.planId)),
                  retryLabel: context.l10n.retry,
                ),
              );
          },
        );
        if (!next.hasError) {
          _lastPlanErrorMessage = null;
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final planAsync = ref.watch(planDetailProvider(widget.planId));

    return DefaultTabController(
      length: 2,
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => RouteResilience.popOrGo(
              context,
              fallbackRoute: '/home',
            ),
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
                message: l10n.planDetailEdit,
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
          data: (plan) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (!mounted) return;
              unawaited(
                _maybeOpenSprintCompletion(plan, _mergedPlanTasks(plan)),
              );
            });
            return TabBarView(
              children: [
                _PlanOverviewTab(plan: plan),
                _PlanProgressTab(plan: plan),
              ],
            );
          },
          loading: () => const _PlanDetailLoadingView(),
          error: (err, _) => CustomErrorWidget.page(
            context: context,
            title: l10n.planDetailLoadError,
            message: _buildPlanLoadErrorMessage(l10n, err),
            onRetry: () => ref.invalidate(planDetailProvider(widget.planId)),
          ),
        ),
      ),
    );
  }

  String _buildPlanLoadErrorMessage(AppLocalizations l10n, Object error) {
    final raw = error.toString().trim();
    final normalized = raw.toLowerCase();

    if (normalized.contains('404') ||
        normalized.contains('not found') ||
        normalized.contains('plan ') && normalized.contains('not')) {
      return l10n.planDetailLoadError404;
    }
    if (normalized.contains('timeout')) {
      return l10n.planDetailLoadErrorTimeout;
    }
    if (raw.isEmpty) {
      return l10n.planDetailLoadErrorEmpty;
    }
    return l10n.planDetailLoadErrorGeneric(raw);
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

  Future<void> _maybeOpenSprintCompletion(
    PlanModel plan,
    List<TaskModel> tasks,
  ) async {
    if (!mounted ||
        _completionCheckInFlight ||
        _navigatedCompletionPlanIds.contains(plan.id) ||
        !_isSevenDaySprintFullyComplete(plan, tasks)) {
      return;
    }

    final signature = _completionSignature(plan, tasks);
    if (_lastCompletionProbeSignature == signature) return;
    _lastCompletionProbeSignature = signature;

    _completionCheckInFlight = true;
    try {
      final result = await ref
          .read(examSprintRepositoryProvider)
          .checkSprintCompletion(plan.id);
      if (!mounted || !result.completed || result.summary == null) {
        return;
      }

      _navigatedCompletionPlanIds.add(plan.id);
      final query = <String, String>{
        'plan_id': plan.id,
        if (plan.subject != null && plan.subject!.trim().isNotEmpty)
          'subject': plan.subject!.trim(),
      };
      final uri = Uri(
        path: '/exam-sprint/completion',
        queryParameters: query,
      );
      unawaited(
        context.push(
          uri.toString(),
          extra: {
            'plan_id': plan.id,
            'subject': plan.subject,
            'summary': result.summary,
          },
        ),
      );
    } catch (e) {
      debugPrint('Sprint completion check failed: $e');
    } finally {
      _completionCheckInFlight = false;
    }
  }

  bool _isSevenDaySprintFullyComplete(
    PlanModel plan,
    List<TaskModel> tasks,
  ) {
    if (plan.type != PlanType.sprint || tasks.isEmpty) return false;
    if (tasks.any((task) => task.syncStatus != TaskSyncStatus.synced)) {
      return false;
    }

    final days = tasks.map(_taskDay).toSet();
    if (Set<int>.from(List<int>.generate(7, (index) => index + 1))
        .difference(days)
        .isNotEmpty) {
      return false;
    }

    return tasks.every((task) => task.status == TaskStatus.completed);
  }

  String _completionSignature(PlanModel plan, List<TaskModel> tasks) {
    final sorted = [...tasks]..sort((a, b) => a.id.compareTo(b.id));
    final taskPart = sorted
        .map(
          (task) => [
            task.id,
            task.status.name,
            task.syncStatus.name,
            task.updatedAt.toIso8601String(),
          ].join(':'),
        )
        .join('|');
    return '${plan.id}:$taskPart';
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
    final mergedTasks = _mergedPlanTasks(plan);

    return ContentConstraint(
      child: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(planDetailProvider(plan.id));
          await ref
              .read(planDetailProvider(plan.id).future)
              .timeout(const Duration(seconds: 10), onTimeout: () => plan);
        },
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
                    error: (err, _) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.lg),
                      child: _InlinePlanSectionError(
                        message: l10n
                            .planDetailLearningPathLoadError(err.toString()),
                        onRetry: () => ref
                            .invalidate(learningPathProgressProvider(plan.id)),
                      ),
                    ),
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
                        label: l10n.planDetailTaskCount(
                          plan.tasks
                                  ?.where((task) =>
                                      task.status == TaskStatus.completed)
                                  .length ??
                              0,
                          plan.tasks?.length ?? 0,
                        ),
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
                  if (plan.healthScore != null) ...[
                    const SizedBox(height: DS.md),
                    _PlanHealthIndicator(plan: plan),
                  ],
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
            if (_isLast24hMode(plan)) ...[
              _Last24hSprintBanner(plan: plan),
              const SizedBox(height: DS.lg),
            ],
            if (_hasExamSprintContext(plan, mergedTasks)) ...[
              _ExamSprintContextSection(
                plan: plan,
                tasks: mergedTasks,
              ),
              const SizedBox(height: DS.lg),
            ],
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
                  title: l10n.planDetailDailyRhythm,
                  icon: Icons.schedule_rounded,
                  content: parsedDescription.schedule,
                ),
              if (parsedDescription.scope.isNotEmpty)
                _PlanRichSection(
                  title: l10n.planDetailPlanScope,
                  icon: Icons.rule_folder_outlined,
                  content: parsedDescription.scope,
                ),
              if (parsedDescription.taskBlueprint.isNotEmpty)
                _PlanRichSection(
                  title: l10n.planDetailTaskBlueprint,
                  icon: Icons.account_tree_outlined,
                  content: parsedDescription.taskBlueprint,
                ),
              if (parsedDescription.guide.isNotEmpty)
                _PlanRichSection(
                  title: l10n.planDetailAiGuide,
                  icon: Icons.auto_awesome_rounded,
                  content: parsedDescription.guide,
                ),
            ],
            _buildArchiveActions(context, ref),
          ],
        ),
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
        AppFeedback.error(context, context.l10n.planDetailTaskLoadFailed(e.toString()));
        return;
      }
    }

    if (!context.mounted) return;

    final candidateTasks = tasks
        .where((task) => task.planId != plan.id)
        .toList()
      ..sort((a, b) => a.title.compareTo(b.title));

    if (candidateTasks.isEmpty) {
      AppFeedback.info(context, context.l10n.planDetailNoExternalTasks);
      return;
    }

    final selectedTaskId = await CardPickerSheet.show(
      context,
      title: context.l10n.planDetailAddExistingTaskTitle,
      options: candidateTasks
          .map(
            (task) => CardPickerOption(
              id: task.id,
              title: task.title,
              subtitle: task.planId == null
                  ? context.l10n.planDetailTaskUnassigned
                  : context.l10n.planDetailTaskInAnotherPlan,
              group: task.planId == null
                  ? context.l10n.planDetailGroupUnassigned
                  : context.l10n.planDetailGroupOtherPlans,
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
      AppFeedback.success(context, context.l10n.planDetailTaskAdded);
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(context, context.l10n.planDetailAddTaskFailed(e.toString()));
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
    final isLast24hMode = _isLast24hMode(plan);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: _SectionHeader(
                title: isLast24hMode
                    ? context.l10n.planDetailSprintFocus
                    : context.l10n.planDetailTodayFocus,
              ),
            ),
            if (!context.isMobile && !isLast24hMode)
              _PlanTaskActions(
                onAddNewTask: onAddNewTask,
                onAddExistingTask: onAddExistingTask,
              ),
          ],
        ),
        if (context.isMobile && !isLast24hMode) ...[
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

class _ExamSprintContextSection extends StatelessWidget {
  const _ExamSprintContextSection({
    required this.plan,
    required this.tasks,
  });

  final PlanModel plan;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context) {
    final groups = _buildPlanDayGroups(tasks);
    final highlightDay = _highlightDay(plan, groups);
    final highlightedTasks = _highlightTasks(plan, groups, highlightDay);
    final packName = _sprintPackName(plan);
    final sprintModeLabel = _sprintModeLabel(context.l10n, plan, tasks);
    final compressionSummary = _compressionSummary(
      plan: plan,
      tasks: highlightedTasks,
      day: highlightDay,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GraphiteCardSurface(
          key: const ValueKey('exam-sprint-context-card'),
          surfaceRole: SparkleSurfaceRole.card,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _PlanMetaChip(
                    icon: Icons.flash_on_rounded,
                    label: sprintModeLabel,
                  ),
                  if (packName != null)
                    _PlanMetaChip(
                      icon: Icons.inventory_2_outlined,
                      label: packName,
                    ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                context.l10n.planDetailSprintPackNodes,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                context.l10n.planDetailSprintPackDesc,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing12),
              if (highlightedTasks.isEmpty)
                Text(
                  context.l10n.planDetailSprintNodesLoading,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                )
              else
                ...highlightedTasks.map(
                  (task) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing8),
                    child: _SprintPackNodeRow(task: task),
                  ),
                ),
            ],
          ),
        ),
        if (compressionSummary != null) ...[
          const SizedBox(height: DS.spacing12),
          _AdaptiveCompressionBanner(summary: compressionSummary),
        ],
      ],
    );
  }
}

class _SprintPackNodeRow extends StatelessWidget {
  const _SprintPackNodeRow({required this.task});

  final TaskModel task;

  @override
  Widget build(BuildContext context) {
    final dotColor = _taskStatusColor(task.status);
    final kind = _taskProtocolKind(task);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing10,
      ),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        children: [
          Container(
            key: ValueKey('sprint-pack-node-dot-${task.id}'),
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _sprintPackNodeLabel(task),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                if (kind != null) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    kind,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Text(
            context.l10n.planDetailMinutes(task.estimatedMinutes),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        ],
      ),
    );
  }
}

class _AdaptiveCompressionBanner extends StatelessWidget {
  const _AdaptiveCompressionBanner({required this.summary});

  final _CompressionSummary summary;

  @override
  Widget build(BuildContext context) => Container(
        key: const ValueKey('plan-adaptive-compression-banner'),
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.warning.withValues(alpha: 0.28)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: DS.warning.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(12),
              ),
              child:
                  Icon(Icons.content_cut_rounded, color: DS.warning, size: 18),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.l10n.planDetailCompressionTitle,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing6),
                  Text(
                    context.l10n.planDetailCompressionDesc(
                        summary.taskCount, summary.totalMinutes),
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                  if (summary.reason != null) ...[
                    const SizedBox(height: DS.spacing6),
                    Text(
                      summary.reason!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      );
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
            label: context.l10n.planDetailAddNewTask,
          ),
          SparkleButton.ghost(
            onPressed: onAddExistingTask,
            icon: const Icon(Icons.playlist_add_rounded),
            label: context.l10n.planDetailAddExistingTask,
          ),
        ],
      );
}

class _Last24hSprintBanner extends StatelessWidget {
  const _Last24hSprintBanner({required this.plan});

  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final recommendation = plan.dayHighlights?.recommendation.trim();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing18),
      decoration: BoxDecoration(
        color: DS.warning.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.warning.withValues(alpha: 0.28)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing8),
            decoration: BoxDecoration(
              color: DS.warning.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.timer_rounded,
              color: DS.warning,
              size: 20,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.planDetailSprintModeLabel,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: DS.textPrimary,
                      ),
                ),
                const SizedBox(height: DS.spacing6),
                Text(
                  recommendation != null && recommendation.isNotEmpty
                      ? recommendation
                      : context.l10n.planDetailDefaultRecommendation,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
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
      context.l10n,
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
    final isLast24hTask = _isLast24hTask(task);
    final isTargetedRepair = _isTargetedRepairTask(task);
    final accentColor = isTargetedRepair ? DS.warning : statusColor;
    final l10n = context.l10n;

    return GraphiteCardSurface(
      key: ValueKey('plan-task-card-${task.id}'),
      onTap: () => context.push('/tasks/${task.id}'),
      borderColor: accentColor.withValues(alpha: 0.36),
      backgroundColor:
          isTargetedRepair ? DS.warning.withValues(alpha: 0.08) : null,
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
                  color: accentColor.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(17),
                ),
                child: task.status == TaskStatus.completed
                    ? Icon(Icons.check_rounded, color: accentColor, size: 20)
                    : isTargetedRepair
                        ? Text(
                            '⚠️',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(height: 1),
                          )
                        : Text(
                            '$sequence',
                            style: Theme.of(context)
                                .textTheme
                                .titleMedium
                                ?.copyWith(
                                  color: accentColor,
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
          _WhyNowNote(text: _taskWhyNow(l10n, task)),
          _CommonMistakesToWatch(
            taskId: task.id,
            mistakes: _taskCommonMistakesToWatch(task),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _TaskMetaPill(
                icon: Icons.schedule_rounded,
                label: l10n.planDetailMinutes(task.estimatedMinutes),
              ),
              _TaskMetaPill(
                icon: Icons.bolt_rounded,
                label:
                    l10n.planDetailTaskDifficulty(task.difficulty.toString()),
              ),
              _TaskMetaPill(
                icon: _taskStatusIcon(task.status),
                label: _taskStatusLabel(l10n, task.status),
                color: statusColor,
              ),
              if (_taskProtocolKind(task) != null)
                _TaskMetaPill(
                  key: ValueKey('plan-task-kind-pill-${task.id}'),
                  icon: Icons.hub_outlined,
                  label: _taskProtocolKind(task)!,
                  color: DS.brandPrimary,
                ),
              if (isLast24hTask)
                _TaskMetaPill(
                  icon: Icons.block_rounded,
                  label: l10n.planDetailTagNoNewContent,
                  color: DS.warning,
                ),
              if (isTargetedRepair)
                _TaskMetaPill(
                  icon: Icons.warning_amber_rounded,
                  label: l10n.planDetailTagErrorRepair,
                  color: DS.warning,
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
        _SectionHeader(title: context.l10n.planDetailFullPlan),
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
            context.l10n.planDetailDayLabel(group.day),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          subtitle: Text(
            context.l10n.planDetailDayGroupSubtitle(
                group.tasks.length, group.totalMinutes),
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
    final isTargetedRepair = _isTargetedRepairTask(task);
    final accentColor = isTargetedRepair ? DS.warning : statusColor;

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
                if (isTargetedRepair)
                  Text(
                    '⚠️',
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(height: 1.2),
                  )
                else
                  Icon(
                    _taskStatusIcon(task.status),
                    size: 18,
                    color: accentColor,
                  ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    task.title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: isTargetedRepair ? DS.warning : null,
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
                _taskWhyNow(context.l10n, task),
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

class _CommonMistakesToWatch extends StatelessWidget {
  const _CommonMistakesToWatch({
    required this.taskId,
    required this.mistakes,
  });

  final String taskId;
  final List<String> mistakes;

  @override
  Widget build(BuildContext context) {
    if (mistakes.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing12),
      child: Column(
        key: ValueKey('plan-common-mistakes-section-$taskId'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.planDetailCommonMistakes,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: DS.warning,
                  fontWeight: FontWeight.w800,
                  height: 1.25,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          ...mistakes.asMap().entries.map(
                (entry) => Padding(
                  padding: EdgeInsets.only(
                    bottom: entry.key == mistakes.length - 1 ? 0 : DS.spacing8,
                  ),
                  child: _CommonMistakeCard(
                    key: ValueKey(
                      'plan-common-mistake-card-$taskId-${entry.key}',
                    ),
                    description: entry.value,
                  ),
                ),
              ),
        ],
      ),
    );
  }
}

class _CommonMistakeCard extends StatelessWidget {
  const _CommonMistakeCard({required this.description, super.key});

  final String description;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing10),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.warning.withValues(alpha: 0.22)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '⚠️',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.warning,
                    height: 1.35,
                  ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                description,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textPrimary,
                      height: 1.4,
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
    super.key,
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

List<String> _taskCommonMistakesToWatch(TaskModel task) {
  final guide = task.guideJson;
  if (guide == null) return const <String>[];

  final raw = guide['common_mistakes_to_watch'] ??
      (guide['daily_spec'] is Map<String, dynamic>
          ? (guide['daily_spec']
              as Map<String, dynamic>)['common_mistakes_to_watch']
          : null);
  if (raw is! List) return const <String>[];

  final mistakes = <String>[];
  for (final item in raw) {
    final description = _mistakeDescription(item);
    if (description.isEmpty) continue;
    mistakes.add(description);
    if (mistakes.length == 3) break;
  }
  return mistakes;
}

String _mistakeDescription(Object? item) {
  if (item is String) return item.trim();
  if (item is Map) {
    for (final key in const [
      'description',
      'label',
      'specific_risk',
      'repair_strategy',
    ]) {
      final value = item[key];
      if (value == null) continue;
      final text = '$value'.trim();
      if (text.isNotEmpty) return text;
    }
  }
  return '';
}

class _PlanDayGroup {
  _PlanDayGroup({required this.day, required this.tasks});

  final int day;
  final List<TaskModel> tasks;

  int get totalMinutes =>
      tasks.fold<int>(0, (sum, task) => sum + task.estimatedMinutes);
}

class _CompressionSummary {
  const _CompressionSummary({
    required this.taskCount,
    required this.totalMinutes,
    this.reason,
  });

  final int taskCount;
  final int totalMinutes;
  final String? reason;
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

bool _hasExamSprintContext(PlanModel plan, List<TaskModel> tasks) {
  if (plan.type != PlanType.sprint) return false;
  if ((plan.sourceMetadata ??
          const <String, dynamic>{})['exam_sprint_intake'] !=
      null) {
    return true;
  }
  return tasks.any(
    (task) =>
        task.tags.contains('exam_sprint') || _taskProtocolKind(task) != null,
  );
}

bool _isLast24hMode(PlanModel plan) {
  final metadata = plan.sourceMetadata ?? const <String, dynamic>{};
  if (metadata['last_24h_mode'] == true) return true;
  if (metadata['exam_sprint_intake'] == null && plan.type != PlanType.sprint) {
    return false;
  }
  final targetDate = plan.targetDate;
  if (targetDate == null) return false;
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final examDay = DateTime(targetDate.year, targetDate.month, targetDate.day);
  return examDay.difference(today).inDays <= 1;
}

String? _sprintPackName(PlanModel plan) {
  final metadata = plan.sourceMetadata ?? const <String, dynamic>{};
  final intake = metadata['exam_sprint_intake'];
  if (intake is! Map) return null;
  final selectedPack = intake['selected_pack'];
  if (selectedPack is! Map) return null;
  final name = '${selectedPack['pack_name'] ?? ''}'.trim();
  return name.isEmpty ? null : name;
}

String _sprintModeLabel(
    AppLocalizations l10n, PlanModel plan, List<TaskModel> tasks) {
  final metadata = plan.sourceMetadata ?? const <String, dynamic>{};
  final intake = metadata['exam_sprint_intake'];
  if (intake is Map) {
    final goalModel = intake['goal_model'];
    final daysLeft = goalModel is Map
        ? int.tryParse('${goalModel['days_left'] ?? ''}')
        : null;
    if (daysLeft == 7) {
      return l10n.planDetailSprintMode7Day;
    }
    final strategyPreview = intake['strategy_preview'];
    final sprintMode = strategyPreview is Map
        ? '${strategyPreview['sprint_mode'] ?? ''}'.trim()
        : '';
    if (sprintMode.contains('seven_day')) {
      return l10n.planDetailSprintMode7Day;
    }
  }
  final totalDays = tasks
      .map(_taskDay)
      .fold<int>(0, (maxDay, day) => day > maxDay ? day : maxDay);
  return totalDays >= 7
      ? l10n.planDetailSprintMode7Day
      : l10n.planDetailSprintModeExam;
}

String _sprintPackNodeLabel(TaskModel task) {
  final guide = task.guideJson ?? const <String, dynamic>{};
  final subjectStrategy = _asStringKeyedMap(guide['subject_strategy']);
  final dailySpec = _asStringKeyedMap(guide['daily_spec']);
  final candidates = [
    subjectStrategy?['primary_node_label'],
    guide['primary_target'],
    dailySpec?['primary_target'],
    guide['title_focus'],
    task.title,
  ];
  for (final candidate in candidates) {
    final text = '$candidate'.trim();
    if (text.isNotEmpty) return text;
  }
  return task.title;
}

String? _taskProtocolKind(TaskModel task) {
  final guide = task.guideJson ?? const <String, dynamic>{};
  final dailySpec = _asStringKeyedMap(guide['daily_spec']);
  final candidates = [
    guide['task_card_template_id'],
    guide['template_id'],
    guide['task_kind'],
    dailySpec?['task_card_template_id'],
    dailySpec?['template_id'],
    dailySpec?['task_kind'],
  ];
  for (final candidate in candidates) {
    final text = '$candidate'.trim();
    if (text.isEmpty || text == 'null' || text == 'generic_task') continue;
    return text;
  }
  return null;
}

_CompressionSummary? _compressionSummary({
  required PlanModel plan,
  required List<TaskModel> tasks,
  required int day,
}) {
  if (tasks.isEmpty) return null;
  final metadata = plan.sourceMetadata ?? const <String, dynamic>{};
  final adaptive = _asStringKeyedMap(metadata['adaptive_compressions']);
  final dayCompression =
      adaptive != null ? _asStringKeyedMap(adaptive['$day']) : null;
  final compressedTasks = tasks.where((task) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final dailySpec = _asStringKeyedMap(guide['daily_spec']);
    return guide['compressed'] == true ||
        dailySpec?['compressed'] == true ||
        _taskProtocolKind(task) == 'compressed_recovery' ||
        task.tags.contains('adaptive_compressed');
  }).toList();
  if (dayCompression == null && compressedTasks.isEmpty) return null;

  final relevantTasks = compressedTasks.isEmpty ? tasks : compressedTasks;
  final reason = [
    if (dayCompression != null)
      '${dayCompression['compression_reason'] ?? ''}'.trim(),
    ...relevantTasks
        .map(
          (task) =>
              '${(task.guideJson ?? const <String, dynamic>{})['compression_reason'] ?? ''}'
                  .trim(),
        )
        .where((text) => text.isNotEmpty),
  ].where((text) => text.isNotEmpty).cast<String>().toSet().join(' ');

  return _CompressionSummary(
    taskCount: relevantTasks.length,
    totalMinutes: relevantTasks.fold<int>(
      0,
      (sum, task) => sum + task.estimatedMinutes,
    ),
    reason: reason.isEmpty ? null : reason,
  );
}

Map<String, dynamic>? _asStringKeyedMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    try {
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }
  return null;
}

bool _isLast24hTask(TaskModel task) {
  final guide = task.guideJson ?? const <String, dynamic>{};
  if (guide['last_24h_mode'] == true) return true;
  return task.tags.any(
    (tag) => tag == 'last_24h_cram' || tag == 'exam_sprint:last_24h_cram',
  );
}

bool _isTargetedRepairTask(TaskModel task) {
  final guide = task.guideJson ?? const <String, dynamic>{};
  if (_isRepairTaskKind('${guide['task_kind'] ?? ''}'.trim())) {
    return true;
  }
  final dailySpec = guide['daily_spec'];
  if (dailySpec is Map<String, dynamic> &&
      _isRepairTaskKind('${dailySpec['task_kind'] ?? ''}'.trim())) {
    return true;
  }
  return task.tags.any(_isRepairTaskKind);
}

bool _isRepairTaskKind(String value) =>
    value == 'targeted_repair' || value == 'specialized_repair';

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
  AppLocalizations l10n,
  PlanModel plan,
  List<TaskModel> tasks,
  int day,
) {
  final serverText = plan.dayHighlights?.recommendation.trim();
  if (serverText != null && serverText.isNotEmpty) return serverText;
  final thingLabel = tasks.length == 1
      ? l10n.planDetailThingCount1
      : l10n.planDetailThingCountN(tasks.length);
  if (day == 1) {
    return l10n.planDetailRecommendationDay1(thingLabel);
  }
  return l10n.planDetailRecommendationDayN(day, thingLabel);
}

String _taskWhyNow(AppLocalizations l10n, TaskModel task) {
  final guide = task.guideJson;
  final whyNow = guide == null ? '' : '${guide['why_now'] ?? ''}'.trim();
  if (whyNow.isNotEmpty) return whyNow;
  switch (task.type) {
    case TaskType.learning:
      return l10n.planDetailWhyNowLearning;
    case TaskType.training:
      return l10n.planDetailWhyNowTraining;
    case TaskType.errorFix:
      return l10n.planDetailWhyNowErrorFix;
    case TaskType.reflection:
      return l10n.planDetailWhyNowReflection;
    case TaskType.social:
      return l10n.planDetailWhyNowSocial;
    case TaskType.planning:
      return l10n.planDetailWhyNowPlanning;
    case TaskType.ocr:
      return l10n.planDetailWhyNowOcr;
  }
}

String _taskStatusLabel(AppLocalizations l10n, TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return l10n.planDetailStatusPending;
    case TaskStatus.inProgress:
      return l10n.planDetailStatusInProgress;
    case TaskStatus.stuck:
      return l10n.planDetailStatusStuck;
    case TaskStatus.completed:
      return l10n.planDetailStatusCompleted;
    case TaskStatus.abandoned:
      return l10n.planDetailStatusAbandoned;
  }
}

IconData _taskStatusIcon(TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return Icons.radio_button_unchecked_rounded;
    case TaskStatus.inProgress:
      return Icons.play_circle_outline_rounded;
    case TaskStatus.stuck:
      return Icons.help_outline_rounded;
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
    case TaskStatus.stuck:
      return DS.warning;
    case TaskStatus.completed:
      return DS.success;
    case TaskStatus.abandoned:
      return DS.textSecondary;
  }
}

class _PlanDetailLoadingView extends StatelessWidget {
  const _PlanDetailLoadingView();

  @override
  Widget build(BuildContext context) => ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: const [
            SparkleCardSkeleton(),
            SizedBox(height: DS.spacing16),
            _PlanTaskSectionSkeleton(),
            SizedBox(height: DS.spacing16),
            _PlanTaskSectionSkeleton(compact: true),
          ],
        ),
      );
}

class _PlanTaskSectionSkeleton extends StatelessWidget {
  const _PlanTaskSectionSkeleton({this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SparkleSkeleton(
            width: compact ? 88 : 120,
            height: 20,
            borderRadius: 10,
          ),
          const SizedBox(height: DS.spacing12),
          if (compact)
            const SparkleCardSkeleton()
          else ...const [
            TaskCardSkeleton(),
            SizedBox(height: DS.spacing12),
            TaskCardSkeleton(),
          ],
        ],
      );
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

class _PlanHealthIndicator extends StatelessWidget {
  const _PlanHealthIndicator({required this.plan});

  final PlanModel plan;

  static Color _planHealthColor(double score) {
    if (score >= 0.75) return DS.success;
    if (score >= 0.5) return DS.warning;
    return DS.error;
  }

  static String _planHealthLabel(
      AppLocalizations l10n, String? status, double score) {
    final normalized = status?.trim().toLowerCase();
    if (normalized == 'critical') return l10n.planDetailHealthNeedReplan;
    if (normalized == 'warning') return l10n.planDetailHealthNeedAttention;
    if (normalized == 'healthy') return l10n.planDetailHealthStable;
    if (score >= 0.75) return l10n.planDetailHealthStable;
    if (score >= 0.5) return l10n.planDetailHealthNeedAttention;
    return l10n.planDetailHealthNeedReplan;
  }

  static String _planHealthReason(AppLocalizations l10n, String reason) {
    switch (reason) {
      case 'time_overrun':
        return l10n.planDetailHealthReasonTimeOverrun;
      case 'difficulty_too_hard':
        return l10n.planDetailHealthReasonTooHard;
      case 'difficulty_too_easy':
        return l10n.planDetailHealthReasonTooEasy;
      case 'progress_lag':
        return l10n.planDetailHealthReasonProgressLag;
      default:
        final normalized = reason.trim();
        return normalized.isEmpty
            ? l10n.planDetailHealthReasonDefault
            : normalized;
    }
  }

  @override
  Widget build(BuildContext context) {
    final score = (plan.healthScore ?? 0).clamp(0, 1).toDouble();
    final color = _planHealthColor(score);
    final l10n = context.l10n;
    final label = _planHealthLabel(l10n, plan.healthStatus, score);
    final reason = plan.healthReasons.isNotEmpty
        ? _planHealthReason(l10n, plan.healthReasons.first)
        : null;

    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.22)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.monitor_heart_outlined, size: 18, color: color),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  l10n.planDetailHealthScore((score * 100).round(), label),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          LinearProgressIndicator(
            value: score,
            minHeight: 6,
            color: color,
            backgroundColor: color.withValues(alpha: 0.16),
            borderRadius: BorderRadius.circular(3),
          ),
          if (reason != null) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              reason,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
            ),
          ],
        ],
      ),
    );
  }
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
            _SectionHeader(title: context.l10n.planDetailPhasesTitle),
            const SizedBox(height: DS.spacing12),
            _InlinePlanSectionError(
              message: context.l10n.planDetailPhasesLoadError(err.toString()),
              onRetry: () => ref.invalidate(planPhasesProvider(plan.id)),
            ),
          ],
        ),
        data: (bundle) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                    child: _SectionHeader(
                        title: context.l10n.planDetailPhasesTitle)),
                SparkleButton.ghost(
                  onPressed: () => _showCreatePhaseDialog(context, ref, bundle),
                  label: context.l10n.planDetailAddPhase,
                  icon: const Icon(Icons.add_rounded),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            if (bundle.weightedProgress != null)
              Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing12),
                child: Text(
                  context.l10n.planDetailWeightedProgress((bundle.weightedProgress! * 100).round()),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ),
            if (bundle.phases.isEmpty)
              Text(
                context.l10n.planDetailNoPhasesYet,
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
    final l10n = context.l10n;
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.planDetailCreatePhaseTitle),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(
            labelText: l10n.planDetailPhaseNameLabel,
            hintText: l10n.planDetailPhaseNameHint,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(dialogContext).pop(controller.text.trim()),
            child: Text(l10n.planCreateAction),
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
        AppFeedback.success(context, l10n.planDetailPhaseCreated);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, l10n.planDetailCreatePhaseFailed(e.toString()));
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
        AppFeedback.success(context, context.l10n.planDetailPhaseActivated);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, context.l10n.planDetailActivatePhaseFailed(e.toString()));
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
        AppFeedback.info(context, context.l10n.planDetailPhaseNeedsFeedback);
      } else {
        AppFeedback.success(context, context.l10n.planDetailPhaseCompleted);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, context.l10n.planDetailCompletePhaseFailed(e.toString()));
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

    final l10n = context.l10n;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setState) => AlertDialog(
          title: Text(l10n.planDetailPhaseFeedbackTitle(phase.title)),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.planDetailPhaseAlignmentQuestion,
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
                  decoration: InputDecoration(
                    labelText: l10n.planDetailPhaseReflectionLabel,
                    hintText: l10n.planDetailPhaseReflectionHint,
                  ),
                ),
                CheckboxListTile(
                  value: blocked,
                  onChanged: (value) =>
                      setState(() => blocked = value ?? false),
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.planDetailPhaseBlocked),
                ),
                CheckboxListTile(
                  value: lifeChanged,
                  onChanged: (value) =>
                      setState(() => lifeChanged = value ?? false),
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.planDetailPhaseLifeChanged),
                ),
                CheckboxListTile(
                  value: requestCompassReview,
                  onChanged: (value) => setState(
                    () => requestCompassReview = value ?? false,
                  ),
                  contentPadding: EdgeInsets.zero,
                  title: Text(l10n.planDetailPhaseRequestReview),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: Text(l10n.commonSubmit),
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
            ? l10n.planDetailFeedbackSavedWithReview
            : l10n.planDetailFeedbackSaved,
      );
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, l10n.planDetailSubmitFeedbackFailed(e.toString()));
      }
    }
  }
}

class _InlinePlanSectionError extends StatelessWidget {
  const _InlinePlanSectionError({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.semanticError.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.semanticError.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Icon(Icons.error_outline_rounded, color: DS.semanticError),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.semanticError,
                    ),
              ),
            ),
            const SizedBox(width: DS.spacing10),
            SparkleButton.ghost(
              onPressed: onRetry,
              label: context.l10n.retry,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ],
        ),
      );
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
            context.l10n.planDetailPhaseStats(
              (phase.progress * 100).round(),
              phase.completedOccurrenceCount,
              phase.occurrenceCount,
              phase.taskCount,
            ),
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
                  label: context.l10n.planDetailPhaseActivate,
                  icon: const Icon(Icons.play_arrow_rounded),
                ),
              if (phase.lifecycleStatus == 'ACTIVE')
                SparkleButton.ghost(
                  onPressed: onComplete,
                  label: context.l10n.planDetailPhaseComplete,
                  icon: const Icon(Icons.check_rounded),
                ),
              if (phase.needsFeedback || phase.lifecycleStatus == 'ACTIVE')
                SparkleButton.ghost(
                  onPressed: onFeedback,
                  label: context.l10n.planDetailPhaseFeedback,
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
