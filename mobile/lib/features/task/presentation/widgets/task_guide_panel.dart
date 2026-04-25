import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class TaskGuidePanel extends StatefulWidget {
  const TaskGuidePanel({required this.task, super.key});

  final TaskModel task;

  @override
  State<TaskGuidePanel> createState() => _TaskGuidePanelState();
}

class _TaskGuidePanelState extends State<TaskGuidePanel> {
  bool _expanded = false;
  final Set<int> _completedSteps = <int>{};
  final Set<int> _completedCriteria = <int>{};

  @override
  void didUpdateWidget(covariant TaskGuidePanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.task.id != widget.task.id ||
        oldWidget.task.updatedAt != widget.task.updatedAt) {
      _expanded = false;
      _completedSteps.clear();
      _completedCriteria.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    final task = widget.task;
    final guide = task.guideJson ?? const <String, dynamic>{};
    final focusCue = _readText(guide['focus_cue']);
    final guidePreview = _firstChars(task.guideContent, 50);
    final todayFocus = focusCue.isNotEmpty ? focusCue : guidePreview;
    final methodSteps = _readList(guide['method_steps']);
    final estimatedMinutes =
        _readInt(guide['time_estimate_minutes']) ?? task.estimatedMinutes;
    final minimumOutput = _readText(guide['minimum_output']);
    final structuredSteps = _readStructuredSteps(
      guide['steps'],
      fallbackSteps: methodSteps,
      estimatedMinutes: estimatedMinutes,
      minimumOutput: minimumOutput,
    );
    final keyPoints = _readList(guide['key_points']).take(3).toList();
    final doneCriteria = _readList(
      guide['done_criteria'] ??
          guide['success_checklist'] ??
          guide['success_criteria'] ??
          task.successCriteria,
    );
    final commonMistakes = _readList(guide['common_mistakes']);
    final hasExpandedContent = todayFocus.isNotEmpty ||
        structuredSteps.isNotEmpty ||
        keyPoints.isNotEmpty ||
        doneCriteria.isNotEmpty ||
        commonMistakes.isNotEmpty;

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing16),
      borderColor: DS.borderSubtle,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: DS.surfaceSecondary,
                  shape: BoxShape.circle,
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Icon(
                  Icons.route_outlined,
                  color: DS.primaryBase,
                  size: 21,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      task.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: DS.titleMedium.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      _estimatedTimeLabel(task.estimatedMinutes),
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              key: const Key('task-guide-toggle'),
              style: TextButton.styleFrom(
                visualDensity: VisualDensity.compact,
                foregroundColor: DS.primaryBase,
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
              ),
              onPressed: () => setState(() => _expanded = !_expanded),
              icon: AnimatedRotation(
                turns: _expanded ? 0.5 : 0,
                duration: DS.motionDuration(SparkleMotionToken.micro),
                curve: DS.motionCurve(SparkleMotionToken.micro),
                child: const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
              ),
              label: Text(
                _expanded ? '收起指南' : '展开指南',
                style: DS.bodySmall.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
          ),
          SparkleExitTransition(
            visible: _expanded,
            maintainSize: false,
            motionToken: SparkleMotionToken.scene,
            child: Padding(
              padding: const EdgeInsets.only(top: DS.spacing8),
              child: hasExpandedContent
                  ? _GuideBody(
                      todayFocus: todayFocus,
                      steps: structuredSteps,
                      currentStepIndex:
                          _currentStepIndex(structuredSteps.length),
                      completedSteps: _completedSteps,
                      onStepTapped: (index) =>
                          _toggleStep(index, structuredSteps.length),
                      keyPoints: keyPoints,
                      doneCriteria: doneCriteria,
                      completedCriteria: _completedCriteria,
                      onCriterionTapped: _toggleCriterion,
                      commonMistakes: commonMistakes,
                    )
                  : Text(
                      '这张卡还没有更细的指南，先从你能确定的一小步开始。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  int? _currentStepIndex(int count) {
    for (var index = 0; index < count; index++) {
      if (!_completedSteps.contains(index)) {
        return index;
      }
    }
    return null;
  }

  void _toggleStep(int index, int count) {
    final current = _currentStepIndex(count);
    setState(() {
      if (_completedSteps.contains(index)) {
        _completedSteps.removeWhere((item) => item >= index);
        return;
      }
      if (current == null || index > current) {
        return;
      }
      _completedSteps.add(index);
    });
  }

  void _toggleCriterion(int index) {
    setState(() {
      if (_completedCriteria.contains(index)) {
        _completedCriteria.remove(index);
      } else {
        _completedCriteria.add(index);
      }
    });
  }

  String _estimatedTimeLabel(int minutes) {
    if (minutes <= 0) return '预估时间：按自己的节奏';
    return '预估时间：$minutes 分钟';
  }
}

class _GuideBody extends StatelessWidget {
  const _GuideBody({
    required this.todayFocus,
    required this.steps,
    required this.currentStepIndex,
    required this.completedSteps,
    required this.onStepTapped,
    required this.keyPoints,
    required this.doneCriteria,
    required this.completedCriteria,
    required this.onCriterionTapped,
    required this.commonMistakes,
  });

  final String todayFocus;
  final List<_GuideStepData> steps;
  final int? currentStepIndex;
  final Set<int> completedSteps;
  final ValueChanged<int> onStepTapped;
  final List<String> keyPoints;
  final List<String> doneCriteria;
  final Set<int> completedCriteria;
  final ValueChanged<int> onCriterionTapped;
  final List<String> commonMistakes;

  @override
  Widget build(BuildContext context) {
    final completedStepCount =
        completedSteps.where((index) => index < steps.length).length;
    final completedCriteriaCount =
        completedCriteria.where((index) => index < doneCriteria.length).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (todayFocus.isNotEmpty)
          _GuideSection(
            title: '今日焦点',
            child: Text(
              todayFocus,
              style: DS.bodyMedium.copyWith(
                color: DS.textPrimary,
                height: 1.45,
              ),
            ),
          ),
        if (steps.isNotEmpty)
          _GuideSection(
            title: '步骤',
            trailing: _ProgressPill(
              label: '已完成 $completedStepCount/${steps.length}',
            ),
            child: Column(
              children: [
                for (var index = 0; index < steps.length; index++)
                  _StructuredStepCard(
                    key: Key('guide-step-$index'),
                    step: steps[index],
                    index: index,
                    isCompleted: completedSteps.contains(index),
                    isCurrent: currentStepIndex == index,
                    onTap: () => onStepTapped(index),
                  ),
              ],
            ),
          ),
        if (keyPoints.isNotEmpty)
          _GuideSection(
            title: '关键提示',
            child: Column(
              children: [
                for (final point in keyPoints)
                  _IconLine(icon: '💡', text: point),
              ],
            ),
          ),
        if (doneCriteria.isNotEmpty)
          _GuideSection(
            title: '完成标准',
            trailing: _ProgressPill(
              label: '$completedCriteriaCount/${doneCriteria.length}',
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    key: const Key('done-criteria-progress'),
                    minHeight: 8,
                    value: doneCriteria.isEmpty
                        ? 0.0
                        : completedCriteriaCount / doneCriteria.length,
                    backgroundColor: DS.surfaceSecondary,
                    valueColor: AlwaysStoppedAnimation<Color>(DS.success),
                  ),
                ),
                const SizedBox(height: DS.spacing10),
                Text(
                  '点一下就能标记你已经完成的标准。',
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                for (var index = 0; index < doneCriteria.length; index++)
                  _CriterionTile(
                    key: Key('done-criterion-$index'),
                    text: doneCriteria[index],
                    checked: completedCriteria.contains(index),
                    onTap: () => onCriterionTapped(index),
                  ),
              ],
            ),
          ),
        if (commonMistakes.isNotEmpty)
          _CommonMistakesSection(commonMistakes: commonMistakes),
      ],
    );
  }
}

