import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/core/offline/list_read_cache.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/error_semantic_summary.dart';
import 'package:sparkle/features/error_book/data/models/remediable_pattern.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/insights/presentation/providers/weekly_growth_narrative_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

part 'error_book_provider.g.dart';

// ============================================
// Repository Provider
// ============================================

/// ErrorBookRepository Provider
///
/// 提供 Repository 的单例实例
@riverpod
ErrorBookRepository errorBookRepository(ErrorBookRepositoryRef ref) {
  final dio = ref.watch(dioProvider);
  // N34：注入本地读缓存——断网冷启动仍可翻上次加载过的错题（第一回
  // 找资产），回读快照带「截至 X」时点标记。
  final readCache = ref.watch(listReadCacheProvider);
  return ErrorBookRepository(dio, readCache: readCache);
}

final remediablePatternsProvider =
    FutureProvider.autoDispose<List<RemediablePattern>>((ref) async {
  // F7-01: demo mode has no remediable-pattern fixture, keep the card empty.
  if (DemoDataService.isDemoMode) {
    return const <RemediablePattern>[];
  }
  final repository = ref.watch(errorBookRepositoryProvider);
  return repository.getRemediablePatterns();
});

// ============================================
// 错题列表 Provider
// ============================================

/// 错题列表查询参数
class ErrorListQuery {
  const ErrorListQuery({
    this.subject,
    this.chapter,
    this.nodeId,
    this.needReview,
    this.keyword,
    this.cognitiveDimension,
    this.page = 1,
    this.pageSize = 20,
  });
  final String? subject;
  final String? chapter;
  final String? nodeId;
  final bool? needReview;
  final String? keyword;
  final CognitiveDimension? cognitiveDimension;
  final int page;
  final int pageSize;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ErrorListQuery &&
          runtimeType == other.runtimeType &&
          subject == other.subject &&
          chapter == other.chapter &&
          nodeId == other.nodeId &&
          needReview == other.needReview &&
          keyword == other.keyword &&
          cognitiveDimension == other.cognitiveDimension &&
          page == other.page &&
          pageSize == other.pageSize;

  @override
  int get hashCode =>
      subject.hashCode ^
      chapter.hashCode ^
      nodeId.hashCode ^
      needReview.hashCode ^
      keyword.hashCode ^
      cognitiveDimension.hashCode ^
      page.hashCode ^
      pageSize.hashCode;
}

/// 错题列表 Provider（支持参数化查询）
///
/// 使用方式：
/// ```dart
/// final listState = ref.watch(errorListProvider(
///   ErrorListQuery(subject: 'math', needReview: true)
/// ));
/// ```
///
/// N34：走缓存感知读——离线命中快照时 `fromCache/asOf` 有值，UI 据此
/// 挂「截至 X」stale 徽标（N36 口径）。
@riverpod
Future<CacheAwareResult<ErrorListResponse>> errorList(
  ErrorListRef ref,
  ErrorListQuery query,
) async {
  // F7-01: demo 数据仅在显式 demo 模式下提供；真实 API 失败时抛出，
  // 由 UI 渲染错误态/重试，绝不拿演示数据冒充用户错题。
  if (DemoDataService.isDemoMode) {
    final items = _demoErrorRecords().where((item) {
      final subjectMatches =
          query.subject == null || query.subject == item.subject;
      final chapterMatches =
          query.chapter == null || query.chapter == item.chapter;
      final nodeKeyword = query.nodeId?.trim().toLowerCase() ?? '';
      final nodeMatches = nodeKeyword.isEmpty ||
          item.questionText.toLowerCase().contains(nodeKeyword) ||
          (item.aiAnalysisSummary?.toLowerCase().contains(nodeKeyword) ??
              false);
      final needReviewMatches = query.needReview != true ||
          item.nextReviewAt == null ||
          !item.nextReviewAt!.isAfter(DateTime.now());
      final keyword = query.keyword?.trim().toLowerCase() ?? '';
      final keywordMatches = keyword.isEmpty ||
          item.questionText.toLowerCase().contains(keyword) ||
          item.correctAnswer.toLowerCase().contains(keyword);
      return subjectMatches &&
          chapterMatches &&
          nodeMatches &&
          needReviewMatches &&
          keywordMatches;
    }).toList();

    return CacheAwareResult(
      ErrorListResponse(
        items: items,
        total: items.length,
        page: query.page,
        pageSize: query.pageSize,
        hasNext: false,
      ),
    );
  }

  final repository = ref.watch(errorBookRepositoryProvider);
  return repository.getErrorsCached(
    subject: query.subject,
    chapter: query.chapter,
    nodeId: query.nodeId,
    needReview: query.needReview,
    keyword: query.keyword,
    cognitiveDimension: query.cognitiveDimension,
    page: query.page,
    pageSize: query.pageSize,
  );
}

