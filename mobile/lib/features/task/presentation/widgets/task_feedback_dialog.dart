import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart' as custom;
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/task/data/models/next_action.dart';
import 'package:sparkle/features/task/data/models/task_completion_result.dart';
import 'package:sparkle/features/task/data/models/task_feedback_response.dart';
import 'package:sparkle/features/task/data/models/task_feedback_submission.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

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
  ConsumerState<TaskFeedbackDialog> createState() => _TaskFeedbackDialogState();
}

class _TaskFeedbackDialogState extends ConsumerState<TaskFeedbackDialog> {
  int? _rating;
  String? _selectedCategory;
  final _stuckController = TextEditingController();
  final _methodController = TextEditingController();
  final _adjustmentController = TextEditingController();
  bool _hasRecordedSkip = false;
  bool _isSubmitting = false;
  bool _reflectionSaved = false;
  Timer? _typewriterTimer;
  String _visibleFeedback = '';
  bool _showStreakCelebration = false;
  bool _typewriterCompleted = false;
  String? _aiReflectionResponse;
  List<Map<String, dynamic>> _linkedKnowledgeNodes = const [];

  bool get _hasStreakMilestone {
    final streakDays =
        (widget.result.statsUpdate?['streak_days'] as num?)?.toInt();
    return streakDays == 7 || streakDays == 14 || streakDays == 30;
  }

  int? get _streakDays =>
      (widget.result.statsUpdate?['streak_days'] as num?)?.toInt();

  @override
  void initState() {
    super.initState();
    _startCelebrationFlow();
  }

  @override
  void dispose() {
    _typewriterTimer?.cancel();
    _stuckController.dispose();
    _methodController.dispose();
    _adjustmentController.dispose();
    // Track skip if user hasn't interacted with any next action
    _recordSkipIfNeeded();
    super.dispose();
  }

