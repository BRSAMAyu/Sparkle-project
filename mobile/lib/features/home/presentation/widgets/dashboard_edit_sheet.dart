import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';

class DashboardEditSheet extends ConsumerWidget {
  const DashboardEditSheet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardCardConfigProvider);
    final notifier = ref.read(dashboardCardConfigProvider.notifier);

    return GraphiteModalSurface(
      title: '编辑卡片区',
      child: SizedBox(
        height: 520,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '布局方式',
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Row(
              children: [
                Expanded(
                  child: _LayoutModeButton(
                    label: '横滑卡组',
                    selected:
                        config.layoutMode == DashboardCardLayoutMode.swipe,
                    onTap: () => notifier.setLayoutMode(
                      DashboardCardLayoutMode.swipe,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _LayoutModeButton(
                    label: '双列网格',
                    selected: config.layoutMode == DashboardCardLayoutMode.grid,
                    onTap: () => notifier.setLayoutMode(
                      DashboardCardLayoutMode.grid,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Text(
                  '显示与排序',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const Spacer(),
                TextButton(
                  onPressed: notifier.restoreDefaults,
                  child: const Text('恢复默认'),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Expanded(
              child: ReorderableListView.builder(
                itemCount: config.cardOrder.length,
                onReorder: notifier.reorderCards,
                buildDefaultDragHandles: false,
                itemBuilder: (context, index) {
                  final cardId = config.cardOrder[index];
                  final isVisible = config.visibleCardIds.contains(cardId);
                  return _EditableCardTile(
                    key: ValueKey(cardId),
                    cardId: cardId,
                    isVisible: isVisible,
                    onToggle: () => notifier.toggleCardVisibility(cardId),
                    index: index,
                  );
                },
              ),
            ),
          ],
        ),
      ),
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
            _titleForCard(cardId),
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: DS.fontWeightSemiBold,
            ),
          ),
          subtitle: Text(
            _subtitleForCard(cardId),
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

  String _titleForCard(String cardId) {
    switch (cardId) {
      case DashboardCardIds.insights:
        return '学习洞察';
      case DashboardCardIds.focus:
        return '专注核心';
      case DashboardCardIds.calendar:
        return '日历热力图';
      case DashboardCardIds.tools:
        return '工具快捷';
      case DashboardCardIds.streak:
        return '连胜卡';
      case DashboardCardIds.nextActions:
        return '下一步';
      case DashboardCardIds.curiosity:
        return '好奇心胶囊';
      case DashboardCardIds.longTermPlan:
        return '长期计划';
      case DashboardCardIds.seedLibrary:
        return '种子库';
      default:
        return cardId;
    }
  }

  String _subtitleForCard(String cardId) {
    switch (cardId) {
      case DashboardCardIds.insights:
        return '学习仿真、推演和报告的统一入口';
      case DashboardCardIds.focus:
        return '专注时长与火焰状态';
      case DashboardCardIds.calendar:
        return '查看当月任务热力图';
      case DashboardCardIds.tools:
        return '固定工具快捷入口';
      case DashboardCardIds.streak:
        return '连续学习成就状态';
      case DashboardCardIds.nextActions:
        return '待推进的关键行动';
      case DashboardCardIds.curiosity:
        return '最近认知与探索摘要';
      case DashboardCardIds.longTermPlan:
        return '长期成长目标进展';
      case DashboardCardIds.seedLibrary:
        return '查看常用知识种子与灵感入口';
      default:
        return '';
    }
  }
}
