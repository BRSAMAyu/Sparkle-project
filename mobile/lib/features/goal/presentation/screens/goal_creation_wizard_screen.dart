import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/goal/data/models/goal_creation_models.dart';
import 'package:sparkle/features/goal/data/models/goal_intent_models.dart';
import 'package:sparkle/features/goal/data/models/scenario_pack_models.dart';
import 'package:sparkle/features/goal/data/repositories/goal_repository.dart';
import 'package:sparkle/features/goal/data/services/goal_intent_service.dart';
import 'package:sparkle/features/goal/data/services/scenario_pack_service.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_intent_input.dart';
import 'package:sparkle/features/goal/presentation/widgets/goal_created_dialog.dart';
import 'package:sparkle/features/goal/presentation/widgets/intent_confirmation_card.dart';

class GoalCreationWizardScreen extends ConsumerStatefulWidget {
  const GoalCreationWizardScreen({
    this.onCreated,
    super.key,
  });

  final ValueChanged<CreatedGoal>? onCreated;

  @override
  ConsumerState<GoalCreationWizardScreen> createState() =>
      _GoalCreationWizardScreenState();
}

class _GoalCreationWizardScreenState
    extends ConsumerState<GoalCreationWizardScreen> {
  final _titleController = TextEditingController();
  final _motivationController = TextEditingController();
  final _descriptionController = TextEditingController();
  // Phase-1 Entry Wire — first-minute intent input owned by the wizard so the
  // input's text persists if the user backs into intent step from later steps.
  final _intentController = TextEditingController();

  int _step = 0;
  String _goalType = 'academic';
  String _timeHorizon = 'short';
  bool _loadingPreview = false;
  bool _creating = false;
  String? _error;
  GoalDecompositionPreview? _preview;
  List<GoalMilestoneDraft> _milestones = const [];

  // Phase-1 Entry Wire state. When [_intentAnalysis] is non-null and not
  // disabled the wizard renders the IntentConfirmationCard at step 0; the
  // user can then choose a suggested action (skip ahead) or pick a
  // correction option (drop into the legacy 5-step flow).
  bool _analyzingIntent = false;
  GoalIntentAnalysis? _intentAnalysis;

  // Matching scenario pack for the selected goal type.
  ScenarioPackSummary? _matchedPack;

  @override
  void initState() {
    super.initState();
    // N-7 UX 旁路：底部继续键要跟随意图输入文本实时点亮/熄灭。
    _intentController.addListener(_onIntentTextChanged);
  }

  void _onIntentTextChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _intentController
      ..removeListener(_onIntentTextChanged)
      ..dispose();
    _titleController.dispose();
    _motivationController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final titles = [
      l10n.goalWizardStepType,
      l10n.goalWizardStepMotivation,
      l10n.goalWizardStepTimeline,
      l10n.goalWizardStepMilestones,
      l10n.goalWizardStepConfirm,
    ];
    final currentStepLabel = titles[_step];

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.goalWizardTitle),
      ),
      body: SafeArea(
        child: Semantics(
          container: true,
          explicitChildNodes: true,
          label: l10n.goalWizardAccessibility(
            (_step + 1).toString(),
            titles.length.toString(),
            currentStepLabel,
          ),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
            children: [
              _WizardProgress(step: _step, titles: titles),
              const SizedBox(height: 18),
              if (_error != null) ...[
                _ErrorBanner(
                    message: _error!,
                    onClose: () => setState(() => _error = null)),
                const SizedBox(height: 14),
              ],
              Semantics(
                container: true,
                label: currentStepLabel,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 180),
                  child: _buildStep(context),
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
          child: Row(
            children: [
              if (_step > 0)
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _creating ? null : () => setState(() => _step--),
                    icon: const Icon(Icons.arrow_back_rounded,
                        semanticLabel: 'Back'),
                    label: Text(l10n.goalWizardBack),
                  ),
                ),
              if (_step > 0) const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  onPressed:
                      _primaryActionEnabled ? () => unawaited(_next()) : null,
                  icon: _creating || _loadingPreview
                      ? LoadingIndicator.circular(
                          size: 16,
                          color: DS.neutral0,
                        )
                      : Icon(
                          _step == 4
                              ? Icons.check_rounded
                              : Icons.arrow_forward_rounded,
                          semanticLabel: _step == 4
                              ? l10n.goalWizardCreate
                              : l10n.goalWizardContinue),
                  label: Text(
                      _step == 4 ? l10n.goalWizardCreate : l10n.goalWizardContinue),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool get _primaryActionEnabled {
    if (_loadingPreview || _creating || _analyzingIntent) return false;
    // Phase-1 Entry Wire，N-7 UX 旁路：第 0 步意图输入未提交时，底部继续键
    // 在文本非空时点亮，点击复用输入卡内提交的同一分析路径（不再强制
    // 用户去点输入卡内的按钮）；空文本保持禁用。确认卡（actionable）
    // 展示时仍由卡内 chips/action rows 主导，底部键保持禁用。
    if (_step == 0 && _intentAnalysis == null) {
      return _intentController.text.trim().isNotEmpty;
    }
    if (_step == 0 &&
        _intentAnalysis != null &&
        _intentAnalysis!.isActionable) {
      return false;
    }
    if (_step == 1) {
      return _titleController.text.trim().isNotEmpty &&
          _motivationController.text.trim().isNotEmpty;
    }
    if (_step == 3) return _milestones.isNotEmpty;
    return true;
  }

  Widget _buildStep(BuildContext context) {
    switch (_step) {
      case 0:
        // Phase-1 Entry Wire: surface the intent input/card if the user
        // hasn't yet picked a path. The legacy type chooser is preserved as
        // the fallback when the user explicitly says "都不对，我解释一下"
        // or when the kill switch is off (server returns mode="disabled").
        if (_intentAnalysis == null) {
          return GoalIntentInput(
            key: const ValueKey('goal-intent-input-step'),
            controller: _intentController,
            analyzing: _analyzingIntent,
            onSubmit: _runIntentAnalysis,
          );
        }
        if (_intentAnalysis!.isActionable) {
          return IntentConfirmationCard(
            key: const ValueKey('goal-intent-confirm-step'),
            analysis: _intentAnalysis!,
            onCorrectionSelected: _onIntentCorrection,
            onSuggestedActionTapped: _onIntentSuggestedAction,
          );
        }
        // mode=disabled or non-actionable → fall back to legacy chooser.
        return _GoalTypeStep(
          key: const ValueKey('goal-type-step'),
          selected: _goalType,
          onSelected: (value) {
            setState(() => _goalType = value);
            unawaited(_loadMatchedPack());
          },
        );
      case 1:
        return _GoalMotivationStep(
          key: const ValueKey('goal-motivation-step'),
          titleController: _titleController,
          motivationController: _motivationController,
          descriptionController: _descriptionController,
          onChanged: () => setState(() {}),
        );
      case 2:
        return _TimeHorizonStep(
          key: const ValueKey('goal-time-step'),
          selected: _timeHorizon,
          onSelected: (value) => setState(() => _timeHorizon = value),
        );
      case 3:
        return _MilestoneEditorStep(
          key: const ValueKey('goal-milestone-step'),
          loading: _loadingPreview,
          preview: _preview,
          milestones: _milestones,
          onChanged: _replaceMilestone,
          onReload: () => unawaited(_loadPreview(force: true)),
        );
      default:
        return _GoalConfirmStep(
          key: const ValueKey('goal-confirm-step'),
          goalType: _goalType,
          title: _titleController.text.trim(),
          motivation: _motivationController.text.trim(),
          timeHorizon: _timeHorizon,
          milestones: _milestones,
          matchedPack: _matchedPack,
        );
    }
  }

  Future<void> _next() async {
    // N-7 UX 旁路：第 0 步意图输入未提交时，底部继续键复用输入卡内
    // 提交的同一分析路径（_runIntentAnalysis），不跳步。
    if (_step == 0 && _intentAnalysis == null) {
      await _runIntentAnalysis();
      return;
    }
    if (_step == 2) {
      await _loadPreview();
      if (!mounted || _preview == null) return;
      setState(() => _step = 3);
      return;
    }
    if (_step == 4) {
      await _createGoal();
      return;
    }
    setState(() => _step++);
  }

  Future<void> _loadMatchedPack() async {
    try {
      final packs = await ref.read(scenarioPackServiceProvider).listPacks();
      if (!mounted) return;
      final backendType = ApiGoalRepository.resolveType(_goalType);
      final match = packs.where((p) => p.goalType == backendType).toList();
      setState(() {
        _matchedPack = match.isNotEmpty ? match.first : null;
      });
    } catch (_) {
      // Silently ignore — pack match is optional
    }
  }

  // ── Phase-1 Entry Wire helpers ────────────────────────────────────

  Future<void> _runIntentAnalysis() async {
    final text = _intentController.text.trim();
    if (text.isEmpty || _analyzingIntent) return;
    setState(() {
      _analyzingIntent = true;
      _error = null;
    });
    final analysis = await ref.read(goalIntentServiceProvider).analyze(text);
    if (!mounted) return;
    if (analysis.isDisabled || !analysis.isActionable) {
      // Kill switch off, server didn't recognise the intent, or transport
      // failed — fall back to legacy wizard. We seed the title/motivation
      // from whatever the user typed so they don't have to re-enter it.
      _seedLegacyFromIntentText(text);
      setState(() {
        _intentAnalysis = analysis; // memoise so we don't re-call on rebuild
        _analyzingIntent = false;
      });
      return;
    }
    // Pre-fill the legacy fields from the analyzer so that if the user
    // later clicks "Continue" through legacy steps, they don't restart
    // from scratch.
    _seedLegacyFromAnalysis(text, analysis);
    setState(() {
      _intentAnalysis = analysis;
      _analyzingIntent = false;
    });
  }

  void _seedLegacyFromIntentText(String text) {
    if (_titleController.text.trim().isEmpty) {
      _titleController.text = text.length > 80 ? text.substring(0, 80) : text;
    }
    if (_motivationController.text.trim().isEmpty) {
      _motivationController.text = text;
    }
  }

  void _seedLegacyFromAnalysis(String text, GoalIntentAnalysis analysis) {
    _seedLegacyFromIntentText(text);
    _goalType = analysis.inferredGoalType;
    _timeHorizon = analysis.inferredTimeHorizon;
  }

  void _onIntentCorrection(GoalIntentCorrectionOption option) {
    setState(() {
      switch (option.key) {
        case 'confirm':
          // User confirmed the judgement → jump to motivation step where
          // they can refine title/motivation. Title was pre-seeded above.
          _step = 1;
        case 'adjust_high_score':
          _goalType = 'academic';
          _timeHorizon = 'short';
          _step = 1;
        case 'not_exam':
          _intentAnalysis = null; // back to legacy chooser
          _goalType = 'skill';
        case 'explain_self':
        default:
          _intentAnalysis = null;
      }
    });
  }

  void _onIntentSuggestedAction(GoalIntentSuggestedAction action) {
    // For Phase-1 we keep this simple: tapping a suggested action confirms
    // the analysis and skips ahead to milestones (step 3) so the user
    // sees a concrete plan without having to re-fill the form.
    // The actual "first task" creation is wired in Phase-2 once the
    // backend `create_with_intent` orchestrator lands.
    setState(() {
      _step = 3;
    });
    unawaited(_loadPreview());
  }

  Future<void> _loadPreview({bool force = false}) async {
    if (_preview != null && !force) return;
    setState(() {
      _loadingPreview = true;
      _error = null;
    });
    try {
      final preview = await ref.read(goalRepositoryProvider).decomposePreview(
            goalType: _goalType,
            title: _titleController.text.trim(),
            motivation: _motivationController.text.trim(),
            timeHorizon: _timeHorizon,
          );
      if (!mounted) return;
      setState(() {
        _preview = preview;
        _milestones = preview.milestones;
        _loadingPreview = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loadingPreview = false;
        _error = context.l10n.goalWizardDecomposeFailed;
      });
    }
  }

  Future<void> _createGoal() async {
    setState(() {
      _creating = true;
      _error = null;
    });
    try {
      final created = await ref.read(goalRepositoryProvider).createGoal(
            goalType: _goalType,
            title: _titleController.text.trim(),
            motivation: _motivationController.text.trim(),
            timeHorizon: _timeHorizon,
            description: _descriptionController.text.trim(),
            milestones: _milestones,
          );
      if (!mounted) return;
      widget.onCreated?.call(created);
      if (widget.onCreated != null) {
        setState(() => _creating = false);
        AppFeedback.success(context, context.l10n.goalWizardGoalCreated);
        return;
      }
      setState(() => _creating = false);
      final router = GoRouter.maybeOf(context);
      if (router != null) {
        final firstMilestone = _milestones.isNotEmpty
            ? _milestones.first.title
            : context.l10n.goalWizardGettingStarted;
        final packDuration = _matchedPack != null
            ? context.l10n.goalWizardDaysLabel(_matchedPack!.horizonDays.toString())
            : null;
        unawaited(
          SparkleGoalCreatedDialog.show(
            context,
            goalName: _titleController.text.trim(),
            firstMilestone: firstMilestone,
            packName: _matchedPack?.name,
            packDurationLabel: packDuration,
            onSeePlan: () {
              router.go('/goals/${Uri.encodeComponent(created.id)}');
            },
            onStartFirstTask: () {
              if (created.firstTaskId != null) {
                router.go(
                  '/tasks/${Uri.encodeComponent(created.firstTaskId!)}/execute',
                );
              } else {
                router.go('/goals/${Uri.encodeComponent(created.id)}');
              }
            },
          ),
        );
      } else {
        AppFeedback.success(context, context.l10n.goalWizardGoalCreated);
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _creating = false;
        _error = context.l10n.goalWizardCreateFailed;
      });
    }
  }

  void _replaceMilestone(int index, GoalMilestoneDraft milestone) {
    final next = [..._milestones];
    next[index] = milestone;
    setState(() => _milestones = next);
  }
}

class _WizardProgress extends StatelessWidget {
  const _WizardProgress({required this.step, required this.titles});

  final int step;
  final List<String> titles;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Semantics(
      container: true,
      label: l10n.goalWizardProgress(
        (step + 1).toString(),
        titles.length.toString(),
      ),
      child: Row(
        children: [
          for (var index = 0; index < titles.length; index++) ...[
            Expanded(
              child: Column(
                children: [
                  Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color:
                          index <= step ? DS.brandPrimary : DS.surfaceTertiary,
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    titles[index],
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
            if (index != titles.length - 1) const SizedBox(width: 5),
          ],
        ],
      ),
    );
  }
}

class _GoalTypeStep extends StatelessWidget {
  const _GoalTypeStep({
    required this.selected,
    required this.onSelected,
    super.key,
  });

  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final items = [
      ('academic', Icons.school_outlined, l10n.goalWizardTypeAcademic),
      ('skill', Icons.psychology_outlined, l10n.goalWizardTypeSkill),
      ('habit', Icons.repeat_rounded, l10n.goalWizardTypeHabit),
      ('project', Icons.rocket_launch_outlined, l10n.goalWizardTypeProject),
      ('other', Icons.more_horiz_rounded, l10n.goalWizardTypeOther),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final item in items)
          ChoiceChip(
            selected: selected == item.$1,
            avatar: Icon(item.$2, size: 18),
            label: Text(item.$3),
            onSelected: (_) => onSelected(item.$1),
          ),
      ],
    );
  }
}

