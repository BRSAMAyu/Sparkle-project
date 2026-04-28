import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
              label: context.l10n.openclawAutomationScheduleCount(automation.schedules.length),
              tone: automation.schedules.isNotEmpty
                  ? OpenClawVisualTone.active
                  : OpenClawVisualTone.offline,
            ),
            OpenClawMetricPill(
              icon: Icons.playlist_play_rounded,
              label: context.l10n.openclawBatchCandidateCount(_selectedTaskIds.length),
              tone: _selectedTaskIds.isNotEmpty
                  ? OpenClawVisualTone.connected
                  : OpenClawVisualTone.active,
              emphasized: _selectedTaskIds.isNotEmpty,
            ),
          ],
        ),
        const SizedBox(height: DS.spacing12),
        Text(
          context.l10n.openclawAutomationIntro,
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
                context.l10n.openclawBatchDelegation,
                style: DS.bodyMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.openclawBatchDelegationDesc,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              DropdownButtonFormField<String>(
                initialValue: _batchStrategy,
                decoration: InputDecoration(
                  labelText: context.l10n.openclawOrchestrationStrategy,
                  helperText: context.l10n.openclawOrchestrationStrategyHelper,
                ),
                items: [
                  DropdownMenuItem(value: 'auto', child: Text(context.l10n.openclawModeAuto)),
                  DropdownMenuItem(value: 'sequential', child: Text(context.l10n.openclawModeSequential)),
                  DropdownMenuItem(value: 'parallel', child: Text(context.l10n.openclawModeParallel)),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => _batchStrategy = value);
                },
              ),
              const SizedBox(height: DS.spacing10),
              if (tasks.isEmpty)
                Text(
                  context.l10n.openclawBatchEmptyHint,
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
                  label: Text(context.l10n.openclawStartBatchDelegation),
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
                context.l10n.openclawScheduledConditionExecution,
                style: DS.bodyMedium.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.openclawScheduledConditionDesc,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              if (tasks.isEmpty)
                Text(
                  context.l10n.openclawNeedTaskFirst,
                  style: DS.bodySmall.copyWith(color: DS.textSecondary),
                )
              else ...[
                DropdownButtonFormField<String>(
                  initialValue: _selectedScheduleTaskId,
                  decoration: InputDecoration(labelText: context.l10n.openclawBindTask),
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
                  decoration: InputDecoration(labelText: context.l10n.openclawTriggerMethod),
                  items: [
                    DropdownMenuItem(value: 'cron', child: Text(context.l10n.openclawTriggerDaily)),
                    DropdownMenuItem(value: 'event', child: Text(context.l10n.openclawTriggerEvent)),
                    DropdownMenuItem(value: 'condition', child: Text(context.l10n.openclawTriggerCondition)),
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
                          decoration: InputDecoration(labelText: context.l10n.openclawHour),
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
                          decoration: InputDecoration(labelText: context.l10n.openclawMinute),
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
                    decoration: InputDecoration(
                      labelText: context.l10n.openclawEventType,
                      helperText: context.l10n.openclawEventTypeHelper,
                    ),
                  ),
                if (_triggerType == 'condition') ...[
                  TextFormField(
                    controller: _checkUrlController,
                    decoration: const InputDecoration(
                      labelText: context.l10n.openclawCheckUrl,
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  TextFormField(
                    controller: _conditionController,
                    decoration: const InputDecoration(
                      labelText: context.l10n.openclawConditionExpression,
                      helperText: context.l10n.openclawConditionHelper,
                    ),
                  ),
                  const SizedBox(height: DS.spacing10),
                  TextFormField(
                    controller: _intervalController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: context.l10n.openclawPollingInterval,
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
                  label: Text(context.l10n.openclawCreateAutomation),
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
                  context.l10n.openclawNoAutomationHint,
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
      ok
          ? SparkleSnackBar.success(context.l10n.openclawBatchSubmitted)
          : SparkleSnackBar.error(service.error ?? context.l10n.openclawBatchFailed),
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
        content: Text(ok ? context.l10n.openclawAutomationCreated : (service.error ?? context.l10n.openclawAutomationCreateFailed)),
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
                  label: context.l10n.openclawCompletedCount(summary.completedCount),
                  tone: OpenClawVisualTone.connected,
                ),
                OpenClawMetricPill(
                  icon: Icons.error_outline_rounded,
                  label: context.l10n.openclawFailedCount(summary.failedCount),
                  tone: summary.failedCount > 0
                      ? OpenClawVisualTone.offline
                      : OpenClawVisualTone.active,
                ),
                OpenClawMetricPill(
                  icon: Icons.schedule_rounded,
                  label: context.l10n.openclawQueuedCount(summary.queuedCount),
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
                  label: schedule.isActive ? context.l10n.openclawRunning : context.l10n.openclawPaused,
                  tone: schedule.isActive
                      ? OpenClawVisualTone.connected
                      : OpenClawVisualTone.offline,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              _describeTrigger(context, schedule),
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.openclawNextRunLastRun(
                next: _formatDate(schedule.nextRunAt),
                last: _formatDate(schedule.lastRunAt),
              ),
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing10),
            Row(
              children: [
                if (schedule.isActive)
                  OutlinedButton.icon(
                    onPressed: onPause,
                    icon: const Icon(Icons.pause_rounded),
                    label: Text(context.l10n.openclawPause),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: onResume,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: Text(context.l10n.openclawResume),
                  ),
                const SizedBox(width: DS.spacing12),
                TextButton.icon(
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline_rounded),
                  label: Text(
                    context.l10n.openclawDelete,
                    style: DS.bodyMedium.copyWith(color: DS.semanticError),
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  static String _describeTrigger(BuildContext context, OpenClawExecutionSchedule schedule) {
    if (schedule.triggerType == 'event') {
      return context.l10n.openclawEventTriggerLabel(
        eventType: '${schedule.triggerConfig['event_type'] ?? context.l10n.openclawNotFilled}',
      );
    }
    if (schedule.triggerType == 'condition') {
      return context.l10n.openclawConditionTriggerLabel(
        condition: '${schedule.triggerConfig['condition'] ?? context.l10n.openclawNotFilled}',
      );
    }
    return context.l10n.openclawCronTriggerLabel(
      cron: '${schedule.triggerConfig['cron'] ?? context.l10n.openclawNotFilled}',
    );
  }

  static String _formatDate(DateTime? value) {
    if (value == null) return '';
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '${value.month}/${value.day} $hour:$minute';
  }
}
