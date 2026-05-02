import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';

final growthDashboardRepositoryProvider =
    Provider<GrowthDashboardRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GrowthDashboardRepository(apiClient);
});

class GrowthDashboardRepository {
  GrowthDashboardRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<GrowthDashboard> getGrowthDashboard() async {
    if (DemoDataService.isDemoMode) {
      return GrowthDashboard.placeholder();
    }
    try {
      final response = await _apiClient.get<dynamic>(
        '/experience/growth-dashboard',
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getGrowthDashboard',
      );
      return GrowthDashboard.fromJson(data);
    } on DioException catch (error) {
      throw Exception(
          _extractDioMessage(error, 'Failed to load growth dashboard'));
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  String _extractDioMessage(DioException error, String fallbackMessage) {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail is Map<String, dynamic>) {
        final message = detail['message'];
        if (message is String && message.isNotEmpty) {
          return message;
        }
      }
      final message = data['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return fallbackMessage;
  }
}
