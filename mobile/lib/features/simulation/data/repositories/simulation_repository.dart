import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';

final simulationRepositoryProvider = Provider<SimulationRepository>(
  (ref) => SimulationRepository(ref.watch(apiClientProvider)),
);

class SimulationRepository {
  SimulationRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<List<SimulationSeedModel>> getRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/simulation/recommended-seeds',
      queryParameters: {
        if (scenarioKey != null && scenarioKey.isNotEmpty)
          'scenario_key': scenarioKey,
        'limit': limit,
      },
    );
    return (response.data?['seeds'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SimulationSeedModel.fromJson)
        .toList();
  }

  Future<SimulationSessionModel> runSimulation({
    required String topic,
    required String scenarioKey,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/simulation/run',
      data: {
        'topic': topic,
        'scenario_key': scenarioKey,
      },
    );
    return SimulationSessionModel.fromJson(response.data ?? const {});
  }

  Stream<SimulationStreamEventModel> streamSimulation({
    required String topic,
    required String scenarioKey,
  }) =>
      _apiClient.postStream(
        '/simulation/run/stream',
        data: {
          'topic': topic,
          'scenario_key': scenarioKey,
        },
      ).map(
        (event) => SimulationStreamEventModel.fromJson(
          event.event,
          event.jsonData ?? const {},
        ),
      );

  Future<SimulationSessionModel> continueSimulation({
    required String sessionId,
    required String userResponse,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '/simulation/sessions/$sessionId/continue',
      data: {
        'user_response': userResponse,
      },
    );
    return SimulationSessionModel.fromJson(response.data ?? const {});
  }

  Stream<SimulationStreamEventModel> continueSimulationStream({
    required String sessionId,
    required String userResponse,
  }) =>
      _apiClient.postStream(
        '/simulation/sessions/$sessionId/continue/stream',
        data: {
          'user_response': userResponse,
        },
      ).map(
        (event) => SimulationStreamEventModel.fromJson(
          event.event,
          event.jsonData ?? const {},
        ),
      );
}
