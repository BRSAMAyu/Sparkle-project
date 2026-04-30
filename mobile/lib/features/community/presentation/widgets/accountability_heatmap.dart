import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 责任伙伴打卡热力图组件
///
/// 按月份展示打卡情况，支持左右滑动切换月份。
class AccountabilityHeatmap extends StatefulWidget {
  const AccountabilityHeatmap({
    required this.heatmap,
    required this.year,
    super.key,
  });

  final List<Map<String, dynamic>> heatmap;
  final int year;

  @override
  State<AccountabilityHeatmap> createState() => _AccountabilityHeatmapState();
}

class _AccountabilityHeatmapState extends State<AccountabilityHeatmap> {
  late final PageController _pageController;
  late int _currentMonthPage;

  List<String> _monthLabels(BuildContext context) {
    final l10n = context.l10n;
    return [
      l10n.communityMonthLabel1,
      l10n.communityMonthLabel2,
      l10n.communityMonthLabel3,
      l10n.communityMonthLabel4,
      l10n.communityMonthLabel5,
      l10n.communityMonthLabel6,
      l10n.communityMonthLabel7,
      l10n.communityMonthLabel8,
      l10n.communityMonthLabel9,
      l10n.communityMonthLabel10,
      l10n.communityMonthLabel11,
      l10n.communityMonthLabel12,
    ];
  }

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _currentMonthPage = now.year == widget.year ? now.month - 1 : 0;
    _pageController = PageController(initialPage: _currentMonthPage);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.heatmap.isEmpty) {
      return _buildEmptyState(context);
    }

    final monthlyData = _groupByMonth();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              context.l10n.communityMonthlyCheckinView(widget.year),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            _buildLegend(context),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          context.l10n.communitySwipeMonthsHint,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
        const SizedBox(height: 16),
        _buildPagerHeader(context),
        const SizedBox(height: 12),
        SizedBox(
          height: 344,
          child: PageView.builder(
            controller: _pageController,
            itemCount: 12,
            onPageChanged: (index) {
              setState(() {
                _currentMonthPage = index;
              });
            },
            itemBuilder: (context, index) => MonthlyHeatmap(
              month: index + 1,
              year: widget.year,
              heatmap: monthlyData[index + 1] ?? const [],
            ),
          ),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: List.generate(12, (index) {
              final month = index + 1;
              final selected = index == _currentMonthPage;
              final count = (monthlyData[month] ?? const []).where((day) {
                final initiator = day['initiator_checkins'] as int? ?? 0;
                final partner = day['partner_checkins'] as int? ?? 0;
                return initiator + partner > 0;
              }).length;

              return Padding(
                padding: EdgeInsets.only(right: index == 11 ? 0 : 8),
                child: ChoiceChip(
                  selected: selected,
                  label: Text(context.l10n.communityMonthDayCount(_monthLabels(context)[index], count)),
                  onSelected: (_) {
                    unawaited(
                      _pageController.animateToPage(
                        index,
                        duration: const Duration(milliseconds: 220),
                        curve: Curves.easeOutCubic,
                      ),
                    );
                  },
                ),
              );
            }),
          ),
        ),
      ],
    );
  }

  Map<int, List<Map<String, dynamic>>> _groupByMonth() {
    final monthlyData = <int, List<Map<String, dynamic>>>{};
    for (final day in widget.heatmap) {
      final rawDate = day['date']?.toString();
      if (rawDate == null || rawDate.isEmpty) {
        continue;
      }
      final date = DateTime.tryParse(rawDate);
      if (date == null || date.year != widget.year) {
        continue;
      }
      monthlyData.putIfAbsent(date.month, () => <Map<String, dynamic>>[]).add(
            day,
          );
    }
    return monthlyData;
  }

  Widget _buildPagerHeader(BuildContext context) => Row(
        children: [
          IconButton(
            onPressed: _currentMonthPage == 0
                ? null
                : () => _pageController.previousPage(
                      duration: const Duration(milliseconds: 220),
                      curve: Curves.easeOutCubic,
                    ),
            icon: const Icon(Icons.chevron_left_rounded),
          ),
          Expanded(
            child: Center(
              child: Text(
                context.l10n.communityYearMonth(widget.year, _currentMonthPage + 1),
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ),
          ),
          IconButton(
            onPressed: _currentMonthPage == 11
                ? null
                : () => _pageController.nextPage(
                      duration: const Duration(milliseconds: 220),
                      curve: Curves.easeOutCubic,
                    ),
            icon: const Icon(Icons.chevron_right_rounded),
          ),
        ],
      );

  Widget _buildEmptyState(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          children: [
            Icon(
              Icons.calendar_today_outlined,
              size: 40,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 12),
            Text(
              context.l10n.communityNoCheckinRecord,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      );

  Widget _buildLegend(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _legendItem(
            context,
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            label: context.l10n.communityNotCheckedIn,
          ),
          const SizedBox(width: 8),
          _legendItem(
            context,
            color: const Color(0xFF9BE9A8),
            label: context.l10n.communitySingleChecked,
          ),
          const SizedBox(width: 8),
          _legendItem(
            context,
            color: const Color(0xFF2E7D32),
            label: context.l10n.communityBothChecked,
          ),
        ],
      );

  Widget _legendItem(
    BuildContext context, {
    required Color color,
    required String label,
  }) =>
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(3),
            ),
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      );
}

