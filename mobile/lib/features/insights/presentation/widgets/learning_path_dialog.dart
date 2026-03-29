import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/repositories/learning_path_repository.dart';
import 'package:sparkle/features/insights/presentation/providers/learning_path_provider.dart';
import 'package:sparkle/features/knowledge/presentation/providers/knowledge_detail_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class LearningPathDialog extends ConsumerStatefulWidget {
  const LearningPathDialog({
    required this.targetNodeId,
    required this.targetNodeName,
    super.key,
  });
  final String targetNodeId;
  final String targetNodeName;

  @override
  ConsumerState<LearningPathDialog> createState() => _LearningPathDialogState();
}

class _LearningPathDialogState extends ConsumerState<LearningPathDialog> {
  bool _isGeneratingTaskPath = false;
  bool _isGeneratingPlan = false;
  bool _isGeneratingFullPlan = false;
  String? _inlineStatus;
  String? _inlineError;
  final Set<String> _selectedRelatedNodeIds = <String>{};

  bool get _isBusy =>
      _isGeneratingTaskPath || _isGeneratingPlan || _isGeneratingFullPlan;

  void _setInlineStatus(String? message) {
    if (!mounted) return;
    setState(() {
      _inlineStatus = message;
      _inlineError = null;
    });
  }

  void _setInlineError(String message) {
    if (!mounted) return;
    setState(() {
      _inlineStatus = null;
      _inlineError = message;
    });
  }

  void _clearInlineFeedback() {
    if (!mounted) return;
    setState(() {
      _inlineStatus = null;
      _inlineError = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final pathAsync = ref.watch(learningPathProvider(widget.targetNodeId));
    final mediaQuery = MediaQuery.of(context);
    final maxDialogHeight = (mediaQuery.size.height -
            mediaQuery.viewPadding.top -
            mediaQuery.viewPadding.bottom) *
        0.76;

    return SizedBox(
      height: maxDialogHeight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '目标：${widget.targetNodeName}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          if (_inlineStatus != null || _inlineError != null) ...[
            const SizedBox(height: DS.md),
            _LearningPathInlineFeedback(
              message: _inlineError ?? _inlineStatus!,
              isError: _inlineError != null,
              isLoading: _isBusy,
              onDismiss: _isBusy ? null : _clearInlineFeedback,
            ),
          ],
          const SizedBox(height: DS.lg),
          Expanded(
            child: pathAsync.when(
              data: (path) {
                final coreNodes = path
                    .where((node) => !node.isOptional)
                    .toList(growable: false);
                final optionalNodes = path
                    .where((node) => node.isOptional)
                    .toList(growable: false);

                if (coreNodes.isEmpty && optionalNodes.isEmpty) {
                  return const Center(
                    child: Text('无需前置知识，可以直接开始学习！'),
                  );
                }

                return SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (coreNodes.isNotEmpty) ...[
                        Text(
                          '主干路径',
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                        const SizedBox(height: DS.md),
                        ...List.generate(coreNodes.length, (index) {
                          final node = coreNodes[index];
                          final isLast = index == coreNodes.length - 1;
                          return _buildTimelineItem(context, node, isLast);
                        }),
                      ],
                      if (optionalNodes.isNotEmpty) ...[
                        const SizedBox(height: DS.sm),
                        _buildOptionalNodesSection(context, optionalNodes),
                      ],
                    ],
                  ),
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, stack) => _LearningPathLoadError(
                message: '加载失败：$err',
                onRetry: () =>
                    ref.invalidate(learningPathProvider(widget.targetNodeId)),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          GraphiteCardSurface(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '生成方式',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: DS.xs),
                Text(
                  '快速任务路径不会占用计划额度，适合先生成几张可以立刻执行的任务卡；完整计划会创建正式方案。',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.md),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 420;
                    final taskButton = SparkleButton(
                      label: _isGeneratingTaskPath ? '正在生成...' : '快速生成任务路径',
                      icon: _isGeneratingTaskPath
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.bolt),
                      expand: true,
                      onPressed:
                          _isBusy ? null : () => _handleCreateTaskPath(context),
                      loading: _isGeneratingTaskPath,
                    );
                    final planButton = SparkleButton(
                      label: _isGeneratingFullPlan ? '正在生成...' : '生成完整计划',
                      icon: _isGeneratingFullPlan
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.auto_awesome),
                      expand: true,
                      variant: ButtonVariant.secondary,
                      onPressed:
                          _isBusy ? null : () => _handleCreateFullPlan(context),
                      loading: _isGeneratingFullPlan,
                    );
                    if (compact) {
                      return Column(
                        children: [
                          taskButton,
                          const SizedBox(height: DS.sm),
                          planButton,
                        ],
                      );
                    }
                    return Row(
                      children: [
                        Expanded(child: taskButton),
                        const SizedBox(width: DS.spacing12),
                        Expanded(child: planButton),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOptionalNodesSection(
    BuildContext context,
    List<LearningPathNode> optionalNodes,
  ) =>
      GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '推荐拓展节点',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              '这些节点不是必须前置，但可以由你决定是否一并纳入学习计划。',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: DS.md),
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: optionalNodes.map((node) {
                final selected = _selectedRelatedNodeIds.contains(node.id);
                final relationLabel = _relationLabel(node.relationType);
                final sourceLabel = _sourceLabel(node.sourceType);
                return FilterChip(
                  selected: selected,
                  label: Text(
                    sourceLabel == null
                        ? '${node.name}${relationLabel == null ? '' : ' · $relationLabel'}'
                        : '${node.name}${relationLabel == null ? '' : ' · $relationLabel'} · $sourceLabel',
                  ),
                  onSelected: _isBusy
                      ? null
                      : (value) {
                          setState(() {
                            if (value) {
                              _selectedRelatedNodeIds.add(node.id);
                            } else {
                              _selectedRelatedNodeIds.remove(node.id);
                            }
                          });
                        },
                );
              }).toList(growable: false),
            ),
          ],
        ),
      );

