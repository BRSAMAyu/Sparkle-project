import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
  @override
  Widget build(BuildContext context) {
    final boardState = ref.watch(taskBoardProvider);
    final isCollapsed = boardState.isCollapsed;
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
                isCollapsed: isCollapsed,
                onToggle: () => ref.read(taskBoardProvider.notifier).toggleCollapsed(),
                onOpenTasks: () => context.push('/tasks'),
              ),
              if (isCollapsed) ...[
                const SizedBox(height: DS.spacing12),
                _CollapsedWorkspacePreview(
                  summary: summaryLabel,
                  view: boardState.currentView,
                ),
              ],
              ClipRect(
                child: AnimatedSize(
                  duration: DS.quick,
                  curve: DS.motionCurve(SparkleMotionToken.standard),
                  alignment: Alignment.topCenter,
                  child: isCollapsed
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
                Expanded(
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
              _panelTitle(context, mode),
              style: context.sparkleTypography.labelLarge.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            _buildPanelContent(context, mode, isChinese: isChinese),
          ],
        ),
      );

  String _panelTitle(BuildContext context, TaskViewMode mode) =>
      switch (mode) {
        TaskViewMode.plan => context.l10n.taskBoardPlanManagement,
        _ => context.l10n.taskBoardHelpfulNotes,
      };

  Widget _buildPanelContent(BuildContext context, TaskViewMode mode, {required bool isChinese}) =>
      switch (mode) {
        TaskViewMode.schedule => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.calendar_today_rounded,
                title: context.l10n.taskBoardBrowseByDate,
                description: context.l10n.taskBoardBrowseByDateDesc,
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.warning_rounded,
                title: context.l10n.taskBoardOverdueTasks,
                description: context.l10n.taskBoardOverdueTasksDesc,
                color: DS.semanticError,
              ),
            ],
          ),
        TaskViewMode.priority => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flag_rounded,
                title: context.l10n.taskBoardPriorityOrder,
                description: context.l10n.taskBoardPriorityOrderDesc,
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.tune_rounded,
                title: context.l10n.taskBoardCustomPriority,
                description: context.l10n.taskBoardCustomPriorityDesc,
              ),
            ],
          ),
        TaskViewMode.plan => const DashboardPlanManager(compact: true),
        TaskViewMode.sprint => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PanelItem(
                icon: Icons.flash_on_rounded,
                title: context.l10n.taskBoardSprintFocus,
                description: context.l10n.taskBoardSprintFocusDesc,
              ),
              const SizedBox(height: DS.spacing12),
              _PanelItem(
                icon: Icons.timer_rounded,
                title: context.l10n.taskBoardSprintTiming,
                description: context.l10n.taskBoardSprintTimingDesc,
              ),
            ],
          ),
      };

  String _summaryLabel(
    TaskBoardTodaySummary summary, {
    required bool isChinese,
  }) {
    if (summary.totalCount == 0) {
      return context.l10n.taskBoardNoTasksToday;
    }
    return context.l10n.taskBoardTodaySummary(
      summary.totalCount,
      summary.completedCount,
    );
  }
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
  Widget build(BuildContext context) => InkWell(
        onTap: onOpenTasks,
        borderRadius: DS.borderRadius16,
        child: DashboardSectionHeader(
          icon: Icons.dashboard_customize_rounded,
          accentColor: DS.brandPrimary,
          title: context.l10n.taskBoardTitle,
          summary: summary,
          trailing: _HeaderToggleButton(
            isCollapsed: isCollapsed,
            onTap: onToggle,
          ),
        ),
      );
}

class _HeaderToggleButton extends StatelessWidget {
  const _HeaderToggleButton({
    required this.isCollapsed,
    required this.onTap,
  });

  final bool isCollapsed;
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
              ? context.l10n.taskBoardExpand
              : context.l10n.taskBoardCollapse,
        ),
      );
}

class _CollapsedWorkspacePreview extends StatelessWidget {
  const _CollapsedWorkspacePreview({
    required this.summary,
    required this.view,
  });

  final String summary;
  final TaskViewMode view;

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
                    context.l10n.taskBoardWorkspaceSummary,
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
                _viewLabel(context, view),
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
          ],
        ),
      );

  String _viewLabel(BuildContext context, TaskViewMode view) =>
      switch (view) {
        TaskViewMode.schedule => context.l10n.taskBoardScheduleView,
        TaskViewMode.priority => context.l10n.taskBoardPriorityView,
        TaskViewMode.plan => context.l10n.taskBoardPlanView,
        TaskViewMode.sprint => context.l10n.taskBoardSprintView,
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
