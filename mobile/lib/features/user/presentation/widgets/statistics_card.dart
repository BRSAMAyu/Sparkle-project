import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

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
                '本周成长趋势',
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

  static const _days = ['一', '二', '三', '四', '五', '六', '日'];
  static const _dayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
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
                  if (value.toInt() >= 0 && value.toInt() < _days.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        _days[value.toInt()],
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
              getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
                return LineTooltipItem(
                  '${_dayLabels[spot.x.toInt()]}\n学习指数 ${spot.y.toStringAsFixed(0)}',
                  TextStyle(
                    color: DS.textPrimary,
                    fontSize: 12,
                    fontWeight: DS.fontWeightMedium,
                    height: 1.35,
                  ),
                );
              }).toList(),
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
