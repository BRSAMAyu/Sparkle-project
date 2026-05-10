import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/galaxy/data/models/node_history_model.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/node_source_materials_provider.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:sparkle/l10n/app_localizations.dart';

typedef NodeReviewContextCallback = void Function(
  Map<String, dynamic> initialContext,
);
typedef NodeErrorFilterCallback = void Function(String nodeId, String label);
typedef NodeAddMaterialCallback = void Function(String nodeId, String label);
typedef NodeGenerateLearningPlanCallback = void Function(
  String nodeId,
  String nodeLabel,
);

class NodeDetailSheet extends ConsumerStatefulWidget {
  const NodeDetailSheet({
    required this.nodeId,
    required this.nodeLabel,
    this.packId,
    this.initialHistory,
    this.onStartReview,
    this.onViewErrors,
    this.onAddMaterial,
    this.onGenerateLearningPlan,
    super.key,
  });

  final String nodeId;
  final String nodeLabel;
  final String? packId;
  final GalaxyNodeHistory? initialHistory;
  final NodeReviewContextCallback? onStartReview;
  final NodeErrorFilterCallback? onViewErrors;
  final NodeAddMaterialCallback? onAddMaterial;
  final NodeGenerateLearningPlanCallback? onGenerateLearningPlan;

  static Future<void> show({
    required BuildContext context,
    required String nodeId,
    required String nodeLabel,
    String? packId,
    NodeAddMaterialCallback? onAddMaterial,
    NodeGenerateLearningPlanCallback? onGenerateLearningPlan,
  }) =>
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        barrierColor: Colors.black.withValues(alpha: 0.1),
        builder: (context) => NodeDetailSheet(
          nodeId: nodeId,
          nodeLabel: nodeLabel,
          packId: packId,
          onAddMaterial: onAddMaterial,
          onGenerateLearningPlan: onGenerateLearningPlan,
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
                  onAddMaterial: _handleAddMaterial,
                  onGenerateLearningPlan: _handleGenerateLearningPlan,
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
                      onAddMaterial: _handleAddMaterial,
                      onGenerateLearningPlan: _handleGenerateLearningPlan,
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
        'prompt': context.l10n.galaxyNodeReviewPrompt(label),
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

  void _handleAddMaterial(GalaxyNodeHistory history) {
    final callback = widget.onAddMaterial;
    if (callback == null) {
      return;
    }
    final label = _effectiveLabel(history);
    Navigator.of(context).pop();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      callback(widget.nodeId, label);
    });
  }

  void _handleGenerateLearningPlan(String nodeId, String label) {
    final callback = widget.onGenerateLearningPlan;
    if (callback != null) {
      callback(nodeId, label);
      return;
    }
    // Default: Navigate to learning path dialog
    Navigator.of(context).pop();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final router = GoRouter.of(context);
      router.push(
        Uri(
          path: '/learning-path',
          queryParameters: {
            'node_id': nodeId,
            'node_label': label,
          },
        ).toString(),
      );
    });
  }

  String _effectiveLabel(GalaxyNodeHistory history) =>
      widget.nodeLabel.trim().isNotEmpty
          ? widget.nodeLabel.trim()
          : history.nodeLabel;

  Map<String, dynamic> _reviewErrorContext(GalaxyNodeErrorItem error) =>
      <String, dynamic>{
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

class _HistoryContent extends StatelessWidget {
  const _HistoryContent({
    required this.history,
    required this.fallbackLabel,
    required this.nodeId,
    required this.onStartReview,
    required this.onViewErrors,
    required this.onAddMaterial,
    required this.onGenerateLearningPlan,
  });

  final GalaxyNodeHistory history;
  final String fallbackLabel;
  final String nodeId;
  final void Function(GalaxyNodeHistory history) onStartReview;
  final void Function(GalaxyNodeHistory history) onViewErrors;
  final void Function(GalaxyNodeHistory history) onAddMaterial;
  final void Function(String nodeId, String label) onGenerateLearningPlan;

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
                context.l10n.galaxyNodeMastery,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: DS.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const Spacer(),
              Text(
                history.mastery <= 0
                    ? context.l10n.galaxyNodeNotLearned
                    : '$percent%',
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
                    ? context.l10n.galaxyNodeStudiedCount(history.studyCount)
                    : context.l10n.galaxyNodeNotLearned,
              ),
              _MetricChip(
                icon: Icons.schedule_rounded,
                label: history.lastStudiedAt == null
                    ? context.l10n.galaxyNodeNoRecord
                    : context.l10n.galaxyNodeLastStudy(
                        _relativeTime(history.lastStudiedAt!, context.l10n)),
              ),
              _MetricChip(
                icon: Icons.assignment_late_rounded,
                label: context.l10n
                    .galaxyNodeRelatedErrors(history.relatedErrors.length),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),
          _SourceMaterialsSection(nodeId: nodeId, nodeLabel: label),
          const SizedBox(height: DS.spacing20),
          Text(
            context.l10n.galaxyNodeRecentErrors,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: DS.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: DS.spacing10),
          if (relatedErrors.isEmpty)
            Text(
              context.l10n.galaxyNodeNoRelatedErrors,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: DS.textSecondary,
                  ),
            )
          else
            ...relatedErrors.map(_ErrorPreview.new),
          const SizedBox(height: DS.spacing20),
          _FocusReasonSection(nodeId: nodeId, mastery: history.mastery),
          const SizedBox(height: DS.spacing20),
          _CommunityInsightSection(nodeId: nodeId),
          const SizedBox(height: DS.spacing20),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: () {
                    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
                    onStartReview(history);
                  },
                  icon: Icon(
                    history.mastery <= 0
                        ? Icons.school_rounded
                        : Icons.play_arrow_rounded,
                  ),
                  label: Text(history.mastery <= 0
                      ? context.l10n.galaxyNodeStartLearn
                      : context.l10n.galaxyNodeStartReview),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
                    onViewErrors(history);
                  },
                  icon: const Icon(Icons.assignment_rounded),
                  label: Text(context.l10n.galaxyNodeViewErrors),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () {
                unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
                onAddMaterial(history);
              },
              icon: const Icon(Icons.menu_book_rounded),
              label: Text(context.l10n.galaxyNodeAddMaterial),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.tonalIcon(
              onPressed: () {
                unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
                onGenerateLearningPlan(nodeId, label);
              },
              icon: const Icon(Icons.route_rounded),
              label: Text(context.l10n.galaxyNodeGeneratePlan),
            ),
          ),
        ],
      ),
    );
  }

  static String _relativeTime(DateTime dateTime, AppLocalizations l10n) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inDays >= 1) {
      return l10n.galaxyNodeDaysAgo(diff.inDays);
    }
    if (diff.inHours >= 1) {
      return l10n.galaxyNodeHoursAgo(diff.inHours);
    }
    if (diff.inMinutes >= 1) {
      return l10n.galaxyNodeMinutesAgo(diff.inMinutes);
    }
    return l10n.galaxyNodeJustNow;
  }
}

