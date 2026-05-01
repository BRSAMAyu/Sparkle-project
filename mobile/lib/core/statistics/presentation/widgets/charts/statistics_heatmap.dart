import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Data point for heatmap visualization
class HeatmapData {
  const HeatmapData({
    required this.x,
    required this.y,
    required this.value,
    this.label,
    this.timestamp,
  });

  /// X coordinate (e.g., day of week, hour of day)
  final int x;

  /// Y coordinate (e.g., week number, day of month)
  final int y;

  /// Value/intensity at this coordinate (0-1 normalized)
  final double value;

  /// Optional label for tooltip
  final String? label;

  /// Optional timestamp for the data point
  final DateTime? timestamp;
}

/// Heatmap widget for statistics visualization (like GitHub contribution graph)
class StatisticsHeatmap extends StatelessWidget {
  const StatisticsHeatmap({
    required this.data,
    required this.columns,
    super.key,
    this.rows,
    this.xLabels,
    this.yLabels,
    this.cellSize,
    this.cellSpacing,
    this.showLegend = true,
    this.legendPosition = LegendPosition.right,
    this.emptyColor,
    this.lowColor,
    this.mediumColor,
    this.highColor,
    this.onTap,
  });

  /// 2D grid of data points
  final List<HeatmapData> data;

  /// Number of columns (x-axis)
  final int columns;

  /// Number of rows (y-axis)
  final int? rows;

  /// X-axis labels
  final List<String>? xLabels;

  /// Y-axis labels
  final List<String>? yLabels;

  /// Cell size
  final double? cellSize;

  /// Cell spacing
  final double? cellSpacing;

  /// Whether to show a color legend
  final bool showLegend;

  /// Legend position
  final LegendPosition legendPosition;

  /// Color for empty/zero values
  final Color? emptyColor;

  /// Low intensity color
  final Color? lowColor;

  /// Medium intensity color
  final Color? mediumColor;

  /// High intensity color
  final Color? highColor;

