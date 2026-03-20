import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Interactive task card - expandable card with quick actions
class InteractiveTaskCard extends ConsumerWidget {
  const InteractiveTaskCard({
    required this.task,
    super.key,
    this.showDueDate = true,
  });

  final TaskModel task;
  final bool showDueDate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boardState = ref.watch(taskBoardProvider);
    final isExpanded = boardState.expandedTaskIds.contains(task.id);

    return MaterialStyler(
      material: AppMaterials.ceramic,
      borderRadius: DS.borderRadius12,
      padding: EdgeInsets.zero,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Compact view (always visible)
          InkWell(
            onTap: () => ref
                .read(taskBoardProvider.notifier)
                .toggleTaskExpansion(task.id),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Row(
                children: [
                  // Priority indicator
                  _buildPriorityIndicator(task.priority),
                  const SizedBox(width: DS.spacing12),
                  // Task info
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          task.title,
                          style: context.sparkleTypography.bodyMedium.copyWith(
                            fontWeight: FontWeight.w500,
                            color: DS.textPrimary,
                          ),
                          maxLines: isExpanded ? null : 1,
                          overflow: isExpanded ? null : TextOverflow.ellipsis,
                        ),
                        if (!isExpanded) ...[
                          const SizedBox(height: DS.spacing4),
                          Row(
                            children: [
                              _buildTaskTypeChip(task.type),
                              const SizedBox(width: DS.spacing6),
                              Text(
                                '${task.estimatedMinutes}m',
                                style: context.sparkleTypography.labelSmall
                                    .copyWith(
                                  color: DS.textSecondary,
                                ),
                              ),
                              if (task.dueDate != null && showDueDate) ...[
                                const SizedBox(width: DS.spacing6),
                                Icon(
                                  Icons.calendar_today_rounded,
                                  size: DS.iconSizeXs,
                                  color: _getDueDateColor(task.dueDate!),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  // Actions
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Quick complete button
                      _QuickCompleteButton(task: task),
                      const SizedBox(width: DS.spacing4),
                      // Expand/collapse icon
                      AnimatedRotation(
                        turns: isExpanded ? 0.5 : 0,
                        duration: DS.quick,
                        child: Icon(
                          Icons.expand_more,
                          color: DS.textSecondary,
                          size: DS.iconSizeSm,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          // Expanded view
          if (isExpanded) _buildExpandedContent(context, ref, task),
        ],
      ),
    );
  }

  Widget _buildExpandedContent(
          BuildContext context, WidgetRef ref, TaskModel task,) =>
      Container(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing12,
          DS.spacing10,
          DS.spacing12,
          DS.spacing12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 1,
              margin: const EdgeInsets.only(bottom: DS.spacing12),
              decoration: BoxDecoration(
                color: DS.border.withValues(alpha: 0.18),
                borderRadius: DS.borderRadiusFull,
              ),
            ),
            // Metadata row
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _buildTaskTypeChip(task.type),
                _buildPriorityChip(task.priority),
                Text(
                  '${task.estimatedMinutes} 分钟',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                if (task.dueDate != null && showDueDate)
                  _buildDueDateChip(context, task.dueDate!),
              ],
            ),
            if (task.tags.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing6,
                runSpacing: DS.spacing6,
                children: task.tags
                    .map(
                      (tag) => Chip(
                        label: Text(
                          tag,
                          style: context.sparkleTypography.labelSmall.copyWith(
                            fontSize: 10,
                          ),
                        ),
                        visualDensity: VisualDensity.compact,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
                        side: BorderSide.none,
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: DS.spacing12),
            // Action buttons
            Row(
              children: [
                Expanded(
                  child: _ActionButton(
                    icon: Icons.play_arrow_rounded,
                    label: '开始',
                    onTap: () {
                      // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
                      ref.read(activeTaskProvider.notifier).state = task;
                      context.push('/tasks/${task.id}/execute');
                    },
                    color: Color.lerp(DS.surfaceSecondary, DS.success, 0.82)!,
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _ActionButton(
                    icon: Icons.edit_rounded,
                    label: '编辑',
                    onTap: () => context.push('/tasks/${task.id}'),
                    color: Color.lerp(DS.surfaceSecondary, DS.info, 0.82)!,
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _ActionButton(
                    icon: Icons.delete_outline_rounded,
                    label: '放弃',
                    onTap: () => _confirmAbandon(context, ref, task),
                    color: Color.lerp(DS.surfaceSecondary, DS.error, 0.86)!,
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _buildPriorityIndicator(int priority) {
    Color color;
    if (priority >= 8) {
      color = DS.error;
    } else if (priority >= 5) {
      color = DS.warning;
    } else {
      color = DS.success;
    }

    return Container(
      width: 4,
      height: 40,
      decoration: BoxDecoration(
        color: color,
        borderRadius: DS.borderRadius4,
      ),
    );
  }

  Widget _buildTaskTypeChip(TaskType type) {
    final (label, color) = switch (type) {
      TaskType.learning => ('学习', DS.brandPrimary),
      TaskType.training => ('训练', DS.success),
      TaskType.errorFix => ('排错', DS.error),
      TaskType.reflection => ('反思', DS.prismPurple),
      TaskType.social => ('社交', DS.info),
      TaskType.planning => ('规划', DS.warning),
      TaskType.ocr => ('OCR', DS.textSecondary),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: DS.borderRadius8,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w500,
          color: color,
        ),
      ),
    );
  }

  Widget _buildPriorityChip(int priority) {
    final (label, color) = switch (priority) {
      >= 8 => ('高优先级', DS.error),
      >= 5 => ('中优先级', DS.warning),
      _ => ('低优先级', DS.success),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: DS.borderRadius8,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w500,
          color: color,
        ),
      ),
    );
  }

  Widget _buildDueDateChip(BuildContext context, DateTime dueDate) {
    final color = _getDueDateColor(dueDate);
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dueDay = DateTime(dueDate.year, dueDate.month, dueDate.day);

    String label;
    if (dueDay.isBefore(today)) {
      label = '已逾期';
    } else if (dueDay == today) {
      label = '今天';
    } else {
      final tomorrow = today.add(const Duration(days: 1));
      if (dueDay == tomorrow) {
        label = '明天';
      } else {
        label = '${dueDate.month}月${dueDate.day}日';
      }
    }

    return GestureDetector(
      onTap: () => context.push('/calendar?date=${dueDate.toIso8601String()}'),
      child: Container(
        padding:
            const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: DS.borderRadius8,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.calendar_today_rounded,
              size: 10,
              color: color,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getDueDateColor(DateTime dueDate) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dueDay = DateTime(dueDate.year, dueDate.month, dueDate.day);

    if (dueDay.isBefore(today)) return DS.error;
    if (dueDay == today) return DS.warning;
    return DS.textSecondary;
  }

  void _confirmAbandon(BuildContext context, WidgetRef ref, TaskModel task) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('放弃任务'),
        content: Text('确定要放弃「${task.title}」吗？'),
        actions: [
          SparkleButton.ghost(
            label: '取消',
            onPressed: () => Navigator.pop(context),
          ),
          SparkleButton.destructive(
            label: '放弃',
            onPressed: () {
              Navigator.pop(context);
              unawaited(
                  ref.read(taskListProvider.notifier).abandonTask(task.id),);
            },
          ),
        ],
      ),
    );
  }
}

class _QuickCompleteButton extends ConsumerWidget {
  const _QuickCompleteButton({required this.task});

  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Tooltip(
        message: '完成任务',
        child: SparkleIconButton(
          icon: const Icon(Icons.check_circle_outline_rounded),
          variant: ButtonVariant.ghost,
          onPressed: () async {
            await ref
                .read(taskListProvider.notifier)
                .completeTask(task.id, task.estimatedMinutes, null);
            await ref.read(dashboardProvider.notifier).refresh();
          },
        ),
      );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.color,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color color;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius8,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          decoration: BoxDecoration(
            border: Border.all(
              color: color.withValues(alpha: 0.3),
            ),
            borderRadius: DS.borderRadius8,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: DS.iconSizeSm, color: color),
              const SizedBox(width: DS.spacing4),
              Text(
                label,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: color,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      );
}
