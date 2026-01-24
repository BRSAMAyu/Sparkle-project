import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/features/translation/data/repositories/local_translation_repository.dart';

/// Translation history state
class TranslationHistoryState {
  const TranslationHistoryState({
    this.records = const [],
    this.isLoading = false,
    this.filter = TranslationFilter.all,
    this.sortOrder = TranslationSortOrder.newestFirst,
    this.searchQuery = '',
    this.statistics = const {},
  });

  final List<TranslationHistoryItem> records;
  final bool isLoading;
  final TranslationFilter filter;
  final TranslationSortOrder sortOrder;
  final String searchQuery;
  final Map<String, int> statistics;

  TranslationHistoryState copyWith({
    List<TranslationHistoryItem>? records,
    bool? isLoading,
    TranslationFilter? filter,
    TranslationSortOrder? sortOrder,
    String? searchQuery,
    Map<String, int>? statistics,
  }) =>
      TranslationHistoryState(
        records: records ?? this.records,
        isLoading: isLoading ?? this.isLoading,
        filter: filter ?? this.filter,
        sortOrder: sortOrder ?? this.sortOrder,
        searchQuery: searchQuery ?? this.searchQuery,
        statistics: statistics ?? this.statistics,
      );
}

/// Translation history notifier
class TranslationHistoryNotifier extends StateNotifier<TranslationHistoryState> {
  TranslationHistoryNotifier(this._repository) : super(const TranslationHistoryState()) {
    loadHistory();
    loadStatistics();
  }

  final LocalTranslationRepository _repository;

  /// Load translation history
  Future<void> loadHistory() async {
    state = state.copyWith(isLoading: true);

    try {
      final records = state.searchQuery.isEmpty
          ? await _repository.getAll(
              filter: state.filter,
              sortOrder: state.sortOrder,
            )
          : await _repository.search(state.searchQuery);

      state = state.copyWith(records: records, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false);
    }
  }

  /// Load statistics
  Future<void> loadStatistics() async {
    try {
      final stats = await _repository.getStatistics();
      state = state.copyWith(statistics: stats);
    } catch (_) {}
  }

  /// Set filter
  void setFilter(TranslationFilter filter) {
    if (state.filter != filter) {
      state = state.copyWith(filter: filter);
      loadHistory();
    }
  }

  /// Set sort order
  void setSortOrder(TranslationSortOrder order) {
    if (state.sortOrder != order) {
      state = state.copyWith(sortOrder: order);
      loadHistory();
    }
  }

  /// Search
  void search(String query) {
    if (state.searchQuery != query) {
      state = state.copyWith(searchQuery: query);
      loadHistory();
    }
  }

  /// Clear search
  void clearSearch() {
    if (state.searchQuery.isNotEmpty) {
      state = state.copyWith(searchQuery: '');
      loadHistory();
    }
  }

  /// Update rating
  Future<bool> updateRating(Id id, int rating) async {
    final success = await _repository.updateRating(id, rating);
    if (success) {
      await loadHistory();
      await loadStatistics();
    }
    return success;
  }

  /// Toggle favorite
  Future<bool?> toggleFavorite(Id id) async {
    final result = await _repository.toggleFavorite(id);
    if (result != null) {
      await loadHistory();
      await loadStatistics();
    }
    return result;
  }

  /// Delete record
  Future<bool> delete(Id id) async {
    final success = await _repository.delete(id);
    if (success) {
      await loadHistory();
      await loadStatistics();
    }
    return success;
  }

  /// Delete all records
  Future<bool> deleteAll() async {
    final success = await _repository.deleteAll();
    if (success) {
      await loadHistory();
      await loadStatistics();
    }
    return success;
  }

  /// Save a new translation
  Future<Id> saveTranslation({
    required String originalText,
    required String translatedText,
    required String sourceLanguage,
    required String targetLanguage,
    int rating = 3,
    bool isFavorited = false,
  }) async {
    final id = await _repository.save(
      originalText: originalText,
      translatedText: translatedText,
      sourceLanguage: sourceLanguage,
      targetLanguage: targetLanguage,
      rating: rating,
      isFavorited: isFavorited,
    );

    // Refresh history
    await loadHistory();
    await loadStatistics();

    return id;
  }

  /// Check for similar translation
  Future<TranslationHistoryItem?> findSimilar({
    required String originalText,
    required String sourceLanguage,
    required String targetLanguage,
  }) async => await _repository.findSimilar(
      originalText: originalText,
      sourceLanguage: sourceLanguage,
      targetLanguage: targetLanguage,
    );
}

/// Repository provider
final localTranslationRepositoryProvider =
    Provider<LocalTranslationRepository>((ref) {
  final repository = LocalTranslationRepository();
  final db = ref.watch(localDatabaseProvider);
  // Initialize repository with database
  ref.onAddListener(() {
    // The database should already be initialized at app startup
    repository.init(db);
  });

  // Try to get the database directly if already initialized
  try {
    repository.init(db);
  } catch (_) {}

  return repository;
});

/// History state provider
final translationHistoryProvider =
    StateNotifierProvider<TranslationHistoryNotifier, TranslationHistoryState>(
        (ref) => TranslationHistoryNotifier(ref.watch(localTranslationRepositoryProvider)),);
