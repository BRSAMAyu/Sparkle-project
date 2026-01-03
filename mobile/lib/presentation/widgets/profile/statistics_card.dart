import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class StatisticsCard extends StatelessWidget {
  const StatisticsCard({super.key});

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.show_chart_rounded,
                  color: DS.primaryBase,
                  size: 16,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '本周成长趋势',
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.neutral900,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          const SizedBox(
            height: 120,
            child: _WeeklyTrendChart(),
          ),
        ],
      ),
    );
}

class _WeeklyTrendChart extends StatelessWidget {
  const _WeeklyTrendChart();

  @override
  Widget build(BuildContext context) {
    // Mock Data: [3, 5, 2, 8, 4, 7, 9]
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
                  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
                  if (value.toInt() >= 0 && value.toInt() < days.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 8.0),
                      child: Text(
                        days[value.toInt()],
                        style: TextStyle(
                          color: DS.neutral500,
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
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
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              color: DS.primaryBase,
              barWidth: 3,
              isStrokeCapRound: true,
              dotData: FlDotData(
                getDotPainter: (spot, percent, barData, index) => FlDotCirclePainter(
                    radius: 4,
                    color: DS.brandPrimaryConst,
                    strokeWidth: 2,
                    strokeColor: DS.primaryBase,
                  ),
              ),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  colors: [
                    DS.primaryBase.withValues(alpha: 0.2),
                    DS.primaryBase.withValues(alpha: 0.0),
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
