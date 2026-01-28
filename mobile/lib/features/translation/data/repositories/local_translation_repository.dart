import 'package:isar/isar.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';

enum TranslationFilter {
  all,
  favorites,
  highRating, // 4+ stars
  recent, // Last 7 days
}

enum TranslationSortOrder {
  newestFirst,
  oldestFirst,
  highestRating,
  lowestRating,
  mostViewed,
}

class TranslationHistoryItem {
  const TranslationHistoryItem({
    required this.id,
    required this.originalText,
    required this.translatedText,
    required this.sourceLanguage,
    required this.targetLanguage,
    required this.rating,
    required this.isFavorited,
    required this.viewCount,
    required this.createdAt,
    required this.lastViewedAt,
  });

  final Id id;
  final String originalText;
  final String translatedText;
  final String sourceLanguage;
  final String targetLanguage;
  final int rating;
  final bool isFavorited;
  final int viewCount;
  final DateTime createdAt;
  final DateTime? lastViewedAt;
}

class LocalTranslationRepository {
  late final IsarCollection<TranslationRecord> _collection;

  void init(LocalDatabase db) {
    _collection = db.translationRecords;
  }

  /// Save a new translation record
  Future<Id> save({
    required String originalText,
    required String translatedText,
    required String sourceLanguage,
    required String targetLanguage,
    int rating = 3,
    bool isFavorited = false,
  }) async {
    final record = TranslationRecordExtension.create(
      originalText: originalText,
      translatedText: translatedText,
      sourceLanguage: sourceLanguage,
      targetLanguage: targetLanguage,
      rating: rating,
      isFavorited: isFavorited,
    );

    return _collection.put(record);
  }

  /// Get all translation records
  Future<List<TranslationHistoryItem>> getAll({
    TranslationFilter filter = TranslationFilter.all,
    TranslationSortOrder sortOrder = TranslationSortOrder.newestFirst,
    int limit = 100,
    int offset = 0,
  }) async {
    List<TranslationRecord> records;

    switch (sortOrder) {
      case TranslationSortOrder.newestFirst:
        final tempRecords = await _collection.where().sortByCreatedAt().offset(offset).limit(limit).findAll();
        records = tempRecords.cast<TranslationRecord>().reversed.toList();
        break;
      case TranslationSortOrder.oldestFirst:
        records = await _collection.where().sortByCreatedAt().offset(offset).limit(limit).findAll();
        break;
      case TranslationSortOrder.highestRating:
        final tempRecords3 = await _collection.where().sortByRating().thenByCreatedAt().offset(offset).limit(limit).findAll();
        records = tempRecords3.cast<TranslationRecord>().reversed.toList();
        break;
      case TranslationSortOrder.lowestRating:
        records = await _collection.where().sortByRating().thenByCreatedAt().offset(offset).limit(limit).findAll();
        break;
      case TranslationSortOrder.mostViewed:
        final tempRecords5 = await _collection.where().sortByViewCount().thenByCreatedAt().offset(offset).limit(limit).findAll();
        records = tempRecords5.cast<TranslationRecord>().reversed.toList();
        break;
    }

    return records.map(_toHistoryItem).toList();
  }

  /// Search translation history
  Future<List<TranslationHistoryItem>> search(String query) async {
    final lowerQuery = query.toLowerCase();

    final records = await _collection
        .filter()
        .group((q) => q
            .originalTextContains(lowerQuery, caseSensitive: false)
            .or()
            .translatedTextContains(lowerQuery, caseSensitive: false),)
        .sortByCreatedAt()
        .limit(50)
        .findAll();

    return records.map(_toHistoryItem).toList();
  }

  /// Update rating for a translation record
  Future<bool> updateRating(Id id, int rating) async {
    final record = await _collection.get(id);
    if (record == null) return false;

    record.rating = rating.clamp(1, 5);
    return await _collection.put(record) >= 0;
  }

  /// Toggle favorite status
  Future<bool?> toggleFavorite(Id id) async {
    final record = await _collection.get(id);
    if (record == null) return null;

    record.isFavorited = !record.isFavorited;
    await _collection.put(record);
    return record.isFavorited;
  }

  /// Increment view count
  Future<void> incrementViewCount(Id id) async {
    final record = await _collection.get(id);
    if (record != null) {
      record.incrementViewCount();
      await _collection.put(record);
    }
  }

  /// Delete a translation record
  Future<bool> delete(Id id) async => _collection.delete(id);

  /// Delete all records
  Future<void> deleteAll() async => _collection.clear();

  /// Delete favorites only
  Future<int> deleteFavorites() async {
    final favorites = await _collection
        .filter()
        .isFavoritedEqualTo(true)
        .findAll();
    return _collection.deleteAll(favorites.map((r) => r.id).toList());
  }

  /// Get statistics
  Future<Map<String, int>> getStatistics() async {
    final total = await _collection.count();
    final favorites = await _collection.filter().isFavoritedEqualTo(true).count();
    final highRated = await _collection.filter().ratingGreaterThan(3).count();

    // Get total views
    final records = await _collection.where().findAll();
    final totalViews = records.fold<int>(0, (sum, r) => sum + r.viewCount);

    return {
      'total': total,
      'favorites': favorites,
      'highRated': highRated,
      'totalViews': totalViews,
    };
  }

  /// Get a single record by ID
  Future<TranslationHistoryItem?> getById(Id id) async {
    final record = await _collection.get(id);
    if (record == null) return null;

    // Increment view count
    record.incrementViewCount();
    await _collection.put(record);

    return _toHistoryItem(record);
  }

  /// Convert TranslationRecord to TranslationHistoryItem
  TranslationHistoryItem _toHistoryItem(TranslationRecord record) => TranslationHistoryItem(
      id: record.id,
      originalText: record.originalText,
      translatedText: record.translatedText,
      sourceLanguage: record.sourceLanguage,
      targetLanguage: record.targetLanguage,
      rating: record.rating,
      isFavorited: record.isFavorited,
      viewCount: record.viewCount,
      createdAt: record.createdAt,
      lastViewedAt: record.lastViewedAt,
    );

  /// Check if a similar translation exists (to avoid duplicates)
  Future<TranslationHistoryItem?> findSimilar({
    required String originalText,
    required String sourceLanguage,
    required String targetLanguage,
  }) async {
    final records = await _collection
        .filter()
        .originalTextEqualTo(originalText)
        .and()
        .sourceLanguageEqualTo(sourceLanguage)
        .and()
        .targetLanguageEqualTo(targetLanguage)
        .sortByCreatedAt()
        .limit(1)
        .findAll();

    if (records.isEmpty) return null;
    return _toHistoryItem(records.first);
  }
}
