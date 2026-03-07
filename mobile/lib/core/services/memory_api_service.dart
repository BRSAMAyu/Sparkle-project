import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';

class MemoryApiService {
  MemoryApiService(this._apiClient);

  final ApiClient _apiClient;

  Future<List<MemoryPreferenceItem>> getPreferences() async {
    final response =
        await _apiClient.get<Map<String, dynamic>>('/memory/preferences');
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MemoryPreferenceItem.fromJson)
        .toList();
    return items;
  }

  Future<List<MemoryPreferenceHistoryItem>> getPreferenceHistory(
    String prefKey,
  ) async {
    final response = await _apiClient
        .get<Map<String, dynamic>>('/memory/preferences/$prefKey/history');
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MemoryPreferenceHistoryItem.fromJson)
        .toList();
    return items;
  }

  Future<List<MemoryGoalItem>> getGoals({
    String? status,
    bool includeExpired = false,
    int limit = 20,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/goals',
      queryParameters: {
        if (status != null) 'status': status,
        'include_expired': includeExpired,
        'limit': limit,
      },
    );
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(MemoryGoalItem.fromJson)
        .toList();
    return items;
  }

  Future<List<EpisodicMemoryItem>> getEpisodic({
    DateTime? start,
    DateTime? end,
    int limit = 20,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/episodic',
      queryParameters: {
        if (start != null) 'start': start.toIso8601String(),
        if (end != null) 'end': end.toIso8601String(),
        'limit': limit,
      },
    );
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(EpisodicMemoryItem.fromJson)
        .toList();
    return items;
  }

  Future<void> retractMemory({
    required String type,
    required String id,
    String? reason,
  }) async {
    await _apiClient.post<void>(
      '/memory/retract',
      data: {
        'type': type,
        'id': id,
        if (reason != null) 'reason': reason,
      },
    );
  }

  Future<MemoryCorrectionResult> correctMemory({
    required String type,
    required String id,
    required String action,
    String? reason,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/memory/correct',
      data: {
        'type': type,
        'id': id,
        'action': action,
        if (reason != null) 'reason': reason,
      },
    );
    final item = response.data?['item'] as Map<String, dynamic>? ?? {};
    return MemoryCorrectionResult.fromJson(item);
  }

  Future<MemorySettingsModel> getMemorySettings() async {
    final response =
        await _apiClient.get<Map<String, dynamic>>('/memory/settings');
    final payload = response.data ?? <String, dynamic>{};
    return MemorySettingsModel.fromJson(payload);
  }

  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      '/memory/settings',
      data: settings.toJson(),
    );
    final payload = response.data ?? <String, dynamic>{};
    return MemorySettingsModel.fromJson(payload);
  }
}

final memoryApiServiceProvider = Provider<MemoryApiService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return MemoryApiService(apiClient);
});
