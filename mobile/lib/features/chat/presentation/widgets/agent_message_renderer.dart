import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/collaboration_timeline.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/prism_behavior_card.dart';
import 'package:sparkle/features/knowledge/presentation/widgets/knowledge_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

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
        child: SparkleMarkdown(
          content: text,
          textColor: Theme.of(context).colorScheme.onSurface,
          codeBackgroundColor:
              Theme.of(context).colorScheme.surfaceContainerHigh,
          linkColor: Theme.of(context).colorScheme.primary,
          contentRole: SparkleMarkdownRole.chatBubble,
        ),
      );

  Widget _buildWidget(BuildContext context, WidgetPayload widget) {
    switch (widget.type) {
      case 'task_card':
        try {
          final entity =
              EntityCardPayload.fromRaw(widget.data, fallbackType: 'task');
          final task = taskModelFromEntityPayload(widget.data);
          if (task == null) {
            throw StateError('Unable to parse task entity payload');
          }
          return TaskCard(
            task: task,
            onTap: () => onTaskAction?.call(entity.entityId ?? task.id),
          );
        } catch (e) {
          debugPrint('Error parsing TaskModel in AgentMessageRenderer: $e');
          return Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Text(
                context.l10n.chatTaskDataInvalid(e.toString()),
              ),
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
        final entity =
            EntityCardPayload.fromRaw(widget.data, fallbackType: 'plan');
        final planId = entity.entityId ??
            widget.data['id']?.toString() ??
            widget.data['plan_id']?.toString();
        return GestureDetector(
          onTap: planId != null
              ? () => context.push(entity.detailRoute ?? '/plans/$planId')
              : null,
          child: PlanCard(data: widget.data),
        );

      case 'plan_context_summary':
      case 'plan_state': // Legacy alias for compatibility
        return PlanContextSummary(contextData: widget.data);

      case 'prism_card':
        return PrismBehaviorCard(data: widget.data);

      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(context, widget);
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
                    context.l10n.chatActionErrorTitle,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.sm),
              ...errors.map(
                (e) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        margin: const EdgeInsets.only(top: 7, right: 8),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          e.message,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (errors.any((e) => e.suggestion != null))
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    context.l10n.chatActionErrorSuggestion(
                      errors
                          .firstWhere((e) => e.suggestion != null)
                          .suggestion!,
                    ),
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
    final l10n = context.l10n;
    var title = l10n.chatConfirmationTitleDefault;
    var description = data.description;
    var confirmLabel = l10n.chatConfirmationActionDefault;

    if (data.toolName == 'update_user_preference') {
      title = l10n.chatConfirmationTitleUpdatePreference;
      final prefKey = data.preview['pref_key'] ?? data.preview['key'];
      final prefValue = data.preview['pref_value'] ?? data.preview['value'];
      if (prefKey != null && prefValue != null) {
        description = l10n.chatConfirmationUpdatePreferenceWithValue(
          prefKey.toString(),
          prefValue.toString(),
        );
      } else if (prefKey != null) {
        description =
            l10n.chatConfirmationUpdatePreferenceKeyOnly(prefKey.toString());
      } else {
        description = l10n.chatConfirmationUpdatePreferenceGeneric;
      }
      confirmLabel = l10n.chatConfirmationConfirmUpdate;
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
                  label: l10n.cancel,
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
                (e) => AgentTimelineStep.fromJson(e as Map<String, dynamic>),
              )
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
              'action': routingStrategy == null
                  ? context.l10n.chatAgentRouting
                  : context.l10n.chatAgentRoutingStrategy(
                      routingStrategy,
                    ),
            }),
          ),
        ];
        if (fallbackReason != null && fallbackReason.isNotEmpty) {
          synthesized.add(
            AgentTimelineStep.fromJson({
              'agent': 'orchestrator',
              'action': context.l10n.chatAgentRoutingFallback(fallbackReason),
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

  Widget _buildUnknownWidget(
    BuildContext context,
    WidgetPayload widget,
  ) =>
      Card(
        margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
        child: Padding(
          padding: const EdgeInsets.all(DS.sm),
          child: Text(context.l10n.chatUnknownWidgetType(widget.type)),
        ),
      );
}
