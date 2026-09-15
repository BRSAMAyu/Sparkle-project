import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Unified chart styling configuration for statistics module
///
/// All statistics charts should use these constants
/// for consistent visual appearance.
class StatisticsChartConfig {
  // Private constructor to prevent instantiation
  StatisticsChartConfig._();

  // ============================================
  // COLOR CONSTANTS
  // ============================================

  /// Primary color for main data series
  static Color get primaryColor => DS.brandPrimary;

  /// Secondary color for comparison data
  static Color get secondaryColor => DS.brandSecondary;

  /// Tertiary color for additional data series
  static Color get tertiaryColor => DS.success;

  /// Quaternary color for more data series
  static Color get quaternaryColor => DS.warning;

  /// Background color for chart containers
  static Color get backgroundColor => DS.surfacePrimary;

  /// Card background color
  static Color get cardColor => DS.surfaceSecondary;

  /// Grid line color (subtle)
  static Color get gridColor => DS.border.withValues(alpha: 0.7);

  /// Axis label color
  static Color get axisLabelColor => DS.textSecondary;

  /// Tooltip background color
  static Color get tooltipBgColor => DS.surfaceHigh;

  /// Tooltip text color
  static Color get tooltipTextColor => DS.textPrimary;

  /// Positive trend color (green)
  static Color get positiveColor => DS.success;

  /// Negative trend color (red)
  static Color get negativeColor => DS.error;

  /// Neutral trend color
  static Color get neutralColor => DS.textSecondary;

  /// Empty state color (for no data)
  static Color get emptyStateColor => DS.surfaceTertiary;

  // ============================================
  // LINE CHART CONFIG
  // ============================================

  /// Default line width for line charts
  static const double lineWidth = 3.0;

  /// Smoothness of line curves (0 = straight, 1 = very smooth)
  static const double lineSmoothness = 0.3;

  /// Show data points on line charts
  static const bool showPoints = true;

  /// Point radius for line charts
  static const double pointRadius = 4.0;

  /// Point halo radius (expanded on tap)
  static const double pointHaloRadius = 8.0;

  /// Fill area under line
  static const bool fillArea = true;

  /// Fill opacity (0 = transparent, 1 = opaque)
  static const double fillOpacity = 0.15;

  /// Line chart colors gradient start
  static Color get lineGradientStart => primaryColor;

  /// Line chart colors gradient end
  static Color get lineGradientEnd => primaryColor.withValues(alpha: 0.75);

  // ============================================
  // BAR CHART CONFIG
  // ============================================

  /// Default bar width
  static const double barWidth = 20.0;

  /// Bar border radius (top corners only)
  static const double barBorderRadius = 6.0;

  /// Minimum bar width (for many bars)
  static const double minBarWidth = 8.0;

  /// Maximum bar width
  static const double maxBarWidth = 40.0;

  /// Spacing between bar groups
  static const double barGroupSpacing = 16.0;

  /// Spacing between bars in a group
  static const double barGroupInnerPadding = 4.0;

  /// Bar chart colors (gradient)
  static List<Color> get barGradientColors => [
        primaryColor,
        lineGradientEnd,
      ];

  // ============================================
  // PIE CHART CONFIG
  // ============================================

  /// Default pie chart radius
  static const double pieRadius = 80.0;

  /// Donut chart inner radius (0 = pie chart, >0 = donut)
  static const double pieInnerRadius = 40.0;

  /// Spacing between pie sections
  static const double pieSectionSpacing = 2.0;

  /// Pie section border width
  static const double pieBorderWidth = 0.0;

  /// Pie chart palette (categorical)
  static List<Color> get piePalette => [
        primaryColor,
        secondaryColor,
        tertiaryColor,
        quaternaryColor,
        DS.info,
        DS.taskReflection,
        DS.error,
        DS.taskPlanning,
      ];

  // ============================================
  // HEATMAP CONFIG
  // ============================================

  /// Heatmap cell size (square)
  static const double heatmapCellSize = 12.0;

  /// Heatmap cell spacing
  static const double heatmapCellSpacing = 3.0;

  /// Heatmap border radius
  static const double heatmapCellRadius = 2.0;

  /// Heatmap empty cell color
  static Color get heatmapEmptyColor => DS.surfaceTertiary;

  /// Heatmap low activity color
  static Color get heatmapLowColor => DS.brandPrimary.withValues(alpha: 0.25);

  /// Heatmap medium activity color
  static Color get heatmapMediumColor =>
      DS.brandPrimary.withValues(alpha: 0.55);

  /// Heatmap high activity color
  static Color get heatmapHighColor => DS.brandPrimary;

  // ============================================
  // AXIS CONFIG
  // ============================================

  /// Show horizontal grid lines
  static const bool showHorizontalGrid = true;

  /// Show vertical grid lines
  static const bool showVerticalGrid = false;

  /// Grid line thickness
  static const double gridThickness = 1.0;

  /// Grid line dash pattern (null = solid)
  static const List<int> gridDashPattern = [4, 4];

  /// Axis line thickness
  static const double axisThickness = 0.0; // Hidden by default

