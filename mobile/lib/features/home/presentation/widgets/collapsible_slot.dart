import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_slot_config_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_edit_sheet.dart';

/// Wraps a top-level dashboard slot with a collapse-to-header affordance.
///
/// When collapsed the wrapper renders only a 56-72px header (icon + title +
/// summary + chevron), which is the user's complaint addressed: a "hidden"
/// slot today still bleeds vertical space, but a collapsed slot here
/// genuinely shrinks. Tapping the header expands inline; an overflow menu
/// gives quick access to the edit sheet so the affordance never feels
/// like a dead end.
class CollapsibleSlot extends ConsumerWidget {
  const CollapsibleSlot({
    required this.slotId,
    required this.title,
    required this.icon,
    required this.child,
    super.key,
    this.summary,
    this.accentColor,
  });

  final String slotId;
  final String title;
  final IconData icon;
  final String? summary;
  final Color? accentColor;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final config = ref.watch(dashboardSlotConfigProvider);
    final notifier = ref.read(dashboardSlotConfigProvider.notifier);
    final isCollapsed = config.isCollapsed(slotId);
    final accent = accentColor ?? DS.brandPrimary;

    return AnimatedSize(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeInOutCubic,
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        child: _CollapsibleHeaderSurface(
          isCollapsed: isCollapsed,
          accent: accent,
          onToggle: () => notifier.toggleSlotCollapsed(slotId),
          onOpenEditSheet: () => _openEditSheet(context),
          icon: icon,
          title: title,
          summary: summary,
          child: child,
        ),
      ),
    );
  }

  Future<void> _openEditSheet(BuildContext context) =>
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => const DashboardEditSheet(),
      );
}

class _CollapsibleHeaderSurface extends StatelessWidget {
  const _CollapsibleHeaderSurface({
    required this.isCollapsed,
    required this.accent,
    required this.onToggle,
    required this.onOpenEditSheet,
    required this.icon,
    required this.title,
    required this.child,
    this.summary,
  });

  final bool isCollapsed;
  final Color accent;
  final VoidCallback onToggle;
  final VoidCallback onOpenEditSheet;
  final IconData icon;
  final String title;
  final String? summary;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (isCollapsed) {
      return Material(
        color: Colors.transparent,
        borderRadius: DS.borderRadius16,
        child: InkWell(
          borderRadius: DS.borderRadius16,
          onTap: onToggle,
          onLongPress: onOpenEditSheet,
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary.withValues(alpha: 0.55),
              borderRadius: DS.borderRadius16,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, size: 16, color: accent),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.sparkleTypography.labelLarge.copyWith(
                          fontWeight: DS.fontWeightSemiBold,
                          color: DS.textPrimary,
                        ),
                      ),
                      if (summary != null && summary!.trim().isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          summary!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.bodySmall.copyWith(
                            color: DS.textTertiary,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Icon(
                  Icons.expand_more_rounded,
                  size: 20,
                  color: DS.textTertiary,
                ),
              ],
            ),
          ),
        ),
      );
    }

    // Expanded: render content with a slim collapse-control bar above it so
    // the user always has a single-tap path back to the compact header.
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing4),
          child: _SlotControlBar(
            onCollapse: onToggle,
            onOpenEditSheet: onOpenEditSheet,
            icon: icon,
            title: title,
            accent: accent,
          ),
        ),
        child,
      ],
    );
  }
}

class _SlotControlBar extends StatelessWidget {
  const _SlotControlBar({
    required this.onCollapse,
    required this.onOpenEditSheet,
    required this.icon,
    required this.title,
    required this.accent,
  });

  final VoidCallback onCollapse;
  final VoidCallback onOpenEditSheet;
  final IconData icon;
  final String title;
  final Color accent;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 14, color: accent.withValues(alpha: 0.9)),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textTertiary,
                fontWeight: DS.fontWeightSemiBold,
                letterSpacing: 0.4,
              ),
            ),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            iconSize: 16,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            tooltip: MaterialLocalizations.of(context).collapsedHint,
            icon: Icon(Icons.expand_less_rounded, color: DS.textTertiary),
            onPressed: onCollapse,
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            iconSize: 16,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            tooltip: MaterialLocalizations.of(context).moreButtonTooltip,
            icon: Icon(Icons.tune_rounded, color: DS.textTertiary),
            onPressed: onOpenEditSheet,
          ),
        ],
      );
}
