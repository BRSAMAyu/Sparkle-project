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

  @override
  Widget build(BuildContext context) {
    final task = widget.task;
    final guide = task.guideJson ?? const <String, dynamic>{};
    final focusCue = _readText(guide['focus_cue']);
    final guidePreview = _firstChars(task.guideContent, 50);
    final todayFocus = focusCue.isNotEmpty ? focusCue : guidePreview;
    final methodSteps = _readList(guide['method_steps']);
    final keyPoints = _readList(guide['key_points']).take(3).toList();
    final successCriteria = _readList(
      guide['success_criteria'] ?? task.successCriteria,
    );
    final commonMistakes = _readList(guide['common_mistakes']);
    final hasExpandedContent = todayFocus.isNotEmpty ||
        methodSteps.isNotEmpty ||
        keyPoints.isNotEmpty ||
        successCriteria.isNotEmpty ||
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
                      methodSteps: methodSteps,
                      keyPoints: keyPoints,
                      successCriteria: successCriteria,
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

  String _estimatedTimeLabel(int minutes) {
    if (minutes <= 0) return '预估时间：按自己的节奏';
    return '预估时间：$minutes 分钟';
  }
}

class _GuideBody extends StatelessWidget {
  const _GuideBody({
    required this.todayFocus,
    required this.methodSteps,
    required this.keyPoints,
    required this.successCriteria,
    required this.commonMistakes,
  });

  final String todayFocus;
  final List<String> methodSteps;
  final List<String> keyPoints;
  final List<String> successCriteria;
  final List<String> commonMistakes;

  @override
  Widget build(BuildContext context) => Column(
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
          if (methodSteps.isNotEmpty)
            _GuideSection(
              title: '步骤',
              child: Column(
                children: [
                  for (var index = 0; index < methodSteps.length; index++)
                    _NumberedStep(
                      number: index + 1,
                      text: methodSteps[index],
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
          if (successCriteria.isNotEmpty)
            _GuideSection(
              title: '完成标准',
              child: Column(
                children: [
                  for (final criterion in successCriteria)
                    _IconLine(icon: '✓', text: criterion),
                ],
              ),
            ),
          if (commonMistakes.isNotEmpty)
            _CommonMistakesSection(commonMistakes: commonMistakes),
        ],
      );
}

class _GuideSection extends StatelessWidget {
  const _GuideSection({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: DS.bodyMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            child,
          ],
        ),
      );
}

class _NumberedStep extends StatelessWidget {
  const _NumberedStep({
    required this.number,
    required this.text,
  });

  final int number;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: DS.primaryBase.withValues(alpha: 0.10),
                shape: BoxShape.circle,
              ),
              child: Text(
                '$number',
                style: DS.bodySmall.copyWith(
                  color: DS.primaryBase,
                  fontWeight: DS.fontWeightBold,
                ),
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

String _readText(Object? value) {
  final text = value?.toString().trim() ?? '';
  return text;
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

String _firstChars(String? value, int maxChars) {
  final text = value?.trim() ?? '';
  if (text.length <= maxChars) return text;
  return '${text.substring(0, maxChars)}...';
}
