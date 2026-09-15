import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

final toolHistoryRepositoryProvider = Provider<ToolHistoryRepository>(
  (ref) => ToolHistoryRepository(ref, ref.watch(apiClientProvider)),
);

class ToolHistoryRepository {
  ToolHistoryRepository(this._ref, this._apiClient);

  final Ref _ref;
  final ApiClient _apiClient;

  Future<int?> recordBreathingCompleted({
    required String pattern,
    required int durationMinutes,
    required int roundsCompleted,
    required String surface,
    required bool completedFromBackground,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'breathing',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'pattern': pattern,
      'duration_minutes': durationMinutes,
      'rounds_completed': roundsCompleted,
      'surface': surface,
      'completed_from_background': completedFromBackground,
    });
  }

  Future<int?> recordCalculatorEvaluated({
    required String complexity,
    required String surface,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'calculator',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'complexity': complexity,
      'surface': surface,
    });
  }

  Future<int?> recordTranslatorCompleted({
    required String sourceLanguage,
    required String targetLanguage,
    required int textLength,
    required String surface,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'translator',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'source_language': sourceLanguage,
      'target_language': targetLanguage,
      'text_length': textLength,
      'surface': surface,
    });
  }

  Future<int?> recordVocabularyLookupCompleted({
    required String lookupTerm,
    required String surface,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'vocabulary_lookup',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'lookup_term': lookupTerm,
      'surface': surface,
    });
  }

  Future<int?> recordNotesSynced({
    required int charCount,
    required int lineCount,
    required String surface,
    String? taskId,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'notes',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'char_count': charCount,
      'line_count': lineCount,
      'task_id': taskId,
      'surface': surface,
    });
  }

  Future<int?> recordFlashCapsuleSaved({
    required String subject,
    required String errorType,
    required String surface,
    String? taskId,
  }) async {
    return _recordClientToolEvent({
      'tool_name': 'flash_capsule',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'subject': subject,
      'error_type': errorType,
      'task_id': taskId,
      'surface': surface,
    });
  }

  Future<bool> forgetToolEvent(int id) async {
    final accessToken =
        await _ref.read(authRepositoryProvider).getAccessToken();
    if (accessToken == null || accessToken.isEmpty) {
      return false;
    }

    try {
      await _apiClient.delete<dynamic>(
        '${ApiEndpoints.toolHistoryClientEvents}/$id',
      );
      return true;
    } catch (error) {
      debugPrint('Failed to forget tool history: $error');
      return false;
    }
  }

  Future<int?> _recordClientToolEvent(Map<String, dynamic> payload) async {
    final accessToken =
        await _ref.read(authRepositoryProvider).getAccessToken();
    if (accessToken == null || accessToken.isEmpty) {
      return null;
    }

    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.toolHistoryClientEvents,
        data: payload,
      );
      final data = response.data;
      if (data is Map<String, dynamic>) {
        return data['id'] as int?;
      }
      if (data is Map) {
        return data['id'] as int?;
      }
    } catch (error) {
      debugPrint('Failed to record tool history: $error');
    }
    return null;
  }
}