class _GuideSection extends StatelessWidget {
  const _GuideSection({
    required this.title,
    required this.child,
    this.trailing,
  });

  final String title;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: DS.bodyMedium.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                if (trailing != null) trailing!,
              ],
            ),
            const SizedBox(height: DS.spacing8),
            child,
          ],
        ),
      );
}

class _ProgressPill extends StatelessWidget {
  const _ProgressPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          label,
          style: DS.bodySmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _StructuredStepCard extends StatelessWidget {
  const _StructuredStepCard({
    required this.step,
    required this.index,
    required this.isCompleted,
    required this.isCurrent,
    required this.onTap,
    super.key,
  });

  final _GuideStepData step;
  final int index;
  final bool isCompleted;
  final bool isCurrent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cardColor = isCurrent
        ? DS.primaryBase.withValues(alpha: 0.08)
        : DS.surfaceSecondary.withValues(alpha: 0.72);
    final borderColor = isCurrent ? DS.primaryBase : DS.borderSubtle;
    final badgeColor = isCompleted ? DS.success : DS.primaryBase;

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing10),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(DS.borderRadiusLG),
          onTap: onTap,
          child: AnimatedContainer(
            duration: DS.motionDuration(SparkleMotionToken.micro),
            curve: DS.motionCurve(SparkleMotionToken.micro),
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: cardColor,
              borderRadius: BorderRadius.circular(DS.borderRadiusLG),
              border: Border.all(color: borderColor),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: badgeColor.withValues(alpha: 0.14),
                        shape: BoxShape.circle,
                      ),
                      child: isCompleted
                          ? Icon(
                              Icons.check_rounded,
                              color: DS.success,
                              size: 18,
                            )
                          : Text(
                              '${index + 1}',
                              style: DS.bodySmall.copyWith(
                                color: badgeColor,
                                fontWeight: DS.fontWeightBold,
                              ),
                            ),
                    ),
                    const SizedBox(width: DS.spacing10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            step.name,
                            style: DS.bodyMedium.copyWith(
                              color: DS.textPrimary,
                              fontWeight: isCurrent
                                  ? DS.fontWeightBold
                                  : DS.fontWeightMedium,
                              height: 1.45,
                            ),
                          ),
                          const SizedBox(height: DS.spacing6),
                          Row(
                            children: [
                              _StepMetaChip(
                                icon: Icons.schedule_rounded,
                                label: '${step.durationMin} 分钟',
                              ),
                              if (isCurrent) ...[
                                const SizedBox(width: DS.spacing8),
                                const _StepStatusChip(label: '当前进行中'),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (step.output.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing10),
                  Text(
                    '期望产出：${step.output}',
                    style: DS.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StepMetaChip extends StatelessWidget {
  const _StepMetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: DS.textSecondary, size: 14),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}

class _StepStatusChip extends StatelessWidget {
  const _StepStatusChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.primaryBase.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: DS.bodySmall.copyWith(
            color: DS.primaryBase,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _CriterionTile extends StatelessWidget {
  const _CriterionTile({
    required this.text,
    required this.checked,
    required this.onTap,
    super.key,
  });

  final String text;
  final bool checked;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(DS.borderRadiusLG),
            onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.spacing10,
              ),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary.withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(DS.borderRadiusLG),
                border: Border.all(
                  color: checked ? DS.success : DS.borderSubtle,
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    checked
                        ? Icons.check_circle_rounded
                        : Icons.radio_button_unchecked_rounded,
                    color: checked ? DS.success : DS.textSecondary,
                    size: 18,
                  ),
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
            ),
          ),
        ),
      );
}

