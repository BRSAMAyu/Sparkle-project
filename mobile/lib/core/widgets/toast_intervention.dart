import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/intervention.dart';

class ToastIntervention extends StatelessWidget {
  const ToastIntervention({
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
        ? const [
            InterventionAction(id: 'start_now', label: '开始', type: 'primary'),
            InterventionAction(id: 'dismiss', label: '稍后', type: 'secondary'),
          ]
        : intervention.actions;
    return Positioned(
      left: DS.md,
      right: DS.md,
      bottom: DS.spacing32,
      child: GestureDetector(
        onTap: () {},
        child: Material(
          borderRadius: BorderRadius.circular(16),
          color: theme.colorScheme.surface,
          elevation: 12,
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (intervention.content.hasSrlPhaseHint) ...[
                  _SrlPhaseBadge(content: intervention.content),
                  const SizedBox(height: DS.spacing8),
                ],
                Text(
                  intervention.content.renderedMessage,
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: DS.spacing12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    SparkleButton.outline(
                      label: actions.length > 1 ? actions[1].label : '稍后',
                      onPressed: actions.length > 1
                          ? () => onAction(actions[1].id)
                          : onDismiss,
                    ),
                    const SizedBox(width: DS.sm),
                    SparkleButton.primary(
                      label: actions.first.label,
                      onPressed: () => onAction(actions.first.id),
                    ),
                  ],
                ),
              ],
            ),
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
        style: theme.textTheme.labelMedium?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
