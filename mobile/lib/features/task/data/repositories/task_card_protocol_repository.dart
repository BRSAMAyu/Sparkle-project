import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/task/data/models/task_card_protocol.dart';

/// TASK-001: Repository for TaskCardProtocol.
///
/// Hits /tasks/{id}/card-protocol. Returns null on 404 / network failure so
/// the UI can degrade gracefully (legacy task guide panel still works).
class TaskCardProtocolRepository {
  TaskCardProtocolRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<TaskCardProtocol?> fetch(String taskId) async {
    try {
      final response = await _apiClient.get<dynamic>(
        ApiEndpoints.taskCardProtocol(taskId),
      );
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getTaskCardProtocol',
      );
      return TaskCardProtocol.fromJson(data);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      // soft fail; log via interceptor; UI shows legacy panel
      return null;
    } catch (_) {
      return null;
    }
  }
}

final taskCardProtocolRepositoryProvider =
    Provider<TaskCardProtocolRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return TaskCardProtocolRepository(apiClient);
});

final taskCardProtocolProvider =
    FutureProvider.family<TaskCardProtocol?, String>((ref, taskId) async {
  if (taskId.isEmpty) return null;
  final repo = ref.watch(taskCardProtocolRepositoryProvider);
  return repo.fetch(taskId);
});
