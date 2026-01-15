import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';

/// Service to generate ContextEnvelope from local focus state
///
/// ContextEnvelope is compressed context sent to backend for prediction.
/// Contains 30-minute aggregated metrics, no PII, no raw event data.
class ContextService {
  /// Generate ContextEnvelope from mindfulness state
  ///
  /// Args:
  ///   focusState: Current mindfulness/focus session state
  ///   translationRequests: Number of translation requests in last 30 min
  ///   translationGranularity: Last translation granularity ("word", "sentence", "page")
  ///   unknownTermsSaved: Number of unknown terms saved to vocabulary
  ///
  /// Returns:
  ///   Map<String, dynamic> representing ContextEnvelope
  Future<Map<String, dynamic>> generateContextEnvelope({
    required MindfulnessState focusState,
    required int translationRequests,
    required String translationGranularity,
    int unknownTermsSaved = 0,
  }) async {
    final now = DateTime.now();

    // Calculate planned minutes from task
    final plannedMinutes = focusState.currentTask?.estimatedMinutes ?? 25;

    // Calculate actual minutes from elapsed seconds
    final actualMinutes = focusState.elapsedSeconds ~/ 60;

    // Calculate completion ratio
    final completion = plannedMinutes > 0
        ? (focusState.elapsedSeconds / (plannedMinutes * 60)).clamp(0.0, 1.0)
        : 0.0;

    return {
      'context_version': 'ce_v1',
      'window': 'last_30min',
      'focus': {
        'planned_min': plannedMinutes,
        'actual_min': actualMinutes,
        'interruptions': focusState.interruptionCount,
        'completion': completion,
      },
      'comprehension': {
        'translation_requests': translationRequests,
        'translation_granularity': translationGranularity,
        'unknown_terms_saved': unknownTermsSaved,
      },
      'time': {
        'local_hour': now.hour,
        'day_of_week': _getDayOfWeek(now.weekday),
      },
      'content': {
        'language': 'en', // TODO: Detect from content
        'domain': 'general', // TODO: Infer from task/content
      },
      'pii_scrubbed': true,
    };
  }

  /// Get day of week string from weekday number
  String _getDayOfWeek(int weekday) {
    const days = [
      'monday',
      'tuesday',
      'wednesday',
      'thursday',
      'friday',
      'saturday',
      'sunday',
    ];
    return days[weekday - 1];
  }
}

/// Singleton instance
final contextService = ContextService();
