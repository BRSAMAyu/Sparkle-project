import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_calibration_card.dart';

final auroraCalibrationRepositoryProvider =
    Provider<AuroraCalibrationRepository>(
  (ref) => AuroraCalibrationRepository(ref.read(apiClientProvider)),
);

class AuroraCalibrationRepository {
  AuroraCalibrationRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<AuroraCalibrationSurface> getCalibrationCards({
    String? planId,
  }) async {
    if (DemoDataService.isDemoMode) {
      return AuroraCalibrationSurface.fromJson(
        DemoDataService().demoAuroraCalibrationCards(planId: planId),
      );
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.auroraCalibrationCards,
      queryParameters: {
        if (planId != null && planId.trim().isNotEmpty) 'plan_id': planId,
      },
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getCalibrationCards',
    );
    return AuroraCalibrationSurface.fromJson(payload);
  }

  Future<void> respondToCalibrationCard({
    required String cardId,
    required AuroraCalibrationResponse response,
    String? reason,
  }) async {
    if (DemoDataService.isDemoMode) {
      DemoDataService().respondToDemoAuroraCalibrationCard(
        cardId: cardId,
        response: response.apiValue,
      );
      return;
    }

    await _apiClient.post<dynamic>(
      ApiEndpoints.auroraCalibrationCardRespond(cardId),
      data: {
        'response': response.apiValue,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason,
      },
    );
  }
}
