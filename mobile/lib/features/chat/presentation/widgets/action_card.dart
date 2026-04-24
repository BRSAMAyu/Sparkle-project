import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart'
    show CustomButton, CustomButtonSize;
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_nudge_entry.dart';
import 'package:sparkle/features/chat/presentation/widgets/bottleneck_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/focus_action_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/graph_diagnostic_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_progress_strip.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_strategy_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/profile_front_door_card.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_card.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_result_renderer.dart';
import 'package:sparkle/features/task/presentation/widgets/task_card.dart';
import 'package:sparkle/features/task/utils/task_identity.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

class ActionCard extends StatefulWidget {
  const ActionCard({
    required this.action,
    super.key,
    this.onConfirm,
    this.onDismiss,
    this.onConfirmTasks,
    this.onConfirmAllTasks,
    this.onPlanNavigation,
    this.onWidgetAction,
  });
  final WidgetPayload action;
  final VoidCallback? onConfirm;
  final VoidCallback? onDismiss;
  final Future<void> Function(String toolResultId)? onConfirmTasks;
  final Future<void> Function(String toolResultId)? onConfirmAllTasks;
  final void Function(String planId)? onPlanNavigation;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;

  @override
  State<ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<ActionCard> with TickerProviderStateMixin {
  static const Set<String> _narrativeKeys = {
    'summary',
    'description',
    'message',
    'subtitle',
    'label',
    'headline',
  };

  static const Set<String> _hiddenGenericKeys = {
    'id',
    'plan_id',
    'task_id',
    'tool_result_id',
    'status_filter',
    'total_tasks',
    'completed_tasks',
    'plans',
    'workflow_id',
    'trace_id',
    'response_id',
    'session_id',
    'run_id',
    'entity_id',
    'linked_entities',
    'linkedentities',
    'metadata',
    'raw',
  };

  late AnimationController _pulseController;
  late Animation<double> _iconScaleAnimation;
  late AnimationController _pressController;
  final TextEditingController _reflectionController = TextEditingController();
  String? _selectedReflectionOption;
  bool _reflectionSubmitted = false;
  late bool _detailsExpanded;
  bool _confirmingTasks = false;
  bool _confirmedTasks = false;
  bool _hiddenAfterAction = false;

  @override
  void initState() {
    super.initState();
    _detailsExpanded = !_shouldCollapseByDefault(widget.action);
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _iconScaleAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _pressController = AnimationController(
      vsync: this,
      duration: SparkleMotion.fast,
    );

    if (widget.onConfirm != null || widget.onDismiss != null) {
      unawaited(_pulseController.repeat(reverse: true));
    }
  }

  @override
  void didUpdateWidget(covariant ActionCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.action != widget.action) {
      _detailsExpanded = !_shouldCollapseByDefault(widget.action);
      _hiddenAfterAction = false;
    }
  }

  @override
  void dispose() {
    _reflectionController.dispose();
    _pulseController.dispose();
    _pressController.dispose();
    super.dispose();
  }

  Future<void> _handleConfirmTasks(String toolResultId) async {
    setState(() => _confirmingTasks = true);
    try {
      await widget.onConfirmTasks!(toolResultId);
      widget.onConfirm?.call();
      if (mounted) {
        setState(() => _confirmedTasks = true);
      }
    } catch (_) {
      // Error feedback handled by caller
    } finally {
      if (mounted) {
        setState(() => _confirmingTasks = false);
      }
    }
  }

  Future<void> _handleConfirmAllTasks(String toolResultId) async {
    setState(() => _confirmingTasks = true);
    try {
      await widget.onConfirmAllTasks!(toolResultId);
      widget.onConfirm?.call();
      if (mounted) {
        setState(() => _confirmedTasks = true);
      }
    } catch (_) {
      // Error feedback handled by caller
    } finally {
      if (mounted) {
        setState(() => _confirmingTasks = false);
      }
    }
  }

  Future<void> _shareResource({
    required String resourceType,
    required String resourceId,
    required String title,
    String? subtitle,
  }) async {
    await showShareResourceSheet(
      context,
      resourceType: resourceType,
      resourceId: resourceId,
      title: title,
      subtitle: subtitle,
    );
  }

  bool _hasStablePlanId(String? id) =>
      id != null &&
      RegExp(
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
      ).hasMatch(id);

