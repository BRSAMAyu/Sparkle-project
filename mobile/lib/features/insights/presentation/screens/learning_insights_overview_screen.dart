import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class LearningInsightsOverviewScreen extends ConsumerWidget {
  const LearningInsightsOverviewScreen({
    super.key,
    this.initialPanel,
  });

  final String? initialPanel;

  static const String panelSimulation = 'simulation';
  static const String panelTheater = 'theater';
  static const String panelReport = 'report';
  static const String panelWeeklyNarrative = 'weeklyNarrative';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
    final topSeed = simulationState.recommendedSeeds.isNotEmpty
        ? simulationState.recommendedSeeds.first
        : null;
    final weeklyNarrative =
        ref.watch(weeklyGrowthNarrativeProvider).valueOrNull;
    final showOverviewEmptyState = (weeklyNarrative?.hasData == false) &&
        latestTheater == null &&
        latestSimulation == null &&
        latestReportPayload == null &&
        topSeed == null;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(context.l10n.insOverviewTitle),
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing24,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showOverviewEmptyState)
                EmptyState(
                  icon: Icons.insights_outlined,
                  title: context.l10n.insOverviewEmpty,
                  description: context.l10n.insOverviewEmptyDesc,
                  actionText: I18nService.instance.isChinese ? '去创建学习任务' : 'Create Learning Task',
                  onAction: () => context.push(TaskRoutes.taskCreate),
                )
              else
                WeeklyGrowthNarrativeCard(
                  initialExpanded: initialPanel == panelWeeklyNarrative,
                ),
              const SizedBox(height: DS.spacing16),
              _OverviewHero(activePanel: initialPanel),
              const SizedBox(height: DS.spacing16),
              _InsightModuleCard(
                title: context.l10n.insSimLabel,
                subtitle: _simulationTitle(
                  context,
                  latestSimulation,
                  fallbackSeed: topSeed,
                ),
                status: latestSimulation != null
                    ? _simulationStatus(context, latestSimulation)
                    : simulationState.recommendedSeeds.isNotEmpty
                        ? context.l10n.lioRecommendedSeeds(simulationState.recommendedSeeds.length)
                        : context.l10n.lioStartNewSim,
                accent: DS.accent,
                icon: Icons.groups_rounded,
                highlighted: initialPanel == panelSimulation,
                buttonLabel: latestSimulation != null
                    ? (I18nService.instance.isChinese ? '继续查看' : 'Continue')
                    : topSeed != null
                        ? (I18nService.instance.isChinese ? '从推荐开始' : 'Start from Recommended')
                        : (I18nService.instance.isChinese ? '开始模拟' : 'Start Simulation'),
                onPressed: () => context.push(
                  latestSimulation != null
                      ? _simulationLocation(context, latestSimulation)
                      : topSeed != null
                          ? '${SimulationRoutes.simulation}?topic=${Uri.encodeComponent(topSeed.topic)}&scenario_key=${Uri.encodeComponent(topSeed.suggestedScenario)}'
                          : SimulationRoutes.simulation,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: context.l10n.insTheaterLabel,
                subtitle: _theaterTitle(context, latestTheater),
                status: _theaterStatus(context, latestTheater),
                accent: DS.info,
                icon: Icons.auto_graph_rounded,
                highlighted: initialPanel == panelTheater,
                buttonLabel: context.l10n.insOpenSim,
                onPressed: () => context.push(
                  _theaterLocation(context, latestTheater),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: context.l10n.insReportLabel,
                subtitle: latestReportPayload?.mastery.isNotEmpty ?? false
                    ? context.l10n.lioRecentAnalysis(latestReportPayload!.mastery.length)
                    : context.l10n.lioBuildConclusion,
                status: _reportStatus(context, latestReportPayload),
                accent: DS.success,
                icon: Icons.article_outlined,
                highlighted: initialPanel == panelReport,
                buttonLabel: context.l10n.insViewReport,
                onPressed: () => context.push(
                  ReportRoutes.learningReport,
                  extra: latestReportPayload,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                padding: const EdgeInsets.all(DS.spacing16),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 360;
                    if (compact) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.swipe_rounded,
                                color: DS.textSecondary,
                                size: 18,
                              ),
                              const SizedBox(width: DS.spacing10),
                              Expanded(
                                child: Text(
                                  I18nService.instance.isChinese ? '首页已经把学习洞察放进可定制卡牌区。默认先看日历，左滑就是洞察，右滑是工具快捷。' : 'Learning Insights is in the customizable card area on the home screen. Default: calendar, swipe left for insights, right for tools.',
                                  style: Theme.of(context)
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
                          const SizedBox(height: DS.spacing10),
                          TextButton(
                            onPressed: () => context.go('/home'),
                            child: Text(context.l10n.insBackToCockpit),
                          ),
                        ],
                      );
                    }
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.swipe_rounded,
                          color: DS.textSecondary,
                          size: 18,
                        ),
                        const SizedBox(width: DS.spacing10),
                        Expanded(
                          child: Text(
                            I18nService.instance.isChinese ? '首页已经把学习洞察放进可定制卡牌区。默认先看日历，左滑就是洞察，右滑是工具快捷。' : 'Learning Insights is in the customizable card area on the home screen. Default: calendar, swipe left for insights, right for tools.',
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.45,
                                    ),
                          ),
                        ),
                        const SizedBox(width: DS.spacing8),
                        TextButton(
                          onPressed: () => context.go('/home'),
                          child: Text(context.l10n.insBackToCockpit),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _theaterTitle(BuildContext context, Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return I18nService.instance.isChinese ? '把一个目标拆成多条学习路径' : 'Break a goal into multiple learning paths';
    }
    final metadata = Map<String, dynamic>.from(
      latestTheater['metadata'] as Map? ?? const {},
    );
    return metadata['title']?.toString().trim().isNotEmpty ?? false
        ? metadata['title']!.toString()
        : latestTheater['description']?.toString() ?? context.l10n.insContinueSim;
  }

  String _simulationTitle(
    BuildContext context,
    Map<String, dynamic>? latestSimulation, {
    required SimulationSeedModel? fallbackSeed,
  }) {
    if (latestSimulation == null) {
      return fallbackSeed?.topic ?? (I18nService.instance.isChinese ? '把一个知识点拉进多角色现场讨论' : 'Bring a knowledge point into multi-role live discussion');
    }
    final metadata = Map<String, dynamic>.from(
      latestSimulation['metadata'] as Map? ?? const {},
    );
    final sessionPayload = metadata['session_payload'];
    if (sessionPayload is Map) {
      final topic = sessionPayload['topic']?.toString().trim();
      if (topic != null && topic.isNotEmpty) {
        return topic;
      }
    }
    return latestSimulation['title']?.toString() ?? context.l10n.insContinueLearnSim;
  }

  String _simulationStatus(BuildContext context, Map<String, dynamic>? latestSimulation) {
    if (latestSimulation == null) {
      return context.l10n.lioNoSimYet;
    }
    return context.l10n.lioRecentUpdate(latestSimulation['description']?.toString() ?? context.l10n.insHasContinue);
  }

  String _theaterStatus(BuildContext context, Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return context.l10n.lioNoTheaterYet;
    }
    return context.l10n.lioRecentUpdate(latestTheater['description']?.toString() ?? context.l10n.insHasContinue);
  }

  String _reportStatus(BuildContext context, LearningReport? report) {
    if (report == null || report.mastery.isEmpty) {
      return context.l10n.lioNoReportYet;
    }
    final avg = report.mastery
            .map((item) => item.masteryScore)
            .fold<double>(0, (sum, value) => sum + value) /
        report.mastery.length;
    return context.l10n.lioMastery(avg.round().toString());
  }

  String _simulationLocation(BuildContext context, Map<String, dynamic>? latestSimulation) {
    if (latestSimulation == null) {
      return SimulationRoutes.simulation;
    }
    final metadata = Map<String, dynamic>.from(
      latestSimulation['metadata'] as Map? ?? const {},
    );
    final deepLink = metadata['deep_link']?.toString().trim();
    if (deepLink != null && deepLink.startsWith(SimulationRoutes.simulation)) {
      return deepLink;
    }
    return SimulationRoutes.simulation;
  }

  String _theaterLocation(BuildContext context, Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return TheaterRoutes.theater;
    }
    final metadata = Map<String, dynamic>.from(
      latestTheater['metadata'] as Map? ?? const {},
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
}

