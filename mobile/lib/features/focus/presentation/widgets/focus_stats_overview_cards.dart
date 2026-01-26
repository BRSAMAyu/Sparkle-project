import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

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
  Widget build(BuildContext context) => Row(
      children: [
        Expanded(
          child: _StatCard(
            icon: Icons.today,
            iconColor: Colors.deepPurple,
            label: '今日专注',
            value: _formatDuration(todayMinutes),
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: _StatCard(
            icon: Icons.calendar_view_week,
            iconColor: DS.brandPrimary,
            label: '本周累计',
            value: _formatDuration(weekTotalMinutes),
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: _StatCard(
            icon: Icons.local_fire_department,
            iconColor: Colors.orange,
            label: '连续天数',
            value: '$streakDays天',
            subtitle: longestStreak != null && longestStreak! > 0
                ? '最长$longestStreak天'
                : null,
          ),
        ),
      ],
    );

  String _formatDuration(int minutes) {
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    if (hours > 0) {
      return '${hours}h ${mins}m';
    }
    return '${mins}m';
  }
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
                    fontWeight: FontWeight.w500,
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
              fontWeight: FontWeight.bold,
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