class _GoalMotivationStep extends StatelessWidget {
  const _GoalMotivationStep({
    required this.titleController,
    required this.motivationController,
    required this.descriptionController,
    required this.onChanged,
    super.key,
  });

  final TextEditingController titleController;
  final TextEditingController motivationController;
  final TextEditingController descriptionController;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      children: [
        TextField(
          controller: titleController,
          onChanged: (_) => onChanged(),
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            labelText: l10n.goalWizardTitleLabel,
            prefixIcon: const Icon(Icons.flag_outlined),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: motivationController,
          onChanged: (_) => onChanged(),
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: l10n.goalWizardWhyLabel,
            prefixIcon: const Icon(Icons.favorite_border_rounded),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: descriptionController,
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: l10n.goalWizardDescriptionLabel,
            prefixIcon: const Icon(Icons.notes_outlined),
          ),
        ),
      ],
    );
  }
}

class _TimeHorizonStep extends StatelessWidget {
  const _TimeHorizonStep({
    required this.selected,
    required this.onSelected,
    super.key,
  });

  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SegmentedButton<String>(
      segments: [
        ButtonSegment(
          value: 'short',
          icon: const Icon(Icons.calendar_view_week_outlined),
          label: Text(l10n.goalWizardShortTerm),
        ),
        ButtonSegment(
          value: 'medium',
          icon: const Icon(Icons.calendar_month_outlined),
          label: Text(l10n.goalWizardMediumTerm),
        ),
        ButtonSegment(
          value: 'long',
          icon: const Icon(Icons.timeline_rounded),
          label: Text(l10n.goalWizardLongTerm),
        ),
      ],
      selected: {selected},
      onSelectionChanged: (values) => onSelected(values.first),
    );
  }
}

