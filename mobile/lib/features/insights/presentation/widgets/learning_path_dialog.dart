import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/repositories/learning_path_repository.dart';
import 'package:sparkle/features/insights/presentation/providers/learning_path_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class LearningPathDialog extends ConsumerWidget {
  const LearningPathDialog({
    required this.targetNodeId,
    required this.targetNodeName,
    super.key,
  });
  final String targetNodeId;
  final String targetNodeName;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pathAsync = ref.watch(learningPathProvider(targetNodeId));
    final mediaQuery = MediaQuery.of(context);
    // Cap list height so the bottom sheet never overflows the screen.
    // Subtract viewPadding + approximate modal chrome (handle + title + padding).
    final maxListHeight = (mediaQuery.size.height -
            mediaQuery.viewPadding.top -
            mediaQuery.viewPadding.bottom) *
        0.55;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '目标：$targetNodeName',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: DS.textSecondary,
              ),
        ),
        const SizedBox(height: DS.lg),
        ConstrainedBox(
          constraints: BoxConstraints(maxHeight: maxListHeight),
          child: pathAsync.when(
            data: (path) {
              if (path.isEmpty) {
                return const Center(
                  child: Text('无需前置知识，可以直接开始学习！'),
                );
              }
              return ListView.builder(
                shrinkWrap: true,
                itemCount: path.length,
                itemBuilder: (context, index) {
                  final node = path[index];
                  final isLast = index == path.length - 1;
                  return _buildTimelineItem(context, ref, node, isLast);
                },
              );
            },
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (err, stack) => Center(child: Text('加载失败：$err')),
          ),
        ),
        const SizedBox(height: DS.lg),
        SparkleButton.primary(
          label: '一键生成学习计划',
          icon: const Icon(Icons.auto_awesome),
          expand: true,
          onPressed: () => _handleCreateFullPlan(context, ref),
        ),
      ],
    );
  }

  Widget _buildTimelineItem(
    BuildContext context,
    WidgetRef ref,
    LearningPathNode node,
    bool isLast,
  ) {
    Color statusColor;
    IconData statusIcon;

    switch (node.status) {
      case 'mastered':
        statusColor = DS.success;
        statusIcon = Icons.check_circle;
      case 'unlocked':
        statusColor = DS.brandPrimary;
        statusIcon = Icons.lock_open;
      case 'locked':
      default:
        statusColor = DS.textTertiary;
        statusIcon = Icons.lock;
    }

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _showNodeActions(context, ref, node),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: statusColor.withValues(alpha: 0.2),
                    ),
                    padding: const EdgeInsets.all(DS.sm),
                    child: Icon(statusIcon, color: statusColor, size: 20),
                  ),
                  if (!isLast)
                    Expanded(
                      child: Container(
                        width: 2,
                        color: DS.brandPrimary.withValues(alpha: 0.3),
                        margin:
                            const EdgeInsets.symmetric(vertical: DS.spacing4),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: DS.lg),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        node.name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: node.isTarget
                                      ? Theme.of(context).primaryColor
                                      : null,
                                ),
                      ),
                      const SizedBox(height: DS.xs),
                      Text(
                        _statusLabel(node.status),
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: statusColor,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showNodeActions(
    BuildContext parentContext,
    WidgetRef ref,
    LearningPathNode node,
  ) {
    unawaited(
      showModalBottomSheet<void>(
        context: parentContext,
        useRootNavigator: true,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (sheetContext) => GraphiteModalSurface(
          title: node.name,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SparkleButton.primary(
                label: '查看详情',
                icon: const Icon(Icons.open_in_new),
                expand: true,
                onPressed: () => _handleOpenNode(
                  parentContext,
                  sheetContext,
                  node,
                ),
              ),
              const SizedBox(height: DS.sm),
              SparkleButton.secondary(
                label: '生成任务卡',
                icon: const Icon(Icons.task_alt),
                expand: true,
                onPressed: () => _handleCreateTask(
                  parentContext,
                  sheetContext,
                  ref,
                  node,
                ),
              ),
              const SizedBox(height: DS.sm),
              SparkleButton.ghost(
                label: '生成学习计划',
                icon: const Icon(Icons.event_note),
                expand: true,
                onPressed: () => _handleCreatePlan(
                  parentContext,
                  sheetContext,
                  ref,
                  node,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleOpenNode(
    BuildContext parentContext,
    BuildContext sheetContext,
    LearningPathNode node,
  ) {
    Navigator.of(sheetContext).pop(); // close action sheet
    Navigator.of(parentContext).pop(); // close learning path dialog
    _pushFromRoot('/galaxy/node/${node.id}', fallbackContext: parentContext);
  }

  Future<void> _handleCreateTask(
    BuildContext parentContext,
    BuildContext sheetContext,
    WidgetRef ref,
    LearningPathNode node,
  ) async {
    final feedbackContext = _feedbackContext(parentContext);
    Navigator.of(sheetContext).pop(); // close action sheet
    AppFeedback.loading(feedbackContext, '正在创建任务卡...');
    try {
      final task = await ref.read(taskRepositoryProvider).createTask(
            TaskCreate(
              title: '学习：${node.name}',
              type: TaskType.learning,
              estimatedMinutes: 25,
              difficulty: 2,
              knowledgeNodeId: node.id,
            ),
          );
      if (!feedbackContext.mounted) return;
      AppFeedback.success(feedbackContext, '任务卡已创建');
      Navigator.of(parentContext).pop(); // close learning path dialog
      _pushFromRoot('/tasks/${task.id}', fallbackContext: feedbackContext);
    } catch (e) {
      if (!feedbackContext.mounted) return;
      AppFeedback.error(feedbackContext, '创建失败: $e');
    }
  }

  Future<void> _handleCreatePlan(
    BuildContext parentContext,
    BuildContext sheetContext,
    WidgetRef ref,
    LearningPathNode node,
  ) async {
    final feedbackContext = _feedbackContext(parentContext);
    Navigator.of(sheetContext).pop(); // close action sheet
    AppFeedback.loading(feedbackContext, '正在生成学习计划（可能需要几秒）...');
    try {
      final response = await ref
          .read(learningPathRepositoryProvider)
          .generateLearningPlan(node.id);
      if (!feedbackContext.mounted) return;
      final message = response.message ?? '学习计划已生成';
      if (response.retry ?? false) {
        AppFeedback.warning(feedbackContext, message);
      } else {
        AppFeedback.success(feedbackContext, message);
      }
      Navigator.of(parentContext).pop(); // close learning path dialog
      _pushFromRoot(
        '/plans/${response.planId}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      if (!feedbackContext.mounted) return;
      AppFeedback.error(feedbackContext, '生成失败: $e');
    }
  }

  Future<void> _handleCreateFullPlan(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final feedbackContext = _feedbackContext(context);
    AppFeedback.loading(feedbackContext, '正在生成全路径计划...');
    try {
      final response = await ref
          .read(learningPathRepositoryProvider)
          .generateFullPathPlan(targetNodeId);
      if (!feedbackContext.mounted) return;
      AppFeedback.success(feedbackContext, '学习计划已生成');
      Navigator.of(context).pop();
      _pushFromRoot(
        '/plans/${response.planId}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      if (!feedbackContext.mounted) return;
      AppFeedback.error(feedbackContext, '生成失败: $e');
    }
  }

  BuildContext _feedbackContext(BuildContext fallbackContext) =>
      navigatorKey.currentContext ?? fallbackContext;

  void _pushFromRoot(String location, {required BuildContext fallbackContext}) {
    final navigationContext = navigatorKey.currentContext ?? fallbackContext;
    if (!navigationContext.mounted) {
      return;
    }
    unawaited(navigationContext.push(location));
  }

  static String _statusLabel(String status) {
    switch (status) {
      case 'mastered':
        return '已掌握';
      case 'unlocked':
        return '可学习';
      case 'locked':
        return '待解锁';
      default:
        return status;
    }
  }
}
