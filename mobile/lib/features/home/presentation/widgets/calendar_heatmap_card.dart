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
      return _buildCompactCard(context, ref, now, calendarState);
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

  Widget _buildCompactCard(
    BuildContext context,
    WidgetRef ref,
    DateTime now,
    TaskCalendarState calendarState,
  ) {
    final contentPadding = dense ? DS.spacing10 : DS.spacing12;
    final headerSpacing = dense ? DS.spacing6 : DS.spacing8;
    final monthlySummaries = calendarState.taskSummaries.entries
        .where(
          (entry) =>
              entry.key.year == now.year && entry.key.month == now.month,
        )
        .map((entry) => entry.value)
        .toList(growable: false);
    final activeDays =
        monthlySummaries.where((summary) => summary.hasTasks).length;
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
    final previewState = ref.watch(calendarPreviewProvider);
    final selectedDate = previewState.selectedDate;
    final selectedSummary = selectedDate != null &&
            selectedDate.year == now.year &&
            selectedDate.month == now.month
        ? calendarState.taskSummaries[
            DateTime(selectedDate.year, selectedDate.month, selectedDate.day)]
        : null;
    final selectedLabel = selectedDate == null
        ? null
        : selectedSummary != null && selectedSummary.hasTasks
            ? '${selectedDate.day}日 · ${selectedSummary.total}项'
            : '${selectedDate.day}日 · 暂无任务';

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
                  // Always use 2/3 + 1/3 layout with flex
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Left 2/3: Calendar grid
                      Expanded(
                        flex: 2,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildWeekdayStrip(context),
                            const SizedBox(height: DS.spacing4),
                            Expanded(
                              child: LayoutBuilder(
                                builder: (context, gridConstraints) =>
                                    _buildMonthGrid(
                                  context,
                                  ref,
                                  gridConstraints,
                                  calendarState,
                                ),
                              ),
                            ),
                            const SizedBox(height: DS.spacing4),
                            _buildLegend(context),
                          ],
                        ),
                      ),
                      SizedBox(width: dense ? DS.spacing8 : DS.spacing10),
                      // Right 1/3: Stats sidebar
                      Expanded(
                        child: _CompactCalendarSidebar(
                          activeDays: activeDays,
                          totalTasks: totalTasks,
                          pendingTasks: pendingTasks,
                          completedTasks: completedTasks,
                          selectedLabel: selectedLabel,
                          dense: dense,
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

  Widget _buildLegend(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Less',
            style: TextStyle(fontSize: 9, color: DS.textTertiary),
          ),
          const SizedBox(width: 3),
          for (var i = 0; i < 5; i++)
            Padding(
              padding: const EdgeInsets.only(right: 2),
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: _HeatmapColor.forLevel(context, i),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          const SizedBox(width: 3),
          Text(
            'More',
            style: TextStyle(fontSize: 9, color: DS.textTertiary),
          ),
        ],
      );

  Widget _buildWeekdayStrip(BuildContext context) {
    const labels = ['一', '二', '三', '四', '五', '六', '日'];
    return Row(
      children: labels
          .map(
            (label) => Expanded(
              child: Center(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: DS.textTertiary,
                        fontSize: 10,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  /// GitHub-style heatmap grid: each column aligns exactly with weekday labels.
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

    final totalLeading = firstWeekday - 1;
    final totalCells = totalLeading + daysInMonth;
    final rows = max(1, (totalCells / 7).ceil());
    const spacing = 3.0;

    final cellWidth = (constraints.maxWidth - spacing * 6) / 7;
    final cellHeight = (constraints.maxHeight - spacing * (rows - 1)) / rows;
    final cellSize = max(8.0, min(cellWidth, cellHeight));

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(rows, (row) => Padding(
        padding: EdgeInsets.only(top: row > 0 ? spacing : 0),
        child: Row(
          children: List.generate(7, (col) {
            final index = row * 7 + col;
            final dayNumber = index - totalLeading + 1;

            final child = (dayNumber >= 1 && dayNumber <= daysInMonth)
                ? _buildDayCell(
                    context, ref, now, dayNumber, cellSize,
                    calendarState, selectedDate,
                  )
                : SizedBox(width: cellSize, height: cellSize);

            return Expanded(child: Center(child: child));
          }),
        ),
      ),),
    );
  }

  Widget _buildDayCell(
    BuildContext context,
    WidgetRef ref,
    DateTime now,
    int day,
    double cellSize,
    TaskCalendarState calendarState,
    DateTime? selectedDate,
  ) {
    final dayKey = DateTime(now.year, now.month, day);
    final summary = calendarState.taskSummaries[dayKey];
    final hasTasks = summary != null && summary.hasTasks;

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

    final isToday = day == now.day;
    final isSelected = selectedDate != null &&
        dayKey.year == selectedDate.year &&
        dayKey.month == selectedDate.month &&
        dayKey.day == selectedDate.day;

    return _DayCell(
      day: day,
      intensity: intensity,
      isToday: isToday,
      isSelected: isSelected,
      hasTasks: hasTasks,
      size: cellSize,
      onTap: () =>
          ref.read(calendarPreviewProvider.notifier).selectDate(dayKey),
    );
  }
}

/// Overflow-safe stats sidebar — uses Flexible children so content
/// gracefully shrinks instead of overflowing when space is tight.
class _CompactCalendarSidebar extends ConsumerWidget {
  const _CompactCalendarSidebar({
    required this.activeDays,
    required this.totalTasks,
    required this.pendingTasks,
    required this.completedTasks,
    required this.selectedLabel,
    required this.dense,
  });

  final int activeDays;
  final int totalTasks;
  final int pendingTasks;
  final int completedTasks;
  final String? selectedLabel;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final todayAggregate = ref.watch(todayAggregateProvider);
    final hasActivity = todayAggregate.hasActivity;

    return Container(
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: DS.surfaceOverlay,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Text(
            '概览',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightBold,
                  fontSize: 10,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          // Today summary — flexible
          Flexible(
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing6,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: hasActivity
                    ? DS.brandPrimary.withValues(alpha: 0.10)
                    : DS.surfacePrimary.withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: hasActivity
                      ? DS.brandPrimary.withValues(alpha: 0.12)
                      : DS.borderSubtle,
                ),
              ),
              child: Text(
                hasActivity
                    ? todayAggregate.summaryText
                    : '今天还没有密集安排',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: hasActivity ? DS.brandPrimary : DS.textSecondary,
                  height: 1.35,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing4),
          // Stat chips — each is a compact row
          _StatChip(label: '总量', value: '$totalTasks'),
          const SizedBox(height: DS.spacing4),
          _StatChip(label: '待办', value: '$pendingTasks'),
          const SizedBox(height: DS.spacing4),
          _StatChip(label: '完成', value: '$completedTasks'),
          // Bottom dynamic label
          if (selectedLabel != null) ...[
            const Spacer(),
            Text(
              selectedLabel!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: DS.textTertiary,
                    fontSize: 9,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Ultra-compact stat row: label + value on one line
class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.68),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Flexible(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 9,
                  color: DS.textSecondary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Text(
              value,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: DS.textPrimary,
              ),
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
    this.size,
  });

  final int day;
  final int intensity;
  final bool isToday;
  final bool isSelected;
  final bool hasTasks;
  final VoidCallback onTap;
  final double? size;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cellSize = size ?? 24.0;
    final fontSize = (cellSize * 0.38).clamp(7.0, 12.0);
    final borderRadius = (cellSize * 0.18).clamp(2.0, 5.0);

    return GestureDetector(
      onTap: hasTasks ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        curve: Curves.easeOut,
        width: cellSize,
        height: cellSize,
        decoration: BoxDecoration(
          color: _HeatmapColor.forLevel(context, intensity),
          borderRadius: BorderRadius.circular(borderRadius),
          border: _buildBorder(),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.3),
                    blurRadius: 6,
                    offset: const Offset(0, 1),
                  ),
                ]
              : null,
        ),
        alignment: Alignment.center,
        child: Text(
          '$day',
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: isToday ? FontWeight.w700 : FontWeight.w500,
            color: _getTextColor(isDark, intensity),
          ),
        ),
      ),
    );
  }

  Color _getTextColor(bool isDark, int intensity) {
    if (intensity >= 3 || isSelected) {
      return DS.textOnPrimary;
    }
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