class _SourceMaterialsSection extends ConsumerStatefulWidget {
  const _SourceMaterialsSection({
    required this.nodeId,
    required this.nodeLabel,
  });

  final String nodeId;
  final String nodeLabel;

  @override
  ConsumerState<_SourceMaterialsSection> createState() =>
      _SourceMaterialsSectionState();
}

class _SourceMaterialsSectionState
    extends ConsumerState<_SourceMaterialsSection> {
  final Set<String> _expandedFileIds = <String>{};

  @override
  Widget build(BuildContext context) {
    final asyncValue = ref.watch(nodeSourceMaterialsProvider(widget.nodeId));
    return TweenAnimationBuilder<double>(
      duration: const Duration(milliseconds: 320),
      curve: Curves.easeOutCubic,
      tween: Tween<double>(begin: 0, end: 1),
      builder: (context, value, child) => Opacity(
        opacity: value,
        child: Transform.translate(
          offset: Offset(0, 14 * (1 - value)),
          child: child,
        ),
      ),
      child: asyncValue.when(
        loading: () => const _SourceMaterialsLoadingState(),
        error: (_, __) => _SourceMaterialsErrorState(
          onRetry: () =>
              ref.invalidate(nodeSourceMaterialsProvider(widget.nodeId)),
        ),
        data: (data) => _buildLoadedState(context, data),
      ),
    );
  }

  Widget _buildLoadedState(
    BuildContext context,
    NodeSourceMaterialsViewData data,
  ) {
    final copy = _SourceMaterialsCopy.of(context);
    final docs = data.documents;
    final stats = data.knowledgeStats;
    final totalDocuments =
        stats.totalDocuments > 0 ? stats.totalDocuments : docs.length;
    final totalChunks = stats.totalChunks > 0
        ? stats.totalChunks
        : docs.fold<int>(
            0,
            (sum, document) => sum + document.document.chunkCount,
          );
    final hasPersonalUploads = data.hasPersonalUploads;
    final accent = hasPersonalUploads ? DS.brandPrimary : DS.textSecondary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          copy.title,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: DS.spacing10),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing14),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                accent.withValues(alpha: hasPersonalUploads ? 0.16 : 0.08),
                DS.surfacePanel,
              ],
            ),
            borderRadius: BorderRadius.circular(DS.radius12),
            border: Border.all(
              color: accent.withValues(alpha: hasPersonalUploads ? 0.24 : 0.14),
            ),
            boxShadow: hasPersonalUploads
                ? [
                    BoxShadow(
                      color: accent.withValues(alpha: 0.12),
                      blurRadius: 18,
                      offset: const Offset(0, 8),
                    ),
                  ]
                : null,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _DocumentStackBadge(count: totalDocuments, accent: accent),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      copy.summary(totalDocuments, totalChunks),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      hasPersonalUploads
                          ? copy.personalBadge
                          : copy.systemBadge,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                    ),
                    if (stats.lastMaterialAdded != null) ...[
                      const SizedBox(height: DS.spacing6),
                      Text(
                        copy.uploadDate(_formatDate(stats.lastMaterialAdded!)),
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: DS.textTertiary,
                            ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        if (docs.isEmpty) ...[
          const SizedBox(height: DS.spacing12),
          _SourceMaterialsEmptyState(
            copy: copy,
            nodeLabel: widget.nodeLabel,
            onAddNotes: _openUploadFlow,
          ),
        ] else ...[
          const SizedBox(height: DS.spacing12),
          _LayeredDocumentList(
            documentCount: docs.length,
            accent: accent,
            child: Column(
              children: docs
                  .map(
                    (document) => Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing10),
                      child: _buildDocumentCard(context, copy, document),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildDocumentCard(
    BuildContext context,
    _SourceMaterialsCopy copy,
    NodeSourceDocumentViewData data,
  ) {
    final document = data.document;
    final isExpanded = _expandedFileIds.contains(document.fileId);
    final accent = _documentAccent(document);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(
          color: accent.withValues(alpha: isExpanded ? 0.34 : 0.18),
        ),
        boxShadow: [
          BoxShadow(
            color: accent.withValues(alpha: isExpanded ? 0.14 : 0.08),
            blurRadius: isExpanded ? 20 : 12,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () => _toggleExpanded(document.fileId),
            borderRadius: BorderRadius.circular(DS.radius12),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(DS.spacing10),
                    ),
                    child: Icon(
                      _documentIcon(document),
                      color: accent,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                document.filename,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodyMedium
                                    ?.copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                            ),
                            const SizedBox(width: DS.spacing8),
                            _PillLabel(
                              label: copy.personalBadge,
                              color: accent,
                            ),
                          ],
                        ),
                        const SizedBox(height: DS.spacing6),
                        Wrap(
                          spacing: DS.spacing8,
                          runSpacing: DS.spacing8,
                          children: [
                            if (document.uploadDate != null)
                              Text(
                                copy.uploadDate(
                                  _formatDate(document.uploadDate!),
                                ),
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(color: DS.textTertiary),
                              ),
                            _PillLabel(
                              label: '${document.chunkCount} ${copy.chunkUnit}',
                              color: DS.info,
                              fill: DS.info.withValues(alpha: 0.10),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Icon(
                    isExpanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: DS.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          ClipRect(
            child: AnimatedSize(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOutCubic,
              child: isExpanded
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(
                        DS.spacing12,
                        0,
                        DS.spacing12,
                        DS.spacing12,
                      ),
                      child: Column(
                        children: [
                          Divider(height: 1, color: DS.borderSubtle),
                          const SizedBox(height: DS.spacing12),
                          if (data.excerpts.isEmpty)
                            _SourceMaterialsMutedMessage(
                              message: copy.noPreview,
                            )
                          else
                            ...data.excerpts.map(
                              (excerpt) => Padding(
                                padding: const EdgeInsets.only(
                                  bottom: DS.spacing10,
                                ),
                                child: _DocumentExcerptCard(
                                  copy: copy,
                                  excerpt: excerpt,
                                  onReadMore: () =>
                                      _openSourceDocument(document, excerpt),
                                ),
                              ),
                            ),
                        ],
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
          ),
        ],
      ),
    );
  }

  void _toggleExpanded(String fileId) {
    setState(() {
      if (_expandedFileIds.contains(fileId)) {
        _expandedFileIds.remove(fileId);
      } else {
        _expandedFileIds.add(fileId);
      }
    });
  }

  Future<void> _openUploadFlow() async {
    final copy = _SourceMaterialsCopy.of(context);
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (context) => FilePickerWithPresignedUpload(
        onUploaded: (file) {
          Navigator.of(context).pop();
          ref.invalidate(nodeSourceMaterialsProvider(widget.nodeId));
          AppFeedback.success(
            this.context,
            copy.uploadSaved(file.fileName),
          );
        },
        onError: (message) => AppFeedback.error(this.context, message),
      ),
    );
  }

  Future<void> _openSourceDocument(
    NodeSourceDocumentRef document,
    NodeSourceExcerptViewData excerpt,
  ) async {
    final copy = _SourceMaterialsCopy.of(context);
    try {
      final presigned = await ref
          .read(fileRepositoryProvider)
          .getDownloadUrl(document.fileId);
      if (!mounted) {
        return;
      }
      final uri = Uri.tryParse(presigned.url);
      if (uri == null) {
        AppFeedback.error(context, copy.openFailed);
        return;
      }
      await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!mounted) {
        return;
      }
      if (excerpt.pageNumbers.isNotEmpty ||
          (excerpt.sectionTitle?.trim().isNotEmpty ?? false)) {
        AppFeedback.info(
          context,
          _buildExcerptReferenceLabel(copy, excerpt),
        );
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, copy.openFailed);
    }
  }
}

class _LayeredDocumentList extends StatelessWidget {
  const _LayeredDocumentList({
    required this.documentCount,
    required this.accent,
    required this.child,
  });

  final int documentCount;
  final Color accent;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (documentCount <= 1) {
      return child;
    }

    final hasThirdLayer = documentCount > 2;
    return Stack(
      children: [
        Positioned(
          top: hasThirdLayer ? 18 : 12,
          left: hasThirdLayer ? 14 : 10,
          right: hasThirdLayer ? 14 : 10,
          child: _StackLayer(
            accent: accent,
            opacity: hasThirdLayer ? 0.09 : 0.12,
          ),
        ),
        if (hasThirdLayer)
          Positioned(
            top: 9,
            left: 8,
            right: 8,
            child: _StackLayer(
              accent: accent,
              opacity: 0.14,
            ),
          ),
        Padding(
          padding: EdgeInsets.only(top: hasThirdLayer ? 24 : 14),
          child: child,
        ),
      ],
    );
  }
}

class _StackLayer extends StatelessWidget {
  const _StackLayer({
    required this.accent,
    required this.opacity,
  });

  final Color accent;
  final double opacity;

  @override
  Widget build(BuildContext context) => Container(
        height: 74,
        decoration: BoxDecoration(
          color: accent.withValues(alpha: opacity),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(
            color: accent.withValues(alpha: opacity + 0.08),
          ),
        ),
      );
}

class _DocumentStackBadge extends StatelessWidget {
  const _DocumentStackBadge({
    required this.count,
    required this.accent,
  });

  final int count;
  final Color accent;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 52,
        height: 52,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            if (count > 2)
              Positioned(
                left: 10,
                top: 10,
                child: _BadgeLayer(
                  size: 30,
                  color: accent.withValues(alpha: 0.18),
                ),
              ),
            if (count > 1)
              Positioned(
                left: 5,
                top: 5,
                child: _BadgeLayer(
                  size: 34,
                  color: accent.withValues(alpha: 0.24),
                ),
              ),
            _BadgeLayer(
              size: 40,
              color: accent.withValues(alpha: 0.14),
              child: Icon(
                Icons.library_books_rounded,
                color: accent,
                size: 20,
              ),
            ),
          ],
        ),
      );
}

