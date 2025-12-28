import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
// import 'package:sparkle/presentation/widgets/task/task_card.dart'; // Assuming TaskCard is available

class SprintScreen extends ConsumerWidget {
  const SprintScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final activeSprint = planState.activePlans.where((p) => p.type == PlanType.sprint).firstOrNull;

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Sprint'),
        actions: [
          if (activeSprint != null)
            IconButton(
              icon: Icon(Icons.edit_outlined),
              onPressed: () {
                context.push('/plans/${activeSprint.id}/edit');
              },
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(planListProvider.notifier).refresh(),
        child: _buildBody(context, planState, activeSprint),
      ),
    );
  }

  Widget _buildBody(BuildContext context, PlanListState state, PlanModel? activeSprint) {
    if (state.isLoading && activeSprint == null) {
      return Center(child: CircularProgressIndicator());
    }

    if (activeSprint == null) {
      return const _NoActiveSprintView();
    }

    return _ActiveSprintView(plan: activeSprint);
  }
}

class _NoActiveSprintView extends StatelessWidget {
  const _NoActiveSprintView();

  @override
  Widget build(BuildContext context) => Center(
      child: Padding(
        padding: EdgeInsets.all(DS.xl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.flag_outlined, size: 80, color: DS.brandPrimary),
            SizedBox(height: DS.lg),
            Text(
              'No Active Sprint',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            SizedBox(height: DS.sm),
            const Text(
              'Create a new sprint plan to focus on a short-term goal.',
              textAlign: TextAlign.center,
            ),
            SizedBox(height: DS.xl),
            ElevatedButton.icon(
              onPressed: () {
                context.push('/plans/new?type=sprint');
              },
              icon: Icon(Icons.add),
              label: const Text('Create Sprint Plan'),
            ),
          ],
        ),
      ),
    );
}

class _ActiveSprintView extends ConsumerWidget {
  const _ActiveSprintView({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // We need the full plan details (with tasks), so we watch the detail provider
    final planDetailAsync = ref.watch(planDetailProvider(plan.id));

    return planDetailAsync.when(
      data: (fullPlan) => CustomScrollView(
        slivers: [
          SliverToBoxAdapter(child: _SprintHeader(plan: fullPlan)),
          SliverToBoxAdapter(
            child: Padding(
              padding: EdgeInsets.all(DS.lg),
              child: Text(
                'Tasks',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
          ),
          if (fullPlan.tasks == null || fullPlan.tasks!.isEmpty)
            const SliverToBoxAdapter(child: Center(child: Text('No tasks in this sprint.')))
          else
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  final task = fullPlan.tasks![index];
                  // return TaskCard(task: task); // TODO: Uncomment when TaskCard is available and integrated
                  return ListTile(title: Text(task.title), subtitle: Text(task.status.name));
                },
                childCount: fullPlan.tasks!.length,
              ),
            ),
        ],
      ),
      loading: () => Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(child: Text('Error: $err')),
    );
  }
}

class _SprintHeader extends StatelessWidget {
  const _SprintHeader({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final daysLeft = plan.targetDate?.difference(DateTime.now()).inDays ?? 0;

    return Padding(
      padding: EdgeInsets.all(DS.lg),
      child: Card(
        elevation: 4,
        child: Padding(
          padding: EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(plan.name, style: Theme.of(context).textTheme.headlineMedium),
              SizedBox(height: DS.sm),
              Text(plan.description ?? '', style: Theme.of(context).textTheme.bodyMedium),
              SizedBox(height: DS.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Progress', style: Theme.of(context).textTheme.bodyLarge),
                  Text('${(plan.progress * 100).toStringAsFixed(0)}%', style: Theme.of(context).textTheme.bodyLarge),
                ],
              ),
              SizedBox(height: DS.sm),
              LinearProgressIndicator(
                value: plan.progress,
                minHeight: 8,
                borderRadius: BorderRadius.circular(4),
              ),
              SizedBox(height: DS.lg),
              Chip(
                label: Text(daysLeft > 0 ? '$daysLeft days left' : 'Sprint ended'),
                avatar: Icon(Icons.timelapse),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
