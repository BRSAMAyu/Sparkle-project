import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_slot_config_provider.dart';

/// Bottom-sheet editor for the dashboard's two layers of customization:
///
/// * **Sections** (top-level slots) — control which whole panels appear,
///   their order, and whether each one ships expanded or collapsed.
/// * **Workspace cards** — control the inner cards inside the workspace
///   slot (legacy editor, kept intact).
class DashboardEditSheet extends ConsumerStatefulWidget {
  const DashboardEditSheet({super.key});

  @override
  ConsumerState<DashboardEditSheet> createState() => _DashboardEditSheetState();
}

enum _EditTab { sections, workspace }

class _DashboardEditSheetState extends ConsumerState<DashboardEditSheet> {
  _EditTab _tab = _EditTab.sections;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;

    return GraphiteModalSurface(
      title: context.l10n.dashboardEditTitle,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.7,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _TabSwitcher(
              current: _tab,
              onChanged: (tab) {
                if (tab == _tab) return;
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                );
                setState(() => _tab = tab);
              },
              sectionsLabel: context.l10n.dashboardSectionsLabel,
              workspaceLabel: context.l10n.dashboardWorkspaceCards,
            ),
            const SizedBox(height: DS.spacing16),
            Expanded(
              child: switch (_tab) {
                _EditTab.sections => const _SlotEditor(),
                _EditTab.workspace => const _WorkspaceCardEditor(),
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _TabSwitcher extends StatelessWidget {
  const _TabSwitcher({
    required this.current,
    required this.onChanged,
    required this.sectionsLabel,
    required this.workspaceLabel,
  });

  final _EditTab current;
  final ValueChanged<_EditTab> onChanged;
  final String sectionsLabel;
  final String workspaceLabel;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: _LayoutModeButton(
              label: sectionsLabel,
              selected: current == _EditTab.sections,
              onTap: () => onChanged(_EditTab.sections),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: _LayoutModeButton(
              label: workspaceLabel,
              selected: current == _EditTab.workspace,
              onTap: () => onChanged(_EditTab.workspace),
            ),
          ),
        ],
      );
}

/// Editor for the new top-level slot system.
class _SlotEditor extends ConsumerWidget {
  const _SlotEditor();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardSlotConfigProvider);
    final notifier = ref.read(dashboardSlotConfigProvider.notifier);
    final zh = I18nService.instance.isChinese;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                zh
                    ? '所有分区默认可见。开关隐藏，拖拽排序，按 ⇕ 让低频分区收成 64px 标题条。'
                    : 'All sections start visible. Switch to hide, drag to reorder, tap ⇕ to collapse low-glance sections into a 64px header.',
                style: context.sparkleTypography.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ),
            TextButton(
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                notifier.resetToLeanView();
              },
              child: Text(context.l10n.dashboardLeanView),
            ),
            TextButton(
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                notifier.restoreDefaults();
              },
              child: Text(context.l10n.dashboardRestoreDefaults),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        Expanded(
          child: ReorderableListView.builder(
            itemCount: config.slotOrder.length,
            onReorder: (oldIndex, newIndex) {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.dragDrop),
              );
              notifier.reorderSlots(oldIndex, newIndex);
            },
            buildDefaultDragHandles: false,
            itemBuilder: (context, index) {
              final slotId = config.slotOrder[index];
              final isVisible = config.isVisible(slotId);
              final isCollapsed = config.isCollapsed(slotId);
              return _EditableSlotTile(
                key: ValueKey(slotId),
                slotId: slotId,
                isVisible: isVisible,
                isCollapsed: isCollapsed,
                index: index,
                onToggleVisible: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.toggle),
                  );
                  notifier.toggleSlotVisibility(slotId);
                },
                onToggleCollapsed: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.toggle),
                  );
                  notifier.toggleSlotCollapsed(slotId);
                },
              );
            },
          ),
        ),
      ],
    );
  }
}

class _EditableSlotTile extends StatelessWidget {
  const _EditableSlotTile({
    required this.slotId,
    required this.isVisible,
    required this.isCollapsed,
    required this.index,
    required this.onToggleVisible,
    required this.onToggleCollapsed,
    super.key,
  });

