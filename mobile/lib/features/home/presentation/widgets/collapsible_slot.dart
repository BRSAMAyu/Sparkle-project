import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_slot_config_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_edit_sheet.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';

/// Wraps a top-level dashboard slot with a real collapse-to-header
/// affordance.
///
/// When collapsed the slot renders a `DashboardSectionShell.summary`
/// surface that occupies ~64px — full design-system vocabulary, not a
/// one-off container — surfacing icon + title + a *live* summary line
/// (e.g. "完成 3/7 · 还差 2 件达标") plus a chevron. Tapping the
/// header expands inline; long-press anywhere opens the edit sheet so
/// users can reorder, hide, or jump to lean view.
///
/// When expanded the wrapper adds no chrome of its own — the underlying
/// card already has its own `DashboardSectionHeader`, so adding a
/// second header bar would double up. Instead a long-press handler
/// gives a quiet escape hatch into the edit sheet without competing
/// for visual weight.
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
    final notifier = ref.read(dashboardSlotConfigProvider.notifier);
    final isCollapsed = ref.watch(
      dashboardSlotConfigProvider.select((c) => c.isCollapsed(slotId)),
    );
    final accent = accentColor ?? DS.brandPrimary;

    Future<void> toggle() async {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.toggle));
      notifier.toggleSlotCollapsed(slotId);
    }

    Future<void> openEditSheet() async {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
      await showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => const DashboardEditSheet(),
      );
    }

    return AnimatedSize(
      duration: DS.durationNormal,
      curve: DS.curveEaseInOut,
      alignment: Alignment.topCenter,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        child: isCollapsed
            ? _CollapsedHeader(
                title: title,
                icon: icon,
                summary: summary,
                accent: accent,
                onTap: toggle,
                onLongPress: openEditSheet,
              )
            : _ExpandedSurface(
                onLongPress: openEditSheet,
                child: child,
              ),
      ),
    );
  }
}

class _CollapsedHeader extends StatelessWidget {
  const _CollapsedHeader({
    required this.title,
    required this.icon,
    required this.accent,
    required this.onTap,
    required this.onLongPress,
    this.summary,
  });

  final String title;
  final IconData icon;
  final String? summary;
  final Color accent;
  final VoidCallback onTap;
  final VoidCallback onLongPress;

  @override
  Widget build(BuildContext context) {
    final hasSummary = summary != null && summary!.trim().isNotEmpty;

    return Semantics(
      button: true,
      label: hasSummary ? '$title · $summary' : title,
      hint: MaterialLocalizations.of(context).expandedHint,
      child: DashboardSectionShell(
        tone: DashboardSurfaceTone.summary,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        borderRadius: DS.borderRadius16,
        onTap: onTap,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onLongPress: onLongPress,
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: accent.withValues(alpha: 0.18),
                  ),
                ),
                child: Icon(icon, size: 16, color: accent),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
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
                    if (hasSummary) ...[
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
              const SizedBox(width: DS.spacing4),
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
}

/// Expanded slots stay clean — no extra header bar. Long-press anywhere
/// opens the edit sheet so users can reorder, hide, or collapse.
class _ExpandedSurface extends StatelessWidget {
  const _ExpandedSurface({
    required this.onLongPress,
    required this.child,
  });

  final VoidCallback onLongPress;
  final Widget child;

  @override
  Widget build(BuildContext context) => GestureDetector(
        behavior: HitTestBehavior.deferToChild,
        onLongPress: onLongPress,
        child: child,
      );
}