class _BadgeLayer extends StatelessWidget {
  const _BadgeLayer({
    required this.size,
    required this.color,
    this.child,
  });

  final double size;
  final Color color;
  final Widget? child;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withValues(alpha: 0.8)),
        ),
        child: child == null ? null : Center(child: child),
      );
}

class _SourceMaterialsEmptyState extends StatelessWidget {
  _SourceMaterialsEmptyState({
    required this.copy,
    required this.nodeLabel,
    required this.onAddNotes,
  });

  final _SourceMaterialsCopy copy;
  final String nodeLabel;
  final Future<void> Function() onAddNotes;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing14),
        decoration: BoxDecoration(
          color: DS.surfacePanel,
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              copy.emptyTitle,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              copy.emptyBody(nodeLabel),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                    height: 1.5,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            OutlinedButton.icon(
              onPressed: onAddNotes,
              icon: const Icon(Icons.upload_file_rounded),
              label: Text(copy.addNotes(nodeLabel)),
            ),
          ],
        ),
      );
}

class _DocumentExcerptCard extends StatelessWidget {
  _DocumentExcerptCard({
    required this.copy,
    required this.excerpt,
    required this.onReadMore,
  });

  final _SourceMaterialsCopy copy;
  final NodeSourceExcerptViewData excerpt;
  final VoidCallback onReadMore;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(DS.spacing10),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              excerpt.preview,
              maxLines: 4,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textPrimary,
                    height: 1.55,
                  ),
            ),
            const SizedBox(height: DS.spacing10),
            Row(
              children: [
                Expanded(
                  child: Text(
                    _buildExcerptReferenceLabel(copy, excerpt),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: DS.textTertiary,
                        ),
                  ),
                ),
                TextButton(
                  onPressed: onReadMore,
                  child: Text(copy.readMore),
                ),
              ],
            ),
          ],
        ),
      );
}

