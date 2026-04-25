import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

/// 错题列表页面
///
/// 设计原则：
/// 1. 筛选灵活：科目、章节、掌握度、需复习等多维度筛选
/// 2. 状态清晰：loading/empty/error 状态都有明确提示
/// 3. 性能优化：分页加载、滑动删除
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

    // 初始化时如果传入了认知维度，立即设置筛选
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

    // 构建查询参数
    final query = filterState.toQuery();

    // 获取错题列表
    final errorListAsync = ref.watch(errorListProvider(query));

    // 获取统计数据
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
            // 如果有认知维度筛选，显示提示条
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
                        fontWeight: FontWeight.bold,
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
                        '知识点：${filterState.nodeLabel ?? filterState.nodeId}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: theme.colorScheme.secondary,
                          fontWeight: FontWeight.bold,
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

            // 科目筛选条
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

            // 列表内容
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // 全部错题
                  _buildErrorList(errorListAsync, query),

                  // 待复习错题
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
            // 防抖搜索
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
                fontWeight: FontWeight.bold,
              ),
            ),
          );
        },
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
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
                return ErrorCard(
                  error: error,
                  onTap: () => _navigateToDetail(context, error.id),
                  onKnowledgeNodeTap: (nodeId, masteryDelta) =>
                      _navigateToGalaxyNode(context, nodeId, masteryDelta),
                  onDelete: () => _deleteError(error.id),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => _buildErrorState(error.toString(), query),
      );

  Widget _buildEmptyState(bool isReviewTab) => Builder(
        builder: (context) => EmptyState(
          icon: isReviewTab ? Icons.check_circle_outline : Icons.inbox_outlined,
          title: isReviewTab
              ? context.l10n.errorBookNoReview
              : context.l10n.errorBookNoErrors,
          description: isReviewTab
              ? '${context.l10n.errorBookNoReviewHint} 先补记最近做错的一题，系统才会安排后续复习。'
              : context.l10n.errorBookNoErrorsHint,
          actionText: isReviewTab ? '去记录第一道错题' : context.l10n.errorBookAddFirst,
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
                context.l10n.loadingFailed,
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
      // 刷新列表
      ref
        ..invalidate(errorListProvider)
        ..invalidate(errorStatsProvider);
    }
  }

  Future<void> _navigateToDetail(BuildContext context, String errorId) async {
    await context.push('/errors/$errorId');

    // 详情页可能会更新错题，返回时刷新列表
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
                  decoration: const InputDecoration(
                    labelText: '章节',
                    hintText: '例如：函数、力学、电磁学',
                    prefixIcon: Icon(Icons.folder_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                SwitchListTile.adaptive(
                  value: needReviewOnly,
                  contentPadding: EdgeInsets.zero,
                  title: const Text('仅显示待复习'),
                  subtitle: const Text('和顶部“待复习”标签页配合使用'),
                  onChanged: (value) {
                    setDialogState(() {
                      needReviewOnly = value;
                    });
                  },
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  '认知维度',
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
                      label: const Text('全部'),
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

/// ErrorListQuery 的 copyWith 扩展
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
