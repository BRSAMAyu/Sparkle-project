import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

class PlanHistoryScreen extends ConsumerWidget {
  const PlanHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final archivedPlans = planState.plans.where((p) => !p.isActive).toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.planHistoryTitle),
      ),
      child: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => ref.read(planListProvider.notifier).refresh(),
          child: _buildBody(context, ref, archivedPlans, planState.isLoading),
        ),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    List<PlanModel> plans,
    bool isLoading,
  ) {
    if (isLoading && plans.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (plans.isEmpty) {
      return Center(
        child: Text(context.l10n.planHistoryEmpty),
      );
    }

    final grouped = <PlanType, List<PlanModel>>{};
    for (final plan in plans) {
      grouped.putIfAbsent(plan.type, () => []).add(plan);
    }

    return ListView(
      padding: const EdgeInsets.all(DS.lg),
      children: grouped.entries
          .map(
            (entry) => _PlanHistorySection(
              title: entry.key == PlanType.sprint
                  ? context.l10n.planTypeSprint
                  : context.l10n.planTypeGrowth,
              plans: entry.value,
            ),
          )
          .toList(),
    );
  }
}

class _PlanHistorySection extends ConsumerWidget {
  const _PlanHistorySection({
    required this.title,
    required this.plans,
  });

  final String title;
  final List<PlanModel> plans;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SparkleStaggerItem(
              index: 0,
              child: Text(
                title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            ...plans.asMap().entries.map(
              (entry) => SparkleStaggerItem(
                index: entry.key + 1,
                child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  margin: const EdgeInsets.only(bottom: DS.spacing12),
                  padding: EdgeInsets.zero,
                  child: ListTile(
                    title: Text(entry.value.name),
                    subtitle: Text(
                      context.l10n.planProgressPercent(
                        (entry.value.progress * 100).toStringAsFixed(0),
                      ),
                    ),
                    trailing: Tooltip(
                      message: context.l10n.planHistoryRestore,
                      child: SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        icon: const Icon(Icons.restore_rounded),
                        onPressed: () async {
                          unawaited(
                            SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.confirm,
                            ),
                          );
                          await ref
                              .read(planListProvider.notifier)
                              .restorePlan(entry.value.id);
                          if (context.mounted) {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.success,
                              ),
                            );
                            AppFeedback.success(
                              context,
                              context.l10n.planHistoryRestoreSuccess,
                            );
                          }
                        },
                      ),
                    ),
                    onTap: () {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        ),
                      );
                      context.push('/plans/${entry.value.id}');
                    },
                  ),
                ),
              ),
            ),
          ],
        ),
      );
}
