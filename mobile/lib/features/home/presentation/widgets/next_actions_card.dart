import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class NextActionsCard extends ConsumerWidget {
  const NextActionsCard({
    super.key,
    this.onViewAll,
    this.compact = false,
    this.dense = false,
    this.embedded = false,
  });

  final VoidCallback? onViewAll;
  final bool compact;
  final bool dense;
  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final nextActions = dashboardState.nextActions;

    if (compact) {
      return _CompactNextActions(
        actions: nextActions,
        onViewAll: onViewAll,
        dense: dense,
        embedded: embedded,
      );
    }

    return MaterialStyler(
      material: AppMaterials.ceramic(context),
      borderRadius: DS.borderRadius20,
      padding: const EdgeInsets.all(DS.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  '下一步',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: DS.textPrimary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (onViewAll != null)
                GestureDetector(
                  onTap: onViewAll,
                  child: Icon(
                    Icons.more_horiz_rounded,
                    color: DS.textSecondary,
                    size: 16,
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.md),
          Flexible(
            child: nextActions.isEmpty
                ? _buildEmptyState(context)
                : ListView.separated(
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: nextActions.length.clamp(0, 1),
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: DS.sm),
                    itemBuilder: (context, index) => _DefaultNextActionItem(
                      task: nextActions[index],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.done_all_rounded,
              color: DS.textSecondary.withValues(alpha: 0.5),
              size: 24,
            ),
            const SizedBox(height: DS.xs),
            Text(
              '清空啦',
              style: TextStyle(fontSize: 10, color: DS.textSecondary),
            ),
          ],
        ),
      );
}

class _CompactNextActions extends StatelessWidget {
  const _CompactNextActions({
    required this.actions,
    this.onViewAll,
    this.dense = false,
    this.embedded = false,
  });

  final List<TaskData> actions;
  final VoidCallback? onViewAll;
  final bool dense;
  final bool embedded;

  @override
  Widget build(BuildContext context) {
    final maxActions = embedded ? 1 : 2;
    final visibleActions = actions.take(maxActions).toList();
    final card = MaterialStyler(
      material: AppMaterials.ceramic(context).copyWith(
        backgroundGradient: LinearGradient(
          colors: [
            DS.brandPrimary10,
            DS.surfaceSecondary,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderColor: DS.brandPrimary.withValues(alpha: 0.16),
        borderWidth: 1,
      ),
      borderRadius: DS.borderRadius20,
      padding: EdgeInsets.all(dense ? DS.spacing12 : DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: embedded ? MainAxisSize.max : MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: dense ? 30 : 34,
                height: dense ? 30 : 34,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.playlist_play_rounded,
                  size: dense ? 16 : 18,
                  color: DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '下一步',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    Text(
                      visibleActions.isEmpty
                          ? '当前没有待推进任务'
                          : embedded
                              ? '最关键的待办'
                              : '优先处理最关键的 ${actions.length} 项行动',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              if (actions.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing8,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfaceOverlay,
                    borderRadius: DS.borderRadiusFull,
                    border: Border.all(color: DS.borderSubtle),
                  ),
                  child: Text(
                    '${actions.length}项',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          if (visibleActions.isEmpty)
            if (embedded)
              Expanded(
                child: Center(
                  child: Text(
                    '今天没有待推进的行动',
                    maxLines: 2,
                    textAlign: TextAlign.center,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ),
              )
            else
              Text(
                '今天没有待推进的行动',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textSecondary,
                ),
              )
          else if (embedded)
            Expanded(
              child: _EmbeddedActionBody(
                actions: visibleActions,
                allActionCount: actions.length,
                onViewAll: onViewAll,
                dense: dense,
              ),
            )
          else
            _FlowActionBody(
              actions: visibleActions,
              allActionCount: actions.length,
              onViewAll: onViewAll,
              dense: dense,
            ),
        ],
      ),
    );

    if (embedded) {
      return card;
    }

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing8,
          DS.spacing16,
          DS.spacing8,
        ),
        child: DashboardEntrance(
          index: 4,
          slideOffset: const Offset(0, 0.06),
          child: card,
        ),
      ),
    );
  }
}

class _EmbeddedActionBody extends StatelessWidget {
  const _EmbeddedActionBody({
    required this.actions,
    required this.allActionCount,
    required this.dense,
    this.onViewAll,
  });

  final List<TaskData> actions;
  final int allActionCount;
  final VoidCallback? onViewAll;
  final bool dense;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          ...actions.asMap().entries.map(
                (entry) => SparkleStaggerItem(
                  index: entry.key,
                  child: Padding(
                    padding: EdgeInsets.only(
                      bottom: entry.key == actions.length - 1 ? 0 : DS.spacing8,
                    ),
                    child: _CompactNextActionRow(
                      task: entry.value,
                      dense: dense,
                      embedded: true,
                    ),
                  ),
                ),
              ),
          if (allActionCount > actions.length && !dense)
            Padding(
              padding: const EdgeInsets.only(top: DS.spacing4),
              child: Text(
                '其余 ${allActionCount - actions.length} 项见任务页',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ),
        ],
      );
}

