import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// V13-MAJORS M-02（诚实性红线）：本卡原先用一组硬编码 FlSpot(3,5,2,8,4,7,9)
/// 画出完整 7 天曲线——零行为的新注册用户也会看到一条"假的成长曲线"。
/// 该卡片没有任何真实数据源（后端无 7 日学习指数序列端点；自造口径违反
/// 口径单一事实源约束），因此零数据时只渲染诚实空态：不画曲线、不造数字。
/// 未来接入真实日粒度序列时，在 [_WeeklyTrendBody] 按 has_data 分支渲染。
class StatisticsCard extends StatelessWidget {
  const StatisticsCard({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final trendAccent =
        isDark ? const Color(0xFF94AFD2) : const Color(0xFF7A93B4);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
        border: Border.all(color: trendAccent.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: trendAccent.withValues(alpha: 0.14),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.show_chart_rounded,
                  color: trendAccent,
                  size: 16,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.statisticsWeeklyGrowthTrend,
                style: TextStyle(
                  fontSize: DS.fontSizeBase,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          SizedBox(
            height: 120,
            child: _WeeklyTrendBody(trendAccent: trendAccent),
          ),
        ],
      ),
    );
  }
}

/// 空数据诚实态占位。当前该卡无任何真实数据源，恒为空态；
/// 接入真实序列后在此按数据有无分支（空态/曲线），禁止回落到伪造数据。
class _WeeklyTrendBody extends StatelessWidget {
  const _WeeklyTrendBody({required this.trendAccent});

  final Color trendAccent;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      decoration: BoxDecoration(
        color: trendAccent.withValues(alpha: isDark ? 0.06 : 0.05),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: trendAccent.withValues(alpha: 0.10)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.insights_outlined,
            size: 22,
            color: trendAccent.withValues(alpha: 0.8),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.statisticsTrendEmptyHint,
            textAlign: TextAlign.center,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}
