import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/collaboration_timeline.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/prism_behavior_card.dart';
import 'package:sparkle/features/knowledge/presentation/widgets/knowledge_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart'; // New widget for plan card
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Agent 消息渲染器
/// 根据消息中的 widgets 字段动态渲染不同类型的组件
class AgentMessageRenderer extends StatelessWidget {
  const AgentMessageRenderer({
    required this.message,
    super.key,
    this.onTaskAction,
    this.onConfirmation,
  });
  final ChatMessageModel message;
  final void Function(String taskId)? onTaskAction;
  final void Function(String actionId, bool confirmed)? onConfirmation;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. 文本内容（如果有）
          if (message.content.isNotEmpty)
            _buildTextBubble(context, message.content),

          // 2. 渲染所有 widgets
          if (message.widgets != null && message.widgets!.isNotEmpty)
            ...message.widgets!.map((widget) => _buildWidget(context, widget)),

          // 3. 多Agent协作时间线（如果有）
          if (message.agentCollaboration != null)
            _buildCollaborationTimeline(context, message.agentCollaboration!),

          // 4. 错误提示（如果有）
          if ((message.hasErrors ?? false) && message.errors != null)
            _buildErrorCard(context, message.errors!),

          // 5. 确认操作（如果需要）
          if ((message.requiresConfirmation ?? false) &&
              message.confirmationData != null)
            _buildConfirmationCard(context, message.confirmationData!),
        ],
      );

  Widget _buildTextBubble(BuildContext context, String text) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(text),
      );

  Widget _buildWidget(BuildContext context, WidgetPayload widget) {
    switch (widget.type) {
      case 'task_card':
        try {
          // Ensure mandatory fields for TaskModel are present
          final data = Map<String, dynamic>.from(widget.data);
          data['user_id'] ??= 'unknown';
          data['tags'] ??= <String>[];
          data['difficulty'] ??= 1;
          data['energy_cost'] ??= 1;
          data['priority'] ??= 1;
          data['created_at'] ??= DateTime.now().toIso8601String();
          data['updated_at'] ??= DateTime.now().toIso8601String();

          // Handle 'type' mapping if it's a string that might not match exactly or needs defaulting
          // Assuming the backend/LLM sends correct string matching the enum (e.g., "learning")

          final task = TaskModel.fromJson(data);
          return TaskCard(
            task: task,
            onTap: () => onTaskAction?.call(task.id),
          );
        } catch (e) {
          debugPrint('Error parsing TaskModel in AgentMessageRenderer: $e');
          return Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Text('Invalid task data: $e'),
            ),
          );
        }

      case 'knowledge_card':
        return KnowledgeCard(data: widget.data);

      case 'task_list':
        final rawTasks = widget.data['tasks'] as List<dynamic>?;
        return TaskListWidget(
          tasks: (rawTasks ?? <dynamic>[])
              .whereType<Map<String, dynamic>>()
              .toList(),
        );

      case 'plan_card':
        return PlanCard(data: widget.data);

      case 'plan_context_summary':
      case 'plan_state': // Legacy alias for compatibility
        return PlanContextSummary(contextData: widget.data);

      case 'prism_card':
        return PrismBehaviorCard(data: widget.data);

      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(widget);
    }
  }

  Widget _buildErrorCard(BuildContext context, List<ErrorInfo> errors) => Card(
        color: Theme.of(context).colorScheme.errorContainer,
        margin: const EdgeInsets.symmetric(vertical: 8),
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.warning_amber,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  const SizedBox(width: DS.sm),
                  Text(
                    '操作遇到问题',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.sm),
              ...errors.map(
                (e) => Text(
                  '• ${e.message}',
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
              if (errors.any((e) => e.suggestion != null))
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    '建议：${errors.firstWhere((e) => e.suggestion != null).suggestion}',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(fontStyle: FontStyle.italic),
                  ),
                ),
            ],
          ),
        ),
      );

  Widget _buildConfirmationCard(
    BuildContext context,
    ConfirmationData data,
  ) {
    var title = '需要确认';
    var description = data.description;
    var confirmLabel = '确认执行';

    if (data.toolName == 'update_user_preference') {
      title = '确认偏好更新';
      final prefKey = data.preview['pref_key'] ?? data.preview['key'];
      final prefValue = data.preview['pref_value'] ?? data.preview['value'];
      if (prefKey != null && prefValue != null) {
        description = '将偏好「$prefKey」更新为「$prefValue」。';
      } else if (prefKey != null) {
        description = '确认更新你的偏好「$prefKey」。';
      } else {
        description = '确认更新你的偏好设置。';
      }
      confirmLabel = '确认更新';
    }

    return Card(
      color: Theme.of(context).colorScheme.tertiaryContainer,
      margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: DS.sm),
            Text(description),
            const SizedBox(height: DS.md),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                SparkleButton.ghost(
                  label: '取消',
                  onPressed: () => onConfirmation?.call(data.actionId, false),
                ),
                const SizedBox(width: DS.sm),
                SparkleButton.primary(
                  label: confirmLabel,
                  onPressed: () => onConfirmation?.call(data.actionId, true),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCollaborationTimeline(
    BuildContext context,
    Map<String, dynamic> collaborationData,
  ) {
    try {
      // Extract workflow type
      final workflowType =
          collaborationData['workflow_type'] as String? ?? 'unknown';

      // Extract execution time
      final executionTimeRaw = collaborationData['execution_time_ms'];
      final executionTimeMs =
          executionTimeRaw is num ? executionTimeRaw.toInt() : 0;
      final executionTime = executionTimeMs / 1000.0;

      // Extract steps
      final stepsList = (collaborationData['steps'] as List<dynamic>?) ??
          (collaborationData['timeline'] as List<dynamic>?);
      final steps = stepsList
              ?.map(
                  (e) => AgentTimelineStep.fromJson(e as Map<String, dynamic>),)
              .toList() ??
          [];

      if (steps.isEmpty) {
        final selectedExpertsRaw = collaborationData['selected_experts'];
        final routingStrategy =
            collaborationData['routing_strategy'] as String?;
        final fallbackReason = collaborationData['fallback_reason'] as String?;
        final selectedExperts = selectedExpertsRaw is List
            ? selectedExpertsRaw.map((e) => '$e').toList()
            : <String>[];

        if (selectedExperts.isEmpty) {
          return const SizedBox.shrink();
        }

        final synthesized = <AgentTimelineStep>[
          ...selectedExperts.map(
            (expert) => AgentTimelineStep.fromJson({
              'agent': expert,
              'action':
                  routingStrategy == null ? '专家路由' : '策略: $routingStrategy',
            }),
          ),
        ];
        if (fallbackReason != null && fallbackReason.isNotEmpty) {
          synthesized.add(
            AgentTimelineStep.fromJson({
              'agent': 'orchestrator',
              'action': '降级: $fallbackReason',
            }),
          );
        }

        return Padding(
          padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          child: AgentCollaborationTimeline(
            steps: synthesized,
            workflowType:
                workflowType == 'unknown' ? 'expert_routing' : workflowType,
            executionTime: executionTime,
          ),
        );
      }

      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
        child: AgentCollaborationTimeline(
          steps: steps,
          workflowType: workflowType,
          executionTime: executionTime,
        ),
      );
    } catch (e) {
      debugPrint('Error building collaboration timeline: $e');
      return const SizedBox.shrink();
    }
  }

  Widget _buildUnknownWidget(WidgetPayload widget) => Card(
        margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
        child: Padding(
          padding: const EdgeInsets.all(DS.sm),
          child: Text('Unknown widget type: ${widget.type}'),
        ),
      );
}
