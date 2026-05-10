import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/share_poster_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/chat_continuity_banner.dart';
import 'package:sparkle/core/widgets/mirofish_stage_header.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/mirofish/presentation/support/mirofish_milestone_service.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

enum _ReportRange { week, month, all }

class _HistoricalReportEntry {
  const _HistoricalReportEntry({
    required this.report,
    required this.createdAt,
  });

  final LearningReport report;
  final DateTime createdAt;
}

class LearningReportScreen extends ConsumerStatefulWidget {
  const LearningReportScreen({
    required this.report,
    super.key,
    this.initialSourceChatSessionId,
  });

  final LearningReport report;
  final String? initialSourceChatSessionId;

  @override
  ConsumerState<LearningReportScreen> createState() =>
      _LearningReportScreenState();
}

class _LearningReportScreenState extends ConsumerState<LearningReportScreen> {
  static const _historyCacheKey = 'learning_report_history_v1';
  static const _maxCachedReports = 8;

  int? _selectedMasteryIndex;
  _ReportRange _range = _ReportRange.week;
  bool _hasTrackedView = false;
  List<_HistoricalReportEntry> _cachedHistoryEntries = const [];
  bool _historyCacheLoaded = false;
  Map<String, dynamic>? _executionProfile;
  bool _executionProfileLoaded = false;

  bool get _aiAnalysisInitiallyExpanded => false;

