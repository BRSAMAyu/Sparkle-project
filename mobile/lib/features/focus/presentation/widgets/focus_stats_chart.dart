import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';

/// Bar chart showing daily focus minutes
class FocusStatsChart extends StatelessWidget {
  const FocusStatsChart({
    required this.dailyData,
    required this.period,
    this.chartType = FocusStatsChartType.bar,
    super.key,
  });

  final Map<String, int> dailyData;
  final StatsViewPeriod period;
  final FocusStatsChartType chartType;

  @override
  Widget build(BuildContext context) {
    if (dailyData.isEmpty) {
      return SizedBox(
        height: 120,
        child: Center(
          child: Text(
            context.l10n.commonNoData,
            style: TextStyle(color: DS.neutral400),
          ),
        ),
      );
    }

    final dataPoints = _getDataPoints(context);
    final maxValue = dataPoints.isNotEmpty
        ? dataPoints.map((e) => e.value).reduce((a, b) => a > b ? a : b)
        : 10.0;

    return SparkleStaggerItem(
      index: 0,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0.94, end: 1),
        duration: DS.motionDuration(SparkleMotionToken.scene),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) => Transform.scale(
          scale: value,
          child: Opacity(opacity: value, child: child),
        ),
        child: SizedBox(
          height: 120,
          child: chartType == FocusStatsChartType.bar
              ? _BarChart(dataPoints: dataPoints, maxValue: maxValue)
              : _LineChart(dataPoints: dataPoints, maxValue: maxValue),
        ),
      ),
    );
  }

  List<_ChartPoint> _getDataPoints(BuildContext context) {
    final sortedKeys = dailyData.keys.toList()..sort();
    final locale = Localizations.localeOf(context).languageCode;
    final points = <_ChartPoint>[];

    for (var i = 0; i < sortedKeys.length; i++) {
      final rawKey = sortedKeys[i];
      final value = (dailyData[rawKey] ?? 0).toDouble();
      final parsedDate = DateTime.tryParse(rawKey);
      final label = _formatLabel(
        parsedDate,
        locale: locale,
        pointCount: sortedKeys.length,
      );
      points.add(
        _ChartPoint(
          index: i,
          label: label,
          value: value,
        ),
      );
    }

    return points;
  }

  String _formatLabel(
    DateTime? date, {
    required String locale,
    required int pointCount,
  }) {
    if (date == null) {
      return '';
    }
    if (pointCount <= 7 && period != StatsViewPeriod.month) {
      return DateFormat.E(locale).format(date);
    }
    return DateFormat.Md(locale).format(date);
  }
}

enum FocusStatsChartType { bar }

class _ChartPoint {
  const _ChartPoint({
    required this.index,
    required this.label,
    required this.value,
  });

  final int index;
  final String label;
  final double value;
}

class _BarChart extends StatelessWidget {
  const _BarChart({
    required this.dataPoints,
    required this.maxValue,
  });

  final List<_ChartPoint> dataPoints;
  final double maxValue;

  @override
  Widget build(BuildContext context) => BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: maxValue > 0 ? maxValue * 1.2 : 10,
          barTouchData: BarTouchData(
            enabled: true,
            touchTooltipData: BarTouchTooltipData(
              tooltipBgColor: DS.neutral800,
              tooltipPadding: const EdgeInsets.all(DS.sm),
              tooltipMargin: 8,
              getTooltipItem: (group, groupIndex, rod, rodIndex) {
                final minutes = rod.toY.round();
                return BarTooltipItem(
                  context.l10n.focusStatsMinutes(minutes),
                  TextStyle(
                    color: DS.neutral0,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                );
              },
            ),
          ),
          titlesData: FlTitlesData(
            leftTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            topTitles: const AxisTitles(),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  final index = value.toInt();
                  if (index >= 0 && index < dataPoints.length) {
                    final label = dataPoints[index].label;
                    if (label.isEmpty) {
                      return const SizedBox.shrink();
                    }
                    return Text(
                      label,
                      style: TextStyle(
                        color: DS.neutral500,
                        fontSize: 10,
                      ),
                    );
                  }
                  return const Text('');
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          gridData: const FlGridData(show: false),
          barGroups: dataPoints.asMap().entries.map((entry) {
            final index = entry.key;
            final spot = entry.value;

            return BarChartGroupData(
              x: index,
              barRods: [
                BarChartRodData(
                  toY: spot.value,
                  color: spot.value > 0 ? DS.brandPrimary : DS.neutral200,
                  width: 16,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(4),
                    topRight: Radius.circular(4),
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      );
}

class _LineChart extends StatelessWidget {
  const _LineChart({
    required this.dataPoints,
    required this.maxValue,
  });

  final List<_ChartPoint> dataPoints;
  final double maxValue;

  List<FlSpot> get _spots => dataPoints
      .map((point) => FlSpot(point.index.toDouble(), point.value))
      .toList();

  @override
  Widget build(BuildContext context) => LineChart(
        LineChartData(
          gridData: const FlGridData(show: false),
          titlesData: FlTitlesData(
            leftTitles: const AxisTitles(),
            rightTitles: const AxisTitles(),
            topTitles: const AxisTitles(),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  final index = value.toInt();
                  if (index >= 0 && index < dataPoints.length) {
                    final label = dataPoints[index].label;
                    if (label.isEmpty) {
                      return const SizedBox.shrink();
                    }
                    return Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        label,
                        style: TextStyle(
                          color: DS.neutral500,
                          fontSize: 10,
                        ),
                      ),
                    );
                  }
                  return const Text('');
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: _spots,
              isCurved: true,
              color: DS.brandPrimaryConst,
              barWidth: 2.5,
              isStrokeCapRound: true,
              dotData: FlDotData(
                getDotPainter: (spot, percent, barData, index) =>
                    FlDotCirclePainter(
                  radius: 3,
                  color: DS.surfacePrimary,
                  strokeWidth: 2,
                  strokeColor: DS.brandPrimary,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [
                    DS.brandPrimary.withValues(alpha: 0.25),
                    DS.brandPrimary.withValues(alpha: 0.0),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
          ],
          minX: 0,
          maxX: (dataPoints.length - 1).toDouble().clamp(6, 29),
          minY: 0,
          maxY: maxValue > 0 ? maxValue * 1.2 : 10,
        ),
      );
}
