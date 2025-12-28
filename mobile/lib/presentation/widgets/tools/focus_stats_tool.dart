import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class FocusStatsTool extends StatelessWidget {
  const FocusStatsTool({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing24),
      decoration: const BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: Colors.deepPurple.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.bar_chart, color: Colors.deepPurple),
              ),
              const SizedBox(width: DS.md),
              const Text(
                '专注统计',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: DS.xl),

          // Overview Cards
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  '今日专注',
                  '2h 35m',
                  Colors.deepPurple,
                ),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: _buildStatCard(
                  '本周累计',
                  '12h 40m',
                  DS.brandPrimary,
                ),
              ),
            ],
          ),

          const SizedBox(height: DS.xxl),

          // Weekly Trend Chart
          const Text(
            '本周趋势',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: DS.lg),
          SizedBox(
            height: 120,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildBar('周一', 0.4),
                _buildBar('周二', 0.7),
                _buildBar('周三', 0.3),
                _buildBar('周四', 0.8),
                _buildBar('周五', 0.5),
                _buildBar('周六', 0.9),
                _buildBar('周日', 0.2),
              ],
            ),
          ),

          const SizedBox(height: DS.xxl),

          // Detailed Stats
          Container(
            padding: const EdgeInsets.all(DS.lg),
            decoration: BoxDecoration(
              color: AppDesignTokens.neutral50,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildDetailStat(Icons.timer, '6', '番茄数'),
                _buildDetailStat(Icons.visibility_off, '2次', '分心'),
                _buildDetailStat(Icons.local_fire_department, '45m', '最长连续'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: color.withValues(alpha: 0.8),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: DS.xs),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBar(String label, double percentage) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Container(
          width: 24,
          height: 100 * percentage,
          decoration: BoxDecoration(
            color: percentage > 0.6 ? Colors.deepPurple : Colors.deepPurple.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(height: DS.sm),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            color: AppDesignTokens.neutral500,
          ),
        ),
      ],
    );
  }

  Widget _buildDetailStat(IconData icon, String value, String label) {
    return Column(
      children: [
        Icon(icon, color: AppDesignTokens.neutral600, size: 24),
        const SizedBox(height: DS.xs),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: AppDesignTokens.neutral900,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: AppDesignTokens.neutral500,
          ),
        ),
      ],
    );
  }
}
