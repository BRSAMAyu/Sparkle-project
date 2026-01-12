import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

final galaxyRepositoryProvider = Provider<GalaxyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GalaxyRepository(apiClient);
});

class GalaxyRepository {
  GalaxyRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<GalaxyGraphResponse> getGraph({double zoomLevel = 1.0}) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoGalaxy;
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.galaxyGraph,
        queryParameters: {'zoom_level': zoomLevel},
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Galaxy graph payload is missing');
      }
      return GalaxyGraphResponse.fromJson(payload);
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to load galaxy graph',
        ),
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<void> sparkNode(String id) async {
    if (DemoDataService.isDemoMode) {
      // Simulate success
      return;
    }
    try {
      await _apiClient.post<void>(ApiEndpoints.sparkNode(id));
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to spark node',
        ),
      );
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
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.galaxyNodeDetail(nodeId),
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Node detail payload is missing');
      }
      return KnowledgeDetailResponse.fromJson(payload);
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to load node detail',
        ),
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  /// Predict the next best node to learn
  Future<KnowledgeDetailResponse?> predictNextNode() async {
    if (DemoDataService.isDemoMode) {
      // Return a random unlocked node or locked neighbor
      return null;
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxyPredictNext,
      );
      final payload = response.data;
      if (payload == null) return null;
      return KnowledgeDetailResponse.fromJson(payload);
    } catch (e) {
      // It's okay if prediction fails, just return null
      return null;
    }
  }

  Future<List<GalaxySearchResult>> searchNodes(String query) async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxySearch,
        data: {'query': query},
      );
      final payload = response.data;
      if (payload == null) return [];
      final searchResponse = GalaxySearchResponse.fromJson(payload);
      return searchResponse.results;
    } on DioException {
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
      await _apiClient.post<void>(ApiEndpoints.galaxyNodeFavorite(nodeId));
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to toggle favorite',
        ),
      );
    }
  }

  /// Pause or resume decay for a knowledge node
  Future<void> pauseDecay(String nodeId, bool pause) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post<void>(
        ApiEndpoints.galaxyNodeDecayPause(nodeId),
        data: {'pause': pause},
      );
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to update decay status',
        ),
      );
    }
  }

  String _extractDetail(DioException exception, {required String defaultMessage}) {
    final data = exception.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
    }
    return defaultMessage;
  }
}
