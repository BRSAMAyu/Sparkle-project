import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Compact task card for calendar preview panel
/// Shows priority indicator, title, type, duration, and quick action
class CompactTaskCard extends ConsumerWidget {
  const CompactTaskCard({
    required this.task,
    super.key,
    this.onTap,
  });

  final TaskModel task;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) => MaterialStyler(
        material: AppMaterials.ceramic(context),
        borderRadius: DS.borderRadius12,
        padding: EdgeInsets.zero,
        child: InkWell(
          onTap: onTap ??
              () => context
                  .push(TaskRoutes.taskDetail.replaceFirst(':id', task.id)),
          borderRadius: DS.borderRadius12,
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
                          fontWeight: DS.fontWeightMedium,
                          color: DS.textPrimary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: DS.spacing4),
                      Row(
                        children: [
                          _buildTaskTypeChip(context, task.type),
                          const SizedBox(width: DS.spacing8),
                          Text(
                            '${task.estimatedMinutes}m',
                            style:
                                context.sparkleTypography.labelSmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                // Quick action button
                _buildQuickActionButton(context, ref, task),
              ],
            ),
          ),
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
      width: 3,
      height: 32,
      decoration: BoxDecoration(
        color: color,
        borderRadius: DS.borderRadius4,
      ),
    );
  }

  Widget _buildTaskTypeChip(BuildContext context, TaskType type) {
    final l10n = context.l10n;
    final (label, color) = switch (type) {
      TaskType.learning => (l10n.taskTypeLearning, DS.brandPrimary),
      TaskType.training => (l10n.taskTypeTraining, DS.success),
      TaskType.errorFix => (l10n.taskTypeErrorFix, DS.error),
      TaskType.reflection => (l10n.taskTypeReflection, DS.prismPurple),
      TaskType.social => (l10n.taskTypeSocial, DS.info),
      TaskType.planning => (l10n.taskTypePlanning, DS.warning),
      TaskType.ocr => (l10n.taskTypeOcr, DS.textSecondary),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: DS.borderRadius8,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: DS.fontWeightMedium,
          color: color,
        ),
      ),
    );
  }

  Widget _buildQuickActionButton(
    BuildContext context,
    WidgetRef ref,
    TaskModel task,
  ) {
    switch (task.status) {
      case TaskStatus.pending:
        return _ActionButton(
          icon: Icons.play_arrow_rounded,
          color: DS.success,
          onTap: () async {
            await ref.read(taskListProvider.notifier).startTask(task.id);
            await ref.read(dashboardProvider.notifier).refresh();
          },
        );
      case TaskStatus.inProgress:
      case TaskStatus.stuck:
        return _ActionButton(
          icon: Icons.check_rounded,
          color: DS.brandPrimaryConst,
          onTap: () {
            // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
            ref.read(activeTaskProvider.notifier).state = task;
            context.push(TaskRoutes.taskExecution.replaceFirst(':id', task.id));
          },
        );
      case TaskStatus.paused:
      case TaskStatus.restore:
        return _ActionButton(
          icon: Icons.restart_alt_rounded,
          color: DS.brandPrimaryConst,
          onTap: () async {
            await ref.read(taskListProvider.notifier).resumeTask(task.id);
            if (!context.mounted) return;
            // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
            ref.read(activeTaskProvider.notifier).state = task;
            await context.push(
              TaskRoutes.taskExecution.replaceFirst(':id', task.id),
            );
          },
        );
      case TaskStatus.completed:
        return _ActionButton(
          icon: Icons.check_circle_rounded,
          color: DS.textSecondary,
          onTap: null,
        );
      case TaskStatus.abandoned:
        return const SizedBox.shrink();
    }
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: color.withValues(alpha: 0.12),
        borderRadius: DS.borderRadius8,
        child: InkWell(
          onTap: onTap,
          borderRadius: DS.borderRadius8,
          child: Container(
            padding: const EdgeInsets.all(DS.spacing6),
            child: Icon(
              icon,
              size: DS.iconSizeSm,
              color: onTap != null ? color : DS.textSecondary,
            ),
          ),
        ),
      );
}
