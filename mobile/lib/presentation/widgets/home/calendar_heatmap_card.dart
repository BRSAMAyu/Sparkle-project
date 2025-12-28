import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class CalendarHeatmapCard extends StatelessWidget {
  const CalendarHeatmapCard({super.key});

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTap: () => context.push('/calendar-stats'),
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppDesignTokens.deepSpaceSurface.withValues(alpha: 0.6),
                  AppDesignTokens.glassBackground,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      DateFormat('MMMM yyyy', 'zh_CN').format(DateTime.now()),
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textOnDark(context).withValues(alpha: 0.8),
                      ),
                    ),
                    Icon(
                      Icons.calendar_month_rounded,
                      size: 16,
                      color: AppColors.textOnDark(context).withValues(alpha: 0.6),
                    ),
                  ],
                ),
                SizedBox(height: DS.md),
                Expanded(
                  child: LayoutBuilder(
                    builder: _buildMonthGrid,
                  ),
                ),
                SizedBox(height: DS.sm),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      'Less',
                      style: TextStyle(fontSize: 10, color: DS.brandPrimary500),
                    ),
                    SizedBox(width: DS.xs),
                    _buildLegendItem(0),
                    const SizedBox(width: 2),
                    _buildLegendItem(1),
                    const SizedBox(width: 2),
                    _buildLegendItem(2),
                    const SizedBox(width: 2),
                    _buildLegendItem(3),
                    const SizedBox(width: 2),
                    _buildLegendItem(4),
                    SizedBox(width: DS.xs),
                    Text(
                      'More',
                      style: TextStyle(fontSize: 10, color: DS.brandPrimary500),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );

  Widget _buildLegendItem(int level) => Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(
        color: _getColorForLevel(level),
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
            color: _getColorForLevel(intensity),
            borderRadius: BorderRadius.circular(4),
            border: i == now.day ? Border.all(color: DS.brandPrimaryConst, width: 1.5) : null,
          ),
          alignment: Alignment.center,
          // child: Text('$i', style: TextStyle(fontSize: 8, color: DS.brandPrimary70)), // Optional: show date
        ),
      );
    }

    return GridView.count(
      crossAxisCount: 7,
      mainAxisSpacing: 4,
      crossAxisSpacing: 4,
      physics: const NeverScrollableScrollPhysics(), 
      children: gridCells,
    );
  }

  Color _getColorForLevel(int level) {
    // Theme color is orange.
    final baseColor = DS.brandPrimaryConst;
    switch (level) {
      case 0: return baseColor.withValues(alpha: 0.1);
      case 1: return baseColor.withValues(alpha: 0.3);
      case 2: return baseColor.withValues(alpha: 0.5);
      case 3: return baseColor.withValues(alpha: 0.7);
      case 4: return baseColor.withValues(alpha: 1.0);
      default: return baseColor.withValues(alpha: 0.1);
    }
  }
}
