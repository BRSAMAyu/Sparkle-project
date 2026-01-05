import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/components/atoms/task_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskCard extends ConsumerStatefulWidget {
  const TaskCard({
    required this.task,
    super.key,
    this.onTap,
    this.onStart,
    this.onComplete,
    this.compact = false,
  });
  final TaskModel task;
  final VoidCallback? onTap;
  final VoidCallback? onStart;
  final VoidCallback? onComplete;
  final bool compact;

  @override
  ConsumerState<TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends ConsumerState<TaskCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

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
        taskColor.withValues(alpha: 0.05),
        context.sparkleColors.surfaceSecondary,
      ],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }

  @override
  Widget build(BuildContext context) => Semantics(
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
                HapticFeedback.lightImpact();
                if (mounted) _controller.forward();
              },
              onTapUp: (_) {
                if (mounted) _controller.reverse();
              },
              onTapCancel: () {
                if (mounted) _controller.reverse();
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
                      borderRadius: context.radius.mdRadius,
                      boxShadow: context.sparkleShadows.medium,
                    ),
                    foregroundDecoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          context.sparkleColors.brandPrimary
                              .withValues(alpha: 0),
                          context.sparkleColors.brandPrimary
                              .withValues(alpha: 0.1),
                          context.sparkleColors.brandPrimary
                              .withValues(alpha: 0),
                        ],
                        stops: const [0.0, 0.5, 1.0],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: context.radius.mdRadius,
                    ),
                    child: ClipRRect(
                      borderRadius: context.radius.mdRadius,
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
                                        context, widget.task.type,),
                                  ),
                                ),
                                // Content
                                Expanded(
                                  child: Padding(
                                    padding: EdgeInsets.all(
                                        context.sparkleSpacing.md,),
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
                                                              ? context
                                                                  .sparkleColors
                                                                  .textDisabled
                                                              : context
                                                                  .sparkleColors
                                                                  .textPrimary,
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
                                                    widget.task.type,),
                                                tone:
                                                    _typeTone(widget.task.type),
                                              ),
                                              if (widget.task.status ==
                                                  TaskStatus.completed) ...[
                                                const SizedBox(width: 4),
                                                Icon(Icons.check_circle,
                                                    color: context.sparkleColors
                                                        .semanticSuccess,
                                                    size: 16,),
                                              ] else if (widget.task.status !=
                                                  TaskStatus.pending) ...[
                                                const SizedBox(width: 4),
                                                TaskPill(
                                                  type: widget.task.type,
                                                  label:
                                                      toBeginningOfSentenceCase(
                                                          widget.task.status
                                                              .name,)!,
                                                  tone: _statusTone(
                                                      widget.task.status,),
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
                                              Icon(Icons.calendar_today,
                                                  size: 14,
                                                  color: context.sparkleColors
                                                      .textSecondary,),
                                              const SizedBox(width: 4),
                                              Text(
                                                DateFormat.yMd().format(
                                                    widget.task.dueDate!,),
                                                style: TextStyle(
                                                    color: context.sparkleColors
                                                        .textSecondary,
                                                    fontSize: 12,),
                                              ),
                                              const SizedBox(width: 12),
                                            ],
                                            Icon(Icons.timer_outlined,
                                                size: 14,
                                                color: context.sparkleColors
                                                    .textSecondary,),
                                            const SizedBox(width: 4),
                                            Text(
                                              '${widget.task.estimatedMinutes} min',
                                              style: TextStyle(
                                                  color: context.sparkleColors
                                                      .textSecondary,
                                                  fontSize: 12,),
                                            ),
                                          ],
                                        ),
                                        if (!widget.compact) ...[
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _DifficultyStars(
                                                  difficulty:
                                                      widget.task.difficulty,),
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
                                                    HapticFeedback
                                                        .selectionClick();
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
                                                    HapticFeedback
                                                        .mediumImpact();
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
                              child: BackdropFilter(
                                filter: ImageFilter.blur(sigmaX: 4, sigmaY: 4),
                                child: ColoredBox(
                                  color: context.sparkleColors.semanticError
                                      .withValues(alpha: 0.8),
                                  child: Center(
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.cloud_off,
                                            color: context
                                                .sparkleColors.brandPrimary,
                                            size: 32,),
                                        const SizedBox(height: 8),
                                        Text(
                                          widget.task.syncError ??
                                              'Sync Failed',
                                          style: TextStyle(
                                              color: context
                                                  .sparkleColors.brandPrimary,
                                              fontWeight: FontWeight.bold,),
                                        ),
                                        const SizedBox(height: 12),
                                        Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            TextButton(
                                              onPressed: () {
                                                ref
                                                    .read(taskListProvider
                                                        .notifier,)
                                                    .discardChange(
                                                        widget.task.id,);
                                              },
                                              style: TextButton.styleFrom(
                                                  foregroundColor: context
                                                      .sparkleColors
                                                      .brandPrimary,),
                                              child: const Text('Discard'),
                                            ),
                                            const SizedBox(width: 8),
                                            ElevatedButton(
                                              onPressed: () {
                                                ref
                                                    .read(taskListProvider
                                                        .notifier,)
                                                    .retryCompleteTask(
                                                      widget.task.id,
                                                      widget.task
                                                              .actualMinutes ??
                                                          widget.task
                                                              .estimatedMinutes,
                                                      widget.task.userNote,
                                                    );
                                              },
                                              style: ElevatedButton.styleFrom(
                                                backgroundColor: context
                                                    .sparkleColors.brandPrimary,
                                                foregroundColor: context
                                                    .sparkleColors
                                                    .semanticError,
                                              ),
                                              child: const Text('Retry'),
                                            ),
                                          ],
                                        ),
                                      ],
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
                                      context.sparkleColors.brandPrimary,),
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
}

class _ActionButton extends StatelessWidget {
  const _ActionButton(
      {required this.icon, required this.color, required this.onPressed,});
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
                Colors.amber,
                SparkleContextExtension(context).colors.brandPrimary,
              ],
            ).createShader(bounds),
            child: Icon(
              index < difficulty ? Icons.star : Icons.star_border,
              color: Colors.white,
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
  }
}
