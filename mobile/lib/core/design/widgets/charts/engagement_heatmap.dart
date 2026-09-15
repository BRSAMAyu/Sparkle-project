import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class EngagementHeatmap extends StatelessWidget {
  const EngagementHeatmap({
    required this.data,
    this.daysToShow = 90,
    this.lowColor,
    this.highColor,
    this.onDayTap,
    super.key,
  });

  final Map<DateTime, double> data;
  final int daysToShow;
  final Color? lowColor;
  final Color? highColor;
  final ValueChanged<DateTime>? onDayTap;

  Color get _resolvedLowColor => lowColor ?? DS.surfaceTertiary;
  Color get _resolvedHighColor => highColor ?? DS.success;

  @override
  Widget build(BuildContext context) => Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Icon(
                    Icons.calendar_month,
                    color: DS.brandPrimary.shade600,
                    size: 24,
                  ),
                  const SizedBox(width: DS.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.l10n.engagementHeatmapTitle,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                        Text(
                          context.l10n.engagementHeatmapSubtitle,
                          style:
                              TextStyle(fontSize: 12, color: DS.brandPrimary),
                        ),
                      ],
                    ),
                  ),
                  _buildLegend(context),
                ],
              ),
              const SizedBox(height: DS.lg),

              // Heatmap Grid
              _buildHeatmapGrid(context),

              const SizedBox(height: DS.md),

              // Stats Summary
              _buildStatsSummary(context),
            ],
          ),
        ),
      );

  Widget _buildHeatmapGrid(BuildContext context) {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: daysToShow));

    final totalDays = daysToShow;
    final weeks = (totalDays / 7).ceil();

    return SizedBox(
      height: 140,
      child: Row(
        children: List.generate(
          weeks,
          (weekIndex) => Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(7, (dayIndex) {
                final dayOffset = weekIndex * 7 + dayIndex;
                if (dayOffset >= totalDays) {
                  return const SizedBox(width: 16, height: 16);
                }

                final date = startDate.add(Duration(days: dayOffset));
                final intensity = _getIntensity(date);

                return _buildDayCell(context, date, intensity);
              }),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDayCell(BuildContext context, DateTime date, double intensity) => Tooltip(
        message: '${_formatDate(date)}\n${context.l10n.engagementHeatmapIntensity(_getIntensityLabel(context, intensity))}',
        child: GestureDetector(
          onTap: onDayTap == null ? null : () => onDayTap!(date),
          child: Container(
            width: 14,
            height: 14,
            margin: const EdgeInsets.all(1),
            decoration: BoxDecoration(
              color: _getColorForIntensity(intensity),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
      );

  Widget _buildLegend(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(context.l10n.engagementLow, style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
          const SizedBox(width: DS.xs),
          ...List.generate(5, (index) {
            final intensity = index / 4;
            return Container(
              width: 12,
              height: 12,
              margin: const EdgeInsets.only(left: DS.xs),
              decoration: BoxDecoration(
                color: _getColorForIntensity(intensity),
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
          const SizedBox(width: DS.xs),
          Text(context.l10n.engagementHigh, style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
        ],
      );

  Widget _buildStatsSummary(BuildContext context) {
    final stats = _calculateStats();

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildStatItem(context.l10n.engagementActiveDays, '${stats['activeDays']}', Icons.check_circle),
        _buildStatItem(
          context.l10n.engagementLongestStreak,
          context.l10n.engagementDaysUnit(stats['longestStreak']!),
          Icons.local_fire_department,
        ),
        _buildStatItem(
          context.l10n.engagementCurrentStreak,
          context.l10n.engagementDaysUnit(stats['currentStreak']!),
          Icons.trending_up,
        ),
      ],
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) => Column(
        children: [
          Icon(icon, size: 20, color: DS.brandPrimary.shade600),
          const SizedBox(height: DS.xs),
          Text(
            value,
            style: const TextStyle(fontSize: 16, fontWeight: DS.fontWeightBold),
          ),
          Text(
            label,
            style: TextStyle(fontSize: 10, color: DS.brandPrimary),
          ),
        ],
      );

  double _getIntensity(DateTime date) {
    final dateKey = data.keys.firstWhere(
      (key) => _isSameDay(key, date),
      orElse: () => DateTime(1970),
    );

    return data[dateKey] ?? 0.0;
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  Color _getColorForIntensity(double intensity) {
    if (intensity == 0) return _resolvedLowColor;
    return Color.lerp(_resolvedLowColor, _resolvedHighColor, intensity) ??
        _resolvedLowColor;
  }

  String _getIntensityLabel(BuildContext context, double intensity) {
    if (intensity == 0) return context.l10n.engagementNone;
    if (intensity < 0.25) return context.l10n.engagementLight;
    if (intensity < 0.5) return context.l10n.engagementModerate;
    if (intensity < 0.75) return context.l10n.engagementHighIntensity;
    return context.l10n.engagementVeryActive;
  }

  String _formatDate(DateTime date) =>
      '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  Map<String, int> _calculateStats() {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: daysToShow));

    var activeDays = 0;
    var longestStreak = 0;
    var currentStreak = 0;
    var tempStreak = 0;

    for (var i = 0; i < daysToShow; i++) {
      final date = startDate.add(Duration(days: i));
      final intensity = _getIntensity(date);

      if (intensity > 0) {
        activeDays++;
        tempStreak++;
        if (tempStreak > longestStreak) {
          longestStreak = tempStreak;
        }
      } else {
        tempStreak = 0;
      }
    }

    for (var i = 0; i < daysToShow; i++) {
      final date = now.subtract(Duration(days: i));
      final intensity = _getIntensity(date);

      if (intensity > 0) {
        currentStreak++;
      } else {
        break;
      }
    }

    return {
      'activeDays': activeDays,
      'longestStreak': longestStreak,
      'currentStreak': currentStreak,
    };
  }
}
