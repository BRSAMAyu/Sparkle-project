import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Standalone widget for restoring a paused task.
class TaskRestoreDialog extends StatelessWidget {
  const TaskRestoreDialog({
    required this.task,
    required this.onConfirm,
    super.key,
  });

  final TaskModel task;
  final VoidCallback? onConfirm;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final metadata = task.metadata;
    final nextStep = _readString(
          metadata,
          const ['next_step', 'resume_next_step'],
        ) ??
        task.guideContent ??
        task.successCriteria ??
        l10n.taskRestoreDialogNextStepFallback;

    return Semantics(
      container: true,
      explicitChildNodes: true,
      label: l10n.taskRestoreDialogTitle,
      child: AlertDialog(
        title: Text(l10n.taskRestoreDialogTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.taskRestoreDialogBody(task.title)),
            const SizedBox(height: 12),
            Text(
              l10n.taskRestoreDialogNextStepLabel,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 6),
            Semantics(
              label: '${l10n.taskRestoreDialogNextStepLabel}: $nextStep',
              child: Text(nextStep),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: onConfirm == null
                ? null
                : () {
                    onConfirm!();
                    Navigator.of(context).pop(true);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(l10n.taskResumeQueued)),
                    );
                  },
            child: Text(l10n.taskActionResume),
          ),
        ],
      ),
    );
  }

  static String? _readString(
    Map<String, dynamic>? metadata,
    List<String> keys,
  ) {
    if (metadata == null) return null;
    for (final key in keys) {
      final value = metadata[key]?.toString().trim();
      if (value != null && value.isNotEmpty) return value;
    }
    return null;
  }
}

/// Convenience function to show the [TaskRestoreDialog].
Future<bool?> showRestoreTaskDialog({
  required BuildContext context,
  required TaskModel task,
  required VoidCallback? onConfirm,
}) {
  return showDialog<bool>(
    context: context,
    builder: (_) => TaskRestoreDialog(task: task, onConfirm: onConfirm),
  );
}
