import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/insights/insights_routes.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class InsightHubCard extends ConsumerStatefulWidget {
  const InsightHubCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  ConsumerState<InsightHubCard> createState() => _InsightHubCardState();
}

class _InsightHubCardState extends ConsumerState<InsightHubCard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref
            .read(simulationProvider.notifier)
            .loadRecommendedSeeds(silent: true),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final simulationState = ref.watch(simulationProvider);
    final systemUpdatesAsync = ref.watch(systemUpdatesProvider);
    final systemUpdates = systemUpdatesAsync.maybeWhen(
      data: (items) => items,
      orElse: () => const <Map<String, dynamic>>[],
    );
    final latestTheater =
        systemUpdates.cast<Map<String, dynamic>?>().firstWhere(
              (item) =>
                  item?['type']?.toString().startsWith('theater_') ?? false,
              orElse: () => null,
            );
    final latestSimulation =
        systemUpdates.cast<Map<String, dynamic>?>().firstWhere(
              (item) => item?['type']?.toString() == 'simulation_session_ready',
              orElse: () => null,
            );
    final latestReport = systemUpdates.cast<Map<String, dynamic>?>().firstWhere(
          (item) => item?['type']?.toString() == 'learning_report_ready',
          orElse: () => null,
        );
    final latestReportPayload = latestReport?['metadata'] is Map
        ? LearningReport.fromJson(
            Map<String, dynamic>.from(
              (latestReport!['metadata'] as Map)['report_payload'] as Map? ??
                  const {},
            ),
          )
        : null;
    final hasRefreshError = (simulationState.error?.isNotEmpty ?? false) ||
        systemUpdatesAsync.hasError;

    if (widget.compact) {
      return _CompactInsightHubCard(
        latestTheater: latestTheater,
        latestSimulation: latestSimulation,
        latestReportPayload: latestReportPayload,
        simulationState: simulationState,
        dense: widget.dense,
        hasRefreshError: hasRefreshError,
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.brandPrimary.withValues(alpha: 0.16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '学习洞察',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              _heroSummary(
                latestTheater,
                latestReportPayload,
                simulationState,
                latestSimulation,
              ),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
            ),
            const SizedBox(height: DS.spacing16),
            Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: [
                _InsightHubQuickAction(
                  icon: Icons.groups_rounded,
                  title: '学习仿真',
                  subtitle: _simulationSubtitle(
                    simulationState,
                    latestSimulation: latestSimulation,
                  ),
                  accent: DS.accent,
                  onTap: () => _openSimulation(
                    context,
                    simulationState,
                    latestSimulation: latestSimulation,
                  ),
                ),
                _InsightHubQuickAction(
                  icon: Icons.auto_graph_rounded,
                  title: '推演剧场',
                  subtitle: _theaterSubtitle(latestTheater),
                  accent: DS.info,
                  onTap: () => _openTheater(context, latestTheater),
                ),
                _InsightHubQuickAction(
                  icon: Icons.article_outlined,
                  title: '学习报告',
                  subtitle: _reportSubtitle(latestReportPayload),
                  accent: DS.success,
                  onTap: () => _openReport(context, latestReportPayload),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Align(
              alignment: Alignment.centerLeft,
              child: FilledButton.tonalIcon(
                onPressed: () => _openOverview(context),
                icon: const Icon(Icons.wb_iridescent_rounded),
                label: const Text('进入洞察总览'),
              ),
            ),
            if (hasRefreshError) ...[
              const SizedBox(height: DS.spacing12),
              _InsightHubStatusBanner(
                onRetry: () {
                  ref.invalidate(systemUpdatesProvider);
                  unawaited(
                    ref
                        .read(simulationProvider.notifier)
                        .loadRecommendedSeeds(),
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _heroSummary(
    Map<String, dynamic>? latestTheater,
    LearningReport? report,
    SimulationState simulationState,
    Map<String, dynamic>? latestSimulation,
  ) {
    if (simulationState.recommendedSeeds.isNotEmpty) {
      return '现在有 ${simulationState.recommendedSeeds.length} 个推荐场景可以直接开始模拟。';
    }
    if (latestSimulation != null) {
      return _simulationSubtitle(
        simulationState,
        latestSimulation: latestSimulation,
      );
    }
    if (report != null && report.mastery.isNotEmpty) {
      return _reportSubtitle(report);
    }
    if (latestTheater != null) {
      return _theaterSubtitle(latestTheater);
    }
    return '把推演、仿真和报告收进一条更轻量的学习动线。';
  }

  void _openOverview(BuildContext context, {String? initialPanel}) {
    unawaited(
      context.push(
        InsightsRoutes.overviewLocation(initialPanel: initialPanel),
      ),
    );
  }

  void _openSimulation(
    BuildContext context,
    SimulationState simulationState, {
    Map<String, dynamic>? latestSimulation,
  }) {
    final metadata = Map<String, dynamic>.from(
      latestSimulation?['metadata'] as Map? ?? const {},
    );
    final deepLink = metadata['deep_link']?.toString().trim();
    if (deepLink != null && deepLink.startsWith(SimulationRoutes.simulation)) {
      unawaited(context.push(deepLink));
      return;
    }
    final seed = simulationState.recommendedSeeds.isNotEmpty
        ? simulationState.recommendedSeeds.first
        : null;
    final location = seed == null
        ? SimulationRoutes.simulation
        : '${SimulationRoutes.simulation}?topic=${Uri.encodeComponent(seed.topic)}&scenario_key=${Uri.encodeComponent(seed.suggestedScenario)}';
    unawaited(context.push(location));
  }

  void _openTheater(BuildContext context, Map<String, dynamic>? latestTheater) {
    unawaited(context.push(_resolveTheaterLocation(latestTheater)));
  }

  void _openReport(BuildContext context, LearningReport? report) {
    unawaited(context.push(ReportRoutes.learningReport, extra: report));
  }
}

class _CompactInsightHubCard extends ConsumerWidget {
  const _CompactInsightHubCard({
    required this.latestTheater,
    required this.latestSimulation,
    required this.latestReportPayload,
    required this.simulationState,
    required this.dense,
    required this.hasRefreshError,
  });

  final Map<String, dynamic>? latestTheater;
  final Map<String, dynamic>? latestSimulation;
  final LearningReport? latestReportPayload;
  final SimulationState simulationState;
  final bool dense;
  final bool hasRefreshError;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contentPadding = dense ? DS.spacing10 : DS.spacing12;
    final summary = _heroSummary(
      latestTheater,
      latestReportPayload,
      simulationState,
      latestSimulation,
    );

    return ClipRRect(
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic.copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              DS.info.withValues(alpha: 0.06),
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.info.withValues(alpha: 0.22),
          borderWidth: 1,
        ),
        borderRadius: DS.borderRadius20,
        padding: EdgeInsets.all(contentPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              onTap: () => context.push(InsightsRoutes.overviewLocation()),
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.all(DS.spacing4),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: dense ? 34 : 38,
                          height: dense ? 34 : 38,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [
                                DS.info.withValues(alpha: 0.9),
                                DS.brandPrimary.withValues(alpha: 0.82),
                              ],
                            ),
                            borderRadius: BorderRadius.circular(12),
                            boxShadow: [
                              BoxShadow(
                                color: DS.info.withValues(alpha: 0.18),
                                blurRadius: 22,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.insights_rounded,
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                        const SizedBox(width: DS.spacing10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '学习洞察',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: context.sparkleTypography.labelLarge
                                    .copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                summary,
                                maxLines: dense ? 1 : 2,
                                overflow: TextOverflow.ellipsis,
                                style: context.sparkleTypography.labelSmall
                                    .copyWith(
                                  color: DS.textSecondary,
                                  height: 1.3,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Icon(
                          Icons.chevron_right_rounded,
                          color: DS.textTertiary,
                          size: 20,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing6,
                      ),
                      decoration: BoxDecoration(
                        color: DS.info.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        '进入洞察总览',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.info,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: dense ? DS.spacing8 : DS.spacing10),
            Expanded(
              child: Row(
                children: [
                  Expanded(
                    child: _CompactInsightAction(
                      title: '仿真',
                      subtitle: _simulationSubtitle(
                        simulationState,
                        latestSimulation: latestSimulation,
                      ),
                      icon: Icons.groups_rounded,
                      accent: DS.accent,
                      onTap: () {
                        final metadata = Map<String, dynamic>.from(
                          latestSimulation?['metadata'] as Map? ?? const {},
                        );
                        final deepLink =
                            metadata['deep_link']?.toString().trim();
                        final seed = simulationState.recommendedSeeds.isNotEmpty
                            ? simulationState.recommendedSeeds.first
                            : null;
                        final location = deepLink != null &&
                                deepLink.startsWith(SimulationRoutes.simulation)
                            ? deepLink
                            : seed == null
                                ? SimulationRoutes.simulation
                                : '${SimulationRoutes.simulation}?topic=${Uri.encodeComponent(seed.topic)}&scenario_key=${Uri.encodeComponent(seed.suggestedScenario)}';
                        unawaited(context.push(location));
                      },
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: _CompactInsightAction(
                      title: '推演',
                      subtitle: _theaterSubtitle(latestTheater),
                      icon: Icons.auto_graph_rounded,
                      accent: DS.info,
                      onTap: () {
                        final metadata = Map<String, dynamic>.from(
                          latestTheater?['metadata'] as Map? ?? const {},
                        );
                        final title = metadata['title']?.toString();
                        final location = title == null || title.isEmpty
                            ? TheaterRoutes.theater
                            : '${TheaterRoutes.theater}?topic=${Uri.encodeComponent(title)}';
                        unawaited(context.push(location));
                      },
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: _CompactInsightAction(
                      title: '报告',
                      subtitle: _reportSubtitle(latestReportPayload),
                      icon: Icons.article_outlined,
                      accent: DS.success,
                      onTap: () => unawaited(
                        context.push(
                          ReportRoutes.learningReport,
                          extra: latestReportPayload,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (hasRefreshError) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                '部分洞察数据尚未刷新，点击后会继续显示已有内容。',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _heroSummary(
    Map<String, dynamic>? latestTheater,
    LearningReport? report,
    SimulationState simulationState,
    Map<String, dynamic>? latestSimulation,
  ) {
    if (simulationState.recommendedSeeds.isNotEmpty) {
      return '${simulationState.recommendedSeeds.length} 个推荐场景待探索';
    }
    if (latestSimulation != null) {
      return _simulationSubtitle(
        simulationState,
        latestSimulation: latestSimulation,
      );
    }
    if (report != null && report.mastery.isNotEmpty) {
      return _reportSubtitle(report);
    }
    if (latestTheater != null) {
      return _theaterSubtitle(latestTheater);
    }
    return '仿真、推演和报告现在收在同一张卡里';
  }
}

class _CompactInsightAction extends StatelessWidget {
  const _CompactInsightAction({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Ink(
            padding: const EdgeInsets.all(DS.spacing10),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: accent.withValues(alpha: 0.12)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 16, color: accent),
                const SizedBox(height: DS.spacing8),
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: DS.spacing4),
                Expanded(
                  child: Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.3,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _InsightHubQuickAction extends StatelessWidget {
  const _InsightHubQuickAction({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Ink(
            width: 220,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: accent.withValues(alpha: 0.14)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 18, color: accent),
                const SizedBox(height: 10),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _InsightHubStatusBanner extends StatelessWidget {
  const _InsightHubStatusBanner({
    required this.onRetry,
  });

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: DS.warning.withValues(alpha: 0.22),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.wifi_tethering_error_rounded,
            size: 18,
            color: DS.warning,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '洞察内容暂时没有刷新成功，当前先显示已有内容。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          const SizedBox(width: 10),
          TextButton(
            onPressed: onRetry,
            child: const Text('重试'),
          ),
        ],
      ),
    );
  }
}

String _theaterSubtitle(Map<String, dynamic>? latestTheater) {
  if (latestTheater == null) {
    return '最近暂无推演';
  }
  final metadata = Map<String, dynamic>.from(
    latestTheater['metadata'] as Map? ?? const {},
  );
  final title = metadata['title']?.toString();
  if (title != null && title.isNotEmpty) {
    return title;
  }
  return latestTheater['description']?.toString() ?? '继续上次推演';
}

String _resolveTheaterLocation(Map<String, dynamic>? latestTheater) {
  final metadata = Map<String, dynamic>.from(
    latestTheater?['metadata'] as Map? ?? const {},
  );
  final deepLink = metadata['deep_link']?.toString().trim();
  if (deepLink != null && deepLink.startsWith(TheaterRoutes.theater)) {
    return deepLink;
  }
  final topicCandidate = metadata['topic']?.toString().trim();
  final targetNameCandidate = metadata['target_name']?.toString().trim();
  final titleCandidate = metadata['title']?.toString().trim();
  final topic = (topicCandidate?.isNotEmpty ?? false)
      ? topicCandidate
      : (targetNameCandidate?.isNotEmpty ?? false)
          ? targetNameCandidate
          : titleCandidate;
  if (topic == null || topic.isEmpty) {
    return TheaterRoutes.theater;
  }
  final query = <String, String>{'topic': topic};
  final targetNodeId = metadata['target_node_id']?.toString().trim();
  if (targetNodeId != null && targetNodeId.isNotEmpty) {
    query['target_node_id'] = targetNodeId;
  }
  return Uri(path: TheaterRoutes.theater, queryParameters: query).toString();
}

String _simulationSubtitle(
  SimulationState simulationState, {
  Map<String, dynamic>? latestSimulation,
}) {
  if (latestSimulation != null) {
    final metadata = Map<String, dynamic>.from(
      latestSimulation['metadata'] as Map? ?? const {},
    );
    final sessionPayload = metadata['session_payload'];
    if (sessionPayload is Map) {
      final topic = sessionPayload['topic']?.toString().trim();
      if (topic != null && topic.isNotEmpty) {
        return '继续 $topic';
      }
    }
    return latestSimulation['description']?.toString() ?? '继续上次仿真';
  }
  if (simulationState.recommendedSeeds.isNotEmpty) {
    return '${simulationState.recommendedSeeds.length} 个推荐场景';
  }
  if (simulationState.session != null) {
    return '继续 ${simulationState.session!.topic}';
  }
  return '开始一轮新模拟';
}

String _reportSubtitle(LearningReport? report) {
  if (report == null || report.mastery.isEmpty) {
    return '最近暂无报告';
  }
  final avg = report.mastery
          .map((item) => item.masteryScore)
          .fold<double>(0, (sum, value) => sum + value) /
      report.mastery.length;
  return '掌握度 ${avg.round()}%';
}
