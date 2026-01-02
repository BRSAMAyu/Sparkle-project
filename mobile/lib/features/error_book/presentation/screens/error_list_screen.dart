import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/subject_chips.dart';
import '../widgets/error_card.dart';
import '../../data/providers/error_book_provider.dart';
import 'add_error_screen.dart';
import 'error_detail_screen.dart';

/// 错题列表页面
///
/// 设计原则：
/// 1. 筛选灵活：科目、章节、掌握度、需复习等多维度筛选
/// 2. 状态清晰：loading/empty/error 状态都有明确提示
/// 3. 性能优化：分页加载、滑动删除
class ErrorListScreen extends ConsumerStatefulWidget {
  const ErrorListScreen({super.key});

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

    // 构建查询参数
    final query = filterState.toQuery();

    // 获取错题列表
    final errorListAsync = ref.watch(errorListProvider(query));

    // 获取统计数据
    final statsAsync = ref.watch(errorStatsProvider);

    return Scaffold(
      appBar: AppBar(
        title: _showSearch ? _buildSearchField() : const Text('错题档案'),
        actions: [
          IconButton(
            icon: Icon(_showSearch ? Icons.close : Icons.search),
            onPressed: () {
              setState(() {
                _showSearch = !_showSearch;
                if (!_showSearch) {
                  _searchController.clear();
                  ref.read(errorFilterProvider.notifier).setSearchKeyword('');
                }
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(context),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text('全部'),
                  const SizedBox(width: 8),
                  _buildStatsBadge(statsAsync, 'total'),
                ],
              ),
            ),
            Tab(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text('待复习'),
                  const SizedBox(width: 8),
                  _buildStatsBadge(statsAsync, 'needReview'),
                ],
              ),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // 科目筛选条
          Container(
            color: theme.colorScheme.surface,
            child: Column(
              children: [
                const SizedBox(height: 12),
                SubjectFilterChips(
                  selectedSubject: filterState.selectedSubject,
                  onSelected: (subject) {
                    ref.read(errorFilterProvider.notifier).setSubject(subject);
                  },
                ),
                const SizedBox(height: 12),
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
                  ref.watch(errorListProvider(
                    query.copyWith(needReview: true),
                  )),
                  query.copyWith(needReview: true),
                ),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _navigateToAddError(context),
        icon: const Icon(Icons.add),
        label: const Text('添加错题'),
      ),
    );
  }

  Widget _buildSearchField() {
    return TextField(
      controller: _searchController,
      autofocus: true,
      decoration: const InputDecoration(
        hintText: '搜索题目内容...',
        border: InputBorder.none,
      ),
      onChanged: (value) {
        // 防抖搜索
        Future.delayed(const Duration(milliseconds: 500), () {
          if (value == _searchController.text) {
            ref.read(errorFilterProvider.notifier).setSearchKeyword(value);
          }
        });
      },
    );
  }

  Widget _buildStatsBadge(AsyncValue<ReviewStats> statsAsync, String type) {
    return statsAsync.when(
      data: (stats) {
        final count = type == 'total'
            ? stats.totalErrors
            : stats.needReviewCount;

        if (count == 0) return const SizedBox.shrink();

        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: type == 'needReview'
                ? Colors.red
                : Theme.of(context).colorScheme.primary,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            count.toString(),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.bold,
            ),
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  Widget _buildErrorList(
    AsyncValue<ErrorListResponse> errorListAsync,
    ErrorListQuery query,
  ) {
    return errorListAsync.when(
      data: (response) {
        if (response.items.isEmpty) {
          return _buildEmptyState(query.needReview == true);
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
                onDelete: () => _deleteError(error.id),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => _buildErrorState(error.toString(), query),
    );
  }

  Widget _buildEmptyState(bool isReviewTab) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            isReviewTab ? Icons.check_circle_outline : Icons.inbox_outlined,
            size: 80,
            color: Colors.grey,
          ),
          const SizedBox(height: 16),
          Text(
            isReviewTab ? '暂无需要复习的错题' : '还没有错题记录',
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            isReviewTab
                ? '做得很好！继续保持'
                : '点击右下角 + 按钮添加错题',
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
          if (!isReviewTab) ...[
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => _navigateToAddError(context),
              icon: const Icon(Icons.add),
              label: const Text('添加第一道错题'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorState(String error, ErrorListQuery query) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 80,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          const Text(
            '加载失败',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () {
              ref.invalidate(errorListProvider(query));
            },
            icon: const Icon(Icons.refresh),
            label: const Text('重试'),
          ),
        ],
      ),
    );
  }

  Future<void> _navigateToAddError(BuildContext context) async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (context) => const AddErrorScreen(),
      ),
    );

    if (result == true && mounted) {
      // 刷新列表
      ref.invalidate(errorListProvider);
      ref.invalidate(errorStatsProvider);
    }
  }

  Future<void> _navigateToDetail(BuildContext context, String errorId) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ErrorDetailScreen(errorId: errorId),
      ),
    );

    // 详情页可能会更新错题，返回时刷新列表
    if (mounted) {
      ref.invalidate(errorListProvider);
      ref.invalidate(errorStatsProvider);
    }
  }

  Future<void> _deleteError(String errorId) async {
    try {
      await ref.read(errorOperationsProvider.notifier).deleteError(errorId);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('删除成功'),
            backgroundColor: Colors.green,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('删除失败: ${e.toString()}'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Future<void> _showFilterDialog(BuildContext context) async {
    // TODO: 实现更多筛选选项（掌握度、章节等）
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('筛选选项'),
        content: const Text('更多筛选功能开发中...'),
        actions: [
          TextButton(
            onPressed: () {
              ref.read(errorFilterProvider.notifier).reset();
              Navigator.of(context).pop();
            },
            child: const Text('重置'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }
}

/// ErrorListQuery 的 copyWith 扩展
extension ErrorListQueryCopyWith on ErrorListQuery {
  ErrorListQuery copyWith({
    String? subject,
    String? chapter,
    bool? needReview,
    String? keyword,
    int? page,
    int? pageSize,
  }) {
    return ErrorListQuery(
      subject: subject ?? this.subject,
      chapter: chapter ?? this.chapter,
      needReview: needReview ?? this.needReview,
      keyword: keyword ?? this.keyword,
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
    );
  }
}
