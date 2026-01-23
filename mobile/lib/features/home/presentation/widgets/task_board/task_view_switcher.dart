import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';

/// Task view switcher - Tab switcher for task board views
class TaskViewSwitcher extends ConsumerWidget {
  const TaskViewSwitcher({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boardState = ref.watch(taskBoardProvider);
    final currentView = boardState.currentView;

    return MaterialStyler(
      material: AppMaterials.neoGlass.copyWith(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.5),
      ),
      borderRadius: DS.borderRadiusFull,
      padding: const EdgeInsets.all(DS.spacing4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: TaskViewMode.values.map((mode) {
          final isSelected = currentView == mode;
          return _ViewTab(
            mode: mode,
            isSelected: isSelected,
            onTap: () => ref.read(taskBoardProvider.notifier).switchView(mode),
          );
        }).toList(),
      ),
    );
  }
}

class _ViewTab extends StatelessWidget {
  const _ViewTab({
    required this.mode,
    required this.isSelected,
    required this.onTap,
  });

  final TaskViewMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: DS.quick,
      curve: DS.curveEaseOut,
      decoration: BoxDecoration(
        color: isSelected ? DS.brandPrimary : Colors.transparent,
        borderRadius: DS.borderRadiusFull,
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadiusFull,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing8,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getIcon(mode),
                size: DS.iconSizeSm,
                color: isSelected ? DS.onBrandPrimary : DS.textSecondary,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                _getLabel(mode),
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: isSelected ? DS.onBrandPrimary : DS.textSecondary,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _getIcon(TaskViewMode mode) {
    return switch (mode) {
      TaskViewMode.schedule => Icons.calendar_today_rounded,
      TaskViewMode.priority => Icons.flag_rounded,
      TaskViewMode.plan => Icons.view_week_rounded,
    };
  }

  String _getLabel(TaskViewMode mode) {
    return switch (mode) {
      TaskViewMode.schedule => '日程',
      TaskViewMode.priority => '重要性',
      TaskViewMode.plan => '方案',
    };
  }
}