  @override
  Widget build(BuildContext context) {
    if (_hiddenAfterAction) {
      return const SizedBox.shrink();
    }

    // focus_card 类型直接使用 FocusActionCard，支持自动启动
    if (widget.action.type == 'focus_card') {
      final actionType = widget.action.data['action']?.toString();
      final shouldAutoStart = actionType == 'start';

      // 自动启动番茄钟
      if (shouldAutoStart) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _handleFocusCardAction(context, widget.action);
        });
      }

      return FocusActionCard(data: widget.action.data);
    }

    if (widget.action.type == 'task_card') {
      try {
        final data = Map<String, dynamic>.from(widget.action.data);
        final entity = EntityCardPayload.fromRaw(data, fallbackType: 'task');
        final task = taskModelFromEntityPayload(data);
        if (task == null) {
          throw StateError('Unable to normalize task payload');
        }
        final status = data['status']?.toString();
        final isAlreadyActive =
            status == 'IN_PROGRESS' || status == 'COMPLETED';
        final toolResultId =
            entity.toolResultId ?? data['tool_result_id']?.toString();
        final canConfirm =
            toolResultId != null && toolResultId.trim().isNotEmpty;
        final detailRoute = entity.detailRoute;
        final share = entity.share;
        final canShareTask = isServerTaskId(task.id) &&
            ((share?.resourceId ?? task.id).isNotEmpty);
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TaskCard(
              task: task,
              onTap: () => context.push(detailRoute ?? '/tasks/${task.id}'),
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
                      label: '查看任务',
                      icon: const Icon(Icons.open_in_new_rounded),
                      onPressed: () => unawaited(
                        context.push(detailRoute ?? '/tasks/${task.id}'),
                      ),
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: SparkleButton(
                      label: '分享卡片',
                      variant: ButtonVariant.ghost,
                      icon: const Icon(Icons.share_outlined),
                      onPressed: canShareTask
                          ? () => unawaited(
                                _shareResource(
                                  resourceType: share?.resourceType ?? 'task',
                                  resourceId: share?.resourceId ?? task.id,
                                  title: share?.title ?? task.title,
                                  subtitle:
                                      share?.subtitle ?? task.guideContent,
                                ),
                              )
                          : () {},
                      disabled: !canShareTask,
                    ),
                  ),
                ],
              ),
            ),
            if (!isAlreadyActive &&
                canConfirm &&
                widget.onConfirmTasks != null &&
                !_confirmedTasks)
              Padding(
                padding: const EdgeInsets.only(
                  top: DS.spacing4,
                  left: DS.spacing8,
                  right: DS.spacing8,
                ),
                child: SparkleButton(
                  label: _confirmingTasks ? '确认中...' : '确认任务',
                  onPressed: _confirmingTasks
                      ? null
                      : () => unawaited(_handleConfirmTasks(toolResultId)),
                ),
              ),
          ],
        );
      } catch (e) {
        debugPrint('Error parsing task card data: $e');
      }
    }

    final resolvedType = _resolveActionType(widget.action);
    final hasAction = (widget.onConfirm != null || widget.onDismiss != null) &&
        !_usesCustomCta(resolvedType);
    final confirmLabel = _getConfirmLabel(widget.action.type);
    final dismissLabel = _getDismissLabel(widget.action.type);
    final isCollapsible = _isCollapsible(widget.action);
    final supportsTapToggle = isCollapsible;
    final isPressable = hasAction || supportsTapToggle;

    void toggleDetails() {
      setState(() {
        _detailsExpanded = !_detailsExpanded;
      });
    }

    return GestureDetector(
      onTapDown: isPressable ? (_) => _pressController.forward() : null,
      onTapUp: isPressable ? (_) => _pressController.reverse() : null,
      onTapCancel: isPressable ? () => _pressController.reverse() : null,
      onTap: supportsTapToggle
          ? () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
              );
              toggleDetails();
            }
          : hasAction
              ? () => unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  )
              : null,
      child: SparkleMotion.pressScale(
        animation: _pressController,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: context.colors.surfaceCard,
            borderRadius: DS.borderRadius16,
            boxShadow: DS.shadowMd,
          ),
          child: ClipRRect(
            borderRadius: DS.borderRadius16,
            child: Stack(
              children: [
                // Gradient Stripe
                Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 4,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: _getActionGradientFor(widget.action),
                    ),
                  ),
                ),

                // Shimmer overlay for unconfirmed actions
                if (hasAction)
                  Positioned.fill(
                    child: TweenAnimationBuilder<double>(
                      tween: Tween(begin: -2.0, end: 2.0),
                      duration: const Duration(seconds: 3),
                      builder: (context, value, child) => Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              DS.surfacePrimary.withValues(alpha: 0),
                              DS.brandPrimary.withValues(alpha: 0.1),
                              DS.surfacePrimary.withValues(alpha: 0),
                            ],
                            stops: [
                              (value - 0.3).clamp(0.0, 1.0),
                              value.clamp(0.0, 1.0),
                              (value + 0.3).clamp(0.0, 1.0),
                            ],
                          ),
                        ),
                      ),
                      onEnd: () {
                        // Restart animation
                        if (mounted) setState(() {});
                      },
                    ),
                  ),

                Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          AnimatedBuilder(
                            animation: _iconScaleAnimation,
                            builder: (context, child) => Transform.scale(
                              scale:
                                  hasAction ? _iconScaleAnimation.value : 1.0,
                              child: Container(
                                padding: const EdgeInsets.all(DS.spacing8),
                                decoration: BoxDecoration(
                                  gradient:
                                      _getActionGradientFor(widget.action),
                                  shape: BoxShape.circle,
                                  boxShadow: [
                                    BoxShadow(
                                      color: _getActionColorFor(widget.action)
                                          .withValues(alpha: 0.3),
                                      blurRadius: 8,
                                      offset: const Offset(0, 2),
                                    ),
                                  ],
                                ),
                                child: Icon(
                                  _getActionIconFor(widget.action),
                                  color: DS.brandPrimaryConst,
                                  size: DS.iconSizeSm,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: Text(
                              _getTitleForAction(widget.action.type),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(
                                    fontWeight: DS.fontWeightBold,
                                    color: DS.neutral900,
                                  ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing16),
                      if (isCollapsible && !_detailsExpanded)
                        _buildCollapsedPreview(context, widget.action)
                      else
                        _buildContentForAction(context, widget.action),
                      if (isCollapsible) ...[
                        const SizedBox(height: DS.spacing12),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton.icon(
                            onPressed: () {
                              setState(() {
                                _detailsExpanded = !_detailsExpanded;
                              });
                            },
                            icon: Icon(
                              _detailsExpanded
                                  ? Icons.unfold_less_rounded
                                  : Icons.unfold_more_rounded,
                              size: DS.iconSizeSm,
                            ),
                            label: Text(
                              _detailsExpanded
                                  ? context.l10n.commonCollapse
                                  : context.l10n.commonExpand,
                            ),
                          ),
                        ),
                      ],
                      if (hasAction) ...[
                        const SizedBox(height: DS.spacing16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            if (widget.onDismiss != null)
                              CustomButton.text(
                                text: dismissLabel,
                                onPressed: () => unawaited(
                                  _handleGenericDismiss(widget.action),
                                ),
                                size: CustomButtonSize.small,
                              ),
                            const SizedBox(width: DS.spacing8),
                            if (widget.onConfirm != null)
                              CustomButton.primary(
                                text: confirmLabel,
                                icon: Icons.check_rounded,
                                onPressed: () => unawaited(
                                  _handleGenericConfirm(widget.action),
                                ),
                                size: CustomButtonSize.small,
                                customGradient:
                                    _getActionGradientFor(widget.action),
                              ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _resolveActionType(WidgetPayload action) {
    if (action.type == 'system_update') {
      return action.data['type']?.toString() ?? action.type;
    }
    return action.type;
  }

  bool _usesCustomCta(String type) =>
      type == 'task_list' || type == 'plan_card';

  LinearGradient _getActionGradientFor(WidgetPayload action) =>
      _getActionGradient(_resolveActionType(action));

  Color _getActionColorFor(WidgetPayload action) =>
      _getActionColor(_resolveActionType(action));

  IconData _getActionIconFor(WidgetPayload action) =>
      _getActionIcon(_resolveActionType(action));

  LinearGradient _getActionGradient(String type) {
    switch (type) {
      case 'create_task':
      case 'task_list':
        return DS.primaryGradient;
      case 'create_plan':
        return DS.secondaryGradient;
      case 'update_preference':
        return DS.infoGradient;
      case 'add_error':
        return DS.warningGradient;
      case 'focus_card':
        return DS.secondaryGradient;
      case 'behavior_pattern_archived':
        return DS.successGradient;
      case 'system_update':
        return DS.infoGradient;
      case 'nightly_review':
        return DS.cardGradientNeutral;
      case 'execution_summary':
        return DS.infoGradient;
      case 'execution_suggestion':
        return LinearGradient(
          colors: [DS.info, DS.primaryBase],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'evolution_card':
        return DS.infoGradient;
      case 'progress_card':
        return LinearGradient(
          colors: [DS.success, DS.secondaryBase],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'reflection_card':
        return DS.warningGradient;
      case 'source_summary':
        return DS.secondaryGradient;
      case 'next_actions':
        return DS.primaryGradient;
      case 'adaptation_summary':
        return LinearGradient(
          colors: [
            DS.info.withValues(alpha: 0.95),
            DS.success.withValues(alpha: 0.9),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'profile_front_door':
        return const LinearGradient(
          colors: [Color(0xFF0EA5A4), Color(0xFF4F46E5)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'continuity_banner':
      case 'mode_explanation':
        return DS.cardGradientNeutral;
      case 'blocked_input_request':
        return DS.warningGradient;
      case 'planning_bottleneck_card':
        return LinearGradient(
          colors: [
            DS.warning.withValues(alpha: 0.95),
            DS.error.withValues(alpha: 0.9),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'planning_strategy_card':
        return LinearGradient(
          colors: [DS.primaryBase, DS.secondaryBase],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      case 'planning_progress_strip':
        return DS.infoGradient;
      case 'aurora_nudge_entry':
        return const LinearGradient(
          colors: [Color(0xFF0EA5A4), Color(0xFF4F46E5)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        );
      default:
        return DS.primaryGradient;
    }
  }

  Color _getActionColor(String type) {
    switch (type) {
      case 'create_task':
      case 'task_list':
        return DS.primaryBase;
      case 'create_plan':
        return DS.secondaryBase;
      case 'update_preference':
        return DS.info;
      case 'add_error':
        return DS.warning;
      case 'focus_card':
        return DS.secondaryBase;
      case 'memory_health_report':
      case 'memory_evidence_missing':
      case 'memory_evidence_repaired':
      case 'memory_decay_applied':
      case 'behavior_pattern_decayed':
        return DS.info;
      case 'behavior_pattern_archived':
        return DS.success;
      case 'system_update':
        return DS.info;
      case 'nightly_review':
        return DS.neutral700;
      case 'execution_summary':
        return DS.info;
      case 'execution_suggestion':
        return DS.primaryBase;
      case 'evolution_card':
        return DS.info;
      case 'progress_card':
        return DS.success;
      case 'reflection_card':
        return DS.warning;
      case 'source_summary':
        return DS.secondaryBase;
      case 'next_actions':
        return DS.primaryBase;
      case 'adaptation_summary':
        return DS.info;
      case 'profile_front_door':
        return const Color(0xFF0EA5A4);
      case 'continuity_banner':
      case 'mode_explanation':
        return DS.neutral700;
      case 'blocked_input_request':
        return DS.warning;
      case 'planning_bottleneck_card':
        return DS.warning;
      case 'planning_strategy_card':
        return DS.primaryBase;
      case 'planning_progress_strip':
        return DS.info;
      case 'aurora_nudge_entry':
        return const Color(0xFF0EA5A4);
      default:
        return DS.primaryBase;
    }
  }

  IconData _getActionIcon(String type) {
    switch (type) {
      case 'create_task':
        return Icons.add_task_rounded;
      case 'task_list':
        return Icons.format_list_bulleted_rounded;
      case 'create_plan':
        return Icons.map_rounded;
      case 'update_preference':
        return Icons.settings_rounded;
      case 'add_error':
        return Icons.error_outline_rounded;
      case 'focus_card':
        return Icons.timer_rounded;
      case 'memory_health_report':
        return Icons.health_and_safety_rounded;
      case 'memory_evidence_missing':
        return Icons.report_problem_rounded;
      case 'memory_evidence_repaired':
        return Icons.build_rounded;
      case 'memory_decay_applied':
        return Icons.trending_down_rounded;
      case 'behavior_pattern_archived':
        return Icons.archive_rounded;
      case 'behavior_pattern_decayed':
        return Icons.show_chart_rounded;
      case 'system_update':
        return Icons.auto_awesome_rounded;
      case 'nightly_review':
        return Icons.nightlight_round;
      case 'execution_summary':
        return Icons.task_alt_rounded;
      case 'execution_suggestion':
        return Icons.rocket_launch_rounded;
      case 'evolution_card':
        return Icons.auto_awesome_motion_rounded;
      case 'progress_card':
        return Icons.insights_rounded;
      case 'reflection_card':
        return Icons.psychology_alt_rounded;
      case 'source_summary':
        return Icons.fact_check_rounded;
      case 'next_actions':
        return Icons.alt_route_rounded;
      case 'adaptation_summary':
        return Icons.tune_rounded;
      case 'profile_front_door':
        return Icons.psychology_rounded;
      case 'continuity_banner':
        return Icons.link_rounded;
      case 'mode_explanation':
        return Icons.tips_and_updates_rounded;
      case 'blocked_input_request':
        return Icons.help_outline_rounded;
      case 'planning_bottleneck_card':
        return Icons.warning_amber_rounded;
      case 'planning_strategy_card':
        return Icons.map_rounded;
      case 'planning_progress_strip':
        return Icons.linear_scale_rounded;
      case 'aurora_nudge_entry':
        return Icons.psychology_rounded;
      default:
        return Icons.touch_app_rounded;
    }
  }

  String _getTitleForAction(String type) {
    final l10n = I18nService.instance.l10n;
    switch (type) {
      case 'create_task':
        return l10n.chatActionTitleCreateTask;
      case 'task_list':
        return l10n.chatActionTitleTaskList;
      case 'create_plan':
        return l10n.chatActionTitleCreatePlan;
      case 'update_preference':
        return l10n.chatActionTitleUpdatePreference;
      case 'add_error':
        return l10n.chatActionTitleAddError;
      case 'focus_card':
        return l10n.chatActionTitleFocusSprint;
      case 'system_update':
        return l10n.chatActionTitleSystemUpdate;
      case 'nightly_review':
        return l10n.chatActionTitleNightlyReview;
      case 'execution_summary':
        return l10n.chatActionTitleExecutionSummary;
      case 'execution_suggestion':
        return 'AI 执行建议';
      case 'evolution_card':
        return l10n.chatActionTitleEvolution;
      case 'progress_card':
        return l10n.chatActionTitleProgress;
      case 'reflection_card':
        return l10n.chatActionTitleReflection;
      case 'source_summary':
        return l10n.chatActionTitleSourceSummary;
      case 'next_actions':
        return l10n.chatActionTitleNextActions;
      case 'adaptation_summary':
        return '这轮调整';
      case 'profile_front_door':
        return '当前画像前门';
      case 'continuity_banner':
        return l10n.chatActionTitleContinuity;
      case 'mode_explanation':
        return l10n.chatActionTitleModeExplanation;
      case 'blocked_input_request':
        return l10n.chatActionTitleBlockedInput;
      case 'planning_bottleneck_card':
        return '瓶颈分析';
      case 'planning_strategy_card':
        return '策略方案';
      case 'planning_progress_strip':
        return '规划流程';
      case 'aurora_nudge_entry':
        return 'Aurora 提醒';
      default:
        return l10n.chatActionTitleDefault;
    }
  }

  String _getConfirmLabel(String type) {
    final l10n = I18nService.instance.l10n;
    if (type == 'nightly_review') {
      return l10n.chatActionReviewed;
    }
    return l10n.confirm;
  }

  String _getDismissLabel(String type) {
    final l10n = I18nService.instance.l10n;
    if (type == 'nightly_review') {
      return l10n.chatActionLater;
    }
    return l10n.chatActionIgnore;
  }

  Widget _buildContentForAction(BuildContext context, WidgetPayload action) {
    if (action.type == 'nightly_review') {
      return _buildNightlyReviewContent(context, action);
    }
    if (action.type == 'task_list') {
      return _buildTaskListContent(context, action);
    }
    if (action.type == 'execution_summary') {
      return _buildExecutionSummary(context, action);
    }
    if (action.type == 'execution_suggestion') {
      return _buildExecutionSuggestion(context, action);
    }
    if (action.type == 'evolution_card') {
      return _buildEvolutionCard(context, action);
    }
    if (action.type == 'progress_card') {
      return _buildProgressCard(context, action);
    }
    if (action.type == 'source_summary') {
      return _buildSourceSummary(context, action);
    }
    if (action.type == 'next_actions') {
      return _buildNextActions(context, action);
    }
    if (action.type == 'adaptation_summary') {
      return _buildAdaptationSummary(context, action);
    }
    if (action.type == 'profile_front_door') {
      return ProfileFrontDoorCard(
        data: action.data,
        onAction: widget.onWidgetAction,
      );
    }
    if (action.type == 'graph_diagnostic') {
      return GraphDiagnosticCard(
        data: action.data,
        onAction: widget.onWidgetAction,
      );
    }
    if (action.type == 'continuity_banner' ||
        action.type == 'mode_explanation') {
      return _buildNarrativeBanner(context, action);
    }
    if (action.type == 'blocked_input_request') {
      return _buildBlockedInputRequest(context, action);
    }
    if (action.type == 'reflection_card') {
      return _buildReflectionCard(context, action);
    }
    if (action.type == 'planning_bottleneck_card') {
      return BottleneckCard(data: action.data);
    }
    if (action.type == 'planning_strategy_card') {
      return PlanStrategyCard(
        data: action.data,
        onWidgetAction: widget.onWidgetAction,
      );
    }
    if (action.type == 'planning_progress_strip') {
      return PlanProgressStrip(data: action.data);
    }
    if (action.type == 'plan_card') {
      return _buildPlanCardContent(context, action);
    }
    if (action.type == 'aurora_nudge_entry') {
      return AuroraNudgeEntry(
        data: action.data,
        onWidgetAction: widget.onWidgetAction,
      );
    }
    if (action.type == 'system_update') {
      final description = action.data['description']?.toString() ?? '';
      final category = action.data['category']?.toString() ?? '';
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (action.data['title'] != null) ...[
            Text(
              action.data['title'] as String,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.neutral900,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
          ],
          if (description.isNotEmpty)
            Text(
              description,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          if (category.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing10,
                vertical: DS.spacing6,
              ),
              decoration: BoxDecoration(
                color: DS.neutral100,
                borderRadius: DS.borderRadius8,
                border: Border.all(color: DS.neutral200),
              ),
              child: Text(
                category,
                style: TextStyle(
                  color: DS.neutral600,
                  fontSize: DS.fontSizeSm,
                ),
              ),
            ),
          ],
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_asString(action.data['title']) != null) ...[
          Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _getActionColorFor(action).withValues(alpha: 0.1),
                  _getActionColorFor(action).withValues(alpha: 0.05),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: DS.borderRadius12,
              border: Border.all(
                color: _getActionColorFor(action).withValues(alpha: 0.2),
              ),
            ),
            child: Text(
              _asString(action.data['title'])!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.neutral900,
                  ),
            ),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (_extractGenericNarrative(action) case final narrative?) ...[
          Text(
            narrative,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (_buildVisibleGenericEntries(action).isNotEmpty)
          LayoutBuilder(
            builder: (context, constraints) {
              final entries = _buildVisibleGenericEntries(action);
              final maxChipWidth =
                  constraints.maxWidth > 220 ? 220.0 : constraints.maxWidth;
              return Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: entries
                    .map(
                      (entry) => ConstrainedBox(
                        constraints: BoxConstraints(maxWidth: maxChipWidth),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing12,
                            vertical: DS.spacing8,
                          ),
                          decoration: BoxDecoration(
                            color: DS.neutral100,
                            borderRadius: DS.borderRadius8,
                            border: Border.all(color: DS.neutral200),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                _getParamIcon(entry.key),
                                size: DS.iconSizeXs,
                                color: DS.neutral600,
                              ),
                              const SizedBox(width: DS.spacing6),
                              Expanded(
                                child: RichText(
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  text: TextSpan(
                                    style: TextStyle(
                                      fontSize: DS.fontSizeSm,
                                      color: DS.neutral900,
                                    ),
                                    children: [
                                      TextSpan(
                                        text: '${_formatParamKey(entry.key)}: ',
                                        style: TextStyle(
                                          color: DS.neutral600,
                                          fontWeight: DS.fontWeightRegular,
                                        ),
                                      ),
                                      TextSpan(
                                        text: entry.value,
                                        style: TextStyle(
                                          color: DS.neutral900,
                                          fontWeight: DS.fontWeightSemibold,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                    .toList(),
              );
            },
          ),
      ],
    );
  }

  bool _isCollapsible(WidgetPayload action) =>
      _isCollapsedByDefault(_resolveActionType(action)) ||
      _shouldCollapseGenericMetadata(action);

  bool _shouldCollapseByDefault(WidgetPayload action) =>
      _isCollapsedByDefault(_resolveActionType(action)) ||
      _shouldCollapseGenericMetadata(action);

  bool _isCollapsedByDefault(String type) {
    switch (type) {
      case 'create_task':
      case 'create_plan':
      case 'plan_card':
      case 'task_list':
      case 'source_summary':
      case 'next_actions':
      case 'profile_front_door':
      case 'continuity_banner':
      case 'mode_explanation':
      case 'execution_summary':
      case 'execution_suggestion':
        return true;
      default:
        return false;
    }
  }

  Widget _buildCollapsedPreview(BuildContext context, WidgetPayload action) {
    final preview = _collapsedPreviewText(action);
    final type = _resolveActionType(action);
    final isSummaryCard = type == 'create_task' ||
        type == 'create_plan' ||
        type == 'plan_card' ||
        type == 'task_list';
    if (isSummaryCard) {
      return Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.neutral200),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing8,
          ),
          child: Row(
            children: [
              Icon(
                Icons.open_in_full_rounded,
                size: DS.iconSizeXs,
                color: DS.neutral600,
              ),
              const SizedBox(width: DS.spacing6),
              Expanded(
                child: Text(
                  preview,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.neutral700,
                        fontWeight: DS.fontWeightMedium,
                      ),
                ),
              ),
            ],
          ),
        ),
      );
    }
    if (_shouldCollapseGenericMetadata(action)) {
      return Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.info_outline_rounded,
              size: DS.iconSizeXs,
              color: DS.neutral600,
            ),
            const SizedBox(width: DS.spacing6),
            Flexible(
              child: Text(
                preview,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral700,
                      fontWeight: DS.fontWeightMedium,
                    ),
              ),
            ),
          ],
        ),
      );
    }
    return Text(
      preview,
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: DS.neutral700,
            height: 1.45,
          ),
    );
  }

  String _collapsedPreviewText(WidgetPayload action) {
    final l10n = I18nService.instance.l10n;
    switch (action.type) {
      case 'source_summary':
        return action.data['headline']?.toString() ??
            action.data['evidence_summary']?.toString() ??
            l10n.chatActionViewSources;
      case 'next_actions':
        final actions = (action.data['actions'] as List<dynamic>? ?? [])
            .whereType<Map<dynamic, dynamic>>()
            .map((item) => item['label']?.toString() ?? '')
            .where((label) => label.isNotEmpty)
            .take(2)
            .join(' · ');
        return actions.isNotEmpty
            ? l10n.chatActionSuggestedActions(actions)
            : (action.data['title']?.toString() ??
                l10n.chatActionViewNextSteps);
      case 'continuity_banner':
      case 'mode_explanation':
        return action.data['message']?.toString() ??
            action.data['description']?.toString() ??
            action.data['label']?.toString() ??
            l10n.viewDetails;
      case 'execution_summary':
      case 'execution_suggestion':
        return action.data['summary']?.toString() ??
            action.data['title']?.toString() ??
            (action.type == 'execution_suggestion'
                ? 'AI 执行建议'
                : l10n.chatActionTitleExecutionSummary);
      case 'create_task':
        return '任务';
      case 'create_plan':
      case 'plan_card':
        return '学习计划';
      case 'task_list':
        return '任务列表';
      default:
        final summary = _extractGenericNarrative(action);
        if (summary != null) {
          return summary;
        }
        final title = _asString(action.data['title']);
        if (title != null) {
          return title;
        }
        final entryPreview = _buildVisibleGenericEntries(action)
            .take(2)
            .map((entry) => '${_formatParamKey(entry.key)} ${entry.value}')
            .join(' · ');
        return entryPreview.isNotEmpty ? entryPreview : l10n.viewDetails;
    }
  }

  Future<void> _handleGenericDismiss(WidgetPayload action) async {
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
    widget.onDismiss?.call();
    if (!mounted) return;
    setState(() {
      _hiddenAfterAction = true;
      _detailsExpanded = false;
    });
  }

  Future<void> _handleGenericConfirm(WidgetPayload action) async {
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
    widget.onConfirm?.call();
    if (!mounted) return;

    final entity = EntityCardPayload.fromRaw(
      action.data,
      fallbackType: action.type,
    );
    final detailRoute = entity.detailRoute ??
        action.data['route']?.toString() ??
        (entity.entityType == 'plan' && entity.entityId != null
            ? '/plans/${entity.entityId}'
            : null) ??
        (entity.entityType == 'task' && entity.entityId != null
            ? '/tasks/${entity.entityId}'
            : null);

    setState(() {
      _hiddenAfterAction = true;
      _detailsExpanded = false;
    });

    if (detailRoute != null && detailRoute.isNotEmpty && context.mounted) {
      unawaited(context.push(detailRoute));
    }
  }

  bool _shouldCollapseGenericMetadata(WidgetPayload action) {
    if (_usesDedicatedContentLayout(_resolveActionType(action))) {
      return false;
    }
    if (_isCollapsedByDefault(_resolveActionType(action))) {
      return false;
    }

    final keys = action.data.keys.map((key) => key.toLowerCase()).toSet();
    final hasInternalMetadata = keys.any(_hiddenGenericKeys.contains);
    final visibleEntries = _buildVisibleGenericEntries(action);
    final narrative = _extractGenericNarrative(action);

    return hasInternalMetadata ||
        visibleEntries.length > 2 ||
        (narrative == null && visibleEntries.isNotEmpty);
  }

  bool _usesDedicatedContentLayout(String type) {
    switch (type) {
      case 'nightly_review':
      case 'execution_summary':
      case 'execution_suggestion':
      case 'evolution_card':
      case 'progress_card':
      case 'source_summary':
      case 'next_actions':
      case 'continuity_banner':
      case 'mode_explanation':
      case 'blocked_input_request':
      case 'reflection_card':
      case 'plan_card':
      case 'task_list':
        return true;
      default:
        return false;
    }
  }

  String? _extractGenericNarrative(WidgetPayload action) {
    for (final key in _narrativeKeys) {
      final text = _asString(action.data[key]);
      if (text != null) {
        return text;
      }
    }
    return null;
  }

  List<MapEntry<String, String>> _buildVisibleGenericEntries(
    WidgetPayload action,
  ) {
    final entries = <MapEntry<String, String>>[];
    for (final entry in action.data.entries) {
      final normalizedKey = entry.key.toLowerCase();
      if (normalizedKey == 'title' ||
          _narrativeKeys.contains(normalizedKey) ||
          _hiddenGenericKeys.contains(normalizedKey)) {
        continue;
      }
      final value = _formatDisplayValue(entry.value);
      if (value == null) {
        continue;
      }
      entries.add(MapEntry(entry.key, value));
    }
    return entries;
  }

  String? _formatDisplayValue(dynamic value) {
    if (value == null) {
      return null;
    }
    if (value is String) {
      final trimmed = value.trim();
      return trimmed.isEmpty ? null : trimmed;
    }
    if (value is num || value is bool) {
      return value.toString();
    }
    if (value is List) {
      final scalarItems = value
          .map(
            (item) => item is String || item is num || item is bool
                ? item.toString().trim()
                : '',
          )
          .where((item) => item.isNotEmpty)
          .take(3)
          .toList();
      if (scalarItems.isEmpty) {
        return null;
      }
      return scalarItems.join(' · ');
    }
    return null;
  }

  Widget _buildTaskListContent(BuildContext context, WidgetPayload action) {
    final l10n = context.l10n;
    final tasks = action.data['tasks'] as List<dynamic>? ?? [];
    if (tasks.isEmpty) return const SizedBox.shrink();
    final entity =
        EntityCardPayload.fromRaw(action.data, fallbackType: 'task_list');

    final toolResultId = entity.toolResultId ??
        action.data['tool_result_id']?.toString() ??
        action.data['id']?.toString();
    final canConfirm = toolResultId != null && toolResultId.trim().isNotEmpty;
    final planId = entity.planId ?? action.data['plan_id']?.toString();
    final planDetailRoute = entity.detailRoute ??
        (_hasStablePlanId(planId) ? '/plans/$planId' : null);
    final canOpenPlan =
        planDetailRoute != null && planDetailRoute.trim().isNotEmpty;
    final planShareId = entity.share?.resourceId ?? planId;
    final canSharePlan = canOpenPlan && (planShareId?.isNotEmpty ?? false);
    final planTitle = _asString(entity.linkedEntities['plan_title']) ??
        action.data['plan_title']?.toString() ??
        action.data['plan_name']?.toString();
    final ragQuality = action.data['rag_quality']?.toString();

    final taskItems = tasks.take(5).map((item) {
      final task = Map<String, dynamic>.from(item as Map);
      final taskEntity = EntityCardPayload.fromRaw(task, fallbackType: 'task');
      final taskId = task['id']?.toString();
      final title = task['title']?.toString() ?? l10n.taskUntitled;
      final taskModel = taskModelFromEntityPayload(task);
      final taskDetailRoute = taskEntity.detailRoute ??
          ((taskId != null && isServerTaskId(taskId))
              ? '/tasks/$taskId'
              : null);
      final canOpenTask =
          taskDetailRoute != null && taskDetailRoute.trim().isNotEmpty;
      final canShareTask = taskId != null &&
          isServerTaskId(taskId) &&
          ((taskEntity.share?.resourceId ?? taskId).isNotEmpty);

      return Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (taskModel != null)
              TaskCard(
                task: taskModel,
                compact: true,
                onTap: canOpenTask ? () => context.push(taskDetailRoute) : null,
              )
            else
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.neutral100,
                  borderRadius: DS.borderRadius12,
                  border: Border.all(color: DS.neutral200),
                ),
                child: Text(title),
              ),
            if (taskId != null)
              Padding(
                padding: const EdgeInsets.only(
                  top: DS.spacing4,
                  left: DS.spacing8,
                  right: DS.spacing8,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: SparkleButton(
                        label: '打开',
                        variant: ButtonVariant.ghost,
                        icon: const Icon(Icons.open_in_new_rounded),
                        onPressed: canOpenTask
                            ? () => unawaited(context.push(taskDetailRoute))
                            : () {},
                        disabled: !canOpenTask,
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: SparkleButton(
                        label: '分享',
                        variant: ButtonVariant.ghost,
                        icon: const Icon(Icons.share_outlined),
                        onPressed: canShareTask
                            ? () => unawaited(
                                  _shareResource(
                                    resourceType:
                                        taskEntity.share?.resourceType ??
                                            'task',
                                    resourceId:
                                        taskEntity.share?.resourceId ?? taskId,
                                    title: taskEntity.share?.title ?? title,
                                    subtitle: taskEntity.share?.subtitle ??
                                        taskModel?.guideContent,
                                  ),
                                )
                            : () {},
                        disabled: !canShareTask,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (planTitle != null || ragQuality != null) ...[
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              if (planTitle != null)
                _buildMetaChip(
                  icon: Icons.flag_outlined,
                  label: planTitle,
                ),
              if (ragQuality != null)
                _buildMetaChip(
                  icon: Icons.psychology_alt_outlined,
                  label: '规划质量: $ragQuality',
                ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
        ],
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 420),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: taskItems,
            ),
          ),
        ),
        if (tasks.length > 5)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing4),
            child: Text(
              l10n.chatTaskListMoreCount(tasks.length - 5),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral500,
                    fontStyle: FontStyle.italic,
                  ),
            ),
          ),
        if (planId != null)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing8),
            child: Row(
              children: [
                Expanded(
                  child: SparkleButton(
                    label: '查看计划',
                    variant: ButtonVariant.ghost,
                    icon: const Icon(Icons.map_outlined),
                    onPressed: canOpenPlan
                        ? () => unawaited(context.push(planDetailRoute))
                        : () {},
                    disabled: !canOpenPlan,
                  ),
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: SparkleButton(
                    label: '分享计划',
                    variant: ButtonVariant.ghost,
                    icon: const Icon(Icons.share_outlined),
                    onPressed: canSharePlan
                        ? () => unawaited(
                              _shareResource(
                                resourceType:
                                    entity.share?.resourceType ?? 'plan',
                                resourceId: entity.share?.resourceId ?? planId,
                                title: entity.share?.title ??
                                    (planTitle ?? '学习计划'),
                                subtitle:
                                    entity.share?.subtitle ?? '由 AI 生成的任务计划',
                              ),
                            )
                        : () {},
                    disabled: !canSharePlan,
                  ),
                ),
              ],
            ),
          ),
        if (canConfirm && widget.onConfirmAllTasks != null && !_confirmedTasks)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing12),
            child: SparkleButton(
              label: _confirmingTasks ? '确认中...' : '确认全部任务',
              icon: const Icon(Icons.check_circle_outline),
              onPressed: _confirmingTasks
                  ? null
                  : () => unawaited(_handleConfirmAllTasks(toolResultId)),
            ),
          ),
        if ((!canConfirm || widget.onConfirmAllTasks == null) &&
            widget.onConfirm != null)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing12),
            child: Align(
              alignment: Alignment.centerRight,
              child: CustomButton.primary(
                text: _getConfirmLabel(action.type),
                icon: Icons.check_rounded,
                onPressed: widget.onConfirm,
                size: CustomButtonSize.small,
                customGradient: _getActionGradientFor(action),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildPlanCardContent(BuildContext context, WidgetPayload action) {
    final entity = EntityCardPayload.fromRaw(action.data, fallbackType: 'plan');
    final planId = entity.entityId ??
        action.data['id']?.toString() ??
        action.data['plan_id']?.toString();
    final detailRoute = entity.detailRoute ??
        ((planId != null && planId.isNotEmpty) ? '/plans/$planId' : null);
    final planShareId = entity.share?.resourceId ?? planId;
    final canSharePlan =
        _hasStablePlanId(planId) && (planShareId?.isNotEmpty ?? false);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        PlanCard(
          data: action.data,
          onTap: detailRoute == null
              ? null
              : () {
                  unawaited(context.push(detailRoute));
                  if (planId != null && planId.isNotEmpty) {
                    widget.onPlanNavigation?.call(planId);
                  }
                },
          onShare: planId == null
              ? null
              : (canSharePlan
                  ? () => unawaited(
                        _shareResource(
                          resourceType: entity.share?.resourceType ?? 'plan',
                          resourceId: entity.share?.resourceId ?? planId,
                          title: entity.share?.title ??
                              action.data['title']?.toString() ??
                              action.data['name']?.toString() ??
                              '学习计划',
                          subtitle: entity.share?.subtitle ??
                              action.data['description']?.toString(),
                        ),
                      )
                  : null),
        ),
      ],
    );
  }

  String? _asString(dynamic value) {
    if (value == null) return null;
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }

  Widget _buildMetaChip({
    required IconData icon,
    required String label,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
        ),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 180),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: DS.iconSizeXs, color: DS.textSecondary),
              const SizedBox(width: DS.spacing4),
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: DS.fontSizeXs,
                  ),
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildNightlyReviewContent(
    BuildContext context,
    WidgetPayload action,
  ) {
    final summary = action.data['summary']?.toString() ?? '';
    final reviewDate = action.data['review_date']?.toString() ?? '';
    final rawTodos = action.data['todo_items'] as List<dynamic>? ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (reviewDate.isNotEmpty)
          Text(
            reviewDate,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                ),
          ),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral900,
                ),
          ),
        ],
        if (rawTodos.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.chatNightlyReviewTodos,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          ...rawTodos.take(5).map((item) {
            final todo = item as Map<String, dynamic>;
            final type = todo['type']?.toString() ?? 'task';
            final payload = todo['payload'] as Map<String, dynamic>? ?? {};
            final label = payload['title']?.toString() ??
                payload['error_id']?.toString() ??
                payload['subject_code']?.toString() ??
                type;
            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.check_circle_outline,
                    size: DS.iconSizeXs,
                    color: DS.neutral500,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      label,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.neutral800,
                          ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ],
    );
  }

  Widget _buildExecutionSummary(BuildContext context, WidgetPayload action) {
    final copy = ExecutionCopy.of(context);
    final l10n = context.l10n;
    final status = action.data['status']?.toString() ?? 'success';
    final impact = action.data['impact_summary']?.toString() ?? '';
    final nextAction = action.data['next_action']?.toString() ?? '';
    final affected = (action.data['affected_objects'] as List<dynamic>? ?? [])
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .toList();

    final statusColor = switch (status) {
      'failed' => DS.error,
      'degraded' => DS.info,
      'partial' => DS.warning,
      _ => DS.success,
    };
    final resultPreview = _executionSummaryPreviewData(
      action.data['result_preview'],
    );
    final replaySteps =
        (action.data['replay_steps'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();
    final qualityWarnings =
        (action.data['quality_warnings'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();
    final validationIssues =
        (action.data['validation_issues'] as List<dynamic>? ?? const [])
            .map((item) => '$item')
            .where((item) => item.isNotEmpty)
            .toList();
    final validationPassed =
        (action.data['validation_passed'] as num?)?.toInt() ?? 0;
    final validationTotal =
        (action.data['validation_total'] as num?)?.toInt() ?? 0;
    final qualityScore =
        (action.data['quality_score'] as num?)?.toDouble() ?? 0.0;
    final comparisonSummary = action.data['comparison_summary'];
    final selfVerification = _executionSummaryPreviewData(
      action.data['self_verification'],
    );
    final errorSuggestion = _executionSummaryPreviewData(
      action.data['error_suggestion'],
    );
    final manualSteps =
        (action.data['manual_steps'] as List<dynamic>? ?? const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();
    final retryAction =
        _executionSummaryPreviewData(action.data['retry_action']);
    final comparisonHeadline = comparisonSummary is Map<String, dynamic>
        ? comparisonSummary['headline']?.toString() ?? '结果对比'
        : comparisonSummary != null
            ? '结果对比'
            : null;
    final comparisonBody = comparisonSummary is Map<String, dynamic>
        ? comparisonSummary['summary']?.toString() ??
            comparisonSummary['headline']?.toString() ??
            ''
        : comparisonSummary?.toString() ?? '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        OpenClawIdentityStrip(
          label: 'OpenClaw 执行结果',
          description: '先看摘要，再按需展开回放、对比和自验证细节',
          tone: status == 'failed'
              ? OpenClawVisualTone.offline
              : status == 'partial'
                  ? OpenClawVisualTone.attention
                  : OpenClawVisualTone.connected,
        ),
        const SizedBox(height: DS.spacing12),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.12),
            borderRadius: DS.borderRadius8,
          ),
          child: Text(
            status == 'failed'
                ? l10n.chatExecutionFailed
                : status == 'degraded'
                    ? '已切到手动协作'
                    : status == 'partial'
                        ? l10n.chatExecutionPartial
                        : l10n.chatExecutionCompleted,
            style: TextStyle(
              color: statusColor,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),
        if (impact.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            impact,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                ),
          ),
        ],
        if (affected.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: affected
                .map(
                  (item) => Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing10,
                      vertical: DS.spacing6,
                    ),
                    decoration: BoxDecoration(
                      color: DS.neutral100,
                      borderRadius: DS.borderRadius8,
                    ),
                    child: Text(item),
                  ),
                )
                .toList(),
          ),
        ],
        if (resultPreview != null) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            copy.resultPreview,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius12,
            ),
            child: ExecutionResultRenderer(
              parsedOutput: resultPreview,
            ),
          ),
        ],
        if (comparisonHeadline != null && comparisonBody.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.info.withValues(alpha: 0.08),
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.info.withValues(alpha: 0.18)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  comparisonHeadline,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.info,
                      ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  comparisonBody,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.neutral800,
                        height: 1.45,
                      ),
                ),
              ],
            ),
          ),
          if (comparisonSummary is Map<String, dynamic> &&
              (comparisonSummary['highlights'] as List<dynamic>? ?? const [])
                  .isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            ...((comparisonSummary['highlights'] as List<dynamic>? ?? const [])
                .map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing4),
                child: Text(
                  '• $item',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.neutral700,
                        height: 1.45,
                      ),
                ),
              ),
            )),
          ],
        ],
        if (replaySteps.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            copy.executionReplay,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          ...replaySteps.map(
            (step) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _buildExecutionReplayStep(context, step),
            ),
          ),
        ],
        if (qualityWarnings.isNotEmpty ||
            validationIssues.isNotEmpty ||
            validationTotal > 0) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            copy.selfVerification,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              if (validationTotal > 0)
                _buildMetaChip(
                  icon: Icons.rule_rounded,
                  label: '步骤 $validationPassed/$validationTotal',
                ),
              if (qualityScore > 0)
                _buildMetaChip(
                  icon: Icons.fact_check_rounded,
                  label: '质量 ${(qualityScore * 100).round()}%',
                ),
              if (selfVerification != null &&
                  (selfVerification['score'] as num?) != null)
                _buildMetaChip(
                  icon: Icons.verified_user_rounded,
                  label:
                      '自检 ${(((selfVerification['score'] as num?) ?? 0) * 100).round()}%',
                ),
            ],
          ),
          if (selfVerification != null &&
              (selfVerification['summary']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing10),
              decoration: BoxDecoration(
                color: switch (selfVerification['verdict']) {
                  'ready' => DS.success.withValues(alpha: 0.08),
                  'needs_revision' => DS.error.withValues(alpha: 0.08),
                  _ => DS.warning.withValues(alpha: 0.08),
                },
                borderRadius: DS.borderRadius12,
              ),
              child: Text(
                selfVerification['summary'].toString(),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral800,
                      height: 1.45,
                    ),
              ),
            ),
          ],
          if (qualityWarnings.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            ...qualityWarnings.map(
              (warning) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing6),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: DS.warning.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius12,
                    border: Border.all(
                      color: DS.warning.withValues(alpha: 0.16),
                    ),
                  ),
                  child: Text(
                    warning['message']?.toString() ?? '',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral800,
                        ),
                  ),
                ),
              ),
            ),
          ],
          if (validationIssues.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            ...validationIssues.map(
              (issue) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing4),
                child: Text(
                  '• $issue',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.neutral700,
                        height: 1.45,
                      ),
                ),
              ),
            ),
          ],
          if (selfVerification != null &&
              (selfVerification['checklist'] as List<dynamic>? ?? const [])
                  .isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            ...((selfVerification['checklist'] as List<dynamic>? ?? const [])
                .whereType<Map<dynamic, dynamic>>()
                .map(Map<String, dynamic>.from)
                .map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing6),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          item['passed'] == true
                              ? Icons.check_circle_outline_rounded
                              : Icons.error_outline_rounded,
                          size: 16,
                          color: item['passed'] == true
                              ? DS.semanticSuccess
                              : DS.warning,
                        ),
                        const SizedBox(width: DS.spacing8),
                        Expanded(
                          child: Text(
                            '${item['label'] ?? '检查项'}：${item['detail'] ?? ''}',
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: DS.neutral700,
                                      height: 1.45,
                                    ),
                          ),
                        ),
                      ],
                    ),
                  ),
                )),
          ],
        ],
        if (errorSuggestion != null ||
            manualSteps.isNotEmpty ||
            retryAction != null) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            '恢复建议',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          if ((errorSuggestion?['suggestion']?.toString() ?? '').isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing10),
              decoration: BoxDecoration(
                color: DS.info.withValues(alpha: 0.08),
                borderRadius: DS.borderRadius12,
                border: Border.all(color: DS.info.withValues(alpha: 0.16)),
              ),
              child: Text(
                errorSuggestion!['suggestion'].toString(),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral800,
                      height: 1.45,
                    ),
              ),
            ),
          if (manualSteps.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            ...manualSteps.map(
              (step) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing10),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    borderRadius: DS.borderRadius12,
                    border: Border.all(color: DS.neutral200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        step['title']?.toString() ?? '手动步骤',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              fontWeight: DS.fontWeightSemibold,
                              color: DS.neutral900,
                            ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        step['description']?.toString() ?? '',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.neutral700,
                              height: 1.45,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
          if (retryAction != null &&
              (retryAction['label']?.toString() ?? '').isNotEmpty &&
              widget.onWidgetAction != null) ...[
            const SizedBox(height: DS.spacing4),
            InkWell(
              onTap: () => unawaited(
                widget.onWidgetAction!.call(
                  retryAction['type']?.toString() ?? 'prompt',
                  retryAction,
                ),
              ),
              borderRadius: DS.borderRadius20,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing12,
                  vertical: DS.spacing8,
                ),
                decoration: BoxDecoration(
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  borderRadius: DS.borderRadius20,
                  border:
                      Border.all(color: DS.primaryBase.withValues(alpha: 0.18)),
                ),
                child: Text(
                  retryAction['label'].toString(),
                  style: TextStyle(
                    color: DS.primaryBase,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
            ),
          ],
        ],
        if (nextAction.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            l10n.chatNextActionLabel(nextAction),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                ),
          ),
        ],
      ],
    );
  }

  Map<String, dynamic>? _executionSummaryPreviewData(dynamic raw) {
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    if (raw is String && raw.trim().isNotEmpty) {
      return {'text': raw.trim()};
    }
    return null;
  }

  Widget _buildExecutionReplayStep(
    BuildContext context,
    Map<String, dynamic> step,
  ) {
    final status = step['status']?.toString() ?? 'completed';
    final durationMs = (step['duration_ms'] as num?)?.toInt();
    final color = status == 'failed' ? DS.semanticError : DS.info;
    final icon = status == 'failed'
        ? Icons.error_outline_rounded
        : Icons.play_circle_outline_rounded;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step['label']?.toString() ?? '执行步骤',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.neutral900,
                      ),
                ),
                if ((step['preview']?.toString() ?? '').isNotEmpty) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    step['preview']!.toString(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral700,
                          height: 1.45,
                        ),
                  ),
                ],
              ],
            ),
          ),
          if (durationMs != null && durationMs > 0)
            Text(
              '${(durationMs / 1000).toStringAsFixed(durationMs >= 1000 ? 1 : 0)}s',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
        ],
      ),
    );
  }

  Widget _buildExecutionSuggestion(BuildContext context, WidgetPayload action) {
    final summary = action.data['summary']?.toString() ?? '';
    final executionMode = action.data['execution_mode']?.toString() ?? 'agent';
    final targetEnv = action.data['target_env']?.toString() ?? 'general';
    final delegatePreference = action.data['delegate_preference'];
    final route = action.data['route']?.toString() ?? '';
    final taskId = action.data['task_id']?.toString() ?? '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        OpenClawIdentityStrip(
          label: 'OpenClaw 委派建议',
          description: '把适合自动执行的工作交给 OpenClaw，必要时再回到任务页审核',
          tone: executionMode == 'hybrid'
              ? OpenClawVisualTone.attention
              : OpenClawVisualTone.active,
        ),
        const SizedBox(height: DS.spacing12),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing10,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: DS.primaryBase.withValues(alpha: 0.12),
            borderRadius: DS.borderRadius8,
          ),
          child: Text(
            executionMode == 'hybrid' ? '需要你审核后完成' : '可直接委派执行',
            style: TextStyle(
              color: DS.primaryBase,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                  height: 1.45,
                ),
          ),
        ],
        const SizedBox(height: DS.spacing12),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            _buildMetaChip(
              icon: Icons.memory_rounded,
              label: executionMode == 'hybrid' ? '混合执行' : '自动执行',
            ),
            _buildMetaChip(
              icon: Icons.hub_outlined,
              label: '环境 ${targetEnv.toUpperCase()}',
            ),
            if (delegatePreference != null)
              _buildMetaChip(
                icon: Icons.favorite_border_rounded,
                label:
                    '信任 ${(double.tryParse('$delegatePreference') ?? 0).toStringAsFixed(2)}',
              ),
          ],
        ),
        const SizedBox(height: DS.spacing16),
        Row(
          children: [
            Expanded(
              child: CustomButton.primary(
                text: '交给 AI 执行',
                onPressed: () => unawaited(
                  widget.onWidgetAction?.call(
                    'handoff_task',
                    {
                      ...action.data,
                      'task_id': taskId,
                      'route': route,
                    },
                  ),
                ),
                size: CustomButtonSize.small,
                customGradient: _getActionGradientFor(action),
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: CustomButton.secondary(
                text: '查看执行页',
                onPressed: () => unawaited(
                  widget.onWidgetAction?.call(
                    'open_task_execution',
                    {
                      ...action.data,
                      'task_id': taskId,
                      'route': route,
                    },
                  ),
                ),
                size: CustomButtonSize.small,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSourceSummary(BuildContext context, WidgetPayload action) {
    final l10n = context.l10n;
    final headline = action.data['headline']?.toString() ?? '';
    final focus = action.data['first_screen_focus']?.toString() ?? '';
    final confidenceBand = action.data['confidence_band']?.toString() ?? '';
    final completionState = action.data['completion_state']?.toString() ?? '';
    final whyThisAnswer = action.data['why_this_answer']?.toString() ?? '';
    final evidenceSummary = action.data['evidence_summary']?.toString() ?? '';
    final citations = (action.data['citations'] as List<dynamic>? ?? [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (headline.isNotEmpty) ...[
          Text(
            headline,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (confidenceBand.isNotEmpty || completionState.isNotEmpty) ...[
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              if (confidenceBand.isNotEmpty)
                _buildMetaPill(_mapConfidenceLabel(confidenceBand)),
              if (completionState.isNotEmpty)
                _buildMetaPill(_mapCompletionLabel(completionState)),
            ],
          ),
          const SizedBox(height: DS.spacing12),
        ],
        if (focus.isNotEmpty) ...[
          Text(
            focus,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (whyThisAnswer.isNotEmpty) ...[
          Text(
            l10n.chatWhyThisAnswer,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            whyThisAnswer,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (evidenceSummary.isNotEmpty)
          Text(
            evidenceSummary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                ),
          ),
        if (citations.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          ...citations.take(3).map((citation) {
            final title =
                citation['title']?.toString() ?? l10n.chatSourceUntitled;
            final sectionTitle = citation['section_title']?.toString() ?? '';
            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Container(
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.neutral100,
                  borderRadius: DS.borderRadius12,
                  border: Border.all(color: DS.neutral200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontWeight: DS.fontWeightSemibold,
                          ),
                    ),
                    if (sectionTitle.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing4),
                      Text(
                        sectionTitle,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.neutral600,
                            ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          }),
        ],
      ],
    );
  }

  Widget _buildNextActions(BuildContext context, WidgetPayload action) {
    final l10n = context.l10n;
    final title = action.data['title']?.toString() ?? '';
    final recoveryMessage = action.data['recovery_message']?.toString() ?? '';
    final actions = (action.data['actions'] as List<dynamic>? ?? [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final retryOptions = (action.data['retry_options'] as List<dynamic>? ?? [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final memoryUpdatesRaw = action.data['memory_updates'];
    final memoryUpdates = memoryUpdatesRaw is Map<String, dynamic>
        ? (memoryUpdatesRaw['highlights'] as List<dynamic>? ?? [])
            .map((e) => '$e')
            .toList()
        : (action.data['memory_updates'] as List<dynamic>? ?? [])
            .map((e) => '$e')
            .toList();

    Widget buildActionChip(
      Map<String, dynamic> item, {
      bool secondary = false,
    }) {
      final label = item['label']?.toString() ?? '';
      final style =
          item['style']?.toString() ?? (secondary ? 'secondary' : 'primary');
      final isPrimary = style == 'primary' && !secondary;
      final isGhost = style == 'ghost';
      final backgroundColor = isPrimary
          ? DS.primaryBase.withValues(alpha: 0.12)
          : (isGhost ? DS.surfacePrimary : DS.surfaceTertiary);
      final borderColor = isPrimary
          ? DS.primaryBase.withValues(alpha: 0.2)
          : (isGhost ? DS.neutral300 : DS.neutral200);
      final textColor = isPrimary ? DS.primaryBase : DS.neutral700;
      return InkWell(
        onTap: label.isEmpty
            ? null
            : () => unawaited(
                  widget.onWidgetAction?.call(
                    item['type']?.toString() ?? 'prompt',
                    item,
                  ),
                ),
        borderRadius: DS.borderRadius20,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: DS.borderRadius20,
            border: Border.all(color: borderColor),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: textColor,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title.isNotEmpty) ...[
          Text(
            title,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (actions.isNotEmpty)
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: actions.map(buildActionChip).toList(),
          ),
        if (recoveryMessage.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            recoveryMessage,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                ),
          ),
        ],
        if (retryOptions.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            l10n.chatNextActionsRetryHint,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: retryOptions
                .map((item) => buildActionChip(item, secondary: true))
                .toList(),
          ),
        ],
        if (memoryUpdates.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          ...memoryUpdates.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 5,
                    height: 5,
                    margin: const EdgeInsets.only(top: 7, right: 8),
                    decoration: BoxDecoration(
                      color: DS.neutral600,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      item,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.neutral600,
                          ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildEvolutionCard(BuildContext context, WidgetPayload action) {
    final l10n = context.l10n;
    final evolutionKind = action.data['evolution_kind']?.toString() ?? '';
    final headline = action.data['headline']?.toString() ??
        l10n.chatEvolutionHeadlineDefault;
    final summary = action.data['summary']?.toString() ?? '';
    final insightText = action.data['insight_text']?.toString() ?? '';
    final evidenceSummary = action.data['evidence_summary']?.toString() ?? '';
    final weeklySummary = action.data['weekly_summary']?.toString() ?? '';
    final oneKeyAdjustment =
        action.data['one_key_adjustment']?.toString() ?? '';
    final comparisonHighlight =
        action.data['comparison_highlight']?.toString() ?? '';
    final periodRange = action.data['period_range']?.toString() ?? '';
    final reasoningSummary = action.data['reasoning_summary']?.toString() ?? '';
    final alignmentSummary = action.data['alignment_summary']?.toString() ?? '';
    final alignmentScore = (action.data['alignment_score'] as num?)?.toDouble();
    final reasoningDetails =
        (action.data['reasoning_details'] as List<dynamic>? ?? [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();
    final profileHitRate =
        (action.data['profile_hit_rate'] as Map<dynamic, dynamic>? ??
                const <dynamic, dynamic>{})
            .map<String, dynamic>((key, value) => MapEntry('$key', value));
    final confidence = (action.data['confidence'] as num?)?.toDouble();
    final topLearnings = (action.data['top_learnings'] as List<dynamic>? ?? [])
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .toList();
    final comparison = (action.data['comparison'] as Map<dynamic, dynamic>? ??
            const <dynamic, dynamic>{})
        .map<String, dynamic>((key, value) => MapEntry('$key', value));
    final recommendedAction =
        (action.data['recommended_action'] as Map<dynamic, dynamic>?)
            ?.map<String, dynamic>((key, value) => MapEntry('$key', value));
    final adaptationRecords =
        (action.data['adaptation_records'] as List<dynamic>? ?? [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();
    final preferenceLearnings =
        (action.data['preference_learnings'] as List<dynamic>? ?? [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList();

    Widget buildDetailBlock(Map<String, dynamic> item) {
      final what = item['what_changed']?.toString() ?? '';
      final why = item['why']?.toString() ?? '';
      final effect = item['expected_effect']?.toString() ?? '';
      return Container(
        margin: const EdgeInsets.only(top: DS.spacing8),
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (what.isNotEmpty)
              Text(
                what,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.neutral900,
                    ),
              ),
            if (why.isNotEmpty) ...[
              const SizedBox(height: DS.spacing6),
              Text(
                l10n.chatEvolutionWhy(why),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral700,
                    ),
              ),
            ],
            if (effect.isNotEmpty) ...[
              const SizedBox(height: DS.spacing6),
              Text(
                l10n.chatEvolutionExpectedEffect(effect),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral700,
                    ),
              ),
            ],
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          headline,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: DS.fontWeightSemibold,
                color: DS.neutral900,
              ),
        ),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                ),
          ),
        ],
        if (evolutionKind == 'proactive_insight' && insightText.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            insightText,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral900,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          if (evidenceSummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              evidenceSummary,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
          if (confidence != null) ...[
            const SizedBox(height: DS.spacing8),
            _buildMetaPill(
              l10n.chatConfidenceLabel((confidence * 100).toInt()),
            ),
          ],
        ],
        if (evolutionKind == 'weekly_learning_report') ...[
          if (weeklySummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              weeklySummary,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.neutral900,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
          if (topLearnings.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            ...topLearnings.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 5,
                      height: 5,
                      margin: const EdgeInsets.only(top: 8, right: 8),
                      decoration: BoxDecoration(
                        color: Theme.of(context).brightness == Brightness.dark
                            ? DS.neutral200
                            : DS.neutral800,
                        shape: BoxShape.circle,
                      ),
                    ),
                    Expanded(child: Text(item)),
                  ],
                ),
              ),
            ),
          ],
          if (oneKeyAdjustment.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.chatEvolutionNextWeekPlan(oneKeyAdjustment),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
          if (evidenceSummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              evidenceSummary,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
          if (comparisonHighlight.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            _buildMetaPill(comparisonHighlight),
          ],
          if (profileHitRate.isNotEmpty &&
              (profileHitRate['summary']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              profileHitRate['summary'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
          if (periodRange.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              periodRange,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral500,
                  ),
            ),
          ],
        ],
        if (evolutionKind == 'progress_comparison' &&
            comparison.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            comparison['delta_text']?.toString() ?? '',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral900,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          _buildMetaPill(
            '${comparison['before_label'] ?? l10n.chatComparisonBefore}: ${comparison['before_value'] ?? '-'}',
          ),
          const SizedBox(height: DS.spacing6),
          _buildMetaPill(
            '${comparison['after_label'] ?? l10n.chatComparisonAfter}: ${comparison['after_value'] ?? '-'}',
          ),
          if ((comparison['why_it_matters']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              comparison['why_it_matters'].toString(),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
          if (evidenceSummary.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              evidenceSummary,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral700,
                  ),
            ),
          ],
        ],
        if ((evolutionKind == 'plan_reasoning' ||
                reasoningSummary.isNotEmpty) &&
            reasoningSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            reasoningSummary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral900,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        ],
        if (alignmentSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            alignmentSummary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.info,
                ),
          ),
        ],
        if (alignmentScore != null) ...[
          const SizedBox(height: DS.spacing8),
          _buildMetaPill(
            l10n.chatAlignmentScoreLabel((alignmentScore * 100).toInt()),
          ),
        ],
        if (evolutionKind == 'plan_reasoning' &&
            evidenceSummary.isNotEmpty &&
            reasoningDetails.isEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral700,
                ),
          ),
        ],
        if (reasoningDetails.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            title: Text(
              l10n.chatViewPlanRationale,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.info,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
            children: reasoningDetails
                .map(
                  (detail) => buildDetailBlock({
                    'what_changed': detail['label'],
                    'why': detail['evidence'],
                    'expected_effect': detail['impact'],
                  }),
                )
                .toList(),
          ),
        ],
        if (recommendedAction != null) ...[
          const SizedBox(height: DS.spacing12),
          CustomButton.primary(
            text: recommendedAction['label']?.toString() ?? l10n.commonContinue,
            onPressed: () => unawaited(
              widget.onWidgetAction?.call(
                recommendedAction['type']?.toString() ?? 'prompt',
                recommendedAction,
              ),
            ),
            size: CustomButtonSize.small,
            customGradient: DS.infoGradient,
          ),
        ],
        if (adaptationRecords.isNotEmpty || preferenceLearnings.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            title: Text(
              l10n.commonLearnMore,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.info,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
            children: [
              ...adaptationRecords.map(buildDetailBlock),
              ...preferenceLearnings.map(buildDetailBlock),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildProgressCard(BuildContext context, WidgetPayload action) {
    final l10n = context.l10n;
    final highlights = (action.data['highlights'] as List<dynamic>? ?? [])
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .toList();
    final streakInfo = (action.data['streak_info'] as Map<dynamic, dynamic>? ??
            const <dynamic, dynamic>{})
        .map<String, dynamic>((key, value) => MapEntry('$key', value));
    final comparisons = (action.data['comparisons'] as Map<dynamic, dynamic>? ??
            const <dynamic, dynamic>{})
        .map<String, dynamic>((key, value) => MapEntry('$key', value));
    final currentStreak = (streakInfo['current_streak'] as num?)?.toInt() ?? 0;
    final maxStreak = (streakInfo['max_streak'] as num?)?.toInt() ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (highlights.isNotEmpty)
          ...highlights.take(3).map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        margin: const EdgeInsets.only(top: 8, right: 8),
                        decoration: BoxDecoration(
                          color: DS.neutral900,
                          shape: BoxShape.circle,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          item,
                          style:
                              Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: DS.neutral900,
                                    fontWeight: DS.fontWeightSemibold,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        if (currentStreak != 0) ...[
          const SizedBox(height: DS.spacing8),
          _buildMetaPill(
            l10n.chatStreakSummary(
              currentStreak,
              maxStreak,
            ),
          ),
        ],
        if (comparisons.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            title: Text(
              l10n.chatViewComparisonData,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.success,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
            children: comparisons.entries.map((entry) {
              final value = entry.value is Map<dynamic, dynamic>
                  ? Map<String, dynamic>.from(
                      entry.value as Map<dynamic, dynamic>,
                    )
                  : const <String, dynamic>{};
              final currentValue = value['current']?.toString() ?? '-';
              final previousValue = value['previous']?.toString() ?? '-';
              return Container(
                margin: const EdgeInsets.only(top: DS.spacing8),
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.neutral100,
                  borderRadius: DS.borderRadius12,
                  border: Border.all(color: DS.neutral200),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(_formatParamKey(entry.key)),
                    Text(
                      l10n.chatComparisonCurrentPrevious(
                        currentValue,
                        previousValue,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildReflectionCard(BuildContext context, WidgetPayload action) {
    final question = action.data['question']?.toString() ?? '';
    final feedbackId = action.data['feedback_id']?.toString() ?? '';
    final options = (action.data['options'] as List<dynamic>? ?? [])
        .map((e) => '$e')
        .where((e) => e.isNotEmpty)
        .toList();
    final initialStatus = action.data['status']?.toString() ?? '';
    final submitted = _reflectionSubmitted || initialStatus == 'completed';

    if (submitted) {
      return Text(
        context.l10n.chatFeedbackThanks,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: DS.neutral700,
            ),
      );
    }

    Future<void> submit() async {
      if (feedbackId.isEmpty) {
        return;
      }
      await widget.onWidgetAction?.call(
        'reflection_submit',
        {
          'feedback_id': feedbackId,
          'selected_option': _selectedReflectionOption,
          'free_text': _reflectionController.text.trim(),
        },
      );
      if (mounted) {
        setState(() {
          _reflectionSubmitted = true;
        });
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (question.isNotEmpty)
          Text(
            question,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral900,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        if (options.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: options
                .map(
                  (option) => ChoiceChip(
                    label: Text(option),
                    selected: _selectedReflectionOption == option,
                    onSelected: (_) {
                      setState(() {
                        _selectedReflectionOption = option;
                      });
                    },
                  ),
                )
                .toList(),
          ),
        ],
        const SizedBox(height: DS.spacing12),
        TextField(
          controller: _reflectionController,
          minLines: 1,
          maxLines: 3,
          decoration: InputDecoration(
            hintText: context.l10n.chatOptionalNotesHint,
            border: const OutlineInputBorder(),
            isDense: true,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Align(
          alignment: Alignment.centerRight,
          child: CustomButton.primary(
            text: context.l10n.chatSubmitFeedback,
            onPressed: submit,
            size: CustomButtonSize.small,
            customGradient: DS.warningGradient,
          ),
        ),
      ],
    );
  }

  Widget _buildAdaptationSummary(BuildContext context, WidgetPayload action) {
    final title = action.data['title']?.toString() ?? '我刚做了一个调整';
    final summary = action.data['summary']?.toString() ?? '';
    final reversibility = action.data['reversibility_note']?.toString() ?? '';
    final evidence = action.data['evidence_summary']?.toString() ?? '';
    final followUp = action.data['follow_up_question']?.toString() ?? '';
    final whatChanged = (action.data['what_changed'] as List<dynamic>? ?? [])
        .map((item) => '$item'.trim())
        .where((item) => item.isNotEmpty)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: DS.fontWeightSemibold,
                color: DS.neutral900,
              ),
        ),
        if (summary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            summary,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                  height: 1.4,
                ),
          ),
        ],
        if (whatChanged.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: whatChanged
                .map(
                  (item) => Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing10,
                      vertical: DS.spacing6,
                    ),
                    decoration: BoxDecoration(
                      color: DS.info.withValues(alpha: 0.08),
                      borderRadius: DS.borderRadiusFull,
                      border: Border.all(
                        color: DS.info.withValues(alpha: 0.18),
                      ),
                    ),
                    child: Text(
                      item,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.neutral800,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
        if (evidence.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            evidence,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral700,
                  height: 1.4,
                ),
          ),
        ],
        if (reversibility.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            reversibility,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral600,
                  height: 1.4,
                ),
          ),
        ],
        if (followUp.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceOverlay,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Text(
              followUp,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral800,
                    fontWeight: DS.fontWeightSemibold,
                    height: 1.4,
                  ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildNarrativeBanner(BuildContext context, WidgetPayload action) {
    final title = action.data['title']?.toString() ??
        action.data['label']?.toString() ??
        '';
    final body = action.data['message']?.toString() ??
        action.data['description']?.toString() ??
        '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title.isNotEmpty)
          Text(
            title,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
        if (body.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            body,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral700,
                ),
          ),
        ],
      ],
    );
  }

  Widget _buildBlockedInputRequest(BuildContext context, WidgetPayload action) {
    final title = action.data['title']?.toString() ?? '';
    final reason = action.data['reason']?.toString() ?? '';
    final recoveryMessage = action.data['recovery_message']?.toString() ?? '';
    final retryOptions = (action.data['retry_options'] as List<dynamic>? ?? [])
        .map(
          (e) => e is Map
              ? Map<String, dynamic>.from(e)
              : {
                  'label': '$e',
                  'type': 'prompt',
                  'payload': {'prompt': '$e'},
                },
        )
        .where((e) => (e['label']?.toString() ?? '').isNotEmpty)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title.isNotEmpty) ...[
          Text(
            title,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (recoveryMessage.isNotEmpty) ...[
          Text(
            recoveryMessage,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                ),
          ),
          const SizedBox(height: DS.spacing8),
        ],
        if (reason.isNotEmpty)
          Text(
            reason,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.neutral800,
                ),
          ),
        if (retryOptions.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: retryOptions.map(
              (item) {
                final nestedPayload = item['payload'];
                final actionPayload = nestedPayload is Map
                    ? <String, dynamic>{
                        ...Map<String, dynamic>.from(nestedPayload),
                        'label': item['label'],
                        'type': item['type'],
                      }
                    : item;

                return InkWell(
                  onTap: () => unawaited(
                    widget.onWidgetAction?.call(
                      item['type']?.toString() ?? 'prompt',
                      actionPayload,
                    ),
                  ),
                  borderRadius: DS.borderRadius20,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing12,
                      vertical: DS.spacing8,
                    ),
                    decoration: BoxDecoration(
                      color: DS.surfaceTertiary,
                      borderRadius: DS.borderRadius20,
                      border: Border.all(color: DS.neutral200),
                    ),
                    child: Text(
                      item['label']?.toString() ?? '',
                      style: TextStyle(
                        color: DS.neutral700,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ),
                );
              },
            ).toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildMetaPill(String label) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.neutral200),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: DS.neutral700,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );

  String _mapConfidenceLabel(String band) {
    final l10n = I18nService.instance.l10n;
    switch (band) {
      case 'high':
        return l10n.chatConfidenceHigh;
      case 'cautious':
        return l10n.chatConfidenceCautious;
      default:
        return l10n.chatConfidenceMedium;
    }
  }

  String _mapCompletionLabel(String state) {
    final l10n = I18nService.instance.l10n;
    switch (state) {
      case 'done':
        return l10n.chatCompletionDone;
      case 'partial':
        return l10n.chatCompletionPartial;
      case 'needs_input':
        return l10n.chatCompletionNeedsInput;
      case 'blocked':
        return l10n.chatCompletionBlocked;
      default:
        return l10n.chatCompletionProcessing;
    }
  }

  void _handleFocusCardAction(BuildContext context, WidgetPayload action) {
    final taskData = action.data['task'] as Map<String, dynamic>?;

    // 构建任务 ID 或使用默认的快速专注 ID
    final taskId = taskData?['id']?.toString() ??
        'focus_${DateTime.now().millisecondsSinceEpoch}';

    // 导航到正念模式（番茄钟）
    unawaited(context.push('/focus/mindfulness/$taskId'));
  }

  IconData _getParamIcon(String key) {
    switch (key.toLowerCase()) {
      case 'type':
      case 'task_type':
        return Icons.category_rounded;
      case 'difficulty':
        return Icons.stars_rounded;
      case 'estimated_minutes':
      case 'duration':
        return Icons.timer_rounded;
      case 'subject':
        return Icons.book_rounded;
      case 'due_date':
      case 'target_date':
        return Icons.calendar_today_rounded;
      default:
        return Icons.label_rounded;
    }
  }

  String _formatParamKey(String key) => key
      .split('_')
      .map((word) => word[0].toUpperCase() + word.substring(1))
      .join(' ');
}
