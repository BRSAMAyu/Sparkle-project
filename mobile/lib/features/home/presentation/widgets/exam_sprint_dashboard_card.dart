import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/home/presentation/widgets/decoration_policy.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// SPEC v1.1 A2.1 正典集入场时长（M3 梯内 320ms）——本卡 #2/#8 共用。
const Duration _kCanonicalEntrance = Duration(milliseconds: 320);

class ExamSprintDashboardCard extends StatefulWidget {
  const ExamSprintDashboardCard({
    required this.data,
    super.key,
    this.onRecordResult,
    this.onStartDiagnostic,
  });

  final ExamSprintDashboardData data;
  final VoidCallback? onRecordResult;

  /// P1-E5: entry to the diagnostic mini-quiz.
  final VoidCallback? onStartDiagnostic;

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
    // SPEC v1.1 N5（改造 #9；「>7d 中性」勘误 @SPEC-REVIEW）：截止临近三档
    // 色阶 —— >7d 中性层（brandPrimary）→ ≤7d warning → ≤1d error。
    // error 槽在本上下文扩展为「不可挽回节点临近」，
    // 禁再泛化；翻转范围收敛至 header（图标+模式 pill）与倒计时数字两处，
    // 计划 chip / 任务组等其余位不再随 urgency 翻色。
    final urgencyColor = _urgencyAccentColor(context.colors, data.daysLeft);
    final futureGroups = data.futureGroups;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing4,
          DS.spacing16,
          DS.spacing8,
        ),
        child: data.daysLeft == 0
            ? _DayZeroBanner(
                data: data,
                isChinese: isChinese,
                onRecordResult: widget.onRecordResult,
              )
            : DashboardSectionShell(
                tone: DashboardSurfaceTone.hero,
                padding: const EdgeInsets.all(DS.spacing18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _CardHeader(
                      isChinese: isChinese,
                      targetMode: data.targetMode,
                      accentColor: urgencyColor,
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
                                urgencyColor: urgencyColor,
                              ),
                              const SizedBox(height: DS.spacing18),
                              Center(
                                child: _PassProbabilityArc(
                                  data: data,
                                  isChinese: isChinese,
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
                                urgencyColor: urgencyColor,
                              ),
                            ),
                            const SizedBox(width: DS.spacing20),
                            _PassProbabilityArc(
                              data: data,
                              isChinese: isChinese,
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
                          label: context.l10n.examHighFreqCoverage,
                          value: _formatPercent(data.highFreqCoverage),
                          detail:
                              '${data.highFreqCoveredCount}/${data.highFreqTotalCount}',
                          accentColor: DS.brandPrimary,
                        ),
                        _MetricPill(
                          label: context.l10n.examMistakeRepair,
                          value: _formatPercent(data.mistakeFixRate),
                          detail:
                              '${data.fixedMistakeCount}/${data.totalMistakeCount}',
                          accentColor: DS.success,
                        ),
                        _MetricPill(
                          label: context.l10n.examStudyStreak,
                          value: context.l10n.examStreakDays(data.streakDays),
                          detail: context.l10n.examKeepRhythm,
                          accentColor: DS.warning,
                        ),
                      ],
                    ),
                    if (data.highYieldLowMasteryTopics.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      Text(
                        context.l10n.examHighYieldWeakSpots(
                            data.highYieldLowMasteryTopics.join(' · '),),
                        style: context.typo.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.35,
                        ),
                      ),
                    ],
                    if (widget.onStartDiagnostic != null) ...[
                      const SizedBox(height: DS.spacing12),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton.icon(
                          onPressed: widget.onStartDiagnostic,
                          icon: const Icon(Icons.quiz_outlined, size: 18),
                          label: Text(
                            context.l10n.examDiagnosticStart,
                            style: context.typo.labelLarge.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
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
                        // N5 翻转收敛：任务组回归中性 accent（不随 urgency 翻色）。
                        accentColor: context.colors.brandPrimary,
                      )
                    else
                      Text(
                        context.l10n.examNoSprintScheduled,
                        style: context.typo.bodySmall.copyWith(
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

class _DayZeroBanner extends StatefulWidget {
  const _DayZeroBanner({
    required this.data,
    required this.isChinese,
    this.onRecordResult,
  });

  final ExamSprintDashboardData data;
  final bool isChinese;
  final VoidCallback? onRecordResult;

  @override
  State<_DayZeroBanner> createState() => _DayZeroBannerState();
}

class _DayZeroBannerState extends State<_DayZeroBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _entranceController;

  /// U-01 Step 2 门控保留；SPEC v1.1 N3（改造 #8）：常驻件禁循环呼吸/浮动——
  /// 原 3000ms repeat(reverse) 浮动降级为**单次入场**（正典集 320ms，自下方
  /// 6px 浮入），入场完成即静止定帧；中低档/reduce-motion 直接钉在静止位，
  /// 不再占 home 屏 §2.6 持续动画源名额。
  late DecorationMode _decorationMode = DecorationMode.animated;

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      vsync: this,
      duration: _kCanonicalEntrance,
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _decorationMode = resolveDecorationMode(context);
    if (_decorationMode == DecorationMode.animated) {
      // 单次入场：只播一次，依赖重建（主题/媒体变化）不重播。
      if (!_entranceController.isAnimating &&
          !_entranceController.isCompleted) {
        unawaited(_entranceController.forward());
      }
    } else {
      // 静止定帧＝入场完成位（offset 0）。
      _entranceController
        ..stop()
        ..value = 1.0;
    }
  }

  @override
  void dispose() {
    _entranceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    final tipText = data.sleepGuardHint;

    return AnimatedBuilder(
      animation: _entranceController,
      builder: (context, child) {
        // 单次入场映射：0＝自下方 6px，1＝静止位（0 偏移）；无循环往返。
        final entrance =
            Curves.easeOutCubic.transform(_entranceController.value);
        return Transform.translate(
          offset: Offset(0, (1 - entrance) * 6),
          child: child,
        );
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing20,
          vertical: DS.spacing24,
        ),
        decoration: BoxDecoration(
          // U-01 Step 2 token 化：本地深靛蓝字面量（0xFF1A237E/0xFF283593）
          // 换 brandPrimary 派生 token 渐变；textOnPrimary 对比度语义不变。
          gradient: LinearGradient(
            colors: [DS.primaryDark, DS.brandPrimary],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: DS.borderRadius20,
          boxShadow: [
            BoxShadow(
              color: DS.primaryDark.withValues(alpha: 0.2),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
          ],
        ),
        child: Column(
          children: [
            Text(
              context.l10n.examDayReady,
              style: context.typo.headingLarge.copyWith(
                color: DS.textOnPrimary,
                fontWeight: DS.fontWeightBold,
                height: 1.2,
              ),
              textAlign: TextAlign.center,
            ),
            if (data.subject.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                data.subject,
                style: context.typo.labelLarge.copyWith(
                  color: DS.textOnPrimary.withValues(alpha: 0.75),
                  fontWeight: DS.fontWeightMedium,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (tipText != null && tipText.isNotEmpty) ...[
              const SizedBox(height: DS.spacing18),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.textOnPrimary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: DS.textOnPrimary.withValues(alpha: 0.18),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.examTips,
                      style: context.typo.labelSmall.copyWith(
                        color: DS.textOnPrimary.withValues(alpha: 0.65),
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      tipText,
                      style: context.typo.bodyMedium.copyWith(
                        color: DS.textOnPrimary.withValues(alpha: 0.9),
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: DS.spacing20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: widget.onRecordResult,
                style: FilledButton.styleFrom(
                  backgroundColor: DS.textOnPrimary.withValues(alpha: 0.18),
                  foregroundColor: DS.textOnPrimary,
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  side: BorderSide(
                    color: DS.textOnPrimary.withValues(alpha: 0.3),
                  ),
                ),
                child: Text(
                  context.l10n.examRecordResult,
                  style: context.typo.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
            ),
          ],
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
    final title = context.l10n.examSprintDashboard;
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
            style: context.typo.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ),
        _ModePill(
          label: _modeLabel(targetMode, l: context.l10n),
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
    required this.urgencyColor,
  });

  final ExamSprintDashboardData data;
  final bool isChinese;

  /// N5（「>7d 中性」勘误 @SPEC-REVIEW）：倒计时数字位＝翻转收敛的两处之一
  /// （另一处是 header）。>7d 档为中性 brandPrimary，≤7d warning，≤1d error。
  final Color urgencyColor;

  @override
  Widget build(BuildContext context) {
    final countdown = data.daysLeft == 0
        ? context.l10n.examDay
        : context.l10n.examDaysUntil(data.daysLeft);
    final progress = context.l10n.examTodayProgress(
        data.todayProgress.completed, data.todayProgress.total,);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          countdown,
          style: context.typo.headingLarge.copyWith(
            color: urgencyColor,
            fontWeight: DS.fontWeightBold,
            height: 1.06,
          ),
        ),
        const SizedBox(height: DS.spacing10),
        Text(
          progress,
          style: context.typo.labelLarge.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        // N5 翻转收敛：计划名 chip 回归中性面（不再随 urgency 翻色）。
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: DS.textSecondary.withValues(alpha: 0.12),
            ),
          ),
          child: Text(
            '${data.planName}${data.subject.isNotEmpty ? ' · ${data.subject}' : ''}',
            style: context.typo.bodySmall.copyWith(
              color: DS.textPrimary,
              height: 1.35,
            ),
          ),
        ),
      ],
    );
  }
}

class _PassProbabilityArc extends StatefulWidget {
  const _PassProbabilityArc({
    required this.data,
    required this.isChinese,
  });

  final ExamSprintDashboardData data;
  final bool isChinese;

  @override
  State<_PassProbabilityArc> createState() => _PassProbabilityArcState();
}

class _PassProbabilityArcState extends State<_PassProbabilityArc>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      // SPEC v1.1 N6④（改造 #2）：入场动画收进 M3 正典集（A2.1 梯内 320ms），
      // 原 1200ms offLadder 退役。
      duration: _kCanonicalEntrance,
    );
    unawaited(_controller.forward());
  }

  @override
  void didUpdateWidget(covariant _PassProbabilityArc oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data.passProbability != widget.data.passProbability) {
      unawaited(_controller.forward(from: 0.0));
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final probability = widget.data.passProbability;
    final isNull = probability == null;
    final target = isNull ? 0.0 : probability.clamp(0.0, 1.0);
    final colors = context.colors;
    // N6③：低档（<0.4）按最终预测值判定（非动画中间值），触发动作文案兜底。
    final showLowTierAction = !isNull && probability < 0.4;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final eased = Curves.easeOutCubic.transform(_controller.value);
        final value = target * eased;
        final ringColor = isNull
            ? DS.textSecondary.withValues(alpha: 0.3)
            : _probabilityColor(colors, value);

        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            RepaintBoundary(
              child: SizedBox(
                width: 108,
                height: 108,
                child: CustomPaint(
                  painter: _PassProbabilityRingPainter(
                    progress: value,
                    color: ringColor,
                  ),
                  child: Center(
                    child: isNull
                        ? Text(
                            '--',
                            style: context.typo.headingLarge
                                .copyWith(
                              color: DS.textSecondary,
                              fontWeight: DS.fontWeightBold,
                            ),
                          )
                        : Text(
                            _formatPercent(value),
                            style: context.typo.headingLarge
                                .copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                              fontFeatures: const [
                                FontFeature.tabularFigures(),
                              ],
                            ),
                          ),
                  ),
                ),
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.data.daysLeft == 0
                      ? context.l10n.examDay
                      : context.l10n.examDaysLeft(widget.data.daysLeft),
                  style: context.typo.labelLarge.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
                // S-G9 清偿（复审 R5/SPEC-FIX）：今日进度文案同卡二出——
                // 弧旁「今日 x/y 完成」块删除，保留 _HeadlineBlock 主位
                // `examTodayProgress`（「今天已完成 x/y 项任务」）：
                // 该措辞带单位与宾语（项任务），x/y 的分母语义（今日任务总数）
                // 就地可读，符合 §6.1「结论+数字」；弧旁仅保留 N6② 口径行。
                // N6②：预测数口径一行，就地可见（「按当前进度估算」级）。
                Text(
                  context.l10n.examPassProbabilityEstimate,
                  style: context.typo.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
                // N6③：低档分档动作文案兜底（不羞辱，给出口）。
                if (showLowTierAction) ...[
                  const SizedBox(height: DS.spacing4),
                  Text(
                    context.l10n.examPassProbabilityLowAction,
                    style: context.typo.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.3,
                    ),
                  ),
                ],
              ],
            ),
          ],
        );
      },
    );
  }

  /// SPEC v1.1 N6④：红绿灯三档编码色走 theme 语义槽（context.colors）——
  /// colorBlindFriendly 主题下自动切换 Okabe-Ito CB-safe 变体，消除红绿单通道依赖；
  /// 禁回退静态 DS 常量直读（那会绕过注入主题）。
  static Color _probabilityColor(SparkleColors colors, double value) {
    if (value < 0.4) return colors.error;
    if (value <= 0.6) return colors.warning;
    return colors.success;
  }
}

