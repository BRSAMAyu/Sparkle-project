import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/plan_name_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/interactive_task_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Plan view - Tasks grouped by plan
class PlanView extends ConsumerWidget {
  const PlanView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planGroups = ref.watch(planGroupsProvider);

    if (planGroups.isEmpty) {
      return _buildEmptyState(context);
    }

    // Sort: null (no plan) last, named plans first
    final sortedKeys = planGroups.keys.toList()
      ..sort((a, b) {
        if (a == null) return 1;
        if (b == null) return -1;
        return a.compareTo(b);
      });

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: sortedKeys.length,
      separatorBuilder: (context, index) => const SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) {
        final planId = sortedKeys[index];
        final tasks = planGroups[planId]!;
        return _PlanSection(planId: planId, tasks: tasks);
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.spacing32),
      child: Column(
        children: [
          Icon(
            Icons.view_week_rounded,
            size: 48,
            color: DS.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '暂无方案任务',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
        ],
      ),
    );
}

class _PlanSection extends ConsumerWidget {
  const _PlanSection({
    required this.planId,
    required this.tasks,
  });

  final String? planId;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 获取计划名称，优先显示名称而非ID
    final planName = (planId != null && planId!.isNotEmpty)
        ? ref.watch(planNameProvider(planId!))
        : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.spacing4, DS.spacing4, DS.spacing12, DS.spacing8),
          child: Row(
            children: [
              Icon(
                Icons.folder_rounded,
                size: 16,
                color: DS.brandPrimary,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                planName ?? planId ?? '未分类',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: (planName != null || planId != null)
                      ? DS.textPrimary
                      : DS.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  '${tasks.length}',
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        // Tasks
        ...tasks.map((task) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: InteractiveTaskCard(task: task),
            ),),
      ],
    );
  }
}
