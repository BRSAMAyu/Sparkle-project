import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/galaxy_model.dart';
import 'package:sparkle/data/models/knowledge_detail_model.dart';
import 'package:sparkle/core/services/demo_data_service.dart';

final galaxyRepositoryProvider = Provider<GalaxyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GalaxyRepository(apiClient);
});

class GalaxyRepository {
  final ApiClient _apiClient;

  GalaxyRepository(this._apiClient);

  Future<GalaxyGraphResponse> getGraph({double zoomLevel = 1.0}) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoGalaxy;
    }
    try {
      final response = await _apiClient.get(
        ApiEndpoints.galaxyGraph,
        queryParameters: {'zoom_level': zoomLevel},
      );
      return GalaxyGraphResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Failed to load galaxy graph';
    } catch (_) {
      throw 'An unexpected error occurred';
    }
  }

  Future<void> sparkNode(String id) async {
    if (DemoDataService.isDemoMode) {
      // Simulate success
      return;
    }
    try {
      await _apiClient.post(ApiEndpoints.sparkNode(id));
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to spark node');
    }
  }

  Stream<SSEEvent> getGalaxyEventsStream() {
    if (DemoDataService.isDemoMode) {
      // In the future we can simulate events here
      return const Stream.empty();
    }
    return _apiClient.getStream(ApiEndpoints.galaxyEvents);
  }

  /// Get detailed information about a specific knowledge node
  Future<KnowledgeDetailResponse> getNodeDetail(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().getDemoNodeDetail(nodeId);
    }
    try {
      final response = await _apiClient.get(ApiEndpoints.galaxyNodeDetail(nodeId));
      return KnowledgeDetailResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Failed to load node detail';
    } catch (_) {
      throw 'An unexpected error occurred';
    }
  }

  /// Predict the next best node to learn
  Future<KnowledgeDetailResponse?> predictNextNode() async {
    if (DemoDataService.isDemoMode) {
      // Return a random unlocked node or locked neighbor
      return null;
    }
    try {
      final response = await _apiClient.post(ApiEndpoints.galaxyPredictNext);
      if (response.data == null) return null;
      return KnowledgeDetailResponse.fromJson(response.data);
    } catch (e) {
      // It's okay if prediction fails, just return null
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<List<GalaxySearchResult>> searchNodes(String query) async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    try {
      final response = await _apiClient.post(
        ApiEndpoints.galaxySearch,
        data: {'query': query},
      );
      final searchResponse = GalaxySearchResponse.fromJson(response.data);
      return searchResponse.results;
    } on DioException catch (e) {
      return [];
    } catch (_) {
      return [];
    }
  }

  /// Toggle favorite status for a knowledge node
  Future<void> toggleFavorite(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post(ApiEndpoints.galaxyNodeFavorite(nodeId));
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to toggle favorite');
    }
  }

  /// Pause or resume decay for a knowledge node
  Future<void> pauseDecay(String nodeId, bool pause) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post(
        ApiEndpoints.galaxyNodeDecayPause(nodeId),
        data: {'pause': pause},
      );
    } on DioException catch (e) {
      throw Exception(e.response?.data?['detail'] ?? 'Failed to update decay status');
    }
  }
}