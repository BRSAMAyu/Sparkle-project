import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

class TaskFeedbackDialog extends ConsumerStatefulWidget {
  const TaskFeedbackDialog({
    required this.result,
    required this.taskId,
    required this.onClose,
    super.key,
  });

  final TaskCompletionResult result;
  final String taskId;
  final VoidCallback onClose;

  @override
  ConsumerState<TaskFeedbackDialog> createState() =>
      _TaskFeedbackDialogState();
}

class _TaskFeedbackDialogState extends ConsumerState<TaskFeedbackDialog> {
  int? _rating;
  final _feedbackController = TextEditingController();
  bool _hasRecordedSkip = false;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _feedbackController.dispose();
    // Track skip if user hasn't interacted with any next action
    _recordSkipIfNeeded();
    super.dispose();
  }

  void _recordSkipIfNeeded() {
    if (!_hasRecordedSkip && widget.result.nextActions.isNotEmpty) {
      ref.read(taskListProvider.notifier).recordNextActionsSkip(
            widget.taskId,
            widget.result.nextActions,
          );
    }
  }

  Future<void> _handleSubmit() async {
    if (_isSubmitting) return;

    setState(() => _isSubmitting = true);

    TaskFeedbackResponse? response;
    if (_rating != null || _feedbackController.text.trim().isNotEmpty) {
      response = await ref.read(taskListProvider.notifier).submitTaskFeedbackWithResponse(
            widget.taskId,
            TaskFeedbackSubmission(
              completionQuality: _rating,
              feedbackText: _feedbackController.text.trim().isEmpty
                  ? null
                  : _feedbackController.text.trim(),
            ),
          );
    }

    setState(() => _isSubmitting = false);

    // Show success message
    if (mounted) {
      _showFeedbackSuccess(response);
    }
    widget.onClose();
  }

  void _showFeedbackSuccess(TaskFeedbackResponse? response) {
    if (!mounted) return;

    final message = response?.message ?? '反馈已提交';
    final hasPreferenceUpdates = response?.preferenceUpdates != null;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(Icons.check_circle, color: DS.semanticSuccess),
            const SizedBox(width: DS.spacing12),
            Text(message),
            if (hasPreferenceUpdates) ...[
              const SizedBox(width: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: 2),
                decoration: BoxDecoration(
                  color: DS.semanticSuccess.withValues(alpha: 0.2),
                  borderRadius: DS.borderRadius4,
                ),
                child: Text(
                  '偏好已更新',
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.semanticSuccess,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ],
        ),
        backgroundColor: DS.neutral800,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 3),
        action: response?.preferenceUpdates != null
            ? SnackBarAction(
                label: '查看',
                textColor: DS.semanticSuccess,
                onPressed: () {
                  _showPreferenceDetailDialog(response!.preferenceUpdates!);
                },
              )
            : null,
      ),
    );
  }

  void _showPreferenceDetailDialog(PreferenceUpdates updates) {
    if (!mounted) return;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('偏好更新'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (updates.depthPreference != null) ...[
              Text('深度偏好: ${_formatDelta(updates.depthPreference)}'),
              const SizedBox(height: DS.sm),
            ],
            if (updates.difficultyPreference != null) ...[
              Text('难度偏好: ${_formatDelta(updates.difficultyPreference)}'),
            ],
            const SizedBox(height: DS.spacing16),
            Text(
              '这些偏好将用于个性化推荐你的下一步学习内容。',
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  String _formatDelta(double? delta) {
    if (delta == null) return '-';
    final sign = delta >= 0 ? '+' : '';
    return '$sign${delta.toStringAsFixed(2)}';
  }

  void _handleNextAction(NextAction action, int position) {
    // Mark that user interacted with an action (don't record skip)
    _hasRecordedSkip = true;

    // Record the selection with displayedActionsCount
    ref.read(taskListProvider.notifier).recordNextActionSelection(
          widget.taskId,
          action,
          position,
          true,
          widget.result.nextActions.length,
        );

    widget.onClose();
    if (action.existingTaskId != null) {
      context.go('/tasks/${action.existingTaskId}/execute');
    } else if (action.quickCreateParams != null &&
        action.canQuickCreate) {
      final title = action.quickCreateParams!['title'] as String?;
      context.go(
        '/tasks/create',
        extra: {'title': title ?? action.title},
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Dialog(
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      backgroundColor: DS.brandPrimary,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 600),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      gradient: DS.primaryGradient,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.auto_awesome,
                        color: Colors.white, size: 24,),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    '任务完成!',
                    style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing20),

              // Scrollable content
              Flexible(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // AI Feedback Content
                      if (widget.result.feedback != null)
                        Container(
                          constraints: const BoxConstraints(maxHeight: 200),
                          child: SingleChildScrollView(
                            child: MarkdownBody(
                              data: widget.result.feedback!,
                              styleSheet: MarkdownStyleSheet(
                                p: theme.textTheme.bodyMedium?.copyWith(
                                      fontSize: DS.fontSizeBase,
                                      height: 1.5,
                                    ),
                                strong: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: DS.primaryDark,),
                              ),
                            ),
                          ),
                        )
                      else
                        Text('任务已完成！继续保持。', style: theme.textTheme.bodyMedium),

                      const SizedBox(height: DS.spacing20),

                      // Stats Updates
                      if (widget.result.flameUpdate != null ||
                          widget.result.statsUpdate != null)
                        Container(
                          padding: const EdgeInsets.all(DS.spacing12),
                          decoration: BoxDecoration(
                            color: DS.neutral50,
                            borderRadius: DS.borderRadius12,
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceAround,
                            children: [
                              if (widget.result.flameUpdate != null)
                                _StatItem(
                                  icon: Icons.local_fire_department,
                                  color: DS.brandPrimaryConst,
                                  value:
                                      "+${widget.result.flameUpdate!['brightness_change'] ?? widget.result.flameUpdate!['level']}%",
                                  label: '亮度',
                                ),
                              if (widget.result.statsUpdate != null)
                                _StatItem(
                                  icon: Icons.emoji_events,
                                  color: Colors.amber,
                                  value: "${widget.result.statsUpdate!['streak_days']}天",
                                  label: '连胜',
                                ),
                            ],
                          ),
                        ),

                      const SizedBox(height: DS.spacing20),

                      // Satisfaction Rating (Optional)
                      Text(
                        '满意度评分 (选填)',
                        style: theme.textTheme.labelMedium?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                      const SizedBox(height: DS.xs),
                      _StarRating(
                        rating: _rating,
                        onRatingChanged: (rating) => setState(() => _rating = rating),
                      ),

                      const SizedBox(height: DS.spacing16),

                      // Text Feedback (Optional)
                      Text(
                        '有什么想说的? (选填)',
                        style: theme.textTheme.labelMedium?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                      const SizedBox(height: DS.xs),
                      TextField(
                        controller: _feedbackController,
                        maxLines: 3,
                        decoration: InputDecoration(
                          hintText: '记录一些心得...',
                          border: OutlineInputBorder(
                            borderRadius: DS.borderRadius8,
                            borderSide:
                                BorderSide(color: DS.neutral300),
                          ),
                          filled: true,
                          fillColor: DS.neutral50,
                          contentPadding: const EdgeInsets.all(DS.spacing12),
                        ),
                      ),

                      // Next Actions Section
                      if (widget.result.nextActions.isNotEmpty) ...[
                        const SizedBox(height: DS.spacing20),
                        Row(
                          children: [
                            Icon(Icons.arrow_forward,
                                size: 18, color: DS.brandPrimaryConst,),
                            const SizedBox(width: DS.xs),
                            Text(
                              '下一步建议',
                              style: theme.textTheme.titleSmall?.copyWith(
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.sm),
                        ...widget.result.nextActions.asMap().entries.map((entry) => _NextActionCard(
                              action: entry.value,
                              position: entry.key,
                              onTap: () => _handleNextAction(entry.value, entry.key),
                            ),),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: DS.spacing24),

              // Bottom Buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: widget.onClose,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: DS.textOnPrimary,
                        side: BorderSide(color: DS.neutral400),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: const Text('跳过'),
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    flex: 2,
                    child: CustomButton.primary(
                      text: '完成',
                      onPressed: _handleSubmit,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StarRating extends StatelessWidget {
  const _StarRating({
    required this.rating,
    required this.onRatingChanged,
  });

  final int? rating;
  final ValueChanged<int> onRatingChanged;

  @override
  Widget build(BuildContext context) => Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(5, (index) {
        final starValue = index + 1;
        return IconButton(
          iconSize: 36,
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(minWidth: 40, minHeight: 40),
          icon: Icon(
            rating != null && starValue <= rating!
                ? Icons.star
                : Icons.star_border,
            color: Colors.amber,
          ),
          onPressed: () => onRatingChanged(starValue),
        );
      }),
    );
}

class _NextActionCard extends StatelessWidget {
  const _NextActionCard({
    required this.action,
    required this.onTap,
    this.position = 0,
  });

  final NextAction action;
  final VoidCallback onTap;
  final int position;

  IconData _getTypeIcon(NextActionType type) {
    switch (type) {
      case NextActionType.quickReview:
        return Icons.replay;
      case NextActionType.lightExpand:
        return Icons.explore;
      case NextActionType.practiceApply:
        return Icons.build;
      case NextActionType.restBreak:
        return Icons.self_improvement;
      case NextActionType.continuePlan:
        return Icons.play_arrow;
    }
  }

  Color _getTypeColor(NextActionType type) {
    switch (type) {
      case NextActionType.quickReview:
        return DS.info;
      case NextActionType.lightExpand:
        return DS.prismPurple;
      case NextActionType.practiceApply:
        return DS.success;
      case NextActionType.restBreak:
        return DS.neutral500;
      case NextActionType.continuePlan:
        return DS.brandPrimaryConst;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final typeColor = _getTypeColor(action.type);

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: InkWell(
        onTap: onTap,
        borderRadius: DS.borderRadius12,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: typeColor.withValues(alpha: 0.1),
            borderRadius: DS.borderRadius12,
            border: Border.all(
              color: typeColor.withValues(alpha: 0.3),
            ),
          ),
          child: Row(
            children: [
              // Type icon
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: typeColor,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _getTypeIcon(action.type),
                  color: Colors.white,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.spacing12),

              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title and estimated time
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            action.title,
                            style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: DS.xs,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: typeColor.withValues(alpha: 0.2),
                            borderRadius: DS.borderRadius4,
                          ),
                          child: Text(
                            '${action.estimatedMinutes}m',
                            style: theme.textTheme.labelSmall?.copyWith(
                                  color: typeColor,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                        ),
                      ],
                    ),
                    if (action.description.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        action.description,
                        style: theme.textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (action.reason.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        '理由: ${action.reason}',
                        style: theme.textTheme.labelSmall?.copyWith(
                              color: DS.textTertiary,
                              fontSize: 10,
                            ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),

              // Energy cost indicator
              if (action.energyCost > 0) ...[
                const SizedBox(width: DS.xs),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(
                    action.energyCost.clamp(1, 5),
                    (index) => Icon(
                      Icons.bolt,
                      size: 14,
                      color: DS.warning.withValues(
                        alpha: 0.4 + (index * 0.15),
                      ),
                    ),
                  ),
                ),
              ],

              // Arrow
              const SizedBox(width: DS.xs),
              Icon(Icons.chevron_right, color: typeColor, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Icon(icon, color: color),
          const SizedBox(height: DS.xs),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          Text(
            label,
            style: TextStyle(color: DS.neutral500, fontSize: 12),
          ),
        ],
      );
}
