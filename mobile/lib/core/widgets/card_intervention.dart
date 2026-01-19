import 'package:flutter/material.dart';
import 'package:sparkle/core/models/intervention.dart';

class CardIntervention extends StatelessWidget {
  final InterventionPushMessage intervention;
  final ValueChanged<String> onAction;
  final VoidCallback onDismiss;

  const CardIntervention({
    super.key,
    required this.intervention,
    required this.onAction,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final actions = intervention.actions.isEmpty
        ? const [
            InterventionAction(id: 'start_now', label: '开始', type: 'primary'),
            InterventionAction(id: 'dismiss', label: '关闭', type: 'secondary'),
          ]
        : intervention.actions;
    return Positioned(
      left: 0,
      right: 0,
      bottom: 0,
      child: Material(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: theme.colorScheme.outlineVariant,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                intervention.content.renderedMessage,
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: actions.length > 1
                        ? () => onAction(actions[1].id)
                        : onDismiss,
                    child: Text(actions.length > 1 ? actions[1].label : '关闭'),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: () => onAction(actions.first.id),
                    child: Text(actions.first.label),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
