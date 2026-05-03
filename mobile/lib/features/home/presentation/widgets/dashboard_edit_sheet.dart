import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';

class DashboardEditSheet extends ConsumerWidget {
  const DashboardEditSheet({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardCardConfigProvider);
    final notifier = ref.read(dashboardCardConfigProvider.notifier);

    return GraphiteModalSurface(
      title: context.l10n.dashboardEditTitle,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.6,
        ),
        child: Column(
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
                    onTap: () => notifier.setLayoutMode(
                      DashboardCardLayoutMode.swipe,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: _LayoutModeButton(
                    label: context.l10n.dashboardLayoutGrid,
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
                  context.l10n.dashboardDisplayAndSort,
                  style: context.sparkleTypography.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const Spacer(),
                TextButton(
                  onPressed: notifier.restoreDefaults,
                  child: Text(context.l10n.dashboardRestoreDefaults),
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
