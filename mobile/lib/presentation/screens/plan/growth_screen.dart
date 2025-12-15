import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';

class GrowthScreen extends ConsumerWidget {
  const GrowthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final growthPlans = planState.plans.where((p) => p.type == PlanType.growth).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Growth Plans'),
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(planListProvider.notifier).loadPlans(type: PlanType.growth),
        child: _buildBody(context, planState, growthPlans),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () { /* TODO: Navigate to create plan screen */ },
        icon: const Icon(Icons.add),
        label: const Text('New Plan'),
      ),
    );
  }

  Widget _buildBody(BuildContext context, PlanListState state, List<PlanModel> plans) {
    if (state.isLoading && plans.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (plans.isEmpty) {
      return const Center(
        child: Text('No growth plans created yet.'),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: plans.length,
      itemBuilder: (context, index) {
        return _GrowthPlanCard(plan: plans[index]);
      },
    );
  }
}

class _GrowthPlanCard extends StatelessWidget {
  final PlanModel plan;
  const _GrowthPlanCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: InkWell(
        onTap: () {
          // TODO: Navigate to plan detail screen
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(plan.name, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              if (plan.description != null) Text(plan.description!, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 16),
              _buildStatRow(
                context,
                'Mastery',
                '${(plan.masteryLevel * 100).toStringAsFixed(0)}%',
                plan.masteryLevel,
                Colors.purple,
              ),
              const SizedBox(height: 8),
              _buildStatRow(
                context,
                'Progress',
                '${(plan.progress * 100).toStringAsFixed(0)}%',
                plan.progress,
                Colors.blue,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatRow(BuildContext context, String label, String valueText, double progressValue, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
         Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: Theme.of(context).textTheme.bodyLarge),
            Text(valueText, style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.bold)),
          ],
        ),
        const SizedBox(height: 4),
        LinearProgressIndicator(
          value: progressValue,
          backgroundColor: color.withOpacity(0.2),
          color: color,
        ),
      ],
    );
  }
}
