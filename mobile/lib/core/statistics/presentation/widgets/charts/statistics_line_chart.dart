import 'package:fl_chart/fl_chart.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Line chart widget for statistics data visualization
class StatisticsLineChart extends StatelessWidget {
  const StatisticsLineChart({
    required this.dataPoints,
    super.key,
    this.lineColor,
    this.showPoints = true,
    this.fillArea = true,
    this.xLabels,
    this.maxY,
    this.minY = 0,
    this.unit,
    this.isHorizontal = false,
    this.tooltipFormatter,
  });

  /// Data points to display
  final List<StatisticsDataPoint> dataPoints;

  /// Color for the line
  final Color? lineColor;

  /// Whether to show data points
  final bool showPoints;

  /// Whether to fill area under the line
  final bool fillArea;

  /// X-axis labels
  final List<String>? xLabels;

  /// Y-axis max value (null = auto)
  final double? maxY;

  /// Y-axis min value (default: 0)
  final double minY;

  /// Unit label for y-axis
  final String? unit;

  /// Whether to show the chart in horizontal mode (landscape)
  final bool isHorizontal;

  /// Custom tooltip formatter
  final String Function(double value)? tooltipFormatter;

  @override
  Widget build(BuildContext context) {
    if (dataPoints.isEmpty) {
      return _buildEmptyState();
    }

    final labels = xLabels ??
        dataPoints.map((p) => p.label ?? _formatLabel(p.timestamp)).toList();

    return AspectRatio(
      aspectRatio: isHorizontal ? 2.5 : 1.6,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.sm,
          DS.lg,
          DS.sm,
          DS.sm,
        ),
        child: LineChart(
          _buildChartData(labels),
          duration: StatisticsAnimationConfig.chartUpdate,
          curve: StatisticsAnimationConfig.chartCurve,
        ),
      ),
    );
  }

  LineChartData _buildChartData(List<String> labels) {
    final baseColor = lineColor ?? StatisticsChartConfig.primaryColor;
    final points = dataPoints
        .map(
          (p) => FlSpot(
            dataPoints.indexOf(p).toDouble(),
            p.value,
          ),
        )
        .toList();

    return LineChartData(
      lineBarsData: [
        LineChartBarData(
          spots: points,
          isCurved: true,
          curveSmoothness: StatisticsChartConfig.lineSmoothness,
          color: baseColor,
          barWidth: StatisticsChartConfig.lineWidth,
          isStrokeCapRound: true,
          dotData: FlDotData(
            show: showPoints,
            getDotPainter: (spot, percent, barData, index) =>
                FlDotCirclePainter(
              radius: StatisticsChartConfig.pointRadius,
              color: baseColor,
              strokeWidth: 2,
              strokeColor: DS.white,
            ),
          ),
          belowBarData: fillArea
              ? BarAreaData(
                  show: true,
                  gradient:
                      StatisticsChartConfig.getLineGradient(color: baseColor),
                )
              : BarAreaData(),
        ),
      ],
      minX: 0,
      maxX: (dataPoints.length - 1).toDouble(),
      minY: minY,
      maxY: maxY,
      gridData: FlGridData(
        drawVerticalLine: StatisticsChartConfig.showVerticalGrid,
        horizontalInterval: maxY != null ? (maxY! - minY) / 4 : null,
        getDrawingHorizontalLine: (value) => FlLine(
          color: StatisticsChartConfig.gridColor,
          strokeWidth: StatisticsChartConfig.gridThickness,
          dashArray: StatisticsChartConfig.gridDashPattern,
        ),
      ),
      titlesData: FlTitlesData(
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: StatisticsChartConfig.axisLabelPadding,
            interval: _getInterval(labels.length),
            getTitlesWidget: (value, meta) {
              final index = value.toInt();
              if (index >= 0 && index < labels.length) {
                return Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Text(
                    labels[index],
                    style: TextStyle(
                      fontSize: StatisticsChartConfig.axisLabelSize,
                      color: StatisticsChartConfig.axisLabelColor,
                    ),
                  ),
                );
              }
              return const Text('');
            },
          ),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            interval: maxY != null ? (maxY! - minY) / 4 : null,
            getTitlesWidget: (value, meta) => Text(
              _formatYValue(value),
              style: TextStyle(
                fontSize: StatisticsChartConfig.axisLabelSize,
                color: StatisticsChartConfig.axisLabelColor,
              ),
            ),
          ),
        ),
        topTitles: const AxisTitles(),
        rightTitles: const AxisTitles(),
      ),
      borderData: FlBorderData(show: false),
      lineTouchData: LineTouchData(
        touchTooltipData: LineTouchTooltipData(
          tooltipBgColor: StatisticsChartConfig.tooltipBgColor,
          getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
            final value = spot.y;
            final text = tooltipFormatter?.call(value) ?? _formatYValue(value);

            return LineTooltipItem(
              text,
              TextStyle(
                color: StatisticsChartConfig.tooltipTextColor,
                fontSize: 12,
                fontWeight: DS.fontWeightMedium,
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildEmptyState() => Container(
        height: 200,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.show_chart,
              size: 48,
              color: StatisticsChartConfig.emptyStateColor,
            ),
            const SizedBox(height: DS.md),
            Text(
              I18nService.instance.isChinese ? '暂无数据' : 'No data',
              style: DS.bodyStyle.copyWith(
                color: DS.neutral400,
              ),
            ),
          ],
        ),
      );

  String _formatLabel(DateTime timestamp) {
    final now = DateTime.now();
    final isToday = now.year == timestamp.year &&
        now.month == timestamp.month &&
        now.day == timestamp.day;

    if (isToday) {
      return '${timestamp.hour}:${timestamp.minute.toString().padLeft(2, '0')}';
    }
    return '${timestamp.month}/${timestamp.day}';
  }

  String _formatYValue(double value) {
    if (unit != null) {
      return '${value.toInt()}$unit';
    }
    return value.toInt().toString();
  }

  double _getInterval(int labelCount) {
    const maxLabels = StatisticsChartConfig.maxXLabels;
    if (labelCount <= maxLabels) return 1;
    return (labelCount / maxLabels).ceil().toDouble();
  }
}

