import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
        loadingMessage: '好，我先把它挪到明天。',
        onChanged: onChanged,
      );
      return;
    case _TaskQuickAction.tooHard:
      final result = await _runTaskAction(
        context: context,
        action: () => ref.read(taskListProvider.notifier).markTaskTooHard(
              task.id,
              reason: '用户从任务卡长按菜单标记为太难',
            ),
        loadingMessage: '我来把这张卡拆小一点。',
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
        loadingMessage: '收到，我先把它从今天拿开。',
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
    AppFeedback.success(context, _feedbackMessage(result));
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

String _feedbackMessage(TaskQuickActionResult result) {
  if (result.message.trim().isNotEmpty) {
    return result.message.trim();
  }
  return switch (result.action) {
    'snooze' => '已推迟到明天，今天轻一点。',
    'too_hard' => '拆好了，先做第一小步。',
    'skip' => '已跳过，这张卡先不打扰你。',
    _ => '已经帮你调整好了。',
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
    '我在做这张任务卡时需要帮助，请带着任务上下文和我一起拆一下。',
    '任务：${task.title}',
    '类型：${task.type.name}',
    '预估时间：${task.estimatedMinutes}分钟',
    '难度：${task.difficulty}/5',
    if (task.dueDate != null)
      '计划日期：${task.dueDate!.toIso8601String().split('T').first}',
    if ((task.successCriteria ?? '').trim().isNotEmpty)
      '完成标准：${task.successCriteria!.trim()}',
    if ((task.guideContent ?? '').trim().isNotEmpty)
      '任务指南：${task.guideContent!.trim()}',
    '请先问我一个最关键的澄清问题，然后给我一个5分钟内能开始的下一步。',
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
                label: '推迟到明天',
                onTap: () => Navigator.of(context).pop(_TaskQuickAction.snooze),
              ),
              _QuickActionTile(
                icon: Icons.auto_fix_high_rounded,
                label: '标记为太难',
                onTap: () =>
                    Navigator.of(context).pop(_TaskQuickAction.tooHard),
              ),
              _QuickActionTile(
                icon: Icons.not_interested_rounded,
                label: '跳过',
                onTap: () => Navigator.of(context).pop(_TaskQuickAction.skip),
              ),
              _QuickActionTile(
                icon: Icons.chat_bubble_outline_rounded,
                label: '寻求帮助',
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
