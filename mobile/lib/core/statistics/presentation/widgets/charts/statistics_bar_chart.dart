import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/statistics/config/statistics_config.dart';
import 'package:sparkle/core/statistics/domain/statistics_domain.dart';

/// Bar chart widget for statistics data visualization
class StatisticsBarChart extends StatelessWidget {
  /// Data points to display
  final List<StatisticsDataPoint> dataPoints;

  /// Color for the bars
  final Color? barColor;

  /// Whether to use gradient on bars
  final bool useGradient;

  /// X-axis labels
  final List<String>? xLabels;

  /// Y-axis max value (null = auto)
  final double? maxY;

  /// Y-axis min value (default: 0)
  final double minY;

  /// Unit label for y-axis
  final String? unit;

  /// Custom tooltip formatter
  final String Function(double value)? tooltipFormatter;

  /// Whether to show horizontal bars instead of vertical
  final bool isHorizontal;

  const StatisticsBarChart({
    super.key,
    required this.dataPoints,
    this.barColor,
    this.useGradient = true,
    this.xLabels,
    this.maxY,
    this.minY = 0,
    this.unit,
    this.tooltipFormatter,
    this.isHorizontal = false,
  });

  @override
  Widget build(BuildContext context) {
    if (dataPoints.isEmpty) {
      return _buildEmptyState();
    }

    final labels = xLabels ??
        dataPoints.map((p) => p.label ?? _formatLabel(p.timestamp)).toList();

    return AspectRatio(
      aspectRatio: isHorizontal ? 1.6 : 1.3,
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          DS.sm,
          DS.lg,
          DS.sm,
          DS.sm,
        ),
        child: isHorizontal
            ? BarChart(_buildHorizontalChartData(labels))
            : BarChart(_buildVerticalChartData(labels)),
      ),
    );
  }

  BarChartData _buildVerticalChartData(List<String> labels) {
    final baseColor = barColor ?? StatisticsChartConfig.primaryColor;
    final groups = dataPoints.asMap().entries.map((entry) {
      return BarChartGroupData(
        x: entry.key,
        barRods: [
          BarChartRodData(
            toY: entry.value.value,
            color: useGradient ? null : baseColor,
            gradient: useGradient
                ? StatisticsChartConfig.getBarGradient(color: baseColor)
                : null,
            width: _calculateBarWidth(dataPoints.length),
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(StatisticsChartConfig.barBorderRadius),
              topRight: Radius.circular(StatisticsChartConfig.barBorderRadius),
            ),
          ),
        ],
      );
    }).toList();

    return BarChartData(
      barGroups: groups,
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
    );
  }

  BarChartData _buildHorizontalChartData(List<String> labels) {
    final baseColor = barColor ?? StatisticsChartConfig.primaryColor;
    final groups = dataPoints.asMap().entries.map((entry) {
      return BarChartGroupData(
        x: entry.key,
        barRods: [
          BarChartRodData(
            toY: entry.value.value,
            color: useGradient ? null : baseColor,
            gradient: useGradient
                ? StatisticsChartConfig.getBarGradient(color: baseColor)
                : null,
            width: _calculateBarWidth(dataPoints.length),
            borderRadius: BorderRadius.only(
              topRight: Radius.circular(StatisticsChartConfig.barBorderRadius),
              bottomRight: Radius.circular(StatisticsChartConfig.barBorderRadius),
            ),
          ),
        ],
      );
    }).toList();

    return BarChartData(
      barGroups: groups,
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
        bottomTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 60,
            getTitlesWidget: (value, meta) {
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
              return const Text('');
            },
          ),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        rightTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
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
      ),
      borderData: FlBorderData(show: false),
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
            Icons.bar_chart,
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

  double _calculateBarWidth(int dataPointCount) {
    final availableWidth = 600.0 / dataPointCount;
    final calculatedWidth = availableWidth - StatisticsChartConfig.barGroupSpacing;
    return calculatedWidth.clamp(
      StatisticsChartConfig.minBarWidth,
      StatisticsChartConfig.maxBarWidth,
    );
  }
}

/// Grouped bar chart for comparing multiple categories
class StatisticsGroupedBarChart extends StatelessWidget {
  /// Data groups to display (each group has multiple bars)
  final List<List<StatisticsDataPoint>> dataGroups;

  /// Colors for each bar in a group
  final List<Color>? barColors;

  /// X-axis labels (one per group)
  final List<String>? xLabels;

  /// Group labels (for legend)
  final List<String>? groupLabels;

  /// Y-axis max value (null = auto)
  final double? maxY;

  /// Y-axis min value (default: 0)
  final double minY;

  const StatisticsGroupedBarChart({
    super.key,
    required this.dataGroups,
    this.barColors,
    this.xLabels,
    this.groupLabels,
    this.maxY,
    this.minY = 0,
  });

  @override
  Widget build(BuildContext context) {
    if (dataGroups.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1.4,
          child: Padding(
            padding: EdgeInsets.fromLTRB(DS.sm, DS.lg, DS.sm, DS.sm),
            child: BarChart(
              _buildChartData(),
            ),
          ),
        ),
        if (groupLabels != null && groupLabels!.isNotEmpty) _buildLegend(),
      ],
    );
  }

  BarChartData _buildChartData() {
    final colors = barColors ??
        [
          StatisticsChartConfig.primaryColor,
          StatisticsChartConfig.secondaryColor,
          StatisticsChartConfig.tertiaryColor,
        ];

    final maxGroupSize = dataGroups.fold<int>(
      0,
      (max, group) => group.length > max ? group.length : max,
    );

    final groups = <BarChartGroupData>[];

    for (int i = 0; i < dataGroups.length; i++) {
      final group = dataGroups[i];
      final rods = <BarChartRodData>[];

      for (int j = 0; j < group.length; j++) {
        rods.add(
          BarChartRodData(
            toY: group[j].value,
            color: colors[j % colors.length],
            width: StatisticsChartConfig.barWidth / maxGroupSize,
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(StatisticsChartConfig.barBorderRadius),
              topRight: Radius.circular(StatisticsChartConfig.barBorderRadius),
            ),
          ),
        );
      }

      groups.add(
        BarChartGroupData(
          x: i,
          barRods: rods,
        ),
      );
    }

    return BarChartData(
      barGroups: groups,
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
    final colors = barColors ??
        [
          StatisticsChartConfig.primaryColor,
          StatisticsChartConfig.secondaryColor,
          StatisticsChartConfig.tertiaryColor,
        ];

    return Padding(
      padding: EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
      child: Wrap(
        spacing: DS.lg,
        runSpacing: DS.sm,
        alignment: WrapAlignment.center,
        children: List.generate(groupLabels!.length, (index) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: StatisticsChartConfig.legendMarkerSize,
                height: StatisticsChartConfig.legendMarkerSize,
                decoration: BoxDecoration(
                  color: colors[index % colors.length],
                  borderRadius: BorderRadius.circular(
                    StatisticsChartConfig.legendMarkerRadius,
                  ),
                ),
              ),
              SizedBox(width: DS.xs),
              Text(
                groupLabels![index],
                style: StatisticsChartConfig.legendTextStyle,
              ),
            ],
          );
        }),
      ),
    );
  }
}
