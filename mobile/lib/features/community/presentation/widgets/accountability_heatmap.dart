import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 责任伙伴打卡热力图组件
///
/// 显示一年内每天打卡情况，类似 GitHub contribution graph
class AccountabilityHeatmap extends StatelessWidget {
  const AccountabilityHeatmap({
    super.key,
    required this.heatmap,
    required this.year,
  });

  final List<Map<String, dynamic>> heatmap;
  final int year;

  @override
  Widget build(BuildContext context) {
    if (heatmap.isEmpty) {
      return _buildEmptyState(context);
    }

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '打卡热力图 - $year',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                _buildLegend(context),
              ],
            ),
            const SizedBox(height: 16),
            _buildMonthlyHeatmaps(context),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            children: [
              Icon(
                Icons.calendar_today_outlined,
                size: 48,
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
              const SizedBox(height: 16),
              Text(
                '暂无打卡记录',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLegend(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '少',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(width: 4),
        _buildLegendDot(context, 0),
        const SizedBox(width: 2),
        _buildLegendDot(context, 1),
        const SizedBox(width: 2),
        _buildLegendDot(context, 2),
        const SizedBox(width: 2),
        _buildLegendDot(context, 3),
        const SizedBox(width: 4),
        Text(
          '多',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }

  Widget _buildLegendDot(BuildContext context, int level) {
    final colors = [
      Theme.of(context).colorScheme.surfaceContainerHighest,
      const Color(0xFF9BE9A8),
      const Color(0xFF40C463),
      const Color(0xFF30A14E),
      const Color(0xFF216E39),
    ];

    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: colors[level],
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _buildMonthlyHeatmaps(BuildContext context) {
    // 按月份分组
    final monthlyData = <String, List<Map<String, dynamic>>>{};
    for (var day in heatmap) {
      final dateStr = day['date'] as String;
      final date = DateTime.parse(dateStr);
      final monthKey = '${date.year}-${date.month.toString().padLeft(2, '0')}';
      monthlyData.putIfAbsent(monthKey, () => []).add(day);
    }

    // 创建12个月的网格
    return Column(
      children: [
        _buildMonthLabels(context),
        const SizedBox(height: 8),
        _buildWeeksGrid(context, monthlyData),
      ],
    );
  }

  Widget _buildMonthLabels(BuildContext context) {
    final months = ['一月', '二月', '三月', '四月', '五月', '六月',
                    '七月', '八月', '九月', '十月', '十一月', '十二月'];

    return Padding(
      padding: const EdgeInsets.only(left: 32), // Space for day labels
      child: Row(
        children: List.generate(12, (index) {
          return Expanded(
            child: Center(
              child: Text(
                months[index],
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildWeeksGrid(BuildContext context, Map<String, List<Map<String, dynamic>>> monthlyData) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Day labels
        _buildDayLabels(context),
        const SizedBox(width: 8),
        // Heatmap grid
        Expanded(
          child: _buildYearGrid(context, monthlyData),
        ),
      ],
    );
  }

  Widget _buildDayLabels(BuildContext context) {
    final days = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

    return Column(
      children: List.generate(7, (index) {
        return SizedBox(
          height: 12,
          child: Center(
            child: Text(
              days[index],
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontSize: 10,
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildYearGrid(BuildContext context, Map<String, List<Map<String, dynamic>>> monthlyData) {
    // 构建一年的格子网格 (53周 x 7天)
    final startOfYear = DateTime(year);
    final endOfYear = DateTime(year + 1).subtract(const Duration(days: 1));

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 53,
        childAspectRatio: 1,
        crossAxisSpacing: 2,
        mainAxisSpacing: 2,
      ),
      itemCount: 53 * 7,
      itemBuilder: (context, index) {
        final week = index ~/ 7;
        final dayOfWeek = index % 7;

        // 计算这个格子的日期
        final date = _getDateForCell(year, week, dayOfWeek);
        if (date == null || date.isBefore(startOfYear) || date.isAfter(endOfYear)) {
          return const SizedBox.shrink();
        }

        final dateKey = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
        final dayData = monthlyData.values
            .expand((days) => days)
            .cast<Map<String, dynamic>?>()
            .firstWhere(
              (day) => day?['date'] == dateKey,
              orElse: () => null,
            );

        return _buildHeatmapCell(context, dayData, index);
      },
    );
  }

  DateTime? _getDateForCell(int year, int week, int dayOfWeek) {
    try {
      // 找到该年份的第一周的第一天（周一）
      final firstDayOfYear = DateTime(year, 1, 1);
      final firstMonday = firstDayOfYear.add(Duration(days: (8 - firstDayOfYear.weekday) % 7));

      // 计算目标日期
      final targetDate = firstMonday.add(Duration(days: week * 7 + dayOfWeek));
      return targetDate;
    } catch (e) {
      return null;
    }
  }

  Widget _buildHeatmapCell(
    BuildContext context,
    Map<String, dynamic>? dayData,
    int revealIndex,
  ) {
    if (dayData == null) {
      return Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(2),
        ),
      );
    }

    final initiatorCheckins = dayData['initiator_checkins'] as int? ?? 0;
    final partnerCheckins = dayData['partner_checkins'] as int? ?? 0;
    final totalCheckins = initiatorCheckins + partnerCheckins;

    // 根据打卡数决定颜色
    Color cellColor;
    if (totalCheckins == 0) {
      cellColor = Theme.of(context).colorScheme.surfaceContainerHighest;
    } else if (totalCheckins == 1) {
      cellColor = const Color(0xFF9BE9A8);
    } else if (totalCheckins == 2) {
      cellColor = const Color(0xFF40C463);
    } else if (totalCheckins >= 3) {
      cellColor = const Color(0xFF30A14E);
    } else {
      cellColor = const Color(0xFF216E39);
    }

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 180 + (revealIndex.clamp(0, 80) * 8)),
      curve: Curves.easeOutCubic,
      builder: (context, value, child) => Opacity(
        opacity: value,
        child: Transform.scale(
          scale: 0.92 + (0.08 * value),
          child: child,
        ),
      ),
      child: Container(
        decoration: BoxDecoration(
          color: cellColor,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
}

/// 月度热力图 - 单个月份的详细视图
class MonthlyHeatmap extends StatelessWidget {
  const MonthlyHeatmap({
    super.key,
    required this.month,
    required this.year,
    required this.heatmap,
    required this.myUserId,
  });

  final int month;
  final int year;
  final List<Map<String, dynamic>> heatmap;
  final String myUserId;

  @override
  Widget build(BuildContext context) {
    // 筛选当月数据
    final monthlyData = heatmap.where((day) {
      final date = DateTime.parse(day['date'] as String);
      return date.year == year && date.month == month;
    }).toList();

    if (monthlyData.isEmpty) {
      return _buildEmptyState(context);
    }

    final daysInMonth = DateTime(year, month + 1, 0).day;
    final firstWeekday = DateTime(year, month, 1).weekday;

    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '$year年${month}月',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            _buildCalendarGrid(context, monthlyData, daysInMonth, firstWeekday),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Text(
            '本月暂无打卡记录',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCalendarGrid(
    BuildContext context,
    List<Map<String, dynamic>> monthlyData,
    int daysInMonth,
    int firstWeekday,
  ) {
    final weekdays = ['一', '二', '三', '四', '五', '六', '日'];

    return Column(
      children: [
        // Weekday headers
        Row(
          children: List.generate(7, (index) {
            return Expanded(
              child: Center(
                child: Text(
                  weekdays[index],
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 8),
        // Calendar grid
        ...List.generate(6, (week) {
          return Row(
            children: List.generate(7, (day) {
              final dayNumber = week * 7 + day - firstWeekday + 1;
              final isCurrentMonth = dayNumber > 0 && dayNumber <= daysInMonth;

              if (!isCurrentMonth) {
                return const Expanded(child: SizedBox(height: 40));
              }

              final dateKey = '$year-${month.toString().padLeft(2, '0')}-${dayNumber.toString().padLeft(2, '0')}';
              final dayData = monthlyData.cast<Map<String, dynamic>?>().firstWhere(
                (d) => d?['date'] == dateKey,
                orElse: () => null,
              );

              return Expanded(
                child: _buildDayCell(context, dayData, dayNumber),
              );
            }),
          );
        }),
      ],
    );
  }

  Widget _buildDayCell(BuildContext context, Map<String, dynamic>? dayData, int dayNumber) {
    final hasInitiatorCheckin = (dayData?['initiator_checkins'] as int? ?? 0) > 0;
    final hasPartnerCheckin = (dayData?['partner_checkins'] as int? ?? 0) > 0;

    Color? cellColor;
    IconData? icon;

    if (hasInitiatorCheckin && hasPartnerCheckin) {
      cellColor = const Color(0xFF216E39); // 双方都打卡
      icon = Icons.group;
    } else if (hasInitiatorCheckin) {
      cellColor = const Color(0xFF40C463); // 我打卡了
    } else if (hasPartnerCheckin) {
      cellColor = const Color(0xFF9BE9A8); // 伙伴打卡了
    } else {
      cellColor = null;
    }

    return Container(
      height: 40,
      margin: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: cellColor ?? Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Stack(
        children: [
          Center(
            child: Text(
              '$dayNumber',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: cellColor != null ? Colors.white : null,
              ),
            ),
          ),
          if (icon != null)
            Positioned(
              top: 2,
              right: 2,
              child: Icon(icon, size: 10, color: Colors.white70),
            ),
        ],
      ),
    );
  }
}