// ============================================
// 错题详情 Provider
// ============================================

/// 错题详情 Provider
///
/// 根据错题 ID 获取详细信息（包含 AI 分析）
@riverpod
Future<ErrorRecord> errorDetail(ErrorDetailRef ref, String errorId) async {
  final repository = ref.watch(errorBookRepositoryProvider);
  return repository.getError(errorId);
}

// ============================================
// 错题语义摘要 Provider
// ============================================

/// 错题语义摘要 Provider
final errorSemanticSummaryProvider =
    FutureProvider.family<ErrorSemanticSummary, String>((ref, errorId) async {
  final repository = ref.watch(errorBookRepositoryProvider);
  return repository.getSemanticSummary(errorId);
});

// ============================================
// 今日待复习 Provider
// ============================================

/// 今日待复习列表 Provider
///
/// 自动获取需要在今天复习的错题
@riverpod
Future<List<ErrorRecord>> todayReviewList(TodayReviewListRef ref) async {
  // F7-01: demo 数据仅在显式 demo 模式下提供；真实 API 失败时抛出错误态。
  if (DemoDataService.isDemoMode) {
    final now = DateTime.now();
    final l10n = I18nService.instance.l10n;
    return [
      ErrorRecord(
        id: 'demo_review_1',
        questionText: l10n.errorDemoVertexQuestion,
        userAnswer: l10n.errorDemoVertexUserAnswer,
        correctAnswer: l10n.errorDemoVertexCorrectAnswer,
        subject: 'math',
        masteryLevel: 0.42,
        reviewCount: 2,
        createdAt: now.subtract(const Duration(days: 3)),
        updatedAt: now.subtract(const Duration(hours: 4)),
        chapter: l10n.errorDemoVertexChapter,
        aiAnalysisSummary: l10n.errorDemoVertexAnalysis,
      ),
      ErrorRecord(
        id: 'demo_review_2',
        questionText: l10n.errorDemoCorrelationQuestion,
        userAnswer: l10n.errorDemoCorrelationUserAnswer,
        correctAnswer: l10n.errorDemoCorrelationCorrectAnswer,
        subject: 'english',
        masteryLevel: 0.58,
        reviewCount: 1,
        createdAt: now.subtract(const Duration(days: 1)),
        updatedAt: now.subtract(const Duration(hours: 2)),
        chapter: l10n.errorDemoCorrelationChapter,
        aiAnalysisSummary: l10n.errorDemoCorrelationAnalysis,
      ),
    ];
  }

  final repository = ref.watch(errorBookRepositoryProvider);
  // N34：走缓存感知读（离线回读快照），今日复习面断网仍有数据。
  final result = await repository.getTodayReviewListCached();
  return result.data.items;
}

// ============================================
// 统计数据 Provider
// ============================================

/// 错题统计数据 Provider
@riverpod
Future<ReviewStats> errorStats(ErrorStatsRef ref) async {
  // F7-01: demo 数据仅在显式 demo 模式下提供；真实 API 失败时抛出错误态。
  if (DemoDataService.isDemoMode) {
    final items = _demoErrorRecords();
    final now = DateTime.now();
    final subjectDistribution = <String, int>{};
    for (final item in items) {
      subjectDistribution[item.subject] =
          (subjectDistribution[item.subject] ?? 0) + 1;
    }
    return ReviewStats(
      totalErrors: items.length,
      masteredCount: items.where((item) => item.masteryLevel >= 0.8).length,
      needReviewCount: items
          .where(
            (item) =>
                item.nextReviewAt == null || !item.nextReviewAt!.isAfter(now),
          )
          .length,
      reviewStreakDays: 3,
      subjectDistribution: subjectDistribution,
    );
  }

  final repository = ref.watch(errorBookRepositoryProvider);
  // N34：走缓存感知读（离线回读快照），徽标计数断网仍有数据。
  final result = await repository.getStatsCached();
  return result.data;
}