  final String slotId;
  final bool isVisible;
  final bool isCollapsed;
  final int index;
  final VoidCallback onToggleVisible;
  final VoidCallback onToggleCollapsed;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final meta = _slotEditorMeta(slotId, zh: zh);
    return Container(
      key: key,
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: isVisible ? DS.borderSubtle : DS.borderSubtle.withValues(alpha: 0.4),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        child: Row(
          children: [
            Switch(
              value: isVisible,
              onChanged: (_) => onToggleVisible(),
            ),
            const SizedBox(width: DS.spacing4),
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(meta.icon, size: 16, color: DS.brandPrimary),
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    meta.title,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      fontWeight: DS.fontWeightSemiBold,
                      color: isVisible ? DS.textPrimary : DS.textTertiary,
                    ),
                  ),
                  Text(
                    meta.subtitle,
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: isCollapsed
                  ? context.l10n.slotEditorExpand
                  : context.l10n.slotEditorCollapse,
              visualDensity: VisualDensity.compact,
              onPressed: isVisible ? onToggleCollapsed : null,
              icon: Icon(
                isCollapsed
                    ? Icons.unfold_more_rounded
                    : Icons.unfold_less_rounded,
                color: isVisible ? DS.textSecondary : DS.borderSubtle,
                size: 20,
              ),
            ),
            ReorderableDragStartListener(
              index: index,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing4),
                child: Icon(
                  Icons.drag_handle_rounded,
                  color: DS.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Wraps the existing per-card editor (workspace inner cards). Kept as
/// its own widget so the previous behavior is unchanged.
class _WorkspaceCardEditor extends ConsumerWidget {
  const _WorkspaceCardEditor();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardCardConfigProvider);
    final notifier = ref.read(dashboardCardConfigProvider.notifier);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.dashboardLayoutMode,
          style: context.sparkleTypography.labelLarge.copyWith(
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Row(
          children: [
            Expanded(
              child: _LayoutModeButton(
                label: context.l10n.dashboardLayoutSwipe,
                selected:
                    config.layoutMode == DashboardCardLayoutMode.swipe,
                onTap: () {
                  if (config.layoutMode == DashboardCardLayoutMode.swipe) {
                    return;
                  }
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection,
                    ),
                  );
                  notifier.setLayoutMode(DashboardCardLayoutMode.swipe);
                },
              ),
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: _LayoutModeButton(
                label: context.l10n.dashboardLayoutGrid,
                selected:
                    config.layoutMode == DashboardCardLayoutMode.grid,
                onTap: () {
                  if (config.layoutMode == DashboardCardLayoutMode.grid) {
                    return;
                  }
                  unawaited(
                    SensoryFeedbackService.emit(
                      SensoryFeedbackEvent.selection,
                    ),
                  );
                  notifier.setLayoutMode(DashboardCardLayoutMode.grid);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing16),
        Row(
          children: [
            Text(
              context.l10n.dashboardDisplayAndSort,
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const Spacer(),
            TextButton(
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm),
                );
                notifier.restoreDefaults();
              },
              child: Text(context.l10n.dashboardRestoreDefaults),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        Expanded(
          child: ReorderableListView.builder(
            itemCount: config.cardOrder.length,
            onReorder: (oldIndex, newIndex) {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.dragDrop),
              );
              notifier.reorderCards(oldIndex, newIndex);
            },
            buildDefaultDragHandles: false,
            itemBuilder: (context, index) {
              final cardId = config.cardOrder[index];
              final isVisible = config.visibleCardIds.contains(cardId);
              return _EditableCardTile(
                key: ValueKey(cardId),
                cardId: cardId,
                isVisible: isVisible,
                onToggle: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.toggle),
                  );
                  notifier.toggleCardVisibility(cardId);
                },
                index: index,
              );
            },
          ),
        ),
      ],
    );
  }
}

class _LayoutModeButton extends StatelessWidget {
  const _LayoutModeButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius16,
        child: AnimatedContainer(
          duration: DS.durationFast,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing12,
          ),
          decoration: BoxDecoration(
            color: selected
                ? DS.brandPrimary.withValues(alpha: 0.14)
                : DS.surfaceSecondary,
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: selected ? DS.brandPrimary : DS.borderSubtle,
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: context.sparkleTypography.labelLarge.copyWith(
                color: selected ? DS.brandPrimary : DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ),
        ),
      );
}

