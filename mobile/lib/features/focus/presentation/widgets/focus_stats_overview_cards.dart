import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';

/// Overview cards showing key statistics
class FocusStatsOverviewCards extends StatelessWidget {
  const FocusStatsOverviewCards({
    required this.todayMinutes,
    required this.weekTotalMinutes,
    required this.streakDays,
    this.longestStreak,
    super.key,
  });

  final int todayMinutes;
  final int weekTotalMinutes;
  final int streakDays;
  final int? longestStreak;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final cards = [
      _StatCard(
        icon: Icons.today,
        iconColor: DS.prismPurple,
        label: l10n.focusStatsToday,
        value: _formatDuration(todayMinutes),
      ),
      _StatCard(
        icon: Icons.calendar_view_week,
        iconColor: DS.brandPrimary,
        label: l10n.focusStatsWeek,
        value: _formatDuration(weekTotalMinutes),
      ),
      _StatCard(
        icon: Icons.local_fire_department,
        iconColor: DS.warning,
        label: l10n.streakTitle,
        value: l10n.streakDays(streakDays),
        subtitle: longestStreak != null && longestStreak! > 0
            ? l10n.streakMax(longestStreak!)
            : null,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final useColumn = constraints.maxWidth < 520;
        if (useColumn) {
          return Column(
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                SparkleStaggerItem(index: i, child: cards[i]),
                if (i != cards.length - 1) const SizedBox(height: DS.md),
              ],
            ],
          );
        }

        return Row(
          children: [
            for (var i = 0; i < cards.length; i++) ...[
              Expanded(
                child: SparkleStaggerItem(index: i, child: cards[i]),
              ),
              if (i != cards.length - 1) const SizedBox(width: DS.md),
            ],
          ],
        );
      },
    );
  }

  String _formatDuration(int minutes) =>
      Formatters.formatFocusDuration(Duration(minutes: minutes));
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    this.subtitle,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final String? subtitle;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: iconColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(DS.md),
          border: Border.all(color: iconColor.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: iconColor, size: 16),
                const SizedBox(width: DS.xs),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: iconColor.withValues(alpha: 0.8),
                      fontSize: 11,
                      fontWeight: DS.fontWeightMedium,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            Text(
              value,
              style: TextStyle(
                color: iconColor,
                fontSize: 18,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: TextStyle(
                  color: iconColor.withValues(alpha: 0.6),
                  fontSize: 10,
                ),
              ),
          ],
        ),
      );
}
