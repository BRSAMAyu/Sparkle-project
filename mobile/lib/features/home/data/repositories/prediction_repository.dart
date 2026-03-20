import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';

final predictionRepositoryProvider = Provider<PredictionRepository>(
  (ref) => PredictionRepository(ref.read(apiClientProvider)),
);

class PredictionRepository {
  PredictionRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<PredictionInsightData?> getRealtimeNextStep({
    required String partialText,
    String? activePlanId,
    String surface = 'chat_input',
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.predictiveRealtimeNextStep,
      data: {
        'partial_text': partialText,
        if (activePlanId != null) 'active_plan_id': activePlanId,
        'surface': surface,
      },
    );
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getRealtimeNextStep',
    );
    return PredictionInsightData.fromJson(data);
  }

  Future<Map<String, dynamic>> getPredictionAnalytics({int days = 7}) async {
    final response = await _apiClient.get<dynamic>(
      '${ApiEndpoints.predictiveAnalytics}?days=$days',
    );
    return ApiResponseParser.unwrapMap(
      response.data,
      action: 'getPredictionAnalytics',
    );
  }
}
