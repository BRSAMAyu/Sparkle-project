import 'package:flutter/material.dart';
import 'package:sparkle/core/models/intervention.dart';

class ToastIntervention extends StatelessWidget {

  const ToastIntervention({
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
    return Positioned(
      left: 16,
      right: 16,
      bottom: 32,
      child: GestureDetector(
        onTap: () {},
        child: Material(
          borderRadius: BorderRadius.circular(16),
          color: theme.colorScheme.surface,
          elevation: 12,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  intervention.content.renderedMessage,
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: actions.length > 1
                          ? () => onAction(actions[1].id)
                          : onDismiss,
                      child: Text(
                        actions.length > 1 ? actions[1].label : '稍后',
                      ),
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
      ),
    );
  }
}
