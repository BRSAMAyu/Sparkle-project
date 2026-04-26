import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/plan/data/models/plan_draft.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/data/services/plan_description_codec.dart';
import 'package:sparkle/features/plan/data/services/plan_guide_generator.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PlanCreateScreen extends ConsumerStatefulWidget {
  const PlanCreateScreen({
    super.key,
    this.planType,
    this.initialPlan,
    this.editingPlanId,
  });

  final String? planType;
  final PlanModel? initialPlan;
  final String? editingPlanId;

  bool get isEditMode => initialPlan != null && editingPlanId != null;

  @override
  ConsumerState<PlanCreateScreen> createState() => _PlanCreateScreenState();
}

class _PlanCreateScreenState extends ConsumerState<PlanCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _subjectController = TextEditingController();
  final _goalController = TextEditingController();
  final _scopeController = TextEditingController();
  final _taskBlueprintController = TextEditingController();
  final _guideController = TextEditingController();

  late PlanType _selectedType;
  late PlanPriority _priority;
  late PlanStage _planStage;
  late int _dailyMinutes;
  late double _totalEstimatedHours;
  late TimeOfDay _reminderTime;
  DateTime? _targetDate;
  var _scheduleLabel = '';
  var _currentStep = 0;
  var _isSubmitting = false;
  var _isGeneratingGuide = false;
  var _didInitType = false;
  var _initialTaskCount = 0;
  var _selectedGuideAudience = PlanGuideAudience.human;
  var _aiGuidePreview = '';
  final List<PlanTaskDraft> _taskDrafts = <PlanTaskDraft>[];

  bool get _isEditMode => widget.isEditMode;

  @override
  void initState() {
    super.initState();
    final initialPlan = widget.initialPlan;
    final parsed = PlanDescriptionCodec.parse(initialPlan?.description);
    _selectedType = initialPlan?.type ??
        (widget.planType == 'growth' ? PlanType.growth : PlanType.sprint);
    _priority = initialPlan?.priority ?? PlanPriority.normal;
    _planStage = initialPlan?.planStage ??
        (_selectedType == PlanType.growth ? PlanStage.daily : PlanStage.sprint);
    _dailyMinutes = initialPlan?.dailyAvailableMinutes ?? 60;
    _totalEstimatedHours = initialPlan?.totalEstimatedHours ?? 12;
    _targetDate = initialPlan?.targetDate;
    _reminderTime = _parseReminder(parsed.reminderTime);

    _nameController.text = initialPlan?.name ?? '';
    _subjectController.text = initialPlan?.subject ?? '';
    _goalController.text = parsed.overview.isNotEmpty
        ? _stripBulletPrefix(parsed.overview)
        : (initialPlan?.description ?? '');
    _scopeController.text = parsed.scope;
    _taskBlueprintController.text = _stripDraftLines(parsed.taskBlueprint);
    _guideController.text = parsed.guide;
    _scheduleLabel = _extractScheduleLabel(parsed.schedule, '');

    final planTasks = initialPlan?.tasks ?? const <TaskModel>[];
    if (planTasks.isNotEmpty) {
      _taskDrafts.addAll(
        planTasks.map(
          (task) => PlanTaskDraft(
            title: task.title,
            estimatedMinutes: task.estimatedMinutes,
            difficulty: task.difficulty,
            dueDate: task.dueDate,
            generateGuide: task.guideContent?.trim().isEmpty ?? true,
          ),
        ),
      );
    } else {
      _taskDrafts.addAll(
        parsed.taskDrafts.map(
          (title) => PlanTaskDraft(
            title: title,
            estimatedMinutes: 30,
            difficulty: 2,
          ),
        ),
      );
    }
    _initialTaskCount = _taskDrafts.length;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_scheduleLabel.isEmpty) {
      _scheduleLabel = context.l10n.planScheduleChipWeekday;
    }
    if (_didInitType || _isEditMode) {
      return;
    }
    _didInitType = true;

    final typeParam = GoRouterState.of(context).uri.queryParameters['type'];
    if (typeParam == 'growth' || typeParam == 'sprint') {
      setState(() {
        _selectedType =
            typeParam == 'growth' ? PlanType.growth : PlanType.sprint;
        _planStage = _selectedType == PlanType.growth
            ? PlanStage.daily
            : PlanStage.sprint;
        _seedSuggestedTasks(replaceExisting: _taskDrafts.isEmpty);
      });
    } else if (_taskDrafts.isEmpty) {
      _seedSuggestedTasks(replaceExisting: true);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _subjectController.dispose();
    _goalController.dispose();
    _scopeController.dispose();
    _taskBlueprintController.dispose();
    _guideController.dispose();
    super.dispose();
  }

  Future<void> _submitPlan() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final l10n = context.l10n;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
    setState(() => _isSubmitting = true);

    try {
      final draft = _buildDraft();
      final description = PlanDescriptionCodec.encode(draft);
      final planRepo = ref.read(planRepositoryProvider);
      final taskRepo = ref.read(taskRepositoryProvider);

      final persistedPlan = _isEditMode
          ? await planRepo.updatePlan(
              widget.editingPlanId!,
              PlanUpdate(
                name: draft.name,
                description: description,
                targetDate: draft.targetDate,
                dailyAvailableMinutes: draft.dailyMinutes,
                totalEstimatedHours: draft.totalEstimatedHours,
                priority: draft.priority,
                planStage: draft.planStage,
              ),
            )
          : await planRepo.createPlan(
              PlanCreate(
                name: draft.name,
                type: draft.type,
                description: description,
                targetDate: draft.targetDate,
                subject:
                    draft.subject.trim().isEmpty ? null : draft.subject.trim(),
                dailyAvailableMinutes: draft.dailyMinutes,
                totalEstimatedHours: draft.totalEstimatedHours,
                priority: draft.priority,
                planStage: draft.planStage,
              ),
            );

      final newTaskDrafts =
          _taskDrafts.skip(_isEditMode ? _initialTaskCount : 0);
      for (final taskDraft in newTaskDrafts) {
        if (taskDraft.title.trim().isEmpty) {
          continue;
        }
        await taskRepo.createTask(
          TaskCreate(
            title: taskDraft.title.trim(),
            type: TaskType.planning,
            estimatedMinutes: taskDraft.estimatedMinutes,
            difficulty: taskDraft.difficulty,
            energyCost: draft.type == PlanType.sprint ? 3 : 2,
            planId: persistedPlan.id,
            tags: <String>[
              if (draft.type == PlanType.growth)
                context.l10n.planTypeGrowth
              else
                context.l10n.planTypeSprint,
              if (draft.subject.trim().isNotEmpty) draft.subject.trim(),
            ],
            dueDate: taskDraft.dueDate,
          ),
          generateGuide: taskDraft.generateGuide,
      );

      await ref.read(planListProvider.notifier).refresh();
      await ref.read(taskListProvider.notifier).refreshTasks();
      if (!mounted) {
        return;
      }
      AppFeedback.success(
        context,
        _isEditMode ? l10n.planUpdated : l10n.planCreateSuccess,
      );
      context.go('/plans/${persistedPlan.id}');
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, e.toString());
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  PlanDraft _buildDraft() {
    final goal = _goalController.text.trim();
    return PlanDraft(
      name: _nameController.text.trim(),
      type: _selectedType,
      dailyMinutes: _dailyMinutes,
      priority: _priority,
      subject: _subjectController.text.trim(),
      goal: goal,
      totalEstimatedHours: _totalEstimatedHours,
      planStage: _planStage,
      reminderTime: _reminderTime,
      scheduleLabel: _scheduleLabel.trim(),
      scopeNotes: _scopeController.text.trim(),
      taskBlueprint: _taskBlueprintController.text.trim(),
      aiGuide: _guideController.text.trim(),
      taskDrafts: List<PlanTaskDraft>.unmodifiable(_taskDrafts),
      targetDate: _targetDate,
    );
  }

  Future<void> _pickTargetDate() async {
    final now = DateTime.now();
    final initialDate = _targetDate ?? now.add(const Duration(days: 14));
    final picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365 * 3)),
    );
    if (picked != null) {
      setState(() => _targetDate = picked);
    }
  }

  Future<void> _pickReminderTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: _reminderTime,
    );
    if (picked != null) {
      setState(() => _reminderTime = picked);
    }
  }

  Future<void> _generateGuide() async {
    if (_goalController.text.trim().isEmpty ||
        _nameController.text.trim().isEmpty) {
      AppFeedback.info(context, context.l10n.planGuideFillNameAndGoalFirst);
      return;
    }

    setState(() => _isGeneratingGuide = true);
    try {
      final content = await ref.read(planGuideGeneratorProvider).generate(
            _buildDraft(),
            audience: _selectedGuideAudience,
          );
      if (!mounted) {
        return;
      }
      setState(() {
        if (_selectedGuideAudience == PlanGuideAudience.human) {
          _guideController.text = content;
        } else {
          _aiGuidePreview = content;
        }
      });
      AppFeedback.success(
        context,
        _selectedGuideAudience == PlanGuideAudience.human
            ? context.l10n.planGuideGeneratedHuman
            : context.l10n.planGuideGeneratedAi,
      );
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.planGuideGenerationFailed(e.toString()));
      }
    } finally {
      if (mounted) {
        setState(() => _isGeneratingGuide = false);
      }
    }
  }

  void _seedSuggestedTasks({required bool replaceExisting}) {
    final l10n = context.l10n;
    final suggestions = _selectedType == PlanType.growth
        ? <PlanTaskDraft>[
            PlanTaskDraft(
              title: l10n.planSuggestedGrowthTask1,
              estimatedMinutes: 30,
              difficulty: 2,
            ),
            PlanTaskDraft(
              title: l10n.planSuggestedGrowthTask2,
              estimatedMinutes: 20,
              difficulty: 1,
            ),
          ]
        : <PlanTaskDraft>[
            PlanTaskDraft(
              title: l10n.planSuggestedSprintTask1,
              estimatedMinutes: 25,
              difficulty: 2,
            ),
            PlanTaskDraft(
              title: l10n.planSuggestedSprintTask2,
              estimatedMinutes: 45,
              difficulty: 3,
            ),
          ];
    setState(() {
      if (replaceExisting) {
        _taskDrafts
          ..clear()
          ..addAll(suggestions);
        _initialTaskCount = _isEditMode ? _initialTaskCount : 0;
      } else {
        _taskDrafts.addAll(suggestions);
      }
    });
  }

  void _addTaskDraft(PlanTaskDraft draft) {
    setState(() => _taskDrafts.add(draft));
  }

  void _removeTaskDraft(int index) {
    setState(() => _taskDrafts.removeAt(index));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final pendingTasks = ref
        .watch(taskListProvider)
        .tasks
        .where(
          (task) => task.status == TaskStatus.pending && task.planId == null,
        )
        .take(4)
        .toList();
    final draft = _buildDraft();
    final preview = PlanDescriptionCodec.encode(draft);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(
          _isEditMode
              ? (_selectedType == PlanType.growth
                  ? l10n.planCreateEditingGrowth
                  : l10n.planCreateEditingSprint)
              : (_selectedType == PlanType.growth
                  ? l10n.createGrowthPlan
                  : l10n.createSprintPlan),
        ),
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      child: ContentConstraint(
        child: Form(
          key: _formKey,
          child: Stepper(
            currentStep: _currentStep,
            onStepTapped: (value) => setState(() => _currentStep = value),
            controlsBuilder: (context, details) {
              final isLast = _currentStep == 4;
              return Padding(
                padding: const EdgeInsets.only(top: DS.spacing16),
                child: Row(
                  children: [
                    Expanded(
                      child: SparkleButton(
                        onPressed: _isSubmitting
                            ? null
                            : isLast
                                ? _submitPlan
                                : () => setState(
                                      () => _currentStep =
                                          (_currentStep + 1).clamp(0, 4),
                                    ),
                        icon: _isSubmitting
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Icon(
                                isLast
                                    ? Icons.check_rounded
                                    : Icons.arrow_forward,
                              ),
                        label: isLast ? (_isEditMode ? l10n.planCreateSavePlan : l10n.planCreateAction) : l10n.commonNext,
                        expand: true,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: SparkleButton.ghost(
                        onPressed: _currentStep == 0
                            ? () => context.pop()
                            : () => setState(
                                  () => _currentStep =
                                      (_currentStep - 1).clamp(0, 4),
                                ),
                        label: _currentStep == 0 ? l10n.commonCancel : l10n.commonPrevious,
                        expand: true,
                      ),
                    ),
                  ],
                ),
              );
            },
            steps: [
              Step(
                title: Text(l10n.planCreateStepPositioning),
                isActive: _currentStep >= 0,
                state:
                    _currentStep > 0 ? StepState.complete : StepState.indexed,
                content: _PlanBasicsStep(
                  selectedType: _selectedType,
                  priority: _priority,
                  nameController: _nameController,
                  subjectController: _subjectController,
                  goalController: _goalController,
                  onTypeChanged: (type) {
                    setState(() {
                      _selectedType = type;
                      _planStage = type == PlanType.growth
                          ? PlanStage.daily
                          : PlanStage.sprint;
                    });
                  },
                  onPriorityChanged: (priority) =>
                      setState(() => _priority = priority),
                ),
              ),
              Step(
                title: Text(l10n.planCreateStepTimeStructure),
                isActive: _currentStep >= 1,
                state:
                    _currentStep > 1 ? StepState.complete : StepState.indexed,
                content: _PlanScheduleStep(
                  dailyMinutes: _dailyMinutes,
                  totalEstimatedHours: _totalEstimatedHours,
                  targetDate: _targetDate,
                  reminderTime: _reminderTime,
                  scheduleLabel: _scheduleLabel,
                  planStage: _planStage,
                  onDailyMinutesChanged: (value) =>
                      setState(() => _dailyMinutes = value),
                  onTotalHoursChanged: (value) =>
                      setState(() => _totalEstimatedHours = value),
                  onPickTargetDate: _pickTargetDate,
                  onPickReminderTime: _pickReminderTime,
                  onScheduleChanged: (value) =>
                      setState(() => _scheduleLabel = value),
                  onPlanStageChanged: (value) =>
                      setState(() => _planStage = value),
                ),
              ),
              Step(
                title: Text(l10n.planCreateStepTaskBlueprint),
                isActive: _currentStep >= 2,
                state:
                    _currentStep > 2 ? StepState.complete : StepState.indexed,
                content: _PlanTasksStep(
                  draftTasks: _taskDrafts,
                  pendingTasks: pendingTasks,
                  blueprintController: _taskBlueprintController,
                  onAddTask: _addTaskDraft,
                  onRemoveTask: _removeTaskDraft,
                ),
              ),
              Step(
                title: Text(l10n.planCreateStepBoundariesGuide),
                isActive: _currentStep >= 3,
                state:
                    _currentStep > 3 ? StepState.complete : StepState.indexed,
                content: _PlanGuideStep(
                  scopeController: _scopeController,
                  guideController: _guideController,
                  selectedAudience: _selectedGuideAudience,
                  aiGuidePreview: _aiGuidePreview,
                  isGenerating: _isGeneratingGuide,
                  enableStage4Experience: AppFeatureFlags.enableTaskGuidanceV2,
                  onAudienceChanged: (audience) =>
                      setState(() => _selectedGuideAudience = audience),
                  onCopyAiGuide: () async {
                    if (_aiGuidePreview.trim().isEmpty) return;
                    await Clipboard.setData(
                      ClipboardData(text: _aiGuidePreview.trim()),
                    );
                    if (!context.mounted) return;
                    AppFeedback.success(context, l10n.planCreateAiGuideCopied);
                  },
                  onGenerateGuide: _generateGuide,
                ),
              ),
              Step(
                title: Text(l10n.planCreateStepReviewConfirm),
                isActive: _currentStep >= 4,
                content: _PlanReviewStep(
                  draft: draft,
                  previewDescription: preview,
                  isEditMode: _isEditMode,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static TimeOfDay _parseReminder(String? label) {
    if (label == null || !label.contains(':')) {
      return const TimeOfDay(hour: 20, minute: 0);
    }
    final parts = label.split(':');
    if (parts.length != 2) {
      return const TimeOfDay(hour: 20, minute: 0);
    }
    return TimeOfDay(
      hour: int.tryParse(parts[0]) ?? 20,
      minute: int.tryParse(parts[1]) ?? 0,
    );
  }

  static String _extractScheduleLabel(String rawSchedule, String defaultLabel) {
    final line = rawSchedule.split('\n').map((item) => item.trim()).firstWhere(
          (item) => item.startsWith('- 节奏说明：'),
          orElse: () => '',
        );
    if (line.isEmpty) {
      return defaultLabel;
    }
    return line.replaceFirst('- 节奏说明：', '').trim();
  }

  static String _stripDraftLines(String taskBlueprint) => taskBlueprint
      .split('\n')
      .where((line) => !line.trim().startsWith('- '))
      .join('\n')
      .trim();

  static String _stripBulletPrefix(String content) => content
      .split('\n')
      .where(
        (line) => line.trim().isNotEmpty && !line.trim().startsWith('- 计划类型'),
      )
      .join('\n')
      .trim();
}

class _PlanBasicsStep extends StatelessWidget {
  const _PlanBasicsStep({
    required this.selectedType,
    required this.priority,
    required this.nameController,
    required this.subjectController,
    required this.goalController,
    required this.onTypeChanged,
    required this.onPriorityChanged,
  });

  final PlanType selectedType;
  final PlanPriority priority;
  final TextEditingController nameController;
  final TextEditingController subjectController;
  final TextEditingController goalController;
  final ValueChanged<PlanType> onTypeChanged;
  final ValueChanged<PlanPriority> onPriorityChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.planCreateBasicsSubtitle,
            style: DS.bodyMedium.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          SegmentedButton<PlanType>(
            segments: [
              ButtonSegment(
                value: PlanType.sprint,
                label: Text(l10n.planTypeSprint),
                icon: const Icon(Icons.flash_on_rounded),
              ),
              ButtonSegment(
                value: PlanType.growth,
                label: Text(l10n.planTypeGrowth),
                icon: const Icon(Icons.trending_up_rounded),
              ),
            ],
            selected: {selectedType},
            onSelectionChanged: (values) => onTypeChanged(values.first),
          ),
          const SizedBox(height: DS.spacing16),
          TextFormField(
            controller: nameController,
            decoration: InputDecoration(
              labelText: l10n.planNameLabel,
              hintText: l10n.planCreateNameHint,
              border: const OutlineInputBorder(),
            ),
            validator: (value) =>
                (value == null || value.trim().isEmpty) ? l10n.planNameRequired : null,
          ),
          const SizedBox(height: DS.spacing16),
          TextFormField(
            controller: subjectController,
            decoration: InputDecoration(
              labelText: l10n.planCreateSubjectLabel,
              hintText: l10n.planCreateSubjectHint,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          TextFormField(
            controller: goalController,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: selectedType == PlanType.growth ? l10n.planCreateGrowthGoalLabel : l10n.planCreateSprintGoalLabel,
              hintText: selectedType == PlanType.growth
                  ? l10n.planCreateGrowthGoalHint
                  : l10n.planCreateSprintGoalHint,
              border: const OutlineInputBorder(),
            ),
            validator: (value) =>
                (value == null || value.trim().isEmpty) ? l10n.planCreateGoalRequired : null,
          ),
          const SizedBox(height: DS.spacing16),
          DropdownButtonFormField<PlanPriority>(
            initialValue: priority,
            decoration: InputDecoration(
              labelText: l10n.planPriorityLabel,
              border: OutlineInputBorder(),
            ),
            items: [
              DropdownMenuItem(value: PlanPriority.low, child: Text(l10n.planPriorityLow)),
              DropdownMenuItem(value: PlanPriority.normal, child: Text(l10n.planPriorityNormal)),
              DropdownMenuItem(value: PlanPriority.high, child: Text(l10n.planPriorityHigh)),
              DropdownMenuItem(value: PlanPriority.critical, child: Text(l10n.planPriorityCritical)),
            ],
            onChanged: (value) {
              if (value != null) {
                onPriorityChanged(value);
              }
            },
          ),
        ],
      );
  }
}

class _PlanScheduleStep extends StatelessWidget {
  const _PlanScheduleStep({
    required this.dailyMinutes,
    required this.totalEstimatedHours,
    required this.targetDate,
    required this.reminderTime,
    required this.scheduleLabel,
    required this.planStage,
    required this.onDailyMinutesChanged,
    required this.onTotalHoursChanged,
    required this.onPickTargetDate,
    required this.onPickReminderTime,
    required this.onScheduleChanged,
    required this.onPlanStageChanged,
  });

  final int dailyMinutes;
  final double totalEstimatedHours;
  final DateTime? targetDate;
  final TimeOfDay reminderTime;
  final String scheduleLabel;
  final PlanStage planStage;
  final ValueChanged<int> onDailyMinutesChanged;
  final ValueChanged<double> onTotalHoursChanged;
  final VoidCallback onPickTargetDate;
  final VoidCallback onPickReminderTime;
  final ValueChanged<String> onScheduleChanged;
  final ValueChanged<PlanStage> onPlanStageChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final reminderLabel =
        '${reminderTime.hour.toString().padLeft(2, '0')}:${reminderTime.minute.toString().padLeft(2, '0')}';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.planCreateScheduleSubtitle,
          style: DS.bodyMedium.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        DropdownButtonFormField<int>(
          initialValue: dailyMinutes,
          decoration: InputDecoration(
            labelText: l10n.planCreateDailyMinutesLabel,
            border: OutlineInputBorder(),
          ),
          items: [20, 30, 45, 60, 90, 120, 180]
              .map(
                (item) => DropdownMenuItem(
                  value: item,
                  child: Text(l10n.planCreateMinutes(item.toString())),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) {
              onDailyMinutesChanged(value);
            }
          },
        ),
        const SizedBox(height: DS.spacing16),
        Text(
          l10n.planCreateTotalEstimatedHours(totalEstimatedHours.toStringAsFixed(1)),
          style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightSemibold),
        ),
        Slider(
          value: totalEstimatedHours.clamp(4, 80),
          min: 4,
          max: 80,
          divisions: 38,
          label: totalEstimatedHours.toStringAsFixed(1),
          onChanged: onTotalHoursChanged,
        ),
        const SizedBox(height: DS.spacing8),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.calendar_month_rounded),
          title: Text(l10n.planTargetDateLabel),
          subtitle: Text(
            targetDate == null
                ? l10n.planTargetDateUnset
                : Formatters.formatDateMedium(targetDate!),
          ),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: onPickTargetDate,
        ),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.notifications_active_outlined),
          title: Text(l10n.planCreateDailyReminderTime),
          subtitle: Text(reminderLabel),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: onPickReminderTime,
        ),
        const SizedBox(height: DS.spacing12),
        DropdownButtonFormField<PlanStage>(
          initialValue: planStage,
          decoration: InputDecoration(
            labelText: l10n.planCreatePlanStageLabel,
            border: OutlineInputBorder(),
          ),
          items: [
            DropdownMenuItem(value: PlanStage.sprint, child: Text(l10n.planCreateStageSprint)),
            DropdownMenuItem(value: PlanStage.daily, child: Text(l10n.planCreateStageDaily)),
            DropdownMenuItem(value: PlanStage.review, child: Text(l10n.planCreateStageReview)),
            DropdownMenuItem(value: PlanStage.paused, child: Text(l10n.planCreateStagePaused)),
          ],
          onChanged: (value) {
            if (value != null) {
              onPlanStageChanged(value);
            }
          },
        ),
        const SizedBox(height: DS.spacing16),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            _ScheduleChip(label: l10n.planCreateScheduleChipWorkday),
            _ScheduleChip(label: l10n.planCreateScheduleChipMorning),
            _ScheduleChip(label: l10n.planCreateScheduleChipAfternoon),
          ],
        ),
        const SizedBox(height: DS.spacing12),
        TextFormField(
          initialValue: scheduleLabel,
          maxLines: 2,
          decoration: InputDecoration(
            labelText: l10n.planCreateScheduleLabel,
            hintText: l10n.planCreateScheduleHint,
            border: OutlineInputBorder(),
          ),
          onChanged: onScheduleChanged,
        ),
      ],
    );
  }
}

