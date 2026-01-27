import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactStats();
    }
    return _buildFullStats();
  }

  Widget _buildFullStats() => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Column(
        children: [
          // 顶部统计行
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  '总成就',
                  '${stats.unlockedCount}/${stats.totalAchievements}',
                  Icons.emoji_events_outlined,
                  DS.brandPrimary,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: _buildStatCard(
                  '完成率',
                  '${stats.unlockedPercentage.toStringAsFixed(0)}%',
                  Icons.bar_chart,
                  DS.semanticSuccess,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: _buildStatCard(
                  '光子',
                  '${stats.totalPhotons}',
                  Icons.stars,
                  const Color(0xFFFFD700),
                ),
              ),
            ],
          ),

          // 进度条
          Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
            child: _buildOverallProgressBar(),
          ),

          // 稀有度分布
          _buildRarityDistribution(),
        ],
      ),
    );

  Widget _buildCompactStats() => Container(
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.border),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildCompactStatItem(
            '${stats.unlockedCount}/${stats.totalAchievements}',
            '成就',
          ),
          _buildVerticalDivider(),
          _buildCompactStatItem(
            '${stats.unlockedPercentage.toStringAsFixed(0)}%',
            '完成率',
          ),
          _buildVerticalDivider(),
          _buildCompactStatItem(
            '${stats.currentStreak}',
            '连胜',
          ),
        ],
      ),
    );

  Widget _buildStatCard(String label, String value, IconData icon, Color color) => Container(
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

  Widget _buildVerticalDivider() => Container(
      width: 1,
      height: 24,
      color: DS.border,
    );

  Widget _buildOverallProgressBar() {
    final progress = stats.unlockedPercentage / 100;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '总体进度',
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
            ),
            Text(
              '${stats.unlockedCount} / ${stats.totalAchievements}',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textTertiary,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        Container(
          height: 8,
          decoration: BoxDecoration(
            color: DS.neutral200,
            borderRadius: DS.borderRadiusFull,
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: progress.clamp(0.0, 1.0),
            child: Container(
              decoration: BoxDecoration(
                gradient: DS.primaryGradient,
                borderRadius: DS.borderRadiusFull,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRarityDistribution() => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '稀有度分布',
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            fontWeight: DS.fontWeightSemibold,
            color: DS.textPrimary,
          ),
        ),
        const SizedBox(height: DS.spacing12),
        Row(
          children: [
            _buildRarityBarItem(
              '普通',
              stats.commonCount,
              const Color(0xFF9E9E9E),
            ),
            const SizedBox(width: DS.spacing8),
            _buildRarityBarItem(
              '稀有',
              stats.rareCount,
              const Color(0xFFFFD700),
            ),
            const SizedBox(width: DS.spacing8),
            _buildRarityBarItem(
              '史诗',
              stats.epicCount,
              const Color(0xFF9B59B6),
            ),
            const SizedBox(width: DS.spacing8),
            _buildRarityBarItem(
              '传说',
              stats.legendaryCount,
              const Color(0xFFFF6B6B),
            ),
            const Spacer(),
            if (stats.hiddenFound > 0)
              _buildHiddenStat(),
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

  Widget _buildHiddenStat() => Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: Colors.purple.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: Colors.purple.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.visibility_off,
            size: DS.iconSizeXs,
            color: Colors.purple,
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            '隐藏: ${stats.hiddenFound}',
            style: const TextStyle(
              fontSize: DS.fontSizeXs,
              color: Colors.purple,
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
      _PieSection(stats.commonCount, const Color(0xFF9E9E9E)),
      _PieSection(stats.rareCount, const Color(0xFFFFD700)),
      _PieSection(stats.epicCount, const Color(0xFF9B59B6)),
      _PieSection(stats.legendaryCount, const Color(0xFFFF6B6B)),
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
  bool shouldRepaint(_PieChartPainter oldDelegate) => oldDelegate.sections != sections;
}
