import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class LearningInsightsOverviewScreen extends ConsumerWidget {
  const LearningInsightsOverviewScreen({
    super.key,
    this.initialPanel,
  });

  final String? initialPanel;

  static const String panelSimulation = 'simulation';
  static const String panelTheater = 'theater';
  static const String panelReport = 'report';

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
        title: const Text('学习洞察'),
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
              _OverviewHero(activePanel: initialPanel),
              const SizedBox(height: DS.spacing16),
              _InsightModuleCard(
                title: '学习仿真',
                subtitle: _simulationTitle(
                  latestSimulation,
                  fallbackSeed: topSeed,
                ),
                status: latestSimulation != null
                    ? _simulationStatus(latestSimulation)
                    : simulationState.recommendedSeeds.isNotEmpty
                        ? '${simulationState.recommendedSeeds.length} 个推荐场景'
                        : '可立即开始一轮新模拟',
                accent: DS.accent,
                icon: Icons.groups_rounded,
                highlighted: initialPanel == panelSimulation,
                buttonLabel: latestSimulation != null
                    ? '继续查看'
                    : topSeed != null
                        ? '从推荐开始'
                        : '开始模拟',
                onPressed: () => context.push(
                  latestSimulation != null
                      ? _simulationLocation(latestSimulation)
                      : topSeed != null
                          ? '${SimulationRoutes.simulation}?topic=${Uri.encodeComponent(topSeed.topic)}&scenario_key=${Uri.encodeComponent(topSeed.suggestedScenario)}'
                          : SimulationRoutes.simulation,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: '推演剧场',
                subtitle: _theaterTitle(latestTheater),
                status: _theaterStatus(latestTheater),
                accent: DS.info,
                icon: Icons.auto_graph_rounded,
                highlighted: initialPanel == panelTheater,
                buttonLabel: '打开推演',
                onPressed: () => context.push(
                  _theaterLocation(latestTheater),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: '学习报告',
                subtitle: latestReportPayload?.mastery.isNotEmpty ?? false
                    ? '最近一次共分析 ${latestReportPayload!.mastery.length} 个知识点'
                    : '沉淀一轮学习后的关键结论',
                status: _reportStatus(latestReportPayload),
                accent: DS.success,
                icon: Icons.article_outlined,
                highlighted: initialPanel == panelReport,
                buttonLabel: '查看报告',
                onPressed: () => context.push(
                  ReportRoutes.learningReport,
                  extra: latestReportPayload,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                padding: const EdgeInsets.all(DS.spacing16),
                child: Row(
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
                        '首页已经把学习洞察放进可定制卡牌区。默认先看日历，左滑就是洞察，右滑是工具快捷。',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    TextButton(
                      onPressed: () => context.go('/home'),
                      child: const Text('回到驾驶舱'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _theaterTitle(Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return '把一个目标拆成多条学习路径';
    }
    final metadata = Map<String, dynamic>.from(
      latestTheater['metadata'] as Map? ?? const {},
    );
    return metadata['title']?.toString().trim().isNotEmpty ?? false
        ? metadata['title']!.toString()
        : latestTheater['description']?.toString() ?? '继续上次推演';
  }

  String _simulationTitle(
    Map<String, dynamic>? latestSimulation, {
    required SimulationSeedModel? fallbackSeed,
  }) {
    if (latestSimulation == null) {
      return fallbackSeed?.topic ?? '把一个知识点拉进多角色现场讨论';
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
    return latestSimulation['title']?.toString() ?? '继续上次学习仿真';
  }

  String _simulationStatus(Map<String, dynamic>? latestSimulation) {
    if (latestSimulation == null) {
      return '暂未生成最近仿真';
    }
    return '最近更新 · ${latestSimulation['description']?.toString() ?? '已有可继续内容'}';
  }

  String _theaterStatus(Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return '暂未生成最近推演';
    }
    return '最近更新 · ${latestTheater['description']?.toString() ?? '已有可继续内容'}';
  }

  String _reportStatus(LearningReport? report) {
    if (report == null || report.mastery.isEmpty) {
      return '暂未生成最近报告';
    }
    final avg = report.mastery
            .map((item) => item.masteryScore)
            .fold<double>(0, (sum, value) => sum + value) /
        report.mastery.length;
    return '掌握度 ${avg.round()}%';
  }

  String _simulationLocation(Map<String, dynamic>? latestSimulation) {
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

  String _theaterLocation(Map<String, dynamic>? latestTheater) {
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
    final focusLabel = switch (activePanel) {
      LearningInsightsOverviewScreen.panelSimulation => '已聚焦：学习仿真',
      LearningInsightsOverviewScreen.panelTheater => '已聚焦：推演剧场',
      LearningInsightsOverviewScreen.panelReport => '已聚焦：学习报告',
      _ => '仿真、推演、报告统一收在这里',
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
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '把学习里的“看见问题、模拟讨论、沉淀结论”放到同一条动线里。',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  height: 1.2,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            '这里只保留你下一步真正需要的入口，不再堆叠多余说明。',
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
                      '推荐先看',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: accent,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    fontWeight: FontWeight.w700,
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
