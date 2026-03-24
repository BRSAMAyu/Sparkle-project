import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/interactive_task_card.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_actions_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/sprint_actions_dialog.dart';
import 'package:sparkle/features/plan/presentation/widgets/sprint_statistics_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Sprint view - 显示当前活跃冲刺的任务
class SprintView extends ConsumerWidget {
  const SprintView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final sprintTasks = ref.watch(sprintTasksProvider);

    // 没有活跃冲刺
    if (dashboardState.sprint == null) {
      return _buildNoSprintState(context);
    }

    // 冲刺有任务
    if (sprintTasks.isNotEmpty) {
      return _buildSprintTasks(
          context, ref, sprintTasks, dashboardState.sprint!,);
    }

    // 冲刺无任务
    return _buildEmptySprintState(context, dashboardState.sprint!);
  }

  Widget _buildNoSprintState(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing32),
        child: Column(
          children: [
            Icon(
              Icons.flash_on_rounded,
              size: 48,
              color: DS.textSecondary.withValues(alpha: 0.5),
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              '暂无活跃冲刺',
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );

  Widget _buildSprintTasks(
    BuildContext context,
    WidgetRef ref,
    List<TaskModel> tasks,
    SprintData sprint,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Sprint header
          _SprintHeader(sprint: sprint, taskCount: tasks.length),
          const SizedBox(height: DS.spacing12),
          // Filter chips
          const _SprintFilterChips(),
          const SizedBox(height: DS.spacing12),
          // Statistics card
          const SprintStatisticsCard(),
          const SizedBox(height: DS.spacing12),
          // Task list
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            padding: EdgeInsets.zero,
            itemCount: tasks.length,
            separatorBuilder: (context, index) =>
                const SizedBox(height: DS.spacing8),
            itemBuilder: (context, index) =>
                InteractiveTaskCard(task: tasks[index]),
          ),
        ],
      );

  Widget _buildEmptySprintState(BuildContext context, SprintData sprint) =>
      Container(
        padding: const EdgeInsets.all(DS.spacing32),
        child: Column(
          children: [
            Icon(
              Icons.check_circle_outline_rounded,
              size: 48,
              color: DS.brandPrimary.withValues(alpha: 0.5),
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              '${sprint.name} 暂无待办任务',
              style: context.sparkleTypography.bodyMedium.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );
}

class _SprintHeader extends ConsumerWidget {
  const _SprintHeader({
    required this.sprint,
    required this.taskCount,
  });

  final SprintData sprint;
  final int taskCount;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.2),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.15),
                borderRadius: DS.borderRadius8,
              ),
              child: Icon(
                Icons.flash_on_rounded,
                size: DS.iconSizeSm,
                color: DS.brandPrimaryConst,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    sprint.name,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    '剩余 $taskCount 个任务 · ${sprint.daysLeft} 天',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            // History button
            SparkleIconButton(
              icon: const Icon(Icons.history_rounded),
              onPressed: () => context.push(PlanRoutes.sprintHistory),
              variant: ButtonVariant.ghost,
              semanticLabel: '冲刺历史',
            ),
            const SizedBox(width: DS.spacing4),
            // Actions menu button
            PopupMenuButton<String>(
              icon: Icon(
                Icons.more_vert_rounded,
                color: DS.brandPrimaryConst,
              ),
              tooltip: '更多操作',
              padding: const EdgeInsets.all(DS.spacing4),
              constraints: const BoxConstraints(
                minWidth: 36,
                minHeight: 36,
              ),
              style: IconButton.styleFrom(
                backgroundColor: DS.surfaceSecondary,
                foregroundColor: DS.brandPrimary,
              ),
              onSelected: (value) => _handleMenuSelection(
                  context, ref, value, sprint.id, sprint.name,),
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'complete',
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_rounded,
                          color: DS.semanticSuccess,),
                      const SizedBox(width: DS.spacing12),
                      const Text('完成冲刺'),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: 'extend',
                  child: Row(
                    children: [
                      Icon(Icons.date_range_rounded, color: DS.info),
                      const SizedBox(width: DS.spacing12),
                      const Text('延长冲刺'),
                    ],
                  ),
                ),
                PopupMenuItem(
                  value: 'abandon',
                  child: Row(
                    children: [
                      Icon(Icons.cancel_rounded, color: DS.semanticError),
                      const SizedBox(width: DS.spacing12),
                      const Text('放弃冲刺'),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(width: DS.spacing4),
            // Progress indicator — constrained to prevent overflow
            SizedBox(
              width: 36,
              height: 36,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 36,
                    height: 36,
                    child: CircularProgressIndicator(
                      value: sprint.progress,
                      strokeWidth: 3,
                      backgroundColor: DS.surfaceSecondary,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                    ),
                  ),
                  Text(
                    '${(sprint.progress * 100).toInt()}%',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textPrimary,
                      fontWeight: FontWeight.w600,
                      fontSize: 9,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Future<void> _handleMenuSelection(
    BuildContext context,
    WidgetRef ref,
    String value,
    String planId,
    String planName,
  ) async {
    switch (value) {
      case 'complete':
        final confirmed = await showConfirmCompleteDialog(
          context,
          planName: planName,
        );
        if (confirmed) {
          await ref.read(sprintActionsProvider.notifier).completeSprint(planId);
        }
      case 'extend':
        final days = await showExtendSprintDialog(
          context,
          planName: planName,
        );
        if (days != null && days > 0) {
          await ref
              .read(sprintActionsProvider.notifier)
              .extendSprint(planId, days);
        }
      case 'abandon':
        final confirmed = await showConfirmAbandonDialog(
          context,
          planName: planName,
        );
        if (confirmed) {
          await ref
              .read(sprintActionsProvider.notifier)
              .abandonSprint(planId, '');
        }
    }
  }
}

/// Sprint filter chips widget
class _SprintFilterChips extends ConsumerWidget {
  const _SprintFilterChips();

  static const _filterLabels = {
    SprintTaskFilter.all: '全部',
    SprintTaskFilter.todo: '待办',
    SprintTaskFilter.inProgress: '进行中',
    SprintTaskFilter.done: '已完成',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentFilter =
        ref.watch(taskBoardProvider.select((s) => s.sprintFilter));
    final counts = ref.watch(sprintTaskCountsProvider);

    return Wrap(
      spacing: DS.spacing8,
      runSpacing: DS.spacing8,
      children: SprintTaskFilter.values.map((filter) {
        final isSelected = currentFilter == filter;
        final count = counts[filter] ?? 0;

        return GestureDetector(
          onTap: () =>
              ref.read(taskBoardProvider.notifier).setSprintFilter(filter),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing6,
            ),
            decoration: BoxDecoration(
              color: isSelected ? DS.brandPrimary : DS.surfaceSecondary,
              borderRadius: DS.borderRadiusFull,
              border: Border.all(
                color: isSelected ? DS.brandPrimary : DS.border,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _filterLabels[filter] ?? '',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: isSelected ? DS.onBrandPrimary : DS.textSecondary,
                    fontWeight:
                        isSelected ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
                if (count > 0) ...[
                  const SizedBox(width: DS.spacing4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing4,
                      vertical: 1,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? DS.white.withValues(alpha: 0.2)
                          : DS.surfaceTertiary,
                      borderRadius: DS.borderRadius8,
                    ),
                    child: Text(
                      count.toString(),
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color:
                            isSelected ? DS.onBrandPrimary : DS.textSecondary,
                        fontSize: 10,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}
