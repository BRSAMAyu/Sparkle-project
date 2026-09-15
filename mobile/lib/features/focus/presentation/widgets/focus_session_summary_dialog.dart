import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/focus/data/repositories/focus_repository.dart';

Future<void> showFocusSessionSummaryDialog(
  BuildContext context, {
  required int durationMinutes,
  required int flameEarned,
  required List<FocusMasteryUpdate> masteryUpdates,
}) async {
  if (masteryUpdates.isEmpty) return;

  await showSensoryDialog<void>(
    context: context,
    builder: (context) => _FocusSessionSummaryDialog(
      durationMinutes: durationMinutes,
      flameEarned: flameEarned,
      masteryUpdates: masteryUpdates,
    ),
  );
}

class _FocusSessionSummaryDialog extends StatelessWidget {
  const _FocusSessionSummaryDialog({
    required this.durationMinutes,
    required this.flameEarned,
    required this.masteryUpdates,
  });

  final int durationMinutes;
  final int flameEarned;
  final List<FocusMasteryUpdate> masteryUpdates;

  @override
  Widget build(BuildContext context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(DS.spacing20),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: GraphiteModalSurface(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: DS.success.withValues(alpha: 0.12),
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: DS.success.withValues(alpha: 0.22),
                        ),
                      ),
                      child: Icon(
                        Icons.auto_graph_rounded,
                        color: DS.success,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        context.l10n.focusSessionComplete,
                        style: DS.titleLarge.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                _SessionMetricRow(
                  durationMinutes: durationMinutes,
                  flameEarned: flameEarned,
                ),
                const SizedBox(height: DS.spacing16),
                ...masteryUpdates.take(3).map(
                      (update) => Padding(
                        padding: const EdgeInsets.only(
                          bottom: DS.spacing10,
                        ),
                        child: _MasteryUpdateLine(update: update),
                      ),
                    ),
                const SizedBox(height: DS.spacing8),
                SizedBox(
                  width: double.infinity,
                  child: SparkleButton(
                    label: context.l10n.focusSessionGotIt,
                    icon: const Icon(Icons.check_rounded),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _SessionMetricRow extends StatelessWidget {
  const _SessionMetricRow({
    required this.durationMinutes,
    required this.flameEarned,
  });

  final int durationMinutes;
  final int flameEarned;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: _MetricPill(
              icon: Icons.timer_outlined,
              label: context.l10n.focusSessionMinutes(durationMinutes),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: _MetricPill(
              icon: Icons.local_fire_department_outlined,
              label: context.l10n.focusSessionFlameEarned(flameEarned),
            ),
          ),
        ],
      );
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius8,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: DS.primaryBase),
            const SizedBox(width: DS.spacing6),
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
          ],
        ),
      );
}

class _MasteryUpdateLine extends StatelessWidget {
  const _MasteryUpdateLine({required this.update});

  final FocusMasteryUpdate update;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.success.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius8,
          border: Border.all(color: DS.success.withValues(alpha: 0.16)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.school_outlined,
              color: DS.success,
              size: 20,
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Text(
                context.l10n.focusSessionMasteryUpdate(
                  update.nodeName,
                  update.oldMastery.toInt(),
                  update.newMastery.toInt(),
                ),
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      );
}
