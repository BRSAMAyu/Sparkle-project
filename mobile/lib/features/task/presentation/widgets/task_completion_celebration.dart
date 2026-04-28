import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskCompletionCelebration extends StatefulWidget {
  const TaskCompletionCelebration({
    required this.task,
    required this.onContinue,
    super.key,
    this.play = true,
    this.autoDismissDelay = const Duration(milliseconds: 2500),
  });

  final TaskModel task;
  final bool play;
  final VoidCallback onContinue;
  final Duration autoDismissDelay;

  @override
  State<TaskCompletionCelebration> createState() =>
      _TaskCompletionCelebrationState();
}

class _TaskCompletionCelebrationState extends State<TaskCompletionCelebration> {
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _scheduleAutoDismiss();
  }

  @override
  void didUpdateWidget(covariant TaskCompletionCelebration oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.task.id != widget.task.id ||
        oldWidget.autoDismissDelay != widget.autoDismissDelay) {
      _scheduleAutoDismiss();
    }
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    super.dispose();
  }

  void _scheduleAutoDismiss() {
    _autoDismissTimer?.cancel();
    _autoDismissTimer = Timer(widget.autoDismissDelay, widget.onContinue);
  }

  @override
  Widget build(BuildContext context) {
    final criteria = taskSuccessCriteriaLines(widget.task);

    return Material(
      key: const Key('task-completion-celebration'),
      color: DS.overlay50.withValues(alpha: 0.62),
      child: SparkleConfetti(
        play: widget.play,
        intensity: SparkleCelebrationIntensity.small,
        enableSensory: false,
        child: Center(
          child: TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0.96, end: 1),
            duration: DS.motionDuration(SparkleMotionToken.scene),
            curve: DS.motionCurve(SparkleMotionToken.scene),
            builder: (context, scale, child) =>
                Transform.scale(scale: scale, child: child),
            child: GraphiteCardSurface(
              borderColor: DS.success.withValues(alpha: 0.24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 360),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      context.l10n.taskCompletedToday,
                      textAlign: TextAlign.center,
                      style: DS.titleLarge.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      context.l10n.taskDone,
                      textAlign: TextAlign.center,
                      style:
                          Theme.of(context).textTheme.headlineSmall?.copyWith(
                                    color: DS.success,
                                    fontWeight: DS.fontWeightBold,
                                  ) ??
                              DS.titleLarge.copyWith(
                                color: DS.success,
                                fontWeight: DS.fontWeightBold,
                              ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    if (criteria.isNotEmpty)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (final item in criteria.take(3))
                            _CelebrationCriterion(text: item),
                        ],
                      )
                    else
                      Text(
                        context.l10n.taskCompletedOneStep,
                        textAlign: TextAlign.center,
                        style: DS.bodyMedium.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      ),
                    const SizedBox(height: DS.spacing20),
                    SparkleButton(
                      label: context.l10n.taskContinueNext,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      onPressed: widget.onContinue,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CelebrationCriterion extends StatelessWidget {
  const _CelebrationCriterion({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.check_circle_rounded, color: DS.success, size: 18),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                text,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
            ),
          ],
        ),
      );
}

List<String> taskSuccessCriteriaLines(TaskModel task) {
  final guide = task.guideJson ?? const <String, dynamic>{};
  final fromGuide = _readList(guide['success_criteria']);
  if (fromGuide.isNotEmpty) return fromGuide;
  return _readList(task.successCriteria);
}

List<String> _readList(Object? value) {
  if (value == null) return const [];
  if (value is Iterable) {
    return value
        .map((item) => item?.toString().trim() ?? '')
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
  final text = value.toString().trim();
  if (text.isEmpty) return const [];
  return text
      .split(RegExp(r'[\n；;]+'))
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}