class _MilestoneEditorStep extends StatelessWidget {
  const _MilestoneEditorStep({
    required this.loading,
    required this.preview,
    required this.milestones,
    required this.onChanged,
    required this.onReload,
    super.key,
  });

  final bool loading;
  final GoalDecompositionPreview? preview;
  final List<GoalMilestoneDraft> milestones;
  final void Function(int index, GoalMilestoneDraft milestone) onChanged;
  final VoidCallback onReload;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (loading) return const LinearProgressIndicator(minHeight: 4);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (preview != null) ...[
          Text(
            preview!.rationale,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: 12),
        ],
        for (var index = 0; index < milestones.length; index++) ...[
          _MilestoneEditorCard(
            milestone: milestones[index],
            index: index,
            onChanged: (milestone) => onChanged(index, milestone),
          ),
          const SizedBox(height: 12),
        ],
        TextButton.icon(
          onPressed: onReload,
          icon: const Icon(Icons.refresh_rounded),
          label: Text(l10n.goalWizardRegenerate),
        ),
      ],
    );
  }
}

class _MilestoneEditorCard extends StatelessWidget {
  const _MilestoneEditorCard({
    required this.milestone,
    required this.index,
    required this.onChanged,
  });

  final GoalMilestoneDraft milestone;
  final int index;
  final ValueChanged<GoalMilestoneDraft> onChanged;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            TextFormField(
              initialValue: milestone.title,
              decoration: InputDecoration(
                labelText: l10n.goalWizardMilestoneLabel((index + 1).toString()),
                prefixIcon: const Icon(Icons.route_outlined),
              ),
              onChanged: (value) => onChanged(milestone.copyWith(title: value)),
            ),
            const SizedBox(height: 10),
            TextFormField(
              initialValue: milestone.description,
              minLines: 2,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: l10n.goalWizardOutcomeLabel,
                prefixIcon: const Icon(Icons.edit_note_rounded),
              ),
              onChanged: (value) =>
                  onChanged(milestone.copyWith(description: value)),
            ),
          ],
        ),
      ),
    );
  }
}