  /// Callback when a cell is tapped
  final void Function(HeatmapData)? onTap;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) {
      return _buildEmptyState(context);
    }

    final effectiveRows = rows ?? _calculateRows();
    final effectiveCellSize = cellSize ?? StatisticsChartConfig.heatmapCellSize;
    final effectiveCellSpacing =
        cellSpacing ?? StatisticsChartConfig.heatmapCellSpacing;

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (yLabels != null)
          _buildYLabels(effectiveRows, effectiveCellSize, effectiveCellSpacing),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeatmapGrid(
              effectiveRows,
              effectiveCellSize,
              effectiveCellSpacing,
            ),
            if (showLegend && legendPosition == LegendPosition.right)
              Padding(
                padding: const EdgeInsets.only(left: DS.md),
                child: _buildLegend(context),
              ),
          ],
        ),
        if (xLabels != null)
          _buildXLabels(columns, effectiveCellSize, effectiveCellSpacing),
      ],
    );

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: content,
    );
  }

  int _calculateRows() {
    if (data.isEmpty) return 7;
    return data.map((d) => d.y).reduce((a, b) => a > b ? a : b) + 1;
  }

  Widget _buildHeatmapGrid(int rows, double cellSize, double cellSpacing) {
    // Build a lookup map for quick access
    final dataMap = <String, HeatmapData>{};
    for (final item in data) {
      dataMap['${item.x}_${item.y}'] = item;
    }

    return Column(
      children: List.generate(
        rows,
        (y) => Padding(
          padding: EdgeInsets.only(bottom: cellSpacing),
          child: Row(
            children: List.generate(columns, (x) {
              final key = '${x}_$y';
              final item = dataMap[key];

              return Padding(
                padding: EdgeInsets.only(right: cellSpacing),
                child: _buildCell(
                    item ?? HeatmapData(x: x, y: y, value: 0), cellSize,),
              );
            }),
          ),
        ),
      ),
    );
  }

  Widget _buildCell(HeatmapData item, double size) {
    final color = _getColorForValue(item.value);

    return GestureDetector(
      onTap: () => onTap?.call(item),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(
            StatisticsChartConfig.heatmapCellRadius,
          ),
        ),
        child: AnimatedContainer(
          duration: StatisticsAnimationConfig.fast,
          curve: StatisticsAnimationConfig.easeOut,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(
              StatisticsChartConfig.heatmapCellRadius,
            ),
            border: item.value > 0
                ? Border.all(
                    color: color,
                  )
                : null,
          ),
        ),
      ),
    );
  }

  Color _getColorForValue(double value) {
    if (value <= 0) {
      return emptyColor ?? StatisticsChartConfig.heatmapEmptyColor;
    }
    if (value < 0.33) return lowColor ?? StatisticsChartConfig.heatmapLowColor;
    if (value < 0.66) {
      return mediumColor ?? StatisticsChartConfig.heatmapMediumColor;
    }
    return highColor ?? StatisticsChartConfig.heatmapHighColor;
  }

  Widget _buildLegend(BuildContext context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildLegendCell(
            StatisticsChartConfig.heatmapEmptyColor,
            '0',
          ),
          _buildLegendCell(
            lowColor ?? StatisticsChartConfig.heatmapLowColor,
            context.l10n.statisticsLegendLow,
          ),
          _buildLegendCell(
            mediumColor ?? StatisticsChartConfig.heatmapMediumColor,
            context.l10n.statisticsLegendMedium,
          ),
          _buildLegendCell(
            highColor ?? StatisticsChartConfig.heatmapHighColor,
            context.l10n.statisticsLegendHigh,
          ),
        ],
      );

  Widget _buildLegendCell(Color color, String label) => Padding(
        padding: const EdgeInsets.only(bottom: DS.xs),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: StatisticsChartConfig.heatmapCellSize,
              height: StatisticsChartConfig.heatmapCellSize,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(
                  StatisticsChartConfig.heatmapCellRadius,
                ),
              ),
            ),
            const SizedBox(width: DS.xs),
            Text(
              label,
              style: DS.captionStyle.copyWith(
                color: DS.neutral500,
                fontSize: 10,
              ),
            ),
          ],
        ),
      );

  Widget _buildXLabels(int count, double cellSize, double cellSpacing) {
    final labels = xLabels ?? [];
    final effectiveCellSize = cellSize + cellSpacing;

    return Padding(
      padding: EdgeInsets.only(top: DS.sm, left: effectiveCellSize),
      child: Row(
        children: List.generate(count, (index) {
          final effectiveIndex = index % labels.length;
          return SizedBox(
            width: effectiveCellSize,
            child: Center(
              child: Text(
                labels.isNotEmpty ? labels[effectiveIndex] : '',
                style: DS.captionStyle.copyWith(
                  color: DS.neutral400,
                  fontSize: 10,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildYLabels(int count, double cellSize, double cellSpacing) {
    final labels = yLabels ?? [];
    final effectiveCellSize = cellSize + cellSpacing;

    return Column(
      children: List.generate(count, (index) {
        final effectiveIndex = index % labels.length;
        return SizedBox(
          height: effectiveCellSize,
          child: Center(
            child: Text(
              labels.isNotEmpty ? labels[effectiveIndex] : '',
              style: DS.captionStyle.copyWith(
                color: DS.neutral400,
                fontSize: 10,
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildEmptyState(BuildContext context) => Container(
        height: 150,
        alignment: Alignment.center,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.grid_on_outlined,
              size: 48,
              color: StatisticsChartConfig.emptyStateColor,
            ),
            const SizedBox(height: DS.md),
            Text(
              context.l10n.statisticsNoData,
              style: DS.bodyStyle.copyWith(
                color: DS.neutral400,
              ),
            ),
          ],
        ),
      );
}

/// GitHub-style contribution heatmap (weekly)
class StatisticsContributionHeatmap extends StatelessWidget {
  const StatisticsContributionHeatmap({
    required this.dailyData,
    required this.startDate,
    super.key,
    this.endDate,
    this.cellSize,
    this.onTap,
  });

  /// Daily activity data (one value per day)
  final Map<DateTime, double> dailyData;

  /// Start date for the heatmap
  final DateTime startDate;

  /// End date for the heatmap (default: today)
  final DateTime? endDate;

  /// Cell size
  final double? cellSize;

  /// Callback when a cell is tapped
  final void Function(DateTime date, double value)? onTap;

  @override
  Widget build(BuildContext context) {
    final end = endDate ?? DateTime.now();
    final heatmapData = _convertToHeatmapData(startDate, end);

    final l10n = AppLocalizations.of(context);
    final xLabels = [l10n!.statisticsChartMon, l10n.statisticsChartWed, l10n.statisticsChartFri];
    final yLabels = [
      l10n.statisticsChartMonth1,
      l10n.statisticsChartMonth2,
      l10n.statisticsChartMonth3,
      l10n.statisticsChartMonth4,
      l10n.statisticsChartMonth5,
      l10n.statisticsChartMonth6,
      l10n.statisticsChartMonth7,
      l10n.statisticsChartMonth8,
      l10n.statisticsChartMonth9,
      l10n.statisticsChartMonth10,
      l10n.statisticsChartMonth11,
      l10n.statisticsChartMonth12,
    ];

    return StatisticsHeatmap(
      data: heatmapData,
      columns: 7, // Days of week
      xLabels: xLabels,
      yLabels: yLabels,
      cellSize: cellSize,
      legendPosition: LegendPosition.bottom,
      onTap: (item) {
        if (item.timestamp != null && onTap != null) {
          onTap!(item.timestamp!, item.value);
        }
      },
    );
  }

  List<HeatmapData> _convertToHeatmapData(DateTime start, DateTime end) {
    final data = <HeatmapData>[];

    // Normalize start to Monday
    final normalizedStart = start.subtract(Duration(days: start.weekday - 1));

    // Calculate week and day indices
    var current = normalizedStart;
    var weekIndex = 0;

    while (current.isBefore(end) || current.isAtSameMomentAs(end)) {
      final dayOfWeek = current.weekday - 1; // 0 = Monday

      // Find the value for this date
      final value =
          dailyData[DateTime(current.year, current.month, current.day)] ?? 0.0;

      data.add(
        HeatmapData(
          x: dayOfWeek,
          y: weekIndex,
          value: value,
          timestamp: current,
          label: '${current.month}/${current.day}',
        ),
      );

      // Move to next day
      current = current.add(const Duration(days: 1));
      if (current.weekday == 1) {
        weekIndex++;
      }
    }

    return data;
  }
}
