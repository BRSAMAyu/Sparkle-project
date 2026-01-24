import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';

/// Local vocabulary word item
class VocabWordItem {
  const VocabWordItem({
    required this.id,
    required this.word,
    required this.importance, required this.reviewCount, required this.correctReviewCount, required this.createdAt, required this.updatedAt, required this.tags, this.phonetic,
    this.definition,
    this.exampleSentence,
    this.partOfSpeech,
    this.nextReviewAt,
    this.lastReviewAt,
    this.sourceTranslationId,
    this.taskId,
  });

  final Id id;
  final String word;
  final String? phonetic;
  final String? definition;
  final String? exampleSentence;
  final String? partOfSpeech;
  final int importance;
  final DateTime? nextReviewAt;
  final int reviewCount;
  final DateTime? lastReviewAt;
  final int correctReviewCount;
  final String? sourceTranslationId;
  final String? taskId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<String> tags;

  /// Check if word is due for review
  bool get isDueForReview {
    if (nextReviewAt == null) return true;
    return DateTime.now().isAfter(nextReviewAt!);
  }

  /// Get accuracy rate
  double get accuracyRate {
    if (reviewCount == 0) return 0.0;
    return correctReviewCount / reviewCount;
  }

  /// Get days until next review
  int? get daysUntilReview {
    if (nextReviewAt == null) return null;
    final diff = nextReviewAt!.difference(DateTime.now());
    return diff.inDays.isNegative ? 0 : diff.inDays;
  }
}

enum VocabFilter {
  all,
  dueForReview,
  highImportance, // 4-5 stars
  mediumImportance, // 3 stars
  lowImportance, // 1-2 stars
  byTag,
}

class LocalVocabularyRepository {
  late final IsarCollection<VocabWord> _vocabWordCollection;
  late final IsarCollection<VocabReview> _vocabReviewCollection;

  void init(LocalDatabase db) {
    _vocabWordCollection = db.vocabWords;
    _vocabReviewCollection = db.vocabReviews;
  }

  /// Add a word to vocabulary
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
    // Check if word already exists
    final existing = await _vocabWordCollection
        .filter()
        .wordEqualTo(word.toLowerCase())
        .findFirst();

    if (existing != null) {
      // Update existing word
      if (definition != null) existing.definition = definition;
      if (phonetic != null) existing.phonetic = phonetic;
      if (exampleSentence != null) existing.exampleSentence = exampleSentence;
      if (partOfSpeech != null) existing.partOfSpeech = partOfSpeech;
      existing.importance = importance.clamp(1, 5);
      existing.updatedAt = DateTime.now();
      if (sourceTranslationId != null) {
        existing.sourceTranslationId = sourceTranslationId;
      }
      if (taskId != null) existing.taskId = taskId;
      if (tags.isNotEmpty) existing.tags = tags;
      await _vocabWordCollection.put(existing);
      return existing.id;
    }

    final newWord = VocabWord.create(
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

    return _vocabWordCollection.put(newWord);
  }

  /// Get word by word string
  Future<VocabWordItem?> getByWord(String word) async {
    final result = await _vocabWordCollection
        .filter()
        .wordEqualTo(word.toLowerCase())
        .findFirst();
    if (result == null) return null;
    return _toItem(result);
  }

  /// Get all words
  Future<List<VocabWordItem>> getAll({
    VocabFilter filter = VocabFilter.all,
    String? tagFilter,
    int limit = 100,
    int offset = 0,
  }) async {
    final words = await _vocabWordCollection
        .filter()
        .offset(offset)
        .limit(limit)
        .findAll();
    return words.map(_toItem).toList();
  }

  /// Get words due for review
  Future<List<VocabWordItem>> getDueForReview({int limit = 20}) async {
    final now = DateTime.now();
    final words = await _vocabWordCollection
        .filter()
        .nextReviewAtLessThan(now)
        .or()
        .nextReviewAtIsNull()
        .sortByNextReviewAt()
        .limit(limit)
        .findAll();
    return words.map(_toItem).toList();
  }

  /// Get due count
  Future<int> getDueCount() async {
    final now = DateTime.now();
    return _vocabWordCollection
        .filter()
        .nextReviewAtLessThan(now)
        .or()
        .nextReviewAtIsNull()
        .count();
  }

