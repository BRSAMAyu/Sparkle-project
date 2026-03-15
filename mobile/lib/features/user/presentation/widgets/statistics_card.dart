import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class StatisticsCard extends StatelessWidget {
  const StatisticsCard({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final trendAccent =
        isDark ? const Color(0xFF94AFD2) : const Color(0xFF7A93B4);
    final trendAccentSoft =
        isDark ? const Color(0xFF8EA18E) : const Color(0xFF9DB1C9);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
        border: Border.all(color: trendAccent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: trendAccent.withValues(alpha: 0.14),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.show_chart_rounded,
                  color: trendAccent,
                  size: 16,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.statisticsWeeklyGrowthTrend,
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          SizedBox(
            height: 120,
            child: _WeeklyTrendChart(
              trendAccent: trendAccent,
              trendAccentSoft: trendAccentSoft,
            ),
          ),
        ],
      ),
    );
  }
}

class _WeeklyTrendChart extends StatelessWidget {
  const _WeeklyTrendChart({
    required this.trendAccent,
    required this.trendAccentSoft,
  });

  final Color trendAccent;
  final Color trendAccentSoft;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final locale = I18nService.instance.currentLocale.languageCode;
    final shortDays = List.generate(
      7,
      (index) => DateFormat.E(locale).format(DateTime(2026, 1, 5 + index)),
    );
    final longDays = List.generate(
      7,
      (index) => DateFormat.EEEE(locale).format(DateTime(2026, 1, 5 + index)),
    );
    final spots = [
      const FlSpot(0, 3),
      const FlSpot(1, 5),
      const FlSpot(2, 2),
      const FlSpot(3, 8),
      const FlSpot(4, 4),
      const FlSpot(5, 7),
      const FlSpot(6, 9),
    ];

    return RepaintBoundary(
      child: LineChart(
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
                  if (value.toInt() >= 0 && value.toInt() < shortDays.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        shortDays[value.toInt()],
                        style: TextStyle(
                          color: DS.textSecondary,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    );
                  }
                  return const Text('');
                },
                interval: 1,
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              tooltipBgColor: isDark
                  ? DS.surfacePrimaryElevated.withValues(alpha: 0.94)
                  : DS.surfacePrimary.withValues(alpha: 0.98),
              tooltipRoundedRadius: 14,
              tooltipPadding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              tooltipMargin: 10,
              fitInsideHorizontally: true,
              fitInsideVertically: true,
              getTooltipItems: (touchedSpots) => touchedSpots.map((spot) => LineTooltipItem(
                  '${longDays[spot.x.toInt()]}\n${context.l10n.statisticsLearningIndex(spot.y.toStringAsFixed(0))}',
                  TextStyle(
                    color: DS.textPrimary,
                    fontSize: 12,
                    fontWeight: DS.fontWeightMedium,
                    height: 1.35,
                  ),
                ),).toList(),
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              gradient: LinearGradient(
                colors: [trendAccent, trendAccentSoft],
              ),
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                getDotPainter: (spot, percent, barData, index) =>
                    FlDotCirclePainter(
                  radius: 4,
                  color: DS.surfacePrimary,
                  strokeWidth: 2,
                  strokeColor: trendAccent,
                ),
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [
                    trendAccent.withValues(alpha: 0.20),
                    trendAccentSoft.withValues(alpha: 0.06),
                    trendAccentSoft.withValues(alpha: 0),
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
            ),
          ],
          minX: 0,
          maxX: 6,
          minY: 0,
          maxY: 10,
        ),
      ),
    );
  }
}
