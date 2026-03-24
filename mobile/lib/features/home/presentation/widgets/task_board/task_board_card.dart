import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/plan_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/priority_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/schedule_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/sprint_view.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_view_switcher.dart';

/// Task board card - Main container with view switcher and content
class TaskBoardCard extends ConsumerStatefulWidget {
  const TaskBoardCard({super.key});

  @override
  ConsumerState<TaskBoardCard> createState() => _TaskBoardCardState();
}

class _TaskBoardCardState extends ConsumerState<TaskBoardCard> {
  bool _isCollapsed = true;

  void _toggleCollapsed() {
    setState(() {
      _isCollapsed = !_isCollapsed;
    });
  }

  @override
  Widget build(BuildContext context) {
    final boardState = ref.watch(taskBoardProvider);
    final summary = ref.watch(taskBoardTodaySummaryProvider);
    final isDualColumn = context.isTablet || context.isDesktop;

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing12,
      ),
      child: DashboardEntrance(
        index: 8,
        child: MaterialStyler(
          material: AppMaterials.ceramic,
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _TaskBoardHeader(
                summary: summary.label,
                isCollapsed: _isCollapsed,
                onToggle: _toggleCollapsed,
                onOpenTasks: () => context.push('/tasks'),
              ),
              ClipRect(
                child: AnimatedSize(
                  duration: DS.quick,
                  curve: DS.motionCurve(SparkleMotionToken.standard),
                  alignment: Alignment.topCenter,
                  child: _isCollapsed
                      ? const SizedBox.shrink()
                      : Padding(
                          padding: const EdgeInsets.only(top: DS.spacing12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildBoardControls(context),
                              const SizedBox(height: DS.spacing12),
                              AnimatedSwitcher(
                                duration: DS.quick,
                                switchInCurve: DS.motionCurve(
                                  SparkleMotionToken.standard,
                                ),
                                switchOutCurve: DS.motionCurve(
                                  SparkleMotionToken.standard,
                                ),
                                transitionBuilder: (child, animation) =>
                                    FadeTransition(
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
                                    ? _buildDualColumnView(
                                        boardState.currentView,
                                      )
                                    : _buildView(boardState.currentView),
                              ),
                            ],
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBoardControls(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final isMobile = ResponsiveSystem.isMobile(context);
          final switcherMinWidth = isMobile ? 260.0 : 320.0;

          if (isMobile) {
            return const TaskViewSwitcher();
          }

          return Align(
            alignment: Alignment.centerRight,
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minWidth: switcherMinWidth,
                maxWidth: 400,
              ),
              child: const TaskViewSwitcher(),
            ),
          );
        },
      );

  Widget _buildView(TaskViewMode mode) => KeyedSubtree(
        key: ValueKey(mode),
        child: switch (mode) {
          TaskViewMode.schedule => const ScheduleView(),
          TaskViewMode.priority => const PriorityView(),
          TaskViewMode.plan => const PlanView(),
          TaskViewMode.sprint => const SprintView(),
        },
      );

  /// Dual-column layout for tablet/desktop
  Widget _buildDualColumnView(TaskViewMode mode) => KeyedSubtree(
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

  Widget _buildSidePanel(BuildContext context, TaskViewMode mode) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: DS.borderRadius16,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _panelTitle(mode),
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

  String _panelTitle(TaskViewMode mode) => switch (mode) {
        TaskViewMode.plan => '计划管理',
        _ => '提示',
      };

  Widget _buildPanelContent(TaskViewMode mode) => switch (mode) {
        TaskViewMode.schedule => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const _PanelItem(
                icon: Icons.calendar_today_rounded,
                title: '按日期查看',
                description: '任务按到期日期分组显示',
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.warning_rounded,
                title: '逾期任务',
                description: '红色高亮显示已逾期的任务',
                color: DS.semanticError,
              ),
            ],
          ),
        TaskViewMode.priority => const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flag_rounded,
                title: '优先级排序',
                description: '高优先级任务显示在前面',
              ),
              SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.tune_rounded,
                title: '自定义优先级',
                description: '在任务编辑中调整优先级',
              ),
            ],
          ),
        TaskViewMode.plan => const DashboardPlanManager(compact: true),
        TaskViewMode.sprint => const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flash_on_rounded,
                title: '冲刺专注模式',
                description: '只显示当前冲刺的任务',
              ),
              SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.timer_rounded,
                title: '冲刺计时',
                description: '关注剩余天数和进度',
              ),
            ],
          ),
      };
}

class _TaskBoardHeader extends StatelessWidget {
  const _TaskBoardHeader({
    required this.summary,
    required this.isCollapsed,
    required this.onToggle,
    required this.onOpenTasks,
  });

  final String summary;
  final bool isCollapsed;
  final VoidCallback onToggle;
  final VoidCallback onOpenTasks;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final isCompact = constraints.maxWidth < 360;
          final trailingLabel = isCollapsed ? '展开' : '收起';

          if (isCompact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _HeaderTitle(onOpenTasks: onOpenTasks),
                    const Spacer(),
                    _HeaderToggleButton(
                      label: trailingLabel,
                      isCollapsed: isCollapsed,
                      onTap: onToggle,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing6),
                Text(
                  summary,
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
            );
          }

          return Row(
            children: [
              _HeaderTitle(onOpenTasks: onOpenTasks),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  summary,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              _HeaderToggleButton(
                label: trailingLabel,
                isCollapsed: isCollapsed,
                onTap: onToggle,
              ),
            ],
          );
        },
      );
}

class _HeaderTitle extends StatelessWidget {
  const _HeaderTitle({required this.onOpenTasks});

  final VoidCallback onOpenTasks;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onOpenTasks,
        borderRadius: BorderRadius.circular(999),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing4,
            vertical: DS.spacing4,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.dashboard_customize_rounded,
                color: DS.brandPrimary,
                size: 18,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '任务看板',
                style: context.sparkleTypography.titleLarge.copyWith(
                  fontWeight: FontWeight.w600,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ),
      );
}

class _HeaderToggleButton extends StatelessWidget {
  const _HeaderToggleButton({
    required this.label,
    required this.isCollapsed,
    required this.onTap,
  });

  final String label;
  final bool isCollapsed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => TextButton.icon(
        onPressed: onTap,
        icon: AnimatedRotation(
          turns: isCollapsed ? 0 : 0.5,
          duration: DS.quick,
          curve: DS.motionCurve(SparkleMotionToken.standard),
          child: const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
        ),
        label: Text(label),
      );
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
            color: DS.surfaceOverlay,
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
