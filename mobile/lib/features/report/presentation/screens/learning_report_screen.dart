import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

enum _ReportRange { week, month, all }

class _HistoricalReportEntry {
  const _HistoricalReportEntry({
    required this.report,
    required this.createdAt,
  });

  final LearningReport report;
  final DateTime createdAt;
}

class LearningReportScreen extends ConsumerStatefulWidget {
  const LearningReportScreen({
    required this.report,
    super.key,
  });

  final LearningReport report;

  @override
  ConsumerState<LearningReportScreen> createState() =>
      _LearningReportScreenState();
}

class _LearningReportScreenState extends ConsumerState<LearningReportScreen> {
  int? _selectedMasteryIndex;
  _ReportRange _range = _ReportRange.week;

  @override
  Widget build(BuildContext context) {
    final report = widget.report;
    final chartData = report.mastery.take(6).toList();
    final averageMastery = _averageMastery(report);
    final strongCount =
        report.mastery.where((item) => item.masteryScore >= 80).length;
    final weakCount =
        report.mastery.where((item) => item.masteryScore < 60).length;
    final history = _loadHistoryEntries(report);
    final filteredHistory = _filterHistory(history);
    final previousReport = filteredHistory.length > 1 ? filteredHistory[1].report : null;
    final trendPoints = filteredHistory
        .map((entry) => _averageMastery(entry.report) / 100)
        .toList()
        .reversed
        .toList();

    return Scaffold(
      appBar: AppBar(title: const Text('学习分析报告')),
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.38),
              Theme.of(context).scaffoldBackgroundColor,
            ],
          ),
        ),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _AnimatedReportSection(
              delay: 0,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '本轮学习画像',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '把掌握度、重点薄弱项和整体趋势放在一个仪表盘里，方便你迅速把握当前状态。',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                    ),
                    if (filteredHistory.length > 1) ...[
                      const SizedBox(height: 16),
                      SegmentedButton<_ReportRange>(
                        segments: const [
                          ButtonSegment<_ReportRange>(
                            value: _ReportRange.week,
                            label: Text('本周'),
                          ),
                          ButtonSegment<_ReportRange>(
                            value: _ReportRange.month,
                            label: Text('本月'),
                          ),
                          ButtonSegment<_ReportRange>(
                            value: _ReportRange.all,
                            label: Text('全部'),
                          ),
                        ],
                        selected: <_ReportRange>{_range},
                        onSelectionChanged: (selection) {
                          setState(() => _range = selection.first);
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ),
            if (filteredHistory.length > 1) ...[
              const SizedBox(height: 14),
              _AnimatedReportSection(
                delay: 90,
                child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '掌握度趋势',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 140,
                        child: _MasteryTrendChart(
                          values: trendPoints,
                          labels: filteredHistory
                              .map((entry) => '${entry.createdAt.month}/${entry.createdAt.day}')
                              .toList()
                              .reversed
                              .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 140,
              child: ExpansionTile(
                initiallyExpanded: true,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                collapsedShape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                title: const Text('掌握度雷达图'),
                subtitle: Text(
                  previousReport == null ? '点击任一维度查看更细的掌握情况' : '当前报告已叠加上次轮廓，可点击维度查看详情',
                ),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  TweenAnimationBuilder<double>(
                    tween: Tween(begin: 0, end: 1),
                    duration: DS.durationSlow,
                    curve: Curves.easeOutCubic,
                    builder: (context, progress, child) => MasteryRadarChart(
                      labels: chartData.map((item) => item.nodeName).toList(),
                      values: chartData
                          .map(
                            (item) => ((item.masteryScore / 100) * progress)
                                .clamp(0.0, 1.0),
                          )
                          .toList(),
                      secondaryValues: _comparisonValuesFor(
                        chartData,
                        previousReport,
                      ),
                      selectedIndex: _selectedMasteryIndex,
                      onValueTap: (index) {
                        setState(() => _selectedMasteryIndex = index);
                        unawaited(_showMasteryDetail(chartData[index]));
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 220,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '关键指标',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _MetricCard(
                          label: '总掌握度',
                          value: '${averageMastery.round()}%',
                        ),
                        _MetricCard(
                          label: '知识点数',
                          value: '${report.mastery.length}',
                        ),
                        _MetricCard(
                          label: '强项',
                          value: '$strongCount',
                        ),
                        _MetricCard(
                          label: '薄弱点',
                          value: '$weakCount',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 320,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '重点知识维度',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: report.mastery
                          .take(8)
                          .map(
                            (item) => ActionChip(
                              avatar: Icon(
                                _masteryIcon(item.masteryScore),
                                size: 16,
                                color: _masteryColor(
                                  item.masteryScore,
                                  Theme.of(context).colorScheme,
                                ),
                              ),
                              label: Text(
                                '${item.nodeName} ${item.masteryScore.round()}%',
                              ),
                              onPressed: () => _showMasteryDetail(item),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 420,
              child: ExpansionTile(
                initiallyExpanded: true,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                collapsedShape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                title: const Text('AI 分析报告'),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    child: SparkleMarkdown(
                      content: report.markdown,
                      textColor: Theme.of(context).colorScheme.onSurface,
                      codeBackgroundColor:
                          Theme.of(context).colorScheme.surfaceContainerHighest,
                      linkColor: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 520,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    FilledButton.tonalIcon(
                      onPressed: () => context.push(GalaxyRoutes.home),
                      icon: const Icon(Icons.auto_graph_rounded),
                      label: const Text('回到 Galaxy'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => context.push(PlanRoutes.sprintHistory),
                      icon: const Icon(Icons.history_rounded),
                      label: const Text('查看 Sprint 历史'),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  double _averageMastery(LearningReport report) => report.mastery.isEmpty
      ? 0.0
      : report.mastery
              .map((item) => item.masteryScore)
              .fold<double>(0, (sum, value) => sum + value) /
          report.mastery.length;

  List<_HistoricalReportEntry> _loadHistoryEntries(LearningReport currentReport) {
    final updates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );
    final entries = <_HistoricalReportEntry>[
      _HistoricalReportEntry(
        report: currentReport,
        createdAt: DateTime.now(),
      ),
    ];
    for (final item in updates) {
      if (item['type']?.toString() != 'learning_report_ready') {
        continue;
      }
      final metadata = item['metadata'];
      if (metadata is! Map) {
        continue;
      }
      final payload = metadata['report_payload'];
      if (payload is! Map) {
        continue;
      }
      final report = LearningReport.fromJson(Map<String, dynamic>.from(payload));
      final createdAt = DateTime.tryParse(item['created_at']?.toString() ?? '');
      entries.add(
        _HistoricalReportEntry(
          report: report,
          createdAt: createdAt ?? DateTime.now(),
        ),
      );
    }
    final deduped = <String, _HistoricalReportEntry>{};
    for (final entry in entries) {
      deduped[entry.report.reportId] = entry;
    }
    final list = deduped.values.toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  List<_HistoricalReportEntry> _filterHistory(List<_HistoricalReportEntry> history) {
    final now = DateTime.now();
    return history.where((entry) {
      switch (_range) {
        case _ReportRange.week:
          return now.difference(entry.createdAt).inDays <= 7;
        case _ReportRange.month:
          return now.difference(entry.createdAt).inDays <= 30;
        case _ReportRange.all:
          return true;
      }
    }).toList();
  }

  List<double>? _comparisonValuesFor(
    List<LearningMasteryDatum> current,
    LearningReport? previous,
  ) {
    if (previous == null || previous.mastery.isEmpty) {
      return null;
    }
    final byName = <String, double>{
      for (final item in previous.mastery) item.nodeName: item.masteryScore / 100,
    };
    return current.map((item) => byName[item.nodeName] ?? 0.0).toList();
  }

  Future<void> _showMasteryDetail(LearningMasteryDatum item) async {
    final score = item.masteryScore;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (sheetContext) {
        final scheme = Theme.of(sheetContext).colorScheme;
        final masteryColor = _masteryColor(score, scheme);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.nodeName,
                  style: Theme.of(sheetContext).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: masteryColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    '${score.round()}% · ${_masteryLabel(score)}',
                    style: Theme.of(sheetContext).textTheme.labelLarge?.copyWith(
                          color: masteryColor,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  _masteryGuidance(item),
                  style: Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.5,
                      ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonalIcon(
                        onPressed: () {
                          Navigator.of(sheetContext).pop();
                          unawaited(context.push(GalaxyRoutes.home));
                        },
                        icon: const Icon(Icons.auto_graph_rounded),
                        label: const Text('打开知识星图'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => Navigator.of(sheetContext).pop(),
                        icon: const Icon(Icons.check_circle_outline_rounded),
                        label: const Text('继续阅读报告'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _masteryLabel(double score) {
    if (score >= 80) {
      return '掌握稳定';
    }
    if (score >= 60) {
      return '仍可巩固';
    }
    return '需要重点补强';
  }

  String _masteryGuidance(LearningMasteryDatum item) {
    final score = item.masteryScore;
    if (score >= 80) {
      return '这个知识点已经比较稳，可以更多地通过应用题和迁移练习来保持熟练度。';
    }
    if (score >= 60) {
      return '这个知识点理解基本建立，但在连续推理或综合题里可能还会波动，适合再补一轮刻意练习。';
    }
    return '这个知识点当前是明显薄弱环节，建议先回到定义、例题和前置概念，再重新做相关练习。';
  }

  Color _masteryColor(double score, ColorScheme scheme) {
    if (score >= 80) {
      return DS.success;
    }
    if (score >= 60) {
      return DS.warning;
    }
    return scheme.error;
  }

  IconData _masteryIcon(double score) {
    if (score >= 80) {
      return Icons.trending_up_rounded;
    }
    if (score >= 60) {
      return Icons.timeline_rounded;
    }
    return Icons.priority_high_rounded;
  }
}

class _MasteryTrendChart extends StatelessWidget {
  const _MasteryTrendChart({
    required this.values,
    required this.labels,
  });

  final List<double> values;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    if (values.length < 2) {
      return Center(
        child: Text(
          '至少需要两份报告才能绘制趋势。',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.textSecondary,
              ),
        ),
      );
    }
    return Column(
      children: [
        Expanded(
          child: CustomPaint(
            painter: _TrendChartPainter(
              values: values,
              lineColor: Theme.of(context).colorScheme.primary,
              fillColor: DS.info.withValues(alpha: 0.12),
              gridColor:
                  Theme.of(context).colorScheme.outlineVariant.withValues(alpha: 0.5),
            ),
            child: const SizedBox.expand(),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: labels
              .map(
                (label) => Text(
                  label,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

class _TrendChartPainter extends CustomPainter {
  const _TrendChartPainter({
    required this.values,
    required this.lineColor,
    required this.fillColor,
    required this.gridColor,
  });

  final List<double> values;
  final Color lineColor;
  final Color fillColor;
  final Color gridColor;

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 1;
    for (var i = 1; i <= 3; i++) {
      final y = size.height * (i / 4);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = values.length == 1 ? size.width / 2 : size.width * (i / (values.length - 1));
      final y = size.height - (values[i].clamp(0.0, 1.0) * (size.height - 12)) - 6;
      points.add(Offset(x, y));
    }
    if (points.isEmpty) {
      return;
    }

    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 1; i < points.length; i++) {
      final previous = points[i - 1];
      final current = points[i];
      final controlX = (previous.dx + current.dx) / 2;
      path.cubicTo(
        controlX,
        previous.dy,
        controlX,
        current.dy,
        current.dx,
        current.dy,
      );
    }

    final fillPath = Path.from(path)
      ..lineTo(points.last.dx, size.height)
      ..lineTo(points.first.dx, size.height)
      ..close();

    canvas.drawPath(
      fillPath,
      Paint()..color = fillColor,
    );
    final linePaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawPath(path, linePaint);
    for (final point in points) {
      canvas.drawCircle(point, 4, Paint()..color = lineColor);
    }
  }

  @override
  bool shouldRepaint(covariant _TrendChartPainter oldDelegate) =>
      oldDelegate.values != values ||
      oldDelegate.lineColor != lineColor ||
      oldDelegate.fillColor != fillColor ||
      oldDelegate.gridColor != gridColor;
}

class _AnimatedReportSection extends StatefulWidget {
  const _AnimatedReportSection({
    required this.delay,
    required this.child,
  });

  final int delay;
  final Widget child;

  @override
  State<_AnimatedReportSection> createState() => _AnimatedReportSectionState();
}

class _AnimatedReportSectionState extends State<_AnimatedReportSection> {
  bool _visible = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer(Duration(milliseconds: widget.delay), () {
      if (!mounted) {
        return;
      }
      setState(() => _visible = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedSlide(
        duration: DS.durationNormal,
        curve: Curves.easeOutCubic,
        offset: _visible ? Offset.zero : const Offset(0, 0.04),
        child: AnimatedOpacity(
          duration: DS.durationNormal,
          opacity: _visible ? 1 : 0,
          child: widget.child,
        ),
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: 152,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: DS.durationSlow,
              curve: Curves.easeOutCubic,
              builder: (context, progress, child) {
                final displayValue = value.contains('%')
                    ? '${(int.parse(value.replaceAll('%', '')) * progress).round()}%'
                    : '${((int.tryParse(value) ?? 0) * progress).round()}';
                return Text(
                  displayValue,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                );
              },
            ),
          ],
        ),
      );
}