/// Line chart with dual series for comparison
class StatisticsDualLineChart extends StatelessWidget {
  const StatisticsDualLineChart({
    required this.primaryData,
    required this.secondaryData,
    super.key,
    this.primaryColor,
    this.secondaryColor,
    this.xLabels,
    this.maxY,
    this.minY = 0,
    this.primaryLabel,
    this.secondaryLabel,
  });

  /// Primary data series
  final List<StatisticsDataPoint> primaryData;

  /// Secondary data series (for comparison)
  final List<StatisticsDataPoint> secondaryData;

  /// Primary color
  final Color? primaryColor;

  /// Secondary color
  final Color? secondaryColor;

  /// X-axis labels
  final List<String>? xLabels;

  /// Y-axis max value (null = auto)
  final double? maxY;

  /// Y-axis min value (default: 0)
  final double minY;

  /// Labels for legend
  final String? primaryLabel;
  final String? secondaryLabel;

  @override
  Widget build(BuildContext context) {
    if (primaryData.isEmpty && secondaryData.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1.6,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(DS.sm, DS.lg, DS.sm, DS.sm),
            child: LineChart(
              _buildChartData(),
              duration: StatisticsAnimationConfig.chartUpdate,
              curve: StatisticsAnimationConfig.chartCurve,
            ),
          ),
        ),
        if (primaryLabel != null || secondaryLabel != null) _buildLegend(),
      ],
    );
  }

  LineChartData _buildChartData() {
    final pColor = primaryColor ?? StatisticsChartConfig.primaryColor;
    final sColor = secondaryColor ?? StatisticsChartConfig.secondaryColor;

    final primarySpots = primaryData
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.value))
        .toList();

    final secondarySpots = secondaryData
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.value))
        .toList();

    return LineChartData(
      lineBarsData: [
        LineChartBarData(
          spots: primarySpots,
          isCurved: true,
          curveSmoothness: StatisticsChartConfig.lineSmoothness,
          color: pColor,
          barWidth: StatisticsChartConfig.lineWidth,
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(
            show: true,
            gradient: StatisticsChartConfig.getLineGradient(color: pColor),
          ),
        ),
        LineChartBarData(
          spots: secondarySpots,
          isCurved: true,
          curveSmoothness: StatisticsChartConfig.lineSmoothness,
          color: sColor,
          barWidth: StatisticsChartConfig.lineWidth,
          dotData: const FlDotData(show: false),
        ),
      ],
      minX: 0,
      maxX: (primaryData.length > secondaryData.length
                  ? primaryData.length
                  : secondaryData.length)
              .toDouble() -
          1,
      minY: minY,
      maxY: maxY,
      gridData: FlGridData(
        drawVerticalLine: false,
        getDrawingHorizontalLine: (value) => FlLine(
          color: StatisticsChartConfig.gridColor,
          strokeWidth: StatisticsChartConfig.gridThickness,
        ),
      ),
      titlesData: FlTitlesData(
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: StatisticsChartConfig.axisLabelPadding,
            getTitlesWidget: (value, meta) {
              final labels = xLabels;
              if (labels != null) {
                final index = value.toInt();
                if (index >= 0 && index < labels.length) {
                  return Text(
                    labels[index],
                    style: TextStyle(
                      fontSize: StatisticsChartConfig.axisLabelSize,
                      color: StatisticsChartConfig.axisLabelColor,
                    ),
                  );
                }
              }
              return const Text('');
            },
          ),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            getTitlesWidget: (value, meta) => Text(
              value.toInt().toString(),
              style: TextStyle(
                fontSize: StatisticsChartConfig.axisLabelSize,
                color: StatisticsChartConfig.axisLabelColor,
              ),
            ),
          ),
        ),
        topTitles: const AxisTitles(),
        rightTitles: const AxisTitles(),
      ),
      borderData: FlBorderData(show: false),
    );
  }

  Widget _buildLegend() => Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.lg),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (primaryLabel != null)
              _buildLegendItem(primaryLabel!, primaryColor),
            if (secondaryLabel != null) ...[
              const SizedBox(width: DS.xl),
              _buildLegendItem(secondaryLabel!, secondaryColor),
            ],
          ],
        ),
      );

  Widget _buildLegendItem(String label, Color? color) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: StatisticsChartConfig.legendMarkerSize,
            height: StatisticsChartConfig.legendMarkerSize,
            decoration: BoxDecoration(
              color: color ?? StatisticsChartConfig.primaryColor,
              borderRadius: BorderRadius.circular(
                StatisticsChartConfig.legendMarkerRadius,
              ),
            ),
          ),
          const SizedBox(width: DS.xs),
          Text(
            label,
            style: StatisticsChartConfig.legendTextStyle,
          ),
        ],
      );
}
