import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class MetricsRow extends ConsumerWidget {
  const MetricsRow({
    required this.dashboardState,
    super.key,
  });

  final DashboardState dashboardState;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');
    final l10n = AppLocalizations.of(context)!;
    final streakStats = ref.watch(streakStatsProvider);
    final taskState = ref.watch(taskListProvider);
    final taskMetric = _buildTaskMetric(taskState, dashboardState);
    final textScale = MediaQuery.textScalerOf(context).scale(1);
    final compactMode = textScale >= 1.2;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          tone: DashboardSurfaceTone.summary,
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing8),
          child: SizedBox(
            height: compactMode ? 82 : 72,
            child: Row(
              children: [
                Expanded(
                  child: DashboardEntrance(
                    index: 1,
                    stagger: const Duration(milliseconds: 80),
                    slideOffset: const Offset(0, 0.05),
                    child: _MetricCell(
                      value: _formatFocusTime(
                        dashboardState.flame.todayFocusMinutes,
                      ),
                      label: context.l10n.metricsTodayFocus,
                      icon: Icons.center_focus_strong_rounded,
                      color: DS.brandPrimary,
                      compact: compactMode,
                      onTap: () => context.push('/focus'),
                    ),
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: DashboardEntrance(
                    index: 2,
                    stagger: const Duration(milliseconds: 80),
                    slideOffset: const Offset(0, 0.05),
                    child: _MetricCell(
                      value: taskMetric.primary,
                      label: context.l10n.metricsTodayTasks,
                      icon: Icons.task_alt_rounded,
                      color: DS.success,
                      compact: compactMode,
                      onTap: () => context.push('/tasks'),
                    ),
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: DashboardEntrance(
                    index: 3,
                    stagger: const Duration(milliseconds: 80),
                    slideOffset: const Offset(0, 0.05),
                    child: _MetricCell(
                      value: isChinese
                          ? '${streakStats.currentStreak}天'
                          : l10n.streakDays(streakStats.currentStreak),
                      label: l10n.winStreak,
                      icon: Icons.local_fire_department_rounded,
                      color: DS.warning,
                      compact: compactMode,
                      onTap: () => context.push('/achievements'),
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
    required this.compact,
    required this.onTap,
  });

  final String value;
  final String label;
  final IconData icon;
  final Color color;
  final bool compact;
  final VoidCallback onTap;

  Color _backgroundColor() {
    if (color == DS.brandPrimary) {
      return Color.lerp(DS.surfaceSecondary, DS.brandPrimary, 0.12)!;
    }
    if (color == DS.success) {
      return Color.lerp(DS.surfaceSecondary, DS.success, 0.12)!;
    }
    if (color == DS.warning) {
      return Color.lerp(DS.surfaceSecondary, DS.warning, 0.12)!;
    }
    return DS.surfacePanel;
  }

  @override
  Widget build(BuildContext context) => DashboardPressable(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        pressedScale: 0.97,
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
                  color: _backgroundColor(),
                  borderRadius: DS.borderRadius12,
                  border: Border.all(
                    color: color.withValues(alpha: 0.14),
                  ),
                ),
                child: Icon(icon, size: 16, color: color),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AnimatedSwitcher(
                      duration: DS.durationFast,
                      switchInCurve: DS.motionCurve(SparkleMotionToken.micro),
                      switchOutCurve: DS.motionCurve(SparkleMotionToken.micro),
                      transitionBuilder: (child, animation) => FadeTransition(
                        opacity: animation,
                        child: child,
                      ),
                      child: Text(
                        value,
                        key: ValueKey(value),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: (compact
                                ? context.sparkleTypography.bodyLarge
                                : context.sparkleTypography.titleLarge)
                            .copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
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
