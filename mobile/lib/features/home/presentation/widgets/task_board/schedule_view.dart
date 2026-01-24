import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/interactive_task_card.dart';

/// Schedule view - Tasks grouped by due date
class ScheduleView extends ConsumerWidget {
  const ScheduleView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groups = ref.watch(scheduleGroupsProvider);

    if (groups.isEmpty || (groups.length == 1 && groups.first.isEmpty)) {
      return _buildEmptyState(context);
    }

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: groups.length,
      separatorBuilder: (context, index) => const SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) {
        final group = groups[index];
        return _ScheduleGroup(group: group);
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing32),
      child: Column(
        children: [
          Icon(
            Icons.event_available_rounded,
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
          const SizedBox(height: DS.spacing6),
          Text(
            '在 OmniBar 中输入创建新任务',
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}

class _ScheduleGroup extends StatelessWidget {
  const _ScheduleGroup({required this.group});

  final ScheduleGroup group;

  @override
  Widget build(BuildContext context) {
    if (group.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Group header
        Padding(
          padding: const EdgeInsets.fromLTRB(DS.spacing4, DS.spacing4, DS.spacing12, DS.spacing8),
          child: Text(
            group.title,
            style: context.sparkleTypography.labelLarge.copyWith(
              color: DS.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        // Tasks in this group
        ...group.tasks.map((task) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: InteractiveTaskCard(task: task),
            )),
      ],
    );
  }
}
