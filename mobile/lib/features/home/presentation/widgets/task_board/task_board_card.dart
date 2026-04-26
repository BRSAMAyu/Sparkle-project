import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
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
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');
    final summaryLabel = _summaryLabel(summary, isChinese: isChinese);

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing12,
      ),
      child: DashboardEntrance(
        index: 8,
        child: DashboardSectionShell(
          key: const ValueKey('dashboard-task-board-section'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _TaskBoardHeader(
                summary: summaryLabel,
                isCollapsed: _isCollapsed,
                isChinese: isChinese,
                onToggle: _toggleCollapsed,
                onOpenTasks: () => context.push('/tasks'),
              ),
              if (_isCollapsed) ...[
                const SizedBox(height: DS.spacing12),
                _CollapsedWorkspacePreview(
                  summary: summaryLabel,
                  view: boardState.currentView,
                  isChinese: isChinese,
                ),
              ],
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
                                        isChinese: isChinese,
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
  Widget _buildDualColumnView(
    TaskViewMode mode, {
    required bool isChinese,
  }) =>
      KeyedSubtree(
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
                  child: _buildSidePanel(context, mode, isChinese: isChinese),
                ),
              ],
            );
          },
        ),
      );

  Widget _buildSidePanel(
    BuildContext context,
    TaskViewMode mode, {
    required bool isChinese,
  }) =>
      Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _panelTitle(mode, isChinese: isChinese),
              style: context.sparkleTypography.labelLarge.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            _buildPanelContent(mode, isChinese: isChinese),
          ],
        ),
      );

  String _panelTitle(TaskViewMode mode, {required bool isChinese}) =>
      switch (mode) {
        TaskViewMode.plan => isChinese ? '计划管理' : 'Plan Management',
        _ => isChinese ? '提示' : 'Helpful Notes',
      };

  Widget _buildPanelContent(TaskViewMode mode, {required bool isChinese}) =>
      switch (mode) {
        TaskViewMode.schedule => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.calendar_today_rounded,
                title: isChinese ? '按日期查看' : 'Browse by Date',
                description: isChinese
                    ? '任务按到期日期分组显示'
                    : 'Tasks are grouped by due date.',
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.warning_rounded,
                title: isChinese ? '逾期任务' : 'Overdue Tasks',
                description: isChinese
                    ? '红色高亮显示已逾期的任务'
                    : 'Overdue tasks are highlighted in red.',
                color: DS.semanticError,
              ),
            ],
          ),
        TaskViewMode.priority => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flag_rounded,
                title: isChinese ? '优先级排序' : 'Priority Order',
                description: isChinese
                    ? '高优先级任务显示在前面'
                    : 'Higher-priority tasks rise to the top.',
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.tune_rounded,
                title: isChinese ? '自定义优先级' : 'Custom Priority',
                description: isChinese
                    ? '在任务编辑中调整优先级'
                    : 'Adjust task priority from the editor.',
              ),
            ],
          ),
        TaskViewMode.plan => const DashboardPlanManager(compact: true),
        TaskViewMode.sprint => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flash_on_rounded,
                title: isChinese ? '冲刺专注模式' : 'Sprint Focus Mode',
                description: isChinese
                    ? '只显示当前冲刺的任务'
                    : 'Only tasks from the active sprint are shown.',
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.timer_rounded,
                title: isChinese ? '冲刺计时' : 'Sprint Timing',
                description: isChinese
                    ? '关注剩余天数和进度'
                    : 'Keep an eye on remaining days and progress.',
              ),
            ],
          ),
      };

  String _summaryLabel(
    TaskBoardTodaySummary summary, {
    required bool isChinese,
  }) {
    if (summary.totalCount == 0) {
      return isChinese ? '今日无任务' : 'No tasks due today';
    }
    return isChinese
        ? '今日${summary.totalCount}项·已完成${summary.completedCount}'
        : '${summary.completedCount} of ${summary.totalCount} completed today';
  }
}

class _TaskBoardHeader extends StatelessWidget {
  const _TaskBoardHeader({
    required this.summary,
    required this.isCollapsed,
    required this.isChinese,
    required this.onToggle,
    required this.onOpenTasks,
  });

  final String summary;
  final bool isCollapsed;
  final bool isChinese;
  final VoidCallback onToggle;
  final VoidCallback onOpenTasks;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onOpenTasks,
        borderRadius: DS.borderRadius16,
        child: DashboardSectionHeader(
          icon: Icons.dashboard_customize_rounded,
          accentColor: DS.brandPrimary,
          title: isChinese ? '任务看板' : 'Task Board',
          summary: summary,
          trailing: _HeaderToggleButton(
            isCollapsed: isCollapsed,
            onTap: onToggle,
            isChinese: isChinese,
          ),
        ),
      );
}

class _HeaderToggleButton extends StatelessWidget {
  const _HeaderToggleButton({
    required this.isCollapsed,
    required this.isChinese,
    required this.onTap,
  });

  final bool isCollapsed;
  final bool isChinese;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => TextButton.icon(
        key: const ValueKey('dashboard-task-board-toggle'),
        onPressed: onTap,
        style: TextButton.styleFrom(
          visualDensity: VisualDensity.compact,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
        ),
        icon: AnimatedRotation(
          turns: isCollapsed ? 0 : 0.5,
          duration: DS.quick,
          curve: DS.motionCurve(SparkleMotionToken.standard),
          child: const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
        ),
        label: Text(
          isCollapsed
              ? (isChinese ? '展开' : 'Expand')
              : (isChinese ? '收起' : 'Collapse'),
        ),
      );
}

class _CollapsedWorkspacePreview extends StatelessWidget {
  const _CollapsedWorkspacePreview({
    required this.summary,
    required this.view,
    required this.isChinese,
  });

  final String summary;
  final TaskViewMode view;
  final bool isChinese;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isChinese ? '工作区摘要' : 'Workspace Summary',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    summary,
                    style: context.sparkleTypography.bodyMedium.copyWith(
                      color: DS.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing10),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing6,
              ),
              decoration: BoxDecoration(
                color: DS.surfaceOverlay,
                borderRadius: DS.borderRadiusFull,
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Text(
                _viewLabel(view, isChinese: isChinese),
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
          ],
        ),
      );

  String _viewLabel(TaskViewMode view, {required bool isChinese}) =>
      switch (view) {
        TaskViewMode.schedule => isChinese ? '日程视图' : 'Schedule',
        TaskViewMode.priority => isChinese ? '优先级' : 'Priority',
        TaskViewMode.plan => isChinese ? '计划视图' : 'Plan',
        TaskViewMode.sprint => isChinese ? '冲刺视图' : 'Sprint',
      };
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
                  fontWeight: DS.fontWeightMedium,
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
