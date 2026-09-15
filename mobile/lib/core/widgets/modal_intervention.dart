import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/intervention.dart';

class ModalIntervention extends StatelessWidget {
  const ModalIntervention({
    required this.intervention,
    required this.onAction,
    required this.onDismiss,
    super.key,
  });
  final InterventionPushMessage intervention;
  final ValueChanged<String> onAction;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final actions = intervention.actions.isEmpty
        ? [
            InterventionAction(id: 'start_now', label: context.l10n.interventionStartNow, type: 'primary'),
            InterventionAction(id: 'dismiss', label: context.l10n.interventionLater, type: 'secondary'),
          ]
        : intervention.actions;
    return Center(
      child: Material(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (intervention.content.hasSrlPhaseHint) ...[
                _SrlPhaseBadge(content: intervention.content),
                const SizedBox(height: DS.spacing12),
              ],
              Text(
                intervention.content.renderedMessage,
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: DS.lg),
              SizedBox(
                width: double.infinity,
                child: SparkleButton.primary(
                  label: actions.first.label,
                  onPressed: () => onAction(actions.first.id),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SizedBox(
                width: double.infinity,
                child: SparkleButton.outline(
                  label: actions.length > 1 ? actions[1].label : context.l10n.interventionLater,
                  onPressed: actions.length > 1
                      ? () => onAction(actions[1].id)
                      : onDismiss,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SrlPhaseBadge extends StatelessWidget {
  const _SrlPhaseBadge({required this.content});

  final InterventionContent content;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '${content.srlPhaseLabel} · ${content.srlPhaseMessage}',
        textAlign: TextAlign.center,
        style: theme.textTheme.labelMedium?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
