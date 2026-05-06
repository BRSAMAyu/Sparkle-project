import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/remediable_patterns_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

/// Error list page.
///
/// Design notes:
/// 1. Flexible filters across subject, chapter, mastery, and due reviews.
/// 2. Clear loading, empty, and error states.
/// 3. Paged loading and swipe deletion for performance.
class ErrorListScreen extends ConsumerStatefulWidget {
  const ErrorListScreen({
    super.key,
    this.filterByDimension,
    this.filterByNodeId,
    this.filterByNodeLabel,
  });
  final CognitiveDimension? filterByDimension;
  final String? filterByNodeId;
  final String? filterByNodeLabel;

  @override
  ConsumerState<ErrorListScreen> createState() => _ErrorListScreenState();
}

class _ErrorListScreenState extends ConsumerState<ErrorListScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _searchController = TextEditingController();
  bool _showSearch = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);

    // Apply the initial cognitive dimension filter when provided.
    if (widget.filterByDimension != null) {
      ref
          .read(errorFilterProvider.notifier)
          .setCognitiveDimension(widget.filterByDimension);
    }
    final nodeId = widget.filterByNodeId?.trim();
    if (nodeId != null && nodeId.isNotEmpty) {
      ref
          .read(errorFilterProvider.notifier)
          .setNodeFilter(nodeId, widget.filterByNodeLabel);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final filterState = ref.watch(errorFilterProvider);
    final hasAdvancedFilters =
        (filterState.chapterFilter?.trim().isNotEmpty ?? false) ||
            (filterState.nodeId?.trim().isNotEmpty ?? false) ||
            filterState.showOnlyNeedReview ||
            filterState.cognitiveDimension != null;

    // Build query parameters.
    final query = filterState.toQuery();

    // Fetch error records.
    final errorListAsync = ref.watch(errorListProvider(query));

    // Fetch statistics.
    final statsAsync = ref.watch(errorStatsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: _showSearch
            ? _buildSearchField()
            : Text(context.l10n.errorBookTitle),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: Icon(_showSearch ? Icons.close : Icons.search),
            onPressed: () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
              );
              setState(() {
                _showSearch = !_showSearch;
                if (!_showSearch) {
                  _searchController.clear();
                  ref.read(errorFilterProvider.notifier).setSearchKeyword('');
                }
              });
            },
          ),
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: Icon(
              Icons.filter_list,
              color: hasAdvancedFilters ? theme.colorScheme.primary : null,
            ),
            onPressed: () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
              );
              unawaited(_showFilterDialog(context));
            },
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(context.l10n.errorBookTabAll),
                  const SizedBox(width: DS.spacing8),
                  _buildStatsBadge(statsAsync, 'total'),
                ],
              ),
            ),
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(context.l10n.errorBookTabNeedReview),
                  const SizedBox(width: DS.spacing8),
                  _buildStatsBadge(statsAsync, 'needReview'),
                ],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
          unawaited(_navigateToAddError(context));
        },
        icon: const Icon(Icons.add),
        label: Text(context.l10n.errorBookAddError),
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            // Show a filter hint when a cognitive dimension is active.
            if (filterState.cognitiveDimension != null)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing8,
                ),
                color:
                    theme.colorScheme.primaryContainer.withValues(alpha: 0.3),
                child: Row(
                  children: [
                    Icon(
                      Icons.psychology,
                      size: 16,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: DS.spacing8),
                    Text(
                      context.l10n.errorBookCognitiveFilter(
                        filterState.cognitiveDimension!.label,
                      ),
                      style: TextStyle(
                        color: theme.colorScheme.primary,
                        fontWeight: DS.fontWeightBold,
                        fontSize: 12,
                      ),
                    ),
                    const Spacer(),
                    InkWell(
                      onTap: () => ref
                          .read(errorFilterProvider.notifier)
                          .setCognitiveDimension(null),
                      borderRadius: DS.borderRadiusFull,
                      child: const Padding(
                        padding: EdgeInsets.all(DS.spacing4),
                        child: Icon(Icons.close, size: DS.iconSizeXs),
                      ),
                    ),
                  ],
                ),
              ),

            if (filterState.nodeId != null)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing8,
                ),
                color:
                    theme.colorScheme.secondaryContainer.withValues(alpha: 0.3),
                child: Row(
                  children: [
                    Icon(
                      Icons.hub_rounded,
                      size: 16,
                      color: theme.colorScheme.secondary,
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        context.l10n.errorBookKnowledgePointFilter(
                          filterState.nodeLabel ?? filterState.nodeId!,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: theme.colorScheme.secondary,
                          fontWeight: DS.fontWeightBold,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    InkWell(
                      onTap: () =>
                          ref.read(errorFilterProvider.notifier).reset(),
                      borderRadius: DS.borderRadiusFull,
                      child: const Padding(
                        padding: EdgeInsets.all(DS.spacing4),
                        child: Icon(Icons.close, size: DS.iconSizeXs),
                      ),
                    ),
                  ],
                ),
              ),

            // Subject filter bar.
            ColoredBox(
              color: theme.colorScheme.surface,
              child: Column(
                children: [
                  const SizedBox(height: DS.spacing12),
                  SubjectFilterChips(
                    selectedSubject: filterState.selectedSubject,
                    onSelected: (subject) {
                      ref
                          .read(errorFilterProvider.notifier)
                          .setSubject(subject);
                    },
                  ),
                  const SizedBox(height: DS.spacing12),
                ],
              ),
            ),
            const RemediablePatternsCard(),

            // List content.
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // All errors.
                  _buildErrorList(errorListAsync, query),

                  // Errors due for review.
                  _buildErrorList(
                    ref.watch(
                      errorListProvider(
                        query.copyWith(needReview: true),
                      ),
                    ),
                    query.copyWith(needReview: true),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchField() => Builder(
        builder: (context) => TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: context.l10n.errorBookSearchHint,
            border: InputBorder.none,
          ),
          onChanged: (value) {
            // Debounced search.
            unawaited(
              Future.delayed(
                const Duration(milliseconds: 500),
                () {
                  if (value == _searchController.text) {
                    ref
                        .read(errorFilterProvider.notifier)
                        .setSearchKeyword(value);
                  }
                },
              ),
            );
          },
        ),
      );

  Widget _buildStatsBadge(AsyncValue<ReviewStats> statsAsync, String type) =>
      statsAsync.when(
        data: (stats) {
          final count =
              type == 'total' ? stats.totalErrors : stats.needReviewCount;

          if (count == 0) return const SizedBox.shrink();

          return Container(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing6,
              vertical: 2,
            ),
            decoration: BoxDecoration(
              color: type == 'needReview'
                  ? DS.error
                  : Theme.of(context).colorScheme.primary,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              count.toString(),
              style: TextStyle(
                color: DS.textOnPrimary,
                fontSize: 11,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          );
        },
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const CompactErrorCard(),
      );

  Widget _buildErrorList(
    AsyncValue<ErrorListResponse> errorListAsync,
    ErrorListQuery query,
  ) =>
      errorListAsync.when(
        data: (response) {
          if (response.items.isEmpty) {
            return _buildEmptyState(query.needReview ?? false);
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(errorListProvider(query));
            },
            child: ListView.builder(
              padding: const EdgeInsets.only(bottom: 80),
              itemCount: response.items.length,
              itemBuilder: (context, index) {
                final error = response.items[index];
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    ErrorCard(
                      error: error,
                      onTap: () => _navigateToDetail(context, error.id),
                      onKnowledgeNodeTap: (nodeId, masteryDelta) =>
                          _navigateToGalaxyNode(context, nodeId, masteryDelta),
                      onDelete: () => _deleteError(error.id),
                    ),
                    if (_shouldShowLinkingHint(error))
                      _buildLinkingHintCard(error.latestAnalysis!.linkingHint!),
                  ],
                );
              },
            ),
          );
        },
        loading: () => const SparkleListSkeleton(),
        error: (error, stack) => _buildErrorState(error.toString(), query),
      );

  bool _shouldShowLinkingHint(ErrorRecord error) {
    final affectedNodeId = error.affectedNodeId?.trim();
    return error.knowledgeLinks.isEmpty &&
        (affectedNodeId == null || affectedNodeId.isEmpty) &&
        error.latestAnalysis?.linkingHint != null;
  }

  Widget _buildLinkingHintCard(ErrorLinkingHint hint) => Builder(
        builder: (context) {
          final theme = Theme.of(context);
          return Card(
            margin: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing8,
            ),
            color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.45),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.account_tree_outlined,
                    color: theme.colorScheme.onSecondaryContainer,
                    size: 20,
                  ),
                  const SizedBox(width: DS.spacing10),
                  Expanded(
                    child: Text(
                      hint.message,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );

  Widget _buildEmptyState(bool isReviewTab) => Builder(
        builder: (context) => EmptyState(
          icon: isReviewTab ? Icons.check_circle_outline : Icons.inbox_outlined,
          title: isReviewTab
              ? context.l10n.errorBookNoReview
              : context.l10n.errorBookNoErrors,
          description: isReviewTab
              ? context.l10n.errorBookNoReviewDescription
              : context.l10n.errorBookNoErrorsHint,
          actionText: isReviewTab
              ? context.l10n.errorBookRecordFirstError
              : context.l10n.errorBookAddFirst,
          onAction: () => _navigateToAddError(context),
        ),
      );

  Widget _buildErrorState(String error, ErrorListQuery query) => Builder(
        builder: (context) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline,
                size: 80,
                color: DS.error,
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.loadingFailed(error),
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                error,
                style: TextStyle(
                  fontSize: 14,
                  color: DS.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing24),
              FilledButton.icon(
                onPressed: () {
                  ref.invalidate(errorListProvider(query));
                },
                icon: const Icon(Icons.refresh),
                label: Text(context.l10n.commonRetry),
              ),
            ],
          ),
        ),
      );

  Future<void> _navigateToAddError(BuildContext context) async {
    final result = await context.push<bool>('/errors/new');

    if ((result ?? false) && mounted) {
      // Refresh the list.
      ref
        ..invalidate(errorListProvider)
        ..invalidate(errorStatsProvider);
    }
  }

  Future<void> _navigateToDetail(BuildContext context, String errorId) async {
    await context.push('/errors/$errorId');

    // Details may update the record, so refresh on return.
    if (mounted) {
      ref
        ..invalidate(errorListProvider)
        ..invalidate(errorStatsProvider);
    }
  }

  void _navigateToGalaxyNode(
    BuildContext context,
    String nodeId,
    double? masteryDelta,
  ) {
    final uri = Uri(
      path: GalaxyRoutes.home,
      queryParameters: {
        'focus_node_id': nodeId,
        if (masteryDelta != null) 'mastery_delta': masteryDelta.toString(),
      },
    );
    context.go(uri.toString());
  }

  Future<void> _deleteError(String errorId) async {
    try {
      await ref.read(errorOperationsProvider.notifier).deleteError(errorId);

      if (mounted) {
        AppFeedback.success(context, context.l10n.errorBookDeleteSuccess);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '${context.l10n.errorBookDeleteFailed}: $e');
      }
    }
  }

  Future<void> _showFilterDialog(BuildContext context) async {
    final current = ref.read(errorFilterProvider);
    final chapterController = TextEditingController(
      text: current.chapterFilter ?? '',
    );
    var needReviewOnly = current.showOnlyNeedReview;
    var cognitiveDimension = current.cognitiveDimension;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: Text(context.l10n.errorBookFilterTitle),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: chapterController,
                  decoration: InputDecoration(
                    labelText: context.l10n.ebChapter,
                    hintText: context.l10n.ebChapterFilterHint,
                    prefixIcon: const Icon(Icons.folder_outlined),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                SwitchListTile.adaptive(
                  value: needReviewOnly,
                  contentPadding: EdgeInsets.zero,
                  title: Text(context.l10n.ebShowDueOnly),
                  subtitle: Text(context.l10n.ebShowDueDesc),
                  onChanged: (value) {
                    setDialogState(() {
                      needReviewOnly = value;
                    });
                  },
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  context.l10n.errorBookCognitiveDimension,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    FilterChip(
                      label: Text(context.l10n.ebAll),
                      selected: cognitiveDimension == null,
                      onSelected: (_) {
                        setDialogState(() {
                          cognitiveDimension = null;
                        });
                      },
                    ),
                    ...CognitiveDimension.values.map(
                      (dimension) => FilterChip(
                        label: Text(dimension.label),
                        selected: cognitiveDimension == dimension,
                        onSelected: (_) {
                          setDialogState(() {
                            cognitiveDimension = cognitiveDimension == dimension
                                ? null
                                : dimension;
                          });
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            SparkleButton.ghost(
              onPressed: () {
                setDialogState(() {
                  chapterController.clear();
                  needReviewOnly = false;
                  cognitiveDimension = null;
                });
              },
              label: context.l10n.commonReset,
            ),
            SparkleButton.ghost(
              onPressed: () => Navigator.of(dialogContext).pop(),
              label: context.l10n.cancel,
            ),
            FilledButton(
              onPressed: () {
                ref.read(errorFilterProvider.notifier)
                  ..setChapter(
                    chapterController.text.trim().isEmpty
                        ? null
                        : chapterController.text.trim(),
                  )
                  ..setCognitiveDimension(cognitiveDimension);
                final currentNeedReview =
                    ref.read(errorFilterProvider).showOnlyNeedReview;
                if (currentNeedReview != needReviewOnly) {
                  ref.read(errorFilterProvider.notifier).toggleNeedReview();
                }
                Navigator.of(dialogContext).pop();
              },
              child: Text(context.l10n.confirm),
            ),
          ],
        ),
      ),
    );
    chapterController.dispose();
  }
}

/// copyWith extension for ErrorListQuery.
extension ErrorListQueryCopyWith on ErrorListQuery {
  ErrorListQuery copyWith({
    String? subject,
    String? chapter,
    String? nodeId,
    bool? needReview,
    String? keyword,
    CognitiveDimension? cognitiveDimension,
    int? page,
    int? pageSize,
  }) =>
      ErrorListQuery(
        subject: subject ?? this.subject,
        chapter: chapter ?? this.chapter,
        nodeId: nodeId ?? this.nodeId,
        needReview: needReview ?? this.needReview,
        keyword: keyword ?? this.keyword,
        cognitiveDimension: cognitiveDimension ?? this.cognitiveDimension,
        page: page ?? this.page,
        pageSize: pageSize ?? this.pageSize,
      );
}
