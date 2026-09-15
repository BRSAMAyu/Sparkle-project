import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/goal/data/models/scenario_pack_models.dart';

class ScenarioPackService {
  const ScenarioPackService(this._apiClient);

  final ApiClient _apiClient;

  Future<List<ScenarioPackSummary>> listPacks() async {
    final response = await _apiClient.get<dynamic>('/scenario-packs');
    final data = response.data;
    if (data is List) {
      return data
          .map((e) => ScenarioPackSummary.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    return const [];
  }

  Future<ScenarioPackDetail?> getPack(String packId) async {
    final response = await _apiClient.get<dynamic>('/scenario-packs/$packId');
    final data = response.data;
    if (data is Map) {
      return ScenarioPackDetail.fromJson(Map<String, dynamic>.from(data));
    }
    return null;
  }

  Future<bool> assignPack({required String packId, required String goalId}) async {
    await _apiClient.post<dynamic>(
      '/scenario-packs/$packId/assign',
      data: {'goal_id': goalId},
    );
    return true;
  }

  Future<JourneyProgress> getProgress({required String goalId}) async {
    final response = await _apiClient.get<dynamic>(
      '/scenario-packs/progress/$goalId',
    );
    final data = response.data;
    if (data is Map) {
      return JourneyProgress.fromJson(Map<String, dynamic>.from(data));
    }
    return const JourneyProgress();
  }
}

final scenarioPackServiceProvider = Provider<ScenarioPackService>(
  (ref) => ScenarioPackService(ref.read(apiClientProvider)),
);

final scenarioPacksProvider = FutureProvider<List<ScenarioPackSummary>>(
  (ref) => ref.read(scenarioPackServiceProvider).listPacks(),
);
