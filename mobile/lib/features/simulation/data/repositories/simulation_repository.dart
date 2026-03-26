import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';

final simulationRepositoryProvider = Provider<SimulationRepository>(
  (ref) => SimulationRepository(ref.watch(apiClientProvider)),
);

class SimulationRepository {
  SimulationRepository(this._apiClient);

  final ApiClient _apiClient;

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
  }) => _apiClient
      .postStream(
        '/simulation/run/stream',
        data: {
          'topic': topic,
          'scenario_key': scenarioKey,
        },
      )
      .map(
        (event) => SimulationStreamEventModel.fromJson(
          event.event,
          event.jsonData ?? const {},
        ),
      );
}
