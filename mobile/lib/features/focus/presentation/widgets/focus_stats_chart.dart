import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Bar chart showing daily focus minutes
class FocusStatsChart extends StatelessWidget {
  const FocusStatsChart({
    required this.dailyData,
    this.chartType = _ChartType.bar,
    super.key,
  });

  final Map<String, int> dailyData;
  final _ChartType chartType;

  @override
  Widget build(BuildContext context) {
    if (dailyData.isEmpty) {
      return const SizedBox(
        height: 120,
        child: Center(
          child: Text(
            '暂无数据',
            style: TextStyle(color: DS.neutral400),
          ),
        ),
      );
    }

    final dataPoints = _getDataPoints();
    final maxValue = dataPoints.isNotEmpty
        ? dataPoints.map((e) => e.y).reduce((a, b) => a > b ? a : b)
        : 10.0;

    return SizedBox(
      height: 120,
      child: chartType == _ChartType.bar
          ? _BarChart(dataPoints: dataPoints, maxValue: maxValue)
          : _LineChart(dataPoints: dataPoints, maxValue: maxValue),
    );
  }

  List<FlSpot> _getDataPoints() {
    final sortedKeys = dailyData.keys.toList()..sort();
    final spots = <FlSpot>[];

    for (var i = 0; i < sortedKeys.length; i++) {
      spots.add(FlSpot(
        i.toDouble(),
        (dailyData[sortedKeys[i]] ?? 0).toDouble(),
      ),);
    }

    return spots;
  }
}

enum _ChartType { bar, line }

class _BarChart extends StatelessWidget {
  const _BarChart({
    required this.dataPoints,
    required this.maxValue,
  });

  final List<FlSpot> dataPoints;
  final double maxValue;

  @override
  Widget build(BuildContext context) {
    final days = ['一', '二', '三', '四', '五', '六', '日'];

    return BarChart(
      BarChartData(
        alignment: BarChartAlignment.spaceAround,
        maxY: maxValue > 0 ? maxValue * 1.2 : 10,
        barTouchData: BarTouchData(
          enabled: true,
          touchTooltipData: BarTouchTooltipData(
            getTooltipColor: (_) => DS.neutral800,
            tooltipPadding: const EdgeInsets.all(DS.sm),
            tooltipMargin: 8,
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final minutes = rod.toY.round();
              return BarTooltipItem(
                '$minutes分钟',
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
                if (index >= 0 && index < days.length && index < dataPoints.length) {
                  return Text(
                    days[index],
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
                toY: spot.y,
                color: spot.y > 0
                    ? DS.brandPrimary
                    : DS.neutral200,
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
}

class _LineChart extends StatelessWidget {
  const _LineChart({
    required this.dataPoints,
    required this.maxValue,
  });

  final List<FlSpot> dataPoints;
  final double maxValue;

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
                final days = ['一', '二', '三', '四', '五', '六', '日'];
                final index = value.toInt();
                if (index >= 0 && index < days.length) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      days[index],
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
            spots: dataPoints,
            isCurved: true,
            color: DS.brandPrimary,
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
