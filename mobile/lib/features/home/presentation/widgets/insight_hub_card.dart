import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class InsightHubCard extends ConsumerStatefulWidget {
  const InsightHubCard({super.key});

  @override
  ConsumerState<InsightHubCard> createState() => _InsightHubCardState();
}

class _InsightHubCardState extends ConsumerState<InsightHubCard> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(simulationProvider.notifier).loadRecommendedSeeds(silent: true),
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
    final latestTheater = systemUpdates.cast<Map<String, dynamic>?>().firstWhere(
          (item) =>
              item?['type']?.toString().startsWith('theater_') ?? false,
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

    final hasAnyData = latestTheater != null ||
        latestReportPayload != null ||
        simulationState.recommendedSeeds.isNotEmpty;
    final hasRefreshError =
        (simulationState.error?.isNotEmpty ?? false) || systemUpdatesAsync.hasError;
    final isShowingStaleData =
        hasRefreshError && hasAnyData;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        borderColor: DS.brandPrimary.withValues(alpha: 0.16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        DS.info.withValues(alpha: 0.9),
                        DS.brandPrimary.withValues(alpha: 0.82),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: DS.info.withValues(alpha: 0.2),
                        blurRadius: 24,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.insights_rounded,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '学习洞察',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.w800,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        hasAnyData
                            ? '把推演、仿真和报告放进同一个洞察中心，自然串起你的学习全貌。'
                            : '输入一个学习目标，AI 会为你推演路径、生成仿真并沉淀学习报告。',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.45,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing16),
            Row(
              children: [
                Expanded(
                  child: _InsightHubAction(
                    icon: Icons.auto_graph_rounded,
                    title: '推演剧场',
                    subtitle: _theaterSubtitle(latestTheater),
                    accent: DS.info,
                    onTap: () => context.push(TheaterRoutes.theater),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: _InsightHubAction(
                    icon: Icons.groups_rounded,
                    title: '学习仿真',
                    subtitle: simulationState.recommendedSeeds.isNotEmpty
                        ? '${simulationState.recommendedSeeds.length} 个推荐场景待探索'
                        : '围绕一个知识点，快速展开辩论或学习小组讨论',
                    accent: DS.accent,
                    onTap: () => context.push(SimulationRoutes.simulation),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: _InsightHubAction(
                    icon: Icons.article_outlined,
                    title: '学习报告',
                    subtitle: _reportSubtitle(latestReportPayload),
                    accent: DS.success,
                    onTap: () => context.push(
                      ReportRoutes.learningReport,
                      extra: latestReportPayload,
                    ),
                  ),
                ),
              ],
            ),
            if (hasRefreshError) ...[
              const SizedBox(height: DS.spacing12),
              _InsightHubStatusBanner(
                isShowingStaleData: isShowingStaleData,
                onRetry: () {
                  ref.invalidate(systemUpdatesProvider);
                  unawaited(
                    ref.read(simulationProvider.notifier).loadRecommendedSeeds(),
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _theaterSubtitle(Map<String, dynamic>? latestTheater) {
    if (latestTheater == null) {
      return '输入一个目标，查看多条学习路径';
    }
    final metadata = Map<String, dynamic>.from(
      latestTheater['metadata'] as Map? ?? const {},
    );
    final title = metadata['title']?.toString();
    if (title != null && title.isNotEmpty) {
      return '上次推演：$title';
    }
    return latestTheater['description']?.toString() ?? '继续上次推演';
  }

  String _reportSubtitle(LearningReport? report) {
    if (report == null || report.mastery.isEmpty) {
      return '完成一轮学习后，自动查看分析报告';
    }
    final avg = report.mastery
            .map((item) => item.masteryScore)
            .fold<double>(0, (sum, value) => sum + value) /
        report.mastery.length;
    return '掌握度 ${avg.round()}% · ${report.mastery.length} 个知识点已分析';
  }
}

class _InsightHubAction extends StatelessWidget {
  const _InsightHubAction({
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Ink(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: accent.withValues(alpha: 0.16)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 18, color: accent),
            ),
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
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InsightHubStatusBanner extends StatelessWidget {
  const _InsightHubStatusBanner({
    required this.isShowingStaleData,
    required this.onRetry,
  });

  final bool isShowingStaleData;
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
              isShowingStaleData
                  ? '洞察推荐暂时没有刷新成功，当前先显示已有内容。'
                  : '洞察中心暂时没有拿到最新数据，你可以立即重试。',
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