class _EditableCardTile extends StatelessWidget {
  const _EditableCardTile({
    required this.cardId,
    required this.isVisible,
    required this.onToggle,
    required this.index,
    super.key,
  });

  final String cardId;
  final bool isVisible;
  final VoidCallback onToggle;
  final int index;

  @override
  Widget build(BuildContext context) => Container(
        key: key,
        margin: const EdgeInsets.only(bottom: DS.spacing8),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: ListTile(
          leading: Switch(
            value: isVisible,
            onChanged: (_) => onToggle(),
          ),
          title: Text(
            _titleForCard(context, cardId),
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: DS.fontWeightSemiBold,
            ),
          ),
          subtitle: Text(
            _subtitleForCard(context, cardId),
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
            ),
          ),
          trailing: ReorderableDragStartListener(
            index: index,
            child: Icon(
              Icons.drag_handle_rounded,
              color: DS.textSecondary,
            ),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing4,
          ),
        ),
      );

  String _titleForCard(BuildContext context, String cardId) {
    switch (cardId) {
      case DashboardCardIds.insights:
        return context.l10n.dashboardCardInsights;
      case DashboardCardIds.focus:
        return context.l10n.dashboardCardFocus;
      case DashboardCardIds.calendar:
        return context.l10n.dashboardCardCalendar;
      case DashboardCardIds.tools:
        return context.l10n.dashboardCardTools;
      case DashboardCardIds.openClaw:
        return context.l10n.dashboardCardOpenclaw;
      case DashboardCardIds.streak:
        return context.l10n.dashboardCardStreak;
      case DashboardCardIds.nextActions:
        return context.l10n.dashboardCardNextActions;
      case DashboardCardIds.curiosity:
        return context.l10n.dashboardCardCuriosity;
      case DashboardCardIds.longTermPlan:
        return context.l10n.dashboardCardLongTermPlan;
      case DashboardCardIds.seedLibrary:
        return context.l10n.dashboardCardSeedLibrary;
      default:
        return cardId;
    }
  }

  String _subtitleForCard(BuildContext context, String cardId) {
    switch (cardId) {
      case DashboardCardIds.insights:
        return context.l10n.dashboardCardInsightsSubtitle;
      case DashboardCardIds.focus:
        return context.l10n.dashboardCardFocusSubtitle;
      case DashboardCardIds.calendar:
        return context.l10n.dashboardCardCalendarSubtitle;
      case DashboardCardIds.tools:
        return context.l10n.dashboardCardToolsSubtitle;
      case DashboardCardIds.openClaw:
        return context.l10n.dashboardCardOpenclawSubtitle;
      case DashboardCardIds.streak:
        return context.l10n.dashboardCardStreakSubtitle;
      case DashboardCardIds.nextActions:
        return context.l10n.dashboardCardNextActionsSubtitle;
      case DashboardCardIds.curiosity:
        return context.l10n.dashboardCardCuriositySubtitle;
      case DashboardCardIds.longTermPlan:
        return context.l10n.dashboardCardLongTermPlanSubtitle;
      case DashboardCardIds.seedLibrary:
        return context.l10n.dashboardCardSeedLibrarySubtitle;
      default:
        return '';
    }
  }
}

