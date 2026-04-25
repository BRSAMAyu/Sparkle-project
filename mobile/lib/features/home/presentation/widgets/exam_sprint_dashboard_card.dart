import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';

class ExamSprintDashboardCard extends StatefulWidget {
  const ExamSprintDashboardCard({
    required this.data,
    super.key,
  });

  final ExamSprintDashboardData data;

  @override
  State<ExamSprintDashboardCard> createState() =>
      _ExamSprintDashboardCardState();
}

class _ExamSprintDashboardCardState extends State<ExamSprintDashboardCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final isChinese = Localizations.localeOf(context)
        .languageCode
        .toLowerCase()
        .startsWith('zh');
    final data = widget.data;
    final accentColor = data.daysLeft <= 3 ? DS.error : DS.brandPrimary;
    final futureGroups = data.futureGroups;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing4,
          DS.spacing16,
          DS.spacing8,
        ),
        child: DashboardSectionShell(
          tone: DashboardSurfaceTone.hero,
          padding: const EdgeInsets.all(DS.spacing18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _CardHeader(
                isChinese: isChinese,
                targetMode: data.targetMode,
                accentColor: accentColor,
              ),
              const SizedBox(height: DS.spacing18),
              LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 620;
                  if (compact) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _HeadlineBlock(
                          data: data,
                          isChinese: isChinese,
                          accentColor: accentColor,
                        ),
                        const SizedBox(height: DS.spacing18),
                        Center(
                          child: _PassProbabilityArc(
                            data: data,
                            isChinese: isChinese,
                            accentColor: accentColor,
                          ),
                        ),
                      ],
                    );
                  }

                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: _HeadlineBlock(
                          data: data,
                          isChinese: isChinese,
                          accentColor: accentColor,
                        ),
                      ),
                      const SizedBox(width: DS.spacing20),
                      _PassProbabilityArc(
                        data: data,
                        isChinese: isChinese,
                        accentColor: accentColor,
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: DS.spacing18),
              Wrap(
                spacing: DS.spacing10,
                runSpacing: DS.spacing10,
                children: [
                  _MetricPill(
                    label: isChinese ? '高频考点覆盖率' : 'High-Freq Coverage',
                    value: _formatPercent(data.highFreqCoverage),
                    detail:
                        '${data.highFreqCoveredCount}/${data.highFreqTotalCount}',
                    accentColor: DS.brandPrimary,
                  ),
                  _MetricPill(
                    label: isChinese ? '错题修复率' : 'Mistake Repair',
                    value: _formatPercent(data.mistakeFixRate),
                    detail:
                        '${data.fixedMistakeCount}/${data.totalMistakeCount}',
                    accentColor: DS.success,
                  ),
                  _MetricPill(
                    label: isChinese ? '连续学习天数' : 'Study Streak',
                    value: isChinese
                        ? '${data.streakDays} 天'
                        : '${data.streakDays} d',
                    detail: isChinese ? '保持节奏' : 'Keep the rhythm',
                    accentColor: DS.warning,
                  ),
                ],
              ),
              if (data.highYieldLowMasteryTopics.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                Text(
                  isChinese
                      ? '高收益低掌握：${data.highYieldLowMasteryTopics.join(' · ')}'
                      : 'High-yield weak spots: ${data.highYieldLowMasteryTopics.join(' · ')}',
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing18),
              _TaskSectionHeader(
                isChinese: isChinese,
                isExpanded: _isExpanded,
                futureGroupCount: futureGroups.length,
                onToggle: futureGroups.isEmpty
                    ? null
                    : () {
                        setState(() {
                          _isExpanded = !_isExpanded;
                        });
                      },
              ),
              const SizedBox(height: DS.spacing12),
              if (data.todayGroup != null)
                _TaskGroupCard(
                  group: data.todayGroup!,
                  isChinese: isChinese,
                  accentColor: accentColor,
                )
              else
                Text(
                  isChinese
                      ? '今天还没有排入冲刺任务。'
                      : 'No sprint tasks scheduled today.',
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              AnimatedSize(
                duration: DS.durationSlow,
                curve: Curves.easeOutCubic,
                child: _isExpanded && futureGroups.isNotEmpty
                    ? Padding(
                        padding: const EdgeInsets.only(top: DS.spacing10),
                        child: Column(
                          children: [
                            for (final group in futureGroups) ...[
                              _TaskGroupCard(
                                group: group,
                                isChinese: isChinese,
                                accentColor: DS.info,
                              ),
                              const SizedBox(height: DS.spacing10),
                            ],
                          ],
                        ),
                      )
                    : const SizedBox.shrink(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CardHeader extends StatelessWidget {
  const _CardHeader({
    required this.isChinese,
    required this.targetMode,
    required this.accentColor,
  });

  final bool isChinese;
  final String? targetMode;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final title = isChinese ? '考试冲刺仪表盘' : 'Exam Sprint Dashboard';
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: accentColor.withValues(alpha: 0.18),
            ),
          ),
          child: Icon(
            Icons.rocket_launch_rounded,
            color: accentColor,
            size: 20,
          ),
        ),
        const SizedBox(width: DS.spacing12),
        Expanded(
          child: Text(
            title,
            style: context.sparkleTypography.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ),
        _ModePill(
          label: _modeLabel(targetMode, isChinese: isChinese),
          accentColor: accentColor,
        ),
      ],
    );
  }
}

