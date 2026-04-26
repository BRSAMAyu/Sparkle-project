import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/galaxy/data/models/node_history_model.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';

typedef NodeReviewContextCallback = void Function(
  Map<String, dynamic> initialContext,
);
typedef NodeErrorFilterCallback = void Function(String nodeId, String label);

class NodeDetailSheet extends ConsumerStatefulWidget {
  const NodeDetailSheet({
    required this.nodeId,
    required this.nodeLabel,
    this.packId,
    this.initialHistory,
    this.onStartReview,
    this.onViewErrors,
    super.key,
  });

  final String nodeId;
  final String nodeLabel;
  final String? packId;
  final GalaxyNodeHistory? initialHistory;
  final NodeReviewContextCallback? onStartReview;
  final NodeErrorFilterCallback? onViewErrors;

  static Future<void> show({
    required BuildContext context,
    required String nodeId,
    required String nodeLabel,
    String? packId,
  }) =>
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        useSafeArea: true,
        builder: (context) => NodeDetailSheet(
          nodeId: nodeId,
          nodeLabel: nodeLabel,
          packId: packId,
        ),
      );

  @override
  ConsumerState<NodeDetailSheet> createState() => _NodeDetailSheetState();
}

class _NodeDetailSheetState extends ConsumerState<NodeDetailSheet> {
  Future<GalaxyNodeHistory>? _historyFuture;

  @override
  void initState() {
    super.initState();
    if (widget.initialHistory == null) {
      _historyFuture = _loadHistory();
    }
  }

  Future<GalaxyNodeHistory> _loadHistory() async {
    final result = await ref
        .read(enhancedGalaxyRepositoryProvider)
        .getNodeHistory(widget.nodeId, packId: widget.packId);
    if (result.isFailure) {
      throw StateError(
        result.error?.toString() ?? 'Failed to load node history',
      );
    }
    return result.value;
  }

  @override
  Widget build(BuildContext context) {
    final initialHistory = widget.initialHistory;
    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.only(
          left: DS.spacing20,
          right: DS.spacing20,
          top: DS.spacing12,
          bottom: MediaQuery.viewInsetsOf(context).bottom + DS.spacing16,
        ),
        child: SingleChildScrollView(
          child: initialHistory != null
              ? _HistoryContent(
                  history: initialHistory,
                  fallbackLabel: widget.nodeLabel,
                  nodeId: widget.nodeId,
                  onStartReview: _handleStartReview,
                  onViewErrors: _handleViewErrors,
                )
              : FutureBuilder<GalaxyNodeHistory>(
                  future: _historyFuture,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState != ConnectionState.done) {
                      return const _HistoryLoadingState();
                    }
                    if (snapshot.hasError || snapshot.data == null) {
                      return _HistoryErrorState(onRetry: _retry);
                    }
                    return _HistoryContent(
                      history: snapshot.data!,
                      fallbackLabel: widget.nodeLabel,
                      nodeId: widget.nodeId,
                      onStartReview: _handleStartReview,
                      onViewErrors: _handleViewErrors,
                    );
                  },
                ),
        ),
      ),
    );
  }

  void _retry() {
    setState(() {
      _historyFuture = _loadHistory();
    });
  }

  void _handleStartReview(GalaxyNodeHistory history) {
    final label = _effectiveLabel(history);
    final initialContext = <String, dynamic>{
      'review_node': widget.nodeId,
      'node_label': label,
      'mastery': history.mastery,
      'study_count': history.studyCount,
      'related_error_count': history.relatedErrors.length,
      'related_errors': history.relatedErrors
          .take(3)
          .map(_reviewErrorContext)
          .toList(growable: false),
    };
    final callback = widget.onStartReview;
    if (callback != null) {
      callback(initialContext);
      return;
    }

    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    final uri = Uri(
      path: '/chat',
      queryParameters: {
        'prompt': '带我复习「$label」。请先基于这个知识节点定位我最该补的薄弱点，再给我一组短练习。',
        'chat_mode': 'study_plan',
        'review_node': widget.nodeId,
        'node_label': label,
        'mastery': history.mastery.toString(),
        'study_count': history.studyCount.toString(),
        'related_error_count': history.relatedErrors.length.toString(),
      },
    );
    unawaited(
      router.push(
        uri.toString(),
        extra: {'initial_context': initialContext},
      ),
    );
  }

  void _handleViewErrors(GalaxyNodeHistory history) {
    final label = _effectiveLabel(history);
    final filterNodeId = history.resolvedNodeId?.trim().isNotEmpty ?? false
        ? history.resolvedNodeId!
        : widget.nodeId;
    final callback = widget.onViewErrors;
    if (callback != null) {
      callback(filterNodeId, label);
      return;
    }

    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    unawaited(
      router.push(
        Uri(
          path: '/errors',
          queryParameters: {
            'node_id': filterNodeId,
            'node_label': label,
          },
        ).toString(),
      ),
    );
  }

  String _effectiveLabel(GalaxyNodeHistory history) =>
      widget.nodeLabel.trim().isNotEmpty
          ? widget.nodeLabel.trim()
          : history.nodeLabel;

  Map<String, dynamic> _reviewErrorContext(GalaxyNodeErrorItem error) {
    return <String, dynamic>{
      'id': error.id,
      if (error.questionText != null && error.questionText!.trim().isNotEmpty)
        'question_text': error.questionText!.trim(),
      if (error.analysisSummary != null &&
          error.analysisSummary!.trim().isNotEmpty)
        'analysis_summary': error.analysisSummary!.trim(),
      'mastery_level': error.masteryLevel,
      'review_count': error.reviewCount,
    };
  }
}

