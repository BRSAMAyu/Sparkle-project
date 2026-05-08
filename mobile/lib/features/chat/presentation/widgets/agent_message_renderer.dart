import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/collaboration_timeline.dart';
import 'package:sparkle/features/chat/presentation/widgets/collapsible_widget_wrapper.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/prism_behavior_card.dart';
import 'package:sparkle/features/knowledge/presentation/widgets/knowledge_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

/// Widget type configuration for collapsible wrapping.
class _WidgetTypeConfig {
  const _WidgetTypeConfig({
    required this.label,
    required this.icon,
    this.accentColor,
  });

  final String label;
  final IconData icon;
  final Color? accentColor;
}

/// Agent 消息渲染器
/// 根据消息中的 widgets 字段动态渲染不同类型的组件
///
/// All metadata widgets are wrapped in [CollapsibleWidgetWrapper] so they
/// default to a collapsed chip. Text bubbles are always visible.
/// When "pure mode" is enabled, metadata widgets are hidden entirely.
class AgentMessageRenderer extends ConsumerWidget {
  const AgentMessageRenderer({
    required this.message,
    super.key,
    this.onTaskAction,
    this.onConfirmation,
  });
  final ChatMessageModel message;
  final void Function(String taskId)? onTaskAction;
  final void Function(String actionId, bool confirmed)? onConfirmation;

  /// Map of widget type strings to their collapsible chip config.
  Map<String, _WidgetTypeConfig> _widgetConfigs(BuildContext context) =>
      <String, _WidgetTypeConfig>{
        'task_card': _WidgetTypeConfig(
          label: context.l10n.chatLabelTask,
          icon: Icons.check_circle_outline,
        ),
        'knowledge_card': _WidgetTypeConfig(
          label: context.l10n.chatWidgetKnowledge,
          icon: Icons.auto_stories,
        ),
        'task_list': _WidgetTypeConfig(
          label: context.l10n.chatActionTaskList,
          icon: Icons.list_alt,
        ),
        'plan_card': _WidgetTypeConfig(
          label: context.l10n.chatLabelPlan,
          icon: Icons.map_outlined,
        ),
        'plan_context_summary': _WidgetTypeConfig(
          label: context.l10n.chatWidgetPlanSummary,
          icon: Icons.summarize_outlined,
        ),
        'plan_state': _WidgetTypeConfig(
          label: context.l10n.chatWidgetPlanStatus,
          icon: Icons.flag_outlined,
        ),
        'prism_card': _WidgetTypeConfig(
          label: context.l10n.chatWidgetCognitiveAnalysis,
          icon: Icons.psychology_outlined,
        ),
        'achievement_card': _WidgetTypeConfig(
          label: context.l10n.chatLabelAchievement,
          icon: Icons.emoji_events_outlined,
          accentColor: DS.warning,
        ),
        'error_card': _WidgetTypeConfig(
          label: context.l10n.chatLabelError,
          icon: Icons.menu_book_outlined,
        ),
      };

  _WidgetTypeConfig _collaborationConfig(BuildContext context) =>
      _WidgetTypeConfig(
        label: context.l10n.chatWidgetCollaborationProcess,
        icon: Icons.hub_outlined,
      );

