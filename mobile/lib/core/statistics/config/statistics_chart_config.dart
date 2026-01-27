import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';

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
  static const Color primaryColor = Color(0xFF6366F1); // Indigo 500

  /// Secondary color for comparison data
  static const Color secondaryColor = Color(0xFFEC4899); // Pink 500

  /// Tertiary color for additional data series
  static const Color tertiaryColor = Color(0xFF10B981); // Emerald 500

  /// Quaternary color for more data series
  static const Color quaternaryColor = Color(0xFFF59E0B); // Amber 500

  /// Background color for chart containers
  static const Color backgroundColor = Color(0xFFFAFAFA); // Neutral 50

  /// Card background color
  static const Color cardColor = Colors.white;

  /// Grid line color (subtle)
  static const Color gridColor = Color(0xFFE5E7EB); // Neutral 200

  /// Axis label color
  static const Color axisLabelColor = Color(0xFF9CA3AF); // Neutral 400

  /// Tooltip background color
  static const Color tooltipBgColor = Color(0xFF1F2937); // Gray 800

  /// Tooltip text color
  static const Color tooltipTextColor = Colors.white;

  /// Positive trend color (green)
  static const Color positiveColor = Color(0xFF10B981); // Emerald 500

  /// Negative trend color (red)
  static const Color negativeColor = Color(0xFFEF4444); // Red 500

  /// Neutral trend color
  static const Color neutralColor = Color(0xFF9CA3AF); // Neutral 400

  /// Empty state color (for no data)
  static const Color emptyStateColor = Color(0xFFE5E7EB); // Neutral 200

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
  static const Color lineGradientStart = Color(0xFF6366F1);

  /// Line chart colors gradient end
  static const Color lineGradientEnd = Color(0xFF818CF8);

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
  static const List<Color> barGradientColors = [
    Color(0xFF6366F1), // Indigo 500
    Color(0xFF818CF8), // Indigo 400
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

  /// Pie chart colors (categorical)
  static const List<Color> pieColors = [
    Color(0xFF6366F1), // Indigo 500
    Color(0xFFEC4899), // Pink 500
    Color(0xFF10B981), // Emerald 500
    Color(0xFFF59E0B), // Amber 500
    Color(0xFF3B82F6), // Blue 500
    Color(0xFF8B5CF6), // Violet 500
    Color(0xFFEF4444), // Red 500
    Color(0xFF14B8A6), // Teal 500
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
  static const Color heatmapEmptyColor = Color(0xFFE5E7EB);

  /// Heatmap low activity color
  static const Color heatmapLowColor = Color(0xFFC7D2FE);

  /// Heatmap medium activity color
  static const Color heatmapMediumColor = Color(0xFF6366F1);

  /// Heatmap high activity color
  static const Color heatmapHighColor = Color(0xFF4338CA);

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
  static const TextStyle legendTextStyle = TextStyle(
    fontSize: 12,
    color: Color(0xFF6B7280), // Neutral 500
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
  static Color getColorForIndex(int index) => pieColors[index % pieColors.length];

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
  }) => LineChartData(
      lineBarsData: lineBarsData,
      minX: 0,
      maxX: (xLabels.length - 1).toDouble(),
      minY: minY,
      maxY: maxY,
      gridData: FlGridData(
        drawVerticalLine: StatisticsChartConfig.showVerticalGrid,
        horizontalInterval: maxY != null ? (maxY - minY) / 4 : null,
        getDrawingHorizontalLine: (value) => const FlLine(
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
                  style: const TextStyle(
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
                style: const TextStyle(
                  fontSize: StatisticsChartConfig.axisLabelSize,
                  color: StatisticsChartConfig.axisLabelColor,
                ),
              ),
          ),
        ),
        topTitles: const AxisTitles(
          
        ),
        rightTitles: const AxisTitles(
          
        ),
      ),
      borderData: FlBorderData(show: false),
      lineTouchData: LineTouchData(
        touchTooltipData: LineTouchTooltipData(
          getTooltipItems: (touchedSpots) => touchedSpots.map((spot) => LineTooltipItem(
                spot.y.toStringAsFixed(1),
                TextStyle(
                  color: StatisticsChartConfig.tooltipTextColor,
                  fontSize: 12,
                ),
              )).toList(),
        ),
      ),
    );

  /// Get default bar chart data with styling applied
  static BarChartData getDefaultBarChartData({
    required List<BarChartGroupData> barGroups,
    required List<String> xLabels,
    double minY = 0,
    double? maxY,
  }) => BarChartData(
      barGroups: barGroups,
      minY: minY,
      maxY: maxY,
      gridData: FlGridData(
        drawVerticalLine: false,
        getDrawingHorizontalLine: (value) => const FlLine(
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
                  style: const TextStyle(
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
                style: const TextStyle(
                  fontSize: StatisticsChartConfig.axisLabelSize,
                  color: StatisticsChartConfig.axisLabelColor,
                ),
              ),
          ),
        ),
        topTitles: const AxisTitles(
          
        ),
        rightTitles: const AxisTitles(
          
        ),
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