class _OverviewHero extends StatelessWidget {
  const _OverviewHero({required this.activePanel});

  final String? activePanel;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final focusLabel = switch (activePanel) {
      LearningInsightsOverviewScreen.panelSimulation => zh ? '已聚焦：学习仿真' : 'Focused: Learning Simulation',
      LearningInsightsOverviewScreen.panelTheater => zh ? '已聚焦：推演剧场' : 'Focused: Scenario Theater',
      LearningInsightsOverviewScreen.panelReport => zh ? '已聚焦：学习报告' : 'Focused: Learning Report',
      _ => zh ? '仿真、推演、报告统一收在这里' : 'Simulation, theater & reports in one place',
    };

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: DS.brandPrimary.withValues(alpha: 0.14),
      padding: const EdgeInsets.all(DS.spacing18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing10,
              vertical: DS.spacing6,
            ),
            decoration: BoxDecoration(
              color: DS.info.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              focusLabel,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.info,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            I18nService.instance.isChinese ? '把学习里的”看见问题、模拟讨论、沉淀结论”放到同一条动线里。' : 'Connect “spot problems, simulate discussions, draw conclusions” into one flow.',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  height: 1.2,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            I18nService.instance.isChinese ? '这里只保留你下一步真正需要的入口，不再堆叠多余说明。' : 'Only the entries you actually need next — no clutter.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
        ],
      ),
    );
  }
}

class _InsightModuleCard extends StatelessWidget {
  const _InsightModuleCard({
    required this.title,
    required this.subtitle,
    required this.status,
    required this.accent,
    required this.icon,
    required this.highlighted,
    required this.buttonLabel,
    required this.onPressed,
  });

  final String title;
  final String subtitle;
  final String status;
  final Color accent;
  final IconData icon;
  final bool highlighted;
  final String buttonLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final background = highlighted
        ? Color.alphaBlend(
            accent.withValues(alpha: 0.05),
            DS.surfacePanel,
          )
        : DS.surfacePanel;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: accent.withValues(alpha: highlighted ? 0.26 : 0.12),
      padding: EdgeInsets.zero,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(DS.radius20),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: accent, size: 20),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                if (highlighted)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing4,
                    ),
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      I18nService.instance.isChinese ? '推荐先看' : 'Recommended',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: accent,
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                    height: 1.35,
                  ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              status,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.45,
                  ),
            ),
            const SizedBox(height: DS.spacing16),
            FilledButton.tonalIcon(
              onPressed: onPressed,
              icon: Icon(icon),
              label: Text(buttonLabel),
            ),
          ],
        ),
      ),
    );
  }
}
