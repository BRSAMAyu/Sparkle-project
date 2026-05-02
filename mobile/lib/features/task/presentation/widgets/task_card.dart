import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/components/atoms/task_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/features/task/presentation/widgets/subtask_list_widget.dart';
import 'package:sparkle/features/task/presentation/widgets/task_quick_action_menu.dart';
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

class _TaskCardState extends ConsumerState<TaskCard> {
  bool _hasEmittedDragStart = false;

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
      _sparkleTheme(context)?.colors.semanticSuccess ?? DS.success;

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
    final card = _buildCardContent(context);
    if (!widget.enableSwipeComplete ||
        widget.onComplete == null ||
        widget.task.status == TaskStatus.completed) {
      return card;
    }
    return Dismissible(
      key: ValueKey('task-card-${widget.task.id}'),
      direction: DismissDirection.endToStart,
      onUpdate: (details) {
        if (details.progress <= 0.01) {
          _hasEmittedDragStart = false;
          return;
        }
        if (_hasEmittedDragStart || details.progress <= 0.04) {
          return;
        }
        _hasEmittedDragStart = true;
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.dragStart),
        );
      },
      confirmDismiss: (_) async {
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.dragDrop),
        );
        final l10n = context.l10n;
        return await showDialog<bool>(
              context: context,
              builder: (dialogContext) => AlertDialog(
                title: Text(l10n.taskConfirmCompleteTitle),
                content: Text(l10n.taskConfirmCompleteBody(widget.task.title)),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(dialogContext).pop(false),
                    child: Text(l10n.cancel),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.of(dialogContext).pop(true),
                    child: Text(l10n.confirm),
                  ),
                ],
              ),
            ) ??
            false;
      },
      onResize: () {
        _hasEmittedDragStart = false;
      },
      onDismissed: (_) {
        _hasEmittedDragStart = false;
        unawaited(
          SensoryFeedbackService.emit(SensoryFeedbackEvent.success),
        );
        widget.onComplete?.call();
      },
      background: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        alignment: Alignment.centerRight,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
          decoration: BoxDecoration(
            color: _success(context).withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: _success(context).withValues(alpha: 0.26),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.check_circle_rounded,
                color: _success(context),
                size: 18,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                context.l10n.taskActionComplete,
                style: TextStyle(
                  color: _success(context),
                  fontWeight: DS.fontWeightBold,
                  fontSize: DS.fontSizeSm,
                ),
              ),
            ],
          ),
        ),
      ),
      child: card,
    );
  }

  Widget _buildCardContent(BuildContext context) => Semantics(
        label: 'Task card for ${widget.task.title}',
        hint: 'Double tap to view details',
        button: true,
        enabled: true,
        child: Hero(
          tag: 'task-${widget.task.id}',
          child: Material(
            type: MaterialType.transparency,
            child: SparkleTappable(
              onTap: widget.onTap,
              onLongPress: () => showTaskQuickActionMenu(
                context: context,
                ref: ref,
                task: widget.task,
              ),
              borderRadius: _radius(context),
              child: RepaintBoundary(
                child: Container(
                  margin:
                      const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  decoration: BoxDecoration(
                    gradient: _getBackgroundGradient(context, widget.task.type),
                    borderRadius: _radius(context),
                    border: Border.all(
                      color: context.sparkleColors
                          .getTaskColor(widget.task.type.name)
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
                        context.sparkleColors.brandPrimary.withValues(alpha: 0),
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
                              Container(
                                width: 4,
                                decoration: BoxDecoration(
                                  gradient: _getTypeGradient(
                                    context,
                                    widget.task.type,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: Padding(
                                  padding: EdgeInsets.all(_spacingMd(context)),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  children: [
                                                    Flexible(
                                                      child: Text(
                                                        widget.task.title,
                                                        style: Theme.of(context)
                                                            .textTheme
                                                            .titleMedium
                                                            ?.copyWith(
                                                              fontWeight:
                                                                  DS
                                                                      .fontWeightBold,
                                                              color:
                                                                  _textPrimary(
                                                                context,
                                                              ),
                                                            ),
                                                        maxLines: widget.compact
                                                            ? 2
                                                            : 3,
                                                        overflow: TextOverflow
                                                            .ellipsis,
                                                      ),
                                                    ),
                                                    if (widget.task.status ==
                                                        TaskStatus.completed)
                                                      Padding(
                                                        padding:
                                                            const EdgeInsets
                                                                .only(
                                                          left: 8,
                                                        ),
                                                        child: Icon(
                                                          Icons.check_circle,
                                                          size: 18,
                                                          color:
                                                              _success(context),
                                                        ),
                                                      ),
                                                  ],
                                                ),
                                                const SizedBox(height: 6),
                                                Row(
                                                  children: [
                                                    _TaskTypePill(
                                                      type: widget.task.type,
                                                    ),
                                                    if (widget.task.status !=
                                                        TaskStatus.pending) ...[
                                                      const SizedBox(width: 8),
                                                      TaskPill(
                                                        type: widget.task.type,
                                                        label: _statusLabel(
                                                          context.l10n,
                                                          widget.task.status,
                                                        ),
                                                        tone: _statusTone(
                                                          widget.task.status,
                                                        ),
                                                      ),
                                                    ],
                                                    if (!widget.compact) ...[
                                                      const SizedBox(width: 8),
                                                      _DifficultyStars(
                                                        difficulty: widget
                                                            .task.difficulty,
                                                      ),
                                                    ],
                                                  ],
                                                ),
                                              ],
                                            ),
                                          ),
                                          if (widget.onStart != null ||
                                              widget.onComplete != null)
                                            Padding(
                                              padding: const EdgeInsets.only(
                                                left: 12,
                                              ),
                                              child: Column(
                                                children: [
                                                  if (widget.onStart != null &&
                                                      widget.task.status ==
                                                          TaskStatus.pending)
                                                    _ActionButton(
                                                      icon: Icons.play_arrow,
                                                      color: context
                                                          .sparkleColors
                                                          .brandPrimary,
                                                      onPressed:
                                                          widget.onStart!,
                                                    ),
                                                  if (widget.onComplete !=
                                                          null &&
                                                      widget.task.status !=
                                                          TaskStatus.completed)
                                                    _ActionButton(
                                                      icon: Icons.check,
                                                      color: _success(context),
                                                      onPressed:
                                                          widget.onComplete!,
                                                    ),
                                                ],
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 10),
                                      Row(
                                        children: [
                                          Icon(
                                            Icons.schedule,
                                            size: 14,
                                            color: _textDisabled(context),
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            context.l10n.taskEstimatedMinutesValue(widget.task.estimatedMinutes),
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.copyWith(
                                                  color: _textDisabled(context),
                                                ),
                                          ),
                                          const SizedBox(width: 12),
                                          Icon(
                                            Icons.flash_on_rounded,
                                            size: 14,
                                            color: _textDisabled(context),
                                          ),
                                          const SizedBox(width: 4),
                                          Text(
                                            '${widget.task.energyCost}',
                                            style: Theme.of(context)
                                                .textTheme
                                                .bodySmall
                                                ?.copyWith(
                                                  color: _textDisabled(context),
                                                ),
                                          ),
                                          const Spacer(),
                                          if (widget.task.dueDate != null)
                                            Text(
                                              DateFormat('MM/dd').format(
                                                widget.task.dueDate!,
                                              ),
                                              style: Theme.of(context)
                                                  .textTheme
                                                  .bodySmall
                                                  ?.copyWith(
                                                    color:
                                                        _textDisabled(context),
                                                  ),
                                            ),
                                        ],
                                      ),
                                      if (widget.task.subtasksTotal > 0) ...[
                                        const SizedBox(height: 10),
                                        SubtaskProgressIndicator(
                                          completed:
                                              widget.task.subtasksCompleted,
                                          total: widget.task.subtasksTotal,
                                        ),
                                      ],
                                      if ((widget.task.userNote ??
                                              widget.task.guideContent ??
                                              '')
                                          .isNotEmpty) ...[
                                        const SizedBox(height: 10),
                                        Text(
                                          widget.task.userNote ??
                                              widget.task.guideContent!,
                                          maxLines: widget.compact ? 2 : 3,
                                          overflow: TextOverflow.ellipsis,
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodySmall
                                              ?.copyWith(
                                                color: DS.textSecondary,
                                                height: 1.35,
                                              ),
                                        ),
                                      ],
                                      if (widget.task.knowledgeNodeId != null) ...[
                                        const SizedBox(height: 8),
                                        _SourceContextChip(task: widget.task),
                                      ],
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
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
      );
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
  Widget build(BuildContext context) => SparkleTappable(
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

class _TaskTypePill extends StatelessWidget {
  const _TaskTypePill({required this.type});

  final TaskType type;

  @override
  Widget build(BuildContext context) => TaskPill(
        type: type,
        label: _typeLabel(type),
        tone: _typeTone(type),
      );
}

class _DifficultyStars extends StatelessWidget {
  const _DifficultyStars({required this.difficulty});
  final int difficulty;

  @override
  Widget build(BuildContext context) => Row(
        children: List.generate(
          5,
          (index) => ExcludeSemantics(
            child: ShaderMask(
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
    case TaskStatus.stuck:
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

String _statusLabel(AppLocalizations l10n, TaskStatus status) {
  switch (status) {
    case TaskStatus.pending:
      return l10n.taskStatusPending;
    case TaskStatus.inProgress:
      return l10n.taskStatusInProgress;
    case TaskStatus.stuck:
      return l10n.taskStatusStuck;
    case TaskStatus.completed:
      return l10n.taskStatusCompleted;
    case TaskStatus.abandoned:
      return l10n.taskStatusAbandoned;
  }
}

class _SourceContextChip extends StatelessWidget {
  const _SourceContextChip({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context) {
    final hasGuide = (task.guideContent ?? '').isNotEmpty;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.auto_stories, size: 14, color: DS.brandPrimary),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              hasGuide ? 'Linked to knowledge source' : 'Knowledge-linked task',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.brandPrimary,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