  /// Axis label font size
  static const double axisLabelSize = 11.0;

  /// Axis label padding
  static const double axisLabelPadding = 8.0;

  /// Maximum number of labels on X axis
  static const int maxXLabels = 7;

  /// Maximum number of labels on Y axis
  static const int maxYLabels = 5;

  // ============================================
  // TOOLTIP CONFIG
  // ============================================

  /// Show tooltips on tap
  static const bool showTooltips = true;

  /// Tooltip border radius
  static const double tooltipRadius = 8.0;

  /// Tooltip padding
  static const double tooltipPadding = 12.0;

  /// Tooltip margin from touch point
  static const double tooltipMargin = 8.0;

  /// Tooltip show duration
  static const Duration tooltipDuration = Duration(milliseconds: 150);

  // ============================================
  // LEGEND CONFIG
  // ============================================

  /// Show chart legend
  static const bool showLegend = true;

  /// Legend position
  static const LegendPosition legendPosition = LegendPosition.bottom;

  /// Legend item spacing
  static const double legendItemSpacing = 16.0;

  /// Legend marker size
  static const double legendMarkerSize = 12.0;

  /// Legend marker border radius
  static const double legendMarkerRadius = 3.0;

  /// Legend text style
  static TextStyle get legendTextStyle => TextStyle(
        fontSize: 12,
        color: DS.textSecondary,
        fontWeight: FontWeight.w500,
      );

  // ============================================
  // TOUCH/INTERACTION CONFIG
  // ============================================

  /// Enable touch interaction
  static const bool touchEnabled = true;

  /// Touch detection radius (larger = easier to trigger)
  static const double touchRadius = 20.0;

  /// Enable long press to show value
  static const bool longPressEnabled = true;

  /// Enable zooming (for detailed charts)
  static const bool zoomEnabled = false;

  /// Enable panning (for zoomed charts)
  static const bool panEnabled = false;

  // ============================================
  // PRESET CHART THEMES
  // ============================================

  /// Get a predefined color for an index
  static Color getColorForIndex(int index) =>
      piePalette[index % piePalette.length];

  /// Get gradient for line chart
  static LinearGradient getLineGradient({Color? color}) => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          (color ?? primaryColor).withValues(alpha: fillOpacity),
          (color ?? primaryColor).withValues(alpha: 0.0),
        ],
      );

  /// Get gradient for bar chart
  static LinearGradient getBarGradient({Color? color}) => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: color != null
            ? [color, color.withValues(alpha: 0.7)]
            : barGradientColors,
      );

  /// Get color based on trend
  static Color getTrendColor(double? changePercentage) {
    if (changePercentage == null) return neutralColor;
    if (changePercentage > 0) return positiveColor;
    if (changePercentage < 0) return negativeColor;
    return neutralColor;
  }

  /// Get gradient for heatmap based on intensity (0-1)
  static Color getHeatmapColor(double intensity) {
    if (intensity <= 0) return heatmapEmptyColor;
    if (intensity < 0.33) return heatmapLowColor;
    if (intensity < 0.66) return heatmapMediumColor;
    return heatmapHighColor;
  }
}

/// Legend position options
enum LegendPosition {
  top,
  bottom,
  left,
  right,
}

/// Helper class for creating styled chart data
class StatisticsChartDataHelper {
  StatisticsChartDataHelper._();

  /// Get default line chart data with styling applied
  static LineChartData getDefaultLineChartData({
    required List<LineChartBarData> lineBarsData,
    required List<String> xLabels,
    double minY = 0,
    double? maxY,
  }) =>
      LineChartData(
        lineBarsData: lineBarsData,
        minX: 0,
        maxX: (xLabels.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        gridData: FlGridData(
          drawVerticalLine: StatisticsChartConfig.showVerticalGrid,
          horizontalInterval: maxY != null ? (maxY - minY) / 4 : null,
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
              interval: _getInterval(xLabels.length),
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index >= 0 && index < xLabels.length) {
                  return Text(
                    xLabels[index],
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
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: maxY != null ? (maxY - minY) / 4 : null,
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
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) => touchedSpots
                .map(
                  (spot) => LineTooltipItem(
                    spot.y.toStringAsFixed(1),
                    TextStyle(
                      color: StatisticsChartConfig.tooltipTextColor,
                      fontSize: 12,
                    ),
                  ),
                )
                .toList(),
          ),
        ),
      );

  /// Get default bar chart data with styling applied
  static BarChartData getDefaultBarChartData({
    required List<BarChartGroupData> barGroups,
    required List<String> xLabels,
    double minY = 0,
    double? maxY,
  }) =>
      BarChartData(
        barGroups: barGroups,
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
              interval: _getInterval(xLabels.length),
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index >= 0 && index < xLabels.length) {
                  return Text(
                    xLabels[index],
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

  /// Calculate interval for X axis labels
  static double _getInterval(int labelCount) {
    const maxLabels = StatisticsChartConfig.maxXLabels;
    if (labelCount <= maxLabels) return 1;
    return (labelCount / maxLabels).ceil().toDouble();
  }
}
