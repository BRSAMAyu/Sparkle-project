import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_detail_provider.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';

/// J-08 目标步骤完成时刻的轻庆祝态 + 一题式微反思。
///
/// 视觉完全复用既有 celebration 形制（与 TaskCompletionCelebration 同源）：
/// 背景模糊 + SparkleConfetti(small) + GraphiteCardSurface + scene 级运动
/// 令牌 + success 感官事件——不发明新视觉。
///
/// 内容即轨迹：步骤（成果）→ 目标（想法）的一句话连线，不展示分钟/
/// streak。内嵌一题式微反思（完成感受三选一，可跳过，一次点击即存），
/// 写入既有任务反馈链（POST /tasks/{id}/feedback 的 category 字段）——
/// 反思汇总页消费同一数据源，零新存储。
class GoalStepCompletionCelebration extends ConsumerStatefulWidget {
  const GoalStepCompletionCelebration({
    required this.celebration,
    required this.onContinue,
    super.key,
  });

  final GoalStepCelebration celebration;
  final VoidCallback onContinue;

  @override
  ConsumerState<GoalStepCompletionCelebration> createState() =>
      _GoalStepCompletionCelebrationState();
}

class _GoalStepCompletionCelebrationState
    extends ConsumerState<GoalStepCompletionCelebration> {
  String? _selectedCategory;
  bool _isSavingReflection = false;
  bool _reflectionSaved = false;
  bool _reflectionFailed = false;

  Future<void> _selectCategory(String category) async {
    if (_reflectionSaved || _isSavingReflection) return;
    unawaited(
      SensoryFeedbackService.emit(
        SensoryFeedbackEvent.selection,
        enableSound: false,
      ),
    );
    setState(() {
      _selectedCategory = category;
      _isSavingReflection = true;
      _reflectionFailed = false;
    });
    try {
      await ref.read(taskRepositoryProvider).submitTaskFeedback(
            widget.celebration.taskId,
            TaskFeedbackSubmission(category: category),
          );
      if (!mounted) return;
      setState(() {
        _reflectionSaved = true;
      });
    } catch (_) {
      // 微反思是可选增强：失败诚实提示，绝不阻塞庆祝态关闭。
      if (!mounted) return;
      setState(() {
        _reflectionFailed = true;
        _selectedCategory = null;
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSavingReflection = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final stepTitle = widget.celebration.stepTitle;

    return Material(
      key: const Key('goal-step-celebration'),
      color: Colors.transparent,
      child: Stack(
        children: [
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
              child: Container(
                color: DS.overlay50.withValues(alpha: 0.5),
              ),
            ),
          ),
          SparkleConfetti(
            play: true,
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
                          l10n.goalStepCelebrationTitle,
                          textAlign: TextAlign.center,
                          style: DS.titleLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        if (stepTitle.isNotEmpty) ...[
                          const SizedBox(height: DS.spacing8),
                          Text(
                            stepTitle,
                            textAlign: TextAlign.center,
                            style: DS.bodyMedium.copyWith(
                              color: DS.success,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                          ),
                        ],
                        const SizedBox(height: DS.spacing12),
                        // 轨迹连线：成果（这一步）→ 想法（目标），替代
                        // 分钟/streak 式的数字汇报。
                        Row(
                          children: [
                            Icon(
                              Icons.route_rounded,
                              size: 16,
                              color: DS.brandPrimary,
                            ),
                            const SizedBox(width: DS.spacing8),
                            Expanded(
                              child: Text(
                                l10n.goalStepCelebrationTrajectory(
                                  widget.celebration.goalTitle,
                                ),
                                style: DS.bodySmall.copyWith(
                                  color: DS.textSecondary,
                                  height: 1.45,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing16),
                        // 一题式微反思：完成感受三选一，一次点击即存，
                        // 复用任务反馈既有 category 枚举与端点。
                        Text(
                          l10n.goalStepReflectionQuestion,
                          style: Theme.of(context)
                                  .textTheme
                                  .labelMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                        ),
                        const SizedBox(height: DS.spacing8),
                        Wrap(
                          spacing: DS.spacing8,
                          runSpacing: DS.spacing8,
                          children: [
                            _FeelingOption(
                              label: l10n.taskFeedbackCategoryStillHard,
                              selected: _selectedCategory == 'too_difficult',
                              onTap: () => unawaited(
                                _selectCategory('too_difficult'),
                              ),
                            ),
                            _FeelingOption(
                              label: l10n.taskFeedbackCategoryJustRight,
                              selected: _selectedCategory == 'just_right',
                              onTap: () => unawaited(
                                _selectCategory('just_right'),
                              ),
                            ),
                            _FeelingOption(
                              label: l10n.taskFeedbackCategoryTooEasy,
                              selected: _selectedCategory == 'too_easy',
                              onTap: () => unawaited(
                                _selectCategory('too_easy'),
                              ),
                            ),
                          ],
                        ),
                        if (_reflectionSaved) ...[
                          const SizedBox(height: DS.spacing8),
                          Text(
                            l10n.goalStepReflectionSaved,
                            style: DS.bodySmall.copyWith(
                              color: DS.success,
                            ),
                          ),
                        ],
                        if (_reflectionFailed) ...[
                          const SizedBox(height: DS.spacing8),
                          Text(
                            l10n.goalStepReflectionFailed,
                            style: DS.bodySmall.copyWith(
                              color: DS.warning,
                            ),
                          ),
                        ],
                        const SizedBox(height: DS.spacing20),
                        SparkleButton(
                          label: l10n.taskContinueNext,
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
        ],
      ),
    );
  }
}

class _FeelingOption extends StatelessWidget {
  const _FeelingOption({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        borderRadius: DS.borderRadius20,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: selected
                ? DS.primaryBase.withValues(alpha: 0.12)
                : DS.neutral50,
            borderRadius: DS.borderRadius20,
            border: Border.all(
              color: selected ? DS.primaryBase : DS.neutral300,
            ),
          ),
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: selected ? DS.primaryBase : DS.textSecondary,
                  fontWeight:
                      selected ? DS.fontWeightSemibold : DS.fontWeightMedium,
                ),
          ),
        ),
      );
}