class _IconLine extends StatelessWidget {
  const _IconLine({
    required this.icon,
    required this.text,
  });

  final String icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 24,
              child: Text(
                icon,
                textAlign: TextAlign.center,
                style: DS.bodyMedium,
              ),
            ),
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

class _CommonMistakesSection extends StatelessWidget {
  const _CommonMistakesSection({required this.commonMistakes});

  final List<String> commonMistakes;

  @override
  Widget build(BuildContext context) => Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          key: const Key('common-mistakes-toggle'),
          tilePadding: EdgeInsets.zero,
          childrenPadding: EdgeInsets.zero,
          title: Text(
            '常见陷阱',
            style: DS.bodyMedium.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          leading: Text('⚠', style: DS.bodyMedium),
          children: [
            const SizedBox(height: DS.spacing6),
            for (final mistake in commonMistakes)
              _IconLine(icon: '⚠', text: mistake),
          ],
        ),
      );
}

class _GuideStepData {
  const _GuideStepData({
    required this.name,
    required this.durationMin,
    required this.output,
  });

  final String name;
  final int durationMin;
  final String output;
}

List<_GuideStepData> _readStructuredSteps(
  Object? value, {
  required List<String> fallbackSteps,
  required int estimatedMinutes,
  required String minimumOutput,
}) {
  final parsed = <_GuideStepData>[];
  if (value is Iterable) {
    for (final item in value) {
      if (item is Map<String, dynamic>) {
        final name = _readText(item['name']);
        if (name.isEmpty) continue;
        parsed.add(
          _GuideStepData(
            name: name,
            durationMin: _readInt(item['duration_min']) ?? 5,
            output: _readText(item['output']),
          ),
        );
      } else {
        final name = item?.toString().trim() ?? '';
        if (name.isEmpty) continue;
        parsed.add(
          _GuideStepData(
            name: name,
            durationMin: 5,
            output: '',
          ),
        );
      }
    }
  }
  if (parsed.isNotEmpty) return parsed.take(4).toList(growable: false);

  final stepNames = <String>[...fallbackSteps];
  if (stepNames.isEmpty) return const [];
  while (stepNames.length < 4) {
    if (stepNames.length == 3) {
      stepNames.add(
        minimumOutput.isNotEmpty
            ? '最后用 $minimumOutput 做一个最小检查。'
            : '最后做一个最小检查，确认今天真的会了。',
      );
    } else {
      stepNames.add('把这一小步拆成你现在能立刻开始的版本。');
    }
  }
  final normalizedSteps = stepNames.take(4).toList(growable: false);
  final durations = _distributeMinutes(
    estimatedMinutes > 0 ? estimatedMinutes : normalizedSteps.length * 10,
    normalizedSteps.length,
  );
  final outputs = <String>[
    '留下这一步的起手框架或关键词。',
    '完成一次不看答案的独立输出。',
    '标出关键缺口，并补一句提醒。',
    minimumOutput.isNotEmpty ? '完成最小检查：$minimumOutput。' : '完成最小检查，确认不是只看懂。',
  ];
  return [
    for (var index = 0; index < normalizedSteps.length; index++)
      _GuideStepData(
        name: normalizedSteps[index],
        durationMin: durations[index],
        output: outputs[index],
      ),
  ];
}