class _HistoryContent extends StatelessWidget {
  const _HistoryContent({
    required this.history,
    required this.fallbackLabel,
    required this.nodeId,
    required this.onStartReview,
    required this.onViewErrors,
  });

  final GalaxyNodeHistory history;
  final String fallbackLabel;
  final String nodeId;
  final void Function(GalaxyNodeHistory history) onStartReview;
  final void Function(GalaxyNodeHistory history) onViewErrors;

  @override
  Widget build(BuildContext context) {
    final label = fallbackLabel.trim().isNotEmpty
        ? fallbackLabel.trim()
        : history.nodeLabel;
    final percent = history.masteryPercent;
    final relatedErrors = history.relatedErrors.take(2).toList();

    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 560),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Center(child: _SheetHandle()),
          const SizedBox(height: DS.spacing16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: DS.brandPrimary12,
                  borderRadius: BorderRadius.circular(DS.radius8),
                  border: Border.all(color: DS.brandPrimary24),
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  color: DS.brandPrimary,
                  size: DS.iconSizeSm,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: DS.textPrimary,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      nodeId,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: DS.textTertiary,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),
          Row(
            children: [
              Text(
                '掌握度',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: DS.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const Spacer(),
              Text(
                history.mastery <= 0 ? '尚未学习' : '$percent%',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: history.mastery <= 0 ? DS.textSecondary : DS.info,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          ClipRRect(
            borderRadius: BorderRadius.circular(DS.radius8),
            child: LinearProgressIndicator(
              minHeight: 8,
              value: history.mastery,
              backgroundColor: DS.surfaceTertiary,
              valueColor: AlwaysStoppedAnimation<Color>(
                history.mastery <= 0 ? DS.textDisabled : DS.info,
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _MetricChip(
                icon: Icons.history_rounded,
                label: history.studyCount > 0
                    ? '已学习 ${history.studyCount} 次'
                    : '尚未学习',
              ),
              _MetricChip(
                icon: Icons.schedule_rounded,
                label: history.lastStudiedAt == null
                    ? '暂无记录'
                    : '上次学习 ${_relativeTime(history.lastStudiedAt!)}',
              ),
              _MetricChip(
                icon: Icons.assignment_late_rounded,
                label: '相关错题 ${history.relatedErrors.length} 道',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),
          Text(
            '最近错题',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: DS.spacing10),
          if (relatedErrors.isEmpty)
            Text(
              '暂无相关错题',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            )
          else
            ...relatedErrors.map(_ErrorPreview.new),
          const SizedBox(height: DS.spacing20),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: () => onStartReview(history),
                  icon: Icon(
                    history.mastery <= 0
                        ? Icons.school_rounded
                        : Icons.play_arrow_rounded,
                  ),
                  label: Text(
                    history.mastery <= 0 ? '开始学习' : '开始复习',
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => onViewErrors(history),
                  icon: const Icon(Icons.assignment_rounded),
                  label: const Text('查看错题'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static String _relativeTime(DateTime dateTime) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inDays >= 1) {
      return '${diff.inDays} 天前';
    }
    if (diff.inHours >= 1) {
      return '${diff.inHours} 小时前';
    }
    if (diff.inMinutes >= 1) {
      return '${diff.inMinutes} 分钟前';
    }
    return '刚刚';
  }
}

class _SheetHandle extends StatelessWidget {
  const _SheetHandle();

  @override
  Widget build(BuildContext context) => Container(
        width: 42,
        height: 4,
        decoration: BoxDecoration(
          color: DS.borderSubtle,
          borderRadius: BorderRadius.circular(2),
        ),
      );
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: BorderRadius.circular(DS.radius8),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: DS.iconSizeXs, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ),
      );
}

class _ErrorPreview extends StatelessWidget {
  const _ErrorPreview(this.error);

  final GalaxyNodeErrorItem error;

  @override
  Widget build(BuildContext context) {
    final title = (error.questionText?.trim().isNotEmpty ?? false)
        ? error.questionText!.trim()
        : '图片错题';
    final subtitle = error.analysisSummary?.trim();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(DS.radius8),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w600,
                ),
          ),
          if (subtitle != null && subtitle.isNotEmpty) ...[
            const SizedBox(height: DS.spacing4),
            Text(
              subtitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}

class _HistoryLoadingState extends StatelessWidget {
  const _HistoryLoadingState();

  @override
  Widget build(BuildContext context) => const SizedBox(
        height: 220,
        child: Center(child: CircularProgressIndicator()),
      );
}

class _HistoryErrorState extends StatelessWidget {
  const _HistoryErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 220,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline_rounded, color: DS.warning),
            const SizedBox(height: DS.spacing12),
            Text(
              '节点历史加载失败',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: DS.spacing12),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('重试'),
            ),
          ],
        ),
      );
}
