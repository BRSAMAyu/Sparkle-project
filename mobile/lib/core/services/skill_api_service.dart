import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/models/skill_models.dart';
import 'package:sparkle/core/network/api_client.dart';

class SkillApiService {
  SkillApiService(this._apiClient);

  final ApiClient _apiClient;

  Future<List<SkillItemModel>> getSkills() async {
    final response = await _apiClient.get<Map<String, dynamic>>('/skills');
    return (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(SkillItemModel.fromJson)
        .toList();
  }

  Future<SkillItemModel> createSkill(Map<String, dynamic> payload) async {
    final response =
        await _apiClient.post<Map<String, dynamic>>('/skills', data: payload);
    return SkillItemModel.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<SkillItemModel> updateSkill(
    String id,
    Map<String, dynamic> payload,
  ) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      '/skills/$id',
      data: payload,
    );
    return SkillItemModel.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<void> deleteSkill(String id) async {
    await _apiClient.delete<void>('/skills/$id');
  }

  Future<SkillItemModel> toggleSkill(String id, bool active) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/skills/$id/toggle',
      data: {'active': active},
    );
    return SkillItemModel.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<SkillDraftModel> extractDraft(Map<String, dynamic> payload) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/skills/drafts/extract',
      data: payload,
    );
    final draft = response.data?['draft'] as Map<String, dynamic>? ?? {};
    return SkillDraftModel.fromJson(draft);
  }

  Future<void> recordDraftOutcome(bool accepted) async {
    await _apiClient.post<void>(
      '/skills/drafts/outcome',
      data: {'accepted': accepted},
    );
  }

  Future<List<SharedSkillItemModel>> getSharedSkills({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/skills/shared',
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    return (response.data?['items'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(SharedSkillItemModel.fromJson)
        .toList();
  }

  Future<Map<String, dynamic>> shareSkill(String id) async {
    final response =
        await _apiClient.post<Map<String, dynamic>>('/skills/$id/share');
    return response.data ?? <String, dynamic>{};
  }

  Future<SkillItemModel> unshareSkill(String id) async {
    final response =
        await _apiClient.post<Map<String, dynamic>>('/skills/$id/unshare');
    return SkillItemModel.fromJson(response.data ?? <String, dynamic>{});
  }

  Future<SkillItemModel> forkSharedSkill(String id) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/skills/shared/$id/fork',
    );
    return SkillItemModel.fromJson(response.data ?? <String, dynamic>{});
  }
}

final skillApiServiceProvider = Provider<SkillApiService>((ref) {
  final client = ref.watch(apiClientProvider);
  return SkillApiService(client);
});