  @override
  void initState() {
    super.initState();
    unawaited(_bootstrapHistoryCache());
    unawaited(_loadExecutionProfile());
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_hasTrackedView) {
        return;
      }
      _hasTrackedView = true;
      unawaited(
        ref.read(appEventStreamServiceProvider).recordReportViewed(
              reportId: widget.report.reportId,
              masteryItemCount: widget.report.mastery.length,
            ),
      );
      unawaited(_celebrateReportMilestone());
    });
  }

  Future<void> _bootstrapHistoryCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cached = _decodeHistoryEntries(prefs.getString(_historyCacheKey));
      final merged = _mergeHistoryEntries(<_HistoricalReportEntry>[
        _HistoricalReportEntry(
          report: widget.report,
          createdAt: DateTime.now(),
        ),
        ...cached,
      ]);
      await prefs.setString(
        _historyCacheKey,
        jsonEncode(
          merged
              .take(_maxCachedReports)
              .map(
                (entry) => <String, dynamic>{
                  'created_at': entry.createdAt.toIso8601String(),
                  'report': entry.report.toJson(),
                },
              )
              .toList(),
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _cachedHistoryEntries = merged;
        _historyCacheLoaded = true;
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _cachedHistoryEntries = const [];
        _historyCacheLoaded = true;
      });
    }
  }

  Future<void> _loadExecutionProfile() async {
    try {
      final response = await ref.read(apiClientProvider).get<dynamic>(
            ApiEndpoints.executionProfileSummary,
          );
      final data = response.data;
      if (!mounted) return;
      setState(() {
        _executionProfile =
            data is Map ? Map<String, dynamic>.from(data) : null;
        _executionProfileLoaded = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _executionProfileLoaded = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final report = _resolveActiveReport(widget.report);
    final chartData = report.mastery.take(6).toList();
    final reportDataStatus = (report.dataStatus ?? 'sufficient').trim();
    final isInsufficientData = reportDataStatus == 'insufficient';
    final isPartialData = reportDataStatus == 'partial';
    final averageMastery = _averageMastery(report);
    final strongCount =
        report.mastery.where((item) => item.masteryScore >= 80).length;
    final weakCount =
        report.mastery.where((item) => item.masteryScore < 60).length;
    final history = _loadHistoryEntries(report);
    final filteredHistory = _filterHistory(history);
    final previousReport =
        filteredHistory.length > 1 ? filteredHistory[1].report : null;
    final strongestNode = _strongestMasteryNode(report);
    final weakestNode = _weakestMasteryNode(report);
    final structuredTrendPoints =
        report.trendOverview?.historyPoints ?? const [];
    final trendPoints = structuredTrendPoints.isNotEmpty
        ? structuredTrendPoints
            .map((point) => (point.averageMastery / 100).clamp(0.0, 1.0))
            .toList()
        : filteredHistory
            .map((entry) => _averageMastery(entry.report) / 100)
            .toList()
            .reversed
            .toList();
    final trendLabels = structuredTrendPoints.isNotEmpty
        ? structuredTrendPoints.map((point) => point.label).toList()
        : filteredHistory
            .map(
              (entry) => '${entry.createdAt.month}/${entry.createdAt.day}',
            )
            .toList()
            .reversed
            .toList();
    final trendStudyMinutes = structuredTrendPoints.isNotEmpty
        ? structuredTrendPoints
            .map((point) => point.studyMinutes.toDouble())
            .toList()
        : const <double>[];

    return Scaffold(
      appBar: AppBar(
        title: Text(context.l10n.reportLearningAnalysisReport),
        actions: [
          IconButton(
            onPressed: () => unawaited(_showReportShareSheet(report)),
            icon: const Icon(Icons.share_outlined),
          ),
        ],
      ),
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.38),
              Theme.of(context).scaffoldBackgroundColor,
            ],
          ),
        ),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if ((widget.initialSourceChatSessionId ?? '')
                .trim()
                .isNotEmpty) ...[
              ChatContinuityBanner(
                sourceChatSessionId: widget.initialSourceChatSessionId!.trim(),
                kind: ChatContinuityKind.journey,
                subtitle: context.l10n.reportContinuationSubtitle,
              ),
              const SizedBox(height: 14),
            ],
            if (report.triggerSummary != null) ...[
              _AnimatedReportSection(
                delay: 0,
                child: _ReportTriggerBanner(
                  triggerSummary: report.triggerSummary!,
                ),
              ),
              const SizedBox(height: 14),
            ],
            if (isPartialData) ...[
              _AnimatedReportSection(
                delay: 20,
                child: _ReportDataStatusBanner(
                  label: context.l10n.reportPartialDataDisclaimer,
                  message: context.l10n.reportPartialDataMessage,
                ),
              ),
              const SizedBox(height: 14),
            ],
            _AnimatedReportSection(
              delay: 0,
              child: MirofishStageHeader(
                icon: Icons.insights_rounded,
                eyebrow: context.l10n.reportDiagnosisPanelEyebrow,
                title: _reportHeroTitle(
                  weakestNode: weakestNode,
                  strongestNode: strongestNode,
                  averageMastery: averageMastery,
                ),
                subtitle: _reportHeroSubtitle(
                  weakestNode: weakestNode,
                  strongestNode: strongestNode,
                  averageMastery: averageMastery,
                  previousAverageMastery: previousReport == null
                      ? null
                      : _averageMastery(previousReport),
                ),
                metrics: _reportHeroMetrics(
                  averageMastery: averageMastery,
                  weakestNode: weakestNode,
                  strongestNode: strongestNode,
                  previousAverageMastery: previousReport == null
                      ? null
                      : _averageMastery(previousReport),
                ),
                primaryLabel: weakestNode == null
                    ? context.l10n.reportOpenGalaxy
                    : context.l10n.reportPrioritizeNode(weakestNode.nodeName),
                onPrimaryTap: weakestNode == null
                    ? () => unawaited(_openReportDeepLink(GalaxyRoutes.home))
                    : () => unawaited(
                          _openReportDeepLink(
                            '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(weakestNode.nodeName)}',
                          ),
                        ),
                footer: history.length > 1
                    ? SegmentedButton<_ReportRange>(
                        segments: [
                           ButtonSegment<_ReportRange>(
                             value: _ReportRange.week,
                             label: Text(context.l10n.reportRangeWeek),
                           ),
                           ButtonSegment<_ReportRange>(
                             value: _ReportRange.month,
                             label: Text(context.l10n.reportRangeMonth),
                           ),
                           ButtonSegment<_ReportRange>(
                             value: _ReportRange.all,
                             label: Text(context.l10n.reportRangeAll),
                           ),
                        ],
                        selected: <_ReportRange>{_range},
                        onSelectionChanged: (selection) {
                          setState(() => _range = selection.first);
                        },
                      )
                    : null,
                accent: DS.info,
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 50,
              child: _ReportDiagnosisStrip(
                diagnosisCards: report.diagnosisCards,
                strongestNode: strongestNode,
                weakestNode: weakestNode,
                averageMastery: averageMastery,
                previousAverageMastery: previousReport == null
                    ? null
                    : _averageMastery(previousReport),
                onCardTap: _showDiagnosisDetail,
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 90,
              child: _ReportActionCard(
                actionCards: report.actionCards,
                weakestNode: weakestNode,
                strongestNode: strongestNode,
                onOpenGalaxy: () =>
                    unawaited(_openReportDeepLink(GalaxyRoutes.home)),
                onOpenTheater: weakestNode == null
                    ? null
                    : () => unawaited(
                          _openReportDeepLink(
                            '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(weakestNode.nodeName)}',
                          ),
                        ),
                onOpenSimulation: () => unawaited(
                  _openReportDeepLink(
                    '${SimulationRoutes.simulation}?topic=${Uri.encodeComponent(weakestNode?.nodeName ?? strongestNode?.nodeName ?? context.l10n.reportCurrentLearningTopic)}&scenario_key=study_group',
                  ),
                ),
                onOpenSprintHistory: () =>
                    unawaited(_openReportDeepLink(PlanRoutes.sprintHistory)),
                onActionTap: _openReportDeepLink,
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 120,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.reportMasteryTrendTitle,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 8),
                    if ((report.trendOverview?.headline ?? '').isNotEmpty) ...[
                      if (isPartialData) ...[
                        _InlineStatusPill(label: context.l10n.reportPartialDataPill),
                        const SizedBox(height: 8),
                      ],
                      Text(
                        report.trendOverview!.headline,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        report.trendOverview!.summary,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                      if (report.trendOverview!.comparisons.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: report.trendOverview!.comparisons
                              .map(
                                (item) => _TrendComparisonChip(
                                  comparison: item,
                                ),
                              )
                              .toList(),
                        ),
                        const SizedBox(height: 12),
                      ] else
                        const SizedBox(height: 12),
                    ],
                    if (isInsufficientData)
                      _ReportEmptyPanel(
                        title: context.l10n.reportTrendEmptyTitle,
                        message: context.l10n.reportTrendEmptyMessage,
                      )
                    else if ((report.trendOverview?.status ?? 'ready') ==
                        'no_data')
                      _TrendHistoryEmptyState(
                        historyCacheLoaded: _historyCacheLoaded,
                        title: context.l10n.reportTrendEmptyTitle,
                        message: report.trendOverview?.message,
                      )
                    else if (trendPoints.length > 1)
                      SizedBox(
                        height: 236,
                        child: _MasteryTrendChart(
                          values: trendPoints,
                          labels: trendLabels,
                          studyMinutes: trendStudyMinutes,
                        ),
                      )
                    else
                      _TrendHistoryEmptyState(
                        historyCacheLoaded: _historyCacheLoaded,
                      ),
                    const SizedBox(height: 12),
                    Text(
                      context.l10n.reportTrendChartHint,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 180,
              child: ExpansionTile(
                initiallyExpanded: true,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                collapsedShape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                title: Text(context.l10n.reportRadarChartTitle),
                subtitle: Text(
                  isInsufficientData
                      ? context.l10n.reportRadarSubtitleInsufficient
                      : previousReport == null
                          ? context.l10n.reportRadarSubtitleNoComparison
                          : context.l10n.reportRadarSubtitleWithComparison,
                ),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  if (isInsufficientData)
                    _ReportEmptyPanel(
                      title: context.l10n.reportRadarSubtitleInsufficient,
                      message: context.l10n.reportRadarEmptyMessage,
                    )
                  else ...[
                    if (isPartialData) ...[
                       Align(
                         alignment: Alignment.centerLeft,
                         child: _InlineStatusPill(label: context.l10n.reportPartialDataPill),
                       ),
                       const SizedBox(height: 12),
                     ],
                    TweenAnimationBuilder<double>(
                      tween: Tween(begin: 0, end: 1),
                      duration: DS.durationSlow,
                      curve: Curves.easeOutCubic,
                      builder: (context, progress, child) => MasteryRadarChart(
                        labels: chartData.map((item) => item.nodeName).toList(),
                        values: chartData
                            .map(
                              (item) => ((item.masteryScore / 100) * progress)
                                  .clamp(0.0, 1.0),
                            )
                            .toList(),
                        secondaryValues: _comparisonValuesFor(
                          chartData,
                          previousReport,
                        ),
                        selectedIndex: _selectedMasteryIndex,
                        onValueTap: (index) {
                          setState(() => _selectedMasteryIndex = index);
                          unawaited(_showMasteryDetail(chartData[index]));
                        },
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 220,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.reportKeyMetricsTitle,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        _MetricCard(
                          label: context.l10n.reportMetricTotalMastery,
                          value: '${averageMastery.round()}%',
                        ),
                        _MetricCard(
                          label: context.l10n.reportMetricKnowledgeCount,
                          value: '${report.mastery.length}',
                        ),
                        _MetricCard(
                          label: context.l10n.reportMetricStrengths,
                          value: '$strongCount',
                        ),
                        _MetricCard(
                          label: context.l10n.reportMetricWeaknesses,
                          value: '$weakCount',
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            if (_executionProfileLoaded && _executionProfile != null) ...[
              const SizedBox(height: 14),
              _AnimatedReportSection(
                delay: 260,
                child: _ExecutionStatsSection(profile: _executionProfile!),
              ),
            ] else if (_executionProfileLoaded) ...[
              const SizedBox(height: 14),
              _AnimatedReportSection(
                delay: 260,
                child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Row(
                    children: [
                      const Icon(Icons.insights_outlined, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          context.l10n.reportExecutionProfileLoadFailed,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.4,
                                  ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 320,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.reportKeyDimensionsTitle,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: report.mastery
                          .take(8)
                          .map(
                            (item) => ActionChip(
                              avatar: Icon(
                                _masteryIcon(item.masteryScore),
                                size: 16,
                                color: _masteryColor(
                                  item.masteryScore,
                                  Theme.of(context).colorScheme,
                                ),
                              ),
                              label: Text(
                                '${item.nodeName} ${item.masteryScore.round()}%',
                              ),
                              onPressed: () => _showMasteryDetail(item),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 420,
              child: ExpansionTile(
                initiallyExpanded: _aiAnalysisInitiallyExpanded,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                collapsedShape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
                title: Text(context.l10n.reportAiAnalysisTitle),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    child: LayoutBuilder(
                      builder: (context, constraints) => SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            minWidth: constraints.maxWidth,
                          ),
                          child: SparkleMarkdown(
                            content: report.markdown,
                            textColor: Theme.of(context).colorScheme.onSurface,
                            codeBackgroundColor: Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                            linkColor: Theme.of(context).colorScheme.primary,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _AnimatedReportSection(
              delay: 520,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    FilledButton.tonalIcon(
                      onPressed: () =>
                          unawaited(_openReportDeepLink(GalaxyRoutes.home)),
                      icon: const Icon(Icons.auto_graph_rounded),
                      label: Text(context.l10n.reportBackToGalaxy),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => unawaited(
                        _openReportDeepLink(PlanRoutes.sprintHistory),
                      ),
                      icon: const Icon(Icons.history_rounded),
                      label: Text(context.l10n.reportViewSprintHistory),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _celebrateReportMilestone() async {
    await MirofishMilestoneService.celebrateIfFirstTime(
      context,
      ref,
      kind: MirofishMilestoneKind.firstReport,
      onShare: () {
        unawaited(_showReportShareSheet(widget.report));
      },
    );
  }

  Future<void> _showReportShareSheet(LearningReport report) async {
    final weakest = _weakestMasteryNode(report);
    final averageMastery = _averageMastery(report).round();
    await showUniversalShareSheet(
      context,
      payload: UniversalSharePayload(
        contentType: ShareableContentType.learningReport,
        resourceId: report.reportId,
        title: context.l10n.reportShareTitle(averageMastery),
        subtitle: weakest == null ? context.l10n.reportShareSubtitleSummary : context.l10n.reportShareSubtitlePriority(weakest.nodeName),
        description: report.markdown,
        metadata: <String, dynamic>{
          'active_plans': report.sections.length,
          'unlocked_achievements': report.diagnosisCards.length,
          'flame_brightness': context.l10n.reportShareMetadataDimensions(report.mastery.length),
        },
        shareMessage: weakest == null
            ? context.l10n.reportShareMessageWithMastery(averageMastery)
            : context.l10n.reportShareMessageWithNode(weakest.nodeName),
      ),
      onGenerateCard: (payload) =>
          SharePosterService().generatePoster(context, payload),
    );
  }

  double _averageMastery(LearningReport report) => report.mastery.isEmpty
      ? 0.0
      : report.mastery
              .map((item) => item.masteryScore)
              .fold<double>(0, (sum, value) => sum + value) /
          report.mastery.length;

  LearningMasteryDatum? _strongestMasteryNode(LearningReport report) {
    if (report.mastery.isEmpty) {
      return null;
    }
    final sorted = [...report.mastery]
      ..sort((a, b) => b.masteryScore.compareTo(a.masteryScore));
    return sorted.first;
  }

  LearningMasteryDatum? _weakestMasteryNode(LearningReport report) {
    if (report.mastery.isEmpty) {
      return null;
    }
    final sorted = [...report.mastery]
      ..sort((a, b) => a.masteryScore.compareTo(b.masteryScore));
    return sorted.first;
  }

  String _reportHeroTitle({
    required LearningMasteryDatum? weakestNode,
    required LearningMasteryDatum? strongestNode,
    required double averageMastery,
  }) {
    if (weakestNode != null) {
      return context.l10n.reportHeroTitlePriority(weakestNode.nodeName);
    }
    if (strongestNode != null) {
      return context.l10n.reportHeroTitleStable;
    }
    return context.l10n.reportHeroTitleBuild;
  }

  String _reportHeroSubtitle({
    required LearningMasteryDatum? weakestNode,
    required LearningMasteryDatum? strongestNode,
    required double averageMastery,
    required double? previousAverageMastery,
  }) {
    final delta = previousAverageMastery == null
        ? null
        : _averageDelta(averageMastery, previousAverageMastery);
    if (weakestNode != null && delta != null) {
      return delta >= 0
          ? context.l10n.reportHeroSubtitleDeltaUp(weakestNode.nodeName)
          : context.l10n.reportHeroSubtitleDeltaDown(weakestNode.nodeName);
    }
    if (strongestNode != null) {
      return context.l10n.reportHeroSubtitleStrong;
    }
    return context.l10n.reportHeroSubtitleDefault;
  }

  List<MirofishStageMetric> _reportHeroMetrics({
    required double averageMastery,
    required LearningMasteryDatum? weakestNode,
    required LearningMasteryDatum? strongestNode,
    required double? previousAverageMastery,
  }) {
    final metrics = <MirofishStageMetric>[
      MirofishStageMetric(
        label: context.l10n.reportMetricAvgMastery,
        value: '${averageMastery.round()}%',
        accent: DS.info,
        icon: Icons.stacked_line_chart_rounded,
      ),
    ];
    if (weakestNode != null) {
      metrics.add(
        MirofishStageMetric(
          label: context.l10n.reportMetricPriority,
          value: '${weakestNode.nodeName} ${weakestNode.masteryScore.round()}%',
          accent: DS.warning,
          icon: Icons.flag_circle_rounded,
        ),
      );
    }
    if (strongestNode != null) {
      metrics.add(
        MirofishStageMetric(
          label: context.l10n.reportMetricCurrentStrength,
          value:
              '${strongestNode.nodeName} ${strongestNode.masteryScore.round()}%',
          accent: DS.success,
          icon: Icons.north_east_rounded,
        ),
      );
    } else if (previousAverageMastery != null) {
      final delta = _averageDelta(averageMastery, previousAverageMastery);
      metrics.add(
        MirofishStageMetric(
          label: context.l10n.reportMetricTrendChange,
          value: '${delta >= 0 ? '+' : ''}${delta.round()}%',
          accent: delta >= 0 ? DS.success : DS.warning,
          icon: delta >= 0
              ? Icons.trending_up_rounded
              : Icons.trending_down_rounded,
        ),
      );
    }
    return metrics.take(3).toList();
  }

  double _averageDelta(double current, double previous) => current - previous;

  LearningReport _resolveActiveReport(LearningReport fallbackReport) {
    if (!_isPlaceholderReport(fallbackReport)) {
      return fallbackReport;
    }
    final latest = _latestReportFromSystemUpdates();
    return latest ?? fallbackReport;
  }

  bool _isPlaceholderReport(LearningReport report) =>
      report.reportId == 'empty' &&
      report.mastery.isEmpty &&
      report.markdown.trim() == context.l10n.reportPlaceholderEmpty;

  LearningReport? _latestReportFromSystemUpdates() {
    final updates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );
    for (final item in updates) {
      if (item['type']?.toString() != 'learning_report_ready') {
        continue;
      }
      final metadata = item['metadata'];
      if (metadata is! Map) {
        continue;
      }
      final payload = metadata['report_payload'];
      if (payload is! Map) {
        continue;
      }
      return LearningReport.fromJson(Map<String, dynamic>.from(payload));
    }
    return null;
  }

  List<_HistoricalReportEntry> _loadHistoryEntries(
    LearningReport currentReport,
  ) {
    final updates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );
    final entries = <_HistoricalReportEntry>[
      _HistoricalReportEntry(
        report: currentReport,
        createdAt: DateTime.now(),
      ),
      ..._cachedHistoryEntries,
    ];
    for (final item in updates) {
      if (item['type']?.toString() != 'learning_report_ready') {
        continue;
      }
      final metadata = item['metadata'];
      if (metadata is! Map) {
        continue;
      }
      final payload = metadata['report_payload'];
      if (payload is! Map) {
        continue;
      }
      final report =
          LearningReport.fromJson(Map<String, dynamic>.from(payload));
      final createdAt = DateTime.tryParse(item['created_at']?.toString() ?? '');
      entries.add(
        _HistoricalReportEntry(
          report: report,
          createdAt: createdAt ?? DateTime.now(),
        ),
      );
    }
    return _mergeHistoryEntries(entries);
  }

  List<_HistoricalReportEntry> _mergeHistoryEntries(
    List<_HistoricalReportEntry> entries,
  ) {
    final deduped = <String, _HistoricalReportEntry>{};
    for (final entry in entries) {
      final reportId = entry.report.reportId.trim();
      final dedupeKey =
          reportId.isNotEmpty ? reportId : jsonEncode(entry.report.toJson());
      final existing = deduped[dedupeKey];
      if (existing == null || entry.createdAt.isAfter(existing.createdAt)) {
        deduped[dedupeKey] = entry;
      }
    }
    final list = deduped.values.toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  List<_HistoricalReportEntry> _decodeHistoryEntries(String? raw) {
    if (raw == null || raw.isEmpty) {
      return const [];
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) {
        return const [];
      }
      return decoded
          .whereType<Map<String, dynamic>>()
          .map((item) {
            final reportJson = item['report'];
            if (reportJson is! Map) {
              return null;
            }
            return _HistoricalReportEntry(
              report: LearningReport.fromJson(
                Map<String, dynamic>.from(reportJson),
              ),
              createdAt: DateTime.tryParse(
                    item['created_at']?.toString() ?? '',
                  ) ??
                  DateTime.now(),
            );
          })
          .whereType<_HistoricalReportEntry>()
          .toList();
    } catch (_) {
      return const [];
    }
  }

  List<_HistoricalReportEntry> _filterHistory(
    List<_HistoricalReportEntry> history,
  ) {
    final now = DateTime.now();
    return history.where((entry) {
      switch (_range) {
        case _ReportRange.week:
          return now.difference(entry.createdAt).inDays <= 7;
        case _ReportRange.month:
          return now.difference(entry.createdAt).inDays <= 30;
        case _ReportRange.all:
          return true;
      }
    }).toList();
  }

  List<double>? _comparisonValuesFor(
    List<LearningMasteryDatum> current,
    LearningReport? previous,
  ) {
    if (previous == null || previous.mastery.isEmpty) {
      return null;
    }
    final byName = <String, double>{
      for (final item in previous.mastery)
        item.nodeName: item.masteryScore / 100,
    };
    return current.map((item) => byName[item.nodeName] ?? 0.0).toList();
  }

  Future<void> _showMasteryDetail(LearningMasteryDatum item) async {
    final score = item.masteryScore;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (sheetContext) {
        final scheme = Theme.of(sheetContext).colorScheme;
        final masteryColor = _masteryColor(score, scheme);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.nodeName,
                  style:
                      Theme.of(sheetContext).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: masteryColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    '${score.round()}% · ${_masteryLabel(score, sheetContext)}',
                    style:
                        Theme.of(sheetContext).textTheme.labelLarge?.copyWith(
                              color: masteryColor,
                              fontWeight: DS.fontWeightBold,
                            ),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  _masteryGuidance(item, sheetContext),
                  style: Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.5,
                      ),
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    FilledButton.tonalIcon(
                      onPressed: () {
                        Navigator.of(sheetContext).pop();
                        unawaited(_openReportDeepLink(GalaxyRoutes.home));
                      },
                      icon: const Icon(Icons.auto_graph_rounded),
                      label: Text(context.l10n.reportOpenGalaxy),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.of(sheetContext).pop(),
                      icon: const Icon(Icons.check_circle_outline_rounded),
                      label: Text(context.l10n.reportContinueReading),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _showDiagnosisDetail(LearningReportDiagnosticCard card) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (sheetContext) {
        final accent = _diagnosisAccent(
          card.severity,
          Theme.of(sheetContext).colorScheme,
        );
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  card.title,
                  style: Theme.of(sheetContext).textTheme.labelLarge?.copyWith(
                        color: accent,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  card.headline,
                  style:
                      Theme.of(sheetContext).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                ),
                const SizedBox(height: 12),
                Text(
                  card.summary,
                  style: Theme.of(sheetContext).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.5,
                      ),
                ),
                if (card.evidence.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Text(
                    context.l10n.reportEvidenceAndAdvice,
                    style:
                        Theme.of(sheetContext).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                  ),
                  const SizedBox(height: 10),
                  ...card.evidence.map(
                    (item) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(top: 6),
                            child: Icon(
                              Icons.fiber_manual_record_rounded,
                              size: 10,
                              color: accent,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              item,
                              style: Theme.of(sheetContext)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.45,
                                  ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    if ((card.deepLink ?? '').isNotEmpty &&
                        (card.ctaLabel ?? '').isNotEmpty)
                      FilledButton.icon(
                        onPressed: () {
                          Navigator.of(sheetContext).pop();
                          unawaited(_openReportDeepLink(card.deepLink!));
                        },
                        icon: const Icon(Icons.rocket_launch_rounded),
                        label: Text(card.ctaLabel!),
                      ),
                    OutlinedButton.icon(
                      onPressed: () => Navigator.of(sheetContext).pop(),
                      icon: const Icon(Icons.check_circle_outline_rounded),
                      label: Text(context.l10n.reportGotIt),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _openReportDeepLink(String deepLink) async {
    final normalized = deepLink.trim();
    if (normalized.isEmpty || !mounted) {
      return;
    }
    final parsed = Uri.tryParse(normalized);
    if (parsed == null) {
      await context.push(normalized);
      return;
    }
    final resolved = _resolveReportDeepLinkUri(parsed);
    if (!mounted) {
      return;
    }
    if (resolved.path == GalaxyRoutes.home) {
      context.go(resolved.toString());
      return;
    }
    await context.push(resolved.toString());
  }

  Uri _resolveReportDeepLinkUri(Uri parsed) {
    final query = Map<String, String>.from(parsed.queryParameters);
    final sourceChatSessionId = widget.initialSourceChatSessionId?.trim();
    final path = parsed.path.trim();
    final resolvedPath = switch (path) {
      '/sprint' => PlanRoutes.sprintHistory,
      '' => ReportRoutes.learningReport,
      _ => path,
    };

    final shouldCarryChatContext =
        resolvedPath.startsWith(TheaterRoutes.theater) ||
            resolvedPath.startsWith(SimulationRoutes.simulation) ||
            resolvedPath.startsWith(ReportRoutes.learningReport) ||
            resolvedPath.startsWith(GalaxyRoutes.home);
    if (shouldCarryChatContext &&
        (sourceChatSessionId?.isNotEmpty ?? false) &&
        !query.containsKey('source_chat_session_id')) {
      query['source_chat_session_id'] = sourceChatSessionId!;
    }

    if (resolvedPath.startsWith(GalaxyRoutes.home)) {
      final nodeId = (query['node_id'] ?? query['target_node_id'] ?? '').trim();
      if (nodeId.isNotEmpty) {
        return Uri(path: '${GalaxyRoutes.home}/node/$nodeId');
      }
      final safeQuery = <String, String>{
        if ((query['source_chat_session_id'] ?? '').trim().isNotEmpty)
          'source_chat_session_id': query['source_chat_session_id']!.trim(),
      };
      return Uri(
        path: GalaxyRoutes.home,
        queryParameters: safeQuery.isEmpty ? null : safeQuery,
      );
    }

    return Uri(
      path: resolvedPath,
      queryParameters: query.isEmpty ? null : query,
    );
  }

  String _masteryLabel(double score, BuildContext context) {
    if (score >= 80) {
      return context.l10n.reportMasteryStable;
    }
    if (score >= 60) {
      return context.l10n.reportMasteryConsolidate;
    }
    return context.l10n.reportMasteryNeedFocus;
  }

  String _masteryGuidance(LearningMasteryDatum item, BuildContext context) {
    final score = item.masteryScore;
    if (score >= 80) {
      return context.l10n.reportGuidanceStable;
    }
    if (score >= 60) {
      return context.l10n.reportGuidanceConsolidate;
    }
    return context.l10n.reportGuidanceNeedFocus;
  }

  Color _masteryColor(double score, ColorScheme scheme) {
    if (score >= 80) {
      return DS.success;
    }
    if (score >= 60) {
      return DS.warning;
    }
    return scheme.error;
  }

  IconData _masteryIcon(double score) {
    if (score >= 80) {
      return Icons.trending_up_rounded;
    }
    if (score >= 60) {
      return Icons.timeline_rounded;
    }
    return Icons.priority_high_rounded;
  }

  Color _diagnosisAccent(String severity, ColorScheme scheme) {
    switch (severity) {
      case 'high':
        return scheme.error;
      case 'medium':
        return DS.warning;
      case 'low':
        return DS.success;
      default:
        return DS.info;
    }
  }
}

class _MasteryTrendChart extends StatefulWidget {
  const _MasteryTrendChart({
    required this.values,
    required this.labels,
    this.studyMinutes = const <double>[],
  });

  final List<double> values;
  final List<String> labels;
  final List<double> studyMinutes;

  @override
  State<_MasteryTrendChart> createState() => _MasteryTrendChartState();
}

class _MasteryTrendChartState extends State<_MasteryTrendChart> {
  int? _selectedIndex;

  @override
  void initState() {
    super.initState();
    _selectedIndex = widget.values.isEmpty ? null : widget.values.length - 1;
  }

  @override
  void didUpdateWidget(covariant _MasteryTrendChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.values.isEmpty) {
      _selectedIndex = null;
      return;
    }
    if (_selectedIndex == null || _selectedIndex! >= widget.values.length) {
      _selectedIndex = widget.values.length - 1;
    }
  }

  void _updateSelection(Offset localPosition, double chartWidth) {
    if (widget.values.length < 2 || chartWidth <= 0) {
      return;
    }
    final ratio = (localPosition.dx / chartWidth).clamp(0.0, 1.0);
    final rawIndex = (ratio * (widget.values.length - 1)).round();
    if (_selectedIndex == rawIndex) {
      return;
    }
    setState(() => _selectedIndex = rawIndex);
  }

  bool _shouldShowLabelAt(int index) {
    if (widget.labels.length <= 5) {
      return true;
    }
    if (index == 0 || index == widget.labels.length - 1) {
      return true;
    }
    final step = widget.labels.length >= 9 ? 3 : 2;
    return index % step == 0;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.values.length < 2) {
      return Center(
        child: Text(
          context.l10n.reportChartFirstReport,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.textSecondary,
              ),
          textAlign: TextAlign.center,
        ),
      );
    }
    final showStudyMinutes =
        widget.studyMinutes.length == widget.values.length &&
            widget.studyMinutes.any((item) => item > 0);
    final selectedIndex = (_selectedIndex ?? (widget.values.length - 1))
        .clamp(0, widget.values.length - 1);
    final selectedLabel = widget.labels[selectedIndex];
    final selectedMastery = (widget.values[selectedIndex] * 100).round();
    final selectedMinutes =
        showStudyMinutes ? widget.studyMinutes[selectedIndex].round() : null;
    final maxStudyMinutes = showStudyMinutes && widget.studyMinutes.isNotEmpty
        ? widget.studyMinutes.reduce((a, b) => a > b ? a : b).round()
        : 0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: Theme.of(context)
                .colorScheme
                .surfaceContainerHighest
                .withValues(alpha: 0.46),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                selectedLabel,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              Text(
                context.l10n.reportChartMasteryLabel(selectedMastery),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              if (selectedMinutes != null)
                Text(
                  context.l10n.reportChartStudyMinutes(selectedMinutes),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.warning,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final axisWidth = showStudyMinutes ? 46.0 : 0.0;
              final chartWidth = (constraints.maxWidth - axisWidth)
                  .clamp(0.0, double.infinity);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTapDown: (details) =>
                          _updateSelection(details.localPosition, chartWidth),
                      onHorizontalDragStart: (details) =>
                          _updateSelection(details.localPosition, chartWidth),
                      onHorizontalDragUpdate: (details) =>
                          _updateSelection(details.localPosition, chartWidth),
                      child: TweenAnimationBuilder<double>(
                        tween: Tween<double>(begin: 0, end: 1),
                        duration: const Duration(milliseconds: 700),
                        curve: Curves.easeOutCubic,
                        builder: (context, progress, _) => CustomPaint(
                          painter: _TrendChartPainter(
                            values: widget.values,
                            secondaryValues: widget.studyMinutes,
                            progress: progress,
                            lineColor: Theme.of(context).colorScheme.primary,
                            secondaryLineColor: DS.warning,
                            fillColor: DS.info.withValues(alpha: 0.12),
                            gridColor: Theme.of(context)
                                .colorScheme
                                .outlineVariant
                                .withValues(alpha: 0.5),
                            selectedIndex: selectedIndex,
                            showSecondarySeries: showStudyMinutes,
                          ),
                          child: const SizedBox.expand(),
                        ),
                      ),
                    ),
                  ),
                  if (showStudyMinutes) ...[
                    const SizedBox(width: 10),
                    SizedBox(
                      width: axisWidth,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            context.l10n.reportChartMinutesShort(maxStudyMinutes),
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: DS.warning,
                                  fontWeight: DS.fontWeightBold,
                                ),
                          ),
                          Text(
                            context.l10n.reportChartMinutesShort((maxStudyMinutes / 2).round()),
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: DS.textSecondary,
                                ),
                          ),
                          Text(
                            context.l10n.reportChartZeroMinutes,
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: DS.textSecondary,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              );
            },
          ),
        ),
        const SizedBox(height: 8),
        if (showStudyMinutes) ...[
          Row(
            children: [
              _TrendLegendChip(
                color: Theme.of(context).colorScheme.primary,
                label: context.l10n.reportLegendMastery,
              ),
              const SizedBox(width: 8),
              _TrendLegendChip(
                color: DS.warning,
                label: context.l10n.reportLegendStudyDuration,
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: widget.labels
              .asMap()
              .entries
              .map(
                (entry) => Expanded(
                  child: Text(
                    _shouldShowLabelAt(entry.key) ? entry.value : ' ',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ),
              )
              .toList(),
        ),
      ],
    );
  }
}

class _ReportDiagnosisStrip extends StatelessWidget {
  const _ReportDiagnosisStrip({
    required this.diagnosisCards,
    required this.strongestNode,
    required this.weakestNode,
    required this.averageMastery,
    required this.previousAverageMastery,
    required this.onCardTap,
  });

  final List<LearningReportDiagnosticCard> diagnosisCards;
  final LearningMasteryDatum? strongestNode;
  final LearningMasteryDatum? weakestNode;
  final double averageMastery;
  final double? previousAverageMastery;
  final ValueChanged<LearningReportDiagnosticCard> onCardTap;

  @override
  Widget build(BuildContext context) {
    final delta = previousAverageMastery == null
        ? null
        : averageMastery - previousAverageMastery!;
    final sortedDiagnosisCards = [...diagnosisCards]..sort(
        (
          LearningReportDiagnosticCard a,
          LearningReportDiagnosticCard b,
        ) =>
            _severityRank(a.severity).compareTo(
          _severityRank(b.severity),
        ),
      );
    final cards = diagnosisCards.isNotEmpty
        ? sortedDiagnosisCards
            .map(
              (LearningReportDiagnosticCard item) => _DiagnosisCard(
                title: item.title,
                headline: item.headline,
                body: item.summary,
                icon: _diagnosisIcon(item.severity),
                accent: _diagnosisAccent(
                  item.severity,
                  Theme.of(context).colorScheme,
                ),
                tag: (item.tag ?? '').trim().isNotEmpty
                    ? item.tag
                    : _decisionTag(item.severity, context),
                onTap: () => onCardTap(item),
              ),
            )
            .toList()
        : <Widget>[
            _DiagnosisCard(
              title: context.l10n.reportDiagnosisTitleStrength,
              headline: strongestNode == null
                  ? context.l10n.reportDiagnosisHeadlinePending
                  : '${strongestNode!.nodeName} ${strongestNode!.masteryScore.round()}%',
              body: strongestNode == null
                  ? context.l10n.reportDiagnosisStrengthBodyPending
                  : context.l10n.reportDiagnosisStrengthBodyData,
              icon: Icons.trending_up_rounded,
              accent: DS.success,
              tag: context.l10n.reportTagConsolidate,
            ),
            _DiagnosisCard(
              title: context.l10n.reportDiagnosisTitleWeakness,
              headline: weakestNode == null
                  ? context.l10n.reportDiagnosisHeadlinePending
                  : '${weakestNode?.nodeName ?? context.l10n.reportDiagnosisWeaknessFallback} ${weakestNode?.masteryScore.round() ?? 0}%',
              body: weakestNode == null
                  ? context.l10n.reportDiagnosisWeaknessBodyPending
                  : context.l10n.reportDiagnosisWeaknessBodyData,
              icon: Icons.priority_high_rounded,
              accent: Theme.of(context).colorScheme.error,
              tag: context.l10n.reportTagProcessFirst,
            ),
            _DiagnosisCard(
              title: context.l10n.reportDiagnosisTitleTrend,
              headline: delta == null
                  ? context.l10n.reportDiagnosisTrendWaitingComparison
                  : '${delta >= 0 ? '+' : ''}${delta.round()}%',
              body: delta == null
                  ? context.l10n.reportDiagnosisTrendBodyPending
                  : delta >= 0
                      ? context.l10n.reportDiagnosisTrendBodyUp
                      : context.l10n.reportDiagnosisTrendBodyDown,
              icon: delta == null
                  ? Icons.timeline_rounded
                  : delta >= 0
                      ? Icons.north_east_rounded
                      : Icons.south_east_rounded,
              accent: delta == null
                  ? DS.info
                  : delta >= 0
                      ? DS.brandPrimary
                      : DS.warning,
              tag: delta == null
                  ? context.l10n.reportTagAwaitMore
                  : delta >= 0
                      ? context.l10n.reportTagKeepRhythm
                      : context.l10n.reportTagCloseGap,
            ),
          ];
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.reportDiagnosisSummaryTitle,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            context.l10n.reportDiagnosisSummaryDesc,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final availableWidth = constraints.maxWidth;
              final useSingleColumn = availableWidth < 520;
              final cardWidth = useSingleColumn
                  ? availableWidth
                  : ((availableWidth - 12) / 2).clamp(220.0, 320.0);
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: cards
                    .map(
                      (card) => SizedBox(
                        width: cardWidth,
                        child: card,
                      ),
                    )
                    .toList(),
              );
            },
          ),
        ],
      ),
    );
  }

  IconData _diagnosisIcon(String severity) {
    switch (severity) {
      case 'high':
        return Icons.priority_high_rounded;
      case 'medium':
        return Icons.psychology_alt_rounded;
      case 'low':
        return Icons.trending_up_rounded;
      default:
        return Icons.insights_rounded;
    }
  }

  Color _diagnosisAccent(String severity, ColorScheme scheme) {
    switch (severity) {
      case 'high':
        return scheme.error;
      case 'medium':
        return DS.warning;
      case 'low':
        return DS.success;
      default:
        return DS.info;
    }
  }

  int _severityRank(String severity) {
    switch (severity) {
      case 'high':
        return 0;
      case 'medium':
        return 1;
      case 'low':
        return 2;
      default:
        return 3;
    }
  }

  String _decisionTag(String severity, BuildContext context) {
    switch (severity) {
      case 'high':
        return context.l10n.reportTagProcessFirst;
      case 'medium':
        return context.l10n.reportTagProcessSoon;
      case 'low':
        return context.l10n.reportTagConsolidate;
      default:
        return context.l10n.reportTagObserve;
    }
  }
}

class _DiagnosisCard extends StatelessWidget {
  const _DiagnosisCard({
    required this.title,
    required this.headline,
    required this.body,
    required this.icon,
    required this.accent,
    this.tag,
    this.onTap,
  });

  final String title;
  final String headline;
  final String body;
  final IconData icon;
  final Color accent;
  final String? tag;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                accent.withValues(alpha: 0.14),
                Theme.of(context).colorScheme.surface.withValues(alpha: 0.92),
              ],
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: accent.withValues(alpha: 0.14)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if ((tag ?? '').isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    tag!,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: accent,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ),
                const SizedBox(height: 10),
              ],
              Icon(icon, color: accent),
              const SizedBox(height: 10),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                headline,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                body,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
            ],
          ),
        ),
      );
}

class _ReportTriggerBanner extends StatelessWidget {
  const _ReportTriggerBanner({
    required this.triggerSummary,
  });

  final LearningReportTriggerSummary triggerSummary;

  @override
  Widget build(BuildContext context) {
    final accent = switch (triggerSummary.mode) {
      'bottleneck' => Theme.of(context).colorScheme.error,
      'breakthrough' => DS.success,
      'baseline_ready' => DS.info,
      _ => Theme.of(context).colorScheme.primary,
    };
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: accent.withValues(alpha: 0.22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              switch (triggerSummary.mode) {
                'bottleneck' => Icons.warning_amber_rounded,
                'breakthrough' => Icons.auto_awesome_rounded,
                'baseline_ready' => Icons.flag_circle_rounded,
                _ => Icons.insights_rounded,
              },
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  triggerSummary.title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  triggerSummary.summary,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ReportDataStatusBanner extends StatelessWidget {
  const _ReportDataStatusBanner({
    required this.label,
    required this.message,
  });

  final String label;
  final String message;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.warning.withValues(alpha: 0.2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: DS.warning),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    message,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _InlineStatusPill extends StatelessWidget {
  const _InlineStatusPill({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: DS.warning,
                fontWeight: DS.fontWeightBold,
              ),
        ),
      );
}

class _ReportActionCard extends StatelessWidget {
  const _ReportActionCard({
    required this.actionCards,
    required this.weakestNode,
    required this.strongestNode,
    required this.onOpenGalaxy,
    required this.onOpenTheater,
    required this.onOpenSimulation,
    required this.onOpenSprintHistory,
    required this.onActionTap,
  });

  final List<LearningReportActionCard> actionCards;
  final LearningMasteryDatum? weakestNode;
  final LearningMasteryDatum? strongestNode;
  final VoidCallback onOpenGalaxy;
  final VoidCallback? onOpenTheater;
  final VoidCallback onOpenSimulation;
  final VoidCallback onOpenSprintHistory;
  final ValueChanged<String> onActionTap;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.info.withValues(alpha: 0.2),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.reportActionTitle,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              weakestNode == null
                  ? context.l10n.reportActionDescNoWeakness
                  : context.l10n.reportActionDescWithWeakness(
                      weakestNode?.nodeName ?? context.l10n.reportActionWeaknessFallback,
                      strongestNode?.nodeName ?? context.l10n.reportActionStrengthFallback,
                    ),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.5,
                  ),
            ),
            const SizedBox(height: 14),
            if (actionCards.isNotEmpty)
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: actionCards
                    .map(
                      (item) => _ActionSuggestionTile(
                        actionCard: item,
                        onTap: () => onActionTap(item.deepLink),
                      ),
                    )
                    .toList(),
              )
            else
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton.icon(
                    onPressed: onOpenGalaxy,
                    icon: const Icon(Icons.auto_graph_rounded),
                    label: Text(context.l10n.reportOpenGalaxy),
                  ),
                  if (onOpenTheater != null)
                    FilledButton.tonalIcon(
                      onPressed: onOpenTheater,
                      icon: const Icon(Icons.theater_comedy_outlined),
                      label: Text(context.l10n.reportActionExploreNode(weakestNode?.nodeName ?? context.l10n.reportActionWeaknessFallback)),
                    ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenSimulation,
                    icon: const Icon(Icons.groups_rounded),
                    label: Text(context.l10n.reportActionEnterSimulation),
                  ),
                  OutlinedButton.icon(
                    onPressed: onOpenSprintHistory,
                    icon: const Icon(Icons.history_rounded),
                    label: Text(context.l10n.reportViewSprintHistory),
                  ),
                ],
              ),
          ],
        ),
      );
}

class _ActionSuggestionTile extends StatelessWidget {
  const _ActionSuggestionTile({
    required this.actionCard,
    required this.onTap,
  });

  final LearningReportActionCard actionCard;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = switch (actionCard.kind) {
      'theater' => DS.brandPrimary,
      'simulation' => DS.info,
      'galaxy' => DS.success,
      'plan' => DS.warning,
      _ => Theme.of(context).colorScheme.primary,
    };
    final icon = switch (actionCard.kind) {
      'theater' => Icons.alt_route_rounded,
      'simulation' => Icons.groups_rounded,
      'galaxy' => Icons.auto_graph_rounded,
      'plan' => Icons.flag_rounded,
      _ => Icons.arrow_forward_rounded,
    };
    return Container(
      constraints: const BoxConstraints(
        maxWidth: 320,
      ),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 18, color: accent),
              ),
              const Spacer(),
              if ((actionCard.badge ?? '').isNotEmpty)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    actionCard.badge!,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: accent,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            actionCard.title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            actionCard.summary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: onTap,
            icon: const Icon(Icons.arrow_forward_rounded),
            label: Text(actionCard.ctaLabel),
          ),
        ],
      ),
    );
  }
}