class _PassProbabilityRingPainter extends CustomPainter {
  _PassProbabilityRingPainter({
    required this.progress,
    required this.color,
  });

  final double progress;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (math.min(size.width, size.height) / 2) - 7;
    const strokeWidth = 8.0;
    final rect = Rect.fromCircle(center: center, radius: radius);

    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = color.withValues(alpha: 0.15)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth,
    );

    if (progress > 0.001) {
      const startAngle = -math.pi / 2;
      final sweepAngle = 2 * math.pi * progress.clamp(0.0, 1.0);
      canvas.drawArc(
        rect,
        startAngle,
        sweepAngle,
        false,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = strokeWidth
          ..strokeCap = StrokeCap.round,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _PassProbabilityRingPainter old) =>
      old.progress != progress || old.color != color;
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
              style: context.typo.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              value,
              style: context.typo.titleLarge.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing2),
            Text(
              detail,
              style: context.typo.bodySmall.copyWith(
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
    final title = context.l10n.examTodaySprintTasks;
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: context.typo.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ),
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
                  ? context.l10n.examHideLaterDays
                  : context.l10n.examShowNextDays(futureGroupCount),
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
        ? context.l10n.examDay
        : context.l10n.examDayIndex(group.dayIndex);
    // S-G10 清偿（复审 R5/SPEC-FIX）：日期手工拼接 `'${m}/${d}'` 退役，
    // 走 date_formatting.dart 唯一入口（X3 防复发，双语各自地道）。
    final subtitle = group.date == null
        ? null
        : formatSparkleDateOnly(group.date!, context.l10n);

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
                style: context.typo.labelLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(width: DS.spacing8),
                Text(
                  subtitle,
                  style: context.typo.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
              const Spacer(),
              Text(
                '${group.completedCount}/${group.totalCount}',
                style: context.typo.labelLarge.copyWith(
                  color: accentColor,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          if (group.tasks.isEmpty)
            Text(
              context.l10n.examNoSprintTasks,
              style: context.typo.bodySmall.copyWith(
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
                style: context.typo.bodyMedium.copyWith(
                  color: DS.textPrimary,
                  height: 1.3,
                  fontWeight: task.isCompleted
                      ? DS.fontWeightMedium
                      : DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                '${context.l10n.examTaskMinutes(task.estimatedMinutes)} · ${_statusLabel(task, l: context.l10n)}',
                style: context.typo.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _statusLabel(ExamSprintTaskItem task, {required AppLocalizations l}) =>
      switch (task.status) {
        'COMPLETED' => l.examStatusCompleted,
        'IN_PROGRESS' => l.examStatusInProgress,
        _ => l.examStatusPending,
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
          style: context.typo.labelSmall.copyWith(
            color: accentColor,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

/// SPEC v1.1 N5（改造 #9）：倒计时上下文三档色阶——≤1d error（含考日豁免
/// 语义「不可挽回节点临近」）→ ≤7d warning → 其余中性（brandPrimary）。
/// 色源走 theme 语义槽，CB-friendly 主题下随 SparkleColors 变体切换。
Color _urgencyAccentColor(SparkleColors colors, int daysLeft) {
  if (daysLeft <= 1) return colors.error;
  if (daysLeft <= 7) return colors.warning;
  return colors.brandPrimary;
}

String _modeLabel(String? mode, {required AppLocalizations l}) {
  switch (mode) {
    case 'high_score':
      return l.examModeHighScore;
    case 'hold':
      return l.examModeHold;
    case 'pass':
      return l.examModePass;
    default:
      return l.examModeSprint;
  }
}

String _formatPercent(double value) =>
    '${(value.clamp(0.0, 1.0) * 100).round()}%';