/// 月度热力图 - 单个月份的详细视图
class MonthlyHeatmap extends StatelessWidget {
  const MonthlyHeatmap({
    required this.month,
    required this.year,
    required this.heatmap,
    super.key,
  });

  final int month;
  final int year;
  final List<Map<String, dynamic>> heatmap;

  List<String> _weekdayLabels(BuildContext context) => [
        context.l10n.communityWeekdayMon,
        context.l10n.communityWeekdayTue,
        context.l10n.communityWeekdayWed,
        context.l10n.communityWeekdayThu,
        context.l10n.communityWeekdayFri,
        context.l10n.communityWeekdaySat,
        context.l10n.communityWeekdaySun,
      ];

  @override
  Widget build(BuildContext context) {
    final daysInMonth = DateTime(year, month + 1, 0).day;
    final firstWeekdayOffset = DateTime(year, month, 1).weekday - 1;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        children: [
          Row(
            children: List.generate(
              7,
              (index) => Expanded(
                child: Center(
                  child: Text(
                    _weekdayLabels(context)[index],
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          ...List.generate(6, (week) {
            return Padding(
              padding: EdgeInsets.only(bottom: week == 5 ? 0 : 8),
              child: Row(
                children: List.generate(7, (day) {
                  final dayNumber = week * 7 + day - firstWeekdayOffset + 1;
                  final isCurrentMonth =
                      dayNumber > 0 && dayNumber <= daysInMonth;

                  if (!isCurrentMonth) {
                    return const Expanded(child: SizedBox(height: 44));
                  }

                  final dateKey =
                      '$year-${month.toString().padLeft(2, '0')}-${dayNumber.toString().padLeft(2, '0')}';
                  final dayData =
                      heatmap.cast<Map<String, dynamic>?>().firstWhere(
                            (d) => d?['date'] == dateKey,
                            orElse: () => null,
                          );

                  return Expanded(
                    child: _DayCell(
                      dayNumber: dayNumber,
                      dayData: dayData,
                    ),
                  );
                }),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.dayNumber,
    required this.dayData,
  });

  final int dayNumber;
  final Map<String, dynamic>? dayData;

  @override
  Widget build(BuildContext context) {
    final initiatorCheckins = dayData?['initiator_checkins'] as int? ?? 0;
    final partnerCheckins = dayData?['partner_checkins'] as int? ?? 0;
    final totalCheckins = initiatorCheckins + partnerCheckins;
    final bothCheckedIn = initiatorCheckins > 0 && partnerCheckins > 0;

    final surface = Theme.of(context).colorScheme.surfaceContainerHighest;
    final cellColor = totalCheckins == 0
        ? surface
        : bothCheckedIn
            ? const Color(0xFF2E7D32)
            : const Color(0xFF9BE9A8);

    final textColor = totalCheckins == 0 ? null : Colors.white;

    return Container(
      height: 44,
      margin: const EdgeInsets.symmetric(horizontal: 3),
      decoration: BoxDecoration(
        color: cellColor,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Stack(
        children: [
          Center(
            child: Text(
              '$dayNumber',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: textColor,
                    fontWeight:
                        totalCheckins == 0 ? DS.fontWeightMedium : DS.fontWeightBold,
                  ),
            ),
          ),
          if (totalCheckins > 0)
            Positioned(
              right: 5,
              top: 5,
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: Colors.white
                      .withValues(alpha: bothCheckedIn ? 0.92 : 0.7),
                  shape: BoxShape.circle,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
