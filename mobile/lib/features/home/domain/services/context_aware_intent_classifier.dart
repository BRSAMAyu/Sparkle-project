/// Context-aware intent prediction with user state consideration
///
/// Takes into account:
/// - Current sprint status
/// - Time of day
/// - Recent user actions
/// - User preferences
library;

import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';

class ContextAwareIntentClassifier {
  const ContextAwareIntentClassifier._();

  /// Predict intent with context awareness
  static IntentClassification? classifyWithContext(
    String text, {
    required bool isInSprint,
    required int hourOfDay, // 0-23
    required List<String> recentActions,
  }) {
    // First, use enhanced classifier
    final baseResult = EnhancedIntentClassifier.classify(text);

    // === Context Boosting ===

    // Boost sprint prediction if user is in sprint mode
    if (isInSprint && _containsSprintKeywords(text)) {
      final currentScore = baseResult?.confidence ?? 0.0;
      if (baseResult?.type == EnhancedIntentType.sprint) {
        // Already predicted as sprint, boost confidence
        return IntentClassification(
          type: EnhancedIntentType.sprint,
          confidence: (baseResult!.confidence + 0.2).clamp(0.0, 1.0),
        );
      } else if (currentScore < 0.6) {
        // Not confidently predicted, but sprint keywords exist
        return const IntentClassification(
          type: EnhancedIntentType.sprint,
          confidence: 0.7,
        );
      }
    }

    // Boost learn/review in evening hours (study time)
    if ((hourOfDay >= 18 || hourOfDay <= 22) &&
        _containsStudyKeywords(text)) {
      if (baseResult?.type == EnhancedIntentType.learn ||
          baseResult?.type == EnhancedIntentType.review) {
        return baseResult;  // Already correct
      } else if (baseResult == null || baseResult.confidence < 0.6) {
        // Weak prediction, but study keywords detected during study time
        return const IntentClassification(
          type: EnhancedIntentType.learn,
          confidence: 0.65,
        );
      }
    }

    // === Recent Action Pattern ===

    // If user recently created tasks, boost task creation
    final recentTaskCreationCount = recentActions
        .where((action) => action.contains('create_task'))
        .length;

    if (recentTaskCreationCount >= 2 &&
        _containsTaskKeywords(text) &&
        (baseResult == null || baseResult.confidence < 0.7)) {
      return const IntentClassification(
        type: EnhancedIntentType.task,
        confidence: 0.75,
      );
    }

    return baseResult;
  }

  static bool _containsSprintKeywords(String text) {
    final lower = text.toLowerCase();
    return lower.contains('冲刺') ||
        lower.contains('sprint') ||
        lower.contains('专注') ||
        lower.contains('focus') ||
        lower.contains('突击');
  }

  static bool _containsStudyKeywords(String text) {
    final lower = text.toLowerCase();
    return lower.contains('学习') ||
        lower.contains('learn') ||
        lower.contains('study') ||
        lower.contains('复习') ||
        lower.contains('review');
  }

  static bool _containsTaskKeywords(String text) {
    final lower = text.toLowerCase();
    return lower.contains('任务') ||
        lower.contains('task') ||
        lower.contains('做') ||
        lower.contains('创建') ||
        lower.contains('create');
  }
}