class _GoalConfirmStep extends StatelessWidget {
  const _GoalConfirmStep({
    required this.goalType,
    required this.title,
    required this.motivation,
    required this.timeHorizon,
    required this.milestones,
    this.matchedPack,
    super.key,
  });

  final String goalType;
  final String title;
  final String motivation;
  final String timeHorizon;
  final List<GoalMilestoneDraft> milestones;
  final ScenarioPackSummary? matchedPack;

  static const _typeLabels = <String, String>{
    'academic': 'Academic',
    'skill': 'Skill',
    'habit': 'Habit',
    'project': 'Project',
    'other': 'Other',
  };

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            Chip(label: Text(_typeLabels[goalType] ?? goalType)),
            Chip(label: Text(timeHorizon)),
          ],
        ),
        const SizedBox(height: 12),
        Text(motivation),
        if (matchedPack != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
            ),
            child: Row(
              children: [
                Icon(Icons.map_outlined, size: 20, color: DS.brandPrimary),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.goalWizardSuggestedPlan,
                        style: DS.labelSmall.copyWith(color: DS.brandPrimary),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${matchedPack!.name} (${matchedPack!.horizonDays}${l10n.goalWizardDay})',
                        style: DS.bodySmall.copyWith(
                          color: DS.textPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (matchedPack!.description.isNotEmpty)
                        Text(
                          matchedPack!.description,
                          style: DS.bodySmall.copyWith(color: DS.textSecondary),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        Text(
          l10n.goalWizardMilestonesTitle,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        for (final milestone in milestones)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.check_circle_outline_rounded),
            title: Text(milestone.title),
            subtitle: Text(milestone.description),
          ),
      ],
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onClose});

  final String message;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: DS.error100,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.error.withValues(alpha: 0.28)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline_rounded, color: DS.error),
          const SizedBox(width: 8),
          Expanded(child: Text(message)),
          IconButton(
            onPressed: onClose,
            icon: const Icon(Icons.close_rounded),
            tooltip: 'Close',
          ),
        ],
      ),
    );
  }
}
