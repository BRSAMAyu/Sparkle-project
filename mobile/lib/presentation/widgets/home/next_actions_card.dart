import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/data/models/task_model.dart';

/// NextActionsCard - Next Actions Card (1x2 tall)
class NextActionsCard extends ConsumerWidget {
  final VoidCallback? onViewAll;

  const NextActionsCard({super.key, this.onViewAll});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final nextActions = dashboardState.nextActions;

    return ClipRRect(
      borderRadius: AppDesignTokens.borderRadius20,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          decoration: BoxDecoration(
            color: AppDesignTokens.glassBackground,
            borderRadius: AppDesignTokens.borderRadius20,
            border: Border.all(color: AppDesignTokens.glassBorder),
          ),
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    '下一步',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  if (onViewAll != null)
                    GestureDetector(
                      onTap: onViewAll,
                      child: const Icon(Icons.more_horiz_rounded, color: Colors.white70, size: 16),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: nextActions.isEmpty
                    ? _buildEmptyState()
                    : ListView.separated(
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: nextActions.length.clamp(0, 1),
                        separatorBuilder: (context, index) => const SizedBox(height: 8),
                        itemBuilder: (context, index) {
                          return _NextActionItem(task: nextActions[index]);
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.done_all_rounded, color: Colors.white.withAlpha(50), size: 24),
          const SizedBox(height: 4),
          Text(
            '清空啦',
            style: TextStyle(fontSize: 10, color: Colors.white.withAlpha(100)),
          ),
        ],
      ),
    );
  }
}

class _NextActionItem extends ConsumerWidget {
  final TaskData task;
  const _NextActionItem({required this.task});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return GestureDetector(
      onTap: () {
        final taskModel = _toTaskModel(task);
        context.push('/focus/mindfulness', extra: taskModel);
      },
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(10),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              task.title,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: Colors.white,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
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
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    '${task.estimatedMinutes}m',
                    style: TextStyle(fontSize: 9, color: Colors.white.withAlpha(120)),
                  ),
                ),
                GestureDetector(
                  onTap: () async {
                    await ref.read(taskListProvider.notifier).completeTask(task.id, task.estimatedMinutes, null);
                    ref.read(dashboardProvider.notifier).refresh();
                  },
                  child: Icon(Icons.check_circle_outline_rounded, color: Colors.white.withAlpha(150), size: 14),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'learning': return Colors.blue;
      case 'training': return Colors.green;
      case 'error_fix': return Colors.red;
      case 'reflection': return AppDesignTokens.prismPurple;
      default: return Colors.grey;
    }
  }

  TaskModel _toTaskModel(TaskData data) {
    return TaskModel(
      id: data.id,
      userId: '',
      title: data.title,
      type: _parseTaskType(data.type),
      tags: [],
      estimatedMinutes: data.estimatedMinutes,
      difficulty: 1,
      energyCost: 1,
      status: TaskStatus.pending,
      priority: data.priority,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  TaskType _parseTaskType(String type) {
    switch (type) {
      case 'learning': return TaskType.learning;
      case 'training': return TaskType.training;
      case 'error_fix': return TaskType.errorFix;
      case 'reflection': return TaskType.reflection;
      case 'social': return TaskType.social;
      case 'planning': return TaskType.planning;
      default: return TaskType.learning;
    }
  }
}