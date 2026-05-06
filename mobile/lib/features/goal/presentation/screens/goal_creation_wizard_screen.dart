import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/goal/data/models/goal_creation_models.dart';
import 'package:sparkle/features/goal/data/repositories/goal_repository.dart';

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

  int _step = 0;
  String _goalType = 'academic';
  String _timeHorizon = 'short';
  bool _loadingPreview = false;
  bool _creating = false;
  String? _error;
  GoalDecompositionPreview? _preview;
  List<GoalMilestoneDraft> _milestones = const [];

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  void dispose() {
    _titleController.dispose();
    _motivationController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final titles = [
      _t('类型', 'Type'),
      _t('动机', 'Motivation'),
      _t('时间', 'Timeline'),
      _t('拆解', 'Milestones'),
      _t('确认', 'Confirm'),
    ];
    final currentStepLabel = titles[_step];

    return Scaffold(
      appBar: AppBar(
        title: Text(_t('创建目标', 'Create goal')),
      ),
      body: SafeArea(
        child: Semantics(
          container: true,
          explicitChildNodes: true,
          label: _t(
            '创建目标，第 ${_step + 1} 步，共 ${titles.length} 步：$currentStepLabel',
            'Create goal, step ${_step + 1} of ${titles.length}: $currentStepLabel',
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
                    label: Text(_t('返回', 'Back')),
                  ),
                ),
              if (_step > 0) const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  onPressed:
                      _primaryActionEnabled ? () => unawaited(_next()) : null,
                  icon: _creating || _loadingPreview
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2,
                              semanticsLabel:
                                  'Loading'),
                        )
                      : Icon(_step == 4
                          ? Icons.check_rounded
                          : Icons.arrow_forward_rounded,
                          semanticLabel: _step == 4
                              ? _t('创建', 'Create')
                              : _t('继续', 'Continue')),
                  label: Text(
                      _step == 4 ? _t('创建', 'Create') : _t('继续', 'Continue')),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool get _primaryActionEnabled {
    if (_loadingPreview || _creating) return false;
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
        return _GoalTypeStep(
          key: const ValueKey('goal-type-step'),
          selected: _goalType,
          onSelected: (value) => setState(() => _goalType = value),
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
        );
    }
  }

  Future<void> _next() async {
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
        _error = _t('目标拆解失败，请稍后再试', 'Could not decompose this goal yet');
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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_t('目标已创建', 'Goal created'))),
        );
        return;
      }
      final router = GoRouter.maybeOf(context);
      if (router != null) {
        router.go('/goals/${Uri.encodeComponent(created.id)}');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_t('目标已创建', 'Goal created'))),
        );
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _creating = false;
        _error = _t('创建失败，请检查目标内容', 'Could not create this goal');
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
    final zh = I18nService.instance.isChinese;
    return Semantics(
      container: true,
      label: zh
          ? '进度：第 ${step + 1} 步，共 ${titles.length} 步'
          : 'Progress: step ${step + 1} of ${titles.length}',
      child: Row(
        children: [
          for (var index = 0; index < titles.length; index++) ...[
            Expanded(
              child: Column(
                children: [
                  Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: index <= step ? DS.brandPrimary : DS.surfaceTertiary,
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

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    final items = [
      ('academic', Icons.school_outlined, _t('学术', 'Academic')),
      ('skill', Icons.psychology_outlined, _t('技能', 'Skill')),
      ('habit', Icons.repeat_rounded, _t('习惯', 'Habit')),
      ('project', Icons.rocket_launch_outlined, _t('项目', 'Project')),
      ('other', Icons.more_horiz_rounded, _t('其他', 'Other')),
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

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TextField(
          controller: titleController,
          onChanged: (_) => onChanged(),
          textInputAction: TextInputAction.next,
          decoration: InputDecoration(
            labelText: _t('目标标题', 'Goal title'),
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
            labelText: _t('为什么重要', 'Why it matters'),
            prefixIcon: const Icon(Icons.favorite_border_rounded),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: descriptionController,
          minLines: 2,
          maxLines: 4,
          decoration: InputDecoration(
            labelText: _t('补充描述', 'Description'),
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

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<String>(
      segments: [
        ButtonSegment(
          value: 'short',
          icon: const Icon(Icons.calendar_view_week_outlined),
          label: Text(_t('短期 7-30 天', 'Short 7-30d')),
        ),
        ButtonSegment(
          value: 'medium',
          icon: const Icon(Icons.calendar_month_outlined),
          label: Text(_t('中期 1-3 月', 'Medium 1-3m')),
        ),
        ButtonSegment(
          value: 'long',
          icon: const Icon(Icons.timeline_rounded),
          label: Text(_t('长期 3 月+', 'Long 3m+')),
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

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
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
          label: Text(_t('重新生成', 'Regenerate')),
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

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            TextFormField(
              initialValue: milestone.title,
              decoration: InputDecoration(
                labelText: _t('里程碑 ${index + 1}', 'Milestone ${index + 1}'),
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
                labelText: _t('产出描述', 'Outcome'),
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
    super.key,
  });

  final String goalType;
  final String title;
  final String motivation;
  final String timeHorizon;
  final List<GoalMilestoneDraft> milestones;

  String _t(String zh, String en) => I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
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
            Chip(label: Text(goalType)),
            Chip(label: Text(timeHorizon)),
          ],
        ),
        const SizedBox(height: 12),
        Text(motivation),
        const SizedBox(height: 16),
        Text(
          _t('里程碑', 'Milestones'),
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
