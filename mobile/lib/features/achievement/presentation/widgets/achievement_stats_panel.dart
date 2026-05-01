import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 成就统计面板组件
///
/// 显示成就统计数据和稀有度分布
class AchievementStatsPanel extends StatelessWidget {
  const AchievementStatsPanel({
    required this.stats,
    super.key,
    this.isCompact = false,
  });

  final AchievementStats stats;
  final bool isCompact;

  bool get _hasStarted =>
      stats.totalAchievements > 0 ||
      stats.unlockedCount > 0 ||
      stats.currentStreak > 0 ||
      stats.totalPhotons > 0;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactStats(context.l10n);
    }
    return _buildFullStats(context.l10n);
  }

  Widget _buildFullStats(AppLocalizations l10n) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.border),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compactStats = constraints.maxWidth < 520;
            final cards = [
              _buildStatCard(
                l10n.achievementTotalLabel,
                _hasStarted
                    ? '${stats.unlockedCount}/${stats.totalAchievements}'
                    : '尚未开始',
                Icons.emoji_events_outlined,
                DS.brandPrimary,
              ),
              _buildStatCard(
                l10n.achievementCompletionRate,
                _hasStarted
                    ? '${stats.unlockedPercentage.toStringAsFixed(0)}%'
                    : '等待点亮',
                Icons.bar_chart,
                DS.semanticSuccess,
              ),
              _buildStatCard(
                l10n.achievementPhotons,
                _hasStarted ? '${stats.totalPhotons}' : '待累积',
                Icons.stars,
                DS.warning,
              ),
            ];

            return Column(
              children: [
                if (compactStats)
                  Column(
                    children: [
                      for (var index = 0; index < cards.length; index++) ...[
                        if (index > 0) const SizedBox(height: DS.spacing10),
                        SparkleStaggerItem(index: index, child: cards[index]),
                      ],
                    ],
                  )
                else
                  Row(
                    children: [
                      for (var index = 0; index < cards.length; index++) ...[
                        if (index > 0) const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: SparkleStaggerItem(
                            index: index,
                            child: cards[index],
                          ),
                        ),
                      ],
                    ],
                  ),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                  child: SparkleStaggerItem(
                    index: 3,
                    child:
                        _buildOverallProgressBar(l10n, compact: compactStats),
                  ),
                ),
                SparkleStaggerItem(
                  index: 4,
                  child: _buildRarityDistribution(l10n),
                ),
              ],
            );
          },
        ),
      );

  Widget _buildCompactStats(AppLocalizations l10n) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.border),
        ),
        child: Wrap(
          alignment: WrapAlignment.spaceAround,
          spacing: DS.spacing12,
          runSpacing: DS.spacing12,
          children: [
            _buildCompactStatItem(
              _hasStarted
                  ? '${stats.unlockedCount}/${stats.totalAchievements}'
                  : '尚未开始',
              l10n.achievementTitle,
            ),
            _buildCompactStatItem(
              _hasStarted
                  ? '${stats.unlockedPercentage.toStringAsFixed(0)}%'
                  : '等待点亮',
              l10n.achievementCompletionRate,
            ),
            _buildCompactStatItem(
              _hasStarted ? '${stats.currentStreak}' : '待累积',
              l10n.winStreak,
            ),
          ],
        ),
      );

  Widget _buildStatCard(
    String label,
    String value,
    IconData icon,
    Color color,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius12,
        ),
        child: Column(
          children: [
            Icon(
              icon,
              color: color,
              size: DS.iconSizeBase,
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              value,
              style: TextStyle(
                fontSize: DS.fontSizeLg,
                fontWeight: DS.fontWeightBold,
                color: color,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );

  Widget _buildCompactStatItem(String value, String label) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: DS.fontSizeBase,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: DS.textSecondary,
            ),
          ),
        ],
      );

  Widget _buildOverallProgressBar(
    AppLocalizations l10n, {
    bool compact = false,
  }) {
    final progress = stats.unlockedPercentage / 100;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (compact)
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.achievementOverallProgress,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                _hasStarted
                    ? '${stats.unlockedCount} / ${stats.totalAchievements}'
                    : '尚未开始解锁',
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textTertiary,
                ),
              ),
            ],
          )
        else
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.achievementOverallProgress,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  color: DS.textSecondary,
                ),
              ),
              Text(
                _hasStarted
                    ? '${stats.unlockedCount} / ${stats.totalAchievements}'
                    : '尚未开始解锁',
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textTertiary,
                ),
              ),
            ],
          ),
        SizedBox(height: compact ? DS.spacing10 : DS.spacing8),
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: progress.clamp(0.0, 1.0)),
          duration: DS.durationSlow,
          curve: Curves.easeOutCubic,
          builder: (context, value, child) => Container(
            height: 8,
            decoration: BoxDecoration(
              color: DS.neutral200,
              borderRadius: DS.borderRadiusFull,
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: value,
              child: Container(
                decoration: BoxDecoration(
                  gradient: DS.primaryGradient,
                  borderRadius: DS.borderRadiusFull,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRarityDistribution(AppLocalizations l10n) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.achievementRarityDistribution,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildRarityBarItem(
                l10n.achievementRarityCommon,
                stats.commonCount,
                DS.neutral500,
              ),
              const SizedBox(width: DS.spacing8),
              _buildRarityBarItem(
                l10n.achievementRarityRare,
                stats.rareCount,
                DS.warning,
              ),
              const SizedBox(width: DS.spacing8),
              _buildRarityBarItem(
                l10n.achievementRarityEpic,
                stats.epicCount,
                DS.prismPurple,
              ),
              const SizedBox(width: DS.spacing8),
              _buildRarityBarItem(
                l10n.achievementRarityLegendary,
                stats.legendaryCount,
                DS.error,
              ),
              if (stats.hiddenFound > 0) _buildHiddenStat(l10n),
            ],
          ),
        ],
      );

  Widget _buildRarityBarItem(String label, int count, Color color) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: count > 0 ? color : DS.neutral300,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: DS.spacing6),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textSecondary,
                ),
              ),
              Text(
                count > 0 ? '$count' : '-',
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  fontWeight: DS.fontWeightBold,
                  color: count > 0 ? color : DS.textTertiary,
                ),
              ),
            ],
          ),
        ],
      );

  Widget _buildHiddenStat(AppLocalizations l10n) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.prismPurple.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius8,
          border: Border.all(
            color: DS.prismPurple.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.visibility_off,
              size: DS.iconSizeXs,
              color: DS.prismPurple,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              l10n.achievementHiddenCount(stats.hiddenFound),
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.prismPurple,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      );
}

