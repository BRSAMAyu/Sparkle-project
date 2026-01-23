import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/responsive_layout.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/plan_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/priority_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/schedule_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_view_switcher.dart';

/// Task board card - Main container with view switcher and content
class TaskBoardCard extends ConsumerWidget {
  const TaskBoardCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final boardState = ref.watch(taskBoardProvider);
    final layoutType = getLayoutType(context);
    final isDualColumn = layoutType == LayoutType.tablet || layoutType == LayoutType.desktop;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: MaterialStyler(
        material: AppMaterials.ceramic,
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with title and view switcher
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '任务看板',
                  style: context.sparkleTypography.titleLarge.copyWith(
                    fontWeight: FontWeight.w600,
                    color: DS.textPrimary,
                  ),
                ),
                const TaskViewSwitcher(),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            // Content based on current view with optional dual-column layout
            AnimatedSwitcher(
              duration: DS.quick,
              transitionBuilder: (child, animation) => FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, 0.05),
                    end: Offset.zero,
                  ).animate(animation),
                  child: child,
                ),
              ),
              child: isDualColumn
                  ? _buildDualColumnView(boardState.currentView)
                  : _buildView(boardState.currentView),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildView(TaskViewMode mode) {
    return KeyedSubtree(
      key: ValueKey(mode),
      child: switch (mode) {
        TaskViewMode.schedule => const ScheduleView(),
        TaskViewMode.priority => const PriorityView(),
        TaskViewMode.plan => const PlanView(),
      },
    );
  }

  /// Dual-column layout for tablet/desktop
  Widget _buildDualColumnView(TaskViewMode mode) {
    return KeyedSubtree(
      key: ValueKey('${mode}_dual'),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // Only use dual-column if width is sufficient
          if (constraints.maxWidth < 600) {
            return _buildView(mode);
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _buildView(mode),
              ),
              const SizedBox(width: DS.spacing16),
              // Right column: Quick stats or related info
              SizedBox(
                width: 280,
                child: _buildSidePanel(context, mode),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSidePanel(BuildContext context, TaskViewMode mode) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfacePrimary.withValues(alpha: 0.5),
        borderRadius: DS.borderRadius16,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '提示',
            style: context.sparkleTypography.labelLarge.copyWith(
              color: DS.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          _buildPanelContent(mode),
        ],
      ),
    );
  }

  Widget _buildPanelContent(TaskViewMode mode) {
    return switch (mode) {
      TaskViewMode.schedule => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _PanelItem(
              icon: Icons.calendar_today_rounded,
              title: '按日期查看',
              description: '任务按到期日期分组显示',
            ),
            const SizedBox(height: DS.spacing12),
            _PanelItem(
              icon: Icons.warning_rounded,
              title: '逾期任务',
              description: '红色高亮显示已逾期的任务',
              color: DS.error,
            ),
          ],
        ),
      TaskViewMode.priority => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _PanelItem(
              icon: Icons.flag_rounded,
              title: '优先级排序',
              description: '高优先级任务显示在前面',
            ),
            const SizedBox(height: DS.spacing12),
            _PanelItem(
              icon: Icons.tune_rounded,
              title: '自定义优先级',
              description: '在任务编辑中调整优先级',
            ),
          ],
        ),
      TaskViewMode.plan => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _PanelItem(
              icon: Icons.folder_rounded,
              title: '按方案分组',
              description: '任务按所属方案分组显示',
            ),
            const SizedBox(height: DS.spacing12),
            _PanelItem(
              icon: Icons.add_circle_outline_rounded,
              title: '创建方案',
              description: '将任务组织到学习方案中',
            ),
          ],
        ),
    };
  }
}

class _PanelItem extends StatelessWidget {
  const _PanelItem({
    required this.icon,
    required this.title,
    required this.description,
    this.color,
  });

  final IconData icon;
  final String title;
  final String description;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final itemColor = color ?? DS.brandPrimary;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(DS.spacing8),
          decoration: BoxDecoration(
            color: itemColor.withValues(alpha: 0.12),
            borderRadius: DS.borderRadius12,
          ),
          child: Icon(
            icon,
            size: DS.iconSizeSm,
            color: itemColor,
          ),
        ),
        const SizedBox(width: DS.spacing12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                description,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
