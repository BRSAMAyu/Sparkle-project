import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 学习活跃度热力图 - GitHub 风格
///
/// 显示过去一段时间（默认90天）的学习活跃度
/// 颜色深度表示学习强度
class EngagementHeatmap extends StatelessWidget {
  const EngagementHeatmap({
    required this.data,
    this.daysToShow = 90,
    this.lowColor = const Color(0xFFE0E0E0),
    this.highColor = const Color(0xFF2E7D32),
    super.key,
  });

  final Map<DateTime, double> data; // DateTime -> intensity (0-1)
  final int daysToShow;
  final Color lowColor;
  final Color highColor;

  @override
  Widget build(BuildContext context) => Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(Icons.calendar_month, color: DS.brandPrimary.shade600, size: 24),
                SizedBox(width: DS.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '学习活跃度',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      Text(
                        '过去 90 天的学习记录',
                        style: TextStyle(fontSize: 12, color: DS.brandPrimary),
                      ),
                    ],
                  ),
                ),
                _buildLegend(),
              ],
            ),
            SizedBox(height: DS.lg),

            // Heatmap Grid
            _buildHeatmapGrid(),

            SizedBox(height: DS.md),

            // Stats Summary
            _buildStatsSummary(),
          ],
        ),
      ),
    );

  Widget _buildHeatmapGrid() {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: daysToShow));

    // Calculate weeks
    final totalDays = daysToShow;
    final weeks = (totalDays / 7).ceil();

    return SizedBox(
      height: 140, // 7 days * 16px + spacing
      child: Row(
        children: List.generate(weeks, (weekIndex) => Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: List.generate(7, (dayIndex) {
                final dayOffset = weekIndex * 7 + dayIndex;
                if (dayOffset >= totalDays) {
                  return SizedBox(width: 16, height: 16);
                }

                final date = startDate.add(Duration(days: dayOffset));
                final intensity = _getIntensity(date);

                return _buildDayCell(date, intensity);
              }),
            ),
          ),),
      ),
    );
  }

  Widget _buildDayCell(DateTime date, double intensity) => Tooltip(
      message: '${_formatDate(date)}\n学习强度: ${_getIntensityLabel(intensity)}',
      child: Container(
        width: 14,
        height: 14,
        margin: EdgeInsets.all(1),
        decoration: BoxDecoration(
          color: _getColorForIntensity(intensity),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );

  Widget _buildLegend() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('低', style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
        SizedBox(width: DS.xs),
        ...List.generate(5, (index) {
          final intensity = index / 4;
          return Container(
            width: 12,
            height: 12,
            margin: EdgeInsets.only(left: DS.xs),
            decoration: BoxDecoration(
              color: _getColorForIntensity(intensity),
              borderRadius: BorderRadius.circular(2),
            ),
          );
        }),
        SizedBox(width: DS.xs),
        Text('高', style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
      ],
    );
  }

  Widget _buildStatsSummary() {
    final stats = _calculateStats();

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildStatItem('活跃天数', '${stats['activeDays']}', Icons.check_circle),
        _buildStatItem('最长连续', '${stats['longestStreak']} 天', Icons.local_fire_department),
        _buildStatItem('当前连续', '${stats['currentStreak']} 天', Icons.trending_up),
      ],
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) => Column(
      children: [
        Icon(icon, size: 20, color: DS.brandPrimary.shade600),
        SizedBox(height: DS.xs),
        Text(
          value,
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 10, color: DS.brandPrimary),
        ),
      ],
    );

  // Helper Methods
  double _getIntensity(DateTime date) {
    // Find data for this date (ignoring time)
    final dateKey = data.keys.firstWhere(
      (key) => _isSameDay(key, date),
      orElse: () => DateTime(1970),
    );

    return data[dateKey] ?? 0.0;
  }

  bool _isSameDay(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;

  Color _getColorForIntensity(double intensity) {
    if (intensity == 0) return lowColor;
    return Color.lerp(lowColor, highColor, intensity) ?? lowColor;
  }

  String _getIntensityLabel(double intensity) {
    if (intensity == 0) return '无学习';
    if (intensity < 0.25) return '轻度';
    if (intensity < 0.5) return '中度';
    if (intensity < 0.75) return '高度';
    return '非常活跃';
  }

  String _formatDate(DateTime date) => '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  Map<String, int> _calculateStats() {
    final now = DateTime.now();
    final startDate = now.subtract(Duration(days: daysToShow));

    var activeDays = 0;
    var longestStreak = 0;
    var currentStreak = 0;
    var tempStreak = 0;

    // Calculate stats
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

    // Calculate current streak (from today backwards)
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