List<ErrorRecord> _demoErrorRecords() => DemoDataService()
    .demoErrorRecords
    .map(
      (item) => ErrorRecord(
        id: item['id'] as String,
        questionText: item['question_text'] as String,
        userAnswer: item['user_answer'] as String,
        correctAnswer: item['correct_answer'] as String,
        subject: _mapDemoSubject(item['subject'] as String),
        masteryLevel: (item['mastery_level'] as num).toDouble(),
        reviewCount: item['review_count'] as int,
        createdAt: DateTime.parse(item['created_at'] as String),
        updatedAt: DateTime.parse(item['updated_at'] as String),
        chapter: item['chapter'] as String?,
        difficulty: item['difficulty'] as int?,
        nextReviewAt:
            DateTime.tryParse(item['next_review_at'] as String? ?? ''),
        aiAnalysisSummary: item['ai_analysis_summary'] as String?,
      ),
    )
    .toList();

String _mapDemoSubject(String raw) {
  switch (raw) {
    case '数据结构':
      return 'cs';
    case '计算机网络':
      return 'network';
    case '操作系统':
      return 'os';
    default:
      return raw.toLowerCase();
  }
}

// ============================================
// 错题操作 Notifier
// ============================================

/// 错题操作状态
class ErrorOperationState {
  const ErrorOperationState({
    this.isLoading = false,
    this.error,
  });
  final bool isLoading;
  final String? error;

