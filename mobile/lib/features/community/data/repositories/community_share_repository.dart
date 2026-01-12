import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

final communityShareRepositoryProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CommunityShareRepository(apiClient);
});

class CommunityShareRepository {
  CommunityShareRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<void> shareResource({
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
  }
}
