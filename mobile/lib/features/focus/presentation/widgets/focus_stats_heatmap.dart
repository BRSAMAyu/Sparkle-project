import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';

/// Heatmap widget showing focus activity over the past N days
/// Similar to GitHub contribution graph
class FocusStatsHeatmap extends StatelessWidget {
  const FocusStatsHeatmap({
    required this.data,
    this.daysToShow = 90,
    this.lowColor,
    this.highColor,
    super.key,
  });

  final Map<DateTime, double> data; // DateTime -> minutes
  final int daysToShow;
  final Color? lowColor;
  final Color? highColor;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    if (data.isEmpty) {
      return SizedBox(
        height: 140,
        child: Center(
          child: Text(
            l10n.commonNoData,
            style: TextStyle(color: DS.neutral400),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: _buildLegend(context),
        ),
        const SizedBox(height: DS.md),
        _buildHeatmapGrid(context),
      ],
    );
  }

  Widget _buildLegend(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            context.l10n.focusStatsLegendLow,
            style: TextStyle(fontSize: 10, color: DS.neutral500),
          ),
          const SizedBox(width: DS.xs),
          ...List.generate(5, (index) {
            final intensity = index / 4;
            return Container(
              width: 10,
              height: 10,
              margin: const EdgeInsets.only(left: 2),
              decoration: BoxDecoration(
                color: _getColorForIntensity(intensity),
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
          const SizedBox(width: DS.xs),
          Text(
            context.l10n.focusStatsLegendHigh,
            style: TextStyle(fontSize: 10, color: DS.neutral500),
          ),
        ],
      );

  Widget _buildHeatmapGrid(BuildContext context) {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: daysToShow));

    // Calculate weeks
    final totalDays = daysToShow;
    final weeks = (totalDays / 7).ceil();

    return SizedBox(
      height: 120,
      child: Row(
        children: List.generate(
          weeks,
          (weekIndex) => Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(7, (dayIndex) {
                final dayOffset = weekIndex * 7 + dayIndex;
                if (dayOffset >= totalDays) {
                  return const SizedBox(width: 12, height: 12);
                }

                final date = startDate.add(Duration(days: dayOffset));
                final minutes = _getMinutesForDate(date);
                final intensity = _calculateIntensity(minutes);

                return _buildDayCell(context, date, minutes, intensity);
              }),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDayCell(
    BuildContext context,
    DateTime date,
    double minutes,
    double intensity,
  ) =>
      Tooltip(
        message:
            '${Formatters.formatDateShort(date)}\n${context.l10n.focusStatsDurationTooltip(minutes.toInt())}',
        child: Container(
          width: 12,
          height: 12,
          margin: const EdgeInsets.all(1),
          decoration: BoxDecoration(
            color: _getColorForIntensity(intensity),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
      );

  double _getMinutesForDate(DateTime date) {
    // Find data for this date (ignoring time)
    final dateKey = data.keys.firstWhere(
      (key) => _isSameDay(key, date),
      orElse: () => DateTime(1970),
    );
    return data[dateKey] ?? 0.0;
  }

  double _calculateIntensity(double minutes) {
    // Normalize: 0 minutes = 0, 180+ minutes = 1.0
    const maxMinutes = 180.0;
    return minutes.clamp(0.0, maxMinutes) / maxMinutes;
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  Color _getColorForIntensity(double intensity) {
    final low = lowColor ?? DS.neutral300;
    final high = highColor ?? DS.brandPrimary;
    if (intensity == 0) return low;
    return Color.lerp(low, high, intensity) ?? low;
  }
}
