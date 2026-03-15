import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/models/learning_path_plan_response.dart';

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
      final data = ApiResponseParser.unwrapList(response.data, action: 'getLearningPath');
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

  Future<LearningPathPlanResponse> generateLearningPlan(
      String targetNodeId,) async {
    if (DemoDataService.isDemoMode) {
      return LearningPathPlanResponse(
        planId: 'mock_plan_${DateTime.now().millisecondsSinceEpoch}',
        planSummary: '这是一个示例学习计划摘要，包含若干学习步骤与任务。',
        tasks: [
          LearningPathTaskSummary(
            id: 'mock_task_1',
            title: '学习基础概念',
            type: 'learning',
            estimatedMinutes: 25,
            status: 'pending',
          ),
        ],
      );
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.learningPathPlan(targetNodeId),
      );
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'generateLearningPlan');
      return LearningPathPlanResponse.fromJson(data);
    } on DioException catch (e) {
      throw Exception(
        (e.response?.data as Map<String, dynamic>?)?['detail'] ??
            'Failed to generate learning plan',
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }
}