  Widget _buildTimelineItem(
    BuildContext context,
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
        onTap: _isBusy ? null : () => _showNodeActions(context, node),
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
    LearningPathNode node,
  ) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: parentContext,
        useRootNavigator: true,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (sheetContext) => GraphiteModalSurface(
          title: node.name,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _LearningPathNodeSummary(
                node: node,
                relatedTasksFuture: _loadRelatedTasks(node.id),
              ),
              const SizedBox(height: DS.md),
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
                  node,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<List<TaskModel>> _loadRelatedTasks(String nodeId) async {
    final response = await ref.read(taskRepositoryProvider).getTasks(
          pageSize: 50,
        );
    return response.items
        .where((task) => task.knowledgeNodeId == nodeId)
        .toList(growable: false);
  }

  void _handleOpenNode(
    BuildContext parentContext,
    BuildContext sheetContext,
    LearningPathNode node,
  ) {
    Navigator.of(sheetContext).pop(); // close action sheet
    _closeThenPushFromRoot(
      parentContext,
      '/galaxy/node/${node.id}',
    );
  }

  Future<void> _handleCreateTask(
    BuildContext parentContext,
    BuildContext sheetContext,
    LearningPathNode node,
  ) async {
    final feedbackContext = _feedbackContext(parentContext);
    Navigator.of(sheetContext).pop(); // close action sheet
    _setInlineStatus('正在为「${node.name}」创建任务卡...');
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
      _clearInlineFeedback();
      _closeThenPushFromRoot(
        parentContext,
        '/tasks/${task.id}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      _setInlineError('创建失败：$e');
    }
  }

  Future<void> _handleCreatePlan(
    BuildContext parentContext,
    BuildContext sheetContext,
    LearningPathNode node,
  ) async {
    final feedbackContext = _feedbackContext(parentContext);
    Navigator.of(sheetContext).pop(); // close action sheet
    setState(() {
      _isGeneratingPlan = true;
    });
    _setInlineStatus('正在为「${node.name}」生成学习计划，请稍候...');
    try {
      final response =
          await ref.read(learningPathRepositoryProvider).generateLearningPlan(
                node.id,
                selectedRelatedNodeIds: node.id == widget.targetNodeId
                    ? _selectedRelatedNodeIds.toList(growable: false)
                    : const [],
              );
      if (!feedbackContext.mounted) return;
      final message = response.message ?? '学习计划已生成';
      if (response.retry ?? false) {
        AppFeedback.warning(feedbackContext, message);
      } else {
        AppFeedback.success(feedbackContext, message);
      }
      _clearInlineFeedback();
      _closeThenPushFromRoot(
        parentContext,
        '/plans/${response.planId}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      _setInlineError('生成失败：$e');
    } finally {
      if (mounted) {
        setState(() {
          _isGeneratingPlan = false;
        });
      }
    }
  }

  Future<void> _handleCreateFullPlan(
    BuildContext context,
  ) async {
    final feedbackContext = _feedbackContext(context);
    setState(() {
      _isGeneratingFullPlan = true;
    });
    _setInlineStatus('正在生成完整学习路径计划，这可能需要十几秒...');
    try {
      final response =
          await ref.read(learningPathRepositoryProvider).generateFullPathPlan(
                widget.targetNodeId,
                selectedRelatedNodeIds:
                    _selectedRelatedNodeIds.toList(growable: false),
              );
      if (!feedbackContext.mounted) return;
      AppFeedback.success(feedbackContext, '学习计划已生成');
      _clearInlineFeedback();
      _closeThenPushFromRoot(
        context,
        '/plans/${response.planId}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      _setInlineError('生成失败：$e');
    } finally {
      if (mounted) {
        setState(() {
          _isGeneratingFullPlan = false;
        });
      }
    }
  }

  Future<void> _handleCreateTaskPath(BuildContext context) async {
    final feedbackContext = _feedbackContext(context);
    setState(() {
      _isGeneratingTaskPath = true;
    });
    _setInlineStatus('正在生成可立即执行的任务路径...');
    try {
      final response =
          await ref.read(learningPathRepositoryProvider).generateTaskPath(
                widget.targetNodeId,
                selectedRelatedNodeIds:
                    _selectedRelatedNodeIds.toList(growable: false),
              );
      if (!feedbackContext.mounted) return;
      AppFeedback.success(
        feedbackContext,
        response.message ?? '任务路径已生成',
      );
      ref.invalidate(knowledgeDetailProvider(widget.targetNodeId));
      _clearInlineFeedback();
      final taskListRoute = response.taskListEntityCard?.detailRoute?.trim();
      if (taskListRoute != null && taskListRoute.isNotEmpty) {
        _closeThenPushFromRoot(
          context,
          taskListRoute,
          fallbackContext: feedbackContext,
        );
      } else if (response.tasks.isNotEmpty) {
        _closeThenPushFromRoot(
          context,
          '/tasks',
          fallbackContext: feedbackContext,
        );
      } else {
        Navigator.of(context).pop();
      }
    } catch (e) {
      _setInlineError('生成失败：$e');
    } finally {
      if (mounted) {
        setState(() {
          _isGeneratingTaskPath = false;
        });
      }
    }
  }

  BuildContext _feedbackContext(BuildContext fallbackContext) =>
      navigatorKey.currentContext ?? fallbackContext;

  void _closeThenPushFromRoot(
    BuildContext sheetContext,
    String location, {
    BuildContext? fallbackContext,
  }) {
    final rootContext = navigatorKey.currentContext ??
        Navigator.of(sheetContext, rootNavigator: true).context;
    Navigator.of(sheetContext).pop();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final navigationContext =
          navigatorKey.currentContext ?? fallbackContext ?? rootContext;
      if (!navigationContext.mounted) {
        return;
      }
      unawaited(navigationContext.push(location));
    });
  }

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

  static String? _relationLabel(String? relationType) {
    switch (relationType) {
      case 'application':
        return '应用';
      case 'evolution':
        return '进阶';
      case 'composition':
        return '组成';
      case 'related':
        return '相关';
      default:
        return null;
    }
  }

  static String? _sourceLabel(String? sourceType) {
    switch (sourceType) {
      case 'llm_expanded':
        return 'AI推荐';
      case 'seed':
        return '预设';
      case 'user_created':
        return '用户添加';
      default:
        return null;
    }
  }
}

class _LearningPathNodeSummary extends StatelessWidget {
  const _LearningPathNodeSummary({
    required this.node,
    required this.relatedTasksFuture,
  });