String _readText(Object? value) {
  final text = value?.toString().trim() ?? '';
  return text;
}

int? _readInt(Object? value) {
  if (value == null) return null;
  if (value is num) {
    final intValue = value.toInt();
    return intValue > 0 ? intValue : null;
  }
  final parsed = int.tryParse(value.toString().trim());
  if (parsed == null || parsed <= 0) return null;
  return parsed;
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

List<int> _distributeMinutes(int total, int count) {
  if (count <= 0) return const [];
  final weights = <double>[0.18, 0.27, 0.33, 0.22];
  final values = <int>[];
  for (var index = 0; index < count; index++) {
    final weight = weights[index < weights.length ? index : weights.length - 1];
    values.add(((total * weight).round().clamp(3, total) as num).toInt());
  }
  var delta = total - values.reduce((sum, item) => sum + item);
  var pointer = 0;
  while (delta != 0 && values.isNotEmpty) {
    final target = pointer % values.length;
    if (delta > 0) {
      values[target] += 1;
      delta -= 1;
    } else if (values[target] > 3) {
      values[target] -= 1;
      delta += 1;
    }
    pointer += 1;
    if (pointer > 200) break;
  }
  return values;
}

String _firstChars(String? value, int maxChars) {
  final text = value?.trim() ?? '';
  if (text.length <= maxChars) return text;
  return '${text.substring(0, maxChars)}...';
}
