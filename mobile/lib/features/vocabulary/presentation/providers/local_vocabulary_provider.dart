import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/features/vocabulary/data/repositories/local_vocabulary_repository.dart';

/// Local vocabulary state
class LocalVocabularyState {
  const LocalVocabularyState({
    this.words = const [],
    this.dueWords = const [],
    this.isLoading = false,
    this.filter = VocabFilter.all,
    this.tagFilter,
    this.searchQuery = '',
    this.statistics = const {},
    this.allTags = const [],
  });

  final List<VocabWordItem> words;
  final List<VocabWordItem> dueWords;
  final bool isLoading;
  final VocabFilter filter;
  final String? tagFilter;
  final String searchQuery;
  final Map<String, dynamic> statistics;
  final List<String> allTags;

  LocalVocabularyState copyWith({
    List<VocabWordItem>? words,
    List<VocabWordItem>? dueWords,
    bool? isLoading,
    VocabFilter? filter,
    String? tagFilter,
    String? searchQuery,
    Map<String, dynamic>? statistics,
    List<String>? allTags,
    bool clearTagFilter = false,
  }) =>
      LocalVocabularyState(
        words: words ?? this.words,
        dueWords: dueWords ?? this.dueWords,
        isLoading: isLoading ?? this.isLoading,
        filter: filter ?? this.filter,
        tagFilter: clearTagFilter ? null : (tagFilter ?? this.tagFilter),
        searchQuery: searchQuery ?? this.searchQuery,
        statistics: statistics ?? this.statistics,
        allTags: allTags ?? this.allTags,
      );

  int get dueCount => statistics['dueCount'] as int? ?? 0;
  int get totalCount => statistics['total'] as int? ?? 0;
}

/// Local vocabulary notifier
class LocalVocabularyNotifier extends StateNotifier<LocalVocabularyState> {
  LocalVocabularyNotifier(this._repository) : super(const LocalVocabularyState()) {
    loadWords();
    loadDueWords();
    loadStatistics();
    loadTags();
  }

  final LocalVocabularyRepository _repository;

  /// Load all words
  Future<void> loadWords() async {
    state = state.copyWith(isLoading: true);

    try {
      final words = state.searchQuery.isEmpty
          ? await _repository.getAll(
              filter: state.filter,
              tagFilter: state.tagFilter,
            )
          : await _repository.search(state.searchQuery);

      state = state.copyWith(words: words, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false);
    }
  }

  /// Load words due for review
  Future<void> loadDueWords() async {
    try {
      final dueWords = await _repository.getDueForReview();
      state = state.copyWith(dueWords: dueWords);
    } catch (_) {}
  }

  /// Load statistics
  Future<void> loadStatistics() async {
    try {
      final stats = await _repository.getStatistics();
      state = state.copyWith(statistics: stats);
    } catch (_) {}
  }

  /// Load all tags
  Future<void> loadTags() async {
    try {
      final tags = await _repository.getAllTags();
      state = state.copyWith(allTags: tags);
    } catch (_) {}
  }

  /// Set filter
  void setFilter(VocabFilter filter) {
    if (state.filter != filter) {
      state = state.copyWith(filter: filter);
      loadWords();
    }
  }

  /// Set tag filter
  void setTagFilter(String? tag) {
    if (state.tagFilter != tag) {
      state = state.copyWith(filter: VocabFilter.byTag, tagFilter: tag);
      loadWords();
    }
  }

  /// Clear tag filter
  void clearTagFilter() {
    if (state.tagFilter != null) {
      state = state.copyWith(filter: VocabFilter.all, clearTagFilter: true);
      loadWords();
    }
  }

  /// Search
  void search(String query) {
    if (state.searchQuery != query) {
      state = state.copyWith(searchQuery: query);
      loadWords();
    }
  }

  /// Clear search
  void clearSearch() {
    if (state.searchQuery.isNotEmpty) {
      state = state.copyWith(searchQuery: '');
      loadWords();
    }
  }

  /// Add a word
  Future<Id> addWord({
    required String word,
    String? phonetic,
    String? definition,
    String? exampleSentence,
    String? partOfSpeech,
    int importance = 3,
    String? sourceTranslationId,
    String? taskId,
    List<String> tags = const [],
  }) async {
    final id = await _repository.addWord(
      word: word,
      phonetic: phonetic,
      definition: definition,
      exampleSentence: exampleSentence,
      partOfSpeech: partOfSpeech,
      importance: importance,
      sourceTranslationId: sourceTranslationId,
      taskId: taskId,
      tags: tags,
    );

    // Refresh data
    await loadWords();
    await loadStatistics();
    await loadTags();

    return id;
  }

  /// Update word importance
  Future<bool> updateImportance(Id id, int importance) async {
    final success = await _repository.updateImportance(id, importance);
    if (success) {
      await loadWords();
      await loadStatistics();
    }
    return success;
  }

  /// Record a review
  Future<bool> recordReview(Id id, bool remembered, {int responseTimeMs = 0}) async {
    final success = await _repository.recordReview(id, remembered, responseTimeMs: responseTimeMs);
    if (success) {
      await loadWords();
      await loadDueWords();
      await loadStatistics();
    }
    return success;
  }

  /// Delete a word
  Future<bool> delete(Id id) async {
    final success = await _repository.delete(id);
    if (success) {
      await loadWords();
      await loadDueWords();
      await loadStatistics();
      await loadTags();
    }
    return success;
  }

  /// Check if a word exists
  Future<VocabWordItem?> getByWord(String word) async => _repository.getByWord(word);

  /// Get a word by ID
  Future<VocabWordItem?> getById(Id id) async {
    final words = state.words.where((w) => w.id == id).toList();
    if (words.isNotEmpty) return words.first;

    // If not in current list, fetch directly
    try {
      final allWords = await _repository.getAll();
      return allWords.where((w) => w.id == id).firstOrNull;
    } catch (_) {
      return null;
    }
  }
}

/// Repository provider
final localVocabularyRepositoryProvider =
    Provider<LocalVocabularyRepository>((ref) {
  final repository = LocalVocabularyRepository();
  final db = ref.watch(localDatabaseProvider);

  ref.onAddListener(() {
    repository.init(db);
  });

  try {
    repository.init(db);
  } catch (_) {}

  return repository;
});

/// State provider
final localVocabularyProvider =
    StateNotifierProvider<LocalVocabularyNotifier, LocalVocabularyState>(
        (ref) => LocalVocabularyNotifier(ref.watch(localVocabularyRepositoryProvider)),);

/// Due count provider (for badges)
final localVocabularyDueCountProvider =
    Provider<int>((ref) => ref.watch(localVocabularyProvider).dueCount);

/// Total count provider
final localVocabularyTotalCountProvider =
    Provider<int>((ref) => ref.watch(localVocabularyProvider).totalCount);
