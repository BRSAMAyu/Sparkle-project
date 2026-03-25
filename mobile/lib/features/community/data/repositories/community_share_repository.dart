import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';

final communityShareRepositoryProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final eventStream = ref.watch(appEventStreamServiceProvider);
  return CommunityShareRepository(apiClient, eventStream);
});

class CommunityShareRepository {
  CommunityShareRepository(this._apiClient, this._eventStream);

  final ApiClient _apiClient;
  final AppEventStreamService _eventStream;

  Future<Map<String, dynamic>> shareResource({
    required String resourceType,
    required String resourceId,
    String? targetGroupId,
    String? targetUserId,
    String permission = 'view',
    String? comment,
  }) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.communityShare,
      data: {
        'resource_type': resourceType,
        'resource_id': resourceId,
        'target_group_id': targetGroupId,
        'target_user_id': targetUserId,
        'permission': permission,
        'comment': comment,
      },
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to share resource');
    }

    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'shareResource',
    );
    await _eventStream.recordSharedResourceAction(
      action: 'created',
      sharedResourceId: data['id']?.toString() ?? '',
      resourceType: resourceType,
      resourceId: resourceId,
    );
    return data;
  }

  Future<Map<String, dynamic>> adoptResource({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) {
      throw Exception('Shared resource id is empty');
    }
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.adoptSharedResource(trimmedId),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to adopt shared resource');
    }
    final data =
        ApiResponseParser.unwrapMap(response.data, action: 'adoptResource');
    await _eventStream.recordSharedResourceAction(
      action: 'adopted',
      sharedResourceId: sharedResourceId,
      resourceType: data['resource_type']?.toString() ?? 'unknown',
      adoptedEntityId: data['new_resource_id']?.toString(),
    );
    return data;
  }
}
