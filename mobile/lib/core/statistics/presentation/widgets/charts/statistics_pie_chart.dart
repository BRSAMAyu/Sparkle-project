import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Data class for pie chart sections
class PieChartSection {

  const PieChartSection({
    required this.value,
    required this.label,
    this.color,
    this.icon,
  });
  /// Value of this section
  final double value;

  /// Label for this section
  final String label;

  /// Color for this section (null = use default)
  final Color? color;

  /// Icon to show in the center when selected
  final IconData? icon;
}

/// Pie chart widget for statistics data visualization
class StatisticsPieChart extends StatelessWidget {

  const StatisticsPieChart({
    required this.sections, super.key,
    this.radius,
    this.innerRadius,
    this.isDonut = true,
    this.centerText,
    this.centerWidget,
    this.showLabels = true,
    this.showLegend = true,
    this.legendPosition = LegendPosition.bottom,
  });
  /// Data sections to display
  final List<PieChartSection> sections;

  /// Radius of the pie chart
  final double? radius;

  /// Inner radius (0 = pie chart, >0 = donut chart)
  final double? innerRadius;

  /// Whether to show the chart as a donut
  final bool isDonut;

  /// Text to show in the center of donut chart
  final String? centerText;

  /// Optional center widget for donut chart
  final Widget? centerWidget;

  /// Whether to show labels on sections
  final bool showLabels;

  /// Whether to show legend
  final bool showLegend;

  /// Legend position
  final LegendPosition legendPosition;

  @override
  Widget build(BuildContext context) {
    if (sections.isEmpty) {
      return _buildEmptyState();
    }

    final chart = _buildChart();

    if (!showLegend) {
      return chart;
    }

    switch (legendPosition) {
      case LegendPosition.bottom:
      case LegendPosition.top:
        return Column(
          children: [
            if (legendPosition == LegendPosition.top) _buildLegend(),
            Flexible(child: chart),
            if (legendPosition == LegendPosition.bottom) _buildLegend(),
          ],
        );
      case LegendPosition.left:
      case LegendPosition.right:
        return Row(
          children: [
            if (legendPosition == LegendPosition.left) _buildLegend(),
            Expanded(child: chart),
            if (legendPosition == LegendPosition.right) _buildLegend(),
          ],
        );
    }
  }

  Widget _buildChart() {
    final effectiveRadius = radius ??
        (isDonut ? StatisticsChartConfig.pieRadius : 80);
    final effectiveInnerRadius = innerRadius ??
        (isDonut ? StatisticsChartConfig.pieInnerRadius : 0);

    return SizedBox(
      height: effectiveRadius * 2 + 40,
      child: PieChart(
        PieChartData(
          sectionsSpace: StatisticsChartConfig.pieSectionSpacing,
          centerSpaceRadius: effectiveInnerRadius,
          sections: _buildSections(),
          pieTouchData: PieTouchData(
            touchCallback: (FlTouchEvent event, pieTouchResponse) {
              // Handle touch events if needed
            },
            enabled: true,
          ),
        ),
      ),
    );
  }

  List<PieChartSectionData> _buildSections() {
    final total = sections.fold<double>(0, (sum, s) => sum + s.value);
    const colors = StatisticsChartConfig.pieColors;

    double startAngle = 0;

    return sections.asMap().entries.map((entry) {
      final index = entry.key;
      final section = entry.value;
      final percentage = total > 0 ? (section.value / total) : 0.0;
      final angle = percentage * 360;
      final midAngle = startAngle + angle / 2;

      final color = section.color ?? colors[index % colors.length];

      final sectionData = PieChartSectionData(
        value: section.value,
        title: showLabels ? '${(percentage * 100).toInt()}%' : '',
        radius: effectiveRadius(),
        color: color,
        titleStyle: TextStyle(
          fontSize: showLabels ? 12 : 0,
          fontWeight: DS.fontWeightMedium,
          color: DS.white,
        ),
        badgeWidget: _buildBadge(section, percentage, midAngle),
        badgePositionPercentageOffset: isDonut ? 0.8 : .5,
      );

      startAngle += angle;
      return sectionData;
    }).toList();
  }

  double effectiveRadius() => radius ?? StatisticsChartConfig.pieRadius;

  Widget? _buildBadge(PieChartSection section, double percentage, double angle) {
    if (!showLabels) return null;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: DS.xs),
      decoration: BoxDecoration(
        color: section.color ??
            StatisticsChartConfig.pieColors[
                sections.indexOf(section) % StatisticsChartConfig.pieColors.length],
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        section.label,
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: Colors.white,
        ),
      ),
    );
  }

  Widget _buildLegend() {
    const colors = StatisticsChartConfig.pieColors;

    return Padding(
      padding: const EdgeInsets.all(DS.md),
      child: Wrap(
        spacing: DS.lg,
        runSpacing: DS.sm,
        alignment: WrapAlignment.center,
        children: sections.map((section) {
          final index = sections.indexOf(section);
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: StatisticsChartConfig.legendMarkerSize,
                height: StatisticsChartConfig.legendMarkerSize,
                decoration: BoxDecoration(
                  color: section.color ?? colors[index % colors.length],
                  borderRadius: BorderRadius.circular(
                    StatisticsChartConfig.legendMarkerRadius,
                  ),
                ),
              ),
              const SizedBox(width: DS.xs),
              Text(
                section.label,
                style: StatisticsChartConfig.legendTextStyle,
              ),
            ],
          );
        }).toList(),
      ),
    );
  }

  Widget _buildEmptyState() => Container(
      height: 200,
      alignment: Alignment.center,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.pie_chart,
            size: 48,
            color: StatisticsChartConfig.emptyStateColor,
          ),
          const SizedBox(height: DS.md),
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

/// Donut chart with center content
class StatisticsDonutChart extends StatelessWidget {

  const StatisticsDonutChart({
    required this.sections, super.key,
    this.radius,
    this.centerText,
    this.centerValue,
    this.centerUnit,
    this.centerWidget,
  });
  /// Data sections to display
  final List<PieChartSection> sections;

  /// Radius of the chart
  final double? radius;

  /// Text to show in the center
  final String? centerText;

  /// Value to show in the center (large number)
  final String? centerValue;

  /// Unit for the center value
  final String? centerUnit;

  /// Widget to show in the center
  final Widget? centerWidget;

  @override
  Widget build(BuildContext context) => StatisticsPieChart(
      sections: sections,
      radius: radius,
      centerWidget: centerWidget ??
          _buildDefaultCenterWidget(),
    );

  Widget _buildDefaultCenterWidget() => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (centerText != null)
          Text(
            centerText!,
            style: DS.captionStyle.copyWith(
              color: DS.neutral500,
            ),
          ),
        if (centerValue != null) ...[
          const SizedBox(height: DS.xs),
          Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                centerValue!,
                style: DS.headlineStyle.copyWith(
                  fontSize: 32,
                  fontWeight: DS.fontWeightBold,
                  color: DS.neutral800,
                ),
              ),
              if (centerUnit != null) ...[
                const SizedBox(width: 2),
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    centerUnit!,
                    style: DS.captionStyle.copyWith(
                      color: DS.neutral400,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ],
    );
}