class _ScheduleChip extends StatelessWidget {
  const _ScheduleChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: DS.bodySmall.copyWith(color: DS.textSecondary),
        ),
      );
}

class _PlanTasksStep extends StatefulWidget {
  const _PlanTasksStep({
    required this.draftTasks,
    required this.pendingTasks,
    required this.blueprintController,
    required this.onAddTask,
    required this.onRemoveTask,
  });

  final List<PlanTaskDraft> draftTasks;
  final List<TaskModel> pendingTasks;
  final TextEditingController blueprintController;
  final ValueChanged<PlanTaskDraft> onAddTask;
  final ValueChanged<int> onRemoveTask;

  @override
  State<_PlanTasksStep> createState() => _PlanTasksStepState();
}

class _PlanTasksStepState extends State<_PlanTasksStep> {
  final _titleController = TextEditingController();
  var _minutes = 30;
  var _difficulty = 2;

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  void _appendManualTask() {
    final title = _titleController.text.trim();
    if (title.isEmpty) {
      return;
    }
    widget.onAddTask(
      PlanTaskDraft(
        title: title,
        estimatedMinutes: _minutes,
        difficulty: _difficulty,
      ),
    );
    _titleController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.planCreateTasksSubtitle,
            style: DS.bodyMedium.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          TextFormField(
            controller: widget.blueprintController,
            maxLines: 3,
            decoration: InputDecoration(
              labelText: l10n.planCreateTaskBlueprintLabel,
              hintText: l10n.planCreateTaskBlueprintHint,
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          if (widget.pendingTasks.isNotEmpty) ...[
            Text(
              l10n.planCreateReferenceExistingTasks,
              style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold),
            ),
            const SizedBox(height: DS.spacing8),
            ...widget.pendingTasks.map(
              (task) => Card(
                margin: const EdgeInsets.only(bottom: DS.spacing8),
                child: ListTile(
                  title: Text(task.title),
                  subtitle: Text(
                    l10n.planCreateTaskSubtitle(task.estimatedMinutes.toString(), task.difficulty.toString()),
                  ),
                  trailing: TextButton(
                    onPressed: () => widget.onAddTask(
                      PlanTaskDraft(
                        title: task.title,
                        estimatedMinutes: task.estimatedMinutes,
                        difficulty: task.difficulty,
                        dueDate: task.dueDate,
                        generateGuide:
                            task.guideContent?.trim().isEmpty ?? true,
                      ),
                    ),
                    child: Text(l10n.planCreateCopyToPlan),
                  ),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing12),
          ],
          Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfacePanel,
              borderRadius: DS.borderRadius16,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Column(
              children: [
                TextFormField(
                  controller: _titleController,
                  decoration: InputDecoration(
                    labelText: l10n.planCreateNewTaskLabel,
                    hintText: l10n.planCreateNewTaskHint,
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: _minutes,
                        decoration: InputDecoration(
                          labelText: l10n.planCreateDurationLabel,
                          border: OutlineInputBorder(),
                        ),
                        items: const [20, 30, 45, 60, 90]
                            .map(
                              (value) => DropdownMenuItem(
                                value: value,
                                child: Text(l10n.planCreateMinutes(value.toString())),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          if (value != null) {
                            setState(() => _minutes = value);
                          }
                        },
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: _difficulty,
                        decoration: InputDecoration(
                          labelText: l10n.planCreateDifficultyLabel,
                          border: OutlineInputBorder(),
                        ),
                        items: const [1, 2, 3, 4, 5]
                            .map(
                              (value) => DropdownMenuItem(
                                value: value,
                                child: Text('$value'),
                              ),
                            )
                            .toList(),
                        onChanged: (value) {
                          if (value != null) {
                            setState(() => _difficulty = value);
                          }
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),
                Align(
                  alignment: Alignment.centerRight,
                  child: SparkleButton.ghost(
                    onPressed: _appendManualTask,
                    label: l10n.planCreateAddTaskToPlan,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          if (widget.draftTasks.isEmpty)
            Text(
              l10n.planCreateNoTasks,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...widget.draftTasks.asMap().entries.map(
                  (entry) => Card(
                    margin: const EdgeInsets.only(bottom: DS.spacing8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor:
                            DS.brandPrimary.withValues(alpha: 0.12),
                        child: Text('${entry.key + 1}'),
                      ),
                      title: Text(entry.value.title),
                      subtitle: Text(
                        l10n.planCreateTaskSubtitle(entry.value.estimatedMinutes.toString(), entry.value.difficulty.toString()),
                      ),
                      trailing: IconButton(
                        onPressed: () => widget.onRemoveTask(entry.key),
                        icon: const Icon(Icons.delete_outline_rounded),
                      ),
                    ),
                  ),
                ),
        ],
        );
  }
}

class _PlanGuideStep extends StatelessWidget {
  const _PlanGuideStep({
    required this.scopeController,
    required this.guideController,
    required this.selectedAudience,
    required this.aiGuidePreview,
    required this.isGenerating,
    required this.enableStage4Experience,
    required this.onAudienceChanged,
    required this.onCopyAiGuide,
    required this.onGenerateGuide,
  });

  final TextEditingController scopeController;
  final TextEditingController guideController;
  final PlanGuideAudience selectedAudience;
  final String aiGuidePreview;
  final bool isGenerating;
  final bool enableStage4Experience;
  final ValueChanged<PlanGuideAudience> onAudienceChanged;
  final VoidCallback onCopyAiGuide;
  final VoidCallback onGenerateGuide;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final isHuman = selectedAudience == PlanGuideAudience.human;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: scopeController,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: l10n.planCreateScopeLabel,
            hintText: l10n.planCreateScopeHint,
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: DS.spacing16),
        if (enableStage4Experience) ...[
          Text(
            l10n.planCreateGuidePerspective,
            style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: DS.spacing8),
          SegmentedButton<PlanGuideAudience>(
            segments: [
              ButtonSegment(
                value: PlanGuideAudience.human,
                label: Text(l10n.planCreateGuideForSelf),
                icon: const Icon(Icons.person_outline_rounded),
              ),
              ButtonSegment(
                value: PlanGuideAudience.ai,
                label: Text(l10n.planCreateGuideForAi),
                icon: const Icon(Icons.auto_awesome_rounded),
              ),
            ],
            selected: {selectedAudience},
            onSelectionChanged: (selection) =>
                onAudienceChanged(selection.first),
          ),
          const SizedBox(height: DS.spacing12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Text(
              isHuman
                  ? l10n.planCreateGuideHumanDescription
                  : l10n.planCreateGuideAiDescription,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
        ],
        Row(
          children: [
            Expanded(
              child: Text(
                isHuman || !enableStage4Experience ? l10n.planCreateGuideHumanTitle : l10n.planCreateGuideAiTitle,
                style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold),
              ),
            ),
            SparkleButton(
              onPressed: isGenerating ? null : onGenerateGuide,
              variant: ButtonVariant.ghost,
              disabled: isGenerating,
              icon: isGenerating
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(
                      isHuman || !enableStage4Experience
                          ? Icons.auto_awesome_rounded
                          : Icons.smart_toy_outlined,
                    ),
              label: isGenerating
                  ? l10n.generating
                  : (isHuman || !enableStage4Experience ? l10n.planCreateGenerateHumanGuide : l10n.planCreateGenerateAiGuide),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        if (isHuman || !enableStage4Experience)
          TextFormField(
            controller: guideController,
            maxLines: 12,
            decoration: InputDecoration(
              hintText: l10n.planCreateGuideHint,
              border: OutlineInputBorder(),
            ),
          )
        else
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.neutral50,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  aiGuidePreview.trim().isEmpty
                      ? l10n.planCreateAiGuideEmpty
                      : aiGuidePreview.trim(),
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    fontFamily:
                        aiGuidePreview.trim().isEmpty ? null : 'monospace',
                    height: 1.55,
                  ),
                ),
                if (aiGuidePreview.trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing12),
                  SparkleButton.ghost(
                    onPressed: onCopyAiGuide,
                    icon: const Icon(Icons.copy_all_rounded),
                    label: l10n.planCreateCopyAiGuide,
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }
}

class _PlanReviewStep extends StatelessWidget {
  const _PlanReviewStep({
    required this.draft,
    required this.previewDescription,
    required this.isEditMode,
  });

  final PlanDraft draft;
  final String previewDescription;
  final bool isEditMode;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.08),
              borderRadius: DS.borderRadius16,
              border:
                  Border.all(color: DS.brandPrimary.withValues(alpha: 0.14)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  draft.name,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  l10n.planCreateReviewSummary(
                    draft.type == PlanType.growth ? l10n.planTypeGrowth : l10n.planTypeSprint,
                    draft.dailyMinutes.toString(),
                    draft.totalEstimatedHours.toStringAsFixed(1),
                  ),
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  draft.goal,
                  style: DS.bodyMedium.copyWith(height: 1.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            isEditMode
                ? l10n.planCreateReviewEditDescription
                : l10n.planCreateReviewCreateDescription,
            style: DS.bodyMedium.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            l10n.planCreateFinalDescription,
            style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: DS.spacing8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: DS.surfacePanel,
              borderRadius: DS.borderRadius16,
              border: Border.all(color: DS.borderSubtle),
            ),
            child: SelectableText(
              previewDescription,
              style: DS.bodySmall.copyWith(height: 1.6),
            ),
          ),
        ],
      );
}
