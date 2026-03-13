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
      title: '专注统计',
      subtitle: '把计时和专注行为沉淀成结构化洞察，方便你判断节奏是否稳定、是否需要调整工作块长度。',
      accentColor: accent,
      compactHeader: true,
      headerAction: SparkleIconButton(
        icon: const Icon(Icons.refresh_rounded),
        onPressed: _refresh,
        variant: ButtonVariant.ghost,
      ),
      heroChips: [
        ToolHeroChip(
          label: '${state.streakDays} 天连续专注',
          accentColor: accent,
          icon: Icons.local_fire_department_rounded,
        ),
        ToolHeroChip(
          label: totalSessions == 0 ? '等待数据' : '$totalSessions 条最近记录',
          accentColor: accent,
          icon: Icons.history_rounded,
        ),
      ],
      body: state.isLoading
          ? Center(child: CircularProgressIndicator(color: accent))
          : SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Wrap(
                    spacing: DS.spacing12,
                    runSpacing: DS.spacing12,
                    children: [
                      ToolMetricCard(
                        label: '今日专注',
                        value: state.todayFormatted,
                        accentColor: accent,
                        icon: Icons.today_rounded,
                      ),
                      ToolMetricCard(
                        label: '本周累计',
                        value: state.weekTotalFormatted,
                        accentColor: accent,
                        icon: Icons.calendar_view_week_rounded,
                      ),
                      ToolMetricCard(
                        label: '日均专注',
                        value: '$averageDaily 分',
                        accentColor: accent,
                        icon: Icons.stacked_line_chart_rounded,
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing16),
                  ToolSectionCard(
                    accentColor: accent,
                    title: '本周趋势',
                    subtitle: '最近 7 天的专注时长变化。',
                    child: state.dailyBreakdown.isEmpty
                        ? ToolEmptyState(
                            icon: Icons.insights_rounded,
                            title: '还没有趋势数据',
                            description: '完成几次专注会话后，这里会形成有参考价值的趋势图。',
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
                    title: '最近会话',
                    subtitle: '帮助你回看最近的专注节奏和时长结构。',
                    child: FocusStatsSessionList(
                      sessions: state.sessionHistory.take(5).toList(),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
