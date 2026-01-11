import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/error_semantic_summary.dart';
import 'package:sparkle/features/error_book/data/repositories/error_book_repository.dart';
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
  return ErrorBookRepository(dio);
}

// ============================================
// 错题列表 Provider
// ============================================

/// 错题列表查询参数
class ErrorListQuery {
  const ErrorListQuery({
    this.subject,
    this.chapter,
    this.needReview,
    this.keyword,
    this.cognitiveDimension,
    this.page = 1,
    this.pageSize = 20,
  });
  final String? subject;
  final String? chapter;
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
          needReview == other.needReview &&
          keyword == other.keyword &&
          cognitiveDimension == other.cognitiveDimension &&
          page == other.page &&
          pageSize == other.pageSize;

  @override
  int get hashCode =>
      subject.hashCode ^
      chapter.hashCode ^
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
@riverpod
Future<ErrorListResponse> errorList(
  ErrorListRef ref,
  ErrorListQuery query,
) async {
  final repository = ref.watch(errorBookRepositoryProvider);

  return repository.getErrors(
    subject: query.subject,
    chapter: query.chapter,
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
  final repository = ref.watch(errorBookRepositoryProvider);
  final response = await repository.getTodayReviewList();
  return response.items;
}

// ============================================
// 统计数据 Provider
// ============================================

/// 错题统计数据 Provider
@riverpod
Future<ReviewStats> errorStats(ErrorStatsRef ref) async {
  final repository = ref.watch(errorBookRepositoryProvider);
  return repository.getStats();
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
    required String userAnswer,
    required String correctAnswer,
    required String subject,
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

      // 刷新相关列表
      ref.invalidate(errorListProvider);
      ref.invalidate(errorStatsProvider);

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
      );

      // 刷新详情和列表
      ref.invalidate(errorDetailProvider(errorId));
      ref.invalidate(errorListProvider);

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
      ref.invalidate(errorListProvider);
      ref.invalidate(errorStatsProvider);

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

      // 刷新详情、列表和统计
      ref.invalidate(errorDetailProvider(errorId));
      ref.invalidate(errorListProvider);
      ref.invalidate(todayReviewListProvider);
      ref.invalidate(errorStatsProvider);

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
    this.showOnlyNeedReview = false,
    this.searchKeyword = '',
    this.cognitiveDimension,
  });
  final String? selectedSubject;
  final String? chapterFilter;
  final bool showOnlyNeedReview;
  final String searchKeyword;
  final CognitiveDimension? cognitiveDimension;

  ErrorFilterState copyWith({
    String? selectedSubject,
    String? chapterFilter,
    bool? showOnlyNeedReview,
    String? searchKeyword,
    CognitiveDimension? cognitiveDimension,
  }) =>
      ErrorFilterState(
        selectedSubject: selectedSubject ?? this.selectedSubject,
        chapterFilter: chapterFilter ?? this.chapterFilter,
        showOnlyNeedReview: showOnlyNeedReview ?? this.showOnlyNeedReview,
        searchKeyword: searchKeyword ?? this.searchKeyword,
        cognitiveDimension: cognitiveDimension ?? this.cognitiveDimension,
      );

  /// 转换为查询参数
  ErrorListQuery toQuery({int page = 1, int pageSize = 20}) => ErrorListQuery(
        subject: selectedSubject,
        chapter: chapterFilter,
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

  void reset() {
    state = const ErrorFilterState();
  }
}
