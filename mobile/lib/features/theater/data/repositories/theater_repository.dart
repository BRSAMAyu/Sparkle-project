import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';

final theaterRepositoryProvider = Provider<TheaterRepository>(
  (ref) => TheaterRepository(ref.watch(apiClientProvider)),
);

class TheaterRepository {
  TheaterRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<TheaterPrediction> generatePrediction({
    required String topic,
    String? targetNodeId,
    int horizonDays = 14,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.theaterGeneratePrediction,
      data: {
        'topic': topic,
        if (targetNodeId != null && targetNodeId.isNotEmpty)
          'target_node_id': targetNodeId,
        'horizon_days': horizonDays,
      },
    );
    return TheaterPrediction.fromJson(response.data ?? const {});
  }

  Future<TheaterWhatIfResult> simulateWhatIf({
    required String predictionId,
    required String routeId,
    required String skipNodeId,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.theaterWhatIf,
      data: {
        'prediction_id': predictionId,
        'route_id': routeId,
        'skip_node_id': skipNodeId,
      },
    );
    return TheaterWhatIfResult.fromJson(response.data ?? const {});
  }

  Future<TheaterSnapshot> saveSnapshot({
    required String predictionId,
    required String routeId,
    String? note,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.theaterSnapshots,
      data: {
        'prediction_id': predictionId,
        'route_id': routeId,
        if (note != null && note.isNotEmpty) 'note': note,
      },
    );
    return TheaterSnapshot.fromJson(response.data ?? const {});
  }

  Future<TheaterAdoptionResult> adoptRoute({
    required String predictionId,
    required String routeId,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.theaterAdopt(predictionId),
      data: {
        'prediction_id': predictionId,
        'route_id': routeId,
      },
    );
    return TheaterAdoptionResult.fromJson(response.data ?? const {});
  }

  Future<TheaterAccuracySummary> recordActuals({
    required String predictionId,
    double? actualCompletionRate,
    double? actualMastery,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.theaterActuals(predictionId),
      data: {
        if (actualCompletionRate != null)
          'actual_completion_rate': actualCompletionRate,
        if (actualMastery != null) 'actual_mastery': actualMastery,
      },
    );
    return TheaterAccuracySummary.fromJson(response.data ?? const {});
  }

  Future<TheaterAccuracySummary?> getAccuracy(String predictionId) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.theaterAccuracy(predictionId),
    );
    final data = response.data;
    if (data == null || data.isEmpty) {
      return null;
    }
    return TheaterAccuracySummary.fromJson(data);
  }
}
