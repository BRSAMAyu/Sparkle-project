import 'dart:ui';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:intl/intl.dart';

class TaskCard extends ConsumerStatefulWidget {
  final TaskModel task;
  final VoidCallback? onTap;
  final VoidCallback? onStart;
  final VoidCallback? onComplete;
  final bool compact;

  const TaskCard({
    required this.task,
    super.key,
    this.onTap,
    this.onStart,
    this.onComplete,
    this.compact = false,
  });

  @override
  ConsumerState<TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends ConsumerState<TaskCard> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AppDesignTokens.durationFast,
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

  LinearGradient _getTypeGradient(BuildContext context, TaskType type) {
    return context.colors.getTaskGradient(type.name);
  }

  LinearGradient _getBackgroundGradient(BuildContext context, TaskType type) {
    final taskColor = context.colors.getTaskColor(type.name);
    return LinearGradient(
      colors: [
        taskColor.withValues(alpha: 0.05),
        context.colors.surfaceCard,
      ],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
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
              _controller.forward();
            },
            onTapUp: (_) => _controller.reverse(),
            onTapCancel: () => _controller.reverse(),
            onTap: widget.onTap,
            child: RepaintBoundary(
              child: AnimatedBuilder(
                animation: _scaleAnimation,
                builder: (context, child) {
                  return Transform.scale(
                    scale: _scaleAnimation.value,
                    child: child,
                  );
                },
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  decoration: BoxDecoration(
                    gradient: _getBackgroundGradient(context, widget.task.type),
                    borderRadius: AppDesignTokens.borderRadius12,
                    boxShadow: AppDesignTokens.shadowSm,
                  ),
                  foregroundDecoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        DS.brandPrimary.withValues(alpha: 0),
                        DS.brandPrimary.withValues(alpha: 0.1), // Subtle shimmer/highlight
                        DS.brandPrimary.withValues(alpha: 0),
                      ],
                      stops: const [0.0, 0.5, 1.0],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: AppDesignTokens.borderRadius12,
                  ),
                  child: ClipRRect(
                    borderRadius: AppDesignTokens.borderRadius12,
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
                                  gradient: _getTypeGradient(context, widget.task.type),
                                ),
                              ),
                              // Content
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.all(AppDesignTokens.spacing12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Expanded(
                                            child: Text(
                                              widget.task.title,
                                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                                fontWeight: AppDesignTokens.fontWeightBold,
                                                decoration: widget.task.status == TaskStatus.completed
                                                    ? TextDecoration.lineThrough
                                                    : null,
                                                color: widget.task.status == TaskStatus.completed
                                                    ? AppDesignTokens.neutral500
                                                    : AppDesignTokens.neutral900,
                                              ),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                          if (!widget.compact) ...[
                                            const SizedBox(width: AppDesignTokens.spacing8),
                                            _TaskTypeChip(type: widget.task.type),
                                            if (widget.task.status == TaskStatus.completed) ...[
                                              const SizedBox(width: AppDesignTokens.spacing4),
                                              const Icon(Icons.check_circle, color: AppDesignTokens.success, size: 16),
                                            ] else if (widget.task.status != TaskStatus.pending) ...[
                                               const SizedBox(width: AppDesignTokens.spacing4),
                                              _StatusChip(status: widget.task.status),
                                            ],
                                          ],
                                        ],
                                      ),
                                      const SizedBox(height: AppDesignTokens.spacing8),
                                      Row(
                                        children: [
                                          if (widget.task.dueDate != null) ...[
                                            const Icon(Icons.calendar_today, size: 14, color: AppDesignTokens.neutral600),
                                            const SizedBox(width: DS.xs),
                                            Text(
                                              DateFormat.yMd().format(widget.task.dueDate!),
                                              style: const TextStyle(color: AppDesignTokens.neutral700, fontSize: 12),
                                            ),
                                            const SizedBox(width: AppDesignTokens.spacing12),
                                          ],
                                          const Icon(Icons.timer_outlined, size: 14, color: AppDesignTokens.neutral600),
                                          const SizedBox(width: DS.xs),
                                          Text(
                                            '${widget.task.estimatedMinutes} min',
                                            style: const TextStyle(color: AppDesignTokens.neutral700, fontSize: 12),
                                          ),
                                        ],
                                      ),
                                      if (!widget.compact) ...[
                                        const SizedBox(height: AppDesignTokens.spacing8),
                                        Row(
                                          children: [
                                            _DifficultyStars(difficulty: widget.task.difficulty),
                                            const Spacer(),
                                            if (widget.onStart != null && widget.task.status != TaskStatus.completed)
                                              _ActionButton(
                                                icon: Icons.play_arrow_rounded,
                                                color: AppDesignTokens.primaryBase,
                                                onPressed: () {
                                                  HapticFeedback.selectionClick();
                                                  widget.onStart!();
                                                },
                                              ),
                                            if (widget.onComplete != null && widget.task.status != TaskStatus.completed) ...[
                                              const SizedBox(width: AppDesignTokens.spacing8),
                                              _ActionButton(
                                                icon: Icons.check_rounded,
                                                color: AppDesignTokens.success,
                                                onPressed: () {
                                                  HapticFeedback.mediumImpact();
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
                              child: Container(
                                color: AppDesignTokens.error.withValues(alpha: 0.8),
                                child: Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(Icons.cloud_off, color: DS.brandPrimary, size: 32),
                                      const SizedBox(height: AppDesignTokens.spacing8),
                                      Text(
                                        widget.task.syncError ?? 'Sync Failed',
                                        style: const TextStyle(color: DS.brandPrimary, fontWeight: FontWeight.bold),
                                      ),
                                      const SizedBox(height: AppDesignTokens.spacing12),
                                      Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          TextButton(
                                            onPressed: () {
                                               ref.read(taskListProvider.notifier).discardChange(widget.task.id);
                                            },
                                            style: TextButton.styleFrom(foregroundColor: DS.brandPrimary),
                                            child: const Text('Discard'),
                                          ),
                                          const SizedBox(width: DS.sm),
                                          ElevatedButton(
                                            onPressed: () {
                                               ref.read(taskListProvider.notifier).retryCompleteTask(
                                                widget.task.id, 
                                                widget.task.actualMinutes ?? widget.task.estimatedMinutes, 
                                                widget.task.userNote,
                                              );
                                            },
                                            style: ElevatedButton.styleFrom(
                                              backgroundColor: DS.brandPrimary,
                                              foregroundColor: AppDesignTokens.error,
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
                          const Positioned(
                            top: 8,
                            right: 8,
                            child: SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(AppDesignTokens.primaryBase),
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
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;

  const _ActionButton({required this.icon, required this.color, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onPressed,
      borderRadius: AppDesignTokens.borderRadius20,
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
}

class _DifficultyStars extends StatelessWidget {
  final int difficulty;
  const _DifficultyStars({required this.difficulty});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(5, (index) {
        return ShaderMask(
          shaderCallback: (bounds) {
            return const LinearGradient(
              colors: [Colors.amber, Colors.orange],
            ).createShader(bounds);
          },
          child: Icon(
            index < difficulty ? Icons.star : Icons.star_border,
            color: DS.brandPrimary, // Color is ignored by shader but needed for structure
            size: 16,
          ),
        );
      }),
    );
  }
}

class _TaskTypeChip extends StatelessWidget {
  final TaskType type;
  const _TaskTypeChip({required this.type});

  @override
  Widget build(BuildContext context) {
    Color color;
    String label;
    switch (type) {
      case TaskType.learning:
        color = DS.brandPrimary;
        label = 'Learning';
        break;
      case TaskType.training:
        color = Colors.orange;
        label = 'Training';
        break;
      case TaskType.errorFix:
        color = DS.error;
        label = 'Fix';
        break;
      case TaskType.reflection:
        color = Colors.purple;
        label = 'Reflection';
        break;
      case TaskType.social:
        color = DS.success;
        label = 'Social';
        break;
      case TaskType.planning:
        color = Colors.teal;
        label = 'Plan';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: AppDesignTokens.borderRadius12,
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 10,
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final TaskStatus status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (status) {
      case TaskStatus.pending:
        color = Colors.orange;
        break;
      case TaskStatus.inProgress:
        color = DS.brandPrimary;
        break;
      case TaskStatus.completed:
        color = DS.success;
        break;
      case TaskStatus.abandoned:
        color = DS.brandPrimary;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: AppDesignTokens.borderRadius12,
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        toBeginningOfSentenceCase(status.name)!,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 10,
        ),
      ),
    );
  }
}