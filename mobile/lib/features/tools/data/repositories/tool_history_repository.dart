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

  Future<void> recordBreathingCompleted({
    required String pattern,
    required int durationMinutes,
    required int roundsCompleted,
    required String surface,
    required bool completedFromBackground,
  }) async {
    await _recordClientToolEvent({
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

  Future<void> recordCalculatorEvaluated({
    required String complexity,
    required String surface,
  }) async {
    await _recordClientToolEvent({
      'tool_name': 'calculator',
      'used_at': DateTime.now().toIso8601String(),
      'success': true,
      'complexity': complexity,
      'surface': surface,
    });
  }

  Future<void> _recordClientToolEvent(Map<String, dynamic> payload) async {
    final accessToken =
        await _ref.read(authRepositoryProvider).getAccessToken();
    if (accessToken == null || accessToken.isEmpty) {
      return;
    }

    try {
      await _apiClient.post<dynamic>(
        ApiEndpoints.toolHistoryClientEvents,
        data: payload,
      );
    } catch (error) {
      debugPrint('Failed to record tool history: $error');
    }
  }
}