  _WidgetTypeConfig _errorInfoConfig(BuildContext context) => _WidgetTypeConfig(
        label: context.l10n.chatWidgetErrorHint,
        icon: Icons.warning_amber,
        accentColor: DS.error,
      );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chatPureMode = ref.watch(chatPureModeProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 1. 文本内容（始终可见，不受纯净模式影响）
        if (message.content.isNotEmpty)
          _buildTextBubble(context, message.content),

        // 2. 渲染所有 widgets（纯净模式下隐藏）
        if (!chatPureMode &&
            message.widgets != null &&
            message.widgets!.isNotEmpty)
          ...message.widgets!.map((w) => _buildWidget(context, w)),

        // 3. 多Agent协作时间线（纯净模式下隐藏）
        if (!chatPureMode && message.agentCollaboration != null)
          _buildCollaborationTimeline(context, message.agentCollaboration!),

        // 4. 错误提示（纯净模式下隐藏）
        if (!chatPureMode &&
            (message.hasErrors ?? false) &&
            message.errors != null)
          _buildErrorCard(context, message.errors!),

        // 5. 确认操作（始终显示，这是用户必须操作的）
        if ((message.requiresConfirmation ?? false) &&
            message.confirmationData != null)
          _buildConfirmationCard(context, message.confirmationData!),
      ],
    );
  }

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
    final config = _widgetConfigs(context)[widget.type];
    final inner = _buildInnerWidget(context, widget);

    // knowledge_card renders its own full content with expand by default
    // through the outer CollapsibleWidgetWrapper below
    if (widget.type == 'knowledge_card') {
      final knowledgeConfig = _widgetConfigs(context)['knowledge_card']!;
      return _wrap(
        label: knowledgeConfig.label,
        icon: knowledgeConfig.icon,
        accentColor: knowledgeConfig.accentColor,
        defaultExpanded: true,
        child: inner,
      );
    }

    // If no config found, render raw with a generic wrapper.
    if (config == null) {
      return _wrap(
        label: widget.type,
        icon: Icons.widgets_outlined,
        child: inner,
      );
    }

    return _wrap(
      label: config.label,
      icon: config.icon,
      accentColor: config.accentColor,
      child: inner,
    );
  }

  /// Builds the actual widget content (without collapsible wrapping).
  Widget _buildInnerWidget(BuildContext context, WidgetPayload widget) {
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
        try {
          return KnowledgeCard(data: widget.data);
        } catch (e) {
          debugPrint('Error rendering KnowledgeCard: $e');
          return CompactErrorCard(
            onRetry: null,
          );
        }

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
        return Semantics(
          button: true,
          label: 'Chat agent message renderer control 1',
          child: GestureDetector(
            onTap: planId != null
                ? () => context.push(entity.detailRoute ?? '/plans/$planId')
                : null,
            child: PlanCard(data: widget.data),
          ),
        );

      case 'plan_context_summary':
      case 'plan_state': // Legacy alias for compatibility
        try {
          return PlanContextSummary(contextData: widget.data);
        } catch (e) {
          debugPrint('Error rendering PlanContextSummary: $e');
          return const CompactErrorCard(onRetry: null);
        }

      case 'prism_card':
        try {
          return PrismBehaviorCard(data: widget.data);
        } catch (e) {
          debugPrint('Error rendering PrismBehaviorCard: $e');
          return const CompactErrorCard(onRetry: null);
        }

      case 'achievement_card':
        return _buildAchievementCard(context, widget.data);

      case 'error_card':
        return _buildErrorBookCard(context, widget.data);

      default:
        // 未知类型：显示 JSON
        return _buildUnknownWidget(context, widget);
    }
  }

  Widget _wrap({
    required String label,
    required IconData icon,
    required Widget child,
    Color? accentColor,
    bool defaultExpanded = false,
  }) =>
      Padding(
        padding: const EdgeInsets.only(top: DS.sm),
        child: CollapsibleWidgetWrapper(
          label: label,
          icon: icon,
          accentColor: accentColor,
          defaultExpanded: defaultExpanded,
          child: child,
        ),
      );

  Widget _buildAchievementCard(
      BuildContext context, Map<String, dynamic> data) {
    final name = (data['name'] ??
            data['title'] ??
            context.l10n.chatWidgetAchievementUnlock)
        .toString();
    final desc = (data['description'] ?? '').toString();
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(Icons.emoji_events, color: DS.warning, size: 32),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: Theme.of(context).textTheme.titleSmall),
                  if (desc.isNotEmpty)
                    Text(desc, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorBookCard(BuildContext context, Map<String, dynamic> data) {
    final subject = (data['subject'] ?? data['subject_code'] ?? '').toString();
    final question =
        (data['question_text'] ?? data['title'] ?? context.l10n.chatLabelError).toString();
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(Icons.menu_book, color: DS.warning, size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(question,
                      style: Theme.of(context).textTheme.titleSmall,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis),
                  if (subject.isNotEmpty)
                    Text(subject, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorCard(BuildContext context, List<ErrorInfo> errors) {
    final errorConfig = _errorInfoConfig(context);
    return _wrap(
      label: errorConfig.label,
      icon: errorConfig.icon,
      accentColor: errorConfig.accentColor,
      child: Card(
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
      ),
    );
  }

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

      final collabConfig = _collaborationConfig(context);

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

        return _wrap(
          label: collabConfig.label,
          icon: collabConfig.icon,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
            child: AgentCollaborationTimeline(
              steps: synthesized,
              workflowType:
                  workflowType == 'unknown' ? 'expert_routing' : workflowType,
              executionTime: executionTime,
            ),
          ),
        );
      }

      return _wrap(
        label: collabConfig.label,
        icon: collabConfig.icon,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
          child: AgentCollaborationTimeline(
            steps: steps,
            workflowType: workflowType,
            executionTime: executionTime,
          ),
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
