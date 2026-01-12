import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/knowledge/data/repositories/vocabulary_repository.dart';

/// 生词本状态
class VocabularyState {
  const VocabularyState({
    this.lookupResult,
    this.wordbook = const [],
    this.reviewList = const [],
    this.associations = const [],
    this.exampleSentence,
    this.isLoading = false,
    this.isLookingUp = false,
    this.error,
  });
  final Map<String, dynamic>? lookupResult;
  final List<dynamic> wordbook;
  final List<dynamic> reviewList;
  final List<String> associations;
  final String? exampleSentence;
  final bool isLoading;
  final bool isLookingUp;
  final String? error;

  VocabularyState copyWith({
    Map<String, dynamic>? lookupResult,
    List<dynamic>? wordbook,
    List<dynamic>? reviewList,
    List<String>? associations,
    String? exampleSentence,
    bool? isLoading,
    bool? isLookingUp,
    String? error,
    bool clearLookup = false,
    bool clearError = false,
  }) =>
      VocabularyState(
        lookupResult: clearLookup ? null : (lookupResult ?? this.lookupResult),
        wordbook: wordbook ?? this.wordbook,
        reviewList: reviewList ?? this.reviewList,
        associations: associations ?? this.associations,
        exampleSentence: exampleSentence ?? this.exampleSentence,
        isLoading: isLoading ?? this.isLoading,
        isLookingUp: isLookingUp ?? this.isLookingUp,
        error: clearError ? null : (error ?? this.error),
      );
}

/// 生词本状态管理器
class VocabularyNotifier extends StateNotifier<VocabularyState> {
  VocabularyNotifier(this._repository) : super(const VocabularyState());
  final VocabularyRepository _repository;

  /// 查询单词
  Future<void> lookup(String word) async {
    if (word.trim().isEmpty) return;

    state = state.copyWith(
      isLookingUp: true,
      clearError: true,
      clearLookup: true,
      associations: [],
    );

    try {
      final result = await _repository.lookup(word.trim().toLowerCase());
      state = state.copyWith(
        lookupResult: result,
        isLookingUp: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLookingUp: false,
        error: e.toString().contains('404') ? '未找到该单词' : '查询失败: $e',
      );
    }
  }

  /// 添加到生词本
  Future<bool> addToWordbook({
    required String word,
    required String definition,
    String? phonetic,
    String? contextSentence,
    String? taskId,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      await _repository.addToWordbook({
        'word': word,
        'definition': definition,
        if (phonetic != null) 'phonetic': phonetic,
        if (contextSentence != null) 'context_sentence': contextSentence,
        if (taskId != null) 'task_id': taskId,
      });
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: '添加失败: $e',
      );
      return false;
    }
  }

  /// 获取待复习列表
  Future<void> fetchReviewList() async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final list = await _repository.getReviewList();
      state = state.copyWith(
        reviewList: list,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: '获取复习列表失败: $e',
      );
    }
  }

  /// 记录复习结果
  Future<void> recordReview(String wordId, bool success) async {
    try {
      await _repository.recordReview(wordId, success);
      // 乐观更新：从复习列表中移除已复习的单词
      state = state.copyWith(
        reviewList: state.reviewList.where((w) => w['id'] != wordId).toList(),
      );
    } catch (e) {
      state = state.copyWith(error: '记录失败: $e');
    }
  }

  /// 获取关联词汇 (LLM)
  Future<void> fetchAssociations(String word) async {
    if (word.trim().isEmpty) return;

    try {
      final associations = await _repository.getAssociations(word);
      state = state.copyWith(associations: associations);
    } catch (e) {
      // 非关键功能，静默失败
    }
  }

  /// 生成例句 (LLM)
  Future<void> generateSentence(String word, {String? context}) async {
    if (word.trim().isEmpty) return;

    try {
      final sentence =
          await _repository.generateSentence(word, context: context);
      state = state.copyWith(exampleSentence: sentence);
    } catch (e) {
      // 非关键功能，静默失败
    }
  }

  /// 清除查询结果
  void clearLookup() {
    state = state.copyWith(
      clearLookup: true,
      associations: [],
      clearError: true,
    );
  }

  /// 清除错误
  void clearError() {
    state = state.copyWith(clearError: true);
  }
}

/// 生词本 Provider
final vocabularyProvider =
    StateNotifierProvider<VocabularyNotifier, VocabularyState>(
        (ref) => VocabularyNotifier(ref.watch(vocabularyRepositoryProvider)),);
