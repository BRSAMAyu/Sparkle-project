import 'package:sparkle/core/i18n/intent_keywords.dart';

/// Enhanced intent classifier with better coverage
///
/// Matches backend intent types:
/// - chat, create, update, delete, query
/// - learn, review, translation, prism, sprint
enum EnhancedIntentType {
  chat,
  task,
  capsule,
  translation,
  prism,
  sprint,
  learn,
  review,
}

class IntentClassification {
  const IntentClassification({
    required this.type,
    required this.confidence,
  });

  final EnhancedIntentType type;
  final double confidence; // 0.0 - 1.0
}

class EnhancedIntentClassifier {
  const EnhancedIntentClassifier._();

  /// Classify user input with confidence scoring
  /// Returns null if no clear intent detected
  ///
  /// Supports both Chinese and English keywords for bilingual intent detection.
  static IntentClassification? classify(String text) {
    if (text.isEmpty) return null;

    final lower = text.toLowerCase();
    var maxScore = 0.0;
    EnhancedIntentType? bestType;

    // === Priority 1: Special modes (high confidence keywords) ===

    // Translation (翻译)
    if (_containsAny(lower, IntentKeywords.getTranslationBaseKeywords())) {
      final score = _calculateScore(lower, IntentKeywords.getTranslationKeywords());
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.translation;
      }
    }

    // Cognitive Prism (认知棱镜)
    if (_containsAny(lower, IntentKeywords.getPrismBaseKeywords())) {
      final score = _calculateScore(lower, IntentKeywords.getPrismKeywords());
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.prism;
      }
    }

    // Sprint/Focus Mode (冲刺/专注)
    if (_containsAny(lower, IntentKeywords.getSprintBaseKeywords())) {
      final score = _calculateScore(lower, IntentKeywords.getSprintKeywords());
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.sprint;
      }
    }

    // === Priority 2: Learning related ===

    // Review (复习)
    if (_containsAny(lower, IntentKeywords.getReviewBaseKeywords())) {
      final score = _calculateScore(lower, IntentKeywords.getReviewKeywords());
      if (score > maxScore) {
        maxScore = score;
        bestType = EnhancedIntentType.review;
      }
    }

    // Learn (学习)
    if (_containsAny(lower, IntentKeywords.getLearnBaseKeywords())) {
      // Exclude combinations with other intents
      if (!lower.contains('复习') && !lower.contains('翻译') && !lower.contains('冲刺') && !lower.contains('专注模式') &&
          !lower.contains('review') && !lower.contains('translate') && !lower.contains('sprint')) {
        final score = _calculateScore(lower, IntentKeywords.getLearnKeywords());
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.learn;
        }
      }
    }

    // === Priority 3: Task management ===

    // Task/创建
    if (_containsAny(lower, IntentKeywords.getTaskBaseKeywords())) {
      // Exclude interference words
      if (!lower.contains('冲刺') && !lower.contains('翻译') && !lower.contains('sprint') && !lower.contains('translate')) {
        final score = _calculateScore(lower, IntentKeywords.getTaskKeywords());
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.task;
        }
      }
    }

    // === Priority 4: Cognitive capsule (emotional expressions) ===

    // Capsule (好奇心胶囊)
    if (_containsAny(lower, IntentKeywords.getCapsuleBaseKeywords())) {
      // Exclude combinations with other intents
      if (!lower.contains('学习') && !lower.contains('复习') && !lower.contains('翻译') &&
          !lower.contains('learn') && !lower.contains('review') && !lower.contains('translate')) {
        final score = _calculateScore(lower, IntentKeywords.getCapsuleKeywords());
        if (score > maxScore) {
          maxScore = score;
          bestType = EnhancedIntentType.capsule;
        }
      }
    }

    // === Priority 5: Default chat ===

    // Long text tends to be chat
    if (text.length > 15 && maxScore < 0.5) {
      bestType = EnhancedIntentType.chat;
      maxScore = 0.5; // Set to 0.5 to meet the minimum threshold
    }

    // Return result only if confidence is high enough
    if (bestType != null && maxScore >= 0.5) {
      return IntentClassification(
        type: bestType,
        confidence: maxScore,
      );
    }

    return null;  // No clear intent detected
  }

  /// Calculate score based on keyword matches
  static double _calculateScore(String text, Map<String, double> keywords) {
    var score = 0.0;
    for (final entry in keywords.entries) {
      if (text.contains(entry.key)) {
        score = score > entry.value ? score : entry.value;
      }
    }
    return score;
  }

  /// Check if text contains any of the keywords
  static bool _containsAny(String text, List<String> keywords) => keywords.any((keyword) => text.contains(keyword));
}
