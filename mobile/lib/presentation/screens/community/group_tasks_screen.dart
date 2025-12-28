import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class GroupTasksScreen extends ConsumerWidget {

  const GroupTasksScreen({required this.groupId, super.key});
  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksState = ref.watch(groupTasksProvider(groupId));

    return Scaffold(
      appBar: AppBar(title: const Text('Group Tasks')),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Feature: Show task creation dialog
          _showCreateTaskDialog(context, ref);
        },
        child: const Icon(Icons.add),
      ),
      body: tasksState.when(
        data: (tasks) {
          if (tasks.isEmpty) {
            return const Center(child: CompactEmptyState(message: 'No tasks yet', icon: Icons.assignment_outlined));
          }
          return RefreshIndicator(
            onRefresh: () => ref.read(groupTasksProvider(groupId).notifier).refresh(),
            child: ListView.separated(
              padding: const EdgeInsets.all(DS.lg),
              itemCount: tasks.length,
              separatorBuilder: (context, index) => const SizedBox(height: DS.md),
              itemBuilder: (context, index) {
                final task = tasks[index];
                return Card(
                  child: ListTile(
                    title: Text(task.title),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (task.description != null) Text(task.description!, maxLines: 1, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: DS.xs),
                        Row(
                          children: [
                            const Icon(Icons.timer, size: 14, color: DS.brandPrimary),
                            const SizedBox(width: DS.xs),
                            Text('${task.estimatedMinutes} min'),
                            const SizedBox(width: DS.md),
                            const Icon(Icons.people, size: 14, color: DS.brandPrimary),
                            const SizedBox(width: DS.xs),
                            Text('${task.totalClaims} claimed'),
                          ],
                        ),
                      ],
                    ),
                    trailing: task.isClaimedByMe
                        ? (task.myCompletionStatus ?? false
                            ? const Icon(Icons.check_circle, color: DS.success)
                            : const Icon(Icons.hourglass_bottom, color: DS.brandPrimary))
                        : SparkleButton.primary(label: 'Claim', onPressed: () {
                               ref.read(groupTasksProvider(groupId).notifier).claimTask(task.id);
                            },),
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () => ref.read(groupTasksProvider(groupId).notifier).refresh())),
      ),
    );
  }

  void _showCreateTaskDialog(BuildContext context, WidgetRef ref) {
    // Basic dialog to create task
    // Using a simple placeholder for now as detailed implementation would require more fields
    // and connecting to createGroupTask method in repo (which needs to be added to notifier)
  }
}