class _HeadlineBlock extends StatelessWidget {
  const _HeadlineBlock({
    required this.data,
    required this.isChinese,
    required this.accentColor,
  });

  final ExamSprintDashboardData data;
  final bool isChinese;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final countdown = data.daysLeft == 0
        ? (isChinese ? '今天考试' : 'Exam day')
        : (isChinese
            ? '距考试还有 ${data.daysLeft} 天'
            : '${data.daysLeft} days until exam');
    final progress = isChinese
        ? '今天已完成 ${data.todayProgress.completed}/${data.todayProgress.total} 项任务'
        : 'Today: ${data.todayProgress.completed}/${data.todayProgress.total} tasks';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          countdown,
          style: context.sparkleTypography.headingLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightBold,
            height: 1.06,
          ),
        ),
        const SizedBox(height: DS.spacing10),
        Text(
          progress,
          style: context.sparkleTypography.labelLarge.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: accentColor.withValues(alpha: 0.14),
            ),
          ),
          child: Text(
            isChinese
                ? '${data.planName}${data.subject.isNotEmpty ? ' · ${data.subject}' : ''}'
                : '${data.planName}${data.subject.isNotEmpty ? ' · ${data.subject}' : ''}',
            style: context.sparkleTypography.bodySmall.copyWith(
              color: DS.textPrimary,
              height: 1.35,
            ),
          ),
        ),
      ],
    );
  }
}

class _PassProbabilityArc extends StatelessWidget {
  const _PassProbabilityArc({
    required this.data,
    required this.isChinese,
    required this.accentColor,
  });

