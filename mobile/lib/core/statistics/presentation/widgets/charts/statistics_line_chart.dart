import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/statistics/config/statistics_config.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

/// Line chart widget for statistics data visualization
class StatisticsLineChart extends StatelessWidget {
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

  const StatisticsLineChart({
    super.key,
    required this.dataPoints,
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
        padding: EdgeInsets.fromLTRB(
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
    final points = dataPoints.map((p) => FlSpot(
      dataPoints.indexOf(p).toDouble(),
      p.value,
    )).toList();

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
            getDotPainter: (spot, percent, barData, index) {
              return FlDotCirclePainter(
                radius: StatisticsChartConfig.pointRadius,
                color: baseColor,
                strokeWidth: 2,
                strokeColor: DS.white,
              );
            },
          ),
          belowBarData: fillArea
              ? BarAreaData(
                  show: true,
                  gradient: StatisticsChartConfig.getLineGradient(color: baseColor),
                )
              : BarAreaData(show: false),
        ),
      ],
      minX: 0,
      maxX: (dataPoints.length - 1).toDouble(),
      minY: minY,
      maxY: maxY,
      gridData: FlGridData(
        show: StatisticsChartConfig.showHorizontalGrid,
        drawVerticalLine: StatisticsChartConfig.showVerticalGrid,
        horizontalInterval: maxY != null ? (maxY! - minY) / 4 : null,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: StatisticsChartConfig.gridColor,
            strokeWidth: StatisticsChartConfig.gridThickness,
            dashArray: StatisticsChartConfig.gridDashPattern,
          );
        },
      ),
      titlesData: FlTitlesData(
        show: true,
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
            getTitlesWidget: (value, meta) {
              return Text(
                _formatYValue(value),
                style: TextStyle(
                  fontSize: StatisticsChartConfig.axisLabelSize,
                  color: StatisticsChartConfig.axisLabelColor,
                ),
              );
            },
          ),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
      ),
      borderData: FlBorderData(show: false),
      lineTouchData: LineTouchData(
        enabled: StatisticsChartConfig.touchEnabled,
        touchTooltipData: LineTouchTooltipData(
          tooltipBgColor: StatisticsChartConfig.tooltipBgColor,
          getTooltipItems: (touchedSpots) {
            return touchedSpots.map((spot) {
              final value = spot.y;
              final text = tooltipFormatter?.call(value) ??
                  _formatYValue(value);

              return LineTooltipItem(
                text,
                TextStyle(
                  color: StatisticsChartConfig.tooltipTextColor,
                  fontSize: 12,
                  fontWeight: DS.fontWeightMedium,
                ),
              );
            }).toList();
          },
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
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
          SizedBox(height: DS.md),
          Text(
            '暂无数据',
            style: DS.bodyStyle.copyWith(
              color: DS.neutral400,
            ),
          ),
        ],
      ),
    );
  }

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
    final maxLabels = StatisticsChartConfig.maxXLabels;
    if (labelCount <= maxLabels) return 1;
    return (labelCount / maxLabels).ceil().toDouble();
  }
}

/// Line chart with dual series for comparison
class StatisticsDualLineChart extends StatelessWidget {
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

  const StatisticsDualLineChart({
    super.key,
    required this.primaryData,
    required this.secondaryData,
    this.primaryColor,
    this.secondaryColor,
    this.xLabels,
    this.maxY,
    this.minY = 0,
    this.primaryLabel,
    this.secondaryLabel,
  });

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
            padding: EdgeInsets.fromLTRB(DS.sm, DS.lg, DS.sm, DS.sm),
            child: LineChart(
              _buildChartData(),
              duration: StatisticsAnimationConfig.chartUpdate,
              curve: StatisticsAnimationConfig.chartCurve,
            ),
          ),
        ),
        if (primaryLabel != null || secondaryLabel != null)
          _buildLegend(),
      ],
    );
  }

  LineChartData _buildChartData() {
    final pColor = primaryColor ?? StatisticsChartConfig.primaryColor;
    final sColor = secondaryColor ?? StatisticsChartConfig.secondaryColor;

    final primarySpots = primaryData.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.value);
    }).toList();

    final secondarySpots = secondaryData.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value.value);
    }).toList();

    return LineChartData(
      lineBarsData: [
        LineChartBarData(
          spots: primarySpots,
          isCurved: true,
          curveSmoothness: StatisticsChartConfig.lineSmoothness,
          color: pColor,
          barWidth: StatisticsChartConfig.lineWidth,
          dotData: FlDotData(show: false),
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
          dotData: FlDotData(show: false),
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
        show: StatisticsChartConfig.showHorizontalGrid,
        drawVerticalLine: false,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: StatisticsChartConfig.gridColor,
            strokeWidth: StatisticsChartConfig.gridThickness,
          );
        },
      ),
      titlesData: FlTitlesData(
        show: true,
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
            getTitlesWidget: (value, meta) {
              return Text(
                value.toInt().toString(),
                style: TextStyle(
                  fontSize: StatisticsChartConfig.axisLabelSize,
                  color: StatisticsChartConfig.axisLabelColor,
                ),
              );
            },
          ),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
      ),
      borderData: FlBorderData(show: false),
    );
  }

  Widget _buildLegend() {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: DS.lg),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (primaryLabel != null) _buildLegendItem(primaryLabel!, primaryColor),
          if (secondaryLabel != null) ...[
            SizedBox(width: DS.xl),
            _buildLegendItem(secondaryLabel!, secondaryColor),
          ],
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color? color) {
    return Row(
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
        SizedBox(width: DS.xs),
        Text(
          label,
          style: StatisticsChartConfig.legendTextStyle,
        ),
      ],
    );
  }
}