class _SourceMaterialsMutedMessage extends StatelessWidget {
  const _SourceMaterialsMutedMessage({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(DS.spacing10),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          message,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.textSecondary,
              ),
        ),
      );
}

class _SourceMaterialsLoadingState extends StatelessWidget {
  const _SourceMaterialsLoadingState();

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 128,
            height: 18,
            decoration: BoxDecoration(
              color: DS.surfaceTertiary,
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Container(
            width: double.infinity,
            height: 98,
            decoration: BoxDecoration(
              color: DS.surfacePanel,
              borderRadius: BorderRadius.circular(DS.radius12),
              border: Border.all(color: DS.borderSubtle),
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Container(
            width: double.infinity,
            height: 88,
            decoration: BoxDecoration(
              color: DS.surfacePanel,
              borderRadius: BorderRadius.circular(DS.radius12),
              border: Border.all(color: DS.borderSubtle),
            ),
          ),
        ],
      );
}

class _SourceMaterialsErrorState extends StatelessWidget {
  const _SourceMaterialsErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final copy = _SourceMaterialsCopy.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: BorderRadius.circular(DS.radius12),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        children: [
          Icon(Icons.library_books_outlined, color: DS.textSecondary),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Text(
              copy.openFailed,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ),
          TextButton(
            onPressed: onRetry,
            child: Text(copy.retry),
          ),
        ],
      ),
    );
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

