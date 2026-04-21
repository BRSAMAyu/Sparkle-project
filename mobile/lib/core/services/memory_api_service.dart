import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';

class MemoryApiService {
  MemoryApiService(this._apiClient);

  final ApiClient _apiClient;

  static final MemorySettingsModel _defaultMemorySettings = MemorySettingsModel(
    enabled: true,
    allowPreferences: true,
    allowGoals: true,
    allowEpisodic: true,
    allowInferredEpisodic: true,
    captureLevel: 'medium',
    blockedPrefKeys: <String>[],
    blockedSources: <String>[],
  );
  static final PushOptInSettingsModel _defaultPushSettings =
      PushOptInSettingsModel(
    enabled: false,
    allowCommitmentFollowUp: false,
    allowEngagementRecovery: false,
    quietHoursStart: '22:00',
    quietHoursEnd: '08:00',
    timezone: 'Asia/Shanghai',
  );

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

  Future<List<PendingCommitmentItem>> getPendingCommitments() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/accountability/pending',
    );
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(PendingCommitmentItem.fromJson)
        .toList();
    return items;
  }

  Future<List<RecentSceneSummaryItem>> getRecentScenes() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/accountability/recent-scenes',
    );
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(RecentSceneSummaryItem.fromJson)
        .toList();
    return items;
  }

  Future<ForesightHintSummaryItem?> getForesightHintSummary() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/accountability/foresight-hint',
    );
    final payload = response.data ?? <String, dynamic>{};
    final hintText = payload['hint_text'] as String?;
    if (hintText == null || hintText.isEmpty) {
      return null;
    }
    return ForesightHintSummaryItem.fromJson(payload);
  }

  Future<PendingCommitmentItem> resolvePendingCommitment(String id) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/memory/accountability/pending/$id/resolve',
    );
    return PendingCommitmentItem.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<List<UnresolvedConflictItem>> getUnresolvedConflicts() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/unresolved-conflicts',
    );
    final items = (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(UnresolvedConflictItem.fromJson)
        .toList();
    return items;
  }

  Future<UnresolvedConflictItem> arbitrateUnresolvedConflict(
    String id, {
    required String selection,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/memory/unresolved-conflicts/$id/arbitrate',
      data: {'selection': selection},
    );
    return UnresolvedConflictItem.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }

  Future<WorkingMemorySessionModel> getWorkingMemorySession({
    String? sessionId,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/memory/working-memory/session',
      queryParameters: {
        if (sessionId != null && sessionId.isNotEmpty) 'session_id': sessionId,
      },
    );
    return WorkingMemorySessionModel.fromJson(
      response.data ?? <String, dynamic>{},
    );
  }

  Future<void> forgetWorkingMemoryEntry(
    String entryId, {
    String? sessionId,
  }) async {
    await _apiClient.post<void>(
      '/memory/working-memory/$entryId/forget',
      queryParameters: {
        if (sessionId != null && sessionId.isNotEmpty) 'session_id': sessionId,
      },
    );
  }

  Future<WorkingMemoryItem> markWorkingMemoryEntryCorrect(
    String entryId, {
    String? sessionId,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/memory/working-memory/$entryId/mark-correct',
      queryParameters: {
        if (sessionId != null && sessionId.isNotEmpty) 'session_id': sessionId,
      },
    );
    return WorkingMemoryItem.fromJson(response.data ?? <String, dynamic>{});
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
    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/memory/settings');
      final payload = response.data ?? <String, dynamic>{};
      return MemorySettingsModel.fromJson(payload);
    } on DioException catch (error) {
      if (_shouldUseLocalFallback(error)) {
        return _defaultMemorySettings;
      }
      rethrow;
    }
  }

  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/memory/settings',
        data: settings.toJson(),
      );
      final payload = response.data ?? <String, dynamic>{};
      return MemorySettingsModel.fromJson(payload);
    } on DioException catch (error) {
      if (_shouldUseLocalFallback(error)) {
        return settings;
      }
      rethrow;
    }
  }

  Future<PushOptInSettingsModel> getPushSettings() async {
    try {
      final response =
          await _apiClient.get<Map<String, dynamic>>('/memory/push-settings');
      final payload = response.data ?? <String, dynamic>{};
      return PushOptInSettingsModel.fromJson(payload);
    } on DioException catch (error) {
      if (_shouldUseLocalFallback(error)) {
        return _defaultPushSettings;
      }
      rethrow;
    }
  }

  Future<PushOptInSettingsModel> updatePushSettings(
    PushOptInSettingsModel settings,
  ) async {
    try {
      final response = await _apiClient.put<Map<String, dynamic>>(
        '/memory/push-settings',
        data: settings.toJson(),
      );
      final payload = response.data ?? <String, dynamic>{};
      return PushOptInSettingsModel.fromJson(payload);
    } on DioException catch (error) {
      if (_shouldUseLocalFallback(error)) {
        return settings;
      }
      rethrow;
    }
  }

  bool _shouldUseLocalFallback(DioException error) {
    final statusCode = error.response?.statusCode;
    return statusCode == 401 || statusCode == 403;
  }
}

final memoryApiServiceProvider = Provider<MemoryApiService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return MemoryApiService(apiClient);
});
