import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/focus_action_card.dart';

class ActionCard extends StatefulWidget {
  const ActionCard({
    required this.action,
    super.key,
    this.onConfirm,
    this.onDismiss,
  });
  final WidgetPayload action;
  final VoidCallback? onConfirm;
  final VoidCallback? onDismiss;

  @override
  State<ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<ActionCard> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _iconScaleAnimation;
  late AnimationController _pressController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _iconScaleAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _pressController = AnimationController(
      vsync: this,
      duration: SparkleMotion.fast,
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _pressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
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

    final hasAction = widget.onConfirm != null || widget.onDismiss != null;
    final confirmLabel = _getConfirmLabel(widget.action.type);
    final dismissLabel = _getDismissLabel(widget.action.type);

    return GestureDetector(
      onTapDown: hasAction ? (_) => _pressController.forward() : null,
      onTapUp: hasAction ? (_) => _pressController.reverse() : null,
      onTapCancel: hasAction ? () => _pressController.reverse() : null,
      onTap: hasAction ? HapticFeedback.selectionClick : null,
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
                              Colors.transparent,
                              DS.brandPrimary.withValues(alpha: 0.1),
                              Colors.transparent,
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
                      _buildContentForAction(context, widget.action),
                      if (hasAction) ...[
                        const SizedBox(height: DS.spacing16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            if (widget.onDismiss != null)
                              CustomButton.text(
                                text: dismissLabel,
                                onPressed: widget.onDismiss,
                                size: CustomButtonSize.small,
                              ),
                            const SizedBox(width: DS.spacing8),
                            if (widget.onConfirm != null)
                              CustomButton.primary(
                                text: confirmLabel,
                                icon: Icons.check_rounded,
                                onPressed: widget.onConfirm,
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

  LinearGradient _getActionGradientFor(WidgetPayload action) => _getActionGradient(_resolveActionType(action));

  Color _getActionColorFor(WidgetPayload action) => _getActionColor(_resolveActionType(action));

  IconData _getActionIconFor(WidgetPayload action) => _getActionIcon(_resolveActionType(action));

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
      default:
        return Icons.touch_app_rounded;
    }
  }

  String _getTitleForAction(String type) {
    switch (type) {
      case 'create_task':
        return 'AI建议：创建任务';
      case 'task_list':
        return 'AI任务拆解';
      case 'create_plan':
        return 'AI建议：创建计划';
      case 'update_preference':
        return 'AI建议：更新偏好';
      case 'add_error':
        return 'AI建议：记录错题';
      case 'focus_card':
        return 'AI建议：专注冲刺';
      case 'system_update':
        return '系统更新';
      case 'nightly_review':
        return '夜间复盘';
      default:
        return 'AI建议操作';
    }
  }

  String _getConfirmLabel(String type) {
    if (type == 'nightly_review') {
      return '已复盘';
    }
    return '确认';
  }

  String _getDismissLabel(String type) {
    if (type == 'nightly_review') {
      return '稍后';
    }
    return '忽略';
  }

  Widget _buildContentForAction(BuildContext context, WidgetPayload action) {
    if (action.type == 'nightly_review') {
      return _buildNightlyReviewContent(context, action);
    }
    if (action.type == 'task_list') {
      return _buildTaskListContent(context, action);
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
          if (action.data['title'] != null) ...[
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
                action.data['title'] as String,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.neutral900,
                    ),
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          if (action.data.entries.where((e) => e.key != 'title').isNotEmpty)
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: action.data.entries
                  .where((e) => e.key != 'title')
                  .map(
                    (entry) => Container(
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
                          const SizedBox(width: DS.spacing4),
                          Text(
                            '${_formatParamKey(entry.key)}: ',
                            style: TextStyle(
                              color: DS.neutral600,
                              fontSize: DS.fontSizeSm,
                            ),
                          ),
                          Text(
                            entry.value.toString(),
                            style: TextStyle(
                              fontWeight: DS.fontWeightSemibold,
                              fontSize: DS.fontSizeSm,
                              color: DS.neutral900,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
        ],
      );
  }

  Widget _buildTaskListContent(BuildContext context, WidgetPayload action) {
    final tasks = action.data['tasks'] as List<dynamic>? ?? [];
    if (tasks.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ...tasks.take(5).map((item) {
          final task = item as Map<String, dynamic>;
          final title = task['title']?.toString() ?? '未命名任务';
          final minutes = task['estimated_minutes']?.toString() ?? '30';
          
          return Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.neutral100,
                borderRadius: DS.borderRadius12,
                border: Border.all(color: DS.neutral200),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.spacing4),
                    decoration: BoxDecoration(
                      color: DS.primaryBase.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.check_rounded,
                      size: 16,
                      color: DS.primaryBase,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                fontWeight: DS.fontWeightSemibold,
                                color: DS.neutral900,
                              ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '$minutes 分钟',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: DS.neutral600,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
        if (tasks.length > 5)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing4),
            child: Text(
              '以及其他 ${tasks.length - 5} 个任务...',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral500,
                    fontStyle: FontStyle.italic,
                  ),
            ),
          ),
      ],
    );
  }

  Widget _buildNightlyReviewContent(BuildContext context, WidgetPayload action) {
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
            '明日待办',
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
                  Icon(Icons.check_circle_outline,
                      size: DS.iconSizeXs, color: DS.neutral500,),
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

  void _handleFocusCardAction(BuildContext context, WidgetPayload action) {
    final taskData = action.data['task'] as Map<String, dynamic>?;

    // 构建任务 ID 或使用默认的快速专注 ID
    final taskId = taskData?['id']?.toString() ?? 'focus_${DateTime.now().millisecondsSinceEpoch}';

    // 导航到正念模式（番茄钟）
    context.push('/focus/mindfulness/$taskId');
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

  String _formatParamKey(String key) {
    // Convert snake_case to readable format
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}