class _PillLabel extends StatelessWidget {
  const _PillLabel({
    required this.label,
    required this.color,
    this.fill,
  });

  final String label;
  final Color color;
  final Color? fill;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: fill ?? color.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
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
        : context.l10n.galaxyNodeImageError;
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
              context.l10n.galaxyNodeHistoryFailed,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: DS.spacing12),
            TextButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: Text(context.l10n.galaxyNodeRetry),
            ),
          ],
        ),
      );
}

class _SourceMaterialsCopy {
  _SourceMaterialsCopy._(this.l10n);

  factory _SourceMaterialsCopy.of(BuildContext context) =>
      _SourceMaterialsCopy._(context.l10n);

  final AppLocalizations l10n;

  String get title => l10n.galaxyNodeSourceAssets;
  String get personalBadge => l10n.galaxyNodePersonalBadge;
  String get systemBadge => l10n.galaxyNodeNoPersonalNote;
  String get chunkUnit => l10n.galaxyNodeChunkUnit;
  String get emptyTitle => l10n.galaxyNodeEmptySourceTitle;
  String get readMore => l10n.galaxyNodeReadMore;
  String get noPreview => l10n.galaxyNodeNoPreview;
  String get openFailed => l10n.galaxyNodeOpenFailed;
  String get retry => l10n.galaxyNodeRetry;

