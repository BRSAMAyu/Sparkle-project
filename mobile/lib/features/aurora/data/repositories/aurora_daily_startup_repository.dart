import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/aurora/data/models/aurora_daily_startup_message.dart';

final auroraDailyStartupRepositoryProvider =
    Provider<AuroraDailyStartupRepository>(
  (ref) => AuroraDailyStartupRepository(ref.read(apiClientProvider)),
);

class AuroraDailyStartupRepository {
  AuroraDailyStartupRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<AuroraDailyStartupMessage> getDailyStartup({
    required String planId,
  }) async {
    if (DemoDataService.isDemoMode) {
      return const AuroraDailyStartupMessage(
        message:
            '早上好，今天是你备考计算机网络的第 2 天。今天的核心任务是 TCP 流量控制，预计 45 分钟。昨天做得很好，推进很顺利，今天我们保持这个手感。准备好了吗？',
        todayFocus: 'TCP 流量控制',
        estimatedMinutes: 45,
        adjustmentReason: '昨天完成率 90%，今天保持当前节奏。',
      );
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.auroraDailyStartup,
      queryParameters: {'plan_id': planId},
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getDailyStartup',
    );
    return AuroraDailyStartupMessage.fromJson(payload);
  }

  Future<AuroraComebackContext> getComebackContext() async {
    if (DemoDataService.isDemoMode) {
      return const AuroraComebackContext.empty();
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.auroraComebackContext,
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getComebackContext',
    );
    if (payload.isEmpty) {
      return const AuroraComebackContext.empty();
    }
    return AuroraComebackContext.fromJson(payload);
  }
}
