import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/community/share_resource_sheet.dart';

class PlanDetailScreen extends ConsumerWidget {
  const PlanDetailScreen({required this.planId, super.key});
  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planAsync = ref.watch(planDetailProvider(planId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('计划详情'),
        actions: [
          planAsync.maybeWhen(
            data: (plan) => IconButton(
              icon: const Icon(Icons.share_outlined),
              onPressed: () => showShareResourceSheet(
                context,
                resourceType: 'plan',
                resourceId: plan.id,
                title: plan.name,
                subtitle: plan.description ?? plan.subject ?? '',
              ),
            ),
            orElse: () => const SizedBox.shrink(),
          ),
        ],
      ),
      body: planAsync.when(
        data: (plan) => _PlanDetailView(plan: plan),
        loading: () => const Center(child: LoadingIndicator()),
        error: (err, _) => CustomErrorWidget.page(
          message: '计划加载失败：$err',
          onRetry: () => ref.refresh(planDetailProvider(planId)),
        ),
      ),
    );
  }
}

class _PlanDetailView extends StatelessWidget {
  const _PlanDetailView({required this.plan});
  final PlanModel plan;

  @override
  Widget build(BuildContext context) {
    final targetDate = plan.targetDate != null
        ? DateFormat.yMMMd().format(plan.targetDate!)
        : null;

    return ListView(
      padding: const EdgeInsets.all(DS.lg),
      children: [
        Card(
          elevation: 2,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  plan.name,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                if (plan.description != null &&
                    plan.description!.isNotEmpty) ...[
                  const SizedBox(height: DS.sm),
                  Text(plan.description!,
                      style: Theme.of(context).textTheme.bodyMedium,),
                ],
                const SizedBox(height: DS.lg),
                LinearProgressIndicator(
                  value: plan.progress,
                  minHeight: 8,
                  borderRadius: BorderRadius.circular(4),
                ),
                const SizedBox(height: DS.sm),
                Text('${(plan.progress * 100).toStringAsFixed(0)}% 进度'),
                if (targetDate != null) ...[
                  const SizedBox(height: DS.md),
                  Row(
                    children: [
                      Icon(Icons.event, size: 16, color: DS.textSecondary),
                      const SizedBox(width: DS.xs),
                      Text('目标日期: $targetDate'),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: DS.lg),
        Text('相关任务', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: DS.sm),
        if (plan.tasks == null || plan.tasks!.isEmpty)
          Text('暂无任务', style: TextStyle(color: DS.textSecondary))
        else
          ...plan.tasks!.map(
            (task) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(task.title),
              subtitle: Text(task.status.name),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push('/tasks/${task.id}'),
            ),
          ),
      ],
    );
  }
}
