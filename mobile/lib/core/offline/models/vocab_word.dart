import 'package:isar/isar.dart';

part 'vocab_word.g.dart';

@collection
class VocabWord {
  Id id = Isar.autoIncrement;

  // Word information
  @Index(unique: true)
  late String word;
  String? phonetic;
  String? definition;
  String? exampleSentence;
  String? partOfSpeech;

  // User rating - 1-5 stars importance (replaces mastery_level 0-7)
  late int importance;

  // Review system (calculate interval based on importance)
  @Index()
  DateTime? nextReviewAt;
  late int reviewCount;
  DateTime? lastReviewAt;
  late int correctReviewCount;
  
  // Streak for SRS calculation
  int consecutiveCorrect = 0;

  // Associations
  String? sourceTranslationId;
  String? taskId;

  // Timestamps
  @Index()
  late DateTime createdAt;
  late DateTime updatedAt;

  // Tags
  List<String> tags = [];

  VocabWord();

  /// Calculate next review time based on importance and accuracy
  DateTime calculateNextReview(bool remembered) {
    if (!remembered) {
      // If forgotten, review very soon (e.g. 1 day)
      return DateTime.now().add(const Duration(days: 1));
    }

    // Higher importance = Shorter base interval (Need to review more often)
    // Importance 5 -> Base 1 day
    // Importance 1 -> Base 5 days
    final baseInterval = (6 - importance).clamp(1, 5);
    
    // Exponential backoff based on streak
    // interval = base * (2 ^ (streak - 1))
    // streak 1: base * 1
    // streak 2: base * 2
    // streak 3: base * 4
    final multiplier = (1 << (consecutiveCorrect - 1)).toDouble();
    final days = baseInterval * multiplier;
    
    return DateTime.now().add(Duration(days: days.toInt()));
  }

  /// Record a review and update the review schedule
  void recordReview(bool remembered) {
    reviewCount++;
    lastReviewAt = DateTime.now();
    
    if (remembered) {
      correctReviewCount++;
      consecutiveCorrect++;
    } else {
      // Reset streak on failure
      consecutiveCorrect = 0;
    }
    
    nextReviewAt = calculateNextReview(remembered);
    updatedAt = DateTime.now();
  }

  /// Check if the word is due for review
  bool get isDueForReview {
    if (nextReviewAt == null) return true;
    return DateTime.now().isAfter(nextReviewAt!);
  }

  /// Get days until next review
  int? get daysUntilReview {
    if (nextReviewAt == null) return null;
    final diff = nextReviewAt!.difference(DateTime.now());
    return diff.inDays.isNegative ? 0 : diff.inDays;
  }

  /// Get accuracy rate (0.0 to 1.0)
  double get accuracyRate {
    if (reviewCount == 0) return 0.0;
    return correctReviewCount / reviewCount;
  }

  /// Create a new VocabWord with default values
  static VocabWord create({
    required String word,
    String? phonetic,
    String? definition,
    String? exampleSentence,
    String? partOfSpeech,
    int importance = 3,
    String? sourceTranslationId,
    String? taskId,
    List<String> tags = const [],
  }) {
    final now = DateTime.now();
    final vocabWord = VocabWord()
      ..word = word.toLowerCase()
      ..phonetic = phonetic
      ..definition = definition
      ..exampleSentence = exampleSentence
      ..partOfSpeech = partOfSpeech
      ..importance = importance.clamp(1, 5)
      ..reviewCount = 0
      ..correctReviewCount = 0
      ..consecutiveCorrect = 0
      ..nextReviewAt = now.add(Duration(days: (6 - importance).clamp(1, 5))) // Initial review based on importance
      ..sourceTranslationId = sourceTranslationId
      ..taskId = taskId
      ..createdAt = now
      ..updatedAt = now
      ..tags = tags;

    return vocabWord;
  }

  VocabWord copyWith({
    String? word,
    String? phonetic,
    String? definition,
    String? exampleSentence,
    String? partOfSpeech,
    int? importance,
    DateTime? nextReviewAt,
    int? reviewCount,
    DateTime? lastReviewAt,
    int? correctReviewCount,
    int? consecutiveCorrect,
    String? sourceTranslationId,
    String? taskId,
    DateTime? createdAt,
    DateTime? updatedAt,
    List<String>? tags,
  }) {
    final vocabWord = VocabWord()
      ..id = id
      ..word = word ?? this.word
      ..phonetic = phonetic ?? this.phonetic
      ..definition = definition ?? this.definition
      ..exampleSentence = exampleSentence ?? this.exampleSentence
      ..partOfSpeech = partOfSpeech ?? this.partOfSpeech
      ..importance = (importance ?? this.importance).clamp(1, 5)
      ..nextReviewAt = nextReviewAt ?? this.nextReviewAt
      ..reviewCount = reviewCount ?? this.reviewCount
      ..lastReviewAt = lastReviewAt ?? this.lastReviewAt
      ..correctReviewCount = correctReviewCount ?? this.correctReviewCount
      ..consecutiveCorrect = consecutiveCorrect ?? this.consecutiveCorrect
      ..sourceTranslationId = sourceTranslationId ?? this.sourceTranslationId
      ..taskId = taskId ?? this.taskId
      ..createdAt = createdAt ?? this.createdAt
      ..updatedAt = updatedAt ?? this.updatedAt
      ..tags = tags ?? this.tags;

    return vocabWord;
  }
}

/// Collection for review history tracking
@collection
class VocabReview {
  Id id = Isar.autoIncrement;

  @Index()
  late int vocabWordId;

  late bool remembered;
  late int responseTimeMs;
  late DateTime reviewedAt;

  VocabReview();

  static VocabReview create({
    required int vocabWordId,
    required bool remembered,
    required int responseTimeMs,
    DateTime? reviewedAt,
  }) {
    final review = VocabReview()
      ..vocabWordId = vocabWordId
      ..remembered = remembered
      ..responseTimeMs = responseTimeMs
      ..reviewedAt = reviewedAt ?? DateTime.now();

    return review;
  }
}