class _SlotEditorMeta {
  const _SlotEditorMeta({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;
}

_SlotEditorMeta _slotEditorMeta(String slotId, {required bool zh}) {
  switch (slotId) {
    case DashboardSlotIds.dailyBriefing:
      return _SlotEditorMeta(
        title: zh ? '今日简报' : 'Daily briefing',
        subtitle: zh ? '当天的状态、节奏与重点' : 'Today\'s status, pace, focus',
        icon: Icons.wb_sunny_outlined,
      );
    case DashboardSlotIds.metricsRow:
      return _SlotEditorMeta(
        title: zh ? '关键指标' : 'Key metrics',
        subtitle: zh ? '进度、连续天数、动力' : 'Progress, streak, momentum',
        icon: Icons.insights_rounded,
      );
    case DashboardSlotIds.commandCenter:
      return _SlotEditorMeta(
        title: zh ? '指挥中心' : 'Command center',
        subtitle: zh ? '下一步行动入口' : 'Pick up the next action',
        icon: Icons.bolt_rounded,
      );
    case DashboardSlotIds.understanding:
      return _SlotEditorMeta(
        title: zh ? '理解面板' : 'Understanding',
        subtitle: zh ? 'Sparkle 对你的认知拆解' : 'How Sparkle reads you',
        icon: Icons.psychology_outlined,
      );
    case DashboardSlotIds.returnCaseFile:
      return _SlotEditorMeta(
        title: zh ? '回归档案' : 'Return case file',
        subtitle: zh ? '上次离开时的现场' : 'Where you left off',
        icon: Icons.history_edu_rounded,
      );
    case DashboardSlotIds.goalDetailSnapshot:
      return _SlotEditorMeta(
        title: zh ? '目标详情' : 'Goal snapshot',
        subtitle: zh ? '当前目标的近况' : 'Active goal snapshot',
        icon: Icons.flag_outlined,
      );
    case DashboardSlotIds.multiGoalDashboard:
      return _SlotEditorMeta(
        title: zh ? '多目标看板' : 'Multi-goal board',
        subtitle: zh ? '所有目标的总览' : 'All goals at a glance',
        icon: Icons.dashboard_customize_outlined,
      );
    case DashboardSlotIds.taskBoard:
      return _SlotEditorMeta(
        title: zh ? '任务面板' : 'Task board',
        subtitle: zh ? '今日待办与进度' : 'Today\'s tasks & progress',
        icon: Icons.checklist_rounded,
      );
    case DashboardSlotIds.examSprint:
      return _SlotEditorMeta(
        title: zh ? '考试冲刺' : 'Exam sprint',
        subtitle: zh ? '剩余天数与节奏' : 'Days left & cadence',
        icon: Icons.local_fire_department_outlined,
      );
    case DashboardSlotIds.dashboardUpdates:
      return _SlotEditorMeta(
        title: zh ? '动态' : 'Updates',
        subtitle: zh ? '通知、洞察、提醒' : 'Notifications & insights',
        icon: Icons.notifications_outlined,
      );
    case DashboardSlotIds.growthQuality:
      return _SlotEditorMeta(
        title: zh ? '成长质量' : 'Growth quality',
        subtitle: zh ? '深度、稳定性、平衡' : 'Depth, stability, balance',
        icon: Icons.trending_up_rounded,
      );
    case DashboardSlotIds.weeklyNarrative:
      return _SlotEditorMeta(
        title: zh ? '本周叙事' : 'Weekly narrative',
        subtitle: zh ? '一周变化的故事线' : 'This week\'s story',
        icon: Icons.menu_book_outlined,
      );
    case DashboardSlotIds.community:
      return _SlotEditorMeta(
        title: zh ? '同行社群' : 'Community',
        subtitle: zh ? '伙伴动态与监督' : 'Partners & accountability',
        icon: Icons.group_outlined,
      );
    case DashboardSlotIds.achievementProgress:
      return _SlotEditorMeta(
        title: zh ? '成就进度' : 'Achievements',
        subtitle: zh ? '近期解锁与里程碑' : 'Recent unlocks & milestones',
        icon: Icons.emoji_events_outlined,
      );
    case DashboardSlotIds.learningHeatmap:
      return _SlotEditorMeta(
        title: zh ? '学习热力图' : 'Learning heatmap',
        subtitle: zh ? '过去30天的活跃度' : 'Last 30 days of activity',
        icon: Icons.calendar_view_month_rounded,
      );
    case DashboardSlotIds.workspaceCards:
      return _SlotEditorMeta(
        title: zh ? '工作区卡片' : 'Workspace cards',
        subtitle: zh ? '可滑动 / 网格的功能卡' : 'Swipe or grid feature cards',
        icon: Icons.view_module_outlined,
      );
  }
  return _SlotEditorMeta(
    title: slotId,
    subtitle: '',
    icon: Icons.extension_outlined,
  );
}