class _TrendComparisonChip extends StatelessWidget {
  const _TrendComparisonChip({
    required this.comparison,
  });

  final LearningTrendComparison comparison;

  @override
  Widget build(BuildContext context) {
    final accent = switch (comparison.direction) {
      'up' => DS.success,
      'down' => Theme.of(context).colorScheme.error,
      _ => DS.info,
    };
    return Container(
      constraints: const BoxConstraints(
        maxWidth: 280,
      ),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            comparison.label,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: accent,
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            comparison.summary,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
        ],
      ),
    );
  }
}

class _TrendHistoryEmptyState extends StatelessWidget {
  const _TrendHistoryEmptyState({
    required this.historyCacheLoaded,
    this.title,
    this.message,
  });

  final bool historyCacheLoaded;
  final String? title;
  final String? message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: scheme.outlineVariant.withValues(alpha: 0.45),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.insights_rounded,
                color: scheme.primary,
              ),
              const SizedBox(width: 10),
              Text(
                title ?? context.l10n.reportTrendAutoFillTitle,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            message ??
                (historyCacheLoaded
                    ? context.l10n.reportTrendFirstReportMessage
                    : context.l10n.reportTrendLoadingHistory),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.5,
                ),
          ),
        ],
      ),
    );
  }
}

class _ReportEmptyPanel extends StatelessWidget {
  const _ReportEmptyPanel({
    required this.title,
    required this.message,
  });

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.45),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: scheme.outlineVariant.withValues(alpha: 0.45),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.textSecondary,
                  height: 1.5,
                ),
          ),
        ],
      ),
    );
  }
}