  final LearningPathNode node;
  final Future<List<TaskModel>> relatedTasksFuture;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.xs,
              children: [
                _MetaChip(
                  icon: Icons.radio_button_checked_rounded,
                  label: _LearningPathDialogState._statusLabel(node.status),
                ),
                if (node.isTarget)
                  const _MetaChip(
                    icon: Icons.flag_rounded,
                    label: '目标节点',
                  ),
                if (node.isOptional)
                  const _MetaChip(
                    icon: Icons.extension_rounded,
                    label: '可选拓展',
                  ),
                if (_LearningPathDialogState._relationLabel(
                      node.relationType,
                    ) !=
                    null)
                  _MetaChip(
                    icon: Icons.hub_rounded,
                    label: _LearningPathDialogState._relationLabel(
                      node.relationType,
                    )!,
                  ),
                if (_LearningPathDialogState._sourceLabel(node.sourceType) !=
                    null)
                  _MetaChip(
                    icon: Icons.auto_awesome_rounded,
                    label: _LearningPathDialogState._sourceLabel(
                      node.sourceType,
                    )!,
                  ),
              ],
            ),
            const SizedBox(height: DS.md),
            Text(
              node.isTarget ? '这是当前学习路径的目标节点。' : '你可以围绕这个节点单独建任务，或把它并入学习计划。',
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.md),
            FutureBuilder<List<TaskModel>>(
              future: relatedTasksFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Text(
                    '正在加载关联任务...',
                    style: DS.bodySmall.copyWith(color: DS.textTertiary),
                  );
                }

