import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/subtask_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

enum _TaskQuickAction {
  pause,
  resume,
  snooze,
  tooHard,
  skip,
  help,
}

/// N23（A-SPEC4 §4.5 静默成功执行令）：快操作在飞状态（内联表达）。
///
/// 替代已删除的 loading toast——动作在 sheet 关闭后异步执行，TaskCard
/// watch 本 provider 在卡片角部显示内联 spinner（等待必须有形状），
/// 同时作重入守卫（同一任务在飞时重复唤起菜单直接忽略，防重复提交）。
/// 仅本菜单写；TaskCard / InteractiveTaskCard 读。
final taskQuickActionInFlightProvider = StateProvider<String?>((ref) => null);

Future<void> showTaskQuickActionMenu({
  required BuildContext context,
  required WidgetRef ref,
  required TaskModel task,
  Future<void> Function()? onChanged,
}) async {
  // 重入守卫：同一任务的快操作在飞时忽略再次唤起。
  if (ref.read(taskQuickActionInFlightProvider) == task.id) {
    return;
  }
  final action = await showSensoryModalBottomSheet<_TaskQuickAction>(
    context: context,
    builder: (sheetContext) => _TaskQuickActionSheet(task: task),
  );
  if (action == null || !context.mounted) {
    return;
  }

  ref.read(taskQuickActionInFlightProvider.notifier).state = task.id;
  try {
    switch (action) {
      case _TaskQuickAction.pause:
        await _runTaskVoidAction(
          context: context,
          action: () => ref.read(taskListProvider.notifier).pauseTask(
                task.id,
                reason: 'user_paused_from_quick_action',
              ),
          onChanged: onChanged,
        );
        return;
      case _TaskQuickAction.resume:
        await _runTaskVoidAction(
          context: context,
          action: () => ref.read(taskListProvider.notifier).resumeTask(task.id),
          onChanged: onChanged,
        );
        return;
      case _TaskQuickAction.snooze:
        await _runTaskAction(
          context: context,
          action: () => ref.read(taskListProvider.notifier).snoozeTask(task.id),
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
          onChanged: onChanged,
        );
        return;
      case _TaskQuickAction.help:
        _openTaskHelpChat(context, task);
        return;
    }
  } finally {
    if (ref.read(taskQuickActionInFlightProvider) == task.id) {
      ref.read(taskQuickActionInFlightProvider.notifier).state = null;
    }
  }
}

/// N23 静默成功：暂停/恢复等无返回值动作——成功即状态本体变化
/// （卡片状态徽章/列表位置随 provider 更新），不再 toast；
/// loading toast 已删（TaskCard 内联 spinner 承接等待形状）。
/// 仅失败仍 toast，文案经 uiErrorMessage 单源映射（N15/N16，禁洗 toString）。
Future<void> _runTaskVoidAction({
  required BuildContext context,
  required Future<void> Function() action,
  Future<void> Function()? onChanged,
}) async {
  try {
    await action();
    if (!context.mounted) return;
    await onChanged?.call();
  } catch (error) {
    if (!context.mounted) return;
    AppFeedback.error(
      context,
      uiErrorMessage(context.l10n, categorizeUiError(error)),
    );
  }
}

/// N23 静默成功：snooze/tooHard/skip——成功反馈 = 返回的 TaskQuickActionResult
/// 已由 provider 应用到状态本体（任务换位/子任务重排），不再 toast；
/// 失败仍 toast（uiErrorMessage 单源映射）。
Future<TaskQuickActionResult?> _runTaskAction({
  required BuildContext context,
  required Future<TaskQuickActionResult> Function() action,
  Future<void> Function()? onChanged,
}) async {
  try {
    final result = await action();
    if (!context.mounted) return result;
    await onChanged?.call();
    return result;
  } catch (error) {
    if (!context.mounted) return null;
    AppFeedback.error(
      context,
      uiErrorMessage(context.l10n, categorizeUiError(error)),
    );
    return null;
  }
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
              if (task.status == TaskStatus.inProgress ||
                  task.status == TaskStatus.stuck)
                _QuickActionTile(
                  icon: Icons.pause_rounded,
                  label: context.l10n.taskActionPause,
                  onTap: () =>
                      Navigator.of(context).pop(_TaskQuickAction.pause),
                ),
              if (task.status == TaskStatus.paused ||
                  task.status == TaskStatus.restore)
                _QuickActionTile(
                  icon: Icons.restart_alt_rounded,
                  label: context.l10n.taskActionResume,
                  onTap: () =>
                      Navigator.of(context).pop(_TaskQuickAction.resume),
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
