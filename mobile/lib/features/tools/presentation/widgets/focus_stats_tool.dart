import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart'
    as feature;
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_chart.dart';
import 'package:sparkle/features/focus/presentation/widgets/focus_stats_session_list.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class FocusStatsTool extends ConsumerStatefulWidget {
  const FocusStatsTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  ConsumerState<FocusStatsTool> createState() => _FocusStatsToolState();
}

class _FocusStatsToolState extends ConsumerState<FocusStatsTool> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refresh();
    });
  }

  void _refresh() {
    unawaited(
      ref.read(feature.focusStatisticsProvider.notifier).loadTodayStats(),
    );
    unawaited(
      ref.read(feature.focusStatisticsProvider.notifier).loadWeeklyStats(),
    );
    unawaited(
      ref
          .read(feature.focusStatisticsProvider.notifier)
          .loadSessionHistory(limit: 5),
    );
  }

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final state = ref.watch(feature.focusStatisticsProvider);
    final accent = DS.prismBlue;
    final totalSessions = state.sessionHistory.length;
    final averageDaily = state.dailyBreakdown.isEmpty
        ? 0
        : (state.dailyBreakdown.values.reduce((a, b) => a + b) /
                state.dailyBreakdown.length)
            .round();

    return ToolShell(
      surface: widget.surface,
      icon: Icons.bar_chart_rounded,
      title: context.l10n.toolsStatsTitle,
      subtitle: context.l10n.toolsStatsSubtitle,
      accentColor: accent,
      compactHeader: true,
      headerAction: SparkleIconButton(
        icon: const Icon(Icons.refresh_rounded),
        onPressed: _refresh,
        variant: ButtonVariant.ghost,
      ),
      heroChips: [
        ToolHeroChip(
          label: context.l10n.toolsStatsStreak(state.streakDays),
          accentColor: accent,
          icon: Icons.local_fire_department_rounded,
        ),
        ToolHeroChip(
          label: totalSessions == 0 ? context.l10n.toolsStatsWaitingData : (zh ? '$totalSessions 条最近记录' : '$totalSessions recent sessions'),
          accentColor: accent,
          icon: Icons.history_rounded,
        ),
      ],
      body: state.isLoading
          ? Center(child: CircularProgressIndicator(color: accent))
          : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ToolMetricRow(
                    children: [
                      ToolMetricCard(
                        label: context.l10n.toolsStatsTodayFocus,
                        value: state.todayFormatted,
                        accentColor: accent,
                        icon: Icons.today_rounded,
                      ),
                      ToolMetricCard(
                        label: context.l10n.toolsStatsWeekTotal,
                        value: state.weekTotalFormatted,
                        accentColor: accent,
                        icon: Icons.calendar_view_week_rounded,
                      ),
                      ToolMetricCard(
                        label: context.l10n.toolsStatsDailyAvg,
                        value: zh ? '$averageDaily 分' : '$averageDaily min',
                        accentColor: accent,
                        icon: Icons.stacked_line_chart_rounded,
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing16),
                  ToolSectionCard(
                    accentColor: accent,
                    title: context.l10n.toolsStatsWeekTrend,
                    subtitle: context.l10n.toolsStatsWeekTrendDesc,
                    child: state.dailyBreakdown.isEmpty
                        ? ToolEmptyState(
                            icon: Icons.insights_rounded,
                            title: context.l10n.toolsStatsNoTrend,
                            description: context.l10n.toolsStatsNoTrendDesc,
                            accentColor: accent,
                          )
                        : SizedBox(
                            height: 168,
                            child: FocusStatsChart(
                              dailyData: state.dailyBreakdown,
                              period: feature.StatsViewPeriod.week,
                            ),
                          ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  ToolSectionCard(
                    accentColor: accent,
                    title: context.l10n.toolsStatsRecentSessions,
                    subtitle: context.l10n.toolsStatsRecentDesc,
                    child: FocusStatsSessionList(
                      sessions: state.sessionHistory.take(5).toList(),
                    ),
                  ),
                ],
              ),
    );
  }
}
