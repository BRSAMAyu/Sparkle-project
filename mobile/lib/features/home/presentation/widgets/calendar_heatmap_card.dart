import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/home/presentation/providers/calendar_preview_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar/task_preview_panel.dart';

/// Color utility for heatmap intensity levels
class _HeatmapColor {
  /// Get color for intensity level (0-4)
  /// 0 = no tasks, 1-4 = increasing intensity
  static Color forLevel(BuildContext context, int level) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = DS.brandPrimary;
    final alphaValues = isDark
        ? [0.15, 0.35, 0.55, 0.75, 1.0]
        : [0.2, 0.4, 0.6, 0.8, 1.0];
    final safeIndex = level.clamp(0, alphaValues.length - 1);
    return baseColor.withValues(alpha: alphaValues[safeIndex]);
  }
}

class CalendarHeatmapCard extends ConsumerWidget {
  const CalendarHeatmapCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final previewState = ref.watch(calendarPreviewProvider);
    final isExpanded = previewState.isExpanded;

    // Load task data for current month
    final now = DateTime.now();
    final calendarState = ref.watch(taskCalendarProvider);

    // Only load if the current month's data hasn't been loaded yet
    // This prevents unnecessary reloads on every rebuild
    final currentMonthKey = DateTime(now.year, now.month);
    final hasCurrentMonthData = calendarState.taskSummaries.keys.any((date) =>
        date.year == now.year && date.month == now.month,);
    if (!hasCurrentMonthData) {
      ref.read(taskCalendarProvider.notifier).loadTasksForMonth(now);
    }

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
                    builder: (context, constraints) =>
                        _buildMonthGrid(context, ref, constraints, calendarState),
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

  Widget _buildHeader(BuildContext context) => Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Flexible(
          child: Text(
            DateFormat('MMMM yyyy', 'zh_CN').format(DateTime.now()),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: DS.textPrimary,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        Icon(
          Icons.calendar_month_rounded,
          size: 16,
          color: DS.textSecondary,
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
      alignment: Alignment.topLeft,
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
  Widget build(BuildContext context) => GestureDetector(
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
        child: isToday
            ? Text(
                '$day',
                style: TextStyle(
                  fontSize: 8,
                  fontWeight: FontWeight.w600,
                  color: DS.brandPrimary70,
                ),
              )
            : null,
      ),
    );

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