class _FlowActionBody extends StatelessWidget {
  const _FlowActionBody({
    required this.actions,
    required this.allActionCount,
    required this.dense,
    this.onViewAll,
  });

  final List<TaskData> actions;
  final int allActionCount;
  final VoidCallback? onViewAll;
  final bool dense;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          ...actions.asMap().entries.map(
                (entry) => SparkleStaggerItem(
                  index: entry.key,
                  child: Padding(
                    padding: EdgeInsets.only(
                      bottom: entry.key == actions.length - 1 ? 0 : DS.spacing8,
                    ),
                    child: _CompactNextActionRow(
                      task: entry.value,
                      dense: dense,
                    ),
                  ),
                ),
              ),
          if (onViewAll != null) ...[
            const SizedBox(height: DS.spacing8),
            Align(
              alignment: Alignment.centerRight,
              child: InkWell(
                onTap: onViewAll,
                borderRadius: BorderRadius.circular(999),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing4,
                    vertical: 2,
                  ),
                  child: Text(
                    allActionCount > actions.length ? '查看全部 →' : '任务总览 →',
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.brandPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ],
      );
}

class _CompactNextActionRow extends ConsumerWidget {
  const _CompactNextActionRow({
    required this.task,
    this.dense = false,
    this.embedded = false,
  });

  final TaskData task;
  final bool dense;
  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskModel = _toTaskModel(task);

