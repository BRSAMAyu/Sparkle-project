import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/user_state_models.dart';

class AchievementSummaryCard extends StatelessWidget {
  const AchievementSummaryCard({required this.summary, super.key});

  final UserStateFieldEnvelope<Stage35AchievementSummary>? summary;

  @override
  Widget build(BuildContext context) {
    final value = summary?.value;
    final unlocks = value?.recentUnlocks ?? const <Stage35AchievementUnlock>[];
    final progress =
        value?.inProgressAchievements ?? const <Stage35AchievementProgress>[];

    return GraphiteCardSurface(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '成就摘要',
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              '总成就分 ${value?.totalAchievementScore.toStringAsFixed(1) ?? '0.0'}',
              style: DS.bodyLarge.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            if (unlocks.isEmpty && progress.isEmpty)
              Text(
                '近期还没有新的高光或进度变化，继续推进会在这里留下痕迹。',
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              )
            else ...[
              if (unlocks.isNotEmpty)
                _MetricLine(label: '最近解锁', value: unlocks.first.name),
              if (progress.isNotEmpty)
                _MetricLine(
                  label: '当前推进',
                  value:
                      '${progress.first.name} ${(progress.first.progress * 100).round()}%',
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Row(
          children: [
            SizedBox(
              width: 76,
              child: Text(
                label,
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
            ),
            Expanded(
              child: Text(
                value,
                style: DS.bodyMedium.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ),
          ],
        ),
      );
}
