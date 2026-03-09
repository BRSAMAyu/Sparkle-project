import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class NextActionsCard extends ConsumerWidget {
  const NextActionsCard({
    super.key,
    this.onViewAll,
    this.compact = false,
  });

  final VoidCallback? onViewAll;
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final nextActions = dashboardState.nextActions;

    if (compact) {
      return _CompactNextActions(
        actions: nextActions,
        onViewAll: onViewAll,
      );
    }

    return MaterialStyler(
      material: AppMaterials.ceramic,
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

class _CompactNextActions extends ConsumerWidget {
  const _CompactNextActions({
    required this.actions,
    this.onViewAll,
  });

  final List<TaskData> actions;
  final VoidCallback? onViewAll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visibleActions = actions.take(2).toList();

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
          child: MaterialStyler(
            material: AppMaterials.ceramic,
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.all(DS.spacing12),
            child: visibleActions.isEmpty
                ? Text(
                    '今天没有待推进的行动',
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.textSecondary,
                    ),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ...visibleActions.map(
                        (task) => Padding(
                          padding: const EdgeInsets.only(bottom: DS.spacing8),
                          child: _CompactNextActionRow(task: task),
                        ),
                      ),
                      if (actions.length > 2)
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
                                '查看全部 →',
                                style: context.sparkleTypography.labelLarge
                                    .copyWith(
                                  color: DS.brandPrimary,
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                            ),
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

class _CompactNextActionRow extends ConsumerWidget {
  const _CompactNextActionRow({required this.task});

  final TaskData task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskModel = _toTaskModel(task);

    return InkWell(
      onTap: () => _openTaskExecution(context, ref, taskModel),
      borderRadius: DS.borderRadius12,
      child: Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing8),
        decoration: BoxDecoration(
          color: _itemColor(context),
          borderRadius: DS.borderRadius12,
        ),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: _getTypeColor(task.type),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                task.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemiBold,
                ),
              ),
            ),
            const SizedBox(width: DS.spacing8),
            InkWell(
              onTap: () => _openTaskExecution(context, ref, taskModel),
              borderRadius: BorderRadius.circular(999),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '开始',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ),
          ],
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