/// 稀有度分布饼图组件
class RarityPieChart extends StatelessWidget {
  const RarityPieChart({
    required this.stats,
    super.key,
    this.size = 100,
  });

  final AchievementStats stats;
  final double size;

  @override
  Widget build(BuildContext context) {
    final total = stats.commonCount +
        stats.rareCount +
        stats.epicCount +
        stats.legendaryCount;

    if (total == 0) {
      return _buildEmptyChart();
    }

    final sections = [
      _PieSection(stats.commonCount, DS.neutral500),
      _PieSection(stats.rareCount, DS.warning),
      _PieSection(stats.epicCount, DS.prismPurple),
      _PieSection(stats.legendaryCount, DS.error),
    ];

    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _PieChartPainter(sections),
      ),
    );
  }

  Widget _buildEmptyChart() => SizedBox(
        width: size,
        height: size,
        child: DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: DS.neutral200,
          ),
          child: Center(
            child: Icon(
              Icons.pie_chart,
              size: size * 0.4,
              color: DS.textTertiary,
            ),
          ),
        ),
      );
}

class _PieSection {
  _PieSection(this.count, this.color);
  final int count;
  final Color color;
}

class _PieChartPainter extends CustomPainter {
  _PieChartPainter(this.sections);

  final List<_PieSection> sections;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    final total = sections.fold<int>(0, (sum, s) => sum + s.count);

    var startAngle = -math.pi / 2;

    for (final section in sections) {
      if (section.count == 0) continue;

      final sweepAngle = (section.count / total) * 2 * math.pi;
      final rect = Rect.fromCircle(center: center, radius: radius);

      final paint = Paint()
        ..color = section.color
        ..style = PaintingStyle.fill;

      canvas.drawArc(
        rect,
        startAngle,
        sweepAngle,
        true,
        paint,
      );

      startAngle += sweepAngle;
    }

    // Draw center hole for donut effect
    final holePaint = Paint()
      ..color = DS.surfacePrimary
      ..style = PaintingStyle.fill;

    canvas.drawCircle(
      center,
      radius * 0.6,
      holePaint,
    );
  }

  @override
  bool shouldRepaint(_PieChartPainter oldDelegate) =>
      oldDelegate.sections != sections;
}
