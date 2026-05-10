import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
        title: Text(context.l10n.communityGroupTasks),
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
            return Center(
              child: CompactEmptyState(
                message:
                    context.l10n.communityNoTasks,
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
            child: SparkleRefreshIndicator(
              onRefresh: () =>
                  ref.read(groupTasksProvider(groupId).notifier).refresh(),
              child: ListView(
                padding: const EdgeInsets.all(DS.lg),
                children: [
                  if (inProgress.isNotEmpty) ...[
                    _sectionHeader(
                      context.l10n.communityInProgress,
                      DS.brandPrimary,
                    ),
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
                                AppFeedback.success(
                                    context,
                                    context.l10n.communityTaskCompleted);
                              }
                            } catch (e) {
                              if (context.mounted) {
                                AppFeedback.error(
                                  context,
                                  '${context.l10n.communityOperationFailed}: $e',
                                );
                              }
                            }
                          },
                        ),
                      ),
                    ),
                  ],
                  if (unclaimed.isNotEmpty) ...[
                    _sectionHeader(
                      context.l10n.communityUnclaimed,
                      DS.neutral500,
                    ),
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
                    _sectionHeader(
                      context.l10n.communityCompleted,
                      DS.success,
                    ),
                    ...completed.indexed.map(
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
                fontWeight: DS.fontWeightBold,
                color: color,
                fontSize: DS.fontSizeBase,
              ),
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
                    fontWeight: DS.fontWeightBold,
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
                '${task.estimatedMinutes} ${context.l10n.communityTaskMinutes}',
                style:
                    TextStyle(fontSize: DS.fontSizeSm, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.md),
              Icon(Icons.people, size: 14, color: DS.textSecondary),
              const SizedBox(width: DS.xs),
              Text(
                '${task.totalClaims} ${context.l10n.communityTaskClaimed}',
                style:
                    TextStyle(fontSize: DS.fontSizeSm, color: DS.textSecondary),
              ),
              const Spacer(),
              if (onClaim != null)
                SparkleButton.primary(
                  label: context.l10n.communityTaskClaim,
                  onPressed: onClaim!,
                )
              else if (onComplete != null)
                SparkleButton.primary(
                  label: context.l10n.communityTaskComplete,
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
          title: Text(
              context.l10n.communityCreateTaskTitle),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: titleController,
                  decoration: InputDecoration(
                    labelText:
                        context.l10n.communityTaskTitleField,
                    hintText: context.l10n.communityTaskTitleHint,
                    border: const OutlineInputBorder(),
                  ),
                  autofocus: true,
                ),
                const SizedBox(height: DS.md),
                TextField(
                  controller: descriptionController,
                  decoration: InputDecoration(
                    labelText: context.l10n.communityTaskDescription,
                    hintText: context.l10n.communityTaskDescriptionHint,
                    border: const OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: DS.md),
                Text(
                  '${context.l10n.communityTaskEstimatedTime}: $estimatedMinutes ${context.l10n.communityTaskMinutes}',
                  style: const TextStyle(fontWeight: DS.fontWeightBold),
                ),
                Slider(
                  value: estimatedMinutes.toDouble(),
                  min: 5,
                  max: 180,
                  divisions: 35,
                  label:
                      '$estimatedMinutes ${context.l10n.communityTaskMinutes}',
                  onChanged: (value) {
                    setState(() {
                      estimatedMinutes = value.toInt();
                    });
                  },
                ),
                const SizedBox(height: DS.md),
                Text(
                  '${context.l10n.communityTaskDifficulty}: $difficulty/5',
                  style: const TextStyle(fontWeight: DS.fontWeightBold),
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
              label: context.l10n.communityCancel,
              onPressed: () => Navigator.pop(context),
            ),
            SparkleButton.primary(
              label: context.l10n.communityCreate,
              onPressed: () async {
                final title = titleController.text.trim();
                if (title.isEmpty) {
                  AppFeedback.info(
                    context,
                    context.l10n.communityEnterTaskTitle,
                  );
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
                    AppFeedback.success(
                      context,
                      context.l10n.communityTaskCreated,
                    );
                  }
                } catch (e) {
                  if (context.mounted) {
                    AppFeedback.error(
                      context,
                      context.l10n.communityCreateTaskFailed(e.toString()),
                    );
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
