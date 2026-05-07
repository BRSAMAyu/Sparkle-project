import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart'
    as feature;
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
  @override
  void initState() {
    super.initState();
    // Load all data on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_loadAllData());
    });
  }

  Future<void> _loadAllData() async {
    await ref.read(feature.focusStatisticsProvider.notifier).refresh();
  }

  Future<void> _onRefresh() async {
    await ref.read(feature.focusStatisticsProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(feature.focusStatisticsProvider);
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(l10n.focusStatsScreenTitle),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.sync),
            onPressed: state.isRefreshing
                ? null
                : () {
                    unawaited(_onRefresh());
                  },
          ),
        ],
      ),
      child: ContentConstraint(
        child: SparkleRefreshIndicator(
          onRefresh: _onRefresh,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Period Toggle
                SparkleStaggerItem(
                  index: 0,
                  child: Center(
                    child: FocusStatsPeriodToggle(
                      period: state.period,
                      onChanged: (period) => ref
                          .read(feature.focusStatisticsProvider.notifier)
                          .setPeriod(period),
                    ),
                  ),
                ),

                const SizedBox(height: DS.xl),

                // Overview Cards
                SparkleStaggerItem(
                  index: 1,
                  child: FocusStatsOverviewCards(
                    todayMinutes: state.todayMinutes,
                    weekTotalMinutes:
                        state.weeklyData?['total_minutes'] as int? ?? 0,
                    streakDays: state.streakDays,
                    longestStreak: state.longestStreak,
                  ),
                ),

                const SizedBox(height: DS.xl),

                // Chart Section
                SparkleStaggerItem(
                  index: 2,
                  child: _buildSection(
                    title: l10n.focusStatsTrendTitle,
                    child: FocusStatsChart(
                      dailyData: state.dailyBreakdown,
                      period: state.period,
                    ),
                  ),
                ),

                const SizedBox(height: DS.xl),

                // Heatmap Section
                SparkleStaggerItem(
                  index: 3,
                  child: _buildSection(
                    title: l10n.focusStatsHeatmapRange(90),
                    child: FocusStatsHeatmap(
                      data: state.heatmapData,
                    ),
                  ),
                ),

                const SizedBox(height: DS.xl),

                // Session History
                SparkleStaggerItem(
                  index: 4,
                  child: _buildSection(
                    title: l10n.focusStatsRecentSessionsTitle,
                    child: FocusStatsSessionList(
                      sessions: state.sessionHistory,
                      hasMore: state.sessionHistory.length >= 20,
                      onLoadMore: () => unawaited(
                        ref
                            .read(feature.focusStatisticsProvider.notifier)
                            .loadSessionHistory(
                              limit: state.sessionHistory.length + 20,
                            ),
                      ),
                      isLoading: state.isLoading,
                    ),
                  ),
                ),

                const SizedBox(height: DS.xxl),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSection({required String title, required Widget child}) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.md),
            child,
          ],
        ),
      );
}
