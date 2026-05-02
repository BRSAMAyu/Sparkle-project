import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/task/data/models/priority_reasoning.dart';

class PriorityReasoningRepository {
  PriorityReasoningRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<PriorityReasoning?> fetch(
    String taskId, {
    bool refresh = false,
    int retryCount = 1,
  }) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.taskPriorityReasoning(taskId),
        queryParameters: refresh ? {'refresh': true} : null,
      );
      if (response.statusCode == 202) {
        if (retryCount <= 0) return null;
        await Future<void>.delayed(const Duration(milliseconds: 450));
        return fetch(taskId, retryCount: retryCount - 1);
      }
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getTaskPriorityReasoning',
      );
      if (data.isEmpty) return null;
      return PriorityReasoning.fromJson(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      return null;
    } catch (_) {
      return null;
    }
  }
}

final priorityReasoningRepositoryProvider =
    Provider<PriorityReasoningRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return PriorityReasoningRepository(apiClient);
});

final priorityReasoningProvider =
    FutureProvider.family<PriorityReasoning?, String>((ref, taskId) async {
  if (taskId.isEmpty) return null;
  final repository = ref.watch(priorityReasoningRepositoryProvider);
  return repository.fetch(taskId);
});
