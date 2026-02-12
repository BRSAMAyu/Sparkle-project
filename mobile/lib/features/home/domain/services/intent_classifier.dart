import 'package:flutter/material.dart';

import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';

/// Legacy enum for backward compatibility
@Deprecated('Use EnhancedIntentType instead')
enum IntentType { task, capsule, chat }

/// Enhanced Intent Classifier - 8 Intent Types with Confidence Scoring
///
/// Intent Types:
/// - chat: General conversation and questions
/// - task: Task creation and management
/// - capsule: Cognitive curiosity fragments
/// - translation: Language translation requests
/// - prism: Cognitive prism and behavior analysis
/// - sprint: Sprint/focus mode activation
/// - learn: Learning and knowledge acquisition
/// - review: Review and revision activities
///
/// Performance: < 2ms classification latency
class IntentClassifier {
  const IntentClassifier._();

  /// Classify user input into intent type with confidence
  ///
  /// Returns [IntentClassification] with type and confidence score (0.0-1.0)
  /// Returns null if no clear intent is detected (confidence < 0.5)
  static IntentClassification? classify(String text) => EnhancedIntentClassifier.classify(text);

  /// Legacy method for backward compatibility
  /// Returns simple enum without confidence score
  @Deprecated('Use classify() which returns IntentClassification with confidence')
  static IntentType? classifySimple(String text) {
    final result = classify(text);
    if (result == null) return null;

    // Map enhanced type to legacy type
    switch (result.type) {
      case EnhancedIntentType.task:
        return IntentType.task;
      case EnhancedIntentType.capsule:
        return IntentType.capsule;
      case EnhancedIntentType.chat:
        return IntentType.chat;
      default:
        // Map new types to chat for backward compatibility
        return IntentType.chat;
    }
  }

  /// Get intent color for UI visualization
  static Color getIntentColor(EnhancedIntentType type) {
    switch (type) {
      case EnhancedIntentType.chat:
        return const Color(0xFF42A5F5); // Blue
      case EnhancedIntentType.task:
        return const Color(0xFF66BB6A); // Green
      case EnhancedIntentType.capsule:
        return const Color(0xFFAB47BC); // Purple
      case EnhancedIntentType.translation:
        return const Color(0xFF26C6DA); // Cyan
      case EnhancedIntentType.prism:
        return const Color(0xFF7E57C2); // Deep Purple
      case EnhancedIntentType.sprint:
        return const Color(0xFFFFA726); // Orange
      case EnhancedIntentType.learn:
        return const Color(0xFFEC407A); // Pink
      case EnhancedIntentType.review:
        return const Color(0xFF5C6BC0); // Indigo
    }
  }

  /// Get intent icon for UI
  static String getIntentIcon(EnhancedIntentType type) {
    switch (type) {
      case EnhancedIntentType.chat:
        return 'auto_awesome';
      case EnhancedIntentType.task:
        return 'add_task';
      case EnhancedIntentType.capsule:
        return 'lightbulb';
      case EnhancedIntentType.translation:
        return 'translate';
      case EnhancedIntentType.prism:
        return 'psychology';
      case EnhancedIntentType.sprint:
        return 'flash_on';
      case EnhancedIntentType.learn:
        return 'school';
      case EnhancedIntentType.review:
        return 'replay';
    }
  }
}
