import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:sparkle/features/focus/data/models/candidate_action_model.dart';

/// Service for requesting behavior predictions from the signals pipeline
class PredictionService {
  PredictionService(this._dio);

  final Dio _dio;

  /// Request next action predictions based on context envelope
  ///
  /// This calls the /inference/run endpoint with PREDICT_NEXT_ACTIONS task type.
  /// The backend will run the signals pipeline:
  /// 1. Feature extraction (objective metrics)
  /// 2. Signal generation (decision-ready signals)
  /// 3. Candidate generation (actionable suggestions with constraints)
  ///
  /// Returns a list of 0-3 candidate actions.
  Future<List<CandidateActionModel>> requestPredictions({
    required String userId,
    required Map<String, dynamic> contextEnvelope,
  }) async {
    try {
      debugPrint('🔮 Requesting predictions for user: $userId');
      debugPrint('📊 Context: ${jsonEncode(contextEnvelope)}');

      final response = await _dio.post<Map<String, dynamic>>(
        '/inference/run',
        data: {
          'task_type': 'PREDICT_NEXT_ACTIONS',
          'user_id': userId,
          'metadata': {
            'context_envelope': jsonEncode(contextEnvelope),
          },
          'priority': 'P0',
          'budgets': {
            'max_output_tokens': 300,
            'max_cost_level': 'free_only',
          },
        },
      );

      if (response.statusCode == 200 &&
          response.data != null &&
          response.data!['ok'] == true) {
        debugPrint('✅ Received prediction response');

        // Parse content (which is a JSON string)
        final content = jsonDecode(response.data!['content'] as String);
        final candidatesData = content['candidates'] as List<dynamic>?;

        if (candidatesData == null || candidatesData.isEmpty) {
          debugPrint('ℹ️ No candidates generated');
          return [];
        }

        // Parse candidates
        final candidates = candidatesData
            .map((json) => CandidateActionModel.fromJson(json as Map<String, dynamic>))
            .toList();

        debugPrint('✨ Generated ${candidates.length} candidates:');
        for (final candidate in candidates) {
          debugPrint('  - ${candidate.actionType}: ${candidate.title} (${(candidate.confidence * 100).round()}%)');
        }

        return candidates;
      } else {
        debugPrint('⚠️ Prediction request failed: ${response.data}');
        return [];
      }
    } catch (e) {
      debugPrint('❌ Failed to request predictions: $e');
      // Don't rethrow - predictions are non-critical
      return [];
    }
  }
}
