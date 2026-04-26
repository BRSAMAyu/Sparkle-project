import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/task/data/models/task_nudge.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskCreateScreen extends ConsumerStatefulWidget {
  const TaskCreateScreen({super.key});

  @override
  ConsumerState<TaskCreateScreen> createState() => _TaskCreateScreenState();
}

class _TaskCreateScreenState extends ConsumerState<TaskCreateScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _tagsController = TextEditingController();

  TaskType _selectedType = TaskType.learning;
  int _estimatedMinutes = 25;
  int _difficulty = 1;
  int _energyCost = 1;
  DateTime? _dueDate;
  bool _generateGuide = false;
  bool _isSubmitting = false;
  String? _selectedKnowledgeNodeId;

  // Intelligent Suggestions State
  Timer? _debounce;
  TaskSuggestionResponse? _suggestions;
  bool _isLoadingSuggestions = false;

  // Nudge suggestions state
  List<TaskNudge> _nudges = [];
  bool _showNudgesAfterCreation = false;
  bool _didInitQuery = false;
  String? _editingTaskId;
  String? _selectedPlanId;
  String? _selectedPlanName;
  bool _isEditMode = false;
  bool _isLoadingExistingTask = false;

  BuildContext get _feedbackContext => Navigator.of(
        context,
        rootNavigator: true,
      ).context;

  @override
  void initState() {
    super.initState();
    _titleController.addListener(_onTitleChanged);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didInitQuery) {
      return;
    }
    _didInitQuery = true;
    final queryParameters = GoRouterState.of(context).uri.queryParameters;
    final titleQueryParam = queryParameters['title'];
    final taskId = queryParameters['taskId'];
    final planId = queryParameters['planId'];
    final planName = queryParameters['planName'];
    if (titleQueryParam != null && titleQueryParam.isNotEmpty) {
      _titleController.text = titleQueryParam;
    }
    if (planId != null && planId.isNotEmpty) {
      _selectedPlanId = planId;
    }
    if (planName != null && planName.isNotEmpty) {
      _selectedPlanName = planName;
    }
    if (taskId != null && taskId.isNotEmpty) {
      _editingTaskId = taskId;
      _isEditMode = true;
      unawaited(_loadExistingTask(taskId));
    }
  }

  Future<void> _loadExistingTask(String taskId) async {
    setState(() => _isLoadingExistingTask = true);
    try {
      final task = await ref.read(taskRepositoryProvider).getTask(taskId);
      if (!mounted) {
        return;
      }
      _titleController.text = task.title;
      _selectedType = task.type;
      _estimatedMinutes = task.estimatedMinutes;
      _difficulty = task.difficulty;
      _energyCost = task.energyCost;
      _dueDate = task.dueDate;
      _tagsController.text = task.tags.join(', ');
      setState(() {});
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '加载任务失败：$e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoadingExistingTask = false);
      }
    }
  }

  void _closeAfterSubmit() {
    if (context.canPop()) {
      context.pop();
      return;
    }
    context.go(TaskRoutes.home);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _titleController
      ..removeListener(_onTitleChanged)
      ..dispose();
    _tagsController.dispose();
    super.dispose();
  }

  void _onTitleChanged() {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(
      const Duration(milliseconds: 800),
      () {
        if (_titleController.text.length > 2) {
          unawaited(_fetchSuggestions(_titleController.text));
        }
      },
    );
  }

  Future<void> _fetchSuggestions(String input) async {
    if (!mounted) return;
    setState(() => _isLoadingSuggestions = true);
    try {
      final result =
          await ref.read(taskRepositoryProvider).getSuggestions(input);
      if (mounted) {
        setState(() {
          _suggestions = result;
          _isLoadingSuggestions = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoadingSuggestions = false);
      }
    }
  }

  void _applySuggestion(SuggestedNode node) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    setState(() {
      _titleController.text = node.name;
      _selectedKnowledgeNodeId = node.id;
      // Also apply suggested tags if available and not already added
      if (_suggestions != null) {
        final currentTags =
            _tagsController.text.split(',').map((e) => e.trim()).toList();
        for (final tag in _suggestions!.suggestedTags) {
          if (!currentTags.contains(tag)) {
            if (_tagsController.text.isEmpty) {
              _tagsController.text = tag;
            } else {
              _tagsController.text += ', $tag';
            }
          }
        }
        if (_suggestions!.estimatedMinutes != null) {
          _estimatedMinutes = _suggestions!.estimatedMinutes!;
        }
        if (_suggestions!.difficulty != null) {
          _difficulty = _suggestions!.difficulty!;
        }
      }
    });
  }

  Future<void> _submitTask() async {
    if (!_formKey.currentState!.validate()) return;
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));

    setState(() {
      _isSubmitting = true;
    });

    try {
      final tags = _tagsController.text
          .split(',')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();

      if (_isEditMode && _editingTaskId != null) {
        await ref.read(taskListProvider.notifier).updateTask(
              _editingTaskId!,
              TaskUpdate(
                title: _titleController.text.trim(),
                type: _selectedType,
                estimatedMinutes: _estimatedMinutes,
                difficulty: _difficulty,
                energyCost: _energyCost,
                tags: tags,
                dueDate: _dueDate,
              ),
            );
        if (mounted) {
          AppFeedback.success(_feedbackContext, '任务已更新');
          _closeAfterSubmit();
        }
        return;
      }

      final taskCreate = TaskCreate(
        title: _titleController.text.trim(),
        type: _selectedType,
        estimatedMinutes: _estimatedMinutes,
        difficulty: _difficulty,
        energyCost: _energyCost,
        planId: _selectedPlanId,
        tags: tags,
        dueDate: _dueDate,
        knowledgeNodeId: _selectedKnowledgeNodeId,
      );

      // Use createTaskWithNudges to get behavioral suggestions
      final result =
          await ref.read(taskRepositoryProvider).createTaskWithNudges(
                taskCreate,
                generateGuide: _generateGuide,
              );

      // 🔧 修复：刷新任务列表以确保任务看板显示新任务
      await ref.read(taskListProvider.notifier).refreshTasks();

      if (mounted) {
        if (result.nudges.isNotEmpty) {
          // Show nudges instead of navigating back
          setState(() {
            _nudges = result.nudges;
            _showNudgesAfterCreation = true;
            _isSubmitting = false;
          });
          AppFeedback.info(context, context.l10n.taskCreatedWithSuggestions);
        } else {
          AppFeedback.success(_feedbackContext, context.l10n.taskCreateSuccess);
          _closeAfterSubmit();
        }
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.taskCreateFailed(e.toString()));
      }
    } finally {
      if (mounted && _nudges.isEmpty) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  void _applyNudge(TaskNudge nudge) {
    setState(() {
      if (nudge.type == 'time_adjustment' && nudge.suggestedValue != null) {
        _estimatedMinutes = nudge.suggestedValue!;
      }
      // Remove the applied nudge from the list
      _nudges = _nudges.where((n) => n != nudge).toList();
      if (_nudges.isEmpty) {
        _showNudgesAfterCreation = false;
      }
    });
    AppFeedback.success(
      context,
      context.l10n.taskNudgeApplied(nudge.title),
    );
  }

  void _dismissNudges() {
    setState(() {
      _nudges = [];
      _showNudgesAfterCreation = false;
    });
    _closeAfterSubmit();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(_isEditMode ? '编辑任务' : l10n.taskCreateTitle),
      ),
      child: ContentConstraint(
        child: _isLoadingExistingTask
            ? const Center(child: CircularProgressIndicator())
            : Form(
                key: _formKey,
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(
                    DS.spacing16,
                    DS.spacing16,
                    DS.spacing16,
                    DS.spacing24,
                  ),
                  children: [
                    if (_isEditMode) ...[
                      Container(
                        margin: const EdgeInsets.only(bottom: DS.lg),
                        padding: const EdgeInsets.all(DS.spacing12),
                        decoration: BoxDecoration(
                          color: DS.info.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: DS.info.withValues(alpha: 0.18),
                          ),
                        ),
                        child: Text(
                          '这里调整的是已有任务的安排信息，例如预计时长、难度、截止时间和标签。',
                          style:
                              TextStyle(color: DS.textSecondary, height: 1.4),
                        ),
                      ),
                    ],
                    if (_selectedPlanId != null && !_isEditMode) ...[
                      Container(
                        margin: const EdgeInsets.only(bottom: DS.lg),
                        padding: const EdgeInsets.all(DS.spacing12),
                        decoration: BoxDecoration(
                          color: DS.brandPrimary.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: DS.brandPrimary.withValues(alpha: 0.18),
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.account_tree_rounded,
                              color: DS.brandPrimaryConst,
                            ),
                            const SizedBox(width: DS.spacing10),
                            Expanded(
                              child: Text(
                                '这个任务会加入计划：${_selectedPlanName ?? _selectedPlanId}',
                                style: TextStyle(
                                  color: DS.textPrimary,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    // Title
                    TextFormField(
                      controller: _titleController,
                      decoration: InputDecoration(
                        labelText: l10n.taskTitleLabel,
                        hintText: l10n.taskTitleHint,
                        border: const OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return l10n.taskTitleRequired;
                        }
                        return null;
                      },
                    ),
                    if (_isLoadingSuggestions)
                      const Padding(
                        padding: EdgeInsets.only(top: 8.0),
                        child: LinearProgressIndicator(minHeight: 2),
                      ),
                    if (_suggestions != null &&
                        _suggestions!.suggestedNodes.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 8.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              l10n.taskSuggestedKnowledge,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 4),
                            SparkleStaggerWrap(
                              children: _suggestions!.suggestedNodes
                                  .map(
                                    (node) => ActionChip(
                                      avatar: Icon(
                                        node.isNew
                                            ? Icons.add_circle_outline
                                            : Icons.link,
                                        size: 16,
                                      ),
                                      label: Text(node.name),
                                      onPressed: () => _applySuggestion(node),
                                      tooltip: node.reason,
                                      backgroundColor: node.isNew
                                          ? DS.success.withValues(alpha: 0.1)
                                          : DS.brandPrimary
                                              .withValues(alpha: 0.1),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: DS.lg),

                    // Type Selector
                    DropdownButtonFormField<TaskType>(
                      initialValue: _selectedType,
                      decoration: InputDecoration(
                        labelText: l10n.taskTypeLabel,
                        border: const OutlineInputBorder(),
                      ),
                      items: TaskType.values
                          .map(
                            (type) => DropdownMenuItem(
                              value: type,
                              child: Row(
                                children: [
                                  Icon(getTypeIcon(type), size: 18),
                                  const SizedBox(width: DS.sm),
                                  Text(getTypeLabel(l10n, type)),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (value) {
                        if (value != null) {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            ),
                          );
                          setState(() => _selectedType = value);
                        }
                      },
                    ),
                    const SizedBox(height: DS.lg),

                    // Tags
                    TextFormField(
                      controller: _tagsController,
                      decoration: InputDecoration(
                        labelText: l10n.taskTagsLabel,
                        hintText: l10n.taskTagsHint,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.label_outline),
                      ),
                    ),
                    const SizedBox(height: DS.lg),

                    // Estimated Time & Difficulty - Responsive layout
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final isNarrow = constraints.maxWidth < 500;
                        if (isNarrow) {
                          // Narrow screen: Column layout
                          return Column(
                            children: [
                              DropdownButtonFormField<int>(
                                initialValue: _estimatedMinutes,
                                decoration: InputDecoration(
                                  labelText: l10n.taskEstimatedDurationLabel,
                                  border: const OutlineInputBorder(),
                                  prefixIcon: const Icon(Icons.timer_outlined),
                                ),
                                items: ({
                                  15,
                                  25,
                                  45,
                                  60,
                                  90,
                                  120,
                                  _estimatedMinutes,
                                }.toList()
                                      ..sort())
                                    .map(
                                      (m) => DropdownMenuItem(
                                        value: m,
                                        child: Text(l10n.taskMinutesOption(m)),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v != null) {
                                    setState(() => _estimatedMinutes = v);
                                  }
                                },
                              ),
                              const SizedBox(height: DS.lg),
                              DropdownButtonFormField<int>(
                                initialValue: _difficulty,
                                decoration: InputDecoration(
                                  labelText: l10n.taskDifficultyLabel,
                                  border: const OutlineInputBorder(),
                                  prefixIcon: const Icon(Icons.bar_chart),
                                ),
                                items: [1, 2, 3, 4, 5]
                                    .map(
                                      (l) => DropdownMenuItem(
                                        value: l,
                                        child:
                                            Text(l10n.taskDifficultyLevel(l)),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v != null) {
                                    setState(() => _difficulty = v);
                                  }
                                },
                              ),
                            ],
                          );
                        }
                        // Wide screen: Row layout
                        return Row(
                          children: [
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                initialValue: _estimatedMinutes,
                                decoration: InputDecoration(
                                  labelText: l10n.taskEstimatedDurationLabel,
                                  border: const OutlineInputBorder(),
                                  prefixIcon: const Icon(Icons.timer_outlined),
                                ),
                                items: ({
                                  15,
                                  25,
                                  45,
                                  60,
                                  90,
                                  120,
                                  _estimatedMinutes,
                                }.toList()
                                      ..sort())
                                    .map(
                                      (m) => DropdownMenuItem(
                                        value: m,
                                        child: Text(l10n.taskMinutesOption(m)),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v != null) {
                                    setState(() => _estimatedMinutes = v);
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: DS.lg),
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                initialValue: _difficulty,
                                decoration: InputDecoration(
                                  labelText: l10n.taskDifficultyLabel,
                                  border: const OutlineInputBorder(),
                                  prefixIcon: const Icon(Icons.bar_chart),
                                ),
                                items: [1, 2, 3, 4, 5]
                                    .map(
                                      (l) => DropdownMenuItem(
                                        value: l,
                                        child:
                                            Text(l10n.taskDifficultyLevel(l)),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) {
                                  if (v != null) {
                                    setState(() => _difficulty = v);
                                  }
                                },
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                    const SizedBox(height: DS.lg),

                    // Energy Cost
                    DropdownButtonFormField<int>(
                      initialValue: _energyCost,
                      decoration: InputDecoration(
                        labelText: l10n.taskEnergyCostLabel,
                        border: const OutlineInputBorder(),
                        prefixIcon: const Icon(Icons.bolt),
                      ),
                      items: [1, 2, 3, 4, 5]
                          .map(
                            (l) => DropdownMenuItem(
                              value: l,
                              child: Text(l10n.taskEnergyCostValue(l)),
                            ),
                          )
                          .toList(),
                      onChanged: (v) => setState(() => _energyCost = v!),
                    ),
                    const SizedBox(height: DS.lg),

                    // Due Date
                    ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing12,
                        vertical: DS.spacing4,
                      ),
                      title: Text(l10n.taskDeadlineLabel),
                      subtitle: Text(
                        _dueDate == null
                            ? l10n.taskDueDateUnset
                            : Formatters.formatDateShort(_dueDate!),
                      ),
                      leading: const Icon(Icons.calendar_today),
                      shape: RoundedRectangleBorder(
                        side: BorderSide(
                          color: DS.brandPrimary.withValues(alpha: 0.4),
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      onTap: () async {
                        final now = DateTime.now();
                        final initialDate =
                            _dueDate != null && _dueDate!.isAfter(now)
                                ? _dueDate!
                                : now;
                        final date = await showDatePicker(
                          context: context,
                          initialDate: initialDate,
                          firstDate: now,
                          lastDate: now.add(const Duration(days: 365)),
                        );
                        if (date != null) {
                          setState(() => _dueDate = date);
                        }
                      },
                      trailing: _dueDate != null
                          ? SparkleIconButton(
                              variant: ButtonVariant.ghost,
                              size: 32,
                              icon: const Icon(Icons.clear),
                              onPressed: () => setState(() => _dueDate = null),
                            )
                          : null,
                    ),
                    const SizedBox(height: DS.lg),

                    if (!_isEditMode)
                      SwitchListTile(
                        title: Text(l10n.taskGenerateGuideTitle),
                        subtitle: Text(l10n.taskGenerateGuideSubtitle),
                        value: _generateGuide,
                        onChanged: (v) => setState(() => _generateGuide = v),
                        secondary: const Icon(Icons.auto_awesome),
                      ),

                    // Nudge Suggestions (shown after task creation)
                    if (_showNudgesAfterCreation && _nudges.isNotEmpty) ...[
                      const SizedBox(height: DS.lg),
                      Container(
                        padding: const EdgeInsets.all(DS.md),
                        decoration: BoxDecoration(
                          color: DS.prismPurple.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: DS.prismPurple.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  Icons.lightbulb,
                                  color: DS.prismPurple,
                                  size: 20,
                                ),
                                const SizedBox(width: DS.sm),
                                Text(
                                  l10n.taskNudgeTitle,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: DS.sm),
                            ..._nudges.map(
                              (nudge) => Padding(
                                padding: const EdgeInsets.only(bottom: DS.sm),
                                child: Card(
                                  elevation: 0,
                                  color: DS.prismPurple.withValues(alpha: 0.05),
                                  child: Padding(
                                    padding: const EdgeInsets.all(DS.sm),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        LayoutBuilder(
                                          builder: (context, constraints) {
                                            final compact =
                                                constraints.maxWidth < 340;
                                            final actionButton =
                                                nudge.suggestedValue != null
                                                    ? SparkleButton(
                                                        label:
                                                            l10n.taskNudgeApply,
                                                        variant:
                                                            ButtonVariant.ghost,
                                                        onPressed: () =>
                                                            _applyNudge(nudge),
                                                      )
                                                    : null;
                                            if (compact) {
                                              return Column(
                                                crossAxisAlignment:
                                                    CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    nudge.title,
                                                    style: const TextStyle(
                                                      fontWeight:
                                                          DS.fontWeightSemibold,
                                                      fontSize: 13,
                                                    ),
                                                  ),
                                                  if (actionButton != null) ...[
                                                    const SizedBox(height: 6),
                                                    Align(
                                                      alignment:
                                                          Alignment.centerLeft,
                                                      child: actionButton,
                                                    ),
                                                  ],
                                                ],
                                              );
                                            }
                                            return Row(
                                              children: [
                                                Expanded(
                                                  child: Text(
                                                    nudge.title,
                                                    style: const TextStyle(
                                                      fontWeight:
                                                          DS.fontWeightSemibold,
                                                      fontSize: 13,
                                                    ),
                                                  ),
                                                ),
                                                if (actionButton != null)
                                                  Flexible(
                                                    child: Align(
                                                      alignment:
                                                          Alignment.centerRight,
                                                      child: actionButton,
                                                    ),
                                                  ),
                                              ],
                                            );
                                          },
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          nudge.message,
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: DS.textSecondary,
                                          ),
                                        ),
                                        if (nudge.confidence != null) ...[
                                          const SizedBox(height: 4),
                                          Text(
                                            l10n.taskNudgeConfidence(
                                              (nudge.confidence! * 100).toInt(),
                                            ),
                                            style: TextStyle(
                                              fontSize: 10,
                                              color: DS.textTertiary,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: DS.sm),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                SparkleButton(
                                  label: l10n.taskNudgeDismiss,
                                  variant: ButtonVariant.ghost,
                                  onPressed: _dismissNudges,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: DS.xxl),

                    // Submit Button
                    FilledButton.icon(
                      onPressed: _isSubmitting ? null : _submitTask,
                      icon: _isSubmitting
                          ? SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: DS.textOnPrimary,
                              ),
                            )
                          : const Icon(Icons.check),
                      label: Text(
                        _isSubmitting
                            ? (_isEditMode ? '保存中...' : l10n.taskCreating)
                            : (_isEditMode ? '保存修改' : l10n.taskCreateAction),
                      ),
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  IconData getTypeIcon(TaskType type) {
    switch (type) {
      case TaskType.learning:
        return Icons.school;
      case TaskType.training:
        return Icons.fitness_center;
      case TaskType.errorFix:
        return Icons.build;
      case TaskType.reflection:
        return Icons.psychology;
      case TaskType.social:
        return Icons.people;
      case TaskType.planning:
        return Icons.map;
      case TaskType.ocr:
        return Icons.document_scanner_outlined;
    }
  }

  String getTypeLabel(AppLocalizations l10n, TaskType type) {
    switch (type) {
      case TaskType.learning:
        return l10n.taskTypeLearning;
      case TaskType.training:
        return l10n.taskTypeTraining;
      case TaskType.errorFix:
        return l10n.taskTypeFix;
      case TaskType.reflection:
        return l10n.taskTypeReflection;
      case TaskType.social:
        return l10n.taskTypeSocial;
      case TaskType.planning:
        return l10n.taskTypePlanning;
      case TaskType.ocr:
        return l10n.taskTypeOcr;
    }
  }
}
