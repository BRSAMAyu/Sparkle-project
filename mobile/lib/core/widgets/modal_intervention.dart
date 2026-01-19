import 'package:flutter/material.dart';
import 'package:sparkle/core/models/intervention.dart';

class ModalIntervention extends StatelessWidget {

  const ModalIntervention({
    super.key,
    required this.intervention,
    required this.onAction,
    required this.onDismiss,
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
    return Center(
      child: Material(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(24),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                intervention.content.renderedMessage,
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => onAction(actions.first.id),
                  child: Text(actions.first.label),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: actions.length > 1
                      ? () => onAction(actions[1].id)
                      : onDismiss,
                  child: Text(actions.length > 1 ? actions[1].label : '稍后'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