  String summary(int documents, int chunks) =>
      l10n.galaxyNodeSourceSummary(documents, chunks);

  String uploadDate(String date) =>
      '${l10n.galaxyNodeUploadDateLabel} $date';

  String emptyBody(String topic) {
    if (topic.trim().isEmpty) return l10n.galaxyNodeEmptySourceBody;
    return l10n.galaxyNodeSourceEmptyBody(topic);
  }

  String addNotes(String topic) {
    if (topic.trim().isEmpty) return l10n.galaxyNodeAddNotesLabel;
    return l10n.galaxyNodeSourceAddNotes(topic);
  }

  String uploadSaved(String filename) =>
      l10n.galaxyNodeSourceUploadSaved(filename);

  String page(int number) => l10n.galaxyNodeSourcePage(number);

  String pages(String pages) => l10n.galaxyNodeSourcePages(pages);

  String excerpt(int index) => l10n.galaxyNodeSourceExcerpt(index);
}

IconData _documentIcon(NodeSourceDocumentRef document) {
  switch (document.normalizedFileType) {
    case 'pdf':
      return Icons.picture_as_pdf_outlined;
    case 'docx':
      return Icons.description_outlined;
    case 'pptx':
      return Icons.slideshow_outlined;
    case 'md':
      return Icons.article_outlined;
    case 'image':
      return Icons.image_outlined;
    default:
      return Icons.insert_drive_file_outlined;
  }
}

Color _documentAccent(NodeSourceDocumentRef document) {
  switch (document.normalizedFileType) {
    case 'pdf':
      return DS.error;
    case 'docx':
      return DS.info;
    case 'pptx':
      return DS.warning;
    case 'md':
      return DS.success;
    case 'image':
      return DS.brandSecondary;
    default:
      return DS.brandPrimary;
  }
}

String _formatDate(DateTime date) {
  final month = date.month.toString().padLeft(2, '0');
  final day = date.day.toString().padLeft(2, '0');
  return '${date.year}-$month-$day';
}