class _TrendChartPainter extends CustomPainter {
  const _TrendChartPainter({
    required this.values,
    required this.progress,
    required this.lineColor,
    required this.secondaryLineColor,
    required this.fillColor,
    required this.gridColor,
    required this.selectedIndex,
    required this.showSecondarySeries,
    this.secondaryValues = const <double>[],
  });

  final List<double> values;
  final List<double> secondaryValues;
  final double progress;
  final Color lineColor;
  final Color secondaryLineColor;
  final Color fillColor;
  final Color gridColor;
  final int selectedIndex;
  final bool showSecondarySeries;

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 1;
    for (var i = 1; i <= 3; i++) {
      final y = size.height * (i / 4);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = values.length == 1
          ? size.width / 2
          : size.width * (i / (values.length - 1));
      final y =
          size.height - (values[i].clamp(0.0, 1.0) * (size.height - 12)) - 6;
      points.add(Offset(x, y));
    }
    if (points.isEmpty) {
      return;
    }

    final path = _buildSmoothPath(points);

    final fillPath = Path.from(path)
      ..lineTo(points.last.dx, size.height)
      ..lineTo(points.first.dx, size.height)
      ..close();

    canvas
      ..save()
      ..clipRect(Rect.fromLTWH(0, 0, size.width * progress, size.height))
      ..drawPath(
        fillPath,
        Paint()..color = fillColor,
      );
    final linePaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawPath(path, linePaint);
    if (showSecondarySeries &&
        secondaryValues.isNotEmpty &&
        secondaryValues.length == values.length) {
      final maxSecondary = secondaryValues.reduce((a, b) => a > b ? a : b);
      final normalizedSecondary = maxSecondary <= 0
          ? List<double>.filled(secondaryValues.length, 0)
          : secondaryValues.map((item) => item / maxSecondary).toList();
      final secondaryPoints = <Offset>[];
      for (var i = 0; i < normalizedSecondary.length; i++) {
        final x = normalizedSecondary.length == 1
            ? size.width / 2
            : size.width * (i / (normalizedSecondary.length - 1));
        final y = size.height -
            (normalizedSecondary[i].clamp(0.0, 1.0) * (size.height - 12)) -
            6;
        secondaryPoints.add(Offset(x, y));
      }
      if (secondaryPoints.isNotEmpty) {
        canvas.drawPath(
          _buildSmoothPath(secondaryPoints),
          Paint()
            ..color = secondaryLineColor
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2,
        );
      }
    }
    final pointRadius = values.length >= 10
        ? 2.4
        : values.length >= 7
            ? 3.0
            : 4.0;
    final selected = points[selectedIndex.clamp(0, points.length - 1)];
    canvas.drawLine(
      Offset(selected.dx, 0),
      Offset(selected.dx, size.height),
      Paint()
        ..color = lineColor.withValues(alpha: 0.18)
        ..strokeWidth = 1.2,
    );
    for (var i = 0; i < points.length; i++) {
      final point = points[i];
      final isSelected = i == selectedIndex;
      canvas
        ..drawCircle(
          point,
          isSelected ? pointRadius + 2 : pointRadius,
          Paint()
            ..color = isSelected
                ? lineColor.withValues(alpha: 0.2)
                : Colors.transparent,
        )
        ..drawCircle(
          point,
          isSelected ? pointRadius + 0.8 : pointRadius,
          Paint()..color = lineColor,
        );
    }
    canvas.restore();
  }

  Path _buildSmoothPath(List<Offset> points) {
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 1; i < points.length; i++) {
      final previous = points[i - 1];
      final current = points[i];
      final controlX = (previous.dx + current.dx) / 2;
      path.cubicTo(
        controlX,
        previous.dy,
        controlX,
        current.dy,
        current.dx,
        current.dy,
      );
    }
    return path;
  }

  @override
  bool shouldRepaint(covariant _TrendChartPainter oldDelegate) =>
      oldDelegate.values != values ||
      oldDelegate.secondaryValues != secondaryValues ||
      oldDelegate.progress != progress ||
      oldDelegate.lineColor != lineColor ||
      oldDelegate.secondaryLineColor != secondaryLineColor ||
      oldDelegate.fillColor != fillColor ||
      oldDelegate.gridColor != gridColor ||
      oldDelegate.selectedIndex != selectedIndex ||
      oldDelegate.showSecondarySeries != showSecondarySeries;
}

