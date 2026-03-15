import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

class GroupTasksScreen extends ConsumerWidget {
  const GroupTasksScreen({required this.groupId, super.key});
  final String groupId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksState = ref.watch(groupTasksProvider(groupId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('Group Tasks'),
      ),
      floatingActionButton: SparkleIconButton(
        size: DS.touchTargetMinSize,
        icon: const Icon(Icons.add),
        onPressed: () {
          // Feature: Show task creation dialog
          _showCreateTaskDialog(context, ref);
        },
      ),
      child: tasksState.when(
        data: (tasks) {
          if (tasks.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: 'No tasks yet',
                icon: Icons.assignment_outlined,
              ),
            );
          }
          return ContentConstraint(
            child: RefreshIndicator(
              onRefresh: () =>
                  ref.read(groupTasksProvider(groupId).notifier).refresh(),
              child: ListView.separated(
                padding: const EdgeInsets.all(DS.lg),
                itemCount: tasks.length,
                separatorBuilder: (context, index) =>
                    const SizedBox(height: DS.md),
                itemBuilder: (context, index) {
                  final task = tasks[index];
                  return GraphiteCardSurface(
                    surfaceRole: SparkleSurfaceRole.card,
                    padding: EdgeInsets.zero,
                    child: ListTile(
                      title: Text(task.title),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (task.description != null)
                            Text(
                              task.description!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          const SizedBox(height: DS.xs),
                          Row(
                            children: [
                              Icon(
                                Icons.timer,
                                size: 14,
                                color: DS.textSecondary,
                              ),
                              const SizedBox(width: DS.xs),
                              Text('${task.estimatedMinutes} min'),
                              const SizedBox(width: DS.md),
                              Icon(
                                Icons.people,
                                size: 14,
                                color: DS.textSecondary,
                              ),
                              const SizedBox(width: DS.xs),
                              Text('${task.totalClaims} claimed'),
                            ],
                          ),
                        ],
                      ),
                      trailing: task.isClaimedByMe
                          ? (task.myCompletionStatus ?? false
                              ? Icon(Icons.check_circle, color: DS.success)
                              : Icon(
                                  Icons.hourglass_bottom,
                                  color: DS.brandPrimaryConst,
                                ))
                          : SparkleButton.primary(
                              label: 'Claim',
                              onPressed: () {
                                ref
                                    .read(groupTasksProvider(groupId).notifier)
                                    .claimTask(task.id);
                              },
                            ),
                    ),
                  );
                },
              ),
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(
          child: CustomErrorWidget.page(
            context: context,
            message: e.toString(),
            onRetry: () =>
                ref.read(groupTasksProvider(groupId).notifier).refresh(),
          ),
        ),
      ),
    );
  }

  void _showCreateTaskDialog(BuildContext context, WidgetRef ref) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    var estimatedMinutes = 30;
    var difficulty = 2;

    showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('创建群组任务'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(
                    labelText: '任务标题',
                    hintText: '例如：完成第三章练习',
                    border: OutlineInputBorder(),
                  ),
                  autofocus: true,
                ),
                const SizedBox(height: DS.md),
                TextField(
                  controller: descriptionController,
                  decoration: const InputDecoration(
                    labelText: '任务描述（可选）',
                    hintText: '详细描述任务内容...',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: DS.md),
                Text(
                  '预计时间: $estimatedMinutes 分钟',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Slider(
                  value: estimatedMinutes.toDouble(),
                  min: 5,
                  max: 180,
                  divisions: 35,
                  label: '$estimatedMinutes 分钟',
                  onChanged: (value) {
                    setState(() {
                      estimatedMinutes = value.toInt();
                    });
                  },
                ),
                const SizedBox(height: DS.md),
                Text(
                  '难度: $difficulty/5',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Slider(
                  value: difficulty.toDouble(),
                  min: 1,
                  max: 5,
                  divisions: 4,
                  label: '$difficulty',
                  onChanged: (value) {
                    setState(() {
                      difficulty = value.toInt();
                    });
                  },
                ),
              ],
            ),
          ),
          actions: [
            SparkleButton.ghost(
              label: '取消',
              onPressed: () => Navigator.pop(context),
            ),
            SparkleButton.primary(
              label: '创建',
              onPressed: () async {
                final title = titleController.text.trim();
                if (title.isEmpty) {
                  AppFeedback.info(context, '请输入任务标题');
                  return;
                }

                Navigator.pop(context);

                try {
                  await ref
                      .read(groupTasksProvider(groupId).notifier)
                      .createTask(
                        GroupTaskCreate(
                          title: title,
                          description: descriptionController.text.trim().isEmpty
                              ? null
                              : descriptionController.text.trim(),
                          estimatedMinutes: estimatedMinutes,
                          difficulty: difficulty,
                        ),
                      );

                  if (context.mounted) {
                    AppFeedback.success(context, '任务创建成功');
                  }
                } catch (e) {
                  if (context.mounted) {
                    AppFeedback.error(context, '创建失败: $e');
                  }
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}
