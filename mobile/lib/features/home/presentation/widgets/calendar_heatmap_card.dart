import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/home/presentation/providers/calendar_preview_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar/task_preview_panel.dart';

/// Color utility for heatmap intensity levels
class _HeatmapColor {
  /// Get color for intensity level (0-4)
  /// 0 = no tasks, 1-4 = increasing intensity
  static Color forLevel(BuildContext context, int level) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = DS.brandPrimary;
    final alphaValues =
        isDark ? [0.15, 0.35, 0.55, 0.75, 1.0] : [0.2, 0.4, 0.6, 0.8, 1.0];
    final safeIndex = level.clamp(0, alphaValues.length - 1);
    return baseColor.withValues(alpha: alphaValues[safeIndex]);
  }
}

class CalendarHeatmapCard extends ConsumerWidget {
  const CalendarHeatmapCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Load task data for current month
    final now = DateTime.now();
    final calendarState = ref.watch(taskCalendarProvider);
    final monthKey = '${now.year}-${now.month.toString().padLeft(2, '0')}';
    if (!calendarState.loadedMonths.contains(monthKey)) {
      unawaited(ref.read(taskCalendarProvider.notifier).loadTasksForMonth(now));
    }

    if (compact) {
      final showLegend = !dense;
      final contentPadding = dense ? DS.spacing10 : DS.spacing12;
      final headerSpacing = dense ? DS.spacing8 : DS.spacing10;
      final monthlySummaries = calendarState.taskSummaries.entries
          .where(
            (entry) =>
                entry.key.year == now.year && entry.key.month == now.month,
          )
          .map((entry) => entry.value)
          .toList(growable: false);
      final activeDays =
          monthlySummaries.where((summary) => summary.hasTasks).length;
      final peakTasks = monthlySummaries.isEmpty
          ? 0
          : monthlySummaries.map((summary) => summary.total).reduce(max);
      final totalTasks = monthlySummaries.fold<int>(
        0,
        (sum, summary) => sum + summary.total,
      );
      final pendingTasks = monthlySummaries.fold<int>(
        0,
        (sum, summary) =>
            sum + summary.pending + summary.inProgress + summary.overdue,
      );
      final completedTasks = monthlySummaries.fold<int>(
        0,
        (sum, summary) => sum + summary.completed,
      );

      return GestureDetector(
        onTap: () => context.push('/calendar-stats'),
        child: MaterialStyler(
          material: AppMaterials.ceramic,
          borderRadius: DS.borderRadius20,
          padding: EdgeInsets.all(contentPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(context, dense: dense),
              SizedBox(height: headerSpacing),
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final showSidebar = constraints.maxWidth >= 290;
                    final sidebarWidth = dense
                        ? 92.0
                        : constraints.maxWidth >= 340
                            ? 112.0
                            : 96.0;
                    final grid = _buildMonthGrid(
                      context,
                      ref,
                      BoxConstraints(
                        maxWidth: showSidebar
                            ? constraints.maxWidth - sidebarWidth - DS.spacing10
                            : constraints.maxWidth,
                        maxHeight: constraints.maxHeight,
                      ),
                      calendarState,
                    );

                    if (!showSidebar) {
                      return Column(
                        children: [
                          Expanded(child: grid),
                          if (showLegend) ...[
                            const SizedBox(height: DS.spacing8),
                            _buildLegend(context),
                          ],
                        ],
                      );
                    }

                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(child: grid),
                        const SizedBox(width: DS.spacing10),
                        SizedBox(
                          width: sidebarWidth,
                          child: _CompactCalendarSidebar(
                            activeDays: activeDays,
                            peakTasks: peakTasks,
                            totalTasks: totalTasks,
                            pendingTasks: pendingTasks,
                            completedTasks: completedTasks,
                            showLegend: showLegend,
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      );
    }

    final previewState = ref.watch(calendarPreviewProvider);
    final isExpanded = previewState.isExpanded;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: () => context.push('/calendar-stats'),
          child: MaterialStyler(
            material: AppMaterials.ceramic,
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildHeader(context),
                const SizedBox(height: DS.md),
                Flexible(
                  child: LayoutBuilder(
                    builder: (context, constraints) => _buildMonthGrid(
                      context,
                      ref,
                      constraints,
                      calendarState,
                    ),
                  ),
                ),
                const SizedBox(height: DS.sm),
                _buildLegend(context),
              ],
            ),
          ),
        ),
        if (isExpanded) const TaskPreviewPanel(),
      ],
    );
  }

  Widget _buildHeader(
    BuildContext context, {
    bool dense = false,
  }) =>
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Flexible(
            child: Text(
              DateFormat('MMMM yyyy', 'zh_CN').format(DateTime.now()),
              style: TextStyle(
                fontSize: dense ? 12 : 13,
                fontWeight: FontWeight.w600,
                color: DS.textPrimary,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          // Quick jump to today button
          GestureDetector(
            onTap: () => context
                .push('/calendar/day?date=${DateTime.now().toIso8601String()}'),
            child: Container(
              padding: EdgeInsets.symmetric(
                horizontal: dense ? DS.spacing6 : DS.spacing8,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.today_rounded,
                    size: dense ? 12 : 14,
                    color: DS.brandPrimary,
                  ),
                  const SizedBox(width: DS.spacing4),
                  Text(
                    '今日',
                    style: TextStyle(
                      fontSize: dense ? 10 : 11,
                      fontWeight: FontWeight.w600,
                      color: DS.brandPrimary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );

  Widget _buildLegend(BuildContext context) => Wrap(
        alignment: WrapAlignment.end,
        spacing: 2,
        runSpacing: 2,
        children: [
          Text(
            'Less',
            style: TextStyle(fontSize: 10, color: DS.textSecondary),
          ),
          const SizedBox(width: DS.xs),
          _buildLegendItem(context, 0),
          _buildLegendItem(context, 1),
          _buildLegendItem(context, 2),
          _buildLegendItem(context, 3),
          _buildLegendItem(context, 4),
          const SizedBox(width: DS.xs),
          Text(
            'More',
            style: TextStyle(fontSize: 10, color: DS.textSecondary),
          ),
        ],
      );

  Widget _buildLegendItem(BuildContext context, int level) => Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: _HeatmapColor.forLevel(context, level),
          borderRadius: BorderRadius.circular(2),
        ),
      );

  Widget _buildMonthGrid(
    BuildContext context,
    WidgetRef ref,
    BoxConstraints constraints,
    TaskCalendarState calendarState,
  ) {
    final now = DateTime.now();
    final daysInMonth = DateTime(now.year, now.month + 1, 0).day;
    final firstWeekday = DateTime(now.year, now.month).weekday;

    final previewState = ref.watch(calendarPreviewProvider);
    final selectedDate = previewState.selectedDate;

    final gridCells = <Widget>[];

    // Empty cells for offset
    for (var i = 0; i < firstWeekday - 1; i++) {
      gridCells.add(const SizedBox());
    }

    // Days
    for (var i = 1; i <= daysInMonth; i++) {
      final dayDate = DateTime(now.year, now.month, i);
      final dayKey = DateTime(now.year, now.month, i);

      // Get task summary for this day from real data
      final summary = calendarState.taskSummaries[dayKey];
      final hasTasks = summary != null && summary.hasTasks;

      // Calculate intensity based on task count
      var intensity = 0;
      if (hasTasks) {
        final totalTasks = summary.total;
        if (totalTasks >= 6) {
          intensity = 4;
        } else if (totalTasks >= 4) {
          intensity = 3;
        } else if (totalTasks >= 2) {
          intensity = 2;
        } else {
          intensity = 1;
        }
      }

      final isToday = i == now.day;
      final isSelected = selectedDate != null &&
          dayKey.year == selectedDate.year &&
          dayKey.month == selectedDate.month &&
          dayKey.day == selectedDate.day;

      gridCells.add(
        _DayCell(
          day: i,
          intensity: intensity,
          isToday: isToday,
          isSelected: isSelected,
          hasTasks: hasTasks,
          onTap: () => _handleDateTap(ref, dayDate),
        ),
      );
    }

    const columns = 7;
    const spacing = 4.0;
    final rows = max(1, (gridCells.length / columns).ceil());
    final cellSizeFromWidth =
        (constraints.maxWidth - spacing * (columns - 1)) / columns;
    final cellSizeFromHeight =
        (constraints.maxHeight - spacing * (rows - 1)) / rows;
    final cellSize = max(0.0, min(cellSizeFromWidth, cellSizeFromHeight));
    final totalCells = rows * columns;

    return Align(
      alignment: Alignment.center,
      child: SizedBox(
        width: cellSize * columns + spacing * (columns - 1),
        height: cellSize * rows + spacing * (rows - 1),
        child: GridView.builder(
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            mainAxisSpacing: spacing,
            crossAxisSpacing: spacing,
          ),
          physics: const NeverScrollableScrollPhysics(),
          padding: EdgeInsets.zero,
          itemCount: totalCells,
          itemBuilder: (context, index) {
            if (index >= gridCells.length) {
              return const SizedBox();
            }
            return gridCells[index];
          },
        ),
      ),
    );
  }

  void _handleDateTap(WidgetRef ref, DateTime date) {
    ref.read(calendarPreviewProvider.notifier).selectDate(date);
  }
}

class _CompactCalendarSidebar extends ConsumerWidget {
  const _CompactCalendarSidebar({
    required this.activeDays,
    required this.peakTasks,
    required this.totalTasks,
    required this.pendingTasks,
    required this.completedTasks,
    required this.showLegend,
  });

  final int activeDays;
  final int peakTasks;
  final int totalTasks;
  final int pendingTasks;
  final int completedTasks;
  final bool showLegend;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Get today's aggregate for summary
    final todayAggregate = ref.watch(todayAggregateProvider);
    final todaySummary = todayAggregate.summaryText;
    final hasActivePlan = todayAggregate.activePlan != null;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: DS.surfaceOverlay,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '本月概览',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing6),
          // Today's overview badge
          if (todayAggregate.hasActivity)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing6,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                todaySummary,
                style: TextStyle(
                  fontSize: 9.5,
                  fontWeight: FontWeight.w600,
                  color: DS.brandPrimary,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          if (todayAggregate.hasActivity) const SizedBox(height: DS.spacing8),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxHeight < 126;
                final statSpacing = compact ? DS.spacing6 : DS.spacing8;
                return Wrap(
                  spacing: DS.spacing8,
                  runSpacing: statSpacing,
                  children: [
                    _CompactCalendarStat(
                      label: '任务总量',
                      value: '$totalTasks项',
                      width: (constraints.maxWidth - DS.spacing8) / 2,
                    ),
                    _CompactCalendarStat(
                      label: '待处理',
                      value: '$pendingTasks项',
                      width: (constraints.maxWidth - DS.spacing8) / 2,
                    ),
                    _CompactCalendarStat(
                      label: '已完成',
                      value: '$completedTasks项',
                      width: (constraints.maxWidth - DS.spacing8) / 2,
                    ),
                    _CompactCalendarStat(
                      label: '活跃日期',
                      value: '$activeDays天',
                      width: (constraints.maxWidth - DS.spacing8) / 2,
                    ),
                    _CompactCalendarStat(
                      label: '单日峰值',
                      value: '$peakTasks项',
                      width: constraints.maxWidth,
                    ),
                  ],
                );
              },
            ),
          ),
          // Active plan indicator
          if (hasActivePlan) ...[
            const SizedBox(height: DS.spacing6),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing6,
                vertical: 5,
              ),
              decoration: BoxDecoration(
                color: DS.surfacePrimary.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.flag_rounded,
                    size: 12,
                    color: DS.info,
                  ),
                  const SizedBox(width: DS.spacing4),
                  Expanded(
                    child: Text(
                      todayAggregate.activePlan!.name,
                      style: TextStyle(
                        fontSize: 9.5,
                        color: DS.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing6,
                vertical: 5,
              ),
              decoration: BoxDecoration(
                color: DS.surfacePrimary.withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Text(
                '今天没有活跃计划，适合整理待办与安排节奏。',
                style: TextStyle(
                  fontSize: 9.5,
                  color: DS.textSecondary,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _CompactCalendarStat extends StatelessWidget {
  const _CompactCalendarStat({
    required this.label,
    required this.value,
    required this.width,
  });

  final String label;
  final String value;
  final double width;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: width,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textSecondary,
                  ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            Text(
              value,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      );
}

/// Individual day cell in the calendar grid
class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.day,
    required this.intensity,
    required this.isToday,
    required this.isSelected,
    required this.hasTasks,
    required this.onTap,
  });

  final int day;
  final int intensity;
  final bool isToday;
  final bool isSelected;
  final bool hasTasks;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: hasTasks ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          color: _HeatmapColor.forLevel(context, intensity),
          borderRadius: BorderRadius.circular(4),
          border: _buildBorder(),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        alignment: Alignment.center,
        child: Text(
          '$day',
          style: TextStyle(
            fontSize: 8,
            fontWeight: isToday ? FontWeight.w700 : FontWeight.w600,
            color: _getTextColor(isDark, intensity),
          ),
        ),
      ),
    );
  }

  Color _getTextColor(bool isDark, int intensity) {
    // High intensity (3-4) or selected = white text
    if (intensity >= 3 || isSelected) {
      return DS.textOnPrimary;
    }
    // Low intensity (0-2) = use contrast color based on theme
    if (isDark) {
      return isToday ? DS.primaryBase : DS.textSecondary;
    }
    return isToday ? DS.primaryBase : DS.textPrimary;
  }

  Border? _buildBorder() {
    if (isSelected) {
      return Border.all(
        color: DS.brandPrimary.withValues(alpha: 0.9),
        width: 2,
      );
    }
    if (isToday) {
      return Border.all(
        color: DS.brandPrimary.withValues(alpha: 0.8),
        width: 1.5,
      );
    }
    return null;
  }
}
