import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart' as feature;
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_chart.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_session_list.dart';

/// Focus statistics tool widget - shows real-time focus statistics
/// Can be used as a bottom sheet or standalone widget
class FocusStatsTool extends ConsumerStatefulWidget {
  const FocusStatsTool({super.key});

  @override
  ConsumerState<FocusStatsTool> createState() => _FocusStatsToolState();
}

class _FocusStatsToolState extends ConsumerState<FocusStatsTool> {
  @override
  void initState() {
    super.initState();
    // Load data on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(feature.focusStatisticsProvider.notifier).loadTodayStats();
      ref.read(feature.focusStatisticsProvider.notifier).loadWeeklyStats();
      ref.read(feature.focusStatisticsProvider.notifier).loadSessionHistory(limit: 5);
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(feature.focusStatisticsProvider);

    return Container(
      padding: const EdgeInsets.all(DS.spacing24),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
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
                const Icon(Icons.bar_chart, color: Colors.deepPurple),
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

          // Loading indicator
          if (state.isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(DS.xl),
                child: CircularProgressIndicator(
                  color: Colors.white,
                ),
              ),
            ),

          // Overview Cards
          if (!state.isLoading)
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    '今日专注',
                    state.todayFormatted,
                    Colors.deepPurple,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    '本周累计',
                    state.weekTotalFormatted,
                    DS.brandPrimary,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    '连续天数',
                    '${state.streakDays}天',
                    Colors.orange,
                  ),
                ),
              ],
            ),

          const SizedBox(height: DS.xxl),

          // Weekly Trend Chart
          if (!state.isLoading && state.dailyBreakdown.isNotEmpty)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '本周趋势',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: DS.lg),
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  padding: const EdgeInsets.all(DS.md),
                  child: FocusStatsChart(
                    dailyData: state.dailyBreakdown,
                  ),
                ),
              ],
            ),

          if (!state.isLoading && state.dailyBreakdown.isEmpty)
            _buildEmptyState('暂无本周数据'),

          const SizedBox(height: DS.xxl),

          // Recent Sessions
          if (!state.isLoading && state.sessionHistory.isNotEmpty)
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '最近会话',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: DS.md),
                Container(
                  constraints: const BoxConstraints(maxHeight: 200),
                  child: FocusStatsSessionList(
                    sessions: state.sessionHistory.take(5).toList(),
                  ),
                ),
              ],
            ),

          if (!state.isLoading && state.sessionHistory.isEmpty)
            _buildEmptyState('暂无会话记录'),

          const SizedBox(height: DS.md),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, Color color) => Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.8),
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

  Widget _buildEmptyState(String message) => Container(
        padding: const EdgeInsets.all(DS.xl),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.info_outline,
              color: Colors.white.withValues(alpha: 0.6),
            ),
            const SizedBox(width: DS.sm),
            Text(
              message,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
}
