import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

enum _TaskQuickAction {
  snooze,
  tooHard,
  skip,
  help,
}

Future<void> showTaskQuickActionMenu({
  required BuildContext context,
  required WidgetRef ref,
  required TaskModel task,
  Future<void> Function()? onChanged,
}) async {
  final action = await showModalBottomSheet<_TaskQuickAction>(
    context: context,
    backgroundColor: Colors.transparent,
    builder: (sheetContext) => _TaskQuickActionSheet(task: task),
  );
  if (action == null || !context.mounted) {
    return;
  }

  switch (action) {
    case _TaskQuickAction.snooze:
      await _runTaskAction(
        context: context,
        action: () => ref.read(taskListProvider.notifier).snoozeTask(task.id),
        loadingMessage: context.l10n.taskQuickActionSnoozing,
        onChanged: onChanged,
      );
      return;
    case _TaskQuickAction.tooHard:
      final result = await _runTaskAction(
        context: context,
        action: () => ref.read(taskListProvider.notifier).markTaskTooHard(
              task.id,
              reason: 'user_marked_too_hard_via_long_press',
            ),
        loadingMessage: context.l10n.taskQuickActionSimplifying,
        onChanged: onChanged,
      );
      if (result != null && result.subtasks.isNotEmpty) {
        ref.invalidate(subtaskNotifierProvider(task.id));
      }
      return;
    case _TaskQuickAction.skip:
      await _runTaskAction(
        context: context,
        action: () => ref.read(taskListProvider.notifier).skipTask(task.id),
        loadingMessage: context.l10n.taskQuickActionSkipping,
        onChanged: onChanged,
      );
      return;
    case _TaskQuickAction.help:
      _openTaskHelpChat(context, task);
      return;
  }
}

Future<TaskQuickActionResult?> _runTaskAction({
  required BuildContext context,
  required Future<TaskQuickActionResult> Function() action,
  required String loadingMessage,
  Future<void> Function()? onChanged,
}) async {
  AppFeedback.loading(context, loadingMessage);
  try {
    final result = await action();
    if (!context.mounted) return result;
    AppFeedback.success(context, _feedbackMessage(context, result));
    await onChanged?.call();
    return result;
  } catch (error) {
    if (!context.mounted) return null;
    AppFeedback.error(
      context,
      error.toString().replaceFirst(RegExp(r'^Exception:\s*'), ''),
    );
    return null;
  }
}

String _feedbackMessage(BuildContext context, TaskQuickActionResult result) {
  if (result.message.trim().isNotEmpty) {
    return result.message.trim();
  }
  final l10n = context.l10n;
  return switch (result.action) {
    'snooze' => l10n.taskQuickActionSnoozed,
    'too_hard' => l10n.taskQuickActionTooHard,
    'skip' => l10n.taskQuickActionSkipped,
    _ => l10n.taskQuickActionAdjusted,
  };
}

void _openTaskHelpChat(BuildContext context, TaskModel task) {
  final prompt = _buildTaskHelpPrompt(task);
  context.go(
    Uri(
      path: '/chat',
      queryParameters: {
        'chat_mode': 'study_plan',
        'prompt': prompt,
      },
    ).toString(),
  );
}

String _buildTaskHelpPrompt(TaskModel task) {
  final parts = <String>[
    S.taskHelpPromptPrefix,
    S.taskHelpPromptTitle(task.title),
    S.taskHelpPromptType(task.type.name),
    S.taskHelpPromptEstimate(task.estimatedMinutes),
    S.taskHelpPromptDifficulty(task.difficulty),
    if (task.dueDate != null)
      S.taskHelpPromptDueDate(task.dueDate!.toIso8601String().split('T').first),
    if ((task.successCriteria ?? '').trim().isNotEmpty)
      S.taskHelpPromptCriteria(task.successCriteria!.trim()),
    if ((task.guideContent ?? '').trim().isNotEmpty)
      S.taskHelpPromptGuide(task.guideContent!.trim()),
    S.taskHelpPromptSuffix,
  ];
  return parts.join('\n');
}

class _TaskQuickActionSheet extends StatelessWidget {
  const _TaskQuickActionSheet({required this.task});

  final TaskModel task;

  @override
  Widget build(BuildContext context) => SafeArea(
        child: Container(
          margin: const EdgeInsets.all(DS.spacing12),
          padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.borderSubtle),
            boxShadow: DS.shadowLg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing16,
                  DS.spacing8,
                  DS.spacing16,
                  DS.spacing6,
                ),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    task.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: DS.bodyMedium.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ),
              _QuickActionTile(
                icon: Icons.event_repeat_rounded,
                label: context.l10n.taskQuickActionSnooze,
                onTap: () => Navigator.of(context).pop(_TaskQuickAction.snooze),
              ),
              _QuickActionTile(
                icon: Icons.auto_fix_high_rounded,
                label: context.l10n.taskQuickActionTooHardLabel,
                onTap: () =>
                    Navigator.of(context).pop(_TaskQuickAction.tooHard),
              ),
              _QuickActionTile(
                icon: Icons.not_interested_rounded,
                label: context.l10n.taskQuickActionSkip,
                onTap: () => Navigator.of(context).pop(_TaskQuickAction.skip),
              ),
              _QuickActionTile(
                icon: Icons.chat_bubble_outline_rounded,
                label: context.l10n.taskQuickActionHelp,
                onTap: () => Navigator.of(context).pop(_TaskQuickAction.help),
              ),
            ],
          ),
        ),
      );
}

class _QuickActionTile extends StatelessWidget {
  const _QuickActionTile({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ListTile(
        leading: Icon(icon, color: DS.brandPrimary),
        title: Text(
          label,
          style: DS.bodyMedium.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
        onTap: onTap,
      );
}