  void _startCelebrationFlow() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
    if (_hasStreakMilestone) {
      _showStreakCelebration = true;
      unawaited(
        SensoryFeedbackService.emitSeries(
          const [
            SensoryFeedbackEvent.selection,
            SensoryFeedbackEvent.success,
            SensoryFeedbackEvent.streak,
          ],
          gap: const Duration(milliseconds: 150),
          enableSound: false,
        ),
      );
      unawaited(
        Future<void>.delayed(const Duration(milliseconds: 1800), () {
          if (!mounted) return;
          setState(() {
            _showStreakCelebration = false;
          });
        }),
      );
    }
    _startTypewriter();
  }

  void _startTypewriter() {
    final feedback = widget.result.feedback;
    if (feedback == null || feedback.isEmpty) {
      _visibleFeedback = '';
      _typewriterCompleted = true;
      return;
    }
    _typewriterTimer?.cancel();
    var length = 0;
    _visibleFeedback = '';
    _typewriterCompleted = false;
    _typewriterTimer =
        Timer.periodic(const Duration(milliseconds: 40), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      length = (length + 2).clamp(0, feedback.length);
      setState(() {
        _visibleFeedback = feedback.substring(0, length);
      });
      if (length >= feedback.length) {
        _typewriterCompleted = true;
        timer.cancel();
      }
    });
  }

  void _recordSkipIfNeeded() {
    if (!_hasRecordedSkip && widget.result.nextActions.isNotEmpty) {
      unawaited(
        ref.read(taskListProvider.notifier).recordNextActionsSkip(
              widget.taskId,
              widget.result.nextActions,
            ),
      );
    }
  }

  Future<void> _handleSubmit() async {
    if (_isSubmitting) return;
    if (_reflectionSaved) {
      widget.onClose();
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      TaskFeedbackResponse? response;
      final stuckPoint = _stuckController.text.trim();
      final effectiveMethod = _methodController.text.trim();
      final adjustmentIntention = _adjustmentController.text.trim();
      final hasStructuredReflection = stuckPoint.isNotEmpty ||
          effectiveMethod.isNotEmpty ||
          adjustmentIntention.isNotEmpty;
      if (_rating != null ||
          _selectedCategory != null ||
          hasStructuredReflection) {
        await SensoryFeedbackService.emit(
          SensoryFeedbackEvent.confirm,
          enableHaptic: false,
        );
        await SensoryFeedbackService.emit(
          SensoryFeedbackEvent.selection,
          enableSound: false,
        );
        response = await ref
            .read(taskListProvider.notifier)
            .submitTaskFeedbackWithResponse(
              widget.taskId,
              TaskFeedbackSubmission(
                completionQuality: _rating,
                feedbackText: stuckPoint.isEmpty ? null : stuckPoint,
                category: _selectedCategory,
                stuckPoint: stuckPoint.isEmpty ? null : stuckPoint,
                effectiveMethod:
                    effectiveMethod.isEmpty ? null : effectiveMethod,
                adjustmentIntention:
                    adjustmentIntention.isEmpty ? null : adjustmentIntention,
              ),
            );
      }

      _hasRecordedSkip = true;

      if (!mounted) return;
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
      _showFeedbackSuccess(response);
      final aiResponse = response?.aiResponse ??
          response?.reflectionPayload?['ai_response']?.toString();
      final linkedNodes = _parseLinkedNodes(response?.reflectionPayload);
      if ((aiResponse ?? '').isNotEmpty) {
        setState(() {
          _reflectionSaved = true;
          _aiReflectionResponse = aiResponse;
          _linkedKnowledgeNodes = linkedNodes;
        });
        return;
      }
      widget.onClose();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.submitFailedWithError(e));
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  List<Map<String, dynamic>> _parseLinkedNodes(Map<String, dynamic>? payload) {
    final raw = payload?['linked_knowledge_nodes'];
    if (raw is! List) {
      return [];
    }
    return raw
        .whereType<Map<dynamic, dynamic>>()
        .map((item) => item.map((key, value) => MapEntry('$key', value)))
        .toList();
  }

  void _showFeedbackSuccess(TaskFeedbackResponse? response) {
    if (!mounted) return;

    final l10n = context.l10n;
    final message = response?.message ?? l10n.taskFeedbackSubmitted;

    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.create(
        message: message,
        backgroundColor: DS.neutral800,
        foregroundColor: DS.neutral0,
        icon: Icons.check_circle,
        duration: const Duration(seconds: 3),
        showCloseIcon: true,
        actionLabel: response?.preferenceUpdates != null
            ? l10n.taskFeedbackView
            : null,
        onAction: response?.preferenceUpdates != null
            ? () => _showPreferenceDetailDialog(response!.preferenceUpdates!)
            : null,
      ),
    );
  }

  void _showPreferenceDetailDialog(PreferenceUpdates updates) {
    if (!mounted) return;
    final l10n = context.l10n;

    unawaited(
      showSensoryDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.taskFeedbackPreferenceDialogTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (updates.depthPreference != null) ...[
                Text(
                  l10n.taskFeedbackDepthPreference(
                    _formatDelta(updates.depthPreference),
                  ),
                ),
                const SizedBox(height: DS.sm),
              ],
              if (updates.difficultyPreference != null) ...[
                Text(
                  l10n.taskFeedbackDifficultyPreference(
                    _formatDelta(updates.difficultyPreference),
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing16),
              Text(
                l10n.taskFeedbackPreferenceDialogDesc,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              label: l10n.taskFeedbackGotIt,
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
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
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
    );
    unawaited(
      ref.read(taskListProvider.notifier).recordNextActionSelection(
            widget.taskId,
            action,
            position,
            true,
            widget.result.nextActions.length,
          ),
    );

    widget.onClose();
    if (action.existingTaskId != null) {
      // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
      ref.read(activeTaskProvider.notifier).state = TaskModel(
        id: action.existingTaskId!,
        userId: '',
        title: action.title,
        type: TaskType.learning,
        tags: [],
        estimatedMinutes: action.estimatedMinutes,
        difficulty: action.difficulty,
        energyCost: action.energyCost,
        status: TaskStatus.inProgress,
        priority: 5,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      context.go('/tasks/${action.existingTaskId}/execute');
    } else if (action.quickCreateParams != null && action.canQuickCreate) {
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
    final l10n = context.l10n;

    return BgmScope(
      track: BgmTrack.achievement,
      priority: BgmPriority.stage,
      child: Dialog(
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
        backgroundColor: Colors.transparent,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480, maxHeight: 600),
          child: Stack(
            children: [
              if (_showStreakCelebration)
                const Positioned.fill(
                  child: IgnorePointer(
                    child: RepaintBoundary(
                      child: SparkleConfetti(
                        play: true,
                        enableSensory: false,
                        intensity: SparkleCelebrationIntensity.large,
                        particleCount: 36,
                        colors: [
                          Color(0xFFFFA726),
                          Color(0xFFFF7043),
                          Color(0xFFFFD54F),
                        ],
                      ),
                    ),
                  ),
                ),
              TweenAnimationBuilder<double>(
                tween: Tween<double>(begin: 0.92, end: 1.0),
                duration: const Duration(milliseconds: 600),
                curve: Curves.elasticOut,
                builder: (context, scale, child) => Transform.scale(
                  scale: scale,
                  child: child,
                ),
                child: GraphiteModalSurface(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                  child: Padding(
                    padding: const EdgeInsets.only(top: DS.spacing4),
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
                                gradient: LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: [
                                    DS.surfaceSecondary,
                                    Color.alphaBlend(
                                      DS.info.withValues(alpha: 0.04),
                                      DS.surfacePrimary,
                                    ),
                                  ],
                                ),
                                shape: BoxShape.circle,
                                border: Border.all(color: DS.borderSubtle),
                              ),
                              child: Icon(
                                Icons.auto_awesome,
                                color: DS.primaryBase,
                                size: 24,
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            Text(
                              l10n.taskFeedbackCompletedTitle,
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
                                    constraints:
                                        const BoxConstraints(maxHeight: 200),
                                    child: SingleChildScrollView(
                                      child: SparkleMarkdown(
                                        content: _typewriterCompleted
                                            ? widget.result.feedback!
                                            : _visibleFeedback,
                                        textColor: DS.textPrimary,
                                        codeBackgroundColor: DS.neutral100,
                                        linkColor: DS.primaryBase,
                                      ),
                                    ),
                                  )
                                else
                                  Text(
                                    l10n.taskFeedbackCompletedSubtitle,
                                    style: theme.textTheme.bodyMedium,
                                  ),

                                if (_hasStreakMilestone) ...[
                                  const SizedBox(height: DS.spacing16),
                                  Container(
                                    padding: const EdgeInsets.all(DS.spacing12),
                                    decoration: BoxDecoration(
                                      gradient: const LinearGradient(
                                        colors: [
                                          Color(0xFFFFF3E0),
                                          Color(0xFFFFE0B2),
                                        ],
                                        begin: Alignment.topLeft,
                                        end: Alignment.bottomRight,
                                      ),
                                      borderRadius: DS.borderRadius12,
                                      border: Border.all(
                                        color: const Color(0xFFFFB74D),
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        const Icon(
                                          Icons.local_fire_department_rounded,
                                          color: Color(0xFFFF7043),
                                        ),
                                        const SizedBox(width: DS.spacing8),
                                        Expanded(
                                          child: Text(
                                            context.l10n.taskStreakDaysPraise(_streakDays ?? 0),
                                            style: theme.textTheme.bodyMedium
                                                ?.copyWith(
                                              fontWeight: DS.fontWeightBold,
                                              color: const Color(0xFF8D4E1D),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],

                                if (widget.result.unlockedAchievements
                                    .isNotEmpty) ...[
                                  const SizedBox(height: DS.spacing16),
                                  Container(
                                    padding: const EdgeInsets.all(DS.spacing12),
                                    decoration: BoxDecoration(
                                      color: DS.warning.withValues(alpha: 0.08),
                                      borderRadius: DS.borderRadius12,
                                      border: Border.all(
                                        color:
                                            DS.warning.withValues(alpha: 0.22),
                                      ),
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Icon(
                                              Icons.emoji_events_rounded,
                                              color: DS.warning,
                                              size: 18,
                                            ),
                                            const SizedBox(width: DS.spacing8),
                                            Text(
                                              context.l10n.taskUnlockedAchievements,
                                              style: theme.textTheme.titleSmall
                                                  ?.copyWith(
                                                fontWeight: DS.fontWeightBold,
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: DS.spacing8),
                                        ...widget.result.unlockedAchievements
                                            .take(3)
                                            .map(
                                              (achievement) => Padding(
                                                padding: const EdgeInsets.only(
                                                  bottom: DS.spacing4,
                                                ),
                                                child: Row(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  children: [
                                                    Container(
                                                      width: 5,
                                                      height: 5,
                                                      margin:
                                                          const EdgeInsets.only(
                                                        top: 8,
                                                        right: 8,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        color: theme
                                                                .textTheme
                                                                .bodyMedium
                                                                ?.color ??
                                                            DS.textPrimary,
                                                        shape: BoxShape.circle,
                                                      ),
                                                    ),
                                                    Expanded(
                                                      child: Text(
                                                        ((achievement as Map<
                                                                        String,
                                                                        dynamic>)[
                                                                    'name'] ??
                                                                context.l10n.taskNewAchievement)
                                                            .toString(),
                                                        style: theme.textTheme
                                                            .bodyMedium,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ),
                                      ],
                                    ),
                                  ),
                                ],

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
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceAround,
                                      children: [
                                        if (widget.result.flameUpdate != null)
                                          _StatItem(
                                            icon: Icons.local_fire_department,
                                            color: DS.brandPrimaryConst,
                                            value: ((widget.result.flameUpdate![
                                                            'brightness_change'] ??
                                                        widget.result
                                                                .flameUpdate![
                                                            'level']) as num?)
                                                    ?.toDouble() ??
                                                0,
                                            suffix: '%',
                                            label: l10n.taskFeedbackBrightness,
                                          ),
                                        if (widget.result.statsUpdate?[
                                                'total_minutes'] !=
                                            null)
                                          _StatItem(
                                            icon: Icons.schedule_rounded,
                                            color: DS.info,
                                            value: (widget.result.statsUpdate![
                                                            'total_minutes']
                                                        as num?)
                                                    ?.toDouble() ??
                                                0,
                                            suffix: 'm',
                                            label: context.l10n.taskTodayTotal,
                                          ),
                                        if (widget.result.statsUpdate != null)
                                          _StatItem(
                                            icon: Icons.emoji_events,
                                            color: DS.rarityRare,
                                            value: (widget.result.statsUpdate![
                                                        'streak_days'] as num?)
                                                    ?.toDouble() ??
                                                0,
                                            suffix: context.l10n.taskDaysUnit,
                                            label: l10n.taskFeedbackStreak,
                                          ),
                                      ],
                                    ),
                                  ),

                                const SizedBox(height: DS.spacing20),

                                // Satisfaction Rating (Optional)
                                Text(
                                  l10n.taskFeedbackOptionalRating,
                                  style: theme.textTheme.labelMedium?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: DS.xs),
                                _StarRating(
                                  rating: _rating,
                                  onRatingChanged: (rating) {
                                    unawaited(
                                      SensoryFeedbackService.emit(
                                        SensoryFeedbackEvent.selection,
                                        enableSound: false,
                                      ),
                                    );
                                    setState(() => _rating = rating);
                                  },
                                ),

                                const SizedBox(height: DS.spacing16),

                                Text(
                                  l10n.taskFeedbackDifficultyQuestion,
                                  style: theme.textTheme.labelMedium?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                                ),
                                const SizedBox(height: DS.xs),
                                Wrap(
                                  spacing: DS.spacing8,
                                  runSpacing: DS.spacing8,
                                  children: [
                                    _FeedbackCategoryChip(
                                      label: l10n.taskFeedbackCategoryJustRight,
                                      selected:
                                          _selectedCategory == 'just_right',
                                      onTap: () => setState(
                                        () => _selectedCategory = 'just_right',
                                      ),
                                    ),
                                    _FeedbackCategoryChip(
                                      label: l10n.taskFeedbackCategoryStillHard,
                                      selected:
                                          _selectedCategory == 'too_difficult',
                                      onTap: () => setState(
                                        () =>
                                            _selectedCategory = 'too_difficult',
                                      ),
                                    ),
                                    _FeedbackCategoryChip(
                                      label: l10n.taskFeedbackCategoryTooEasy,
                                      selected: _selectedCategory == 'too_easy',
                                      onTap: () => setState(
                                        () => _selectedCategory = 'too_easy',
                                      ),
                                    ),
                                  ],
                                ),

                                const SizedBox(height: DS.spacing16),

                                _ReflectionQuestionField(
                                  label: context.l10n.taskFeedbackStuckLabel,
                                  hint: context.l10n.taskFeedbackStuckHint,
                                  controller: _stuckController,
                                ),
                                const SizedBox(height: DS.spacing12),
                                _ReflectionQuestionField(
                                  label: context.l10n.taskFeedbackProgressLabel,
                                  hint: context.l10n.taskFeedbackProgressHint,
                                  controller: _methodController,
                                ),
                                const SizedBox(height: DS.spacing12),
                                _ReflectionQuestionField(
                                  label: context.l10n.taskFeedbackChangeLabel,
                                  hint: context.l10n.taskFeedbackChangeHint,
                                  controller: _adjustmentController,
                                ),
                                if (_aiReflectionResponse != null) ...[
                                  const SizedBox(height: DS.spacing16),
                                  _ReflectionResponseCard(
                                    title: l10n.taskFeedbackAiSaved,
                                    response: _aiReflectionResponse!,
                                    linkedKnowledgeNodes: _linkedKnowledgeNodes,
                                  ),
                                ],

                                // Next Actions Section
                                if (widget.result.nextActions.isNotEmpty) ...[
                                  const SizedBox(height: DS.spacing20),
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.arrow_forward,
                                        size: 18,
                                        color: DS.brandPrimaryConst,
                                      ),
                                      const SizedBox(width: DS.xs),
                                      Text(
                                        l10n.taskFeedbackNextSteps,
                                        style: theme.textTheme.titleSmall
                                            ?.copyWith(
                                          fontWeight: DS.fontWeightBold,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: DS.sm),
                                  ...widget.result.nextActions
                                      .asMap()
                                      .entries
                                      .map(
                                        (entry) => _NextActionCard(
                                          action: entry.value,
                                          position: entry.key,
                                          onTap: () => _handleNextAction(
                                            entry.value,
                                            entry.key,
                                          ),
                                        ),
                                      ),
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
                              child: SparkleButton(
                                label: _reflectionSaved
                                    ? l10n.commonClose
                                    : l10n.taskFeedbackSkip,
                                onPressed: widget.onClose,
                                variant: ButtonVariant.ghost,
                                disabled: _isSubmitting,
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            Expanded(
                              flex: 2,
                              child: custom.CustomButton.primary(
                                text: _reflectionSaved
                                    ? l10n.commonDone
                                    : l10n.commonSave,
                                onPressed: _isSubmitting ? null : _handleSubmit,
                                isLoading: _isSubmitting,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReflectionQuestionField extends StatelessWidget {
  const _ReflectionQuestionField({
    required this.label,
    required this.hint,
    required this.controller,
  });

  final String label;
  final String hint;
  final TextEditingController controller;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: DS.xs),
          TextField(
            controller: controller,
            minLines: 2,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: hint,
              border: OutlineInputBorder(
                borderRadius: DS.borderRadius8,
                borderSide: BorderSide(color: DS.neutral300),
              ),
              filled: true,
              fillColor: DS.neutral50,
              contentPadding: const EdgeInsets.all(DS.spacing12),
            ),
          ),
        ],
      );
}

class _ReflectionResponseCard extends StatelessWidget {
  const _ReflectionResponseCard({
    required this.title,
    required this.response,
    this.linkedKnowledgeNodes = const [],
  });

  final String title;
  final String response;
  final List<Map<String, dynamic>> linkedKnowledgeNodes;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.info.withValues(alpha: 0.08),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.info.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.forum_rounded, size: 18, color: DS.info),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            response,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: DS.textPrimary,
              height: 1.4,
            ),
          ),
          if (linkedKnowledgeNodes.isNotEmpty) ...[
            const SizedBox(height: DS.spacing10),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: linkedKnowledgeNodes
                  .map(
                    (node) => Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing10,
                        vertical: DS.spacing6,
                      ),
                      decoration: BoxDecoration(
                        color: DS.info.withValues(alpha: 0.12),
                        borderRadius: DS.borderRadius20,
                      ),
                      child: Text(
                        (node['name'] ?? node['id'] ?? '').toString(),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: DS.info,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
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
          return GestureDetector(
            onTap: () => onRatingChanged(starValue),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing4),
              child: Icon(
                rating != null && starValue <= rating!
                    ? Icons.star
                    : Icons.star_border,
                color: DS.rarityRare,
                size: 36,
              ),
            ),
          );
        }),
      );
}

class _FeedbackCategoryChip extends StatelessWidget {
  const _FeedbackCategoryChip({
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
                  color: DS.white,
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
                        context.l10n.taskFeedbackReason(action.reason),
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
    this.suffix = '',
  });

  final IconData icon;
  final Color color;
  final double value;
  final String label;
  final String suffix;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Icon(icon, color: color),
          const SizedBox(height: DS.xs),
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0, end: value),
            duration: const Duration(milliseconds: 800),
            curve: Curves.easeOutCubic,
            builder: (context, animatedValue, child) => Text(
              '${animatedValue.toStringAsFixed(animatedValue >= 10 ? 0 : 1)}$suffix',
              style: const TextStyle(fontWeight: DS.fontWeightBold, fontSize: DS.fontSizeBase),
            ),
          ),
          Text(
            label,
            style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeXs),
          ),
        ],
      );
}
