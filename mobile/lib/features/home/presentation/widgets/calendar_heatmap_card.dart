import 'dart:math';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';

class CalendarHeatmapCard extends StatelessWidget {
  const CalendarHeatmapCard({super.key});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: () => context.push('/calendar-stats'),
        child: MaterialStyler(
          material: AppMaterials.ceramic,
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
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
              ),
              const SizedBox(height: DS.md),
              Flexible(
                child: LayoutBuilder(
                  builder: _buildMonthGrid,
                ),
              ),
              const SizedBox(height: DS.sm),
              Wrap(
                alignment: WrapAlignment.end,
                spacing: 2,
                runSpacing: 2,
                children: [
                  Text(
                    'Less',
                    style:
                        TextStyle(fontSize: 10, color: DS.textSecondary),
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
                    style:
                        TextStyle(fontSize: 10, color: DS.textSecondary),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _buildLegendItem(BuildContext context, int level) => Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          color: _getColorForLevel(context, level),
          borderRadius: BorderRadius.circular(2),
        ),
      );

  Widget _buildMonthGrid(BuildContext context, BoxConstraints constraints) {
    final now = DateTime.now();
    final daysInMonth = DateTime(now.year, now.month + 1, 0).day;
    final firstWeekday = DateTime(now.year, now.month).weekday; // 1=Mon, 7=Sun

    // We can use a Wrap or Column of Rows. Let's use GridView for simplicity but carefully sized.
    // Or just a custom loop to build rows.

    final gridCells = <Widget>[];

    // Empty cells for offset
    for (var i = 0; i < firstWeekday - 1; i++) {
      gridCells.add(const SizedBox());
    }

    // Days
    for (var i = 1; i <= daysInMonth; i++) {
      // Fake intensity based on day number
      var intensity = (i * 7) % 5;
      if (i == now.day) intensity = 4; // Today is max

      gridCells.add(
        Container(
          decoration: BoxDecoration(
            color: _getColorForLevel(context, intensity),
            borderRadius: BorderRadius.circular(4),
            border: i == now.day
                ? Border.all(color: DS.brandPrimary.withValues(alpha: 0.8), width: 1.5)
                : null,
          ),
          alignment: Alignment.center,
          // child: Text('$i', style: TextStyle(fontSize: 8, color: DS.brandPrimary70)), // Optional: show date
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

  Color _getColorForLevel(BuildContext context, int level) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = isDark ? DS.brandPrimary : DS.brandPrimary;
    final alphaValues = isDark
        ? [0.15, 0.35, 0.55, 0.75, 1.0]
        : [0.2, 0.4, 0.6, 0.8, 1.0];
    final safeIndex = level.clamp(0, alphaValues.length - 1);
    return baseColor.withValues(alpha: alphaValues[safeIndex]);
  }
}
