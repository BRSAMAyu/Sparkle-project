import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/interactive_task_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Priority view - Tasks sorted by priority
class PriorityView extends ConsumerWidget {
  const PriorityView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasks = ref.watch(priorityTasksProvider);

    if (tasks.isEmpty) {
      return _buildEmptyState(context);
    }

    // Group by priority ranges
    final highPriority = <TaskModel>[];
    final mediumPriority = <TaskModel>[];
    final lowPriority = <TaskModel>[];

    for (final task in tasks) {
      if (task.priority >= 8) {
        highPriority.add(task);
      } else if (task.priority >= 5) {
        mediumPriority.add(task);
      } else {
        lowPriority.add(task);
      }
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: 3,
      separatorBuilder: (context, index) => const SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) {
        switch (index) {
          case 0:
            return highPriority.isNotEmpty
                ? _PrioritySection(
                    title: '高优先级',
                    color: DS.error,
                    tasks: highPriority,
                  )
                : const SizedBox.shrink();
          case 1:
            return mediumPriority.isNotEmpty
                ? _PrioritySection(
                    title: '中优先级',
                    color: DS.warning,
                    tasks: mediumPriority,
                  )
                : const SizedBox.shrink();
          case 2:
            return lowPriority.isNotEmpty
                ? _PrioritySection(
                    title: '低优先级',
                    color: DS.success,
                    tasks: lowPriority,
                  )
                : const SizedBox.shrink();
          default:
            return const SizedBox.shrink();
        }
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing32),
      child: Column(
        children: [
          Icon(
            Icons.flag_rounded,
            size: 48,
            color: DS.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '暂无任务',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _PrioritySection extends StatelessWidget {
  const _PrioritySection({
    required this.title,
    required this.color,
    required this.tasks,
  });

  final String title;
  final Color color;
  final List<TaskModel> tasks;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header with colored indicator
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.spacing4, DS.spacing4, DS.spacing12, DS.spacing8),
          child: Row(
            children: [
              Container(
                width: 4,
                height: 16,
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: DS.borderRadius4,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '$title (${tasks.length})',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        // Tasks
        ...tasks.map((task) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: InteractiveTaskCard(task: task),
            )),
      ],
    );
  }
}
