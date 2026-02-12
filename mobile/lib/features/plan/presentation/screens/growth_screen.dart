import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

class GrowthScreen extends ConsumerWidget {
  const GrowthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final growthPlans = planState.plans
        .where((p) => p.type == PlanType.growth && p.isActive)
        .toList();

    return Scaffold(
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Growth Plans'),
        actions: [
          Tooltip(
            message: '历史计划',
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              size: DS.touchTargetMinSize,
              icon: const Icon(Icons.archive_outlined),
              onPressed: () => context.push('/plans/history'),
            ),
          ),
        ],
      ),
      body: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => ref
              .read(planListProvider.notifier)
              .loadPlans(type: PlanType.growth),
          child: _buildBody(context, planState, growthPlans),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          context.push('/plans/new?type=growth');
        },
        icon: const Icon(Icons.add),
        label: const Text('New Plan'),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    PlanListState state,
    List<PlanModel> plans,
  ) {
    if (state.isLoading && plans.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (plans.isEmpty) {
      return const Center(
        child: Text('No growth plans created yet.'),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(DS.sm),
      itemCount: plans.length,
      itemBuilder: (context, index) => _GrowthPlanCard(plan: plans[index]),
    );
  }
}

class _GrowthPlanCard extends StatelessWidget {
  const _GrowthPlanCard({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) => Card(
        elevation: 2,
        margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
        child: InkWell(
          onTap: () {
            context.push('/plans/${plan.id}');
          },
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(plan.name, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: DS.xs),
                if (plan.description != null)
                  Text(
                    plan.description!,
                    style: Theme.of(context).textTheme.bodyMedium,
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
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
          LinearProgressIndicator(
            value: progressValue,
            backgroundColor: color.withValues(alpha: 0.2),
            color: color,
          ),
        ],
      );
}
