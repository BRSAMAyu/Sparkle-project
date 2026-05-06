import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/data/services/plan_description_codec.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

class GrowthScreen extends ConsumerWidget {
  const GrowthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final growthPlans = planState.plans
        .where((p) => p.type == PlanType.growth && p.isActive)
        .toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.growthPlansTitle),
        actions: [
          Tooltip(
            message: context.l10n.planHistoryPlans,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.archive_outlined),
              onPressed: () => context.push('/plans/history'),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          unawaited(context.push('/plans/new?type=growth'));
        },
        icon: const Icon(Icons.add),
        label: Text(context.l10n.newPlanLabel),
      ),
      child: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => ref
              .read(planListProvider.notifier)
              .loadPlans(type: PlanType.growth),
          child: _buildBody(context, planState, growthPlans),
        ),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    PlanListState state,
    List<PlanModel> plans,
  ) {
    if (state.isLoading && plans.isEmpty) {
      return const SparkleListSkeleton();
    }

    if (plans.isEmpty) {
      return EmptyState(
        type: EmptyStateType.noPlans,
        title: 'No active growth plans yet',
        description:
            'Turn a long-term direction into one living plan you can refine as you grow.',
        icon: Icons.trending_up_rounded,
        actionText: 'Create growth plan',
        onAction: () => unawaited(context.push('/plans/new?type=growth')),
      );
    }

    return ScrollEdgeHaptics(
      child: ListView.builder(
        padding: const EdgeInsets.all(DS.sm),
        itemCount: plans.length,
        itemBuilder: (context, index) => SparkleStaggerItem(
          index: index,
          child: _GrowthPlanCard(plan: plans[index]),
        ),
      ),
    );
  }
}

class _GrowthPlanCard extends StatelessWidget {
  const _GrowthPlanCard({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final parsed = PlanDescriptionCodec.parse(plan.description);
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
      padding: EdgeInsets.zero,
      child: SparkleTappable(
        onTap: () {
          unawaited(
            SensoryFeedbackService.emit(
              SensoryFeedbackEvent.selection,
            ),
          );
          unawaited(context.push('/plans/${plan.id}'));
        },
        hapticEvent: SensoryFeedbackEvent.selection,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(plan.name, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: DS.xs),
              if (parsed.schedule.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing8),
                  child: Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      if (parsed.reminderTime != null)
                        _InfoChip(
                          icon: Icons.alarm_rounded,
                          label: parsed.reminderTime!,
                        ),
                      if (plan.totalEstimatedHours != null)
                        _InfoChip(
                          icon: Icons.timelapse_rounded,
                          label:
                              context.l10n.planHoursUnit(plan.totalEstimatedHours!.toStringAsFixed(0)),
                        ),
                    ],
                  ),
                ),
              if (parsed.overview.isNotEmpty)
                _PlanMarkdownPreview(
                  data: parsed.overview,
                )
              else if (plan.description != null)
                _PlanMarkdownPreview(
                  data: plan.description!,
                ),
              const SizedBox(height: DS.lg),
              _buildStatRow(
                context,
                'Mastery',
                '${(plan.masteryLevel * 100).toStringAsFixed(0)}%',
                plan.masteryLevel,
                DS.brandSecondary,
              ),
              const SizedBox(height: DS.sm),
              _buildStatRow(
                context,
                'Progress',
                '${(plan.progress * 100).toStringAsFixed(0)}%',
                plan.progress,
                DS.brandPrimary,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatRow(
    BuildContext context,
    String label,
    String valueText,
    double progressValue,
    Color color,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodyLarge),
              Text(
                valueText,
                style: Theme.of(context)
                    .textTheme
                    .bodyLarge
                    ?.copyWith(fontWeight: DS.fontWeightBold),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0, end: progressValue),
            duration: DS.motionDuration(SparkleMotionToken.hero),
            curve: DS.motionCurve(SparkleMotionToken.hero),
            builder: (context, value, _) => LinearProgressIndicator(
              value: value,
              backgroundColor: color.withValues(alpha: 0.2),
              color: color,
            ),
          ),
        ],
      );
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(label, style: DS.bodySmall.copyWith(color: DS.textSecondary)),
          ],
        ),
      );
}

class _PlanMarkdownPreview extends StatelessWidget {
  const _PlanMarkdownPreview({required this.data});

  final String data;

  @override
  Widget build(BuildContext context) => SparkleMarkdown(
        content: data,
        textColor: DS.textSecondary,
        codeBackgroundColor: DS.surfaceSecondary,
        linkColor: DS.brandPrimary,
        lineHeight: 1.55,
      );
}
