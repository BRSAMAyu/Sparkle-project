import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PausedTaskStatusPanel extends StatelessWidget {
  const PausedTaskStatusPanel({
    required this.task,
    super.key,
    this.onResume,
    this.onPause,
  });

  final TaskModel task;
  final VoidCallback? onResume;
  final VoidCallback? onPause;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final details = PausedTaskDetails.fromTask(task);

    return Semantics(
      container: true,
      label: l10n.taskPausedPanelSemantics(task.title),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colorScheme.secondaryContainer.withValues(alpha: 0.36),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: colorScheme.secondary.withValues(alpha: 0.28),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.pause_circle_outline_rounded,
                  size: 18,
                  color: colorScheme.secondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.taskPausedPanelTitle,
                    style: textTheme.titleSmall?.copyWith(
                      color: colorScheme.onSecondaryContainer,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Text(
                  details.pausedDurationLabel(context),
                  style: textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSecondaryContainer,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            _PausedInfoRow(
              icon: Icons.info_outline_rounded,
              label: l10n.taskPauseReasonLabel,
              value: details.pauseReason ?? l10n.taskPauseReasonFallback,
            ),
            const SizedBox(height: 8),
            _PausedInfoRow(
              icon: Icons.flag_outlined,
              label: l10n.taskRestoreConditionLabel,
              value: details.restoreCondition ??
                  (task.dueDate == null
                      ? l10n.taskRestoreConditionFallback
                      : l10n.taskRestoreConditionDueDate(
                          DateFormat.yMMMd(context.locale.toLanguageTag())
                              .format(task.dueDate!),
                        )),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.icon(
                onPressed: onResume == null
                    ? null
                    : () {
                        onResume!.call();
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(l10n.taskResumeQueued),
                            action: onPause == null
                                ? null
                                : SnackBarAction(
                                    label: l10n.chatUndo,
                                    onPressed: onPause!,
                                  ),
                          ),
                        );
                      },
                icon: const Icon(Icons.restart_alt_rounded),
                label: Text(l10n.taskActionResume),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class PausedTaskDetails {
  const PausedTaskDetails({
    this.pauseReason,
    this.restoreCondition,
    this.pausedAt,
  });

  factory PausedTaskDetails.fromTask(TaskModel task) {
    final metadata = task.metadata;
    final pauseReason = _readString(metadata, const [
      'pause_reason',
      'paused_reason',
      'reason',
      'blocked_reason',
    ]);
    final restoreCondition = _readString(metadata, const [
      'restore_condition',
      'resume_condition',
      'resume_when',
      'unblock_condition',
    ]);
    final pausedAt = _readDate(metadata, const [
          'paused_at',
          'pause_started_at',
          'paused_since',
        ]) ??
        task.updatedAt;
    return PausedTaskDetails(
      pauseReason: pauseReason,
      restoreCondition: restoreCondition,
      pausedAt: pausedAt,
    );
  }

  final String? pauseReason;
  final String? restoreCondition;
  final DateTime? pausedAt;

  String pausedDurationLabel(BuildContext context) {
    final at = pausedAt;
    if (at == null) {
      return context.l10n.taskPausedDurationUnknown;
    }
    final elapsed = DateTime.now().difference(at);
    if (elapsed.inMinutes < 1) {
      return context.l10n.taskPausedDurationNow;
    }
    if (elapsed.inHours < 1) {
      return context.l10n.taskPausedDurationMinutes(elapsed.inMinutes);
    }
    if (elapsed.inDays < 1) {
      return context.l10n.taskPausedDurationHours(elapsed.inHours);
    }
    return context.l10n.taskPausedDurationDays(elapsed.inDays);
  }

  static String? _readString(Map<String, dynamic> metadata, List<String> keys) {
    for (final key in keys) {
      final value = metadata[key]?.toString().trim();
      if (value != null && value.isNotEmpty && value != 'null') {
        return value;
      }
    }
    return null;
  }

  static DateTime? _readDate(Map<String, dynamic> metadata, List<String> keys) {
    for (final key in keys) {
      final value = metadata[key];
      if (value is DateTime) {
        return value;
      }
      if (value is String && value.trim().isNotEmpty) {
        final parsed = DateTime.tryParse(value.trim());
        if (parsed != null) {
          return parsed;
        }
      }
    }
    return null;
  }
}

class _PausedInfoRow extends StatelessWidget {
  const _PausedInfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: colorScheme.onSecondaryContainer),
        const SizedBox(width: 8),
        Expanded(
          child: RichText(
            text: TextSpan(
              style: textTheme.bodySmall?.copyWith(
                color: colorScheme.onSecondaryContainer,
                height: 1.35,
              ),
              children: [
                TextSpan(
                  text: '$label ',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                TextSpan(text: value),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

Future<bool?> showRestoreTaskDialog({
  required BuildContext context,
  required TaskModel task,
  required VoidCallback? onConfirm,
}) {
  final l10n = context.l10n;
  final metadata = task.metadata;
  final nextStep = PausedTaskDetails._readString(
        metadata,
        const ['next_step', 'resume_next_step'],
      ) ??
      task.guideContent ??
      task.successCriteria ??
      l10n.taskRestoreDialogNextStepFallback;

  return showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(l10n.taskRestoreDialogTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l10n.taskRestoreDialogBody(task.title)),
          const SizedBox(height: 12),
          Text(
            l10n.taskRestoreDialogNextStepLabel,
            style: Theme.of(dialogContext).textTheme.titleSmall,
          ),
          const SizedBox(height: 6),
          Text(nextStep),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: onConfirm == null
              ? null
              : () {
                  onConfirm();
                  Navigator.of(dialogContext).pop(true);
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
