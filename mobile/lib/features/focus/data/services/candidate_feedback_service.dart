import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Service for sending candidate action feedback to backend
class CandidateFeedbackService {
  CandidateFeedbackService(this._dio);

  final Dio _dio;

  /// Record user feedback on a candidate action
  ///
  /// Feedback types:
  /// - "accept": User clicked on the candidate action
  /// - "ignore": User saw but didn't interact (implicit)
  /// - "dismiss": User explicitly dismissed the candidate
  Future<void> recordFeedback({
    required String candidateId,
    required String actionType,
    required String feedbackType,
    bool executed = false,
    Map<String, dynamic>? completionResult,
    Map<String, dynamic>? contextSnapshot,
  }) async {
    try {
      debugPrint('📤 Sending feedback: $candidateId ($feedbackType)');

      final response = await _dio.post(
        '/signals/feedback',
        data: {
          'candidate_id': candidateId,
          'action_type': actionType,
          'feedback_type': feedbackType,
          'executed': executed,
          'completion_result': completionResult,
          'context_snapshot': contextSnapshot,
        },
      );

      if (response.statusCode == 200 && response.data['ok'] == true) {
        debugPrint('✅ Feedback recorded: ${response.data['feedback_id']}');
      } else {
        debugPrint('⚠️ Feedback recording failed: ${response.data}');
      }
    } catch (e) {
      debugPrint('❌ Failed to record feedback: $e');
      // Don't rethrow - feedback is non-critical
    }
  }

  /// Get feedback statistics for current user
  Future<Map<String, dynamic>?> getFeedbackStats() async {
    try {
      final response = await _dio.get('/signals/feedback/stats');

      if (response.statusCode == 200 && response.data['ok'] == true) {
        return {
          'total_count': response.data['total_count'],
          'ctr_percent': response.data['ctr_percent'],
          'completion_rate_percent': response.data['completion_rate_percent'],
          'feedback_type_breakdown': response.data['feedback_type_breakdown'],
          'action_type_breakdown': response.data['action_type_breakdown'],
        };
      }
      return null;
    } catch (e) {
      debugPrint('❌ Failed to get feedback stats: $e');
      return null;
    }
  }
}
