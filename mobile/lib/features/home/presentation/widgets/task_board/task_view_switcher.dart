import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';

/// Task view switcher - Tab switcher for task board views
/// Responsive design with larger touch targets for better usability
class TaskViewSwitcher extends ConsumerWidget {
  const TaskViewSwitcher({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boardState = ref.watch(taskBoardProvider);
    final currentView = boardState.currentView;
    final isMobile = ResponsiveSystem.isMobile(context);
    final brightness = Theme.of(context).brightness;

    // Responsive sizing
    final height = isMobile ? 36.0 : 42.0;
    final fontSize = isMobile ? DS.fontSizeSm : DS.fontSizeBase;
    final iconSize = isMobile ? 18.0 : DS.iconSizeBase;
    final horizontalPadding = isMobile ? DS.spacing12 : DS.spacing16;

    return MaterialStyler(
      key: ValueKey('task_view_switcher_$brightness'),
      material: AppMaterials.neoGlass(context).copyWith(
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0.5),
      ),
      borderRadius: DS.borderRadius16,
      padding: const EdgeInsets.all(DS.spacing4),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // Use expanded layout if width allows, otherwise scrollable
          final useExpanded = constraints.maxWidth >= 320;

          if (useExpanded && !isMobile) {
            // Tablet/Desktop: Equal width tabs
            return Row(
              children: TaskViewMode.values.map((mode) {
                final isSelected = currentView == mode;
                return Expanded(
                  child: _ViewTab(
                    key: ValueKey('view_tab_${mode.name}_$brightness'),
                    mode: mode,
                    isSelected: isSelected,
                    height: height,
                    fontSize: fontSize,
                    iconSize: iconSize,
                    horizontalPadding: horizontalPadding,
                    onTap: () =>
                        ref.read(taskBoardProvider.notifier).switchView(mode),
                  ),
                );
              }).toList(),
            );
          }

          // Mobile: Scrollable row with minimum width
          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: TaskViewMode.values.map((mode) {
                final isSelected = currentView == mode;
                return _ViewTab(
                  key: ValueKey('view_tab_${mode.name}_$brightness'),
                  mode: mode,
                  isSelected: isSelected,
                  height: height,
                  fontSize: fontSize,
                  iconSize: iconSize,
                  horizontalPadding: horizontalPadding,
                  onTap: () =>
                      ref.read(taskBoardProvider.notifier).switchView(mode),
                );
              }).toList(),
            ),
          );
        },
      ),
    );
  }
}

class _ViewTab extends StatelessWidget {
  const _ViewTab({
    required this.mode,
    required this.isSelected,
    required this.height,
    required this.fontSize,
    required this.iconSize,
    required this.horizontalPadding,
    required this.onTap,
    super.key,
  });

  final TaskViewMode mode;
  final bool isSelected;
  final double height;
  final double fontSize;
  final double iconSize;
  final double horizontalPadding;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    // Get colors dynamically based on current theme
    final selectedColor = DS.brandPrimary;
    final unselectedColor = DS.surfacePrimary.withValues(alpha: 0);
    final selectedTextColor = DS.onBrandPrimary;
    final unselectedTextColor = DS.textSecondary;

    return AnimatedContainer(
      duration: DS.quick,
      curve: DS.curveEaseOut,
      height: height,
      decoration: BoxDecoration(
        color: isSelected ? selectedColor : unselectedColor,
        borderRadius: DS.borderRadius12,
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius12,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: horizontalPadding),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getIcon(mode),
                size: iconSize,
                color: isSelected ? selectedTextColor : unselectedTextColor,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                _getLabel(mode),
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: isSelected ? selectedTextColor : unselectedTextColor,
                  fontWeight: isSelected ? DS.fontWeightSemibold : DS.fontWeightMedium,
                  fontSize: fontSize,
                ),
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _getIcon(TaskViewMode mode) => switch (mode) {
        TaskViewMode.schedule => Icons.calendar_today_rounded,
        TaskViewMode.priority => Icons.flag_rounded,
        TaskViewMode.plan => Icons.view_week_rounded,
        TaskViewMode.sprint => Icons.flash_on_rounded,
      };

  String _getLabel(TaskViewMode mode) => switch (mode) {
        TaskViewMode.schedule => '日程',
        TaskViewMode.priority => '重要性',
        TaskViewMode.plan => '方案',
        TaskViewMode.sprint => '冲刺',
      };
}
