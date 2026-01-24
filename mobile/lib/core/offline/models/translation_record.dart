import 'package:isar/isar.dart';

part 'translation_record.g.dart';

@collection
class TranslationRecord {
  Id id = Isar.autoIncrement;

  // Translation content
  @Index()
  late String originalText;
  late String translatedText;
  late String sourceLanguage;
  late String targetLanguage;

  // User feedback
  late int rating; // 1-5 stars importance
  late bool isFavorited;

  // Statistics
  late int viewCount;
  DateTime? lastViewedAt;

  // Timestamp
  @Index()
  late DateTime createdAt;

  // Associated words (extracted keywords)
  final extractedWords = IsarLinks<TranslationWordLink>();
}

@collection
class TranslationWordLink {

  TranslationWordLink();
  Id id = Isar.autoIncrement;

  @Index()
  late int translationRecordId;

  late String word;
}

extension TranslationRecordExtension on TranslationRecord {
  static const int defaultRating = 3;
  static const int defaultViewCount = 0;

  static TranslationRecord create({
    required String originalText,
    required String translatedText,
    required String sourceLanguage,
    required String targetLanguage,
    int rating = defaultRating,
    bool isFavorited = false,
  }) {
    final record = TranslationRecord()
      ..originalText = originalText
      ..translatedText = translatedText
      ..sourceLanguage = sourceLanguage
      ..targetLanguage = targetLanguage
      ..rating = rating.clamp(1, 5)
      ..isFavorited = isFavorited
      ..viewCount = defaultViewCount
      ..createdAt = DateTime.now();

    return record;
  }

  void incrementViewCount() {
    viewCount++;
    lastViewedAt = DateTime.now();
  }

  TranslationRecord copyWith({
    String? originalText,
    String? translatedText,
    String? sourceLanguage,
    String? targetLanguage,
    int? rating,
    bool? isFavorited,
    int? viewCount,
    DateTime? lastViewedAt,
    DateTime? createdAt,
  }) {
    final record = TranslationRecord()
      ..id = id
      ..originalText = originalText ?? this.originalText
      ..translatedText = translatedText ?? this.translatedText
      ..sourceLanguage = sourceLanguage ?? this.sourceLanguage
      ..targetLanguage = targetLanguage ?? this.targetLanguage
      ..rating = (rating ?? this.rating).clamp(1, 5)
      ..isFavorited = isFavorited ?? this.isFavorited
      ..viewCount = viewCount ?? this.viewCount
      ..lastViewedAt = lastViewedAt ?? this.lastViewedAt
      ..createdAt = createdAt ?? this.createdAt;

    return record;
  }
}
