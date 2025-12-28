import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

/// NextActionsCard - Next Actions Card (1x2 tall)
class NextActionsCard extends ConsumerWidget {

  const NextActionsCard({super.key, this.onViewAll});
  final VoidCallback? onViewAll;

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
          padding: EdgeInsets.all(DS.md),
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
                      color: DS.brandPrimaryConst,
                    ),
                  ),
                  if (onViewAll != null)
                    GestureDetector(
                      onTap: onViewAll,
                      child: Icon(Icons.more_horiz_rounded, color: DS.brandPrimary70Const, size: 16),
                    ),
                ],
              ),
              SizedBox(height: DS.md),
              Expanded(
                child: nextActions.isEmpty
                    ? _buildEmptyState()
                    : ListView.separated(
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: nextActions.length.clamp(0, 1),
                        separatorBuilder: (context, index) => SizedBox(height: DS.sm),
                        itemBuilder: (context, index) => _NextActionItem(task: nextActions[index]),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() => Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.done_all_rounded, color: DS.brandPrimary.withAlpha(50), size: 24),
          SizedBox(height: DS.xs),
          Text(
            '清空啦',
            style: TextStyle(fontSize: 10, color: DS.brandPrimary.withAlpha(100)),
          ),
        ],
      ),
    );
}

class _NextActionItem extends ConsumerWidget {
  const _NextActionItem({required this.task});
  final TaskData task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => GestureDetector(
      onTap: () {
        final taskModel = _toTaskModel(task);
        context.push('/focus/mindfulness', extra: taskModel);
      },
      child: Container(
        padding: EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withAlpha(10),
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
                color: DS.brandPrimaryConst,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            SizedBox(height: DS.xs),
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
                SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    '${task.estimatedMinutes}m',
                    style: TextStyle(fontSize: 9, color: DS.brandPrimary.withAlpha(120)),
                  ),
                ),
                GestureDetector(
                  onTap: () async {
                    await ref.read(taskListProvider.notifier).completeTask(task.id, task.estimatedMinutes, null);
                    ref.read(dashboardProvider.notifier).refresh();
                  },
                  child: Icon(Icons.check_circle_outline_rounded, color: DS.brandPrimary.withAlpha(150), size: 14),
                ),
              ],
            ),
          ],
        ),
      ),
    );

  Color _getTypeColor(String type) {
    switch (type) {
      case 'learning': return DS.brandPrimary;
      case 'training': return DS.success;
      case 'error_fix': return DS.error;
      case 'reflection': return AppDesignTokens.prismPurple;
      default: return DS.brandPrimary;
    }
  }

  TaskModel _toTaskModel(TaskData data) => TaskModel(
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