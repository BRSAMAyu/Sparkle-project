import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart'
    hide ButtonVariant;
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/guidance/task_guidance_surface.dart';
import 'package:sparkle/features/task/presentation/widgets/subtask_list_widget.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/widgets/card_picker_sheet.dart';

class TaskDetailScreen extends ConsumerWidget {
  const TaskDetailScreen({required this.taskId, super.key});
  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskAsync = ref.watch(taskDetailProvider(taskId));

    // P1: Design System Adoption - Wrap screen in NeoGlass material
    return MaterialStyler(
      material: AppMaterials.neoGlass(context),
      child: SparklePageScaffold(
        role: SparklePageRole.content,
        child: taskAsync.when(
          data: (task) => _TaskDetailView(task: task),
          loading: () => Center(
            child: LoadingIndicator.circular(
              showText: true,
              loadingText: context.l10n.taskDetailLoading,
            ),
          ),
          error: (err, stack) => CustomErrorWidget.page(
            context: context,
            message: context.l10n.taskDetailLoadFailed(err.toString()),
            onRetry: () => ref.refresh(taskDetailProvider(taskId)),
          ),
        ),
      ),
    );
  }
}

class _TaskDetailView extends ConsumerWidget {
  const _TaskDetailView({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Column(
        children: [
          Expanded(
            child: CustomScrollView(
              slivers: [
                _buildSliverAppBar(context, ref),
                SliverToBoxAdapter(
                  child: ContentConstraint(
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: SparkleStaggerList(
                        gap: DS.spacing24,
                        children: [
                          _buildInfoSection(context, ref),
                          if (task.guideJson != null ||
                              (task.aiPrompt ?? '').trim().isNotEmpty)
                            _StructuredGuideSection(task: task),
                          if ((task.userNote ?? '').trim().isNotEmpty)
                            _buildNoteSection(context),
                          _buildSubtaskSection(context, ref),
                          if (AppFeatureFlags.enableTaskGuidanceV2)
                            TaskGuidanceSurface(task: task)
                          else
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        context.l10n.taskGuideTitle,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleLarge
                                            ?.copyWith(
                                              fontWeight: DS.fontWeightBold,
                                            ),
                                      ),
                                    ),
                                    _GenerateGuideButton(taskId: task.id),
                                  ],
                                ),
                                const SizedBox(height: DS.spacing12),
                                _buildGuideSection(context),
                              ],
                            ),
                          const SizedBox(height: DS.spacing64),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          _BottomActionBar(task: task),
        ],
      );

  Widget _buildNoteSection(BuildContext context) => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.notes_rounded, color: DS.primaryBase, size: 20),
                const SizedBox(width: DS.spacing8),
                Text(
                  context.l10n.taskDetailNoteSection,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              task.userNote!.trim(),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.6,
                  ),
            ),
          ],
        ),
      );

  Widget _buildSubtaskSection(BuildContext context, WidgetRef ref) {
    final subtaskState = ref.watch(subtaskNotifierProvider(task.id));
    final shouldShowSection = task.subtasksTotal > 0 || subtaskState.total > 0;
    if (!shouldShowSection) {
      return const SizedBox.shrink();
    }

    return GraphiteCardSurface(
      padding: EdgeInsets.zero,
      child: ExpansionTile(
        initiallyExpanded: true,
        shape: const Border(),
        tilePadding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                shape: BoxShape.circle,
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Icon(
                Icons.checklist_rounded,
                color: DS.primaryBase,
                size: 20,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                context.l10n.taskDetailSubtasks(subtaskState.completed, subtaskState.total),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ),
          ],
        ),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing16,
            ),
            child: subtaskState.isLoading && subtaskState.total == 0
                ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                : subtaskState.error != null && subtaskState.total == 0
                    ? Text(
                        context.l10n.taskDetailSubtaskLoadFailed(subtaskState.error ?? ''),
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.error,
                            ),
                      )
                    : SubtaskListWidget(
                        parentTaskId: task.id,
                        onSubtaskToggle: (_) {},
                        onSubtaskDelete: (_) {},
                        readOnly: true,
                      ),
          ),
        ],
      ),
    );
  }

  LinearGradient _getBackgroundGradient(TaskType type) {
    switch (type) {
      case TaskType.learning:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.18)!,
            Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.62)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.training:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.success, 0.18)!,
            Color.lerp(DS.surfaceSecondary, DS.success, 0.58)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.errorFix:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.error, 0.14)!,
            Color.lerp(DS.surfaceSecondary, DS.error, 0.52)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.reflection:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.rarityEpic, 0.18)!,
            Color.lerp(DS.surfaceSecondary, DS.rarityEpic, 0.56)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.social:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.info, 0.16)!,
            Color.lerp(DS.surfaceSecondary, DS.info, 0.54)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.planning:
        return LinearGradient(
          colors: [
            Color.lerp(DS.surfaceSecondary, DS.warning, 0.14)!,
            Color.lerp(DS.surfaceSecondary, DS.warning, 0.48)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case TaskType.ocr:
        return LinearGradient(
          colors: [DS.neutral50, DS.neutral400],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
    }
  }

  Widget _buildSliverAppBar(BuildContext context, WidgetRef ref) =>
      SliverAppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        expandedHeight: DS.spacing40 * 5, // 200 = 40 * 5
        pinned: true,
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.drive_file_move_outline),
            onPressed: () => unawaited(_showMoveToPlanPicker(context, ref)),
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.share_outlined),
            onPressed: () => unawaited(_showShareSheet(context)),
          ),
        ],
        flexibleSpace: FlexibleSpaceBar(
          background: Hero(
            tag: 'task-${task.id}',
            child: Material(
              type: MaterialType.transparency,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: _getBackgroundGradient(task.type),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(DS.spacing16),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          task.title,
                          style: Theme.of(context)
                              .textTheme
                              .headlineSmall
                              ?.copyWith(
                                fontWeight: DS.fontWeightBold,
                                color: DS.neutral900,
                              ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        Wrap(
                          spacing: DS.spacing8,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Chip(
                              label: Text(
                                _taskTypeLabel(context, task.type),
                                style: const TextStyle(fontSize: DS.fontSizeSm),
                              ),
                              backgroundColor:
                                  DS.surfaceOverlay.withValues(alpha: 0.92),
                              avatar: Icon(
                                Icons.category,
                                size: DS.iconSizeXs,
                                color: DS.textSecondary,
                              ),
                              labelStyle: TextStyle(color: DS.textPrimary),
                            ),
                            Chip(
                              label: Text(
                                _taskStatusLabel(context, task.status),
                                style: const TextStyle(fontSize: DS.fontSizeSm),
                              ),
                              backgroundColor: _getStatusColor(task.status)
                                  .withValues(alpha: 0.2),
                              labelStyle: TextStyle(
                                color: _getStatusColor(task.status),
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                            if (_taskProtocolKind(task) != null)
                              Chip(
                                key: const ValueKey('task-protocol-kind-chip'),
                                label: Text(
                                  _taskProtocolKind(task)!,
                                  style:
                                      const TextStyle(fontSize: DS.fontSizeSm),
                                ),
                                backgroundColor:
                                    DS.surfaceOverlay.withValues(alpha: 0.92),
                                avatar: Icon(
                                  Icons.hub_outlined,
                                  size: DS.iconSizeXs,
                                  color: DS.textSecondary,
                                ),
                                labelStyle: TextStyle(color: DS.textPrimary),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );

  Future<void> _showShareSheet(BuildContext context) async {
    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: ShareableContentType.taskCompletion,
        resourceId: task.id,
        title: task.title,
        subtitle: task.guideContent?.split('\n').first ?? '',
        description: task.userNote,
        metadata: {
          'duration': task.actualMinutes ?? task.estimatedMinutes,
          'completed_at':
              (task.completedAt ?? task.updatedAt).toIso8601String(),
          'task_type': _taskTypeLabel(context, task.type),
          'subtasks_completed': task.subtasksCompleted,
          'subtasks_total': task.subtasksTotal,
        },
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
    );
  }

  Future<void> _showMoveToPlanPicker(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final plans = <PlanModel>[
      ...ref.read(planListProvider).activePlans,
      ...ref.read(planListProvider).plans,
    ];
    if (plans.isEmpty) {
      try {
        plans.addAll(await ref.read(planRepositoryProvider).getPlans());
      } catch (e) {
        if (!context.mounted) return;
        AppFeedback.error(context, 'Failed to load plans: $e');
        return;
      }
    }

    if (!context.mounted) return;

    final deduped = <String, PlanModel>{};
    for (final plan in plans) {
      deduped[plan.id] = plan;
    }

    final selectedPlanId = await CardPickerSheet.show(
      context,
      title: 'Move task to plan',
      allowEmptySelection: true,
      emptySelectionLabel: 'Detach from current plan',
      options: deduped.values
          .map(
            (plan) => CardPickerOption(
              id: plan.id,
              title: plan.name,
              subtitle: plan.description ?? plan.subject ?? '',
              group: plan.isActive ? 'Active plans' : 'Archived plans',
              icon: plan.type == PlanType.growth
                  ? Icons.alt_route_rounded
                  : Icons.flag_outlined,
              isSelected: plan.id == task.planId,
            ),
          )
          .toList()
        ..sort((a, b) => a.title.compareTo(b.title)),
    );

    if (!context.mounted) return;
    if (selectedPlanId == task.planId) return;

    try {
      await ref.read(taskListProvider.notifier).moveTaskToPlan(
            task.id,
            selectedPlanId,
            previousPlanId: task.planId,
          );
      if (!context.mounted) return;
      ref.invalidate(taskDetailProvider(task.id));
      AppFeedback.success(
        context,
        selectedPlanId == null
            ? 'Task detached from plan'
            : 'Task moved successfully',
      );
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(context, 'Move failed: $e');
    }
  }

  Widget _buildInfoSection(BuildContext context, WidgetRef ref) {
    final planAsync = task.planId == null
        ? null
        : ref.watch(planDetailProvider(task.planId!));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (planAsync != null) ...[
          _buildPlanContextCard(context, planAsync),
          const SizedBox(height: DS.spacing12),
        ],
        _InfoTileCard(
          icon: Icons.timer_outlined,
          title: context.l10n.taskEstimatedDuration,
          content: Formatters.formatDuration(
            Duration(minutes: task.estimatedMinutes),
          ),
          gradient: DS.primaryGradient,
        ),
        const SizedBox(height: DS.spacing12),
        Row(
          children: [
            Expanded(
              child: _InfoTileCard(
                icon: Icons.star_border,
                title: context.l10n.taskDifficulty,
                content: '${task.difficulty} / 5',
                gradient: DS.warningGradient,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: _InfoTileCard(
                icon: Icons.local_fire_department,
                title: context.l10n.taskEnergyCost,
                content: '${task.energyCost} / 5',
                gradient: DS.errorGradient,
              ),
            ),
          ],
        ),
        if (task.dueDate != null) ...[
          const SizedBox(height: DS.spacing12),
          _InfoTileCard(
            icon: Icons.calendar_today,
            title: context.l10n.taskDeadline,
            content: DateFormat.yMMMd().format(task.dueDate!),
            gradient: DS.infoGradient,
          ),
        ],
      ],
    );
  }

  Widget _buildPlanContextCard(
    BuildContext context,
    AsyncValue<PlanModel> planAsync,
  ) =>
      planAsync.when(
        data: (plan) => GraphiteCardSurface(
          child: InkWell(
            borderRadius: DS.borderRadius16,
            onTap: () => context.push('/plans/${plan.id}'),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    gradient: DS.primaryGradient,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: const Icon(
                    Icons.route_rounded,
                    color: Colors.white,
                    size: 18,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.taskDetailPlanContext,
                        style:
                            Theme.of(context).textTheme.labelMedium?.copyWith(
                                  color: DS.textSecondary,
                                  fontWeight: DS.fontWeightMedium,
                                ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        plan.name,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                      ),
                    ],
                  ),
                ),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.textSecondary,
                ),
              ],
            ),
          ),
        ),
        loading: () => GraphiteCardSurface(
          child: Row(
            children: [
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              const SizedBox(width: DS.spacing12),
              Text(
                '正在加载所属计划...',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ),
        ),
        error: (_, __) => const SizedBox.shrink(),
      );

  Widget _buildGuideSection(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
          boxShadow: DS.shadowSm,
        ),
        child: SparkleMarkdown(
          content: task.guideContent ?? context.l10n.taskGuideEmpty,
          textColor: DS.textPrimary,
          codeBackgroundColor: DS.neutral100,
          linkColor: DS.primaryBase,
          contentRole: SparkleMarkdownRole.taskGuide,
        ),
      );

  String _taskTypeLabel(BuildContext context, TaskType type) {
    final l10n = context.l10n;
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
        return l10n.taskTypeLearning;
    }
  }

  String? _taskProtocolKind(TaskModel task) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final dailySpec = guide['daily_spec'];
    final candidates = [
      guide['task_card_template_id'],
      guide['template_id'],
      guide['task_kind'],
      if (dailySpec is Map) dailySpec['task_card_template_id'],
      if (dailySpec is Map) dailySpec['template_id'],
      if (dailySpec is Map) dailySpec['task_kind'],
    ];
    for (final candidate in candidates) {
      final text = '$candidate'.trim();
      if (text.isEmpty || text == 'null' || text == 'generic_task') continue;
      return text;
    }
    return null;
  }

  String _taskStatusLabel(BuildContext context, TaskStatus status) {
    final l10n = context.l10n;
    switch (status) {
      case TaskStatus.pending:
        return l10n.taskStatusPending;
      case TaskStatus.inProgress:
        return l10n.taskStatusInProgress;
      case TaskStatus.stuck:
        return l10n.taskStatusStuck;
      case TaskStatus.completed:
        return l10n.taskStatusCompleted;
      case TaskStatus.abandoned:
        return l10n.taskStatusAbandoned;
    }
  }

  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending:
        return DS.warning;
      case TaskStatus.inProgress:
      case TaskStatus.stuck:
        return DS.info;
      case TaskStatus.completed:
        return DS.success;
      case TaskStatus.abandoned:
        return DS.neutral500;
    }
  }
}