  /// Build filter query
  Query<VocabWord> _buildFilterQuery(VocabFilter filter, String? tagFilter) {
    final now = DateTime.now();

    switch (filter) {
      case VocabFilter.dueForReview:
        return _vocabWordCollection
            .filter()
            .nextReviewAtLessThan(now)
            .or()
            .nextReviewAtIsNull()
            .build();
      case VocabFilter.highImportance:
        return _vocabWordCollection
            .filter()
            .importanceGreaterThan(3)
            .build();
      case VocabFilter.mediumImportance:
        return _vocabWordCollection
            .filter()
            .importanceEqualTo(3)
            .build();
      case VocabFilter.lowImportance:
        return _vocabWordCollection
            .filter()
            .importanceLessThan(3)
            .build();
      case VocabFilter.byTag:
        if (tagFilter == null) {
          return _vocabWordCollection.filter().build();
        }
        return _vocabWordCollection
            .filter()
            .tagsElementContains(tagFilter)
            .build();
      case VocabFilter.all:
      default:
        if (tagFilter != null) {
          return _vocabWordCollection
              .filter()
              .tagsElementContains(tagFilter)
              .build();
        }
        return _vocabWordCollection.filter().build();
    }
  }

  /// Update word importance
  Future<bool> updateImportance(Id id, int importance) async {
    final word = await _vocabWordCollection.get(id);
    if (word == null) return false;

    word.importance = importance.clamp(1, 5);
    word.updatedAt = DateTime.now();

    // Recalculate next review if not currently reviewing
    if (word.nextReviewAt == null || !word.isDueForReview) {
      word.nextReviewAt = word.calculateNextReview(true);
    }

    return await _vocabWordCollection.put(word) >= 0;
  }

  /// Record a review
  Future<bool> recordReview(Id id, bool remembered, {int responseTimeMs = 0}) async {
    final word = await _vocabWordCollection.get(id);
    if (word == null) return false;

    // Record review in word
    word.recordReview(remembered);
    await _vocabWordCollection.put(word);

    // Also record in review history
    final review = VocabReview.create(
      vocabWordId: id,
      remembered: remembered,
      responseTimeMs: responseTimeMs,
    );
    await _vocabReviewCollection.put(review);

    return true;
  }

  /// Delete a word
  Future<bool> delete(Id id) async {
    // Also delete associated reviews
    await _vocabReviewCollection
        .filter()
        .vocabWordIdEqualTo(id)
        .deleteAll();
    return _vocabWordCollection.delete(id);
  }

  /// Delete all words
  Future<bool> deleteAll() async {
    await _vocabReviewCollection.clear();
    await _vocabWordCollection.clear();
    return true;
  }

  /// Search words
  Future<List<VocabWordItem>> search(String query) async {
    final lowerQuery = query.toLowerCase();

    final words = await _vocabWordCollection
        .filter()
        .group((q) => q
            .wordContains(lowerQuery, caseSensitive: false)
            .or()
            .definitionContains(lowerQuery, caseSensitive: false)
            .or()
            .tagsElementContains(lowerQuery))
        .limit(50)
        .findAll();

    return words.map(_toItem).toList();
  }

  /// Get all tags
  Future<List<String>> getAllTags() async {
    final words = await _vocabWordCollection.where().findAll();
    final tagSet = <String>{};
    for (final word in words) {
      tagSet.addAll(word.tags);
    }
    return tagSet.toList()..sort();
  }

  /// Get statistics
  Future<Map<String, dynamic>> getStatistics() async {
    final total = await _vocabWordCollection.count();
    final dueCount = await getDueCount();
    final highImportance = await _vocabWordCollection
        .filter()
        .importanceGreaterThan(3)
        .count();

    // Get review stats
    final reviews = await _vocabReviewCollection.where().findAll();
    final totalReviews = reviews.length;
    final correctReviews = reviews.where((r) => r.remembered).length;

    return {
      'total': total,
      'dueCount': dueCount,
      'highImportance': highImportance,
      'totalReviews': totalReviews,
      'correctReviews': correctReviews,
      'accuracyRate': totalReviews > 0 ? correctReviews / totalReviews : 0.0,
    };
  }

  /// Get review history for a word
  Future<List<VocabReview>> getReviewHistory(Id wordId) async => await _vocabReviewCollection
        .filter()
        .vocabWordIdEqualTo(wordId)
        .sortByReviewedAtDesc()
        .findAll();

  /// Convert VocabWord to VocabWordItem
  VocabWordItem _toItem(VocabWord word) => VocabWordItem(
      id: word.id,
      word: word.word,
      phonetic: word.phonetic,
      definition: word.definition,
      exampleSentence: word.exampleSentence,
      partOfSpeech: word.partOfSpeech,
      importance: word.importance,
      nextReviewAt: word.nextReviewAt,
      reviewCount: word.reviewCount,
      lastReviewAt: word.lastReviewAt,
      correctReviewCount: word.correctReviewCount,
      sourceTranslationId: word.sourceTranslationId,
      taskId: word.taskId,
      createdAt: word.createdAt,
      updatedAt: word.updatedAt,
      tags: List.from(word.tags),
    );
}
