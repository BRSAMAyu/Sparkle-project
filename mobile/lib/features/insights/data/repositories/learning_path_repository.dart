import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/insights/data/models/learning_path_node.dart';
import 'package:sparkle/features/insights/data/models/learning_path_plan_response.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

final learningPathRepositoryProvider = Provider<LearningPathRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return LearningPathRepository(apiClient);
});

class LearningPathRepository {
  LearningPathRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<LearningPathNode>> getLearningPath(String targetNodeId) async {
    if (DemoDataService.isDemoMode) {
      return _buildDemoLearningPath(targetNodeId);
    }
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.learningPath(targetNodeId),
      );
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getLearningPath',
      );
      return data
          .map((e) => LearningPathNode.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(_extractDioMessage(e, 'Failed to load learning path'));
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<LearningPathPlanResponse> generateLearningPlan(
    String targetNodeId,
  ) async {
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
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'generateLearningPlan',
      );
      return LearningPathPlanResponse.fromJson(data);
    } on DioException catch (e) {
      throw Exception(
        _extractDioMessage(e, 'Failed to generate learning plan'),
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  Future<FullPlanResponse> generateFullPathPlan(
    String targetNodeId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return FullPlanResponse(
        planId: 'mock_full_plan_${DateTime.now().millisecondsSinceEpoch}',
        planSummary: '这是一键生成的全路径计划',
        parentTaskId:
            'mock_parent_task_${DateTime.now().millisecondsSinceEpoch}',
        subtaskCount: 3,
      );
    }
    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.learningPathFullPlan(targetNodeId),
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'generateFullPathPlan',
      );
      return FullPlanResponse.fromJson(data);
    } on DioException catch (e) {
      throw Exception(
        _extractDioMessage(e, 'Failed to generate full path learning plan'),
      );
    } catch (_) {
      throw Exception('An unexpected error occurred');
    }
  }

  List<LearningPathNode> _buildDemoLearningPath(String targetNodeId) {
    final galaxy = DemoDataService().demoGalaxy;
    final nodesById = {for (final node in galaxy.nodes) node.id: node};
    final targetNode = nodesById[targetNodeId];
    if (targetNode == null) {
      return const [];
    }

    final predecessors = <String, Set<String>>{};
    for (final edge in galaxy.edges) {
      if (edge.relationType != EdgeRelationType.prerequisite) {
        continue;
      }
      predecessors
          .putIfAbsent(edge.targetId, () => <String>{})
          .add(edge.sourceId);
    }

    final orderedIds = <String>[];
    final visited = <String>{};

    void visit(String nodeId) {
      if (!visited.add(nodeId)) {
        return;
      }
      final dependencyIds = predecessors[nodeId] ?? const <String>{};
      for (final dependencyId in dependencyIds) {
        if (nodesById.containsKey(dependencyId)) {
          visit(dependencyId);
        }
      }
      orderedIds.add(nodeId);
    }

    visit(targetNodeId);

    return orderedIds.map((nodeId) {
      final node = nodesById[nodeId]!;
      final dependencyIds = predecessors[nodeId] ?? const <String>{};
      final isMastered = node.masteryScore >= 80;
      final isUnlocked = !isMastered &&
          dependencyIds.every((dependencyId) {
            final dependencyNode = nodesById[dependencyId];
            return dependencyNode != null && dependencyNode.masteryScore >= 80;
          });

      return LearningPathNode(
        id: node.id,
        name: node.name,
        status: isMastered ? 'mastered' : (isUnlocked ? 'unlocked' : 'locked'),
        isTarget: node.id == targetNodeId,
      );
    }).toList();
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
