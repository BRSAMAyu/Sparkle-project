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
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
            context.l10n.lpTarget(widget.targetNodeName),
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
                  return Center(
                    child: Text(context.l10n.insNoPrereq),
                  );
                }

                return SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (coreNodes.isNotEmpty) ...[
                        Text(
                          context.l10n.lpMainPath,
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: DS.fontWeightBold,
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
                message: context.l10n.lpLoadFailed(err.toString()),
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
                  context.l10n.lpGenMethod,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.xs),
                Text(
                  context.l10n.lpGenMethodDesc,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.md),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 420;
                    final taskButton = SparkleButton(
                      label: _isGeneratingTaskPath ? context.l10n.lpGenerating : context.l10n.insQuickPath,
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
                      label: _isGeneratingFullPlan ? context.l10n.lpGenerating : context.l10n.insFullPlan,
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
              context.l10n.lpOptionalNodes,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              context.l10n.lpOptionalNodesDesc,
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
                final relationLabel = _relationLabel(context.l10n, node.relationType);
                final sourceLabel = _sourceLabel(context.l10n, node.sourceType);
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
                                  fontWeight: DS.fontWeightBold,
                                  color: node.isTarget
                                      ? Theme.of(context).primaryColor
                                      : null,
                                ),
                      ),
                      const SizedBox(height: DS.xs),
                      Text(
                        _statusLabel(context.l10n, node.status),
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
                label: context.l10n.insViewDetail,
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
                label: context.l10n.insGenTaskCard,
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
                label: context.l10n.insGenPlan,
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
    _setInlineStatus(context.l10n.lpCreatingTask(node.name));
    try {
      final task = await ref.read(taskRepositoryProvider).createTask(
            TaskCreate(
              title: context.l10n.insLearnNode(node.name),
              type: TaskType.learning,
              estimatedMinutes: 25,
              difficulty: 2,
              knowledgeNodeId: node.id,
            ),
          );
      if (!feedbackContext.mounted) return;
      AppFeedback.success(feedbackContext, context.l10n.lpTaskCreated);
      _clearInlineFeedback();
      _closeThenPushFromRoot(
        parentContext,
        '/tasks/${task.id}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      _setInlineError(context.l10n.insCreateFailed(e.toString()));
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
    _setInlineStatus(context.l10n.lpGeneratingPlan(node.name));
    try {
      final response =
          await ref.read(learningPathRepositoryProvider).generateLearningPlan(
                node.id,
                selectedRelatedNodeIds: node.id == widget.targetNodeId
                    ? _selectedRelatedNodeIds.toList(growable: false)
                    : const [],
              );
      if (!feedbackContext.mounted) return;
      final message = response.message ?? context.l10n.lpPlanGenerated;
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
      _setInlineError(context.l10n.insGenFailed(e.toString()));
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
    _setInlineStatus(context.l10n.lpGeneratingFullPath);
    try {
      final response =
          await ref.read(learningPathRepositoryProvider).generateFullPathPlan(
                widget.targetNodeId,
                selectedRelatedNodeIds:
                    _selectedRelatedNodeIds.toList(growable: false),
              );
      if (!feedbackContext.mounted) return;
      AppFeedback.success(feedbackContext, I18nService.instance.isChinese ? '学习计划已生成' : 'Learning plan generated');
      _clearInlineFeedback();
      _closeThenPushFromRoot(
        context,
        '/plans/${response.planId}',
        fallbackContext: feedbackContext,
      );
    } catch (e) {
      _setInlineError(context.l10n.insGenFailed(e.toString()));
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
    _setInlineStatus(context.l10n.lpGeneratingTaskPath);
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
        response.message ?? context.l10n.lpTaskPathGenerated,
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
      _setInlineError(context.l10n.insGenFailed(e.toString()));
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

  static String _statusLabel(AppLocalizations l, String status) {
    switch (status) {
      case 'mastered':
        return l.lpStatusMastered;
      case 'unlocked':
        return l.lpStatusUnlocked;
      case 'locked':
        return l.lpStatusLocked;
      default:
        return status;
    }
  }

  static String? _relationLabel(AppLocalizations l, String? relationType) {
    switch (relationType) {
      case 'application':
        return l.lpRelationApplication;
      case 'evolution':
        return l.lpRelationEvolution;
      case 'composition':
        return l.lpRelationComposition;
      case 'related':
        return l.lpRelationRelated;
      default:
        return null;
    }
  }

  static String? _sourceLabel(AppLocalizations l, String? sourceType) {
    switch (sourceType) {
      case 'llm_expanded':
        return l.lpSourceLlm;
      case 'seed':
        return l.lpSourceSeed;
      case 'user_created':
        return l.lpSourceUser;
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
  Widget build(BuildContext context) {
    final l = context.l10n;
    return GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.xs,
              children: [
                _MetaChip(
                  icon: Icons.radio_button_checked_rounded,
                  label: _LearningPathDialogState._statusLabel(l, node.status),
                ),
                if (node.isTarget)
                  _MetaChip(
                    icon: Icons.flag_rounded,
                    label: l.insTargetNode,
                  ),
                if (node.isOptional)
                  _MetaChip(
                    icon: Icons.extension_rounded,
                    label: l.insOptionalExtend,
                  ),
                if (_LearningPathDialogState._relationLabel(
                      l,
                      node.relationType,
                    ) !=
                    null)
                  _MetaChip(
                    icon: Icons.hub_rounded,
                    label: _LearningPathDialogState._relationLabel(
                      l,
                      node.relationType,
                    )!,
                  ),
                if (_LearningPathDialogState._sourceLabel(l, node.sourceType) !=
                    null)
                  _MetaChip(
                    icon: Icons.auto_awesome_rounded,
                    label: _LearningPathDialogState._sourceLabel(
                      l,
                      node.sourceType,
                    )!,
                  ),
              ],
            ),
            const SizedBox(height: DS.md),
            Text(
              node.isTarget ? l.lpTargetNodeDesc : l.lpNormalNodeDesc,
              style: DS.bodyMedium.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.md),
            FutureBuilder<List<TaskModel>>(
              future: relatedTasksFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Text(
                    l.lpLoadingRelatedTasks,
                    style: DS.bodySmall.copyWith(color: DS.textTertiary),
                  );
                }

                final tasks = snapshot.data ?? const <TaskModel>[];
                if (tasks.isEmpty) {
                  return Text(
                    l.lpNoRelatedTasks,
                    style: DS.bodySmall.copyWith(color: DS.textTertiary),
                  );
                }

                final visible = tasks.take(3).toList(growable: false);
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l.lpRelatedTasks,
                      style: DS.labelLarge.copyWith(
                        fontWeight: DS.fontWeightBold,
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
                  label: context.l10n.insRetryLoad,
                  icon: const Icon(Icons.refresh_rounded),
                  onPressed: onRetry,
                ),
              ],
            ),
          ),
        ),
      );
}
