import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class MetricsRow extends ConsumerWidget {
  const MetricsRow({
    required this.dashboardState,
    super.key,
  });

  final DashboardState dashboardState;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final streakStats = ref.watch(streakStatsProvider);
    final taskState = ref.watch(taskListProvider);
    final taskMetric = _buildTaskMetric(taskState, dashboardState);

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: MaterialStyler(
          material: AppMaterials.ceramic,
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing8),
          child: SizedBox(
            height: 64,
            child: Row(
              children: [
                Expanded(
                  child: _MetricCell(
                    value: _formatFocusTime(
                      dashboardState.flame.todayFocusMinutes,
                    ),
                    label: '今日专注',
                    icon: Icons.center_focus_strong_rounded,
                    color: DS.brandPrimary,
                    onTap: () => context.push('/focus'),
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _MetricCell(
                    value: taskMetric.primary,
                    label: '今日任务',
                    icon: Icons.task_alt_rounded,
                    color: DS.success,
                    onTap: () => context.push('/tasks'),
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _MetricCell(
                    value: '${streakStats.currentStreak}天',
                    label: '连胜',
                    icon: Icons.local_fire_department_rounded,
                    color: DS.warning,
                    onTap: () => context.push('/achievements'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  _TaskMetric _buildTaskMetric(
    TaskListState taskState,
    DashboardState dashboard,
  ) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);

    bool isSameDay(DateTime? value) =>
        value != null &&
        value.year == today.year &&
        value.month == today.month &&
        value.day == today.day;

    final todayTasks = taskState.tasks
        .where((task) => isSameDay(task.dueDate) || isSameDay(task.completedAt))
        .toList();

    final completedToday = todayTasks
        .where(
          (task) =>
              task.status == TaskStatus.completed &&
              isSameDay(task.completedAt),
        )
        .length;

    if (todayTasks.isNotEmpty) {
      return _TaskMetric(
        primary: '$completedToday/${todayTasks.length}',
      );
    }

    if (dashboard.nextActions.isNotEmpty) {
      return _TaskMetric(primary: '0/${dashboard.nextActions.length}');
    }

    return const _TaskMetric(primary: '0/0');
  }

  String _formatFocusTime(int minutes) {
    if (minutes < 60) return '${minutes}m';
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    return mins > 0 ? '${hours}h${mins}m' : '${hours}h';
  }
}

class _MetricCell extends StatelessWidget {
  const _MetricCell({
    required this.value,
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String value;
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing10,
          ),
          child: Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, size: 16, color: color),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.titleLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}

class _MetricDivider extends StatelessWidget {
  const _MetricDivider();

  @override
  Widget build(BuildContext context) => Container(
        width: 1,
        margin: const EdgeInsets.symmetric(vertical: DS.spacing12),
        color: DS.borderSubtle,
      );
}

class _TaskMetric {
  const _TaskMetric({required this.primary});

  final String primary;
}
