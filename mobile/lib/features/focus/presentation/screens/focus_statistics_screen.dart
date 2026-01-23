import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pull_to_refresh/pull_to_refresh.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_chart.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_heatmap.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_overview_cards.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_period_toggle.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_session_list.dart';

/// Focus statistics screen showing comprehensive focus session analytics
class FocusStatisticsScreen extends ConsumerStatefulWidget {
  const FocusStatisticsScreen({super.key});

  @override
  ConsumerState<FocusStatisticsScreen> createState() =>
      _FocusStatisticsScreenState();
}

class _FocusStatisticsScreenState extends ConsumerState<FocusStatisticsScreen> {
  final _refreshController = RefreshController(initialRefresh: false);

  @override
  void initState() {
    super.initState();
    // Load all data on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadAllData();
    });
  }

  @override
  void dispose() {
    _refreshController.dispose();
    super.dispose();
  }

  Future<void> _loadAllData() async {
    await ref.read(focusStatisticsProvider.notifier).refresh();
  }

  Future<void> _onRefresh() async {
    await ref.read(focusStatisticsProvider.notifier).refresh();
    _refreshController.refreshCompleted();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(focusStatisticsProvider);

    return Scaffold(
      backgroundColor: DS.neutral50,
      appBar: AppBar(
        title: const Text('专注统计'),
        backgroundColor: DS.brandPrimary,
        foregroundColor: DS.neutral0,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            onPressed: state.isRefreshing ? null : _onRefresh,
          ),
        ],
      ),
      body: SmartRefresher(
        controller: _refreshController,
        onRefresh: _onRefresh,
        enablePullUp: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Period Toggle
              Center(
                child: FocusStatsPeriodToggle(
                  period: state.period,
                  onChanged: (period) {
                    ref.read(focusStatisticsProvider.notifier).setPeriod(period);
                  },
                ),
              ),

              const SizedBox(height: DS.xl),

              // Overview Cards
              FocusStatsOverviewCards(
                todayMinutes: state.todayMinutes,
                weekTotalMinutes:
                    state.weeklyData?['total_minutes'] as int? ?? 0,
                streakDays: state.streakDays,
                longestStreak: state.longestStreak,
              ),

              const SizedBox(height: DS.xl),

              // Chart Section
              _buildSection(
                title: '专注趋势',
                child: FocusStatsChart(
                  dailyData: state.dailyBreakdown,
                ),
              ),

              const SizedBox(height: DS.xl),

              // Heatmap Section
              _buildSection(
                title: '活跃热力图 (90天)',
                child: FocusStatsHeatmap(
                  data: state.heatmapData,
                ),
              ),

              const SizedBox(height: DS.xl),

              // Session History
              _buildSection(
                title: '最近会话',
                child: FocusStatsSessionList(
                  sessions: state.sessionHistory,
                  hasMore: state.sessionHistory.length >= 20,
                  onLoadMore: () {
                    ref.read(focusStatisticsProvider.notifier).loadSessionHistory(
                          limit: state.sessionHistory.length + 20,
                        );
                  },
                  isLoading: state.isLoading,
                ),
              ),

              const SizedBox(height: DS.xxl),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSection({required String title, required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.neutral0,
        borderRadius: BorderRadius.circular(DS.md),
        boxShadow: [
          BoxShadow(
            color: DS.neutral900.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: child,
    );
  }
}