class _InfoTileCard extends StatefulWidget {
  const _InfoTileCard({
    required this.icon,
    required this.title,
    required this.content,
    required this.gradient,
  });
  final IconData icon;
  final String title;
  final String content;
  final LinearGradient gradient;

  @override
  State<_InfoTileCard> createState() => _InfoTileCardState();
}

class _InfoTileCardState extends State<_InfoTileCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTapDown: (_) => _controller.forward(),
        onTapUp: (_) => _controller.reverse(),
        onTapCancel: () => _controller.reverse(),
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: MaterialStyler(
            material: AppMaterials.ceramic(context).copyWith(
              // Inject the gradient tint into the ceramic material
              backgroundColor:
                  widget.gradient.colors.first.withValues(alpha: 0.1),
              borderColor: widget.gradient.colors.first.withValues(alpha: 0.3),
            ),
            borderRadius: DS.borderRadius12,
            padding: const EdgeInsets.all(DS.spacing16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    gradient: widget.gradient,
                    borderRadius: DS.borderRadius8,
                    boxShadow: [
                      BoxShadow(
                        color:
                            widget.gradient.colors.first.withValues(alpha: 0.3),
                        blurRadius: DS.spacing8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Icon(
                    widget.icon,
                    color: DS.brandPrimaryConst,
                    size: DS.iconSizeSm,
                  ),
                ),
                const SizedBox(width: DS.spacing16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: DS.neutral600,
                              fontWeight: DS.fontWeightMedium,
                              letterSpacing: 0.5,
                            ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        widget.content,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                  color: DS.neutral900,
                                ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _BottomActionBar extends ConsumerWidget {
  const _BottomActionBar({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Max width for bottom action bar on larger screens
    final maxBarWidth =
        context.isMobile ? double.infinity : DS.contentMaxWidthDesktop;

    return SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxBarWidth),
          child: Container(
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.surfacePrimary,
              boxShadow: DS.shadowMd,
              border: Border(
                top: BorderSide(
                  color: DS.borderSubtle,
                ),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: CustomButton.secondary(
                    text: context.l10n.commonEdit,
                    icon: Icons.edit_outlined,
                    onPressed: () {
                      unawaited(
                        SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
                      );
                      // TRACKED(TD-002): 需要创建任务编辑页面，暂时导航到创建页面
                      unawaited(context.push('/tasks/new'));
                    },
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  flex: 2,
                  child: CustomButton.primary(
                    text: context.l10n.taskStart,
                    icon: Icons.play_arrow_rounded,
                    onPressed: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.confirm,
                        ),
                      );
                      ref.read(activeTaskProvider.notifier).state = task;
                      // P0-1: Auto-switch plan context when starting task
                      ref
                          .read(activePlanProvider.notifier)
                          .selectFromTaskPlanId(task.planId);
                      unawaited(context.push('/tasks/${task.id}/execute'));
                    },
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: DS.error.withValues(alpha: 0.3),
                      width: 1.5,
                    ),
                    borderRadius: DS.borderRadius12,
                  ),
                  child: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 40,
                    icon: Icon(Icons.delete_outline, color: DS.error),
                    onPressed: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.dialogOpen,
                        ),
                      );
                      unawaited(
                        showSensoryDialog<void>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            shape: const RoundedRectangleBorder(
                              borderRadius: DS.borderRadius20,
                            ),
                            title: Text(
                              context.l10n.taskDeleteTitle,
                              style: const TextStyle(
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                            content: Text(context.l10n.taskDeleteConfirm),
                            actions: [
                              CustomButton.text(
                                text: context.l10n.cancel,
                                onPressed: () => Navigator.of(ctx).pop(),
                              ),
                              CustomButton.primary(
                                text: context.l10n.commonDelete,
                                icon: Icons.delete_rounded,
                                onPressed: () {
                                  unawaited(
                                    SensoryFeedbackService.emit(
                                      SensoryFeedbackEvent.error,
                                    ),
                                  );
                                  Navigator.of(ctx).pop();
                                  unawaited(
                                    ref
                                        .read(taskListProvider.notifier)
                                        .deleteTask(task.id),
                                  );
                                  context.pop();
                                },
                                customGradient: DS.errorGradient,
                                size: CustomButtonSize.small,
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StructuredGuideSection extends StatelessWidget {
  const _StructuredGuideSection({required this.task});

  final TaskModel task;

  @override
  Widget build(BuildContext context) {
    final guide = task.guideJson ?? const <String, dynamic>{};
    final methodSteps = (guide['method_steps'] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.trim().isNotEmpty)
        .toList();
    final keyPoints = (guide['key_points'] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.trim().isNotEmpty)
        .toList();

    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  context.l10n.taskGuideTitle,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
              if ((task.aiPrompt ?? '').trim().isNotEmpty)
                SparkleButton(
                  label: context.l10n.taskCopyAiPrompt,
                  size: ButtonSize.small,
                  variant: ButtonVariant.secondary,
                  icon: const Icon(Icons.content_copy_rounded, size: 14),
                  onPressed: () => _copyAiPrompt(context),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          if ((guide['objective']?.toString() ?? '').trim().isNotEmpty)
            _GuideInfoRow(
              icon: Icons.track_changes_rounded,
              label: context.l10n.taskObjective,
              value: guide['objective'].toString(),
            ),
          if ((guide['time_estimate_minutes']?.toString() ?? '')
              .trim()
              .isNotEmpty)
            _GuideInfoRow(
              icon: Icons.timer_outlined,
              label: context.l10n.taskEstimatedTime,
              value: context.l10n.taskDetailStepMinutesValue(guide['time_estimate_minutes'] as int),
            ),
          if ((task.successCriteria ??
                  guide['success_criteria']?.toString() ??
                  '')
              .trim()
              .isNotEmpty)
            _GuideInfoRow(
              icon: Icons.verified_outlined,
              label: context.l10n.taskCompletionCriteria,
              value: (task.successCriteria ??
                      guide['success_criteria']?.toString() ??
                      '')
                  .trim(),
            ),
          if (methodSteps.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.taskSteps,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            ...List.generate(
              methodSteps.length,
              (index) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing6),
                child: Text(
                  '${index + 1}. ${methodSteps[index]}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                ),
              ),
            ),
          ],
          if (keyPoints.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              context.l10n.taskKeyPoints,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: keyPoints
                  .map(
                    (point) => Chip(
                      label: Text(point),
                      backgroundColor: DS.surfaceSecondary,
                      labelStyle: TextStyle(color: DS.textPrimary),
                    ),
                  )
                  .toList(),
            ),
          ],
          if ((task.aiPrompt ?? '').trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    label: context.l10n.taskStartFocus,
                    variant: ButtonVariant.primary,
                    icon: const Icon(Icons.play_arrow_rounded, size: 16),
                    onPressed: () => unawaited(
                      context.push('/tasks/${task.id}/execute'),
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.taskOpenAiAssistant,
                    variant: ButtonVariant.secondary,
                    icon: const Icon(Icons.smart_toy_outlined, size: 16),
                    onPressed: () => unawaited(
                      context.push('/tasks/${task.id}/execute?panel=assistant'),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _copyAiPrompt(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: task.aiPrompt ?? ''));
    if (!context.mounted) return;
    AppFeedback.success(context, context.l10n.taskDetailCopyAiPromptSuccess);
  }
}

class _GuideInfoRow extends StatelessWidget {
  const _GuideInfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: DS.primaryBase),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: DS.textPrimary,
                      height: 1.45,
                    ),
                children: [
                  TextSpan(
                    text: '$label：',
                    style: const TextStyle(fontWeight: DS.fontWeightBold),
                  ),
                  TextSpan(text: value),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GenerateGuideButton extends ConsumerStatefulWidget {
  const _GenerateGuideButton({required this.taskId});
  final String taskId;

  @override
  ConsumerState<_GenerateGuideButton> createState() =>
      _GenerateGuideButtonState();
}

class _GenerateGuideButtonState extends ConsumerState<_GenerateGuideButton> {
  bool _isGenerating = false;

  Future<void> _generate() async {
    setState(() => _isGenerating = true);
    try {
      await ref.read(taskListProvider.notifier).generateGuide(widget.taskId);
      if (mounted) {
        ref.invalidate(taskDetailProvider(widget.taskId));
        AppFeedback.success(context, context.l10n.taskDetailGuideGenerated);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.taskDetailGuideGenerateFailed('$e'));
      }
    } finally {
      if (mounted) setState(() => _isGenerating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isGenerating) {
      return const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    return SparkleButton(
      label: context.l10n.taskAiGenerate,
      size: ButtonSize.small,
      variant: ButtonVariant.secondary,
      icon: const Icon(Icons.auto_awesome, size: 14),
      onPressed: _generate,
    );
  }
}