                final tasks = snapshot.data ?? const <TaskModel>[];
                if (tasks.isEmpty) {
                  return Text(
                    '当前还没有关联任务。',
                    style: DS.bodySmall.copyWith(color: DS.textTertiary),
                  );
                }

                final visible = tasks.take(3).toList(growable: false);
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '关联任务',
                      style: DS.labelLarge.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    ...visible.map(
                      (task) => Padding(
                        padding: const EdgeInsets.only(bottom: DS.xs),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 5,
                              height: 5,
                              margin: const EdgeInsets.only(top: 7, right: 8),
                              decoration: BoxDecoration(
                                color: DS.textSecondary,
                                shape: BoxShape.circle,
                              ),
                            ),
                            Expanded(
                              child: Text(
                                task.title,
                                style: DS.bodySmall.copyWith(
                                  color: DS.textSecondary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      );
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.sm,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.xs),
            Text(
              label,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
          ],
        ),
      );
}

class _LearningPathInlineFeedback extends StatelessWidget {
  const _LearningPathInlineFeedback({
    required this.message,
    required this.isError,
    this.isLoading = false,
    this.onDismiss,
  });

  final String message;
  final bool isError;
  final bool isLoading;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final accent = isError ? DS.error : DS.primaryBase;
    final icon = isError
        ? Icons.error_outline_rounded
        : (isLoading
            ? Icons.hourglass_top_rounded
            : Icons.info_outline_rounded);

    return GraphiteCardSurface(
      borderColor: accent.withValues(alpha: 0.22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Icon(icon, size: 18, color: accent),
          ),
          const SizedBox(width: DS.sm),
          Expanded(
            child: Text(
              message,
              style: DS.bodyMedium.copyWith(color: DS.textPrimary),
            ),
          ),
          if (onDismiss != null)
            SparkleIconButton(
              icon: Icon(Icons.close_rounded, color: DS.textSecondary),
              onPressed: onDismiss,
              semanticLabel: 'dismiss feedback',
              variant: ButtonVariant.ghost,
            ),
        ],
      ),
    );
  }
}

class _LearningPathLoadError extends StatelessWidget {
  const _LearningPathLoadError({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: GraphiteCardSurface(
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.timeline_outlined, color: DS.error),
                const SizedBox(height: DS.sm),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.md),
                SparkleButton.secondary(
                  label: '重试加载',
                  icon: const Icon(Icons.refresh_rounded),
                  onPressed: onRetry,
                ),
              ],
            ),
          ),
        ),
      );
}
