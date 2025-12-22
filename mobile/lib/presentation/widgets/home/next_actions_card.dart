import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

/// NextActionsCard - Next Actions Card for v2.3 dashboard
///
/// 2xN wide card displaying:
/// - Top 3 pending tasks
/// - Quick complete action
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
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          decoration: BoxDecoration(
            color: AppDesignTokens.glassBackground,
            borderRadius: AppDesignTokens.borderRadius20,
            border: Border.all(color: AppDesignTokens.glassBorder),
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.playlist_add_check_rounded,
                        color: Colors.white70,
                        size: 18,
                      ),
                      SizedBox(width: 8),
                      Text(
                        '下一步',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  if (onViewAll != null)
                    GestureDetector(
                      onTap: onViewAll,
                      child: Text(
                        '全部',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.white.withAlpha(150),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Task list
              if (nextActions.isEmpty)
                _buildEmptyState()
              else
                ...nextActions.map(
                  (task) => _NextActionItem(task: task),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              color: Colors.white.withAlpha(100),
              size: 32,
            ),
            const SizedBox(height: 8),
            Text(
              '暂无待办任务',
              style: TextStyle(
                fontSize: 13,
                color: Colors.white.withAlpha(150),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NextActionItem extends ConsumerWidget {
  final TaskData task;

  const _NextActionItem({required this.task});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(10),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          // Type indicator
          Container(
            width: 4,
            height: 32,
            decoration: BoxDecoration(
              color: _getTypeColor(task.type),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 12),

          // Task info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  task.title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: Colors.white,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Icon(
                      Icons.timer_outlined,
                      size: 12,
                      color: Colors.white.withAlpha(120),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${task.estimatedMinutes}min',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.white.withAlpha(120),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Complete button
          GestureDetector(
            onTap: () async {
              await ref.read(taskListProvider.notifier).completeTask(
                    task.id,
                    task.estimatedMinutes,
                    null,
                  );
              // Refresh dashboard
              ref.read(dashboardProvider.notifier).refresh();
            },
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(15),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.check_rounded,
                color: Colors.white70,
                size: 18,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'learning':
        return AppDesignTokens.info;
      case 'training':
        return AppDesignTokens.success;
      case 'error_fix':
        return AppDesignTokens.error;
      case 'reflection':
        return AppDesignTokens.prismPurple;
      default:
        return AppDesignTokens.neutral400;
    }
  }
}
