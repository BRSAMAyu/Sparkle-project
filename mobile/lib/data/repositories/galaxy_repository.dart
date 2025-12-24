import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

final galaxyRepositoryProvider = Provider<GalaxyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GalaxyRepository(apiClient);
});

class GalaxyRepository {
  final ApiClient _apiClient;

  GalaxyRepository(this._apiClient);

  Future<GalaxyGraphResponse> getGraph() async {
    try {
      final response = await _apiClient.get(ApiEndpoints.galaxyGraph);
      return GalaxyGraphResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Failed to load galaxy graph';
    } catch (e) {
      throw 'An unexpected error occurred';
    }
  }

  Future<void> sparkNode(String id) async {
    try {
      await _apiClient.post(ApiEndpoints.sparkNode(id));
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to spark node');
    }
  }

  Stream<SSEEvent> getGalaxyEventsStream() {
    return _apiClient.getStream(ApiEndpoints.galaxyEvents);
  }
}
