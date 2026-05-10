import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

final communityShareRepositoryProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final eventStream = ref.watch(appEventStreamServiceProvider);
  return CommunityShareRepository(apiClient, eventStream);
});

class CommunityShareRepository {
  CommunityShareRepository(this._apiClient, this._eventStream);

  final ApiClient _apiClient;
  final AppEventStreamService _eventStream;

  /// Fetch shared resources with quality scoring info.
  Future<List<SharedResourceInfo>> fetchSharedResources({
    String sort = 'quality',
    String? resourceType,
    int limit = 20,
  }) async {
    final queryParams = <String, dynamic>{
      'sort': sort,
      'limit': limit,
    };
    if (resourceType != null) {
      queryParams['resource_type'] = resourceType;
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.communityResources,
      queryParameters: queryParams,
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to fetch shared resources');
    }

    final data = response.data;
    // Backend returns {"resources": [...], "total": N, ...}
    List<dynamic> items;
    if (data is List) {
      items = data;
    } else if (data is Map<String, dynamic> && data['resources'] is List) {
      items = data['resources'] as List;
    } else {
      return [];
    }

    return items
        .whereType<Map<String, dynamic>>()
        .map((json) => SharedResourceInfo.fromJson(json))
        .toList();
  }

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

  /// Reject a recommended community resource so it does not appear
  /// in future suggestions for this user.
  Future<void> rejectResource({
    required String sharedResourceId,
  }) async {
    final trimmedId = sharedResourceId.trim();
    if (trimmedId.isEmpty) return;

    try {
      await _apiClient.post<dynamic>(
        '/community/shared-resources/$trimmedId/reject',
      );
    } catch (_) {
      // Fallback: record rejection through event stream if server unreachable
      await _eventStream.recordSharedResourceAction(
        action: 'rejected',
        sharedResourceId: sharedResourceId,
        resourceType: 'community_share',
      );
    }
  }
}
