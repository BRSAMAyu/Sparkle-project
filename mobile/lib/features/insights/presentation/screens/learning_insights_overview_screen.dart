import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/error_book/presentation/widgets/remediable_patterns_card.dart';
import 'package:sparkle/features/insights/insights_routes.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

/// U-07 导航减负：洞察总览收敛为 CORE/CONTEXTUAL 洞察模块。simulation /
/// theater 模块卡摘除（LABS hidden by default），对应 provider 监听、
/// 空态判定与 deep-link 定位 helper 一并移除。
class LearningInsightsOverviewScreen extends ConsumerWidget {
  const LearningInsightsOverviewScreen({
    super.key,
    this.initialPanel,
  });

  final String? initialPanel;

  static const String panelReport = 'report';
  static const String panelWeeklyNarrative = 'weeklyNarrative';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
    final weeklyNarrative =
        ref.watch(weeklyGrowthNarrativeProvider).valueOrNull;
    final colors = Theme.of(context).colorScheme;
    final showOverviewEmptyState = (weeklyNarrative?.hasData == false) &&
        latestReportPayload == null;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          semanticLabel: context.l10n.back,
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
                  actionText: context.l10n.taskCreateAction,
                  onAction: () => context.push(TaskRoutes.taskCreate),
                )
              else
                WeeklyGrowthNarrativeCard(
                  initialExpanded: initialPanel == panelWeeklyNarrative,
                ),
              const RemediablePatternsCard(),
              const SizedBox(height: DS.spacing16),
              _InsightModuleCard(
                title: context.l10n.gdChronicleTitle,
                subtitle: context.l10n.gdChronicleSubtitle,
                status: context.l10n.gdStorySummary,
                accent: colors.primary,
                icon: Icons.auto_stories_rounded,
                highlighted: initialPanel == panelWeeklyNarrative,
                buttonLabel: context.l10n.gdOpenChronicle,
                onPressed: () => context.push(InsightsRoutes.growthChronicle),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: context.l10n.gdLearningDashboardTitle,
                subtitle: context.l10n.gdLearningDashboardSubtitle,
                status: context.l10n.gdDashboardSemantics,
                accent: colors.tertiary,
                icon: Icons.dashboard_customize_rounded,
                highlighted: false,
                buttonLabel: context.l10n.gdOpenDashboard,
                onPressed: () => context.push(InsightsRoutes.learningDashboard),
              ),
              const SizedBox(height: DS.spacing12),
              _InsightModuleCard(
                title: context.l10n.insDecisionLogTitle,
                subtitle: context.l10n.insDecisionLogSubtitle,
                status: context.l10n.insDecisionLogStatus,
                accent: DS.info,
                icon: Icons.account_tree_outlined,
                highlighted: false,
                buttonLabel: context.l10n.insDecisionLogOpen,
                onPressed: () => context.push(InsightsRoutes.directiveAudit),
              ),
              const SizedBox(height: DS.spacing16),
              _OverviewHero(activePanel: initialPanel),
              const SizedBox(height: DS.spacing16),
              _InsightModuleCard(
                title: context.l10n.insReportLabel,
                subtitle: latestReportPayload?.mastery.isNotEmpty ?? false
                    ? context.l10n
                        .lioRecentAnalysis(latestReportPayload!.mastery.length)
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
                                  context.l10n.insSwipeHint,
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(
                                        color: DS.textSecondary,
                                        height: 1.52,
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
                            context.l10n.insSwipeHint,
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: DS.textSecondary,
                                      height: 1.52,
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
}

class _OverviewHero extends StatelessWidget {
  const _OverviewHero({required this.activePanel});

  final String? activePanel;

  @override
  Widget build(BuildContext context) {
    final focusLabel = switch (activePanel) {
      LearningInsightsOverviewScreen.panelReport =>
        'Report · ${context.l10n.insFlowTitle}',
      _ => context.l10n.insFlowTitle,
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
            context.l10n.insFlowTitle,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  height: 1.2,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.insFlowSubtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                  height: 1.52,
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
                          fontWeight: FontWeight.w700,
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
                      context.l10n.insRecommended,
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
                    height: 1.52,
                  ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              status,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.52,
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