class _TrendLegendChip extends StatelessWidget {
  const _TrendLegendChip({
    required this.color,
    required this.label,
  });

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(99),
              ),
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );
}

class _ExecutionStatsSection extends StatelessWidget {
  const _ExecutionStatsSection({required this.profile});

  final Map<String, dynamic> profile;

  @override
  Widget build(BuildContext context) {
    final totalExecutions = (profile['total_executions'] as num?)?.toInt() ?? 0;
    if (totalExecutions <= 0) {
      return const SizedBox.shrink();
    }

    final successRate = (profile['success_rate'] as num?)?.toDouble() ?? 0.0;
    final timeSaved =
        (profile['estimated_time_saved_minutes'] as num?)?.toDouble() ?? 0.0;
    final byType = profile['by_type'] is Map
        ? Map<String, dynamic>.from(profile['by_type'] as Map)
        : const <String, dynamic>{};

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.smart_toy_rounded, size: 20, color: DS.info),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.reportAiExecutionAssistant,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.reportAiExecutionDesc,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              _ReportStatCard(
                label: context.l10n.reportStatTotalExecutions,
                value: '$totalExecutions',
                unit: context.l10n.reportStatUnitTimes,
                color: DS.info,
              ),
              const SizedBox(width: DS.spacing8),
              _ReportStatCard(
                label: context.l10n.reportStatSuccessRate,
                value: '${(successRate * 100).round()}',
                unit: '%',
                color: DS.semanticSuccess,
              ),
              const SizedBox(width: DS.spacing8),
              _ReportStatCard(
                label: context.l10n.reportStatTimeSaved,
                value: timeSaved >= 60
                    ? (timeSaved / 60).toStringAsFixed(1)
                    : '${timeSaved.round()}',
                unit: timeSaved >= 60 ? context.l10n.reportStatUnitHours : context.l10n.reportStatUnitMinutes,
                color: DS.primaryBase,
              ),
            ],
          ),
          if (byType.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: byType.entries.map((entry) {
                final data = entry.value is Map
                    ? Map<String, dynamic>.from(entry.value as Map)
                    : const <String, dynamic>{};
                final count = (data['total'] as num?)?.toInt() ?? 0;
                final success = (data['success_rate'] as num?)?.toDouble() ?? 0;
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing6,
                  ),
                  decoration: BoxDecoration(
                    color: DS.surfaceSecondary,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    context.l10n.reportStatByTypeFormat(entry.key, count, (success * 100).round()),
                    style: DS.bodySmall.copyWith(color: DS.textSecondary),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReportStatCard extends StatelessWidget {
  const _ReportStatCard({
    required this.label,
    required this.value,
    required this.unit,
    required this.color,
  });

  final String label;
  final String value;
  final String unit;
  final Color color;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Container(
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: DS.bodySmall.copyWith(color: DS.textTertiary),
              ),
              const SizedBox(height: DS.spacing4),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    value,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          color: color,
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(width: 2),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 3),
                    child: Text(
                      unit,
                      style: DS.bodySmall.copyWith(
                        color: color.withValues(alpha: 0.72),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
}

class _AnimatedReportSection extends StatefulWidget {
  const _AnimatedReportSection({
    required this.delay,
    required this.child,
  });

  final int delay;
  final Widget child;

  @override
  State<_AnimatedReportSection> createState() => _AnimatedReportSectionState();
}

class _AnimatedReportSectionState extends State<_AnimatedReportSection> {
  bool _visible = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    final effectiveDelay = widget.delay > 140 ? 140 : widget.delay;
    _timer = Timer(Duration(milliseconds: effectiveDelay), () {
      if (!mounted) {
        return;
      }
      setState(() => _visible = true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedSlide(
        duration: context.reduceMotion ? Duration.zero : DS.durationNormal,
        curve: Curves.easeOutCubic,
        offset: _visible ? Offset.zero : const Offset(0, 0.04),
        child: AnimatedOpacity(
          duration: context.reduceMotion ? Duration.zero : DS.durationNormal,
          opacity: _visible ? 1 : 0,
          child: widget.child,
        ),
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: 152,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: DS.durationSlow,
              curve: Curves.easeOutCubic,
              builder: (context, progress, child) {
                final displayValue = value.contains('%')
                    ? '${(int.parse(value.replaceAll('%', '')) * progress).round()}%'
                    : '${((int.tryParse(value) ?? 0) * progress).round()}';
                return Text(
                  displayValue,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                );
              },
            ),
          ],
        ),
      );
}
