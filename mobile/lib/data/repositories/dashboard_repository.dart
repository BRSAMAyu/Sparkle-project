import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

final dashboardRepositoryProvider = Provider<DashboardRepository>(
    (ref) => DashboardRepository(ref.read(apiClientProvider)),);

class DashboardRepository {
  DashboardRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<Map<String, dynamic>> getDashboardStatus() async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoDashboard;
    }
    final response = await _apiClient.get<dynamic>(ApiEndpoints.dashboardStatus);
    return response.data as Map<String, dynamic>;
  }
}
