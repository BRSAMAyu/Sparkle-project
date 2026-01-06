import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/domain/models/learning_path_node.dart';

final learningPathRepositoryProvider = Provider<LearningPathRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LearningPathRepository(apiClient);
});

class LearningPathRepository {
  LearningPathRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<LearningPathNode>> getLearningPath(String targetNodeId) async {
    if (DemoDataService.isDemoMode) {
      // Mock data for demo
      return [
        LearningPathNode(id: '1', name: 'Base Concept', status: 'mastered'),
        LearningPathNode(
            id: '2', name: 'Intermediate Step', status: 'unlocked',),
        LearningPathNode(
            id: targetNodeId,
            name: 'Target Concept',
            status: 'locked',
            isTarget: true,),
      ];
    }
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.learningPath(targetNodeId),
      );
      final data = response.data as List<dynamic>;
      return data
          .map((e) => LearningPathNode.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(
        (e.response?.data as Map<String, dynamic>?)?['detail'] ??
            'Failed to load learning path',
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }
}
