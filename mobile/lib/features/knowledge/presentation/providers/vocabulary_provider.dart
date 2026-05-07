import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/knowledge/data/repositories/vocabulary_repository.dart';

/// 生词本状态
class VocabularyState {
  const VocabularyState({
    this.lookupResult,
    this.wordbook = const [],
    this.reviewList = const [],
    this.associations = const [],
    this.stats = const {},
    this.exampleSentence,
    this.isLoading = false,
    this.isLookingUp = false,
    this.error,
  });
  final Map<String, dynamic>? lookupResult;
  final List<dynamic> wordbook;
  final List<dynamic> reviewList;
  final List<String> associations;
  final Map<String, dynamic> stats;
  final String? exampleSentence;
  final bool isLoading;
  final bool isLookingUp;
  final String? error;

  VocabularyState copyWith({
    Map<String, dynamic>? lookupResult,
    List<dynamic>? wordbook,
    List<dynamic>? reviewList,
    List<String>? associations,
    Map<String, dynamic>? stats,
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
        stats: stats ?? this.stats,
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
        error: e.toString().contains('404')
            ? (I18nService.instance.isChinese ? '未找到该单词' : 'Word not found')
            : (I18nService.instance.isChinese ? '查询失败: $e' : 'Lookup failed: $e'),
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
    int importance = 3,
    String? partOfSpeech,
    String? sourceTranslationId,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      await _repository.addToWordbook(
        word: word,
        definition: definition,
        phonetic: phonetic,
        contextSentence: contextSentence,
        taskId: taskId,
        importance: importance,
        partOfSpeech: partOfSpeech,
        sourceTranslationId: sourceTranslationId,
      );
      await Future.wait([fetchWordbook(), fetchReviewList(), fetchStats()]);
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: I18nService.instance.isChinese ? '添加失败: $e' : 'Add failed: $e',
      );
      return false;
    }
  }

  Future<void> fetchWordbook({String? search}) async {
    state = state.copyWith(isLoading: true, clearError: true);

    try {
      final list = await _repository.getWordbook(search: search);
      state = state.copyWith(
        wordbook: list,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: I18nService.instance.isChinese ? '获取生词本失败: $e' : 'Failed to load wordbook: $e',
      );
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
        error: I18nService.instance.isChinese ? '获取复习列表失败: $e' : 'Failed to load review list: $e',
      );
    }
  }

  Future<void> fetchStats() async {
    try {
      final stats = await _repository.getStats();
      state = state.copyWith(stats: stats);
    } catch (e) {
      state = state.copyWith(error: I18nService.instance.isChinese ? '获取词汇统计失败: $e' : 'Failed to load stats: $e');
    }
  }

  /// 记录复习结果
  Future<void> recordReview(String wordId, bool success) async {
    try {
      await _repository.recordReview(wordId, success);
      await Future.wait([fetchWordbook(), fetchReviewList(), fetchStats()]);
    } catch (e) {
      state = state.copyWith(error: I18nService.instance.isChinese ? '记录失败: $e' : 'Record failed: $e');
    }
  }

  Future<void> updateImportance(String wordId, int importance) async {
    try {
      await _repository.updateImportance(wordId, importance);
      await Future.wait([fetchWordbook(), fetchReviewList(), fetchStats()]);
    } catch (e) {
      state = state.copyWith(error: I18nService.instance.isChinese ? '更新重要度失败: $e' : 'Update failed: $e');
    }
  }

  Future<void> deleteWordbookEntry(String wordId) async {
    try {
      await _repository.deleteWordbook(wordId);
      await Future.wait([fetchWordbook(), fetchReviewList(), fetchStats()]);
    } catch (e) {
      state = state.copyWith(error: I18nService.instance.isChinese ? '删除失败: $e' : 'Delete failed: $e');
    }
  }

  Map<String, dynamic>? getWordbookEntryByWord(String word) {
    final normalized = word.trim().toLowerCase();
    for (final entry in state.wordbook) {
      if (entry is Map<String, dynamic> &&
          (entry['word'] as String?)?.toLowerCase() == normalized) {
        return entry;
      }
    }
    return null;
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
  (ref) => VocabularyNotifier(ref.watch(vocabularyRepositoryProvider)),
);
