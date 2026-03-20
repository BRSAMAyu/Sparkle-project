import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

/// 任务列表组件
/// 用于在聊天中批量显示 AI 生成的任务
class TaskListWidget extends StatefulWidget {
  // List of Map<String, dynamic>

  const TaskListWidget({
    required this.tasks,
    this.toolResultId,
    this.onConfirmAll,
    super.key,
  });
  final List<Map<String, dynamic>> tasks;
  final String? toolResultId;
  final Future<void> Function(String toolResultId)? onConfirmAll;

  @override
  State<TaskListWidget> createState() => _TaskListWidgetState();
}

class _TaskListWidgetState extends State<TaskListWidget> {
  bool _confirmed = false;
  bool _isConfirming = false;

  @override
  Widget build(BuildContext context) {
    if (widget.tasks.isEmpty) {
      return const SizedBox.shrink();
    }
    final listPayload = EntityCardPayload.fromRaw(
      {
        'tasks': widget.tasks,
        'tool_result_id': widget.toolResultId,
      },
      fallbackType: 'task_list',
    );
    final planId =
        _asString(listPayload.linkedEntities['plan_id']) ?? widget.tasks.first['plan_id']?.toString();

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.taskBatchCreateTitle(widget.tasks.length),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 10),
            if (planId != null && planId.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: DS.sm),
                child: Row(
                  children: [
                    Expanded(
                      child: SparkleButton.ghost(
                        label: '查看计划',
                        icon: const Icon(Icons.map_outlined, size: 16),
                        onPressed: () => context.push('/plans/$planId'),
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: SparkleButton.ghost(
                        label: '分享计划',
                        icon: const Icon(Icons.share_outlined, size: 16),
                        onPressed: () => _sharePlan(context),
                      ),
                    ),
                  ],
                ),
              ),
            ...widget.tasks.map((taskData) => _buildTaskItem(context, taskData)),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                SparkleButton(
                  label: context.l10n.taskViewAll,
                  variant: ButtonVariant.ghost,
                  icon: const Icon(Icons.arrow_forward_ios, size: 16),
                    onPressed: () {
                      // 导航到任务列表页面
                      unawaited(context.push('/tasks'));
                    },
                ),
                if (widget.toolResultId != null &&
                    widget.toolResultId!.trim().isNotEmpty &&
                    widget.onConfirmAll != null &&
                    !_confirmed)
                  SparkleButton(
                    label: _isConfirming ? '确认中...' : '确认全部任务',
                    icon: const Icon(Icons.check_circle_outline),
                    onPressed: _isConfirming ? null : _handleConfirmAll,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleConfirmAll() async {
    final toolResultId = widget.toolResultId;
    final onConfirmAll = widget.onConfirmAll;
    if (toolResultId == null ||
        toolResultId.trim().isEmpty ||
        onConfirmAll == null) {
      return;
    }
    setState(() => _isConfirming = true);
    try {
      await onConfirmAll(toolResultId);
      if (!mounted) return;
      setState(() => _confirmed = true);
    } catch (_) {
      // Error feedback handled by caller
    } finally {
      if (mounted) {
        setState(() => _isConfirming = false);
      }
    }
  }

  Widget _buildTaskItem(BuildContext context, Map<String, dynamic> taskData) {
    final title = taskData['title'] as String;
    final id = taskData['id'] as String;
    final taskModel = taskModelFromEntityPayload(taskData);

    if (taskModel != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Column(
          children: [
            TaskCard(
              task: taskModel,
              compact: true,
              onTap: () => context.push('/tasks/$id'),
            ),
            Padding(
              padding: const EdgeInsets.only(
                top: DS.spacing4,
                left: DS.spacing8,
                right: DS.spacing8,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      label: context.l10n.taskViewAll,
                      icon: const Icon(Icons.open_in_new_rounded, size: 16),
                      onPressed: () => context.push('/tasks/$id'),
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: SparkleButton.ghost(
                      label: '分享',
                      icon: const Icon(Icons.share_outlined, size: 16),
                      onPressed: () => _shareTask(context, taskData),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final type = taskData['type'] as String? ?? 'learning';
    final status = taskData['status'] as String? ?? 'pending';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          _buildTaskIcon(type),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
          _buildStatusChip(context, status),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            size: 32,
            icon: const Icon(Icons.info_outline, size: 20),
            onPressed: () {
              // 导航到任务详情页面
              unawaited(context.push('/tasks/$id'));
            },
          ),
        ],
      ),
    );
  }

  Future<void> _shareTask(
    BuildContext context,
    Map<String, dynamic> taskData,
  ) async {
    await showShareResourceSheet(
      context,
      resourceType: 'task',
      resourceId: taskData['id'] as String,
      title: taskData['title'] as String? ?? '任务卡片',
      subtitle: taskData['guide_content'] as String? ??
          taskData['description'] as String?,
    );
  }

  Future<void> _sharePlan(BuildContext context) async {
    final listPayload = EntityCardPayload.fromRaw(
      {
        'tasks': widget.tasks,
        'tool_result_id': widget.toolResultId,
      },
      fallbackType: 'task_list',
    );
    final planId =
        _asString(listPayload.linkedEntities['plan_id']) ?? widget.tasks.first['plan_id']?.toString();
    if (planId == null || planId.isEmpty) return;
    await showShareResourceSheet(
      context,
      resourceType: 'plan',
      resourceId: planId,
      title: _asString(listPayload.linkedEntities['plan_title']) ?? '学习计划',
      subtitle: '包含 ${widget.tasks.length} 个可执行任务',
    );
  }

  String? _asString(dynamic value) {
    if (value == null) return null;
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }

  Widget _buildTaskIcon(String type) {
    IconData icon;
    Color color;
    switch (type) {
      case 'learning':
        icon = Icons.menu_book;
        color = DS.brandPrimary;
      case 'training':
        icon = Icons.fitness_center;
        color = DS.brandPrimary;
      case 'error_fix':
        icon = Icons.bug_report;
        color = DS.error;
      case 'reflection':
        icon = Icons.psychology;
        color = DS.rarityEpic;
      case 'social':
        icon = Icons.people;
        color = DS.info;
      case 'planning':
        icon = Icons.event_note;
        color = DS.success;
      default:
        icon = Icons.task_alt;
        color = DS.brandPrimary;
    }
    return Icon(icon, size: 24, color: color);
  }

  Widget _buildStatusChip(BuildContext context, String status) {
    final l10n = context.l10n;
    Color color;
    String label;
    switch (status) {
      case 'pending':
        color = DS.brandPrimary;
        label = l10n.taskStatusPending;
      case 'in_progress':
        color = DS.brandPrimary;
        label = l10n.taskStatusInProgress;
      case 'completed':
        color = DS.success;
        label = l10n.taskStatusCompleted;
      case 'abandoned':
        color = DS.error;
        label = l10n.taskStatusAbandoned;
      default:
        color = DS.brandPrimary;
        label = status;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 12),
      ),
    );
  }
}
