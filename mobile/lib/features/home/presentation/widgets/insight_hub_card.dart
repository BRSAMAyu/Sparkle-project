import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/insights/insights_routes.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/presentation/providers/simulation_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

/// U-07 导航减负：洞察枢纽卡收敛为「学习报告」单一 CONTEXTUAL 动作 +
/// 洞察总览入口。simulation/theater 属 LABS（hidden by default），不再
/// 在 CORE 首页面挂快速入口；对应推荐种子加载与 LABS 通知聚合一并摘除。
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
  Widget build(BuildContext context) {
    final systemUpdatesAsync = ref.watch(systemUpdatesProvider);
    final systemUpdates = systemUpdatesAsync.maybeWhen(
      data: (items) => items,
      orElse: () => const <Map<String, dynamic>>[],
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
    // 洞察刷新失败感知双源：systemUpdates 流与 insights/simulation 源任一
    // 出错都要诚实亮横幅（U-07 收敛后曾丢掉 simulation 源的失败感知）。
    final hasRefreshError = systemUpdatesAsync.hasError ||
        ref.watch(simulationProvider.select((state) => state.error != null));

    if (widget.compact) {
      return _CompactInsightHubCard(
        latestReportPayload: latestReportPayload,
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
              context.l10n.insightHubTitle,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              // 报告上下文只在「学习报告」入口副题出现一次；hero 行保持
              // 常驻摘要，不与入口副题重复渲染同一段掌握度文案。
              context.l10n.insightHubFallbackSummary,
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
                  icon: Icons.article_outlined,
                  title: context.l10n.insightHubReport,
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
                label: Text(context.l10n.insightHubEnterOverview),
              ),
            ),
            if (hasRefreshError) ...[
              const SizedBox(height: DS.spacing12),
              _InsightHubStatusBanner(
                onRetry: () {
                  ref.invalidate(systemUpdatesProvider);
                  ref.invalidate(simulationProvider);
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _openOverview(BuildContext context, {String? initialPanel}) {
    unawaited(
      context.push(
        InsightsRoutes.overviewLocation(initialPanel: initialPanel),
      ),
    );
  }

  void _openReport(BuildContext context, LearningReport? report) {
    unawaited(context.push(ReportRoutes.learningReport, extra: report));
  }
}

class _CompactInsightHubCard extends ConsumerWidget {
  const _CompactInsightHubCard({
    required this.latestReportPayload,
    required this.dense,
    required this.hasRefreshError,
  });

  final LearningReport? latestReportPayload;
  final bool dense;
  final bool hasRefreshError;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contentPadding = dense ? DS.spacing10 : DS.spacing12;
    // 与标准卡同口径：compact hero 保持常驻摘要，报告上下文只在
    // 「学习报告」动作 tile 副题渲染一次。
    final summary = context.l10n.insightHubCompactFallback;

    return ClipRRect(
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context).copyWith(
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
                          child: Icon(
                            Icons.insights_rounded,
                            color: DS.textOnPrimary,
                            size: 18,
                          ),
                        ),
                        const SizedBox(width: DS.spacing10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                context.l10n.insightHubTitle,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: context.typo.labelLarge
                                    .copyWith(
                                  fontWeight: DS.fontWeightBold,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                summary,
                                maxLines: dense ? 1 : 2,
                                overflow: TextOverflow.ellipsis,
                                style: context.typo.labelSmall
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
                        context.l10n.insightHubEnterOverview,
                        style: context.typo.labelSmall.copyWith(
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
              child: LayoutBuilder(
                builder: (context, constraints) {
                  // U-07：LABS 快捷动作（simulation/theater）摘除后，
                  // 紧凑形态只剩报告动作——单卡满宽，不再三等分。
                  final action = _CompactInsightAction(
                    title: context.l10n.insightHubCompactReport,
                    subtitle: _reportSubtitle(latestReportPayload),
                    icon: Icons.article_outlined,
                    accent: DS.success,
                    onTap: () => unawaited(
                      context.push(
                        ReportRoutes.learningReport,
                        extra: latestReportPayload,
                      ),
                    ),
                  );
                  final useHorizontalStrip =
                      dense || constraints.maxWidth < 420;
                  if (useHorizontalStrip) {
                    final itemWidth =
                        (constraints.maxWidth * 0.48).clamp(108.0, 152.0);
                    return ListView(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      children: [
                        SizedBox(
                          width: itemWidth,
                          child: action,
                        ),
                      ],
                    );
                  }
                  return action;
                },
              ),
            ),
            if (hasRefreshError) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.insightHubRefreshWarning,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.typo.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
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
                        fontWeight: DS.fontWeightBold,
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
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 320),
            child: Ink(
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
                          fontWeight: DS.fontWeightBold,
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
              context.l10n.insightHubRefreshFailed,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.4,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ),
          const SizedBox(width: 10),
          SparkleButton(
            label: context.l10n.insightHubRetry,
            variant: ButtonVariant.text,
            size: ButtonSize.small,
            minWidth: 64,
            minHeight: 40,
            onPressed: onRetry,
          ),
        ],
      ),
    );
  }
}

String _reportSubtitle(LearningReport? report) {
  if (report == null || report.mastery.isEmpty) {
    return S.insightHubNoRecentReport;
  }
  final avg = report.mastery
          .map((item) => item.masteryScore)
          .fold<double>(0, (sum, value) => sum + value) /
      report.mastery.length;
  return S.insightHubMasteryPercent(avg.round());
}
