import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_automation_service.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class OpenClawAutomationPanel extends ConsumerStatefulWidget {
  const OpenClawAutomationPanel({super.key});

  @override
  ConsumerState<OpenClawAutomationPanel> createState() =>
      _OpenClawAutomationPanelState();
}

class _OpenClawAutomationPanelState
    extends ConsumerState<OpenClawAutomationPanel> {
  final Set<String> _selectedTaskIds = <String>{};
  final TextEditingController _eventTypeController = TextEditingController();
  final TextEditingController _checkUrlController = TextEditingController();
  final TextEditingController _conditionController = TextEditingController(
    text: "contains('merged')",
  );
  final TextEditingController _intervalController = TextEditingController(
    text: '15',
  );
  String _batchStrategy = 'auto';
  String _triggerType = 'cron';
  String? _selectedScheduleTaskId;
  int _selectedHour = 8;
  int _selectedMinute = 0;

  @override
  void dispose() {
    _eventTypeController.dispose();
    _checkUrlController.dispose();
    _conditionController.dispose();
    _intervalController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final automation = ref.watch(openClawAutomationProvider);
    final taskState = ref.watch(taskListProvider);
    final tasks = _serverTasks(taskState);
    _selectedScheduleTaskId ??= tasks.isNotEmpty ? tasks.first.id : null;
    _selectedTaskIds.removeWhere((taskId) => tasks.every((task) => task.id != taskId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            OpenClawMetricPill(
              icon: Icons.schedule_rounded,
              label: '${automation.schedules.length} 条自动化',
              tone: automation.schedules.isNotEmpty
                  ? OpenClawVisualTone.active
                  : OpenClawVisualTone.offline,
            ),
            OpenClawMetricPill(
              icon: Icons.playlist_play_rounded,
              label: '${_selectedTaskIds.length} 个批量候选',
              tone: _selectedTaskIds.isNotEmpty
                  ? OpenClawVisualTone.connected
                  : OpenClawVisualTone.active,
              emphasized: _selectedTaskIds.isNotEmpty,
            ),
          ],
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          '把一次性的批量委派和长期的定时执行都集中到这里。你不需要离开 OpenClaw Hub，就能把“现在做”与“之后自动做”都安排好。',
          style: DS.bodySmall.copyWith(
            color: DS.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: DS.spacing16),
        GraphiteCardSurface(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '批量委派',
                style: DS.bodyMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                '从最近任务里挑选多个可执行项，一次性发给 OpenClaw，并在同一张摘要里查看完成、失败和排队情况。',
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              DropdownButtonFormField<String>(
                initialValue: _batchStrategy,
                decoration: const InputDecoration(
                  labelText: '编排策略',
                  helperText: '自动模式会根据任务差异选择串行或并行。',
                ),
                items: const [
                  DropdownMenuItem(value: 'auto', child: Text('自动')),
                  DropdownMenuItem(value: 'sequential', child: Text('串行')),
                  DropdownMenuItem(value: 'parallel', child: Text('并行')),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => _batchStrategy = value);
                },
              ),
              const SizedBox(height: DS.spacing10),
              if (tasks.isEmpty)
                Text(
                  '先让任务列表加载出来，或回到任务页创建几个正式任务，这里就会出现可批量委派的候选。',
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                )
              else ...[
                ...tasks.take(6).map(
                  (task) => CheckboxListTile(
                    value: _selectedTaskIds.contains(task.id),
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    title: Text(task.title),
                    subtitle: Text(task.type.name),
                    onChanged: (selected) {
                      setState(() {
                        if (selected ?? false) {
                          _selectedTaskIds.add(task.id);
                        } else {
                          _selectedTaskIds.remove(task.id);
                        }
                      });
                    },
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                FilledButton.icon(
                  onPressed: automation.isSubmittingBatch || _selectedTaskIds.isEmpty
                      ? null
                      : () => unawaited(_submitBatch(automation)),
                  icon: automation.isSubmittingBatch
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Icon(Icons.playlist_add_check_circle_rounded),
                  label: const Text('开始批量委派'),
                ),
              ],
              if (automation.latestBatch != null) ...[
                const SizedBox(height: DS.spacing12),
                _BatchSummaryCard(summary: automation.latestBatch!),
              ],
            ],
          ),
        ),
        const SizedBox(height: DS.spacing16),
        GraphiteCardSurface(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '定时 / 条件执行',
                style: DS.bodyMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                '给常规任务设一个节奏，或监听外部事件与条件。创建后 Sparkle 会按计划自动把它交给 OpenClaw。',
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              if (tasks.isEmpty)
                Text(
                  '需要先有正式任务，才能创建自动化执行。',
                  style: DS.bodySmall.copyWith(color: DS.textSecondary),
                )
              else ...[
                DropdownButtonFormField<String>(
                  initialValue: _selectedScheduleTaskId,
                  decoration: const InputDecoration(labelText: '绑定任务'),
                  items: tasks
                      .map(
                        (task) => DropdownMenuItem<String>(
                          value: task.id,
                          child: Text(task.title),
                        ),
                      )
                      .toList(growable: false),
                  onChanged: (value) {
                    setState(() => _selectedScheduleTaskId = value);
                  },
                ),
                const SizedBox(height: DS.spacing10),
                DropdownButtonFormField<String>(
                  initialValue: _triggerType,
                  decoration: const InputDecoration(labelText: '触发方式'),
                  items: const [
                    DropdownMenuItem(value: 'cron', child: Text('每天定时')),
                    DropdownMenuItem(value: 'event', child: Text('事件触发')),
                    DropdownMenuItem(value: 'condition', child: Text('条件轮询')),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _triggerType = value);
                  },
                ),
                const SizedBox(height: DS.spacing10),
                if (_triggerType == 'cron')
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<int>(
                          initialValue: _selectedHour,
                          decoration: const InputDecoration(labelText: '小时'),
                          items: List<DropdownMenuItem<int>>.generate(
                            24,
                            (index) => DropdownMenuItem(
                              value: index,
                              child: Text(index.toString().padLeft(2, '0')),
                            ),
                          ),
                          onChanged: (value) {
                            if (value != null) {
                              setState(() => _selectedHour = value);
                            }
                          },
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: DropdownButtonFormField<int>(
                          initialValue: _selectedMinute,
                          decoration: const InputDecoration(labelText: '分钟'),
                          items: List<DropdownMenuItem<int>>.generate(
                            12,
                            (index) {
                              final minute = index * 5;
                              return DropdownMenuItem(
                                value: minute,
                                child: Text(minute.toString().padLeft(2, '0')),
                              );
                            },
                          ),
                          onChanged: (value) {
                            if (value != null) {
                              setState(() => _selectedMinute = value);
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                if (_triggerType == 'event')
                  TextFormField(
                    controller: _eventTypeController,
                    decoration: const InputDecoration(
                      labelText: '事件类型',
                      helperText: '例如 pr_merged / inbox_arrived',
                    ),
                  ),
                if (_triggerType == 'condition') ...[
                  TextFormField(
                    controller: _checkUrlController,
                    decoration: const InputDecoration(
                      labelText: '检查地址',
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  TextFormField(
                    controller: _conditionController,
                    decoration: const InputDecoration(
                      labelText: '条件表达式',
                      helperText: "例如 contains('merged') 或 equals('ok')",
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  TextFormField(
                    controller: _intervalController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: '轮询间隔（分钟）',
                    ),
                  ),
                ],
                const SizedBox(height: DS.spacing10),
                FilledButton.icon(
                  onPressed: automation.isSavingSchedule || _selectedScheduleTaskId == null
                      ? null
                      : () => unawaited(_createSchedule(automation)),
                  icon: automation.isSavingSchedule
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Icon(Icons.add_alarm_rounded),
                  label: const Text('创建自动化'),
                ),
              ],
              if (automation.error != null &&
                  automation.error!.trim().isNotEmpty) ...[
                const SizedBox(height: DS.spacing10),
                Text(
                  automation.error!,
                  style: DS.bodySmall.copyWith(color: DS.semanticError),
                ),
              ],
              const SizedBox(height: DS.spacing16),
              if (automation.isLoading && automation.schedules.isEmpty)
                const Center(child: CircularProgressIndicator())
              else if (automation.schedules.isEmpty)
                Text(
                  '还没有任何自动化。先创建一个“每天定时”或“条件轮询”，这里就会显示后续运行计划。',
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
                )
              else
                ...automation.schedules.map(
                  (schedule) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing10),
                    child: _ScheduleCard(
                      schedule: schedule,
                      taskLabel: _taskLabelFor(tasks, schedule),
                      onPause: () => unawaited(automation.pauseSchedule(schedule.id)),
                      onResume: () => unawaited(automation.resumeSchedule(schedule.id)),
                      onDelete: () => unawaited(automation.deleteSchedule(schedule.id)),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }

  List<TaskModel> _serverTasks(TaskListState taskState) {
    final combined = <TaskModel>[
      ...taskState.todayTasks,
      ...taskState.recommendedTasks,
      ...taskState.tasks,
    ];
    final seen = <String>{};
    return combined
        .where((task) => isServerTaskId(task.id))
        .where((task) => seen.add(task.id))
        .toList(growable: false);
  }

  Future<void> _submitBatch(OpenClawAutomationService service) async {
    final ok = await service.handoffTaskBatch(
      _selectedTaskIds.toList(growable: false),
      executionStrategy: _batchStrategy,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? '批量委派已提交' : (service.error ?? '批量委派失败')),
        backgroundColor: ok ? DS.semanticSuccess : DS.semanticError,
      ),
    );
  }

  Future<void> _createSchedule(OpenClawAutomationService service) async {
    final taskId = _selectedScheduleTaskId;
    if (taskId == null) return;
    final triggerConfig = switch (_triggerType) {
      'event' => <String, dynamic>{
          'event_type': _eventTypeController.text.trim(),
        },
      'condition' => <String, dynamic>{
          'check_url': _checkUrlController.text.trim(),
          'condition': _conditionController.text.trim(),
          'interval_minutes': int.tryParse(_intervalController.text.trim()) ?? 15,
        },
      _ => <String, dynamic>{
          'cron':
              '${_selectedMinute.toString().padLeft(2, '0')} ${_selectedHour.toString().padLeft(2, '0')} * * *',
        },
    };
    final ok = await service.createSchedule(
      <String, dynamic>{
        'task_id': taskId,
        'trigger_type': _triggerType,
        'trigger_config': triggerConfig,
        'is_active': true,
      },
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? '自动化已创建' : (service.error ?? '自动化创建失败')),
        backgroundColor: ok ? DS.semanticSuccess : DS.semanticError,
      ),
    );
  }

  String _taskLabelFor(
    List<TaskModel> tasks,
    OpenClawExecutionSchedule schedule,
  ) {
    for (final task in tasks) {
      if (task.id == schedule.taskId) {
        return task.title;
      }
    }
    return schedule.intentTemplate['goal']?.toString() ?? schedule.taskId;
  }
}

class _BatchSummaryCard extends StatelessWidget {
  const _BatchSummaryCard({required this.summary});

  final OpenClawExecutionBatchSummary summary;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                OpenClawMetricPill(
                  icon: Icons.view_in_ar_rounded,
                  label: summary.resolvedStrategy,
                ),
                OpenClawMetricPill(
                  icon: Icons.check_circle_rounded,
                  label: '${summary.completedCount} 完成',
                  tone: OpenClawVisualTone.connected,
                ),
                OpenClawMetricPill(
                  icon: Icons.error_outline_rounded,
                  label: '${summary.failedCount} 失败',
                  tone: summary.failedCount > 0
                      ? OpenClawVisualTone.offline
                      : OpenClawVisualTone.active,
                ),
                OpenClawMetricPill(
                  icon: Icons.schedule_rounded,
                  label: '${summary.queuedCount} 排队',
                  tone: summary.queuedCount > 0
                      ? OpenClawVisualTone.attention
                      : OpenClawVisualTone.active,
                ),
              ],
            ),
            if (summary.items.isNotEmpty) ...[
              const SizedBox(height: DS.spacing10),
              ...summary.items.take(4).map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing6),
                  child: Text(
                    '${item.taskId} · ${item.status ?? 'unknown'}${item.errorMessage != null ? ' · ${item.errorMessage}' : ''}',
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      );
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({
    required this.schedule,
    required this.taskLabel,
    required this.onPause,
    required this.onResume,
    required this.onDelete,
  });

  final OpenClawExecutionSchedule schedule;
  final String taskLabel;
  final VoidCallback onPause;
  final VoidCallback onResume;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: schedule.isActive
                ? DS.semanticSuccess.withValues(alpha: 0.18)
                : DS.border,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    taskLabel,
                    style: DS.bodyMedium.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                OpenClawMetricPill(
                  icon: schedule.isActive
                      ? Icons.play_circle_rounded
                      : Icons.pause_circle_rounded,
                  label: schedule.isActive ? '运行中' : '已暂停',
                  tone: schedule.isActive
                      ? OpenClawVisualTone.connected
                      : OpenClawVisualTone.offline,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              _describeTrigger(schedule),
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '下次：${_formatDate(schedule.nextRunAt)} · 上次：${_formatDate(schedule.lastRunAt)}',
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing10),
            Row(
              children: [
                if (schedule.isActive)
                  OutlinedButton.icon(
                    onPressed: onPause,
                    icon: const Icon(Icons.pause_rounded),
                    label: const Text('暂停'),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: onResume,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: const Text('恢复'),
                  ),
                const SizedBox(width: DS.spacing12),
                TextButton.icon(
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline_rounded),
                  label: Text(
                    '删除',
                    style: DS.bodyMedium.copyWith(color: DS.semanticError),
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  static String _describeTrigger(OpenClawExecutionSchedule schedule) {
    if (schedule.triggerType == 'event') {
      return '事件触发：${schedule.triggerConfig['event_type'] ?? '未填写'}';
    }
    if (schedule.triggerType == 'condition') {
      return '条件轮询：${schedule.triggerConfig['condition'] ?? '未填写'}';
    }
    return '每天定时：${schedule.triggerConfig['cron'] ?? '未填写'}';
  }

  static String _formatDate(DateTime? value) {
    if (value == null) return '暂无';
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '${value.month}/${value.day} $hour:$minute';
  }
}
