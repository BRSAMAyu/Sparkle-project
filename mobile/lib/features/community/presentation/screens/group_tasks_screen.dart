import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
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
        title: const Text('群组任务'),
      ),
      floatingActionButton: SparkleIconButton(
        icon: const Icon(Icons.add),
        onPressed: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
          _showCreateTaskDialog(context, ref);
        },
      ),
      child: tasksState.when(
        data: (tasks) {
          if (tasks.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: '暂无任务',
                icon: Icons.assignment_outlined,
              ),
            );
          }

          // Kanban: unclaimed / in-progress / completed
          final unclaimed = tasks.where((t) => !t.isClaimedByMe).toList();
          final inProgress = tasks
              .where((t) => t.isClaimedByMe && !(t.myCompletionStatus ?? false))
              .toList();
          final completed = tasks
              .where((t) => t.isClaimedByMe && (t.myCompletionStatus ?? false))
              .toList();

          return ContentConstraint(
            child: RefreshIndicator(
              onRefresh: () =>
                  ref.read(groupTasksProvider(groupId).notifier).refresh(),
              child: ListView(
                padding: const EdgeInsets.all(DS.lg),
                children: [
                  if (inProgress.isNotEmpty) ...[
                    _sectionHeader('进行中', DS.brandPrimary),
                    ...inProgress.indexed.map(
                      (entry) => SparkleStaggerItem(
                        index: entry.$1,
                        child: _TaskCard(
                          task: entry.$2,
                          groupId: groupId,
                          onComplete: () async {
                            try {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.success,
                                ),
                              );
                              await ref
                                  .read(communityRepositoryProvider)
                                  .completeTask(entry.$2.id);
                              ref.invalidate(groupTasksProvider(groupId));
                              if (context.mounted) {
                                AppFeedback.success(context, '任务已完成！');
                              }
                            } catch (e) {
                              if (context.mounted) {
                                AppFeedback.error(context, '操作失败: $e');
                              }
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                  if (unclaimed.isNotEmpty) ...[
                    _sectionHeader('待认领', DS.neutral500),
                    ...unclaimed.indexed.map(
                      (entry) => SparkleStaggerItem(
                        index: entry.$1 + inProgress.length,
                        child: _TaskCard(
                          task: entry.$2,
                          groupId: groupId,
                          onClaim: () {
                            unawaited(
                              SensoryFeedbackService.emit(
                                SensoryFeedbackEvent.confirm,
                              ),
                            );
                            ref
                                .read(groupTasksProvider(groupId).notifier)
                                .claimTask(entry.$2.id);
                          },
                        ),
                      ),
                    ),
                  ],
                  if (completed.isNotEmpty) ...[
                    _sectionHeader('已完成', DS.success),
                    ...completed.indexed
                        .map(
                          (entry) => SparkleStaggerItem(
                            index: entry.$1 + inProgress.length + unclaimed.length,
                            child: _TaskCard(
                              task: entry.$2,
                              groupId: groupId,
                            ),
                          ),
                        ),
                  ],
                ],
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

  Widget _sectionHeader(String title, Color color) => Padding(
        padding: const EdgeInsets.fromLTRB(0, DS.md, 0, DS.sm),
        child: Row(
          children: [
            Container(
              width: 4,
              height: 18,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: DS.sm),
            Text(
              title,
              style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: color,
                  fontSize: DS.fontSizeBase,),
            ),
          ],
        ),
      );
}

// ─── Task Card ────────────────────────────────────────────────────────────────

class _TaskCard extends StatelessWidget {
  const _TaskCard({
    required this.task,
    required this.groupId,
    this.onClaim,
    this.onComplete,
  });

  final GroupTaskInfo task;
  final String groupId;
  final VoidCallback? onClaim;
  final VoidCallback? onComplete;

  @override
  Widget build(BuildContext context) {
    final isDone = task.isClaimedByMe && (task.myCompletionStatus ?? false);
    final isInProgress =
        task.isClaimedByMe && !(task.myCompletionStatus ?? false);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      margin: const EdgeInsets.only(bottom: DS.md),
      padding: const EdgeInsets.all(DS.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  task.title,
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    decoration: isDone ? TextDecoration.lineThrough : null,
                  ),
                ),
              ),
              if (isDone) Icon(Icons.check_circle, color: DS.success, size: 20),
              if (isInProgress)
                Icon(
                  Icons.hourglass_bottom,
                  color: DS.brandPrimaryConst,
                  size: 20,
                ),
            ],
          ),
          if (task.description != null) ...[
            const SizedBox(height: DS.xs),
            Text(
              task.description!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style:
                  TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ],
          const SizedBox(height: DS.sm),
          Row(
            children: [
              Icon(Icons.timer, size: 14, color: DS.textSecondary),
              const SizedBox(width: DS.xs),
              Text(
                '${task.estimatedMinutes} 分钟',
                style:
                    TextStyle(fontSize: DS.fontSizeSm, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.md),
              Icon(Icons.people, size: 14, color: DS.textSecondary),
              const SizedBox(width: DS.xs),
              Text(
                '${task.totalClaims} 已认领',
                style:
                    TextStyle(fontSize: DS.fontSizeSm, color: DS.textSecondary),
              ),
              const Spacer(),
              if (onClaim != null)
                SparkleButton.primary(
                  label: '认领',
                  onPressed: onClaim!,
                )
              else if (onComplete != null)
                SparkleButton.primary(
                  label: '完成',
                  onPressed: onComplete!,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

// ─── Create Dialog ────────────────────────────────────────────────────────────

extension on GroupTasksScreen {
  void _showCreateTaskDialog(BuildContext context, WidgetRef ref) {
    final titleController = TextEditingController();
    final descriptionController = TextEditingController();
    var estimatedMinutes = 30;
    var difficulty = 2;

    showSensoryDialog<void>(
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