  final ExamSprintDashboardData data;
  final bool isChinese;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final progress = data.currentPassProbability.clamp(0.0, 1.0);
    final baseline = data.baselinePassProbabilitySafe.clamp(0.0, 1.0);

    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0, end: progress),
      duration: DS.durationSlow,
      curve: Curves.easeOutCubic,
      builder: (context, animatedProgress, _) => SizedBox(
        width: 220,
        height: 180,
        child: CustomPaint(
          painter: _PassProbabilityArcPainter(
            progress: animatedProgress,
            baseline: baseline,
            accentColor: accentColor,
          ),
          child: Padding(
            padding: const EdgeInsets.only(top: DS.spacing24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _formatPercent(animatedProgress),
                  style: context.sparkleTypography.headingLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  isChinese ? '通过概率' : 'Pass Probability',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  _deltaLabel(data, isChinese: isChinese),
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: data.passProbabilityDelta >= 0
                        ? DS.success
                        : DS.warning,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
                if (data.estimatedScoreNow != null) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    isChinese
                        ? '当前估分 ${data.estimatedScoreNow!.round()}'
                        : 'Est. score ${data.estimatedScoreNow!.round()}',
                    style: context.sparkleTypography.bodySmall.copyWith(
                      color: DS.textSecondary,
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

  String _deltaLabel(ExamSprintDashboardData data, {required bool isChinese}) {
    if (!data.hasPassProbabilityDelta) {
      return isChinese ? '等待新诊断更新' : 'Waiting for next diagnostic';
    }
    final delta = (data.passProbabilityDelta * 100).round();
    if (delta == 0) {
      return isChinese ? '与诊断持平' : 'Flat vs diagnostic';
    }
    final sign = delta > 0 ? '+' : '';
    return isChinese ? '较诊断 $sign$delta%' : '$sign$delta% vs diagnostic';
  }
}

class _PassProbabilityArcPainter extends CustomPainter {
  _PassProbabilityArcPainter({
    required this.progress,
    required this.baseline,
    required this.accentColor,
  });

  final double progress;
  final double baseline;
  final Color accentColor;

  static const double _startAngle = math.pi * 0.85;
  static const double _sweepAngle = math.pi * 1.3;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.92);
    final radius = math.min(size.width * 0.38, size.height * 0.72);
    const strokeWidth = 12.0;
    final rect = Rect.fromCircle(center: center, radius: radius);

    final backgroundPaint = Paint()
      ..color = accentColor.withValues(alpha: 0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..color = Color.lerp(accentColor, DS.success, 0.18)!
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas
      ..drawArc(rect, _startAngle, _sweepAngle, false, backgroundPaint)
      ..drawArc(
        rect,
        _startAngle,
        _sweepAngle * progress.clamp(0.0, 1.0),
        false,
        progressPaint,
      );

    _drawMarker(
      canvas,
      center: center,
      radius: radius,
      angle: _startAngle + _sweepAngle * baseline.clamp(0.0, 1.0),
      color: DS.warning,
    );
    _drawMarker(
      canvas,
      center: center,
      radius: radius,
      angle: _startAngle + _sweepAngle * progress.clamp(0.0, 1.0),
      color: accentColor,
      size: 5.5,
    );
  }

  void _drawMarker(
    Canvas canvas, {
    required Offset center,
    required double radius,
    required double angle,
    required Color color,
    double size = 4.5,
  }) {
    final offset = Offset(
      center.dx + radius * math.cos(angle),
      center.dy + radius * math.sin(angle),
    );
    canvas
      ..drawCircle(
        offset,
        size + 2,
        Paint()..color = DS.surfacePrimaryElevated,
      )
      ..drawCircle(
        offset,
        size,
        Paint()..color = color,
      );
  }

  @override
  bool shouldRepaint(covariant _PassProbabilityArcPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.baseline != baseline ||
      oldDelegate.accentColor != accentColor;
}

class _MetricPill extends StatelessWidget {
  const _MetricPill({
    required this.label,
    required this.value,
    required this.detail,
    required this.accentColor,
  });

  final String label;
  final String value;
  final String detail;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => Container(
        width: 170,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: Color.lerp(DS.surfaceSecondary, accentColor, 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: accentColor.withValues(alpha: 0.14),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              value,
              style: context.sparkleTypography.titleLarge.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing2),
            Text(
              detail,
              style: context.sparkleTypography.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );
}

class _TaskSectionHeader extends StatelessWidget {
  const _TaskSectionHeader({
    required this.isChinese,
    required this.isExpanded,
    required this.futureGroupCount,
    this.onToggle,
  });

  final bool isChinese;
  final bool isExpanded;
  final int futureGroupCount;
  final VoidCallback? onToggle;

  @override
  Widget build(BuildContext context) {
    final title = isChinese ? '今日冲刺任务' : 'Today Sprint Tasks';
    return Row(
      children: [
        Text(
          title,
          style: context.sparkleTypography.titleLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
        const Spacer(),
        if (onToggle != null)
          TextButton.icon(
            onPressed: onToggle,
            icon: AnimatedRotation(
              duration: DS.durationFast,
              turns: isExpanded ? 0.5 : 0,
              child: const Icon(Icons.expand_more_rounded),
            ),
            label: Text(
              isExpanded
                  ? (isChinese ? '收起后续天' : 'Hide later days')
                  : (isChinese
                      ? '展开后续 $futureGroupCount 天'
                      : 'Show next $futureGroupCount days'),
            ),
          ),
      ],
    );
  }
}

class _TaskGroupCard extends StatelessWidget {
  const _TaskGroupCard({
    required this.group,
    required this.isChinese,
    required this.accentColor,
  });

  final ExamSprintTaskGroup group;
  final bool isChinese;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final title = group.isToday
        ? (isChinese ? '今天' : 'Today')
        : (isChinese ? '第 ${group.dayIndex} 天' : 'Day ${group.dayIndex}');
    final subtitle = group.date == null
        ? null
        : (isChinese
            ? '${group.date!.month}月${group.date!.day}日'
            : '${group.date!.month}/${group.date!.day}');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: accentColor.withValues(alpha: 0.12),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(width: DS.spacing8),
                Text(
                  subtitle,
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
              const Spacer(),
              Text(
                '${group.completedCount}/${group.totalCount}',
                style: context.sparkleTypography.labelLarge.copyWith(
                  color: accentColor,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          if (group.tasks.isEmpty)
            Text(
              isChinese ? '今天还没有排入任务' : 'No sprint tasks yet',
              style: context.sparkleTypography.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            )
          else
            Column(
              children: [
                for (final task in group.tasks) ...[
                  _TaskRow(task: task, isChinese: isChinese),
                  if (task != group.tasks.last)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: DS.spacing8),
                      child: Divider(height: 1),
                    ),
                ],
              ],
            ),
        ],
      ),
    );
  }
}

class _TaskRow extends StatelessWidget {
  const _TaskRow({
    required this.task,
    required this.isChinese,
  });

  final ExamSprintTaskItem task;
  final bool isChinese;

  @override
  Widget build(BuildContext context) {
    final color = switch (task.status) {
      'COMPLETED' => DS.success,
      'IN_PROGRESS' => DS.warning,
      _ => DS.textSecondary,
    };

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 22,
          height: 22,
          margin: const EdgeInsets.only(top: 1),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: color.withValues(alpha: 0.18),
            ),
          ),
          child: Icon(
            task.isCompleted
                ? Icons.check_rounded
                : task.isInProgress
                    ? Icons.schedule_rounded
                    : Icons.radio_button_unchecked_rounded,
            size: 14,
            color: color,
          ),
        ),
        const SizedBox(width: DS.spacing10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                task.title,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textPrimary,
                  height: 1.3,
                  fontWeight: task.isCompleted
                      ? DS.fontWeightMedium
                      : DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                isChinese
                    ? '${task.estimatedMinutes} 分钟 · ${_statusLabel(task, isChinese: isChinese)}'
                    : '${task.estimatedMinutes} min · ${_statusLabel(task, isChinese: isChinese)}',
                style: context.sparkleTypography.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _statusLabel(ExamSprintTaskItem task, {required bool isChinese}) =>
      switch (task.status) {
        'COMPLETED' => isChinese ? '已完成' : 'Done',
        'IN_PROGRESS' => isChinese ? '进行中' : 'In progress',
        _ => isChinese ? '待开始' : 'Pending',
      };
}

class _ModePill extends StatelessWidget {
  const _ModePill({
    required this.label,
    required this.accentColor,
  });

  final String label;
  final Color accentColor;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: accentColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: accentColor.withValues(alpha: 0.16),
          ),
        ),
        child: Text(
          label,
          style: context.sparkleTypography.labelSmall.copyWith(
            color: accentColor,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

String _modeLabel(String? mode, {required bool isChinese}) {
  switch (mode) {
    case 'high_score':
      return isChinese ? '冲高模式' : 'High Score';
    case 'hold':
      return isChinese ? '稳分模式' : 'Hold';
    case 'pass':
      return isChinese ? '保过模式' : 'Pass';
    default:
      return isChinese ? '冲刺模式' : 'Sprint';
  }
}

String _formatPercent(double value) =>
    '${(value.clamp(0.0, 1.0) * 100).round()}%';