    return InkWell(
      onTap: () => _openTaskExecution(context, ref, taskModel),
      borderRadius: DS.borderRadius12,
      child: Container(
        constraints: BoxConstraints(minHeight: dense ? 46 : 52),
        padding: EdgeInsets.symmetric(
          horizontal: dense ? DS.spacing8 : DS.spacing10,
          vertical: dense ? DS.spacing8 : DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: embedded ? DS.surfaceOverlay : _itemColor(context),
          borderRadius: DS.borderRadius12,
          border: embedded ? Border.all(color: DS.borderSubtle) : null,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compactAction = dense || constraints.maxWidth < 250;
            final actionChip = Container(
              padding: EdgeInsets.symmetric(
                horizontal: compactAction ? DS.spacing6 : DS.spacing8,
                vertical: compactAction ? DS.spacing4 : DS.spacing6,
              ),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(999),
              ),
              child: compactAction
                  ? Icon(
                      Icons.play_arrow_rounded,
                      size: 16,
                      color: DS.brandPrimary,
                    )
                  : Text(
                      '开始',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.brandPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
            );

            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: dense ? 28 : 30,
                  height: dense ? 28 : 30,
                  decoration: BoxDecoration(
                    color: _getTypeColor(task.type).withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    _getTypeIcon(task.type),
                    size: dense ? 15 : 16,
                    color: _getTypeColor(task.type),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        task.title,
                        maxLines: embedded ? 2 : (dense ? 1 : 2),
                        overflow: TextOverflow.ellipsis,
                        style: context.sparkleTypography.labelLarge.copyWith(
                          color: DS.textPrimary,
                          fontSize: dense ? 12 : null,
                          fontWeight: DS.fontWeightSemiBold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${task.estimatedMinutes} 分钟 · ${_taskLabel(task.type)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                actionChip,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _DefaultNextActionItem extends ConsumerWidget {
  const _DefaultNextActionItem({required this.task});

  final TaskData task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final itemColor = isDark
        ? DS.brandPrimary.withValues(alpha: 0.08)
        : DS.brandPrimary.withValues(alpha: 0.15);
    final taskModel = _toTaskModel(task);

    return GestureDetector(
      onTap: () => _openTaskExecution(context, ref, taskModel),
      child: Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          color: itemColor,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              task.title,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: DS.textPrimary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: DS.xs),
            Row(
              children: [
                Container(
                  width: 4,
                  height: 4,
                  decoration: BoxDecoration(
                    color: _getTypeColor(task.type),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    '${task.estimatedMinutes}m',
                    style: TextStyle(fontSize: 9, color: DS.textSecondary),
                  ),
                ),
                GestureDetector(
                  onTap: () => _completeTask(ref, task),
                  child: Icon(
                    Icons.check_circle_outline_rounded,
                    color: isDark
                        ? DS.brandPrimary.withValues(alpha: 0.7)
                        : DS.brandPrimary.withValues(alpha: 0.85),
                    size: 14,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

void _openTaskExecution(
  BuildContext context,
  WidgetRef ref,
  TaskModel taskModel,
) {
  ref.read(activeTaskProvider.notifier).state = taskModel;
  unawaited(context.push('/tasks/${taskModel.id}/execute'));
}

void _completeTask(WidgetRef ref, TaskData task) {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
  unawaited(
    ref
        .read(taskListProvider.notifier)
        .completeTask(task.id, task.estimatedMinutes, null)
        .then((_) => ref.read(dashboardProvider.notifier).refresh()),
  );
}

Color _itemColor(BuildContext context) {
  final isDark = Theme.of(context).brightness == Brightness.dark;
  return isDark
      ? DS.brandPrimary.withValues(alpha: 0.08)
      : DS.brandPrimary.withValues(alpha: 0.12);
}

Color _getTypeColor(String type) {
  switch (type) {
    case 'learning':
      return DS.brandPrimary;
    case 'training':
      return DS.success;
    case 'error_fix':
      return DS.error;
    case 'reflection':
      return DS.prismPurple;
    default:
      return DS.brandPrimary;
  }
}

IconData _getTypeIcon(String type) {
  switch (type) {
    case 'learning':
      return Icons.menu_book_rounded;
    case 'training':
      return Icons.fitness_center_rounded;
    case 'error_fix':
      return Icons.rule_folder_rounded;
    case 'reflection':
      return Icons.self_improvement_rounded;
    case 'social':
      return Icons.groups_rounded;
    case 'planning':
      return Icons.route_rounded;
    default:
      return Icons.bolt_rounded;
  }
}

String _taskLabel(String type) {
  switch (type) {
    case 'learning':
      return '学习';
    case 'training':
      return '训练';
    case 'error_fix':
      return '错题';
    case 'reflection':
      return '复盘';
    case 'social':
      return '社群';
    case 'planning':
      return '计划';
    default:
      return '任务';
  }
}

TaskModel _toTaskModel(TaskData data) => TaskModel(
      id: data.id,
      userId: '',
      title: data.title,
      type: _parseTaskType(data.type),
      tags: const [],
      estimatedMinutes: data.estimatedMinutes,
      difficulty: 1,
      energyCost: 1,
      status: TaskStatus.pending,
      priority: data.priority,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

TaskType _parseTaskType(String type) {
  switch (type) {
    case 'learning':
      return TaskType.learning;
    case 'training':
      return TaskType.training;
    case 'error_fix':
      return TaskType.errorFix;
    case 'reflection':
      return TaskType.reflection;
    case 'social':
      return TaskType.social;
    case 'planning':
      return TaskType.planning;
    default:
      return TaskType.learning;
  }
}