  ErrorOperationState copyWith({
    bool? isLoading,
    String? error,
  }) =>
      ErrorOperationState(
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

/// 错题操作 Notifier
///
/// 提供错题的增删改操作（带状态管理）
/// 使用示例：
/// ```dart
/// await ref.read(errorOperationsProvider.notifier).createError(...);
/// ```
@riverpod
class ErrorOperations extends _$ErrorOperations {
  @override
  ErrorOperationState build() => const ErrorOperationState();

  /// 创建错题
  ///
  /// 成功后会自动刷新相关的 Provider
  Future<ErrorRecord> createError({
    required String questionText,
    required String subject,
    String? userAnswer,
    String? correctAnswer,
    String? chapter,
    String? questionImageUrl,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(errorBookRepositoryProvider);
      final result = await repository.createError(
        questionText: questionText,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer,
        subject: subject,
        chapter: chapter,
        questionImageUrl: questionImageUrl,
      );

      // 刷新相关列表 + Galaxy（后端同步扣减掌握度）
      ref
        ..invalidate(errorListProvider)
        ..invalidate(errorStatsProvider);
      ref.invalidate(galaxyProvider);
      ref.read(galaxyRefreshTriggerProvider.notifier).state++;

      state = state.copyWith(isLoading: false);
      return result;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  /// 更新错题
  Future<ErrorRecord> updateError(
    String errorId, {
    String? questionText,
    String? userAnswer,
    String? correctAnswer,
    String? subject,
    String? chapter,
    String? questionImageUrl,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(errorBookRepositoryProvider);
      final result = await repository.updateError(
        errorId,
        questionText: questionText,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer,
        subject: subject,
        chapter: chapter,
        questionImageUrl: questionImageUrl,
      );

      // 刷新详情和列表
      ref
        ..invalidate(errorDetailProvider(errorId))
        ..invalidate(errorListProvider);

      state = state.copyWith(isLoading: false);
      return result;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  /// 删除错题
  Future<void> deleteError(String errorId) async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(errorBookRepositoryProvider);
      await repository.deleteError(errorId);

      // 刷新列表和统计
      ref
        ..invalidate(errorListProvider)
        ..invalidate(errorStatsProvider);

      state = state.copyWith(isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  /// 重新分析错题
  Future<void> reAnalyze(String errorId) async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(errorBookRepositoryProvider);
      await repository.reAnalyzeError(errorId);

      // 分析是异步的，不需要立即刷新
      // 可以通过 WebSocket 或定时轮询更新

      state = state.copyWith(isLoading: false);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  /// 提交复习记录
  ///
  /// performance: 'remembered' | 'fuzzy' | 'forgotten'
  Future<ErrorRecord> submitReview({
    required String errorId,
    required String performance,
    int? timeSpentSeconds,
  }) async {
    state = state.copyWith(isLoading: true);

    try {
      final repository = ref.read(errorBookRepositoryProvider);
      final result = await repository.submitReview(
        errorId: errorId,
        performance: performance,
        timeSpentSeconds: timeSpentSeconds,
      );

      // 刷新详情、列表、统计 + Galaxy（复习更新掌握度）
      ref
        ..invalidate(errorDetailProvider(errorId))
        ..invalidate(errorListProvider)
        ..invalidate(todayReviewListProvider)
        ..invalidate(errorStatsProvider)
        ..invalidate(planListProvider)
        ..invalidate(planDetailProvider)
        ..invalidate(taskListProvider)
        ..invalidate(systemUpdatesProvider)
        ..invalidate(weeklyGrowthNarrativeProvider)
        ..invalidate(galaxyProvider);
      ref.read(galaxyRefreshTriggerProvider.notifier).state++;

      state = state.copyWith(isLoading: false);
      return result;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
      rethrow;
    }
  }

  /// 清除错误状态
  void clearError() {
    state = state.copyWith();
  }
}

// ============================================
// 筛选状态 Provider
// ============================================

/// 错题列表筛选状态
class ErrorFilterState {
  const ErrorFilterState({
    this.selectedSubject,
    this.chapterFilter,
    this.nodeId,
    this.nodeLabel,
    this.showOnlyNeedReview = false,
    this.searchKeyword = '',
    this.cognitiveDimension,
  });
  final String? selectedSubject;
  final String? chapterFilter;
  final String? nodeId;
  final String? nodeLabel;
  final bool showOnlyNeedReview;
  final String searchKeyword;
  final CognitiveDimension? cognitiveDimension;

  ErrorFilterState copyWith({
    String? selectedSubject,
    String? chapterFilter,
    String? nodeId,
    String? nodeLabel,
    bool? showOnlyNeedReview,
    String? searchKeyword,
    CognitiveDimension? cognitiveDimension,
  }) =>
      ErrorFilterState(
        selectedSubject: selectedSubject ?? this.selectedSubject,
        chapterFilter: chapterFilter ?? this.chapterFilter,
        nodeId: nodeId ?? this.nodeId,
        nodeLabel: nodeLabel ?? this.nodeLabel,
        showOnlyNeedReview: showOnlyNeedReview ?? this.showOnlyNeedReview,
        searchKeyword: searchKeyword ?? this.searchKeyword,
        cognitiveDimension: cognitiveDimension ?? this.cognitiveDimension,
      );

  /// 转换为查询参数
  ErrorListQuery toQuery({int page = 1, int pageSize = 20}) => ErrorListQuery(
        subject: selectedSubject,
        chapter: chapterFilter,
        nodeId: nodeId,
        needReview: showOnlyNeedReview ? true : null,
        keyword: searchKeyword.isEmpty ? null : searchKeyword,
        cognitiveDimension: cognitiveDimension,
        page: page,
        pageSize: pageSize,
      );
}

/// 错题筛选器 Provider
///
/// 管理列表页的筛选状态（科目、章节、只看需复习等）
@riverpod
class ErrorFilter extends _$ErrorFilter {
  @override
  ErrorFilterState build() => const ErrorFilterState();

  void setSubject(String? subject) {
    state = state.copyWith(selectedSubject: subject);
  }

  void setChapter(String? chapter) {
    state = state.copyWith(chapterFilter: chapter);
  }

  void toggleNeedReview() {
    state = state.copyWith(showOnlyNeedReview: !state.showOnlyNeedReview);
  }

  void setSearchKeyword(String keyword) {
    state = state.copyWith(searchKeyword: keyword);
  }

  void setCognitiveDimension(CognitiveDimension? dimension) {
    state = state.copyWith(cognitiveDimension: dimension);
  }

  void setNodeFilter(String nodeId, String? nodeLabel) {
    state = state.copyWith(nodeId: nodeId, nodeLabel: nodeLabel);
  }

  void reset() {
    state = const ErrorFilterState();
  }
}