String _buildExcerptReferenceLabel(
  _SourceMaterialsCopy copy,
  NodeSourceExcerptViewData excerpt,
) {
  final parts = <String>[];
  if (excerpt.pageNumbers.isNotEmpty) {
    parts.add(
      excerpt.pageNumbers.length == 1
          ? copy.page(excerpt.pageNumbers.first)
          : copy.pages(excerpt.pageNumbers.join(', ')),
    );
  }
  final sectionTitle = excerpt.sectionTitle?.trim();
  if (sectionTitle != null && sectionTitle.isNotEmpty) {
    parts.add(sectionTitle);
  }
  if (parts.isEmpty) {
    parts.add(copy.excerpt(excerpt.fallbackOrdinal));
  }
  return parts.join(' · ');
}

/// KG-009: "Why is this node prioritized today?" explainable path section.
class _FocusReasonSection extends StatelessWidget {
  const _FocusReasonSection({required this.nodeId, required this.mastery});

  final String nodeId;
  final double mastery;

  @override
  Widget build(BuildContext context) {
    final reason = _computeReason(context, mastery);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.lightbulb_outline_rounded,
                size: DS.iconSizeSm, color: DS.warning),
            const SizedBox(width: DS.spacing8),
            Text(
              context.l10n.galaxyNodeWhyToday,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing12),
          decoration: BoxDecoration(
            color: DS.warning.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(DS.radius8),
            border: Border.all(color: DS.warning.withValues(alpha: 0.15)),
          ),
          child: Text(
            reason,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: DS.textSecondary),
          ),
        ),
      ],
    );
  }

  String _computeReason(BuildContext context, double m) {
    final l10n = context.l10n;
    if (m <= 0) return l10n.galaxyNodeReasonNew;
    if (m < 0.3) return l10n.galaxyNodeReasonEarly;
    if (m < 0.7) return l10n.galaxyNodeReasonMid;
    return l10n.galaxyNodeReasonLate;
  }
}

class _CommunityInsightSection extends ConsumerWidget {
  const _CommunityInsightSection({required this.nodeId});

  final String nodeId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          context.l10n.galaxyNodeCommunityInsights,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: DS.spacing10),
        _CommunityInsightContent(nodeId: nodeId),
      ],
    );
  }
}

class _CommunityInsightContent extends ConsumerStatefulWidget {
  const _CommunityInsightContent({required this.nodeId});

  final String nodeId;

  @override
  ConsumerState<_CommunityInsightContent> createState() =>
      _CommunityInsightContentState();
}

class _CommunityInsightContentState
    extends ConsumerState<_CommunityInsightContent> {
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>?>(
      future: _fetchCommunitySignal(),
      builder: (context, snapshot) {
        if (!snapshot.hasData || snapshot.data == null) {
          return Text(
            context.l10n.galaxyNodeCommunityNoData,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: DS.textSecondary),
          );
        }
        final signal = snapshot.data!;
        final patterns = signal['common_mistake_patterns'] as List? ?? [];
        if (patterns.isEmpty) {
          return Text(
            context.l10n.galaxyNodeCommunityNoData,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: DS.textSecondary),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: patterns.take(3).map((pattern) {
            final p = pattern as Map<String, dynamic>;
            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                children: [
                  Icon(Icons.group_outlined, size: 14, color: DS.brandPrimary),
                  const SizedBox(width: DS.spacing6),
                  Expanded(
                    child: Text(
                      context.l10n.galaxyNodeCommunityPattern(
                        p['error_type']?.toString() ??
                            context.l10n.galaxyNodeCommunityUnknown,
                        p['user_count'].toString(),
                      ),
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: DS.textSecondary),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        );
      },
    );
  }

  Future<Map<String, dynamic>?> _fetchCommunitySignal() async {
    try {
      final detailResult = await ref
          .read(enhancedGalaxyRepositoryProvider)
          .getNodeDetail(widget.nodeId);
      if (detailResult.isSuccess && detailResult.data != null) {
        return detailResult.data!.node.communitySignal;
      }
      return null;
    } catch (e) {
      debugPrint('Error fetching community signal: $e');
      return null;
    }
  }
}
