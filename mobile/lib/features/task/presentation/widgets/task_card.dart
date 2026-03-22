import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/components/atoms/task_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/utils/theme_utils.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/subtask_list_widget.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskCard extends ConsumerStatefulWidget {
  const TaskCard({
    required this.task,
    super.key,
    this.onTap,
    this.onStart,
    this.onComplete,
    this.compact = false,
    this.enableSwipeComplete = false,
  });
  final TaskModel task;
  final VoidCallback? onTap;
  final VoidCallback? onStart;
  final VoidCallback? onComplete;
  final bool compact;
  final bool enableSwipeComplete;

  @override
  ConsumerState<TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends ConsumerState<TaskCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  SparkleThemeExtension? _sparkleTheme(BuildContext context) =>
      Theme.of(context).extension<SparkleThemeExtension>();

  BorderRadius _radius(BuildContext context) =>
      _sparkleTheme(context)?.radius.mdRadius ?? BorderRadius.circular(16);

  List<BoxShadow> _shadows(BuildContext context) => DS.shadowMd;

  double _spacingMd(BuildContext context) =>
      _sparkleTheme(context)?.spacing.md ?? DS.spacing16;

  Color _surfaceSecondary(BuildContext context) =>
      _sparkleTheme(context)?.colors.surfaceSecondary ??
      Theme.of(context).colorScheme.surfaceContainerHighest;

  Color _textPrimary(BuildContext context) =>
      _sparkleTheme(context)?.colors.textPrimary ??
      Theme.of(context).colorScheme.onSurface;

  Color _textDisabled(BuildContext context) => DS.textDisabled;

  Color _success(BuildContext context) =>
      _sparkleTheme(context)?.colors.semanticSuccess ?? Colors.green;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.98).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  LinearGradient _getTypeGradient(BuildContext context, TaskType type) =>
      context.sparkleColors.getTaskGradient(type.name);

  LinearGradient _getBackgroundGradient(BuildContext context, TaskType type) {
    final taskColor = context.sparkleColors.getTaskColor(type.name);
    return LinearGradient(
      colors: [
        taskColor.withValues(alpha: 0.035),
        _surfaceSecondary(context),
      ],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }

  @override
  Widget build(BuildContext context) {
    final card = Semantics(
        label: 'Task card for ${widget.task.title}',
        hint: 'Double tap to view details',
        button: true,
        enabled: true,
        child: Hero(
          tag: 'task-${widget.task.id}',
          child: Material(
            type: MaterialType.transparency,
            child: GestureDetector(
              onTapDown: (_) {
                unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.tap));
                if (mounted) unawaited(_controller.forward());
              },
              onTapUp: (_) {
                if (mounted) unawaited(_controller.reverse());
              },
              onTapCancel: () {
                if (mounted) unawaited(_controller.reverse());
              },
              onTap: widget.onTap,
              child: RepaintBoundary(
                child: AnimatedBuilder(
                  animation: _scaleAnimation,
                  builder: (context, child) => Transform.scale(
                    scale: _scaleAnimation.value,
                    child: child,
                  ),
                  child: Container(
                    margin:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                    decoration: BoxDecoration(
                      gradient:
                          _getBackgroundGradient(context, widget.task.type),
                      borderRadius: _radius(context),
                      border: Border.all(
                        color: context.sparkleColors
                            .getTaskColor(
                              widget.task.type.name,
                            )
                            .withValues(alpha: 0.12),
                      ),
                      boxShadow: [
                        for (final shadow in _shadows(context))
                          BoxShadow(
                            color: shadow.color.withValues(alpha: 0.08),
                            blurRadius: shadow.blurRadius + 4,
                            offset: const Offset(0, 8),
                          ),
                      ],
                    ),
                    foregroundDecoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.white.withValues(alpha: 0),
                          Colors.white.withValues(alpha: 0.05),
                          context.sparkleColors.brandPrimary
                              .withValues(alpha: 0),
                        ],
                        stops: const [0.0, 0.5, 1.0],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: _radius(context),
                    ),
                    child: ClipRRect(
                      borderRadius: _radius(context),
                      child: Stack(
                        children: [
                          IntrinsicHeight(
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // Colored stripe
                                Container(
                                  width: 4,
                                  decoration: BoxDecoration(
                                    gradient: _getTypeGradient(
                                      context,
                                      widget.task.type,
                                    ),
                                  ),
                                ),
                                // Content
                                Expanded(
                                  child: Padding(
                                    padding:
                                        EdgeInsets.all(_spacingMd(context)),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Expanded(
                                              child: Text(
                                                widget.task.title,
                                                style: Theme.of(context)
                                                    .textTheme
                                                    .titleMedium
                                                    ?.copyWith(
                                                      fontWeight:
                                                          FontWeight.bold,
                                                      decoration:
                                                          widget.task.status ==
                                                                  TaskStatus
                                                                      .completed
                                                              ? TextDecoration
                                                                  .lineThrough
                                                              : null,
                                                      color:
                                                          widget.task.status ==
                                                                  TaskStatus
                                                                      .completed
                                                              ? _textDisabled(
                                                                  context,
                                                                )
                                                              : _textPrimary(
                                                                  context,
                                                                ),
                                                    ),
                                                maxLines: 2,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                            if (!widget.compact) ...[
                                              const SizedBox(width: 8),
                                              TaskPill(
                                                type: widget.task.type,
                                                label: _typeLabel(
                                                  widget.task.type,
                                                ),
                                                tone:
                                                    _typeTone(widget.task.type),
                                              ),
                                              if (widget.task.status ==
                                                  TaskStatus.completed) ...[
                                                const SizedBox(width: 4),
                                                Icon(
                                                  Icons.check_circle,
                                                  color: _success(context),
                                                  size: 16,
                                                ),
                                              ] else if (widget.task.status !=
                                                  TaskStatus.pending) ...[
                                                const SizedBox(width: 4),
                                                TaskPill(
                                                  type: widget.task.type,
                                                  label:
                                                      toBeginningOfSentenceCase(
                                                    widget.task.status.name,
                                                  )!,
                                                  tone: _statusTone(
                                                    widget.task.status,
                                                  ),
                                                ),
                                              ],
                                            ],
                                          ],
                                        ),
                                        const SizedBox(height: 8),
                                        Row(
                                          children: [
                                            if (widget.task.dueDate !=
                                                null) ...[
                                              Icon(
                                                Icons.calendar_today,
                                                size: 14,
                                                color: context.sparkleColors
                                                    .textSecondary,
                                              ),
                                              const SizedBox(width: 4),
                                              Text(
                                                DateFormat.yMd().format(
                                                  widget.task.dueDate!,
                                                ),
                                                style: TextStyle(
                                                  color: context.sparkleColors
                                                      .textSecondary,
                                                  fontSize: 12,
                                                ),
                                              ),
                                              const SizedBox(width: 12),
                                            ],
                                            Icon(
                                              Icons.timer_outlined,
                                              size: 14,
                                              color: context
                                                  .sparkleColors.textSecondary,
                                            ),
                                            const SizedBox(width: 4),
                                            Text(
                                              '${widget.task.estimatedMinutes} min',
                                              style: TextStyle(
                                                color: context.sparkleColors
                                                    .textSecondary,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                        // Subtask progress indicator
                                        if (widget.task.subtasksTotal > 0) ...[
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              Icon(
                                                Icons.checklist,
                                                size: 14,
                                                color: context.sparkleColors
                                                    .textSecondary,
                                              ),
                                              const SizedBox(width: 4),
                                              Expanded(
                                                child: SubtaskProgressIndicator(
                                                  completed: widget
                                                      .task.subtasksCompleted,
                                                  total:
                                                      widget.task.subtasksTotal,
                                                  showLabel: true,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ],
                                        if (!widget.compact) ...[
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _DifficultyStars(
                                                difficulty:
                                                    widget.task.difficulty,
                                              ),
                                              const Spacer(),
                                              if (widget.onStart != null &&
                                                  widget.task.status !=
                                                      TaskStatus.completed)
                                                _ActionButton(
                                                  icon:
                                                      Icons.play_arrow_rounded,
                                                  color: context.sparkleColors
                                                      .brandPrimary,
                                                  onPressed: () {
                                                    unawaited(
                                                      SensoryFeedbackService
                                                          .emit(
                                                        SensoryFeedbackEvent
                                                            .confirm,
                                                      ),
                                                    );
                                                    widget.onStart!();
                                                  },
                                                ),
                                              if (widget.onComplete != null &&
                                                  widget.task.status !=
                                                      TaskStatus.completed) ...[
                                                const SizedBox(width: 8),
                                                _ActionButton(
                                                  icon: Icons.check_rounded,
                                                  color: context.sparkleColors
                                                      .semanticSuccess,
                                                  onPressed: () {
                                                    unawaited(
                                                      SensoryFeedbackService
                                                          .emit(
                                                        SensoryFeedbackEvent
                                                            .success,
                                                      ),
                                                    );
                                                    widget.onComplete!();
                                                  },
                                                ),
                                              ],
                                            ],
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          // Sync Error Overlay
                          if (widget.task.syncStatus == TaskSyncStatus.failed)
                            Positioned.fill(
                              child: ClipRect(
                                child: BackdropFilter(
                                  filter:
                                      ImageFilter.blur(sigmaX: 4, sigmaY: 4),
                                  child: ColoredBox(
                                    color: context.sparkleColors.semanticError
                                        .withValues(alpha: 0.8),
                                    child: Center(
                                      child: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(
                                            Icons.cloud_off,
                                            color:
                                                ThemeUtils.getContrastSafeText(
                                              context
                                                  .sparkleColors.semanticError,
                                              darkText: context
                                                  .sparkleColors.textPrimary,
                                            ),
                                            size: 32,
                                          ),
                                          const SizedBox(height: 8),
                                          Text(
                                            widget.task.syncError ??
                                                'Sync Failed',
                                            style: TextStyle(
                                              color: ThemeUtils
                                                  .getContrastSafeText(
                                                context.sparkleColors
                                                    .semanticError,
                                                darkText: context
                                                    .sparkleColors.textPrimary,
                                              ),
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                          const SizedBox(height: 12),
                                          Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              SparkleButton(
                                                label: 'Discard',
                                                variant: ButtonVariant.ghost,
                                                onPressed: () {
                                                  ref
                                                      .read(
                                                        taskListProvider
                                                            .notifier,
                                                      )
                                                      .discardChange(
                                                        widget.task.id,
                                                      );
                                                },
                                              ),
                                              const SizedBox(width: 8),
                                              SparkleButton(
                                                label: 'Retry',
                                                onPressed: () {
                                                  unawaited(
                                                    ref
                                                        .read(
                                                          taskListProvider
                                                              .notifier,
                                                        )
                                                        .retryCompleteTask(
                                                          widget.task.id,
                                                          widget.task
                                                                  .actualMinutes ??
                                                              widget.task
                                                                  .estimatedMinutes,
                                                          widget.task.userNote,
                                                        ),
                                                  );
                                                },
                                              ),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),

                          // Syncing Indicator
                          if (widget.task.syncStatus == TaskSyncStatus.pending)
                            Positioned(
                              top: 8,
                              right: 8,
                              child: SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(
                                    context.sparkleColors.brandPrimary,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    if (!widget.enableSwipeComplete ||
        widget.onComplete == null ||
        widget.task.status == TaskStatus.completed) {
      return card;
    }
    return Dismissible(
      key: ValueKey('task-card-${widget.task.id}'),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) async {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.dragDrop),
        );
        return true;
      },
      onDismissed: (_) {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.success),
        );
        widget.onComplete?.call();
      },
      background: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing20),
        decoration: BoxDecoration(
          color: _success(context).withValues(alpha: 0.14),
          borderRadius: _radius(context),
          border: Border.all(
            color: _success(context).withValues(alpha: 0.28),
          ),
        ),
        alignment: Alignment.centerRight,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Icon(Icons.check_circle_rounded, color: _success(context)),
            const SizedBox(width: DS.spacing8),
            Text(
              '滑动完成',
              style: TextStyle(
                color: _success(context),
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      ),
      child: card,
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.color,
    required this.onPressed,
  });
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 20, color: color),
        ),
      );
}

class _DifficultyStars extends StatelessWidget {
  const _DifficultyStars({required this.difficulty});
  final int difficulty;

  @override
  Widget build(BuildContext context) => Row(
        children: List.generate(
          5,
          (index) => ShaderMask(
            shaderCallback: (bounds) => LinearGradient(
              colors: [
                DS.semanticWarning,
                SparkleContextExtension(context).colors.brandPrimary,
              ],
            ).createShader(bounds),
            child: Icon(
              index < difficulty ? Icons.star : Icons.star_border,
              color: Theme.of(context).colorScheme.onSurface,
              size: 16,
            ),
          ),
        ),
      );
}

TaskPillTone _typeTone(TaskType type) {
  switch (type) {
    case TaskType.learning:
      return TaskPillTone.brand;
    case TaskType.training:
      return TaskPillTone.brand;
    case TaskType.errorFix:
      return TaskPillTone.danger;
    case TaskType.reflection:
      return TaskPillTone.info;
    case TaskType.social:
      return TaskPillTone.success;
    case TaskType.planning:
      return TaskPillTone.neutral;
    case TaskType.ocr:
      return TaskPillTone.neutral;
  }
}

TaskPillTone _statusTone(TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return TaskPillTone.brand;
    case TaskStatus.inProgress:
      return TaskPillTone.brand;
    case TaskStatus.completed:
      return TaskPillTone.success;
    case TaskStatus.abandoned:
      return TaskPillTone.neutral;
  }
}

String _typeLabel(TaskType type) {
  switch (type) {
    case TaskType.learning:
      return 'Learning';
    case TaskType.training:
      return 'Training';
    case TaskType.errorFix:
      return 'Fix';
    case TaskType.reflection:
      return 'Reflection';
    case TaskType.social:
      return 'Social';
    case TaskType.planning:
      return 'Plan';
    case TaskType.ocr:
      return 'OCR';
  }
}
