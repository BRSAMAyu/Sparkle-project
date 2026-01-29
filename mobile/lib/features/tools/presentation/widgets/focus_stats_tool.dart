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
        color: DS.surfaceSecondary,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: DS.border, width: 0.5),
        ),
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
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Icon(
                    Icons.bar_chart,
                    color: DS.primaryBase,
                    size: 24,
                  ),
                ),
              ),
              const SizedBox(width: DS.md),
              Text(
                '专注统计',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: DS.textPrimary,
                ),
              ),
              const Spacer(),
              IconButton(
                icon: Icon(Icons.close, color: DS.textSecondary),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: DS.xl),

          // Loading indicator
          if (state.isLoading)
            Center(
              child: Padding(
                padding: EdgeInsets.all(DS.xl),
                child: CircularProgressIndicator(
                  color: DS.primaryBase,
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
                    DS.info,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    '本周累计',
                    state.weekTotalFormatted,
                    DS.primaryBase,
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: _buildStatCard(
                    '连续天数',
                    '${state.streakDays}天',
                    DS.warning,
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
                Text(
                  '本周趋势',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.lg),
                Container(
                  decoration: BoxDecoration(
                    color: DS.surfacePrimaryElevated,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: DS.border, width: 0.5),
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
                Text(
                  '最近会话',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: DS.textPrimary,
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
                color: DS.textSecondary,
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
          color: DS.surfacePrimaryElevated,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: DS.border, width: 0.5),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.info_outline,
              color: DS.textSecondary,
            ),
            const SizedBox(width: DS.sm),
            Text(
              message,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
}
