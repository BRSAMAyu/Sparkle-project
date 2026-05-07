import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/task_model.dart';

String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

class PausedTaskBanner extends StatelessWidget {
  const PausedTaskBanner({
    required this.task,
    super.key,
    this.onResume,
    this.onUndoResume,
    this.showReasonAction = true,
  });

  final TaskModel task;
  final Future<bool> Function()? onResume;
  final VoidCallback? onUndoResume;
  final bool showReasonAction;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final details = PausedTaskDetails.fromTask(task);
    final reason = details.localizedPauseReason(context);
    final duration = details.pausedDurationLabel(context);

    return Semantics(
      container: true,
      label: l10n.taskPausedPanelSemantics(task.title),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.warning100,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.warning200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.14),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.pause_circle_outline_rounded,
                    color: DS.warning,
                    size: 20,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _t('任务已暂停', 'Task paused'),
                        style: DS.bodyMedium.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        reason,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                _PausedDurationPill(label: duration),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              alignment: WrapAlignment.end,
              children: [
                if (showReasonAction)
                  OutlinedButton.icon(
                    onPressed: () => unawaited(
                      showPausedTaskReasonDialog(
                        context: context,
                        task: task,
                      ),
                    ),
                    icon: const Icon(Icons.info_outline_rounded, size: 18),
                    label: Text(_t('查看暂停原因', 'View pause reason')),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: DS.warning,
                      side: BorderSide(color: DS.warning200),
                      visualDensity: VisualDensity.compact,
                    ),
                  ),
                FilledButton.icon(
                  onPressed:
                      onResume == null ? null : () => _handleResume(context),
                  icon: const Icon(Icons.restart_alt_rounded, size: 18),
                  label: Text(_t('继续任务', 'Resume task')),
                  style: FilledButton.styleFrom(
                    backgroundColor: DS.warning,
                    foregroundColor: DS.onColor(DS.warning),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleResume(BuildContext context) async {
    try {
      final ok = await onResume?.call();
      if ((ok ?? false) && context.mounted) {
        if (onUndoResume == null) {
          AppFeedback.success(context, context.l10n.taskResumeQueued);
        } else {
          AppFeedback.undoable(
            context: context,
            message: context.l10n.taskResumeQueued,
            actionLabel: context.l10n.chatUndo,
            onAction: onUndoResume!,
          );
        }
      } else if (!(ok ?? false) && context.mounted) {
        AppFeedback.error(context, context.l10n.taskResumeFailed);
      }
    } catch (_) {
      if (context.mounted) {
        AppFeedback.error(context, context.l10n.taskResumeFailed);
      }
    }
  }
}

class PausedTaskStatusPanel extends StatelessWidget {
  const PausedTaskStatusPanel({
    required this.task,
    super.key,
    this.onResume,
    this.onPause,
  });

  final TaskModel task;
  final Future<bool> Function()? onResume;
  final VoidCallback? onPause;

  @override
  Widget build(BuildContext context) => PausedTaskBanner(
        task: task,
        onResume: onResume,
        onUndoResume: onPause,
      );
}

class PausedTaskDetails {
  const PausedTaskDetails({
    this.pauseReason,
    this.restoreCondition,
    this.pausedAt,
  });

  factory PausedTaskDetails.fromTask(TaskModel task) {
    final metadata = task.metadata;
    final pauseReason = task.pausedReason ??
        _readString(metadata, const [
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
    final pausedAt = task.pausedAt ??
        _readDate(metadata, const [
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

  String pausedAtLabel(BuildContext context) {
    final at = pausedAt;
    if (at == null) {
      return context.l10n.taskPausedDurationUnknown;
    }
    return DateFormat.yMMMd(context.locale.toLanguageTag()).add_Hm().format(at);
  }

  String localizedPauseReason(BuildContext context) {
    final raw = pauseReason?.trim();
    if (raw == null || raw.isEmpty) {
      return context.l10n.taskPauseReasonFallback;
    }

    final normalized = raw.toLowerCase();
    if (normalized == 'manual' || normalized.startsWith('user_')) {
      return _t(
        '你手动暂停了这个任务，可以随时继续。',
        'You paused this task manually and can resume anytime.',
      );
    }
    if (normalized == 'inactivity' || normalized.startsWith('auto_')) {
      return _t(
        '长时间未继续，Sparkle 自动暂停以保护当前节奏。',
        'Sparkle paused it after inactivity to protect your current rhythm.',
      );
    }
    if (normalized == 'system') {
      return _t(
        '系统根据当前计划状态暂时暂停了这个任务。',
        'The system paused this task based on the current plan state.',
      );
    }
    return raw;
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

class _PausedDurationPill extends StatelessWidget {
  const _PausedDurationPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 128),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.warning200),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.bodySmall.copyWith(
            color: DS.warning,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
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

Future<bool?> showPausedTaskReasonDialog({
  required BuildContext context,
  required TaskModel task,
}) {
  final l10n = context.l10n;
  final details = PausedTaskDetails.fromTask(task);
  final restoreCondition = details.restoreCondition ??
      (task.dueDate == null
          ? l10n.taskRestoreConditionFallback
          : l10n.taskRestoreConditionDueDate(
              DateFormat.yMMMd(context.locale.toLanguageTag())
                  .format(task.dueDate!),
            ));

  return showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(_t('暂停原因', 'Pause reason')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PausedInfoRow(
            icon: Icons.info_outline_rounded,
            label: l10n.taskPauseReasonLabel,
            value: details.localizedPauseReason(dialogContext),
          ),
          const SizedBox(height: DS.spacing10),
          _PausedInfoRow(
            icon: Icons.schedule_rounded,
            label: _t('暂停时间：', 'Paused at:'),
            value: details.pausedAtLabel(dialogContext),
          ),
          const SizedBox(height: DS.spacing10),
          _PausedInfoRow(
            icon: Icons.flag_outlined,
            label: l10n.taskRestoreConditionLabel,
            value: restoreCondition,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(false),
          child: Text(l10n.confirm),
        ),
      ],
    ),
  );
}
