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
      final response =
          await _apiClient.get(ApiEndpoints.learningPath(targetNodeId));
      final List<dynamic> data = response.data;
      return data.map((e) => LearningPathNode.fromJson(e)).toList();
    } on DioException catch (e) {
      throw e.response?.data['detail'] ?? 'Failed to load learning path';
    } catch (_) {
      throw 'An unexpected error occurred';
    }
  }
}
