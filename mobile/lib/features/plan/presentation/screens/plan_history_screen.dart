import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

class PlanHistoryScreen extends ConsumerWidget {
  const PlanHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final archivedPlans = planState.plans.where((p) => !p.isActive).toList();

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('历史计划'),
      ),
      body: ContentConstraint(
        child: RefreshIndicator(
          onRefresh: () => ref.read(planListProvider.notifier).refresh(),
          child: _buildBody(context, archivedPlans, planState.isLoading),
        ),
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    List<PlanModel> plans,
    bool isLoading,
  ) {
    if (isLoading && plans.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (plans.isEmpty) {
      return const Center(
        child: Text('暂无历史计划'),
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
              title: entry.key == PlanType.sprint ? '冲刺计划' : '成长计划',
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
          Text(
            title,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: DS.spacing12),
          ...plans.map(
            (plan) => Card(
              margin: const EdgeInsets.only(bottom: DS.spacing12),
              child: ListTile(
                title: Text(plan.name),
                subtitle: Text(
                  '${(plan.progress * 100).toStringAsFixed(0)}% 完成',
                ),
                trailing: TextButton.icon(
                  onPressed: () async {
                    await ref.read(planListProvider.notifier).restorePlan(plan.id);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('计划已恢复')),
                      );
                    }
                  },
                  icon: const Icon(Icons.restore_rounded),
                  label: const Text('恢复'),
                ),
                onTap: () => context.push('/plans/${plan.id}'),
              ),
            ),
          ),
        ],
      ),
    );
}
